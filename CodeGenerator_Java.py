# CodeGenerator.py
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
    print "Searching",objName,"for", itemName
    if(not objName in objectsRef[0]):
        return 0  # Model def not found
    retVal=None
    wrappedTypeSpec = progSpec.isWrappedType(objectsRef, objName)
    if(wrappedTypeSpec != None):
        actualFieldType=wrappedTypeSpec['fieldType']
        if not isinstance(actualFieldType, basestring):
            #print "'actualFieldType", wrappedTypeSpec, actualFieldType, objName
            retVal = CheckObjectVars(actualFieldType[0], itemName, 0)
            if retVal!=0:
                retVal['typeSpec']['owner']=wrappedTypeSpec['owner']
                return retVal
        else:
            if 'fieldName' in wrappedTypeSpec and wrappedTypeSpec['fieldName']==itemName:
                #print "WRAPPED FIELDNAME:", itemName
                return wrappedTypeSpec
            else: return 0

    ObjectDef = objectsRef[0][objName]
    for field in ObjectDef['fields']:
        fieldName=field['fieldName']
        if fieldName==itemName:
            print "Found", itemName
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
                if(currentObjName=='GLOBAL'): RefType="GLOBAL"
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


fieldNamesAlreadyUsed={}
def processFlagAndModeFields(objects, objectName, tags, xlator):
    print "                    Coding flags and modes for:", objectName
    global fieldNamesAlreadyUsed
    flagsVarNeeded = False
    bitCursor=0
    structEnums=""
    ObjectDef = objects[0][objectName]
    for field in ObjectDef['fields']:
        fieldType=field['typeSpec']['fieldType'];
        fieldName=field['fieldName'];
        if fieldName in fieldNamesAlreadyUsed: continue
        else:fieldNamesAlreadyUsed[fieldName]=objectName
        #print "                    ", field
        if fieldType=='flag':
            print "                        flag: ", fieldName
            flagsVarNeeded=True
            structEnums += "final int "+fieldName +" = " + hex(1<<bitCursor) +"; \t// Flag: "+fieldName+"\n"
            bitCursor += 1;
        elif fieldType=='mode':
            print "                        mode: ", fieldName, '[]'
            #print field
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
    if structEnums!="": structEnums="\n\n// *** Code for manipulating "+objectName+' flags and modes ***\n'+structEnums
    return [flagsVarNeeded, structEnums]

typeDefMap={}
ObjectsFieldTypeMap={}
def registerType(objName, fieldName, typeOfField, typeDefTag):
    ObjectsFieldTypeMap[objName+'::'+fieldName]={'rawType':typeOfField, 'typeDef':typeDefTag}
    typeDefMap[typeOfField]=typeDefTag

def varTypeIsJavaValueType(convertedType):
    if (convertedType=='int' or convertedType=='long' or convertedType=='byte' or convertedType=='boolean' or convertedType=='char'
       or convertedType=='float' or convertedType=='double' or convertedType=='short'):
        return True
    return False

def codeAllocater(typeSpec):
    S=''
    owner=typeSpec['owner']
    fType=typeSpec['fieldType']
    if isinstance(fType, basestring): varTypeStr=fType;
    else: varTypeStr=fType[0]

    if(owner!='const'):  S="new "+varTypeStr+'()'
    else: print "ERROR: Cannot allocate a 'const' variable."; exit(1);

    return S

def genIfBody(ifBody, indent, xlator):
    ifBodyText = ""
    for ifAction in ifBody:
        actionOut = processAction(ifAction, indent + "    ", xlator)
        #print "If action: ", actionOut
        ifBodyText += actionOut
    return ifBodyText

def convertNameSeg(typeSpecOut, name, paramList, xlator):
    newName = typeSpecOut['codeConverter']
    if paramList != None:
        count=1
        for P in paramList:
            oldTextTag='%'+str(count)
            [S2, argType]=xlator['codeExpr'](P[0], xlator)
            if(isinstance(newName, basestring)):
                newName=newName.replace(oldTextTag, S2)
            else: exit(2)
            count+=1
        paramList=None;
    return [newName, paramList]

################################  C o d e   E x p r e s s i o n s

def codeNameSeg(segSpec, typeSpecIn, connector, xlator):
    # if TypeSpecIn has 'dummyType', this is a non-member and the first segment of the reference.
    #print "CODENAMESEG:", segSpec, typeSpecIn
    S=''
    S_alt=''
    namePrefix=''  # For static_Global vars
    typeSpecOut={'owner':''}
    paramList=None
    if len(segSpec) > 1 and segSpec[1]=='(':
        if(len(segSpec)==2):
            paramList=[]
        else:
            paramList=segSpec[2]

    name=segSpec[0]
    print "                                             CODENAMESEG:", name
    #if not isinstance(name, basestring):  print "NAME:", name, typeSpecIn
    if('arraySpec' in typeSpecIn and typeSpecIn['arraySpec']):
        [containerType, idxType]=xlator['getContainerType'](typeSpecIn)
        typeSpecOut={'owner':typeSpecIn['owner'], 'fieldType': typeSpecIn['fieldType']}
        print "                                                 arraySpec:"
        if(name[0]=='['):
            [S2, idxType] = xlator['codeExpr'](name[1], xlator)
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
            convertedItmType=xlator['convertType'](objectsRef, typeSpecOut, xlator)
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
            convertedItmType=xlator['convertType'](objectsRef, typeSpecOut, xlator)
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
        tmp=codeSpecialFunc(segSpec, xlator)   # Check if it's a special function like 'print'
        if(tmp!=''):
            S=tmp
            return [S, '']
        [typeSpecOut, SRC]=fetchItemsTypeSpec(name)
        if(SRC=="GLOBAL"): namePrefix = 'GLOBAL.static_Global.'
    else:
        fType=typeSpecIn['fieldType']
        owner=typeSpecIn['owner']

        if(name=='allocate'):
            S_alt=' = '+codeAllocater(typeSpecIn)
            typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif(name[0]=='[' and fType=='string'):
            typeSpecOut={'owner':owner, 'fieldType': fType}
            [S2, idxType] = xlator['codeExpr'](name[1], xlator)
            S+= '[' + S2 +']'
            return [S, typeSpecOut]
        else:
            typeSpecOut=CheckObjectVars(fType[0], name, 1)
            if typeSpecOut!=0:
                name=typeSpecOut['fieldName']
                typeSpecOut=typeSpecOut['typeSpec']

    if typeSpecOut and 'codeConverter' in typeSpecOut:
        [name, paramList]=convertNameSeg(typeSpecOut, name, paramList, xlator)
        callAsGlobal=name.find("%G")
        if(callAsGlobal >= 0): namePrefix=''

    if S_alt=='': S+=namePrefix+connector+name
    else: S += S_alt

    # Add parameters if this is a function call
    if(paramList != None):
        if(len(paramList)==0):
            if name != 'return' and name!='break' and name!='continue':
                S+="()"
        else:
            modelParams=None
            if typeSpecOut and ('argList' in typeSpecOut): modelParams=typeSpecOut['argList']
            S+= '('+codeParameterList(paramList, modelParams, xlator)+')'
    return [S,  typeSpecOut]

def codeUnknownNameSeg(segSpec, xlator):
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
            S+= '('+codeParameterList(paramList, None, xlator)+')'
    return S;

def codeItemRef(name, LorR_Val, xlator):
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
                if(segOwner!='me'): connector = xlator['PtrConnector']

        if segType!=None:
            [segStr, segType]=codeNameSeg(segSpec, segType, connector, xlator)
        else:
            segStr= codeUnknownNameSeg(segSpec, xlator)
        prevLen=len(S)


        # Should this be called as a global?
        callAsGlobal=segStr.find("%G")
        if(callAsGlobal >= 0):
            S=''
            prevLen=0
            segStr=segStr.replace("%G", '')
            segStr=segStr[len(connector):]
            connector=''

        # Should this be called C style?
        thisArgIDX=segStr.find("%0")
        if(thisArgIDX >= 0):
            if connector=='->': S="*("+S+")"
            S=segStr.replace("%0", S)
            S=S[len(connector):]
        else: S+=segStr

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


def codeUserMesg(item, xlator):
    # TODO: Make 'user messages'interpolate and adjust for locale.
    S=''; fmtStr=''; argStr='';
    pos=0
    for m in re.finditer(r"%[ilscp]`.+?`", item):
        fmtStr += item[pos:m.start()+2]
        argStr += ', ' + item[m.start()+3:m.end()-1]
        pos=m.end()
    fmtStr += item[pos:]
    fmtStr=fmtStr.replace('"', r'\"')
    S=xlator['langStringFormatterCommand'](fmtStr, argStr)
    return S

def chooseVirtualRValOwner(LVAL, RVAL):
    if RVAL==0 or RVAL==None or isinstance(RVAL, basestring): return ['',''] # This happens e.g., string.size() # TODO: fix this.
    if LVAL==0 or LVAL==None or isinstance(LVAL, basestring): return ['', '']
    LeftOwner=LVAL['owner']
    RightOwner=RVAL['owner']
    if LeftOwner == RightOwner: return ["", ""]
    if LeftOwner=='me' and (RightOwner=='my' or RightOwner=='our' or RightOwner=='their'): return ["(*", ")"]
    if (LeftOwner=='my' or LeftOwner=='our' or LeftOwner=='their') and RightOwner=='me': return ["&", '']
    # TODO: Verify these and other combinations. e.g., do we need something like ['', '.get()'] ?
    return ['','']

def codeParameterList(paramList, modelParams, xlator):
    S=''
    #if(modelParams):  print "CODE-PARAMS:", len(paramList),"=",len(modelParams)
    count = 0
    for P in paramList:
        if(count>0): S+=', '
        [S2, argType]=xlator['codeExpr'](P[0], xlator)
    #    print "    PARAM",P, '<',argType,'>'
    #    print "    MODEL", modelParams[count], '\n'
        if modelParams and (len(modelParams)>count) and ('typeSpec' in modelParams[count]):
            [leftMod, rightMod]=chooseVirtualRValOwner(modelParams[count]['typeSpec'], argType)
            S += leftMod+S2+rightMod
        else: S += S2
        count+=1
    return S

def codeSpecialFunc(segSpec, xlator):
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
                [S2, argType]=xlator['codeExpr'](P[0], xlator)
                S+=S2
        S+=")"
    elif(funcName=='AllocateOrClear'):
        if(len(segSpec)>2):
            print "ALLOCATE-OR-CLEAR():", segSpec[2][0]
            paramList=segSpec[2]
            [varName,  varTypeSpec]=xlator['codeExpr'](paramList[0][0], xlator)
            S+='if('+varName+'){'+varName+'.clear();} else {'+varName+" = "+codeAllocater(varTypeSpec)+";}"
    elif(funcName=='Allocate'):
        if(len(segSpec)>2):
            paramList=segSpec[2]
            [varName,  varTypeSpec]=xlator['codeExpr'](paramList[0][0], xlator)
            S+=varName+" = "+codeAllocater(varTypeSpec)+";"
    #elif(funcName=='break'):
    #elif(funcName=='return'):
    #elif(funcName==''):

    return S

def codeFuncCall(funcCallSpec, xlator):
    S=''
   # if(len(funcCallSpec)==1):
       # tmpStr=codeSpecialFunc(funcCallSpec)
       # if(tmpStr != ''):
       #     return tmpStr
    [codeStr, typeSpec]=codeItemRef(funcCallSpec, 'RVAL', xlator)
    S+=codeStr
    return S

def startPointOfNamesLastSegment(name):
    p=len(name)-1
    while(p>0):
        if name[p]=='>' or name[p]=='.':
            break
        p-=1
    return p

def encodeConditionalStatement(action, indent):
    print "                                         conditional else if: "
    [S2, conditionType] =  xlator['codeExpr'](action['ifCondition'][0], xlator)
    ifCondition = S2
    ifBodyText = genIfBody(action['ifBody'], indent)
    actionText =  indent + "if (" + ifCondition + ") " + "{\n" + ifBodyText + indent + "}\n"
    elseBodyText = ""
    elseBody = action['elseBody']
    if (elseBody):
        if (elseBody[0]=='if'):
            elseAction = elseBody[1]
            elseText = encodeConditionalStatement(elseAction[0], indent)
            actionText += indent + "else " + elseText.lstrip()
        elif (elseBody[0]=='action'):
            elseAction = elseBody[1]['actionList']
            elseText = processActionSeq(elseAction, indent)
            actionText += indent + "else " + elseText.lstrip()
        else:  print"Unrecognized item after else"; exit(2);
    return actionText

def processAction(action, indent, xlator):
    #make a string and return it
    global localVarsAllocated
    actionText = ""
    typeOfAction = action['typeOfAction']

    if (typeOfAction =='newVar'):
        fieldDef=action['fieldDef']
        typeSpec= fieldDef['typeSpec']
        varName = fieldDef['fieldName']
        fieldType = xlator['convertType'](objectsRef, typeSpec, xlator)
        assignValue=''
        print "                                     Action newVar: ", varName
        if isinstance(typeSpec['fieldType'], basestring):
            if(fieldDef['value']):
                print "                                         fieldDef['value']: "
                [S2, rhsType]=xlator['codeExpr'](fieldDef['value'][0], xlator)
                RHS = S2
                print "                                             RHS: ", RHS
                assignValue=' = '+ RHS + ';\n'
            else: assignValue=';\n'
        elif(fieldDef['value']):
            [S2, rhsType]=xlator['codeExpr'](fieldDef['value'][0], xlator)
            RHS = S2
            if not varTypeIsJavaValueType(fieldType):
                assignValue=' = '+ RHS + ';\n'
            else:assignValue=' = new ' + fieldType +'('+ RHS + ');\n'
        else:
            #print "TYPE:", fieldType
            assignValue= " = new " + fieldType +"();\n"

        actionText = indent + fieldType + " " + varName + assignValue
        localVarsAllocated.append([varName, typeSpec])  # Tracking local vars for scope
    elif (typeOfAction =='assign'):
        [codeStr, typeSpec] = codeItemRef(action['LHS'], 'LVAL', xlator)
        LHS = codeStr
        print "                                     assign: ", LHS
        [S2, rhsType]=xlator['codeExpr'](action['RHS'][0], xlator)
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
        print "                                     swap: ", LHS, RHS
        actionText = indent + "swap (" + LHS + ", " + RHS + ");\n"
    elif (typeOfAction =='conditional'):
        [S2, conditionType] =  xlator['codeExpr'](action['ifCondition'][0], xlator)
        ifCondition = S2
        ifBodyText = genIfBody(action['ifBody'], indent, xlator)
        actionText =  indent + "if (" + ifCondition + ") " + "{\n" + ifBodyText + indent + "}\n"
        elseBodyText = ""
        elseBody = action['elseBody']
        if (elseBody):
            if (elseBody[0]=='if'):
                elseAction = elseBody[1][0]
                elseText = encodeConditionalStatement(elseAction, indent)
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
        ctrType=xlator['typeForCounterInt']
        # TODO: add cases for traversing trees and graphs in various orders or ways.
        loopCounterName=''
        if(rangeSpec): # iterate over range
            [S_low, lowValType] = xlator['codeExpr'](rangeSpec[2][0], xlator)
            [S_hi,   hiValType] = xlator['codeExpr'](rangeSpec[4][0], xlator)
            #print "RANGE:", S_low, "..", S_hi
            ctrlVarsTypeSpec = lowValType
            if(traversalMode=='Forward' or traversalMode==None):
                actionText += indent + "for("+ctrType+" " + repName+'='+ S_low + "; " + repName + "!=" + S_hi +"; ++"+ repName + "){\n"
            elif(traversalMode=='Backward'):
                actionText += indent + "for("+ctrType+" " + repName+'='+ S_hi + "-1; " + repName + ">=" + S_low +"; --"+ repName + "){\n"
            localVarsAllocated.append([repName, ctrlVarsTypeSpec])  # Tracking local vars for scope
        elif(whileSpec):
            [whereExpr, whereConditionType] = xlator['codeExpr'](whileSpec[2], xlator)
            actionText += indent + "while(" + whereExpr + "){\n"
        else: # interate over a container
            #print "ITERATE OVER", action['repList'][0]
            [repContainer, containerType] = xlator['codeExpr'](action['repList'][0], xlator)
            #print "CONTAINER-SPEC:", repContainer, containerType
            datastructID = containerType['arraySpec']['datastructID']
            keyFieldType = containerType['arraySpec']['indexType']
            [datastructID, keyFieldType]=xlator['getContainerType'](containerType)
            print "DATAID, KEYTYPE:", [datastructID, keyFieldType]

            wrappedTypeSpec = progSpec.isWrappedType(objectsRef, containerType['fieldType'][0])
            if(wrappedTypeSpec != None):
                containerType=wrappedTypeSpec

            containedType=containerType['fieldType']
            ctrlVarsTypeSpec = {'owner':containerType['owner'], 'fieldType':containedType}
            if datastructID=='TreeMap':
                keyVarSpec = {'owner':containerType['owner'], 'fieldType':keyFieldType, 'codeConverter':(repName+'.getKey()')}
                localVarsAllocated.append([repName+'_key', keyVarSpec])  # Tracking local vars for scope
                ctrlVarsTypeSpec['codeConverter'] = (repName+'.getValue()')
                containedTypeStr=xlator['convertType'](objectsRef, ctrlVarsTypeSpec, xlator)
                indexTypeStr=xlator['convertType'](objectsRef, keyVarSpec, xlator)
                iteratorTypeStr="Map.Entry<"+indexTypeStr+", "+containedTypeStr+">"
                repContainer+='.entrySet()'
            elif datastructID=='list':
                loopCounterName=repName+'_key'
                keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType}
                localVarsAllocated.append([loopCounterName, keyVarSpec])  # Tracking local vars for scope
                iteratorTypeStr=xlator['convertType'](objectsRef, ctrlVarsTypeSpec, xlator)
            else: iteratorTypeStr=xlator['convertType'](objectsRef, ctrlVarsTypeSpec, xlator)
            print "ITEMS:", actionText, indent, containedType," " , repName,' :', repContainer
            actionText += (indent + "for("+iteratorTypeStr+" " + repName+' :'+ repContainer+"){\n")

            localVarsAllocated.append([repName, ctrlVarsTypeSpec])  # Tracking local vars for scope

        if action['whereExpr']:
            [whereExpr, whereConditionType] = xlator['codeExpr'](action['whereExpr'], xlator)
            actionText += indent + "    " + 'if (!' + whereExpr + ') continue;\n'
        if action['untilExpr']:
            [untilExpr, untilConditionType] = xlator['codeExpr'](action['untilExpr'], xlator)
            actionText += indent + '    ' + 'if (' + untilExpr + ') break;\n'
        repBodyText = ''
        for repAction in repBody:
            actionOut = processAction(repAction, indent + "    ", xlator)
            repBodyText += actionOut
        if loopCounterName!='':
            actionText=indent + ctrType+" " + loopCounterName + "=0;\n" + actionText
            repBodyText += indent + "    " + "++" + loopCounterName + ";\n"
        actionText += repBodyText + indent + '}\n'
    elif (typeOfAction =='funcCall'):
        calledFunc = action['calledFunc']
        if calledFunc[0][0] == 'if' or calledFunc=='withEach' or calledFunc=='until' or calledFunc=='where':
            print "\nERROR: It is not allowed to name a function", calledFunc[0][0]
            exit(2)
        actionText = indent + codeFuncCall(calledFunc, xlator) + ';\n'
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


def processActionSeq(actSeq, indent, xlator):
    global localVarsAllocated
    localVarsAllocated.append(["STOP",''])
    actSeqText = "{\n"
    for action in actSeq:
        actionText = processAction(action, indent+'    ', xlator)
        #print actionText
        actSeqText += actionText
    actSeqText += "\n" + indent + "} \n"
    localVarRecord=['','']
    while(localVarRecord[0] != 'STOP'):
        localVarRecord=localVarsAllocated.pop()
    return actSeqText

def generate_constructor(objects, ClassName, tags, xlator):
    baseType = progSpec.isWrappedType(objects, ClassName)
    if(baseType!=None): return ''
    if not ClassName in objects[0]: return ''
    print "                    Generating Constructor for:", ClassName
    constructorInit=":"
    constructorArgs="    "+progSpec.flattenObjectName(ClassName)+"("
    count=0
    ObjectDef = objects[0][ClassName]
    for field in ObjectDef['fields']:
        typeSpec =field['typeSpec']
        fieldType=typeSpec['fieldType']
        if(fieldType=='flag' or fieldType=='mode'): continue
        if(typeSpec['argList'] or typeSpec['argList']!=None): continue
        if(typeSpec['arraySpec'] or typeSpec['arraySpec']!=None): continue
        fieldOwner=typeSpec['owner']
        if(fieldOwner=='const'): continue
        convertedType = xlator['convertType'](objects, typeSpec, xlator)
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

def processOtherStructFields(objects, objectName, tags, indent, xlator):
    print "                    Coding fields for", objectName+ '...'
    ####################################################################
    global localArgsAllocated
    #globalFuncsAcc=''
    funcDefCodeAcc=''
    structCodeAcc=""
    ObjectDef = objects[0][objectName]
    for field in ObjectDef['fields']:
        ################################################################
        ### extracting FIELD data
        ################################################################
        localArgsAllocated=[]
        funcDefCode=""
        structCode=""
        globalFuncs=""
        funcText=""
        typeSpec =field['typeSpec']
        fieldType=typeSpec['fieldType']
        if(fieldType=='flag' or fieldType=='mode'): continue
        fieldOwner=typeSpec['owner']
        fieldName =field['fieldName']
        fieldValue=field['value']
        fieldArglist = typeSpec['argList']
        convertedType = progSpec.flattenObjectName(xlator['convertType'](objects, typeSpec, xlator))
        typeDefName = convertedType # progSpec.createTypedefName(fieldType)



        ################################################################
        ## ASSIGNMENTS
        ################################################################
        if fieldName=='opAssign':
            fieldName='operator='
            print "                         opAssign: ", fieldType, fieldName
        ################################################################
        ##CALCULATE RHS                                                 ###CALCULATE RHS###
        ################################################################
        fieldValueText=""
        if(fieldValue == None):
            if (not varTypeIsJavaValueType(convertedType) and fieldOwner!='their'):
                fieldValueText=" = new " + convertedType + "()"                  # FieldValueText is the RHS text.
            else: fieldValueText=""
        ################################################################
        elif(fieldOwner=='const'):                                          # Const always has Right hand side.
            if isinstance(fieldValue, basestring):                              # Gave a literal value for the constant.
                fieldValueText = ' = "'+ fieldValue + '"'
            else:
                fieldValueText = " = "+ xlator['codeExpr'](fieldValue, xlator)[0]               # Gave an expresssion and needs to be coded.
            print "                         Const: ", fieldType, fieldName
        ################################################################
        elif(fieldArglist==None):                                           # This is not a function because no argList so just code as expression.
            if not varTypeIsJavaValueType(convertedType):
                fieldValueText = " = " + xlator['codeExpr'](fieldValue[0], xlator)[0]
            else: fieldValueText = " = " + xlator['codeExpr'](fieldValue[0], xlator)[0]
            print "                         No argList:", fieldType, fieldName, fieldValueText
        ################################################################
        else:
            fieldValueText = " = "+ str(fieldValue)                         # This handles other cases of RHS code gen.
            print "                         Other: ", fieldType, fieldName
        ################################################################
        ##CALCULATE LHS + RHS                                           ###CALCULATE LHS + RHS###
        ################################################################
        #registerType(objectName, fieldName, convertedType, "")             # If its a constant.
        if(fieldOwner=='const'):                                                # structCode is the whole field definition
            structCode += indent + convertedType + ' ' + fieldName + fieldValueText +';\n';
            print "                             Const : ", convertedType + fieldName
        ###################################################################CODE FUNCTIONS###
        elif(fieldArglist==None):                                           # If its not a function nor a constant.
            if (fieldName == "static_Global" or fieldName == "static_gui_tk"):  # TODO: make static_Global so it is not hard coded
                structCode += indent + "public static " + convertedType + ' ' + fieldName + fieldValueText +';\n';
            else:
                structCode += indent + "public " + convertedType + ' ' + fieldName + fieldValueText +';\n';
            print "                             Not Func or Const: ", convertedType, fieldName
        else:                                                           ### CODE FUNCTIONS
            if(fieldType=='none'):                                          # Arglist exists so this is a function.
                convertedType=''                                            # No field type.
            else:
                convertedType+=''                                           # Has field type.
                argList=field['typeSpec']['argList']                    ####### Generate function header for both declarations and definitions.
                if len(argList)==0:                                             # No arguments
                    argListText=''
                elif argList[0]=='<%':                                          # Verbatim.
                    argListText=argList[1][0]
                else:                                                           # Print out argList.
                    argListText=""
                    count=0
                    for arg in argList:
                        if(count>0): argListText+=", "
                        count+=1
                        argTypeSpec =arg['typeSpec']
                        argFieldName=arg['fieldName']
                        argListText+= xlator['convertType'](objects, argTypeSpec, xlator) + ' ' + argFieldName
                        localArgsAllocated.append([argFieldName, argTypeSpec])  # localArgsAllocated is a global variable that keeps track of nested function arguments and local vars.
                #print "FUNCTION:",convertedType, fieldName, '(', argListText, ') '
                if(fieldType[0] != '<%'):                                       # not verbatim field type
                    pass #registerType(objectName, fieldName, convertedType, typeDefName)
                else: typeDefName=convertedType                                 # grabbing typeDefName if not verbatim
                LangFormOfObjName = progSpec.flattenObjectName(objectName)
            #structCode += indent + "public " + typeDefName +' ' + fieldName +"("+argListText+")\n";
            objPrefix=LangFormOfObjName
            ############################################################
            #### GLOBAL main()                                          #### GLOBAL main()
            ############################################################
            if(objectName=='GLOBAL' and fieldName=='main'):
                print "                             GLOBAL main(): public void ", fieldName
                structCode += indent + "public static void " + fieldName +" (String[] args)\n";
                #localArgsAllocated.append(['args', {'owner':'me', 'fieldType':'String', 'arraySpec':None,'argList':None}])
            ############################################################
            #### GLOBAL miscFuncs()                                     #### GLOBAL miscFuncs()
            ############################################################
            elif(objectName=='GLOBAL') :
                structCode += indent + "public " + typeDefName + ' ' + fieldName +"("+argListText+")\n"
                print "                             GLOBAL miscFuncs(): public ", typeDefName + " " + fieldName
            ############################################################
            #### OTHER FUNCTIONS                                        #### OTHER FUNCTIONS
            ############################################################
            else:
                #funcDefCode += typeDefName +' ' + objPrefix + fieldName +"("+argListText+")"
                structCode += indent + "public " + typeDefName +' ' + fieldName +"("+argListText+")\n";
                print "                             otherFuncs (): public " + typeDefName + " " + fieldName
            ############################################################
            #### VERBATIM FUNC BODY
            ############################################################
            verbatimText=field['value'][1]
            if (verbatimText!=''):                                      # This function body is 'verbatim'.
                if(verbatimText[0]=='!'): # This is a code conversion pattern. Don't write a function decl or body.
                    structCode=""
                    funcText=""
                    funcDefCode=""
                    globalFuncs=""
                else:
                    funcText=verbatimText
            # No verbatim found so generate function text from action sequence
            elif field['value'][0]!='':
                print "                                 Action Func Body: "+ fieldName
                structCode += indent + processActionSeq(field['value'][0], '    ', xlator)+"\n"
            else:
                print "ERROR: In processOtherFields: no funcText or funcTextVerbatim found"
                exit(1)
            ################################################################
            #### funcDefCode
            ################################################################
            structCode += funcText+"\n\n"

        #funcDefCodeAcc += ""
        structCodeAcc  += structCode #+ funcDefCode
        #globalFuncsAcc += globalFuncs


    #constructCode=generate_constructor(objects, objectName, tags, indent)
    #constructCode=""
    #structCodeAcc+=constructCode
    return [structCodeAcc, funcDefCodeAcc]

def generateAllObjectsButMain(objects, tags, xlator):
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

            # The next lines skip defining classes that will already be defined by a library
            ObjectDef = objects[0][objectName]
            ctxTag  =progSpec.searchATagStore(ObjectDef['tags'], 'ctxTag')
            implMode=progSpec.searchATagStore(ObjectDef['tags'], 'implMode')
            if(ctxTag): ctxTag=ctxTag[0]
            if(implMode): implMode=implMode[0]
            if(ctxTag!=None and not (implMode=="declare" or implMode[:7]=="inherit")):  # "useLibrary"
                #print "SKIPPING:", objectName, ctxTag, implMode
                continue

            #print "OBJNAME", objectName
            #charIdx=objectName.find('#')
            #if charIdx>=0:  # there is '#' denoting a library specific version ctxTag.
                #thisCtxTag = objectName[charIdx+1:]
                #if thisCtxTag in progSpec.libsToUse:
                    #print "TAG",thisCtxTag
                    #objectName = objectName[:charIdx-1]
                #else:print "!TAG", thisCtxTag; continue

            print "                [" + objectName+"]"
            currentObjName=objectName
            [needsFlagsVar, strOut]=processFlagAndModeFields(objects, objectName, tags, xlator)
            constsEnums+=strOut
            if(needsFlagsVar):
                progSpec.addField(objects[0], objectName, progSpec.packField(False, 'me', "uint64", None, 'flags', None, None))
            if(objects[0][objectName]['stateType'] == 'struct'): # and ('enumList' not in objects[0][objectName]['typeSpec'])):
                LangFormOfObjName = progSpec.flattenObjectName(objectName)
                parentClass=''
                if(implMode and implMode[:7]=="inherit"):
                    parentClass=implMode[8:]
                    parentClass=' extends '+parentClass+' '
                #forwardDecls+="struct " + LangFormOfObjName + ";  \t// Forward declaration\n"
                [structCode, funcCode]=processOtherStructFields(objects, objectName, tags, '    ', xlator)
                structCodeAcc += "\nclass "+LangFormOfObjName+parentClass+"{\n" + structCode + '};\n'
                funcCodeAcc+=funcCode
        currentObjName=''
    return [constsEnums, forwardDecls, structCodeAcc, funcCodeAcc]

def makeTagText(tags, tagName):
    tagVal=progSpec.fetchTagValue(tags, tagName)
    if tagVal==None: return "Tag '"+tagName+"' is not set in the dog file."
    return tagVal

libInterfacesText=''
def makeFileHeader(tags, xlator):
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
    header += xlator['addSpecialCode']()
    return header

def integrateLibraries(tags, libID, xlator):
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
        headerStr += xlator['includeDirective'](libHdr)
        #print "Added header", libHdr
    #print 'BUILD STR', buildStr_libs
    return headerStr

def connectLibraries(objects, tags, libsToUse, xlator):
    print "\n            Choosing Libaries to link..."
    headerStr = ''
    for lib in libsToUse:
        headerStr += integrateLibraries(tags, lib, xlator)
    return headerStr

def createInit_DeInit(objects, tags):
    initCode=''; deinitCode=''

    if 'initCode'   in tags[0]: initCode  = tags[0]['initCode']
    if 'deinitCode' in tags[0]: deinitCode= tags[0]['deinitCode']
    if 'initCode'   in tags[1]: initCode  += tags[1]['initCode']
    if 'deinitCode' in tags[1]: deinitCode += tags[1]['deinitCode']

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

def generate(objects, tags, libsToUse, xlator):
    #print "\nGenerating code...\n"
    global objectsRef
    global buildStr_libs
    global libInterfacesText
    buildStr_libs = xlator['BuildStrPrefix']
    objectsRef=objects
    buildStr_libs +=  progSpec.fetchTagValue(tags, "FileName")
    createInit_DeInit(objects, tags)
    libInterfacesText=connectLibraries(objects, tags, libsToUse, xlator)
    header = makeFileHeader(tags, xlator)
    [constsEnums, forwardDecls, structCodeAcc, funcCodeAcc]=generateAllObjectsButMain(objects, tags, xlator)
    topBottomStrings = xlator['processMain'](objects, tags, xlator)
    typeDefCode = xlator['produceTypeDefs'](typeDefMap, xlator)
    if('cpp' in progSpec.codeHeader): codeHeader=progSpec.codeHeader['cpp']
    else: codeHeader=''
    outputStr = header + constsEnums + forwardDecls + codeHeader + typeDefCode + structCodeAcc + topBottomStrings[0] + funcCodeAcc + topBottomStrings[1]
    return outputStr
