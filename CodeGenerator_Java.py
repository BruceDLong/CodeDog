# CodeGenerator_Java.py
import progSpec
import re
import datetime
import pattern_Write_Main
import codeDogParser

buildStr_libs=''


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
    containerSpec=typeSpec['arraySpec']
    idxType=''
    if 'indexType' in containerSpec:
        idxType=containerSpec['indexType']
    if idxType[0:4]=='uint': idxType = 'long'
    elif idxType=='string': idxType = 'String'

    datastructID = containerSpec['datastructID']
    if(datastructID=='list'): datastructID = "ArrayDeque"
    elif(datastructID=='map'): datastructID = "TreeMap"
    elif(datastructID=='multimap'): datastructID = "TreeMap"  # TODO: Implement true multmaps in java
    return [datastructID, idxType]

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

def CheckObjectVars(objName, itemName, level):
    #print "Searching",objName,"for", itemName
    if(not objName in objectsRef[0]):
        return 0  # Model def not found
    retVal=None
    wrappedTypeSpec = progSpec.isWrappedType(objectsRef, objName)
    if(wrappedTypeSpec != None):
        actualFieldType=wrappedTypeSpec['fieldType']
        if not isinstance(actualFieldType, basestring):
            #print "'actualFieldType", wrappedTypeSpec, actualFieldType, objName
            retVal = CheckObjectVars(actualFieldType[0], itemName, 0)
            if retVal==0: return 0
            retVal['typeSpec']['owner']=wrappedTypeSpec['owner']
            return retVal
        else:
            if 'fieldName' in wrappedTypeSpec and wrappedTypeSpec['fieldName']==itemName:
                return wrappedTypeSpec
            else: return 0

    ObjectDef = objectsRef[0][objName]
    for field in ObjectDef['fields']:
        fieldName=field['fieldName']
        #print "--------------- FIELD:", fieldName
        if fieldName==itemName:
            return field

    # Not found so look a level deeper (Passive Inheritance)
    # Passive inheritance is disabled for now as it was slow to compile and not being used.
    # It also causes problems with the 'flags' member since multiple child structs have it.
    """
    if level>0:
        count=0
        for field in ObjectDef['fields']:
            fieldName=field['fieldName']
            typeSpec=field['typeSpec']
            fieldType=typeSpec['fieldType']
            owner=typeSpec['owner']
            if isinstance(fieldType, basestring): continue;
            tmpRetVal = CheckObjectVars(fieldType[0], itemName, level-1)
            if tmpRetVal==0: continue;
            print "PASSIVE:", itemName, tmpRetVal
            count+=1
            if(owner=='me'): connector='.'
            else: connector='->'
            retVal=tmpRetVal
            retVal['fieldName']= fieldName + connector + tmpRetVal['fieldName']
        if(count>1): print("Passive Inheritance for "+itemName+" in "+objName+" is ambiguous."); exit(2);
        if(count==1): return retVal
        """

    return 0 # Field not found in model


def fetchItemsTypeSpec(itemName):
    # return format: [{typeSpec}, 'OBJVAR']. Substitute for wrapped types.
    # TODO: also search any libraries that are used.
    global currentObjName
    #print "FETCHING:", itemName, currentObjName
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
            REF=CheckObjectVars(currentObjName, itemName, 1)
            if (REF):
                RefType="OBJVAR"

            else:
                REF=CheckObjectVars("GLOBAL", itemName, 0)
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
    if objName[-5:]=='::mem': return objName[:-5]
    return objName.replace('::', '_')

fieldNamesAlreadyUsed={}
def processFlagAndModeFields(field, fieldName, tags):
    #print "                    Coding flags and modes for:", objectName
    global fieldNamesAlreadyUsed
    flagsVarNeeded = False
    bitCursor=0
    structEnums=""
    fieldType=field['typeSpec']['fieldType'];
    fieldName=field['fieldName'];
    #print "                    ", field
    if fieldType=='flag':
        print "                        flag: ", fieldName
        flagsVarNeeded=True
        structEnums += "final int "+fieldName +" = " + hex(1<<bitCursor) +"; \t// Flag: "+fieldName+"\n"
        bitCursor += 1;
    elif fieldType=='mode':
        print "                        mode: ", fieldName, '[]'
        print field
        structEnums += "\n// For Mode "+fieldName+"\n"
        flagsVarNeeded=True
        # calculate field and bit position
        enumSize= len(field['typeSpec']['enumList'])
        numEnumBits=bitsNeeded(enumSize)
        #field[3]=enumSize;
        #field[4]=numEnumBits;
        enumMask=((1 << numEnumBits) - 1) << bitCursor

        structEnums += "final int "+fieldName +"Offset = " + hex(bitCursor) +";\n"
        structEnums += "final int "+fieldName +"Mask = " + hex(enumMask) +";"

        # enum
        count=0
        for enumName in field['typeSpec']['enumList']:
            structEnums += "final int "+enumName+"="+hex(count)+";\n"
            count=count+1

        structEnums += 'string ' + fieldName+'Strings[] = {"'+('", "'.join(field['typeSpec']['enumList']))+'"};\n'
        # read/write macros
        structEnums += "#define "+fieldName+"is(VAL) ((inf)->flags & )\n"
        # str array and printer

        bitCursor=bitCursor+numEnumBits;
    return structEnums

typeDefMap={}
ObjectsFieldTypeMap={}
def registerType(objName, fieldName, typeOfField, typeDefTag):
    ObjectsFieldTypeMap[objName+'::'+fieldName]={'rawType':typeOfField, 'typeDef':typeDefTag}
    typeDefMap[typeOfField]=typeDefTag

def convertToJavaType(fieldType):
    if(fieldType=='int32'):
        javaType='int'
    elif(fieldType=='uint32' or fieldType=='uint64'):
        javaType='long'
    elif(fieldType=='int64'):
        javaType='long'
    elif(fieldType=='char' ):
        javaType='byte'
    elif(fieldType=='bool' ):
        javaType='boolean'
    elif(fieldType=='string' ):
        javaType='String'
    else:
        javaType=convertObjectNameToCPP(fieldType)
    #print "javaType: ", javaType
    return javaType

def convertType(objects, TypeSpec):
    owner=TypeSpec['owner']
    fieldType=TypeSpec['fieldType']
    #print "fieldType: ", fieldType
    if not isinstance(fieldType, basestring):
        #if len(fieldType)>1: exit(2)
        fieldType=fieldType[0]
    baseType = progSpec.isWrappedType(objects, fieldType)
    if(baseType!=None):
        owner=baseType['owner']
        fieldType=baseType['fieldType']

    cppType="TYPE ERROR"
    if(fieldType=='<%'): return fieldType[1][0]
    if(isinstance(fieldType, basestring)):
        if(fieldType=='uint8' or fieldType=='uint16'): fieldType='uint32'
        elif(fieldType=='int8' or fieldType=='int16'): fieldType='int32'
        cppType= convertToJavaType(fieldType)
    else: cppType=convertObjectNameToCPP(fieldType[0])

    kindOfField=owner
    if kindOfField=='const':
        cppType = "final "+cppType
    elif kindOfField=='me':
        cppType = cppType
    elif kindOfField=='my':
        cppType = cppType
    elif kindOfField=='our':
        cppType = cppType
    elif kindOfField=='their':
        cppType = cppType
    else:
        print "ERROR: Owner of type not valid '" + owner + "'"
        exit(1)
    if cppType=='TYPE ERROR': print cppType, owner, fieldType;
    if 'arraySpec' in TypeSpec:
        arraySpec=TypeSpec['arraySpec']
        if(arraySpec): # Make list, map, etc
            [containerType, idxType]=getContainerType(TypeSpec)
            if containerType=='ArrayDeque':
                cppType="ArrayDeque< "+cppType+" >"
            elif containerType=='TreeMap':
                idxType="Integer" # TODO: This is a hack.
                cppType="TreeMap< "+idxType+', '+cppType+" >"
            elif containerType=='multimap':
                cppType="multimap< "+idxType+', '+cppType+" >"
    return cppType


def genIfBody(ifBody, indent):
    ifBodyText = ""
    for ifAction in ifBody:
        actionOut = processAction(ifAction, indent + "    ")
        #print "If action: ", actionOut
        ifBodyText += actionOut
    return ifBodyText

def convertNameSeg(typeSpecOut, name, paramList):
    newName = typeSpecOut['codeConverter']
    if paramList != None:
        count=1
        for P in paramList:
            oldTextTag='%'+str(count)
            [S2, argType]=codeExpr(P[0])
            if(isinstance(newName, basestring)):
                newName=newName.replace(oldTextTag, S2)
            else: exit(2)
            count+=1
        paramList=None;
    return [newName, paramList]

################################  C o d e   E x p r e s s i o n s

def codeNameSeg(segSpec, typeSpecIn, connector):
    # if TypeSpecIn has 'dummyType', this is a non-member and the first segment of the reference.
    #print "CODENAMESEG:", segSpec, typeSpecIn
    S=''
    S_alt=''
    typeSpecOut={'owner':''}
    paramList=None
    if len(segSpec) > 1 and segSpec[1]=='(':
        if(len(segSpec)==2):
            paramList=[]
        else:
            paramList=segSpec[2]

    name=segSpec[0]
    #if not isinstance(name, basestring):  print "NAME:", name, typeSpecIn
    if('arraySpec' in typeSpecIn and typeSpecIn['arraySpec']):
        [containerType, idxType]=getContainerType(typeSpecIn)
        typeSpecOut={'owner':typeSpecIn['owner'], 'fieldType': typeSpecIn['fieldType']}
        #print "NAME:", name
        if(name[0]=='['):
            [S2, idxType] = codeExpr(name[1])
            S+= '[' + S2 +']'
            return [S, typeSpecOut]
        if containerType=='ArrayDeque':
            if name=='at' or name=='insert' or name=='erase' or  name=='size' or name=='end' or  name=='rend': pass
            elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
            elif name=='front'    : name='begin()'; paramList=None;
            elif name=='back'     : name='rbegin()'; paramList=None;
            elif name=='popFirst' : name='pop_front'
            elif name=='popLast'  : name='pop_back'
            elif name=='pushFirst': name='push_front'
            elif name=='pushLast' : name='push_back'
            else: print "Unknown ArrayDeque command:", name; exit(2);
        elif containerType=='TreeMap':
            convertedIdxType=idxType
            convertedItmType=convertType(objectsRef, typeSpecOut)
            if name=='at' or name=='erase' or  name=='size': pass
            elif name=='insert'   : name='put';
            elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
            elif name=='front': name='firstEntry().getValue()'; paramList=None;
            elif name=='back': name='lastEntry().getValue()'; paramList=None;
            elif name=='popFirst' : name='pop_front'
            elif name=='popLast'  : name='pop_back'
            else: print "Unknown map command:", name; exit(2);
        elif containerType=='multimap':
            convertedIdxType=idxType
            convertedItmType=convertType(objectsRef, typeSpecOut)
            if name=='at' or name=='erase' or  name=='size': pass
            elif name=='insert'   : name='put'; #typeSpecOut['codeConverter']='put(pair<'+convertedIdxType+', '+convertedItmType+'>(%1, %2))'
            elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
            elif name=='front': name='firstEntry().getValue()'; paramList=None;
            elif name=='back': name='lastEntry().getValue()'; paramList=None;
            elif name=='popFirst' : name='pop_front'
            elif name=='popLast'  : name='pop_back'
            else: print "Unknown multimap command:", name; exit(2);
        elif containerType=='tree': # TODO: Make trees work
            if name=='insert' or name=='erase' or  name=='size': pass
            elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
            else: print "Unknown tree command:", name; exit(2)
        elif containerType=='graph': # TODO: Make graphs work
            if name=='insert' or name=='erase' or  name=='size': pass
            elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
            else: print "Unknown graph command:", name; exit(2);
        elif containerType=='stream': # TODO: Make stream work
            pass
        elif containerType=='filesystem': # TODO: Make filesystem work
            pass
        else: print "Unknown container type:", containerType; exit(2);


    elif ('dummyType' in typeSpecIn): # This is the first segment of a name
        tmp=codeSpecialFunc(segSpec)   # Check if it's a special function like 'print'
        if(tmp!=''):
            S=tmp
            return [S, '']
        [typeSpecOut, SRC]=fetchItemsTypeSpec(name)
    else:
        fType=typeSpecIn['fieldType']

        if(name=='allocate'):
            owner=typeSpecIn['owner']
            if(owner=='our'): S_alt=" = new "+fType[0]
            elif(owner=='my'): S_alt=" = new "+fType[0]
            elif(owner=='their'): S_alt=" = new "+fType[0]
            elif(owner=='me'): S_alt=" = new "+fType[0]
            elif(owner=='const'): print "ERROR: Cannot allocate a 'const' variable."; exit(1);
            else: print "ERROR: Cannot allocate variable because owner is", owner+"."; exit(1);
            typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif(name[0]=='[' and fType=='string'):
            typeSpecOut={'owner':typeSpecIn['owner'], 'fieldType': typeSpecIn['fieldType']}
            [S2, idxType] = codeExpr(name[1])
            S+= '[' + S2 +']'
            return [S, typeSpecOut]
        else:
            typeSpecOut=CheckObjectVars(typeSpecIn['fieldType'][0], name, 1)
            if typeSpecOut!=0:
                name=typeSpecOut['fieldName']
                typeSpecOut=typeSpecOut['typeSpec']

    if typeSpecOut and 'codeConverter' in typeSpecOut:
        [name, paramList]=convertNameSeg(typeSpecOut, name, paramList)

    if S_alt=='': S+=connector+name
    else: S += S_alt

    # Add parameters if this is a function call
    if(paramList != None):
        if(len(paramList)==0):
            if name != 'return' and name!='break' and name!='continue':
                S+="()"
        else:
            S+= '('+codeParameterList(paramList)+')'
    return [S,  typeSpecOut]

def codeUnknownNameSeg(segSpec):
    S=''
    paramList=None
    segName=segSpec[0]
    S += '.'+ segName
    if len(segSpec) > 1 and segSpec[1]=='(':
        if(len(segSpec)==2):
            paramList=[]
        else:
            paramList=segSpec[2]
    # Add parameters if this is a function call
    if(paramList != None):
        if(len(paramList)==0):
            S+="()"
        else:
            S+= '('+codeParameterList(paramList)+')'
    return S;

def codeItemRef(name, LorR_Val):
    S=''
    segStr=''
    segType={'owner':'', 'dummyType':True}
    connector=''
    prevLen=len(S)
    segIDX=0
    for segSpec in name:
        #print "NameSeg:", segSpec
        segName=segSpec[0]
        if(segIDX>0):
            # Detect connector to use '.' '->', '', (*...).
            connector='.'
            if(segType): # This is where to detect type of vars not found to determine whether to use '.' or '->'
                #print "SEGTYPE:", segType
                segOwner=segType['owner']
                if(segOwner!='me'): connector='.'

        if segType!=None:
            [segStr, segType]=codeNameSeg(segSpec, segType, connector)
        else:
            segStr= codeUnknownNameSeg(segSpec)
        prevLen=len(S)
        S+=segStr
        segIDX+=1

    # Handle cases where seg's type is flag or mode
    if segType and LorR_Val=='RVAL' and 'fieldType' in segType:
        fieldType=segType['fieldType']
        if fieldType=='flag':
            segName=segStr[len(connector):]
            S='(' + S[0:prevLen] + connector + 'flags & ' + segName + ')' # TODO: prevent 'segStr' namespace collisions by prepending object name to field constant
        elif fieldType=='mode':
            segName=segStr[len(connector):]
            S="((" + S[0:prevLen] + connector +  "flags&"+segName+"Mask)"+">>"+segName+"Offset)"
    return [S, segType]


def codeUserMesg(item):
    # TODO: Make 'user messages'interpolate and adjust for locale.
    S=''; fmtStr=''; argStr='';
    pos=0
    for m in re.finditer(r"%[ilscp]`.+?`", item):
        fmtStr += item[pos:m.start()+2]
        argStr += ', ' + item[m.start()+3:m.end()-1]
        pos=m.end()
    fmtStr += item[pos:]
    fmtStr=fmtStr.replace('"', r'\"')
    S='String.format('+'"'+ fmtStr +'"'+ argStr +')'
    return S

def codeFactor(item):
    ####  ( value | ('(' + expr + ')') | ('!' + expr) | ('-' + expr) | varFuncRef)
    #print '                  factor: ', item
    S=''
    retType='noType'
    item0 = item[0]
    #print "ITEM0=", item0, ">>>>>", item
    if (isinstance(item0, basestring)):
        if item0=='(':
            [S2, retType] = codeExpr(item[1])
            S+='(' + S2 +')'
        elif item0=='!':
            [S2, retType] = codeExpr(item[1])
            S+='!' + S2
        elif item0=='-':
            [S2, retType] = codeExpr(item[1])
            S+='-' + S2
        elif item0=='[':
            tmp="{"
            for expr in item[1:-1]:
                [S2, retType] = codeExpr(expr)
                if len(tmp)>1: tmp+=", "
                tmp+=S2
            tmp+="}"
            S+=tmp
        else:
            retType='string'
            if(item0[0]=="'"): S+=codeUserMesg(item0[1:-1])
            elif (item0[0]=='"'): S+='"'+item0[1:-1] +'"'
            else: S+=item0;
    else:
        if isinstance(item0[0], basestring):
            S+=item0[0]
        else:
            [codeStr, retType]=codeItemRef(item0, 'RVAL')
            S+=codeStr                                # Code variable reference or function call
    return [S, retType]

def codeTerm(item):
    #print '               term item:', item
    [S, retType]=codeFactor(item[0])
    if (not(isinstance(item, basestring))) and (len(item) > 1):
        for i in item[1]:
            #print '               term:', i
            if   (i[0] == '*'): S+=' * '
            elif (i[0] == '/'): S+=' / '
            elif (i[0] == '%'): S+=' % '
            else: print "ERROR: One of '*', '/' or '%' expected Java code generator."; exit(2)
            [S2, retType2] = codeFactor(i[1])
            S+=S2
    return [S, retType]

def codePlus(item):
    #print '            plus item:', item
    [S, retType]=codeTerm(item[0])
    if len(item) > 1:
        for  i in item[1]:
            #print '            plus ', i
            if   (i[0] == '+'): S+=' + '
            elif (i[0] == '-'): S+=' - '
            else: print "ERROR: '+' or '-' expected in Java code generator."; exit(2)
            [S2, retType2] = codeTerm(i[1])
            S+=S2
    return [S, retType]

def codeComparison(item):
    #print '         Comp item', item
    [S, retType]=codePlus(item[0])
    if len(item) > 1:
        for  i in item[1]:
            #print '         comp ', i
            if   (i[0] == '<'): S+=' < '
            elif (i[0] == '>'): S+=' > '
            elif (i[0] == '<='): S+=' <= '
            elif (i[0] == '>='): S+=' >= '
            else: print "ERROR: One of <, >, <= or >= expected in Java code generator."; exit(2)
            [S2, retType] = codePlus(i[1])
            S+=S2
            retType='bool'
    return [S, retType]

def codeIsEQ(item):
    #print '      IsEq item:', item
    [S, retType]=codeComparison(item[0])
    if len(item) > 1:
        for i in item[1]:
            #print '      IsEq ', i
            if   (i[0] == '=='): S+=' == '
            elif (i[0] == '!='): S+=' != '
            else: print "ERROR: 'and' expected in Java code generator."; exit(2)
            [S2, retType] = codeComparison(i[1])
            S+=S2
            retType='bool'
    return [S, retType]

def codeLogAnd(item):
    #print '   And item:', item
    [S, retType] = codeIsEQ(item[0])
    if len(item) > 1:
        for i in item[1]:
            #print '   AND ', i
            if (i[0] == 'and'):
                [S2, retType] = codeIsEQ(i[1])
                S+=' && ' + S2
            else: print "ERROR: 'and' expected in Java code generator."; exit(2)
            retType='bool'
    return [S, retType]

def codeExpr(item):
    #print 'Or item:', item
    [S, retType]=codeLogAnd(item[0])
    if not isinstance(item, basestring) and len(item) > 1:
        for i in item[1]:
            #print 'OR ', i
            if (i[0] == 'or'):
                S+=' || ' + codeLogAnd(i[1])[0]
            else: print "ERROR: 'or' expected in Java code generator."; exit(2)
            retType='bool'
    #print "S:",S
    return [S, retType]

def chooseVirtualRValOwner(LVAL, RVAL):
    if RVAL==0 or RVAL==None or isinstance(RVAL, basestring): return ['',''] # This happens e.g., string.size() # TODO: fix this.
    LeftOwner=LVAL['owner']
    RightOwner=RVAL['owner']
    if LeftOwner == RightOwner: return ["", ""]
    if LeftOwner=='me' and (RightOwner=='my' or RightOwner=='our' or RightOwner=='their'): return ["(*", ")"]
    if (LeftOwner=='my' or LeftOwner=='our' or LeftOwner=='their') and RightOwner=='me': return ["&", '']
    # TODO: Verify these and other combinations. e.g., do we need something like ['', '.get()'] ?

def codeParameterList(paramList):
    S=''
    count = 0
    for P in paramList:
        if(count>0): S+=', '
        count+=1
        #print "PARAM",P
        [S2, argType]=codeExpr(P[0])
        # TODO: get arg's type and call chooseVirtualRValOwner()
        S+=S2
    return S

def codeSpecialFunc(segSpec):
    S=''
    funcName=segSpec[0]
    if(funcName=='print'):
        S+='System.out.print('
        if(len(segSpec)>2):
            paramList=segSpec[2]
            count=0
            for P in paramList:
                if(count!=0): S+=", "
                count+=1
                [S2, argType]=codeExpr(P[0])
                S+=S2
        S+=")"
    #elif(funcName=='break'):
    #elif(funcName=='return'):
    #elif(funcName==''):

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
        if isinstance(fieldType, basestring):
            if(fieldDef['value']):
                [S2, rhsType]=codeExpr(fieldDef['value'][0])
                RHS = S2
                assignValue=' = '+ RHS + ';\n'
            else: assignValue=';\n'
        elif(fieldDef['value']):
                [S2, rhsType]=codeExpr(fieldDef['value'][0])
                RHS = S2
                assignValue=' = new ' + fieldType +'('+ RHS + ');\n'
        else:
            print "TYPE:", fieldType
            assignValue= " = new " + fieldType +"();\n"

        actionText = indent + fieldType + " " + varName + assignValue
        localVarsAllocated.append([varName, typeSpec])  # Tracking local vars for scope
    elif (typeOfAction =='assign'):
        [codeStr, typeSpec] = codeItemRef(action['LHS'], 'LVAL')
        LHS = codeStr
        [S2, rhsType]=codeExpr(action['RHS'][0])
        #print "RHS:", S2, typeSpec, rhsType
        #[leftMod, rightMod]=chooseVirtualRValOwner(typeSpec, rhsType)
        RHS = S2 #leftMod+S2+rightMod
        assignTag = action['assignTag']
        #print "Assign: ", LHS, RHS, typeSpec
        LHS_FieldType=typeSpec['fieldType']
        if assignTag == '':
            if LHS_FieldType=='flag':
                divPoint=startPointOfNamesLastSegment(LHS)
                LHS_Left=LHS[0:divPoint]
                bitMask =LHS[divPoint+1:]
                actionText=indent + "SetBits("+LHS_Left+"."+"flags, "+bitMask+", "+ RHS + ");\n"
                #print "INFO:", LHS, divPoint, "'"+LHS_Left+"'" 'bm:', bitMask,'RHS:', RHS
            elif LHS_FieldType=='mode':
                divPoint=startPointOfNamesLastSegment(LHS)
                LHS_Left=LHS[0:divPoint]
                bitMask =LHS[divPoint+1:]
                actionText=indent + "SetBits("+LHS_Left+"."+"flags, "+bitMask+"Mask, "+ RHS+"<<" +bitMask+"Offset"+");\n"
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
        [S2, conditionType] =  codeExpr(action['ifCondition'][0])
        ifCondition = S2
        ifBodyText = genIfBody(action['ifBody'], indent)
        actionText =  indent + "if (" + ifCondition + ") " + "{\n" + ifBodyText + indent + "}\n"
        elseBodyText = ""
        elseBody = action['elseBody']
        if (elseBody):
            if (elseBody[0]=='if'):
                elseAction = elseBody[1]
                elseText = processActionSeq(elseAction, indent)
                actionText += indent + "else " + elseText.lstrip()
            elif (elseBody[0]=='action'):
                elseAction = elseBody[1]['actionList']
                elseText = processActionSeq(elseAction, indent)
                actionText += indent + "else " + elseText.lstrip()
            else:  print"Unrecognized item after else"; exit(2);
    elif (typeOfAction =='repetition'):
        repBody = action['repBody']
        repName = action['repName']
        traversalMode = action['traversalMode']
        rangeSpec = action['rangeSpec']
        whileSpec = action['whileSpec']
        # TODO: add cases for traversing trees and graphs in various orders or ways.
        loopCounterName=''
        if(rangeSpec): # iterate over range
            [S_low, lowValType] = codeExpr(rangeSpec[2][0])
            [S_hi,   hiValType] = codeExpr(rangeSpec[4][0])
            #print "RANGE:", S_low, "..", S_hi
            ctrlVarsTypeSpec = lowValType
            if(traversalMode=='Forward' or traversalMode==None):
                actionText += indent + "for( long " + repName+'='+ S_low + "; " + repName + "!=" + S_hi +"; ++"+ repName + "){\n"
            elif(traversalMode=='Backward'):
                actionText += indent + "for( long " + repName+'='+ S_hi + "-1; " + repName + ">=" + S_low +"; --"+ repName + "){\n"
            localVarsAllocated.append([repName, ctrlVarsTypeSpec])  # Tracking local vars for scope
        elif(whileSpec):
            [whereExpr, whereConditionType] = codeExpr(whileSpec[2])
            actionText += indent + "while(" + whereExpr + "){\n"
        else: # interate over a container
            #print "ITERATE OVER", action['repList'][0]
            [repContainer, containerType] = codeExpr(action['repList'][0])
            datastructID = containerType['arraySpec']['datastructID']

            wrappedTypeSpec = progSpec.isWrappedType(objectsRef, containerType['fieldType'][0])
            if(wrappedTypeSpec != None):
                containerType=wrappedTypeSpec

            containedType=containerType['fieldType']
            ctrlVarsTypeSpec = {'owner':containerType['owner'], 'fieldType':containedType}
            if datastructID=='multimap' or datastructID=='map':
                keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType, 'codeConverter':(repName+'.first')}
                localVarsAllocated.append([repName+'_key', keyVarSpec])  # Tracking local vars for scope
                ctrlVarsTypeSpec['codeConverter'] = (repName+'.second')
            elif datastructID=='list':
                loopCounterName=repName+'_key'
                keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType}
                localVarsAllocated.append([loopCounterName, keyVarSpec])  # Tracking local vars for scope
            containedTypeStr=convertType(objectsRef, ctrlVarsTypeSpec)
            print "ITEMS:", actionText, indent, containedType," " , repName,' :', repContainer
            actionText += (indent + "for("+containedTypeStr+" " + repName+' :'+ repContainer+"){\n")

            localVarsAllocated.append([repName, ctrlVarsTypeSpec])  # Tracking local vars for scope

        if action['whereExpr']:
            [whereExpr, whereConditionType] = codeExpr(action['whereExpr'])
            actionText += indent + "    " + 'if (!' + whereExpr + ') continue;\n'
        if action['untilExpr']:
            [untilExpr, untilConditionType] = codeExpr(action['untilExpr'])
            actionText += indent + '    ' + 'if (' + untilExpr + ') break;\n'
        repBodyText = ''
        for repAction in repBody:
            actionOut = processAction(repAction, indent + "    ")
            repBodyText += actionOut
        if loopCounterName!='':
            actionText=indent + "long " + loopCounterName + "=0;\n" + actionText
            repBodyText += indent + "    " + "++" + loopCounterName + ";\n"
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
        typeSpec =field['typeSpec']
        fieldType=typeSpec['fieldType']
        fieldName = field['fieldName']
        if(fieldType=='flag' or fieldType=='mode'): 
            if fieldName in fieldNamesAlreadyUsed: continue
            else:fieldNamesAlreadyUsed[fieldName]=objectName
            structCode = indent + processFlagAndModeFields(field, fieldName, tags)
            structCodeAcc  += structCode 
            print "structCodeAcc", structCodeAcc
            continue
        if(typeSpec['argList'] or typeSpec['argList']!=None): continue
        if(typeSpec['arraySpec'] or typeSpec['arraySpec']!=None): continue
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
    globalFuncsAcc=''
    funcDefCodeAcc=''
    structCodeAcc=""
    ObjectDef = objects[0][objectName]
    for field in ObjectDef['fields']:
        localArgsAllocated=[]
        funcDefCode=""
        structCode=""
        globalFuncs=""
        funcText=""
        typeSpec =field['typeSpec']
        fieldType=typeSpec['fieldType']
        fieldName = field['fieldName']
        if(fieldType=='flag' or fieldType=='mode'): 
            if fieldName in fieldNamesAlreadyUsed: continue
            else:fieldNamesAlreadyUsed[fieldName]=objectName
            structCode = indent + processFlagAndModeFields(field, fieldName, tags)
            structCodeAcc  += structCode 
            print "structCodeAcc", structCodeAcc
            continue
        fieldOwner=typeSpec['owner']
        fieldName =field['fieldName']
        fieldValue=field['value']
        fieldArglist = typeSpec['argList']
        if fieldName=='opAssign': fieldName='operator='
        convertedType = convertObjectNameToCPP(convertType(objects, typeSpec))
        typeDefName = convertedType # progSpec.createTypedefName(fieldType)
        print "                       ", fieldType, fieldName
        if(fieldValue == None):fieldValueText=""
        elif(fieldOwner=='const'):
            if isinstance(fieldValue, basestring):
                fieldValueText = ' = "'+ fieldValue + '"'
            else: fieldValueText = " = "+ codeExpr(fieldValue)[0]
        elif(fieldArglist==None):
            fieldValueText = " = "+ codeExpr(fieldValue[0])[0]
        else: fieldValueText = " = "+ str(fieldValue)
        #registerType(objectName, fieldName, convertedType, "")
        if(fieldOwner=='const'):
            structCode += indent + convertedType + ' ' + fieldName + fieldValueText +';\n';
        elif(fieldArglist==None):
            structCode += indent + convertedType + ' ' + fieldName + fieldValueText +';\n';
        #################################################################
        else: # Arglist exists so this is a function.
            if(fieldType=='none'):
                convertedType=''
            else:
                #print convertedType
                convertedType+=''

        ##### Generate function header for both decl and defn.
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
                    pass #registerType(objectName, fieldName, convertedType, typeDefName)
                else: typeDefName=convertedType
                LangFormOfObjName = convertObjectNameToCPP(objectName)
            #structCode += indent + "public static " + typeDefName +' ' + fieldName +"("+argListText+")\n";
            objPrefix=LangFormOfObjName
            if(objectName=='GLOBAL' and fieldName=='main'):
                #funcDefCode += 'public static void main(String[] args)'
                structCode += indent + "public static " + typeDefName +' ' + fieldName +"(String[] args);\n";
                #localArgsAllocated.append(['args', {'owner':'me', 'fieldType':'String', 'arraySpec':None,'argList':None}])
            elif(objectName=='GLOBAL') :
                structCode += indent + "public static " + typeDefName + ' ' + fieldName +"("+argListText+");\n"
            else:
                #funcDefCode += typeDefName +' ' + objPrefix + fieldName +"("+argListText+")"
                structCode += indent + "public " + typeDefName +' ' + fieldName +"("+argListText+")\n";

            ##### Generate Function Body
            verbatimText=field['value'][1]
            if (verbatimText!=''): # This function body is 'verbatim'.
                if(verbatimText[0]=='!'): # This is a code conversion pattern. Don't write a function decl or body.
                    structCode=""
                    funcText=""
                    funcDefCode=""
                    globalFuncs=""
                else:
                    funcText=verbatimText
            # No verbatim found so generate function text from action sequence
            elif field['value'][0]!='':
                structCode += indent + processActionSeq(field['value'][0], '    ')+"\n"
            else:
                print "ERROR: In processOtherFields: no funcText or funcTextVerbatim found"
                exit(1)

            funcDefCode += funcText+"\n\n"

        funcDefCodeAcc += ""
        structCodeAcc  += structCode + funcDefCode
        globalFuncsAcc += globalFuncs


    #constructCode=generate_constructor(objects, objectName, tags, indent)
    constructCode=""
    structCodeAcc+=constructCode
    return [structCodeAcc, funcDefCodeAcc]


def generateAllObjectsButMain(objects, tags):
    print "\n            Generating Objects..."
    global currentObjName
    constsEnums="\n//////////////////////////////////////////////////////////\n////   F l a g   a n d   M o d e   D e f i n i t i o n s\n\n"
    #forwardDecls="\n";
    structCodeAcc='\n////////////////////////////////////////////\n//   O b j e c t   D e c l a r a t i o n s\n\n';
    funcCodeAcc="\n//////////////////////////////////////\n//   M e m b e r   F u n c t i o n s\n\n"
    needsFlagsVar=False;
    for objectName in objects[1]:
        if progSpec.isWrappedType(objects, objectName)!=None: continue
        if(objectName[0] != '!'):
            print "                [" + objectName+"]"
            currentObjName=objectName
            #[needsFlagsVar, strOut]=processFlagAndModeFields(objects, objectName, tags)
            #constsEnums+=strOut
            if(needsFlagsVar):
                progSpec.addField(objects[0], objectName, progSpec.packField(False, 'me', "uint64", None, 'flags', None, None))
            if(objects[0][objectName]['stateType'] == 'struct'): # and ('enumList' not in objects[0][objectName]['typeSpec'])):
                LangFormOfObjName = convertObjectNameToCPP(objectName)
                #forwardDecls+="struct " + LangFormOfObjName + ";  \t// Forward declaration\n"
                [structCode, funcCode]=processOtherStructFields(objects, objectName, tags, '    ')
                structCodeAcc += "\nclass "+LangFormOfObjName+"{\n" + structCode + '};\n'
                funcCodeAcc+=funcCode
        currentObjName=''
    return [constsEnums, structCodeAcc, funcCodeAcc]



def processMain(objects, tags):
    print "\n            Generating GLOBAL..."
    #TODO Java-ize this
    #header += addSpecialCode()

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
    S='\n\n//////////// Java specific code:\n'
    S+="""

    """

    return S

libInterfacesText=''
def makeFileHeader(tags):
    global buildStr_libs
    global libInterfacesText

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
    header += libInterfacesText
    header += addSpecialCode()
    return header


def integrateLibraries(tags, libID):
    print '                Integrating', libID
    # TODO: Choose static or dynamic linking based on defaults, license tags, availability, etc.
    libFiles=progSpec.fetchTagValue(tags, 'libraries.'+libID+'.libFiles')
    #print "LIB_FILES", libFiles
    global buildStr_libs
    headerStr = ''
    for libFile in libFiles:
        buildStr_libs+=' -l'+libFile
    libHeaders=progSpec.fetchTagValue(tags, 'libraries.'+libID+'.headers')
    for libHdr in libHeaders:
        headerStr += 'import '+libHdr+';\n'
        #print "Added header", libHdr
    #print 'BUILD STR', buildStr_libs
    return headerStr

def connectLibraries(objects, tags, libsToUse):
    print "\n            Choosing Libaries to link..."
    headerStr = ''
    for lib in libsToUse:
        headerStr += integrateLibraries(tags, lib)
    return headerStr

def createInit_DeInit(objects, tags):
    initCode=''; deinitCode=''

    if 'initCode'   in tags: initCode  = tags['initCode']
    if 'deinitCode' in tags: deinitCode= tags['deinitCode']

    GLOBAL_CODE="""
struct GLOBAL{
    me void: initialize() <- {
        %s
    }

    me void: deinitialize() <- {
        %s
    }
}
    """ % (initCode, deinitCode)

    codeDogParser.AddToObjectFromText(objects[0], objects[1], GLOBAL_CODE )

def generate(objects, tags, libsToUse):
    #print "\nGenerating CPP code...\n"
    global objectsRef
    global buildStr_libs
    global libInterfacesText
    objectsRef=objects
    buildStr_libs +=  progSpec.fetchTagValue(tags, "FileName")
    createInit_DeInit(objects, tags[0])
    libInterfacesText=connectLibraries(objects, tags, libsToUse)
    header = makeFileHeader(tags)
    [constsEnums, structCodeAcc, funcCodeAcc]=generateAllObjectsButMain(objects, tags)
    #topBottomStrings = processMain(objects, tags)
    #typeDefCode = produceTypeDefs(typeDefMap)
    if('cpp' in progSpec.codeHeader): codeHeader=progSpec.codeHeader['cpp']
    else: codeHeader=''
    outputStr = header + constsEnums + codeHeader  + structCodeAcc + funcCodeAcc
    return outputStr
