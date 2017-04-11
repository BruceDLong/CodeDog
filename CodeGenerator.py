# CodeGenerator.py
import progSpec
import re
import datetime
import codeDogParser
from progSpec import cdlog, cdErr, logLvl, dePythonStr
from progSpec import structsNeedingModification

buildStr_libs=''
globalFuncDeclAcc=''
globalFuncDefnAcc=''
ForwardDeclsForGlobalFuncs=''


def appendGlobalFuncAcc(decl, defn):
    global globalFuncDefnAcc
    global globalFuncDeclAcc
    if decl!="":
        globalFuncDeclAcc+=decl+';      \t// Forward function declaration\n'
        globalFuncDefnAcc+=decl+defn

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
           # print "ITEMNAME:", itemName
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
            #print "Found", itemName
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
   # print "WARNING: Could not find field",itemName ,"in", objName
    return 0 # Field not found in model

StaticMemberVars={} # Used to find parent-class of const and enums

def staticVarNamePrefix(staticVarName, xlator):
    if staticVarName in StaticMemberVars:
        return progSpec.baseStructName(StaticMemberVars[staticVarName]) + xlator['ObjConnector']
    else: return ''

def fetchItemsTypeSpec(itemName, xlator):
    # return format: [{typeSpec}, 'OBJVAR']. Substitute for wrapped types.
    global currentObjName
    global StaticMemberVars
    #print "FETCHING:", itemName, currentObjName
    RefType=""
    REF=CheckBuiltinItems(itemName)
    if (REF):
        RefType="BUILTIN"
        return REF
    else:
        REF=CheckFunctionsLocalVarArgList(itemName)
        if (REF):
            RefType="LOCAL" # could also return FUNCARG
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
                    if(itemName in StaticMemberVars):
                        parentClassName = staticVarNamePrefix(itemName, xlator)
                        crntBaseName = progSpec.baseStructName(currentObjName)
                        #print"STATIC:",itemName, parentClassName, crntBaseName
                        if(parentClassName[: len(crntBaseName)] != crntBaseName):
                            return [None, "STATIC:"+parentClassName]
                    cdlog(logLvl(), "Variable {} could not be found.".format(itemName))
                    return [None, "LIB"]
    return [REF['typeSpec'], RefType]
    # Example: [{typeSpec}, 'OBJVAR']

###### End of type tracking code


fieldNamesAlreadyUsed={}
def codeFlagAndModeFields(objects, objectName, tags, xlator):
    cdlog(5, "                    Coding flags and modes for: {}".format(objectName))
    global fieldNamesAlreadyUsed
    global StaticMemberVars
    flagsVarNeeded = False
    bitCursor=0
    structEnums=""
    ObjectDef = objects[0][objectName]
    for field in ObjectDef['fields']:
        fieldType=field['typeSpec']['fieldType'];
        fieldName=field['fieldName'];
        if fieldType=='flag' or fieldType=='mode':
            flagsVarNeeded=True
            if fieldName in fieldNamesAlreadyUsed: continue
            else:fieldNamesAlreadyUsed[fieldName]=objectName
            if fieldType=='flag':
                cdlog(6, "flag: {}".format(fieldName))
                structEnums += "    " + xlator['getConstIntFieldStr'](fieldName, hex(1<<bitCursor)) +" \t// Flag: "+fieldName+"\n"
                StaticMemberVars[fieldName]  =objectName
                bitCursor += 1;
            elif fieldType=='mode':
                cdlog(6, "mode: {}[]".format(fieldName))
                #print field
                structEnums += "\n// For Mode "+fieldName+"\n"
                # calculate field and bit position
                enumSize= len(field['typeSpec']['enumList'])
                numEnumBits=bitsNeeded(enumSize)
                #field[3]=enumSize;
                #field[4]=numEnumBits;
                enumMask=((1 << numEnumBits) - 1) << bitCursor

                offsetVarName = fieldName+"Offset"
                maskVarName   = fieldName+"Mask"
                structEnums += "    "+xlator['getConstIntFieldStr'](offsetVarName, hex(bitCursor))
                structEnums += "    "+xlator['getConstIntFieldStr'](maskVarName,   hex(enumMask)) + "\n"

                # enum
                enumList=field['typeSpec']['enumList']
                structEnums += xlator['getEnumStr'](fieldName, enumList)

                # Record the utility vars' parent-classes
                StaticMemberVars[offsetVarName]=objectName
                StaticMemberVars[maskVarName]  =objectName
                for eItem in enumList:
                    StaticMemberVars[eItem]=objectName

                bitCursor=bitCursor+numEnumBits;
    if structEnums!="": structEnums="\n\n// *** Code for manipulating "+objectName+' flags and modes ***\n'+structEnums
    return [flagsVarNeeded, structEnums]

typeDefMap={}
ObjectsFieldTypeMap={}
def registerType(objName, fieldName, typeOfField, typeDefTag):
    ObjectsFieldTypeMap[objName+'::'+fieldName]={'rawType':typeOfField, 'typeDef':typeDefTag}
    typeDefMap[typeOfField]=typeDefTag


def codeAllocater(typeSpec, xlator):
    S=''
    owner=progSpec.getTypeSpecOwner(typeSpec)
    fType=typeSpec['fieldType']
    arraySpec=typeSpec['arraySpec']
    if isinstance(fType, basestring): varTypeStr=fType;
    else: varTypeStr=fType[0]

    [varTypeStr, innerType] = xlator['convertType'](objectsRef, typeSpec, 'alloc', xlator)
    S= xlator['getCodeAllocStr'](varTypeStr, owner);
    return S

def genIfBody(ifBody, indent, xlator):
    ifBodyText = ""
    for ifAction in ifBody:
        actionOut = codeAction(ifAction, indent + "    ", xlator)
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

def codeNameSeg(segSpec, typeSpecIn, connector, LorR_Val, xlator):
    # if TypeSpecIn has 'dummyType', this is a non-member and the first segment of the reference.
    #print "CODENAMESEG:", segSpec, "TSI:",typeSpecIn
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

    owner=progSpec.getTypeSpecOwner(typeSpecIn)


    #print "                                             CODENAMESEG:", name
    #if not isinstance(name, basestring):  print "NAME:", name, typeSpecIn
    if ('fieldType' in typeSpecIn and isinstance(typeSpecIn['fieldType'], basestring)):
        if typeSpecIn['fieldType']=="string":
            [name, typeSpecOut] = xlator['recodeStringFunctions'](name, typeSpecOut)

    if owner=='itr':
        if name=='goNext':
            typeSpecOut['codeConverter']='%0++'
        elif name=='goPrev':
            typeSpecOut['codeConverter']='--%0'
        elif name=='key':
            typeSpecOut['codeConverter']='%0->first'
        elif name=='val':
            typeSpecOut['codeConverter']='%0->second'

    elif('arraySpec' in typeSpecIn and typeSpecIn['arraySpec']):
        [containerType, idxType, owner]=xlator['getContainerType'](typeSpecIn)
        typeSpecOut={'owner':typeSpecIn['owner'], 'fieldType': typeSpecIn['fieldType']}
        #print "                                                 arraySpec:",typeSpecOut
        if(name[0]=='['):
            [S2, idxType] = xlator['codeExpr'](name[1], xlator)
            S += xlator['codeArrayIndex'](S2, containerType, LorR_Val)
            return [S, typeSpecOut, S2]
        [name, typeSpecOut, paramList, convertedIdxType]= xlator['getContainerTypeInfo'](containerType, name, idxType, typeSpecOut, paramList, objectsRef, xlator)

    elif ('dummyType' in typeSpecIn): # This is the first segment of a name
        tmp=xlator['codeSpecialFunc'](segSpec, xlator)   # Check if it's a special function like 'print'
        if(tmp!=''):
            S=tmp
            return [S, '', None]
        [typeSpecOut, SRC]=fetchItemsTypeSpec(name, xlator)
        if(SRC=="GLOBAL"): namePrefix = xlator['GlobalVarPrefix']
        if(SRC[:6]=='STATIC'): namePrefix = SRC[7:]
    else:
        fType=typeSpecIn['fieldType']

        if(name=='allocate'):
            S_alt=' = '+codeAllocater(typeSpecIn, xlator)
            typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif(name[0]=='[' and fType=='string'):
            typeSpecOut={'owner':owner, 'fieldType': fType}
            [S2, idxType] = xlator['codeExpr'](name[1], xlator)
            S += xlator['codeArrayIndex'](S2, 'string', LorR_Val)
            return [S, typeSpecOut, S2]  # Here we return S2 for use in code forms other than [idx]. e.g. f(idx)
        else:
            typeSpecOut=CheckObjectVars(fType[0], name, 1)
            if typeSpecOut!=0:
                name=typeSpecOut['fieldName']
                typeSpecOut=typeSpecOut['typeSpec']

    if typeSpecOut and 'codeConverter' in typeSpecOut:
        [convertedName, paramList]=convertNameSeg(typeSpecOut, name, paramList, xlator)
        #print"                             codeConverter:", name, "->", convertedName
        name = convertedName
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
            [CPL, paramTypeList] = codeParameterList(paramList, modelParams, xlator)
            S+= CPL
    if(typeSpecOut==None): cdlog(logLvl(), "Type for {} was not found.".format(name))
    return [S,  typeSpecOut, None]

def codeUnknownNameSeg(segSpec, xlator):
    S=''
    paramList=None
    segName=segSpec[0]
    segConnector = ''
    #print "SEGNAME:", segName
    if(len(segSpec)>1):
        segConnector = xlator['NameSegFuncConnector']
    else:
        segConnector = xlator['NameSegConnector']
    S += segConnector + segName
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
            [CPL, paramTypeList] = codeParameterList(paramList, None, xlator)
            S+= CPL
    return S;

def codeItemRef(name, LorR_Val, xlator):
    S=''
    segStr=''
    segType={'owner':'', 'dummyType':True}
    LHSParentType=''
    connector=''
    prevLen=len(S)
    segIDX=0
    AltFormat=None
    AltIDXFormat=''
    for segSpec in name:
        if(isinstance(segType, int)): cdErr("Segment '{}' in the name '{}' is not valid.".format(segSpec[0], dePythonStr(name)))
        owner=progSpec.getTypeSpecOwner(segType)
        segName=segSpec[0]
        #print "NameSeg:", segName
        if(segIDX>0):
            # Detect connector to use '.' '->', '', (*...).
            connector='.'
            if(segType): # This is where to detect type of vars not found to determine whether to use '.' or '->'
                if progSpec.typeIsPointer(segType):
                    #print "PTRTYPE:", segName, ':  ', segType
                    connector = xlator['PtrConnector']

        AltFormat=None
        if segType!=None:
            if segType and 'fieldType' in segType:
                LHSParentType=segType['fieldType'][0]
            [segStr, segType, AltIDXFormat]=codeNameSeg(segSpec, segType, connector, LorR_Val, xlator)
            if AltIDXFormat!=None:
                AltFormat=[S, AltIDXFormat]   # This is in case of an alternate index format such as Java's string.put(idx, val)
            #print "segStr: ", segStr
        else:
            segStr= codeUnknownNameSeg(segSpec, xlator)
            #print "segStr: ", segStr
        prevLen=len(S)


        # Should this be called as a global?
        callAsGlobal=segStr.find("%G")
        if(callAsGlobal >= 0):
            S=''
            prevLen=0
            segStr=segStr.replace("%G", '')
            segStr=segStr[len(connector):]
            connector=''

        # Handle case where LeftName is connected by '->' but the next segment is '[...]'. So we need '(*left)[...]'
        if connector=='->' and segStr[0]=='[':
            S='(*'+S+')'
            connector=''

        # Should this be called C style?
        thisArgIDX=segStr.find("%0")
        if(thisArgIDX >= 0):
            if connector=='->' and owner!='itr': S="*("+S+")"
            S=segStr.replace("%0", S)
            S=S[len(connector):]
        else: S+=segStr

        segIDX+=1

    # Handle cases where seg's type is flag or mode
    if segType and LorR_Val=='RVAL' and 'fieldType' in segType:
        fieldType=segType['fieldType']
        if fieldType=='flag':
            segName=segStr[len(connector):]
            prefix = staticVarNamePrefix(segName, xlator)
            S='(' + S[0:prevLen] + connector + 'flags & ' + prefix+segName + ')' # TODO: prevent 'segStr' namespace collisions by prepending object name to field constant
        elif fieldType=='mode':
            segName=segStr[len(connector):]
            prefix = staticVarNamePrefix(segName+"Mask", xlator)
            S="((" + S[0:prevLen] + connector +  "flags&"+prefix+segName+"Mask)"+">>"+prefix+segName+"Offset)"
    return [S, segType, LHSParentType, AltFormat]


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


def codeParameterList(paramList, modelParams, xlator):
    S=''
    #if(modelParams):  print "CODE-PARAMS:", len(paramList),"=",len(modelParams)
    count = 0
    paramTypeList=[]
    for P in paramList:
        if(count>0): S+=', '
        [S2, argType]=xlator['codeExpr'](P[0], xlator)
        paramTypeList.append(argType)
    #    print "    PARAM",P, '<',argType,'>'
    #    print "    MODEL", modelParams[count], '\n'
        if modelParams and (len(modelParams)>count) and ('typeSpec' in modelParams[count]):
            [leftMod, rightMod]=xlator['chooseVirtualRValOwner'](modelParams[count]['typeSpec'], argType)
            S += leftMod+S2+rightMod
        else: S += S2
        count+=1
    S='(' + S + ')'
    return [S, paramTypeList]


def codeFuncCall(funcCallSpec, xlator):
    S=''
   # if(len(funcCallSpec)==1):
       # tmpStr=xlator['codeSpecialFunc'](funcCallSpec)
       # if(tmpStr != ''):
       #     return tmpStr
    [codeStr, typeSpec, LHSParentType, AltIDXFormat]=codeItemRef(funcCallSpec, 'RVAL', xlator)
    S+=codeStr
    return S

def startPointOfNamesLastSegment(name):
    p=len(name)-1
    while(p>0):
        if name[p]=='>' or name[p]=='.':
            break
        p-=1
    return p

def encodeConditionalStatement(action, indent, xlator):
    #print "                                         encodeConditionalStatement: "
    [S2, conditionType] =  xlator['codeExpr'](action['ifCondition'][0], xlator)
    ifCondition = S2
    ifBodyText = genIfBody(action['ifBody'], indent, xlator)
    actionText =  indent + "if (" + ifCondition + ") " + "{\n" + ifBodyText + indent + "}\n"
    elseBodyText = ""
    elseBody = action['elseBody']
    if (elseBody):
        if (elseBody[0]=='if'):
            elseAction = elseBody[1]
            elseText = encodeConditionalStatement(elseAction[0], indent, xlator)
            actionText += indent + "else " + elseText.lstrip()
        elif (elseBody[0]=='action'):
            elseAction = elseBody[1]['actionList']
            elseText = codeActionSeq(False, elseAction, indent, xlator)
            actionText += indent + "else " + elseText.lstrip()
        else:  print"Unrecognized item after else"; exit(2);
    return actionText

def codeAction(action, indent, xlator):
    #make a string and return it
    global localVarsAllocated
    actionText = ""
    typeOfAction = action['typeOfAction']

    if (typeOfAction =='newVar'):
        fieldDef=action['fieldDef']
        typeSpec= fieldDef['typeSpec']
        varName = fieldDef['fieldName']
        cdlog(5, "New Var: {}: ".format(varName))
        [fieldType, innerType] = xlator['convertType'](objectsRef, typeSpec, 'var', xlator)
        cdlog(5, "Action newVar: {}".format(varName))
        varDeclareStr = xlator['codeNewVarStr'](typeSpec, varName, fieldDef, fieldType, innerType, xlator)
        actionText = indent + varDeclareStr + ";\n"
        localVarsAllocated.append([varName, typeSpec])  # Tracking local vars for scope
    elif (typeOfAction =='assign'):
        #print "PREASSIGN:", action['LHS']
        # Note: In Java, string A[x]=B must be coded like: A.put(B,x)

        [codeStr, typeSpec, LHSParentType, AltIDXFormat] = codeItemRef(action['LHS'], 'LVAL', xlator)
        assignTag = action['assignTag']
        LHS = codeStr
        cdlog(5, "Assignment: ".format(LHS))
        [S2, rhsType]=xlator['codeExpr'](action['RHS'][0], xlator)
        #print "LHS / RHS:", LHS, ' / ', S2, typeSpec, rhsType
        [LHS_leftMod, LHS_rightMod,  RHS_leftMod, RHS_rightMod]=xlator['determinePtrConfigForAssignments'](typeSpec, rhsType, assignTag)
        LHS = LHS_leftMod+LHS+LHS_rightMod
        RHS = RHS_leftMod+S2+RHS_rightMod
        cdlog(5, "Assignment: {} = {}".format(LHS, RHS))
        if not isinstance (typeSpec, dict):
            print 'Problem: typeSpec is', typeSpec, '\n';
            LHS_FieldType='string'
        else: LHS_FieldType=typeSpec['fieldType']
        if assignTag == '':
            if LHS_FieldType=='flag':
                divPoint=startPointOfNamesLastSegment(LHS)
                LHS_Left=LHS[0:divPoint+1] # The '+1' makes this get the connector too. e.g. '.' or '->'
                bitMask =LHS[divPoint+1:]
                prefix = staticVarNamePrefix(bitMask, xlator)
                setBits = xlator['codeSetBits'](LHS_Left, LHS_FieldType, prefix, bitMask, RHS, rhsType)
                actionText=indent + setBits
                #print "INFO:", LHS, divPoint, "'"+LHS_Left+"'" 'bm:', bitMask,'RHS:', RHS;
            elif LHS_FieldType=='mode':
                divPoint=startPointOfNamesLastSegment(LHS)
                if (divPoint == 0):
                    LHS_Left=""
                    bitMask =LHS
                else:
                    LHS_Left=LHS[0:divPoint+1]
                    bitMask =LHS[divPoint+1:]
                prefix = staticVarNamePrefix(bitMask+"Mask", xlator)
                setBits = xlator['codeSetBits'](LHS_Left, LHS_FieldType, prefix, bitMask, RHS, rhsType)
                actionText=indent + setBits
            else:
                if AltIDXFormat!=None:
                    # Handle special forms of assignment such as LVal(idx, RVal)
                    actionText = xlator['checkIfSpecialAssignmentFormIsNeeded'](AltIDXFormat, RHS, rhsType)
                if actionText=="":
                    # Handle the normal assignment case
                    actionText = indent + LHS + " = " + RHS + ";\n"

        else:
            if(assignTag=='deep'):
                actionText = indent + LHS + " = " + RHS + ";\n"
            else:
                actionText = indent + "opAssign" + assignTag + '(' + LHS + ", " + RHS + ");\n"
    elif (typeOfAction =='swap'):
        LHS =  ".".join(action['LHS'])
        RHS =  ".".join(action['LHS'])
        print "                                     swap: ", LHS, RHS
        actionText = indent + "swap (" + LHS + ", " + RHS + ");\n"
    elif (typeOfAction =='conditional'):
        cdlog(5, "If-statement...")
        [S2, conditionType] =  xlator['codeExpr'](action['ifCondition'][0], xlator)
        [S2, conditionType] =  xlator['adjustIfConditional'](S2, conditionType)
        cdlog(5, "If-statement: Condition is ".format(S2))
        ifCondition = S2


        ifBodyText = genIfBody(action['ifBody'], indent, xlator)
        actionText =  indent + "if (" + ifCondition + ") " + "{\n" + ifBodyText + indent + "}\n"
        elseBodyText = ""
        elseBody = action['elseBody']
        if (elseBody):
            if (elseBody[0]=='if'):
                elseAction = elseBody[1][0]
                elseText = encodeConditionalStatement(elseAction, indent, xlator)
                actionText += indent + "else " + elseText.lstrip()
            elif (elseBody[0]=='action'):
                elseAction = elseBody[1]['actionList']
                elseText = codeActionSeq(False, elseAction, indent, xlator)
                actionText += indent + "else " + elseText.lstrip()
            else:  print"Unrecognized item after else"; exit(2);
    elif (typeOfAction =='repetition'):
        repBody = action['repBody']
        repName = action['repName']
        cdlog(5, "Repetition stmt: loop var is:".format(repName))
        traversalMode = action['traversalMode']
        rangeSpec = action['rangeSpec']
        whileSpec = action['whileSpec']
        keyRange  = action['keyRange']
        fileSpec  = False #action['fileSpec']
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
            [whileExpr, whereConditionType] = xlator['codeExpr'](whileSpec[2], xlator)
            [whileExpr, whereConditionType] =  xlator['adjustIfConditional'](whileExpr, whereConditionType)
            actionText += indent + "while(" + whileExpr + "){\n"
        elif(fileSpec):
            [filenameExpr, filenameType] = xlator['codeExpr'](fileSpec[2], xlator)
            if filenameType!='string':
                print "Filename must be a string.\n"; exit(1);
            print "File iteration not implemeted yet.\n"
            exit(2)
        elif(keyRange):
            [repContainer, containerType] = xlator['codeExpr'](keyRange[0][0], xlator)
            [StartKey, StartType] = xlator['codeExpr'](keyRange[2][0], xlator)
            [EndKey,   EndType] = xlator['codeExpr'](keyRange[4][0], xlator)

            [datastructID, keyFieldType, ContainerOwner]=xlator['getContainerType'](containerType)
            wrappedTypeSpec = progSpec.isWrappedType(objectsRef, containerType['fieldType'][0])
            if(wrappedTypeSpec != None):containerType=wrappedTypeSpec

            [actionTextOut, loopCounterName] = xlator['iterateRangeContainerStr'](objectsRef,localVarsAllocated, StartKey, EndKey, containerType,repName,repContainer,datastructID,keyFieldType,indent,xlator)
            actionText += actionTextOut

        else: # interate over a container
            [repContainer, containerType] = xlator['codeExpr'](action['repList'][0], xlator)
            [datastructID, keyFieldType, ContainerOwner]=xlator['getContainerType'](containerType)

            #print "ITERATE OVER", action['repList'][0], datastructID, containerType
            wrappedTypeSpec = progSpec.isWrappedType(objectsRef, containerType['fieldType'][0])
            if(wrappedTypeSpec != None):containerType=wrappedTypeSpec

            [actionTextOut, loopCounterName] = xlator['iterateContainerStr'](objectsRef,localVarsAllocated,containerType,repName,repContainer,datastructID,keyFieldType, ContainerOwner,indent,xlator)
            actionText += actionTextOut

        if action['whereExpr']:
            [whereExpr, whereConditionType] = xlator['codeExpr'](action['whereExpr'], xlator)
            actionText += indent + "    " + 'if (!' + whereExpr + ') continue;\n'
        if action['untilExpr']:
            [untilExpr, untilConditionType] = xlator['codeExpr'](action['untilExpr'], xlator)
            actionText += indent + '    ' + 'if (' + untilExpr + ') break;\n'
        repBodyText = ''
        for repAction in repBody:
            actionOut = codeAction(repAction, indent + "    ", xlator)
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
        cdlog(5, "Function Call: {}()".format(str(calledFunc[0][0])))
        actionText = indent + codeFuncCall(calledFunc, xlator) + ';\n'
    elif (typeOfAction == 'switchStmt'):
        #print "ACTIONKEY:", str(action['switchKey'])+"'"
        [switchKeyExpr, switchKeyType] = xlator['codeExpr'](action['switchKey'][0], xlator)
        actionText += indent+"switch("+ switchKeyExpr + "){\n"
        for sCases in action['switchCases']:
            for sCase in sCases[0]:
                [caseKeyValue, caseKeyType] = xlator['codeExpr'](sCase[0], xlator)
                actionText += indent+"    case "+caseKeyValue+": "
                caseAction = sCases[1]
                actionText += codeActionSeq(False, caseAction, indent+'    ', xlator)
                actionText += indent+"    break;\n"
        defaultCase=action['defaultCase']
        if defaultCase and len(defaultCase)>0:
            actionText+=indent+"default: "
            actionText += codeActionSeq(False, defaultCase, indent, xlator)
        actionText += indent + "}\n"
    elif (typeOfAction =='actionSeq'):
        cdlog(5, "Action Sequence")
        actionListIn = action['actionList']
        actionListText = ''
        for action in actionListIn:
            actionListOut = codeAction(action, indent + "    ", xlator)
            actionListText += actionListOut
        #print "actionSeq: ", actionListText
        actionText += indent + "{\n" + actionListText + indent + '}\n'
    else:
        print "error in codeAction: ", action
        exit(2)
 #   print "actionText", actionText
    return actionText

def codeActionSeq(isMain, actSeq, indent, xlator):
    global localVarsAllocated
    localVarsAllocated.append(["STOP",''])
    actSeqText = ""

    if (isMain):
        actSeqText += xlator['codeActTextMain'](actSeq, indent, xlator)
    else:
        actSeqText = "{\n"
        for action in actSeq:
            actionText = codeAction(action, indent + '    ', xlator)
            actSeqText += actionText
        actSeqText += indent + "}"

    actSeqText += "\n"
    localVarRecord=['','']
    while(localVarRecord[0] != 'STOP'):
        localVarRecord=localVarsAllocated.pop()
    return actSeqText

def codeConstructor(objects, ClassName, tags, xlator):
    baseType = progSpec.isWrappedType(objects, ClassName)
    if(baseType!=None): return ''
    if not ClassName in objects[0]: return ''
    cdlog(4, "Generating Constructor for: {}".format(ClassName))
    ClassName = progSpec.flattenObjectName(ClassName)
    constructorInit=""
    constructorArgs=""
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
        [convertedType, innerType] = xlator['convertType'](objects, typeSpec, 'var', xlator)
        fieldName=field['fieldName']

        cdlog(4, "                        Constructing: {} {} {} {}".format(ClassName, fieldName, fieldType, convertedType))
        if not isinstance(fieldType, basestring): fieldType=fieldType[0]
        if(fieldOwner != 'me'):
            if(fieldOwner != 'my'):
                constructorArgs += convertedType+" _"+fieldName+"=0,"
                constructorInit += xlator['codeConstructorInit'](fieldName, count, xlator)
                count += 1
        elif (isinstance(fieldType, basestring)):
            if(fieldType[0:3]=="int" or fieldType[0:4]=="uint"):
                constructorArgs += xlator['codeArgText'](" _"+fieldName, convertedType, xlator) +"=0,"
                constructorInit += xlator['codeConstructorInit'](fieldName, count, xlator)
                count += 1
            elif(fieldType=="string"):
                constructorArgs += xlator['codeArgText'](" _"+fieldName, convertedType, xlator) +'="",'
                constructorInit += xlator['codeConstructorInit'](fieldName, count, xlator)
                count += 1
    if(count>0):
        constructorArgs=constructorArgs[0:-1]
        constructCode = "    "+xlator['codeConstructionHeader'](ClassName, constructorArgs, constructorInit, xlator)
    else: constructCode=''
    return constructCode

def codeStructFields(objects, objectName, tags, indent, xlator):
    global ForwardDeclsForGlobalFuncs
    cdlog(3, "Coding fields for {}...".format(objectName))
    ####################################################################
    global localArgsAllocated
    funcBodyIndent   = xlator['funcBodyIndent']
    funcsDefInClass  = xlator['funcsDefInClass']
    MakeConstructors = xlator['MakeConstructors']
    globalFuncsAcc=''
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
        fieldOwner=progSpec.getTypeSpecOwner(typeSpec)
        fieldName =field['fieldName']
        cdlog(4, "FieldName: {}".format(fieldName))
        fieldValue=field['value']
        fieldArglist = typeSpec['argList']
        [intermediateType, innerType] = xlator['convertType'](objects, typeSpec, 'var', xlator)
        convertedType = progSpec.flattenObjectName(intermediateType)
        typeDefName = convertedType # progSpec.createTypedefName(fieldType)
        if(fieldName == "main"):
            isMain = True
        else:
            isMain = False

        ## ASSIGNMENTS###############################################
        if fieldName=='opAssign':
            fieldName='operator='
            #print "                         opAssign: ", fieldType, fieldName

        ##CALCULATE RHS###############################################
        if(fieldValue == None):
            fieldValueText=xlator['codeVarFieldRHS_Str'](fieldValue, convertedType, fieldOwner, field['paramList'], xlator)
           # print "                            RHS none: ", fieldValueText
        elif(fieldOwner=='const'):
            if isinstance(fieldValue, basestring):
                fieldValueText = ' = "'+ fieldValue + '"'
            else:
                fieldValueText = " = "+ xlator['codeExpr'](fieldValue, xlator)[0]
           # print "                            RHS const: ", fieldValueText
        elif(fieldArglist==None):
            fieldValueText = " = " + xlator['codeExpr'](fieldValue[0], xlator)[0]
           # print "                            RHS var: ", fieldValueText
        else:
            fieldValueText = " = "+ str(fieldValue)
            #print "                            RHS func or array"

        ##CALCULATE LHS + RHS ###########################################
        #registerType(objectName, fieldName, convertedType, "")
        if(fieldOwner=='const'):
            structCode += indent + convertedType + ' ' + fieldName + fieldValueText +';\n';

        ############ CODE VARIABLE##########################################################
        elif(fieldArglist==None):
            structCode += xlator['codeVarField_Str'](convertedType, fieldName, fieldValueText, objectName, tags, indent)

        ###### ArgList exists so this is a FUNCTION###########
        else:
            #### ARGLIST
            argList=field['typeSpec']['argList']
            if len(argList)==0:
                argListText='' #'void'
            elif argList[0]=='<%':                                          # Verbatim.arguments
                argListText=argList[1][0]
            else:
                argListText=""
                count=0
                for arg in argList:
                    if(count>0): argListText+=", "
                    count+=1
                    argTypeSpec =arg['typeSpec']
                    argFieldName=arg['fieldName']
                    [argType, innerType] = xlator['convertType'](objects, argTypeSpec, 'arg', xlator)
                    argListText+= xlator['codeArgText'](argFieldName, argType, xlator)
                    localArgsAllocated.append([argFieldName, argTypeSpec])  # localArgsAllocated is a global variable that keeps track of nested function arguments and local vars.
               # print "                            argListText: (", argListText, ")"

            #### RETURN TYPE
            if(fieldType[0] != '<%'):
                pass #registerType(objectName, fieldName, convertedType, typeDefName)
            else: typeDefName=convertedType
            if(typeDefName=='none'): typeDefName=''

            #### FUNC HEADER: for both decl and defn.
            [structCode, funcDefCode, globalFuncs]=xlator['codeFuncHeaderStr'](objectName, fieldName, typeDefName, argListText, localArgsAllocated, indent)

            #### FUNC BODY
            verbatimText=field['value'][1]
            if (verbatimText!=''):                                      # This function body is 'verbatim'.
                if(verbatimText[0]=='!'): # This is a code conversion pattern. Don't write a function decl or body.
                    structCode=""
                    funcText=""
                    funcDefCode=""
                    globalFuncs=""
                else:
                    funcText=verbatimText
               # print "                         Verbatim Func Body"
            elif field['value'][0]!='':
                funcText =  codeActionSeq(isMain, field['value'][0], funcBodyIndent, xlator)
                if globalFuncs!='': ForwardDeclsForGlobalFuncs += globalFuncs+";       \t\t // Forward Decl\n"
               # print "                         Func Body from Action Sequence"
            else:
                print "ERROR: In codeFields: no funcText or funcTextVerbatim found"
                exit(1)

            if(funcsDefInClass=='True' ):
                structCode += funcText

            elif(objectName=='GLOBAL'):
                if(fieldName=='main'):
                    funcDefCode += funcText
                else:
                    globalFuncs += funcText
            else: funcDefCode += funcText


        ## Accumulate field code
        structCodeAcc  += structCode
        funcDefCodeAcc += funcDefCode
        globalFuncsAcc += globalFuncs

    if MakeConstructors=='True' and (objectName!='GLOBAL'):
        constructCode=codeConstructor(objects, objectName, tags, xlator)
        structCodeAcc+=constructCode
    return [structCodeAcc, funcDefCodeAcc, globalFuncsAcc]

def codeAllNonGlobalStructs(objects, tags, xlator):
    global currentObjName
    global structsNeedingModification
    constsEnums=""
    forwardDeclsAcc="\n";
    structCodeAcc='\n////////////////////////////////////////////\n//   O b j e c t   D e c l a r a t i o n s\n\n';
    funcCodeAcc="\n//////////////////////////////////////\n//   M e m b e r   F u n c t i o n s\n\n"
    needsFlagsVar=False;
    constFieldAccs={}
    fileSpecs=[]
    dependancies=[]
    for objectName in objects[1]:
        if progSpec.isWrappedType(objects, objectName)!=None: continue
        if(objectName[0] != '!'):

            # The next lines skip defining classes that will already be defined by a library
            ObjectDef = objects[0][objectName]
            ctxTag  =progSpec.searchATagStore(ObjectDef['tags'], 'ctxTag')
            implMode=progSpec.searchATagStore(ObjectDef['tags'], 'implMode')
            classAttrs=progSpec.searchATagStore(ObjectDef['tags'], 'attrs')
            if(ctxTag): ctxTag=ctxTag[0]
            if(implMode):
                implMode=implMode[0]
                #print "implMode:", implMode
            if(classAttrs): classAttrs=classAttrs[0]+' '
            else: classAttrs=''
            if(ctxTag!=None and not (implMode=="declare" or implMode[:7]=="inherit" or implMode[:9]=="implement")):  # "useLibrary"
                cdlog(2, "SKIPPING: {} {} {}".format(objectName, ctxTag, implMode))
                continue

            #print "OBJNAME", objectName
            #charIdx=objectName.find('#')
            #if charIdx>=0:  # there is '#' denoting a library specific version ctxTag.
                #thisCtxTag = objectName[charIdx+1:]
                #if thisCtxTag in progSpec.libsToUse:
                    #print "TAG",thisCtxTag
                    #objectName = objectName[:charIdx-1]
                #else:print "!TAG", thisCtxTag; continue

            cdlog(2, "CODING: " + objectName)
            if (objectName in structsNeedingModification):
                cdlog(3, "structsNeedingModification: {}".format(str(structsNeedingModification[objectName])))
                [classToModify, modificationMode, interfaceImplemented, markItem]=structsNeedingModification[objectName]
                implMode='implement:' + interfaceImplemented

            currentObjName=objectName
            [needsFlagsVar, strOut]=codeFlagAndModeFields(objects, objectName, tags, xlator)
            objectNameBase=progSpec.baseStructName(objectName)
            if not objectNameBase in constFieldAccs: constFieldAccs[objectNameBase]=""
            constFieldAccs[objectNameBase]+=strOut

            if(needsFlagsVar):
                progSpec.addField(objects[0], objectName, progSpec.packField(False, 'me', "uint64", None, 'flags', None, None, None))
            if(((xlator['doesLangHaveGlobals']=='False') or objectName != 'GLOBAL') and objects[0][objectName]['stateType'] == 'struct'): # and ('enumList' not in objects[0][objectName]['typeSpec'])):
                LangFormOfObjName = progSpec.flattenObjectName(objectName)
                parentClass=''
                if(implMode and implMode[:7]=="inherit"):
                    parentClass=implMode[8:]
                elif(implMode and implMode[:9]=="implement"):
                    parentClass='!' + implMode[10:]
                [structCode, funcCode, globalCode]=codeStructFields(objects, objectName, tags, '    ', xlator)
                structCode+= constFieldAccs[objectNameBase]
                [structCodeOut, forwardDeclsOut] = xlator['codeStructText'](classAttrs, parentClass, LangFormOfObjName, structCode)
                fileSpecs.append([constsEnums, forwardDeclsOut, structCodeOut, funcCode, objectName, dependancies])
        currentObjName=''
    return fileSpecs

def codeStructureCommands(objects, tags, xlator):
    global ModifierCommands
    global funcsCalled
    global MarkItems
    for command in progSpec.ModifierCommands:
        if (command[3] == 'addImplements'):
            calledFuncName = command[1]
            if calledFuncName in progSpec.funcsCalled:
                calledFuncInstances = progSpec.funcsCalled[calledFuncName]
                #print '     addImplements:'
                print '          calledFuncName:', calledFuncName
                for funcCalledParams in calledFuncInstances:
                    #print '\n funcCalledParams:',funcCalledParams
                    paramList = funcCalledParams[0]
                    commandArgs = command[2]
                    if paramList != None:
                        count=1
                        for P in paramList:
                            oldTextTag='%'+str(count)
                            [newText, argType]=xlator['codeExpr'](P[0], xlator)
                            commandArgs=commandArgs.replace(oldTextTag, newText)
                            count+=1
                        #print commandArgs
                    firstColonPos=commandArgs.find(':')
                    secondColonPos=commandArgs.find(':', firstColonPos+1)
                    interfaceImplemented=commandArgs[:firstColonPos]
                    classToModify=commandArgs[secondColonPos+1:]
                    structsNeedingModification[classToModify] = [classToModify, "implement", interfaceImplemented, progSpec.MarkItems]
                   # print "          impl: ", structsNeedingModification[classToModify]

def makeTagText(tags, tagName):
    tagVal=progSpec.fetchTagValue(tags, tagName)
    if tagVal==None: return "Tag '"+tagName+"' is not set in the dog file."
    return tagVal

libInterfacesText=''
def makeFileHeader(tags, filename, xlator):
    global buildStr_libs
    global libInterfacesText
    filename = makeTagText(tags, 'FileName')

    header  = "// " + makeTagText(tags, 'Title') + " "+ makeTagText(tags, 'Version') + '\n'
    header += "// " + makeTagText(tags, 'CopyrightMesg') +'\n'
    header += "// This file: " + filename +'\n'
    header += "// Dog File: " + makeTagText(tags, 'dogFilename') +'\n'
    header += "// Authors of CodeDog file: " + makeTagText(tags, 'Authors') +'\n'
    header += "// Build time: " + datetime.datetime.today().strftime('%c') + '\n'
    header += "\n// " + makeTagText(tags, 'Description') +'\n'
    header += "\n/*  " + makeTagText(tags, 'LicenseText') +'\n*/\n'
    header += "\n// Build Options Used: " +'Not Implemented'+'\n'
    header += "\n// Build Command: " +buildStr_libs+'\n\n'
    header += libInterfacesText
    header += xlator['addSpecialCode'](filename)
    return header

def integrateLibraries(tags, libID, xlator):
    cdlog(3, 'Integrating {}'.format(libID))
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
    cdlog(1, "Attaching chosen libraries...")
    headerStr = ''
    for lib in libsToUse:
        headerStr += integrateLibraries(tags, lib, xlator)
    return headerStr

def addGLOBALSpecialCode(objects, tags, xlator):
    cdlog(1, "Attaching Language Specific Code...")
    xlator['addGLOBALSpecialCode'](objects, tags, xlator)
    initCode=''; deinitCode=''

    if 'initCode'   in tags[0]: initCode  = tags[0]['initCode']
    if 'deinitCode' in tags[0]: deinitCode= tags[0]['deinitCode']
    if 'initCode'   in tags[1]: initCode  += tags[1]['initCode']
    if 'deinitCode' in tags[1]: deinitCode += tags[1]['deinitCode']

    GLOBAL_CODE="""
struct GLOBAL{
    me void: initialize(me string: prgArgs) <- {
        %s
    }

    me void: deinitialize() <- {
        %s
    }
    """ % (initCode, deinitCode)
    GLOBAL_CODE+=r"""
    me void: logPrint(me string: logMode, me string: s) <- {
            print(logMode , s, '\n')
            if (logMode == "FATAL ERROR: "){exit(-1)}
    }

    /- LOGGING INTERFACE:
    me void: logMesg(me string: s) <- <%!logPrint("MESSAGE: ", %1)%>
    me void: logInfo(me string: s) <- <%!logPrint("", %1)%>
    me void: logCriticalIssue(me string: s) <- <%!logPrint("CRITICAL ERROR: ", %1)%>
    me void: logFatalError(me string: s) <- <%!logPrint("FATAL ERROR: ", %1)%>
    me void: logWarning(me string: s) <- <%!logPrint("WARNING: ", %1)%>
    me void: logDebug(me string: s) <- <%!logPrint("DEBUG: ", %1)%>
    /-me void: assert(condition) <- {}
    }"""
    codeDogParser.AddToObjectFromText(objects[0], objects[1], GLOBAL_CODE )

def generateBuildSpecificMainFunctionality(objects, tags, xlator):
    xlator['generateMainFunctionality'](objects, tags)

def pieceTogetherTheSourceFiles(tags, oneFileTF, fileSpecs, headerInfo, MainTopBottom, xlator):
    global ForwardDeclsForGlobalFuncs
    fileSpecsOut=[]
    fileExtension=xlator['fileExtension']
    if oneFileTF: # Generate a single source file
        filename = makeTagText(tags, 'FileName')+fileExtension
        header = makeFileHeader(tags, filename, xlator)
        [constsEnums, forwardDecls, structCodeAcc, funcCodeAcc] = ['', '', '', '']
        for fileSpec in fileSpecs:
            constsEnums   += fileSpec[0]
            forwardDecls  += fileSpec[1]
            structCodeAcc += fileSpec[2]
            funcCodeAcc   += fileSpec[3]

        forwardDecls += globalFuncDeclAcc
        funcCodeAcc  += globalFuncDefnAcc

        outputStr = header + constsEnums + forwardDecls + structCodeAcc + ForwardDeclsForGlobalFuncs + MainTopBottom[0] + funcCodeAcc + MainTopBottom[1]
        filename = progSpec.fetchTagValue(tags, "FileName")
        fileSpecsOut.append([filename, outputStr])

    else: # Generate a file for each class
        for fileSpec in fileSpecs:
            [constsEnums, forwardDecls, structCodeAcc, funcCodeAcc, objectName, dependancies]  = fileSpec
            filename = objectName+fileExtension
            header = makeFileHeader(tags, filename, xlator)
            outputStr = header + constsEnums + forwardDecls + structCodeAcc + funcCodeAcc
            fileSpecsOut.append([filename, outputStr])

    return fileSpecsOut

def clearBuild():
    global localVarsAllocated
    global localArgsAllocated
    global currentObjName
    global libInterfacesText
    global fieldNamesAlreadyUsed
    global StaticMemberVars
    global globalFuncDeclAcc
    global globalFuncDefnAcc
    global ForwardDeclsForGlobalFuncs

    localVarsAllocated = []
    localArgsAllocated = []
    fieldNamesAlreadyUsed={}
    currentObjName=''
    libInterfacesText=''
    StaticMemberVars={}
    globalFuncDeclAcc=''
    globalFuncDefnAcc=''
    ForwardDeclsForGlobalFuncs='\n\n// Forward Declarations of global functions\n'

def generate(objects, tags, libsToUse, xlator):
    clearBuild()
    global objectsRef
    global buildStr_libs
    global libInterfacesText

    buildStr_libs = xlator['BuildStrPrefix']
    objectsRef=objects
    buildStr_libs +=  progSpec.fetchTagValue(tags, "FileName")
    addGLOBALSpecialCode(objects, tags, xlator)
    libInterfacesText=connectLibraries(objects, tags, libsToUse, xlator)

    cdlog(1, "Generating Top-level (e.g., main())...")
    if progSpec.fetchTagValue(tags, 'ProgramOrLibrary') == "program": generateBuildSpecificMainFunctionality(objects, tags, xlator)

    codeStructureCommands(objects, tags, xlator)
    cdlog(1, "Generating Classes...")
    fileSpecs=codeAllNonGlobalStructs(objects, tags, xlator)
    topBottomStrings = xlator['codeMain'](objects, tags, xlator)
    typeDefCode = xlator['produceTypeDefs'](typeDefMap, xlator)

    fileSpecStrings = pieceTogetherTheSourceFiles(tags, True, fileSpecs, [], topBottomStrings, xlator)
   # print "\n\n##########################################################\n"
    return fileSpecStrings
