# CodeGenerator_CPP.py
import progSpec
import re
import datetime
import pattern_Write_Main

buildStr_libs='g++ -g -std=gnu++11 '


def bitsNeeded(n):
    if n <= 1:
        return 0
    else:
        return 1 + bitsNeeded((n + 1) / 2)

###### Routines to track types of identifiers and to look up type based on identifier.

objectsRef=[]
localVarsAllocated = []   # Format: [varName, typeSpec]
localArgsAllocated = []   # Format: [varName, typeSpec]
currentObjName=''

def getContainerType(typeSpec):
    idxType=typeSpec['arraySpec']['indexType']
    if(idxType[0:4]=='uint'): return "deque"
    elif idxType=='string': return 'map'
    print "ERROR: Unknown data structure type"
    exit(2)

def CheckBuiltinItems(itemName):
    if(itemName=='print'):  return [{'owner':'const', 'fieldType':'void', 'arraySpec':None,'argList':None}, 'BUILTIN']
    if(itemName=='return'): return [{'owner':'const', 'fieldType':'void', 'arraySpec':None,'argList':None}, 'BUILTIN']
    if(itemName=='sqrt'):   return [{'owner':'const', 'fieldType':'number', 'arraySpec':None,'argList':None}, 'BUILTIN']

def CheckFunctionsLocalVarArgList(itemName):
    #print "Searching function for", itemName
    global localVarsAllocated
    for item in reversed(localVarsAllocated):
        if item[0]==itemName:
            return [item[1], 'LOCAL']
    global localArgsAllocated
    for item in reversed(localArgsAllocated):
        if item[0]==itemName:
            return [item[1], 'FUNCARG']
    return 0

def CheckObjectVars(objName, itemName):
    #print "Searching",objName,"for", itemName
    if(not objName in objectsRef[0]):
        return 0  # Model def not found
    ObjectDef = objectsRef[0][objName]
    for field in ObjectDef['fields']:
        fieldName=field['fieldName']
        if fieldName==itemName:
            if itemName=='draw_cb':
                print "OBJECTDEF:", field['value']
            return field
    return 0 # Field not found in model


def fetchItemsTypeSpec(itemName):
    # return format: [{typeSpec}, 'OBJVAR']. Substitute for wrapped types.
    # TODO: also search any libraries that are used.
    #print "FETCHING:", itemName
    global currentObjName
    RefType=""
    REF=CheckBuiltinItems(itemName)
    if (REF):
        RefType="BUILTIN"
        return REF
    else:
        REF=CheckFunctionsLocalVarArgList(itemName)
        if (REF):
            RefType="LOCAL"
            return REF
        else:
            REF=CheckObjectVars(currentObjName, itemName)
            if (REF):
                RefType="OBJVAR"

            else:
                REF=CheckObjectVars("GLOBAL", itemName)
                if (REF):
                    RefType="GLOBAL"
                else:
                    #print "\nVariable", itemName, "could not be found."
                    #exit(1)
                    return [None, "LIB"]
    return [REF['typeSpec'], RefType]
    # Example: [{typeSpec}, 'OBJVAR']

###### End of type tracking code

def convertObjectNameToCPP(objName):
    return objName.replace('::', '_')

def processFlagAndModeFields(objects, objectName, tags):
    print "                    Coding flags and modes for:", objectName
    flagsVarNeeded = False
    bitCursor=0
    structEnums="\n\n// *** Code for manipulating "+objectName+' flags and modes ***\n'
    ObjectDef = objects[0][objectName]
    for field in ObjectDef['fields']:
        fieldType=field['typeSpec']['fieldType'];
        fieldName=field['fieldName'];
        #print "                    ", field

        if fieldType=='flag':
            print "                        flag: ", fieldName
            flagsVarNeeded=True
            structEnums += "const int "+fieldName +" = " + hex(1<<bitCursor) +"; \t// Flag: "+fieldName+"\n"
            bitCursor += 1;
        elif fieldType=='mode':
            #print "                        mode: ", fieldName, '[]'
            #print field
            structEnums += "\n// For Mode "+fieldName+"\n"
            flagsVarNeeded=True
            # calculate field and bit position
            enumSize= len(field['typeSpec']['enumList'])
            numEnumBits=bitsNeeded(enumSize)
            #field[3]=enumSize;
            #field[4]=numEnumBits;
            enumMask=((1 << numEnumBits) - 1) << bitCursor

            structEnums += "const int "+fieldName +"Offset = " + hex(bitCursor) +";\n"
            structEnums += "const int "+fieldName +"Mask = " + hex(enumMask) +";"

            # enum
            count=0
            structEnums += "\nenum " + fieldName +" {"
            for enumName in field['typeSpec']['enumList']:
                structEnums += enumName+"="+hex(count<<bitCursor)
                count=count+1
                if(count<enumSize): structEnums += ", "
            structEnums += "};\n";

            structEnums += 'string ' + fieldName+'Strings[] = {"'+('", "'.join(field['typeSpec']['enumList']))+'"};\n'
            # read/write macros
            structEnums += "#define "+fieldName+"is(VAL) ((inf)->flags & )\n"
            # str array and printer

            bitCursor=bitCursor+numEnumBits;
    return [flagsVarNeeded, structEnums]

typeDefMap={}
ObjectsFieldTypeMap={}
def registerType(objName, fieldName, typeOfField, typeDefTag):
    ObjectsFieldTypeMap[objName+'::'+fieldName]={'rawType':typeOfField, 'typeDef':typeDefTag}
    typeDefMap[typeOfField]=typeDefTag

def convertType(objects, TypeSpec):
    owner=TypeSpec['owner']
    fieldType=TypeSpec['fieldType']
    #print "fieldType: ", fieldType
    if not isinstance(fieldType, basestring):
        if len(fieldType)>1: exit(2)
        fieldType=fieldType[0]
    baseType = progSpec.isWrappedType(objects, fieldType)
    if(baseType!=None):
        owner=baseType['owner']
        fieldType=baseType['fieldType']

    cppType="TYPE ERROR"
    if(fieldType=='<%'): return fieldType[1][0]
    if(isinstance(fieldType, basestring)):
        if(fieldType=='uint32' or fieldType=='uint64' or fieldType=='int32' or fieldType=='int64'):
            cppType=fieldType+'_t'
        else:
            cppType=fieldType
    else: cppType=convertObjectNameToCPP(fieldType[0])

    kindOfField=owner
    if kindOfField=='const':
        cppType = "const "+cppType
    elif kindOfField=='me':
        cppType = cppType
    elif kindOfField=='my':
        cppType="unique_ptr<"+cppType + '> '
    elif kindOfField=='our':
        cppType="shared_ptr<"+cppType + '> '
    elif kindOfField=='their':
        cppType += '*'
    else:
        print "ERROR: Owner of type not valid '" + owner + "'"
        exit(1)
    if cppType=='TYPE ERROR': print cppType, owner, fieldType;
    arraySpec=TypeSpec['arraySpec']
    if(arraySpec): # Make list, map, etc
        arrayType=getContainerType(TypeSpec)
        if arrayType=='deque':
            cppType="deque< "+cppType+" >"
        elif arrayType=='map':
            cppType="map< "+cppType+" >"
    return cppType


def genIfBody(ifBody, indent):
    ifBodyText = ""
    for ifAction in ifBody:
        actionOut = processAction(ifAction, indent + "    ")
        #print "If action: ", actionOut
        ifBodyText += actionOut
    return ifBodyText


################################  C o d e   E x p r e s s i o n s

def codeNameSeg(segSpec, typeSpecIn, connector):
    # if TypeSpecIn has 'dummyType', this is a non-member and the first segment of the reference.
    #print "CODENAMESEG:", segSpec, typeSpecIn
    S=''
    typeSpecOut={'owner':''}
    name=segSpec[0]
    if('arraySpec' in typeSpecIn and typeSpecIn['arraySpec']):
        containerType=getContainerType(typeSpecIn)
        resultTypeSpec={'owner':'me', 'fieldType': typeSpecIn['fieldType']}
        if(name=='['):
            S+= '[' + codeExpr(item0[1]) +']'
            return [S, TypeInButNotArray]
        if containerType=='deque':
            if name=='at' or name=='insert' or name=='erase' or  name=='size' or name=='front' or  name=='back': pass
            elif name=='clear': resultTypeSpec={'owner':'me', 'fieldType': ['void']}
            elif name=='popFirst' : name='pop_front'
            elif name=='popLast'  : name='pop_back'
            elif name=='pushFirst': name='push_front'
            elif name=='pushLast' : name='push_back'
            else: print "Unknown deque command:", name; exit(2);
        elif containerType=='map':
            if name=='at' or name=='insert' or name=='erase' or  name=='size' or name=='front' or  name=='back': pass
            elif name=='clear': resultTypeSpec={'owner':'me', 'fieldType': ['void']}
            elif name=='popFront' : name='pop_front'
            elif name=='popBack'  : name='pop_back'
            else: print "Unknown map command:", name; exit(2);
        else: print "Unknown container type:", containerType; exit(2);
        typeSpecOut={'owner':'me', 'fieldType': typeSpecIn['fieldType']}


    elif ('dummyType' in typeSpecIn): # This is the first segment of a name
        tmp=codeSpecialFunc(segSpec)   # Check if it's a special function like 'print'
        if(tmp!=''):
            S=tmp
            return [S, '']
        typeSpecOut=fetchItemsTypeSpec(name)[0]
    else:
        fType=typeSpecIn['fieldType']
        print "TypeSpecIN:", fType

        typeSpecOut=CheckObjectVars(typeSpecIn['fieldType'][0], name)
        if typeSpecOut!=0: typeSpecOut=typeSpecOut['typeSpec']

    S+=connector+name

    # Add parameters if this is a function call
    if(len(segSpec) > 1 and segSpec[1]=='('):
        if(len(segSpec)==2):
            S+="()"
        else:
            print "TypeOUT:", typeSpecOut
            S+= '('+codeParameterList(segSpec[2])+')'
    return [S,  typeSpecOut]

def codeItemRef(name, LorR_Val):
    S=''
    segStr=''
    segType={'owner':'', 'dummyType':True}
    connector=''
    prevLen=len(S)
    segIDX=0
    for segSpec in name:
        print "NameSeg:", segSpec
        segName=segSpec[0]
        if(segIDX>0):
            # Detect connector to use '.' '->', '', (*...).
            connector='.'
            if(segType): # This is where to detect type of vars not found to determine whether to use '.' or '->'
                segOwner=segType['owner']
                if(segOwner!='me'): connector='->'

        if segType!=None:
            [segStr, segType]=codeNameSeg(segSpec, segType, connector)
        prevLen=len(S)
        S+=segStr
        segIDX+=1

    # Handle cases where seg's type is flag or mode
    if segType and LorR_Val=='RVAL':
        fieldType=segType['fieldType']
        if fieldType=='flag':
            S='(' + S[0:prevLen] + connector + 'flags & ' + segStr + ')' # TODO: prevent 'segStr' namespace collisions by prepending object name to field constant
        elif fieldType=='mode':
            S="((" + S[0:prevLen] + "flags&"+segStr+"Mask)"+">>"+segStr+"Offset)"

    return [S, segType]


def codeUserMesg(item):
    # TODO: Make 'user messages'interpolate and adjust for locale.
    S=''; fmtStr=''; argStr='';
    pos=0
    for m in re.finditer(r"%[ils]`.+?-`", item):
        fmtStr += item[pos:m.start()+2]
        argStr += ', ' + item[m.start()+3:m.end()-1]
        pos=m.end()
    fmtStr += item[pos:-1]
    S='strFmt('+'"'+ fmtStr +'"'+ argStr +')'
    return S

def codeFactor(item):
    ####  ( value | ('(' + expr + ')') | ('!' + expr) | ('-' + expr) | varFuncRef)
    #print '                  factor: ', item
    S=''
    item0 = item[0]
    #print "ITEM0=", item0
    if (isinstance(item0, basestring)):
        if item0=='(':
            S+='(' + codeExpr(item[1]) +')'
        elif item0=='!':
            S+='!' + codeExpr(item[1])
        elif item0=='-':
            S+='-' + codeExpr(item[1])
        else:
            if(item0[0]=="'"): S+=codeUserMesg(item0[1:-1])
            elif (item0[0]=='"'): S+='"'+item0[1:-1] +'"'
            else: S=item0
    else:
        [codeStr, typeSpec]=codeItemRef(item0, 'RVAL')
        S+=codeStr                                # Code variable reference or function call
    return S

def codeTerm(item):
    #print '               term item:', item
    S=codeFactor(item[0])
    if (not(isinstance(item, basestring))) and (len(item) > 1):
        for i in item[1]:
            #print '               term:', i
            if   (i[0] == '*'): S+=' * '
            elif (i[0] == '/'): S+=' / '
            elif (i[0] == '%'): S+=' % '
            else: print "ERROR: One of '*', '/' or '%' expected in c++ code generator."; exit(2)
            S+=codeFactor(i[1])
    return S

def codePlus(item):
    #print '            plus item:', item
    S=codeTerm(item[0])
    if len(item) > 1:
        for  i in item[1]:
            #print '            plus ', i
            if   (i[0] == '+'): S+=' + '
            elif (i[0] == '-'): S+=' - '
            else: print "ERROR: '+' or '-' expected in c++ code generator."; exit(2)
            S+=codeTerm(i[1])
    return S

def codeComparison(item):
    #print '         Comp item', item
    S=codePlus(item[0])
    if len(item) > 1:
        for  i in item[1]:
            #print '         comp ', i
            if   (i[0] == '<'): S+=' < '
            elif (i[0] == '>'): S+=' > '
            elif (i[0] == '<='): S+=' <= '
            elif (i[0] == '>='): S+=' >= '
            else: print "ERROR: One of <, >, <= or >= expected in c++ code generator."; exit(2)
            S+=codePlus(i[1])
    return S

def codeIsEQ(item):
    #print '      IsEq item:', item
    S=codeComparison(item[0])
    if len(item) > 1:
        for i in item[1]:
            #print '      IsEq ', i
            if   (i[0] == '=='): S+=' == '
            elif (i[0] == '!='): S+=' != '
            else: print "ERROR: 'and' expected in c++ code generator."; exit(2)
            S+=codeComparison(i[1])
    return S

def codeLogAnd(item):
    #print '   And item:', item
    S= codeIsEQ(item[0])
    if len(item) > 1:
        for i in item[1]:
            #print '   AND ', i
            if (i[0] == 'and'):
                S+=' && ' + codeIsEQ(i[1])
            else: print "ERROR: 'and' expected in c++ code generator."; exit(2)
    return S

def codeExpr(item):
    #print 'Or item:', item
    S=codeLogAnd(item[0])
    if len(item) > 1:
        for i in item[1]:
            #print 'OR ', i
            if (i[0] == 'or'):
                S+=' || ' + codeLogAnd(i[1])
            else: print "ERROR: 'or' expected in c++ code generator."; exit(2)
    #print "S:",S
    return S

def codeParameterList(paramList):
    S=''
    count = 0
    for P in paramList:
        if(count>0): S+=', '
        count+=1
        #print "PARAM",P
        S+=codeExpr(P[0])
    return S

def codeSpecialFunc(segSpec):
    S=''
    funcName=segSpec[0]
    if(funcName=='print'):
        S+='cout'
        if(len(segSpec)>2):
            paramList=segSpec[2]
            for P in paramList:
                S+=' << '+codeExpr(P[0])
    return S

def codeFuncCall(funcCallSpec):
    S=''
   # if(len(funcCallSpec)==1):
       # tmpStr=codeSpecialFunc(funcCallSpec)
       # if(tmpStr != ''):
       #     return tmpStr
    [codeStr, typeSpec]=codeItemRef(funcCallSpec, 'RVAL')
    # We could check type of parameters here.
    S+=codeStr
    return S

def startPointOfNamesLastSegment(name):
    p=len(name)-1
    while(p>0):
        if name[p]=='>' or name[p]=='.':
            break
        p-=1
    return p

def processAction(action, indent):
    #make a string and return it
    global localVarsAllocated
    actionText = ""
    typeOfAction = action['typeOfAction']

    if (typeOfAction =='newVar'):
        fieldDef=action['fieldDef']
        typeSpec= fieldDef['typeSpec']
        varName = fieldDef['fieldName']
        fieldType = convertType(objectsRef, typeSpec)
        assignValue=''
        if(fieldDef['value']):
            assignValue=' = '+fieldDef['value']
        actionText = indent + fieldType + " " + varName + assignValue + ";\n"
        localVarsAllocated.append([varName, typeSpec])  # Tracking local vars for scope
    elif (typeOfAction =='assign'):
        [codeStr, typeSpec] = codeItemRef(action['LHS'], 'LVAL')
        LHS = codeStr
        RHS = codeExpr(action['RHS'][0])
        assignTag = action['assignTag']
        #print "Assign: ", LHS, RHS, typeSpec
        LHS_FieldType=typeSpec['fieldType']
        if assignTag == '':
            if LHS_FieldType=='flag':
                divPoint=startPointOfNamesLastSegment(LHS)
                LHS_Left=LHS[0:divPoint]
                bitMask =LHS[divPoint:]
                actionText=indent + "SetBits("+LHS_Left+"flags, "+bitMask+", "+ RHS+");\n"
                #print "INFO:", LHS, divPoint, "'"+LHS_Left+"'" 'bm:', bitMask,'RHS:', RHS
            elif LHS_FieldType=='mode':
                divPoint=startPointOfNamesLastSegment(LHS)
                LHS_Left=LHS[0:divPoint]
                bitMask =LHS[divPoint:]
                actionText=indent + "SetBits("+LHS_Left+"flags, "+bitMask+"Mask, "+ RHS+");\n"
            else:
                actionText = indent + LHS + " = " + RHS + ";\n"
        else:
            actionText = indent + "opAssign" + assignTag + '(' + LHS + ", " + RHS + ");\n"
    elif (typeOfAction =='swap'):
        LHS =  ".".join(action['LHS'])
        RHS =  ".".join(action['LHS'])
        #print "swap: ", LHS, RHS
        actionText = indent + "swap (" + LHS + ", " + RHS + ");\n"
    elif (typeOfAction =='conditional'):
        ifCondition = codeExpr(action['ifCondition'][0])
        ifBodyText = genIfBody(action['ifBody'], indent)
        actionText =  indent + "if (" + ifCondition + ") " + "{\n" + ifBodyText + indent + "}\n"
        elseBodyText = ""
        elseBody = action['elseBody']
        if (elseBody):
            #print 'ELSE BODY.......ELSE BODY.......ELSE BODY:', elseBody
            """  if (action['nextIf'] ):
                elseIf = elseBody
                elseIfText = processAction(elseIf, indent)
                #print "ELSE IF:  ELSE IF:  ELSE IF:  ELSE IF:  ", elseIfText
                actionText += indent + "else " + elseIfText.lstrip()
"""
            if ('actionList' in elseBody):
                elseActSeq = elseBody['actionList']
            else: elseActSeq = elseBody['elseBody']['actionList']
            elseText = processActionSeq(elseActSeq, indent)
            #print "ELSE: ELSE: ELSE: ELSE: ELSE: ", elseText
            actionText += indent + "else " + elseText.lstrip()
    elif (typeOfAction =='repetition'):
        repBody = action['repBody']
        repName = action['repName']
        traversalMode = action['traversalMode']
        rangeSpec = action['rangeSpec']
        # TODO: add cases for traversing trees and graphs in various orders or ways.
        if(rangeSpec): # iterate over range
            if(traversalMode=='Forward' or traversalMode==None):
                actionText += indent + "for( auto " + repName+'='+codeExpr(rangeSpec[2][0]) + "; " + repName + "!=" +codeExpr(rangeSpec[4][0])+"; ++"+ repName + "){\n"
            elif(traversalMode=='Backward'):
                actionText += indent + "for( auto " + repName+'='+codeExpr(rangeSpec[4][0]) + "; " + repName + "!=" +codeExpr(rangeSpec[2][0])+"; --"+ repName + "){\n"

        else: # interate over a container
            repList = ".".join(action['repList'])
            actionText += indent + "for( auto " + repName + ":" + repList + "){\n"

        # TODO: The type ['int'] in the next line should be the type of the control variable.
        ctrlVarsTypeSpec = ['int']
   #     localVarsAllocated.append([repName, ctrlVarsTypeSpec])  # Tracking local vars for scope

        if action['whereExpr']:
            whereExpr = codeExpr(action['whereExpr'])
            actionText += indent + "    " + 'if (!' + whereExpr + ') continue;\n'
        if action['untilExpr']:
            untilExpr = codeExpr(action['untilExpr'])
            actionText += indent + '    ' + 'if (' + untilExpr + ') break;\n'
        repBodyText = ''
        for repAction in repBody:
            actionOut = processAction(repAction, indent + "    ")
            repBodyText += actionOut
        actionText += repBodyText + indent + '}\n'
    elif (typeOfAction =='funcCall'):
        #print "\n########################################## FUNCTION CALL AS ACTION",action['calledFunc']
        calledFunc = action['calledFunc']
        if calledFunc[0][0] == 'if' or calledFunc=='withEach' or calledFunc=='until' or calledFunc=='where':
            print "\nERROR: It is not allowed to name a function", calledFunc[0][0]
            exit(2)
        actionText = indent + codeFuncCall(calledFunc) + ';\n'
    elif (typeOfAction =='actionSeq'):
        actionListIn = action['actionList']
        actionListText = ''
        for action in actionListIn:
            actionListOut = processAction(action, indent + "    ")
            actionListText += actionListOut
        #print "actionSeq: ", actionListText
        actionText += indent + "{\n" + actionListText + indent + '}\n'
    else:
        print "error in processAction: ", action
 #   print "actionText", actionText
    return actionText


def processActionSeq(actSeq, indent):
    global localVarsAllocated
    localVarsAllocated.append(["STOP",''])
    actSeqText = "{\n"
    for action in actSeq:
        actionText = processAction(action, indent+'    ')
        #print actionText
        actSeqText += actionText
    actSeqText += "\n" + indent + "}"
    localVarRecord=['','']
    while(localVarRecord[0] != 'STOP'):
        localVarRecord=localVarsAllocated.pop()
    return actSeqText

def generate_constructor(objects, ClassName, tags):
    baseType = progSpec.isWrappedType(objects, ClassName)
    if(baseType!=None): return ''
    if not ClassName in objects[0]: return ''
    print "                    Generating Constructor for:", ClassName
    constructorInit=":"
    constructorArgs="    "+convertObjectNameToCPP(ClassName)+"("
    count=0
    ObjectDef = objects[0][ClassName]
    for field in ObjectDef['fields']:
        #print "^^^^^^^^^^^^^^^^^^^^"
        typeSpec =field['typeSpec']
        fieldType=typeSpec['fieldType']
        if(fieldType=='flag' or fieldType=='mode'): continue
        if(typeSpec['argList'] or typeSpec['argList']!=None): continue
        fieldOwner=typeSpec['owner']
        if(fieldOwner=='const'): continue
        convertedType = convertType(objects, typeSpec)
        fieldName=field['fieldName']

        #print "                        Constructing:", ClassName, fieldName, fieldType, convertedType
        if(fieldOwner != 'me'):
            if(fieldOwner != 'my'):
                print "                > ", fieldOwner, convertedType, fieldName
                constructorArgs += convertedType+" _"+fieldName+"=0,"
                constructorInit += fieldName+"("+" _"+fieldName+"),"
                count += 1
        elif (isinstance(fieldType, basestring)):
            if(fieldType[0:3]=="int" or fieldType[0:4]=="uint"):
                constructorArgs += convertedType+" _"+fieldName+"=0,"
                constructorInit += fieldName+"("+" _"+fieldName+"),"
                count += 1
            elif(fieldType=="string"):
                constructorArgs += convertedType+" _"+fieldName+'="",'
                constructorInit += fieldName+"("+" _"+fieldName+"),"
                count += 1
    if(count>0):
        constructorInit=constructorInit[0:-1]
        constructorArgs=constructorArgs[0:-1]
        constructCode = constructorArgs+")"+constructorInit+"{};\n"
    else: constructCode=''
    return constructCode

def processOtherStructFields(objects, objectName, tags, indent):
    print "                    Coding fields for", objectName
    global localArgsAllocated
    globalFuncs=''
    funcDefCode=''
    structCode=""
    ObjectDef = objects[0][objectName]
    for field in ObjectDef['fields']:
        localArgsAllocated=[]
        typeSpec =field['typeSpec']
        fieldType=typeSpec['fieldType']
        if(fieldType=='flag' or fieldType=='mode'): continue
        fieldOwner=typeSpec['owner']
        fieldName =field['fieldName']
        fieldValue=field['value']
        fieldArglist = typeSpec['argList']
        if fieldName=='opAssign': fieldName='operator='
        convertedType = convertType(objects, typeSpec)
        #print "CONVERT-TYPE:", fieldOwner, fieldType, convertedType
        typeDefName = convertedType # progSpec.createTypedefName(fieldType)
        if(fieldValue == None):fieldValueText=""
        else: fieldValueText = " = "+ str(fieldValue)
        registerType(objectName, fieldName, convertedType, "")
        print "                       ", fieldOwner, fieldType, fieldName
        if(fieldOwner=='const'):
            structCode += indent + convertedType + ' ' + fieldName + fieldValueText +';\n';
        elif(fieldArglist==None):
            structCode += indent + convertedType +' ' + fieldName + fieldValueText +';\n';
        #################################################################
        else: # Arglist exists so this is a function.
            if(fieldType=='none'):
                convertedType=''
            else:
                #print convertedType
                convertedType+=''

        ##### Generate function header for both decl and defn.
            if(objectName=='GLOBAL'):
                if fieldName=='main':
                    funcDefCode += 'int main(int argc, char *argv[])'
                    localArgsAllocated.append(['argc', {'owner':'me', 'fieldType':'int', 'arraySpec':None,'argList':None}])
                    localArgsAllocated.append(['argv', {'owner':'their', 'fieldType':'char', 'arraySpec':None,'argList':None}])  # TODO: Wrong. argv should be an array.
                else:
                    #print "FIELD: ", field
                    argList=field['typeSpec']['argList']
                    #print "ARG LIST: ", argList, len(argList)
                    argListText=""
                    if (len(argList)>0):
                        if argList[0]=='<%':
                            argListText=argList[1][0]
                        else:

                            count=0
                            for arg in argList:
                                if(count>0): argListText+=", "
                                count+=1
                                argTypeSpec =arg['typeSpec']
                                argFieldName=arg['fieldName']
                                argListText+= convertType(objects, argTypeSpec) + ' ' + argFieldName
                                localArgsAllocated.append([argFieldName, argTypeSpec])  # Tracking function argumets for scope

                    globalFuncs += "\n" + convertedType  +' '+ fieldName +"("+argListText+")"
            else:
                argList=field['typeSpec']['argList']
                if len(argList)==0:
                    argListText='' #'void'
                elif argList[0]=='<%':
                    argListText=argList[1][0]
                else:
                    argListText=""
                    count=0
                    for arg in argList:
                        if(count>0): argListText+=", "
                        count+=1
                        argTypeSpec =arg['typeSpec']
                        argFieldName=arg['fieldName']
                        argListText+= convertType(objects, argTypeSpec) + ' ' + argFieldName
                        localArgsAllocated.append([argFieldName, argTypeSpec])  # Tracking function argumets for scope
                #print "FUNCTION:",convertedType, fieldName, '(', argListText, ') '
                if(fieldType[0] != '<%'):
                    registerType(objectName, fieldName, convertedType, typeDefName)
                else: typeDefName=convertedType
                LangFormOfObjName = convertObjectNameToCPP(objectName)
                structCode += indent + typeDefName +' ' + fieldName +"("+argListText+");\n";
                objPrefix=LangFormOfObjName +'::'
                funcDefCode += typeDefName +' ' + objPrefix + fieldName +"("+argListText+")"

            ##### Generate Function Body
            if (field['value'][1]!=''): # This function body is 'verbatim'.
                funcText=field['value'][1]
            # No verbatim found so generate function text from action sequence
            elif field['value'][0]!='':
                funcText=processActionSeq(field['value'][0], '')
            else:
                print "ERROR: In processOtherFields: no funcText or funcTextVerbatim found"
                exit(1)

            if(objectName=='GLOBAL'):
                if(fieldName=='main'):
                    funcDefCode += funcText+"\n\n"
                else: globalFuncs += funcText+"\n\n"
            else: funcDefCode += funcText+"\n\n"

    if(objectName=='GLOBAL'):
        return [structCode, funcDefCode, globalFuncs]
    else:
        constructCode=generate_constructor(objects, objectName, tags)
        structCode+=constructCode
        return [structCode, funcDefCode]

def generateAllObjectsButMain(objects, tags):
    print "\n            Generating Objects..."
    global currentObjName
    constsEnums="\n//////////////////////////////////////////////////////////\n////   F l a g   a n d   M o d e   D e f i n i t i o n s\n\n"
    forwardDecls="\n";
    structCodeAcc='\n////////////////////////////////////////////\n//   O b j e c t   D e c l a r a t i o n s\n\n';
    funcCodeAcc="\n//////////////////////////////////////\n//   M e m b e r   F u n c t i o n s\n\n"
    needsFlagsVar=False;
    for objectName in objects[1]:
        if progSpec.isWrappedType(objects, objectName)!=None: continue
        if(objectName[0] != '!'):
            print "                [" + objectName+"]"
            currentObjName=objectName
            [needsFlagsVar, strOut]=processFlagAndModeFields(objects, objectName, tags)
            constsEnums+=strOut
            if(needsFlagsVar):
                progSpec.addField(objects[0], objectName, progSpec.packField(False, 'me', "uint64", None, 'flags', None, None))
            if(objectName != 'GLOBAL' and objects[0][objectName]['stateType'] == 'struct'): # and ('enumList' not in objects[0][objectName]['typeSpec'])):
                LangFormOfObjName = convertObjectNameToCPP(objectName)
                forwardDecls+="struct " + LangFormOfObjName + ";  \t// Forward declaration\n"
                [structCode, funcCode]=processOtherStructFields(objects, objectName, tags, '    ')
                structCodeAcc += "\nstruct "+LangFormOfObjName+"{\n" + structCode + '};\n'
                funcCodeAcc+=funcCode
        currentObjName=''
    return [constsEnums, forwardDecls, structCodeAcc, funcCodeAcc]



def processMain(objects, tags):
    print "\n            Generating GLOBAL..."
    if("GLOBAL" in objects[1]):
        if(objects[0]["GLOBAL"]['stateType'] != 'struct'):
            print "ERROR: GLOBAL must be a 'struct'."
            exit(2)
        [structCode, funcCode, globalFuncs]=processOtherStructFields(objects, "GLOBAL", tags, '')
        if(funcCode==''): funcCode="// No main() function.\n"
        if(structCode==''): structCode="// No Main Globals.\n"
        return ["\n\n// Globals\n" + structCode + globalFuncs, funcCode]
    return ["// No Main Globals.\n", "// No main() function defined.\n"]

def produceTypeDefs(typeDefMap):
    typeDefCode="\n// Typedefs:\n"
    for key in typeDefMap:
        val=typeDefMap[key]
        #sprint '['+key+']='+val+']'
        if(val != '' and val != key):
            typeDefCode += 'typedef '+key+' '+val+';\n'
    return typeDefCode

def makeTagText(tags, tagName):
    tagVal=progSpec.fetchTagValue(tags, tagName)
    if tagVal==None: return "Tag '"+tagName+"' is not set in the dog file."
    return tagVal

def addSpecialCode():
    S='\n\n//////////// C++ specific code:\n'
    S+="string strFmt(string mesg){return mesg;}\n"

    return S

def makeFileHeader(tags):
    global buildStr_libs

    header  = "// " + makeTagText(tags, 'Title') + " "+ makeTagText(tags, 'Version') + '\n'
    header += "// " + makeTagText(tags, 'CopyrightMesg') +'\n'
    header += "// This file: " + makeTagText(tags, 'FileName') +'\n'
    header += "// Dog File: " + makeTagText(tags, 'dogFilename') +'\n'
    header += "// Authors of CodeDog file: " + makeTagText(tags, 'Authors') +'\n'
    header += "// Build time: " + datetime.datetime.today().strftime('%c') + '\n'
    header += "\n// " + makeTagText(tags, 'Description') +'\n'
    header += "\n/*  " + makeTagText(tags, 'LicenseText') +'\n*/\n'
    header += "\n// Build Options Used: " +'Not Implemented'+'\n'
    header += "\n// Build Command: " +buildStr_libs+'\n'
    includes = re.split("[,\s]+", progSpec.fetchTagValue(tags, 'Include'))
    for hdr in includes:
        header+="\n#include "+hdr
    header += "\n\nusing namespace std; \n\n"

    header += r'static void reportFault(int Signal){cout<<"\nSegmentation Fault.\n"; fflush(stdout); abort();}'+'\n\n'

    header += "string enumText(string* array, int enumVal, int enumOffset){return array[enumVal >> enumOffset];}\n";
    header += "#define SetBits(item, mask, val) {(item) &= ~(mask); (item)|=(val);}\n"

    header += addSpecialCode()
    return header

def integrateLibrary(tags, libID):
    print '                Integrating', libID
    # TODO: Choose static or dynamic linking based on defaults, license tags, availability, etc.
    libFiles=progSpec.fetchTagValue(tags, 'libraries.'+libID+'.libFiles')
    #print "LIB_FILES", libFiles
    global buildStr_libs
    for libFile in libFiles:
        buildStr_libs+=' -l'+libFile
    libHeaders=progSpec.fetchTagValue(tags, 'libraries.'+libID+'.headers')

    for libHdr in libHeaders:
        tags[0]['Include'] +=', <'+libHdr+'>'
        #print "Added header", libHdr
    #print 'BUILD STR', buildStr_libs

def connectLibraries(objects, tags, libsToUse):
    print "\n            Choosing Libaries to link..."
    for lib in libsToUse:
        integrateLibrary(tags, lib)

def generate(objects, tags, libsToUse):
    #print "\nGenerating CPP code...\n"
    global objectsRef
    global buildStr_libs
    objectsRef=objects
    buildStr_libs +=  progSpec.fetchTagValue(tags, "FileName")
    libInterfacesText=connectLibraries(objects, tags, libsToUse)
    header = makeFileHeader(tags)
    [constsEnums, forwardDecls, structCodeAcc, funcCodeAcc]=generateAllObjectsButMain(objects, tags)
    topBottomStrings = processMain(objects, tags)
    typeDefCode = produceTypeDefs(typeDefMap)
    if('cpp' in progSpec.codeHeader): codeHeader=progSpec.codeHeader['cpp']
    else: codeHeader=''
    outputStr = header + constsEnums + forwardDecls + codeHeader + typeDefCode + structCodeAcc + topBottomStrings[0] + funcCodeAcc + topBottomStrings[1]
    return outputStr
