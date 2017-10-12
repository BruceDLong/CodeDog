# CodeGenerator.py
import re
import datetime
import platform
import codeDogParser
import libraryMngr
import progSpec
from progSpec import cdlog, cdErr, logLvl, dePythonStr
from progSpec import structsNeedingModification


import pattern_GUI_Toolkit
import pattern_ManageCmdLine
import pattern_DispData
import pattern_GenSymbols
import pattern_MakeMenu

import stringStructs


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

globalClassStore=[]
globalTagStore=None
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

def CheckObjectVars(objName, itemName):
    #print "Searching",objName,"for", itemName
    ObjectDef =  progSpec.findSpecOf(globalClassStore[0], objName, "struct")
    if ObjectDef==None:
        #print "WARNING: Model def not found."
        return 0
    retVal=None
    wrappedTypeSpec = progSpec.isWrappedType(globalClassStore, objName)
    if(wrappedTypeSpec != None):
        actualFieldType=wrappedTypeSpec['fieldType']
        if not isinstance(actualFieldType, basestring):
            #print "'actualFieldType", wrappedTypeSpec, actualFieldType, objName
            retVal = CheckObjectVars(actualFieldType[0], itemName)
            if retVal!=0:
                retVal['typeSpec']['owner']=wrappedTypeSpec['owner']
                return retVal
        else:
            if 'fieldName' in wrappedTypeSpec and wrappedTypeSpec['fieldName']==itemName:
                #print "WRAPPED FIELDNAME:", itemName
                return wrappedTypeSpec
            else: return 0

    callableStructFields=[]
    progSpec.populateCallableStructFields(callableStructFields, globalClassStore, objName)
    for field in callableStructFields:
        fieldName=field['fieldName']
        if fieldName==itemName:
            #print "Found", itemName
            return field

    #print "WARNING: Could not find field",itemName ,"in", objName
    return 0 # Field not found in model

StaticMemberVars={} # Used to find parent-class of const and enums

def staticVarNamePrefix(staticVarName, xlator):
    global StaticMemberVars
    if staticVarName in StaticMemberVars:
        crntBaseName = progSpec.baseStructName(currentObjName)
        refedClass=progSpec.baseStructName(StaticMemberVars[staticVarName])
        if(crntBaseName != refedClass):
            return refedClass + xlator['ObjConnector']
    return ''

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
            REF=CheckObjectVars(currentObjName, itemName)
            if (REF):
                RefType="OBJVAR"
                if(currentObjName=='GLOBAL'): RefType="GLOBAL"
            else:
                REF=CheckObjectVars("GLOBAL", itemName)
                if (REF):
                    RefType="GLOBAL"
                else:
                    if(itemName in StaticMemberVars):
                        parentClassName = staticVarNamePrefix(itemName, xlator)
                        if(parentClassName != ''):
                            return [{'owner':'me', 'fieldType':"string", 'arraySpec':{'note':'not generated from parse', 'owner':'me', 'datastructID':'list'}}, "STATIC:"+parentClassName]  # 'string' is probably not always correct.
                        else: return [{'owner':'me', 'fieldType':"string", 'arraySpec':{'note':'not generated from parse', 'owner':'me', 'datastructID':'list'}}, "CONST"]
                    if itemName=='NULL': return [{'owner':'their', 'fieldType':"pointer", 'arraySpec':None}, "CONST"]
                    cdlog(logLvl(), "Variable {} could not be found.".format(itemName))
                    return [None, "LIB"]      # TODO: Return correct type
    return [REF['typeSpec'], RefType]
    # Example: [{typeSpec}, 'OBJVAR']

###### End of type tracking code

modeStateNames={}

def getModeStateNames():
    global modeStateNames
    return modeStateNames

def codeFlagAndModeFields(classes, className, tags, xlator):
    cdlog(5, "                    Coding flags and modes for: {}".format(className))
    global StaticMemberVars
    global modeStateNames
    flagsVarNeeded = False
    bitCursor=0
    structEnums=""
    CodeDogAddendums = ""
    ObjectDef = classes[0][className]
    for field in progSpec.generateListOfFieldsToImplement(classes, className):
        fieldType=field['typeSpec']['fieldType'];
        fieldName=field['fieldName'];
        if fieldType=='flag' or fieldType=='mode':
            flagsVarNeeded=True

            fieldName = progSpec.flattenObjectName(fieldName)
            if fieldType=='flag':
                cdlog(6, "flag: {}".format(fieldName))
                structEnums += "    " + xlator['getConstIntFieldStr'](fieldName, hex(1<<bitCursor)) +" \t// Flag: "+fieldName+"\n"
                StaticMemberVars[fieldName]  =className
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
                CodeDogAddendums += "    me string[we list]: "+fieldName+'Strings' + ' <- ' + '["'+('", "'.join(enumList))+'"]\n'

                # Record the utility vars' parent-classes
                StaticMemberVars[offsetVarName]=className
                StaticMemberVars[maskVarName]  =className
                StaticMemberVars[fieldName+'Strings']  = className
                modeStateNames[fieldName+'Strings']=className
                for eItem in enumList:
                    StaticMemberVars[eItem]=className

                bitCursor=bitCursor+numEnumBits;
    if structEnums!="": structEnums="\n\n// *** Code for manipulating "+className+' flags and modes ***\n'+structEnums
    return [flagsVarNeeded, structEnums, CodeDogAddendums]

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

    [varTypeStr, innerType] = xlator['convertType'](globalClassStore, typeSpec, 'alloc', xlator)
    S= xlator['getCodeAllocStr'](varTypeStr, owner);
    return S

def convertNameSeg(typeSpecOut, name, paramList, objsRefed, xlator):
    newName = typeSpecOut['codeConverter']
    if paramList != None:
        count=1
        for P in paramList:
            oldTextTag='%'+str(count)
            [S2, argType]=xlator['codeExpr'](P[0], objsRefed, xlator)
            if(isinstance(newName, basestring)):
                newName=newName.replace(oldTextTag, S2)
            else: exit(2)
            count+=1
        paramList=None
    return [newName, paramList]

################################  C o d e   E x p r e s s i o n s

def codeNameSeg(segSpec, typeSpecIn, connector, LorR_Val, previousSegName, previousTypeSpec, objsRefed, xlator):
    # if TypeSpecIn has 'dummyType', this is a non-member and the first segment of the reference.
    #print "CODENAMESEG:", segSpec, "TSI:",typeSpecIn
    S=''
    S_alt=''
    SRC=''
    namePrefix=''  # For static_Global vars
    typeSpecOut={'owner':'', 'fieldType':'void'}
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
        codeCvrtText = xlator['codeIteratorOperation'](name)
        if codeCvrtText!='':
            typeSpecOut['codeConverter'] = codeCvrtText

    elif('arraySpec' in typeSpecIn and typeSpecIn['arraySpec']):
        [containerType, idxType, owner]=xlator['getContainerType'](typeSpecIn)
        typeSpecOut={'owner':typeSpecIn['owner'], 'fieldType': typeSpecIn['fieldType']}
        #print "                                                 arraySpec:",typeSpecOut
        if(name[0]=='['):
            [S2, idxType] = xlator['codeExpr'](name[1], objsRefed, xlator)
            S += xlator['codeArrayIndex'](S2, containerType, LorR_Val, previousSegName)
            return [S, typeSpecOut, S2,'']
        [name, typeSpecOut, paramList, convertedIdxType]= xlator['getContainerTypeInfo'](globalClassStore, containerType, name, idxType, typeSpecOut, paramList, xlator)

    elif ('dummyType' in typeSpecIn): # This is the first segment of a name
        tmp=xlator['codeSpecialFunc'](segSpec, objsRefed, xlator)   # Check if it's a special function like 'print'
        if(tmp!=''):
            S=tmp
            return [S, '', None, '']
        [typeSpecOut, SRC]=fetchItemsTypeSpec(name, xlator)
        if(SRC=="GLOBAL"): namePrefix = xlator['GlobalVarPrefix']
        if(SRC[:6]=='STATIC'): namePrefix = SRC[7:]
    else:
        fType=progSpec.fieldTypeKeyword(typeSpecIn['fieldType'])
        if(name=='allocate'):
            S_alt=' = '+codeAllocater(typeSpecIn, xlator)
            typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif(name[0]=='[' and fType=='string'):
            typeSpecOut={'owner':owner, 'fieldType': fType}
            [S2, idxType] = xlator['codeExpr'](name[1], objsRefed, xlator)
            S += xlator['codeArrayIndex'](S2, 'string', LorR_Val, previousSegName)
            return [S, typeSpecOut, S2, '']  # Here we return S2 for use in code forms other than [idx]. e.g. f(idx)
        else:
            if fType!='string':
                typeSpecOut=CheckObjectVars(fType, name)
                if typeSpecOut!=0:
                    name=typeSpecOut['fieldName']
                    typeSpecOut=typeSpecOut['typeSpec']
                   #print "TESTTYPES:", fType, progSpec.fieldTypeKeyword(typeSpecOut['fieldType'])
                else:
                    print "WARNING: TYPESPEC IS ", typeSpecOut, "for ", fType + '::' + name
                    #print "typeSpecIn: ", typeSpecIn

    if typeSpecOut and 'codeConverter' in typeSpecOut:
        [convertedName, paramList]=convertNameSeg(typeSpecOut, name, paramList, objsRefed, xlator)
        #print"                             codeConverter:", name, "->", convertedName
        name = convertedName
        callAsGlobal=name.find("%G")
        if(callAsGlobal >= 0): namePrefix=''

    if S_alt=='': S+=namePrefix+connector+name
    else: S += S_alt

    # Add parameters if this is a function call
    if(paramList != None):
        modelParams=None
        if typeSpecOut and ('argList' in typeSpecOut): modelParams=typeSpecOut['argList']
        [CPL, paramTypeList] = codeParameterList(name, paramList, modelParams, objsRefed, xlator)
        S+= CPL
    if(typeSpecOut==None): cdlog(logLvl(), "Type for {} was not found.".format(name))

    if ("<MODENAME>" in S):
        S=S.replace("<MODENAME>", ".get(")
        S=S.replace("<MODENAMEend>", ")")
    return [S,  typeSpecOut, None, SRC]

def codeUnknownNameSeg(segSpec, objsRefed, xlator):
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
            [CPL, paramTypeList] = codeParameterList("", paramList, None, objsRefed, xlator)
            S+= CPL
    print "UNKNOWN NAME SEGMENT:", S
    return S;

def codeItemRef(name, LorR_Val, objsRefed, xlator):
    global currentObjName
    previousSegName = ""
    previousTypeSpec = ""
    S=''
    segStr=''
    if(LorR_Val=='RVAL'): canonicalName ='>'
    else: canonicalName = '<'
    segType={'owner':'', 'dummyType':True}

    connector=''
    prevLen=len(S)
    segIDX=0
    AltFormat=None
    AltIDXFormat=''
    for segSpec in name:
        LHSParentType='#'
        if(isinstance(segType, int)):
            cdErr("Segment '{}' in the name '{}' is not valid.".format(segSpec[0], dePythonStr(name)))
        owner=progSpec.getTypeSpecOwner(segType)
        segName=segSpec[0]
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
                LHSParentType = progSpec.fieldTypeKeyword(segType['fieldType'])
            else: LHSParentType = progSpec.fieldTypeKeyword(currentObjName)   # Landed here because this is the first segment
            [segStr, segType, AltIDXFormat, nameSource]=codeNameSeg(segSpec, segType, connector, LorR_Val, previousSegName, previousTypeSpec, objsRefed, xlator)
            if nameSource!='': canonicalName+=nameSource
            if AltIDXFormat!=None:
                AltFormat=[S, previousTypeSpec, AltIDXFormat]   # This is in case of an alternate index format such as Java's string.put(idx, val)
            #print "segStr: ", segStr
        else:
            segStr= codeUnknownNameSeg(segSpec, objsRefed, xlator)
            #print "segStr: ", segStr
        prevLen=len(S)

        # Record canonical name for record keeping
        if not isinstance(segName, basestring):
            if segName[0]=='[': canonicalName+='[...]'
            else: cdErr('Odd segment name:'+str(segName))
        else: canonicalName+='.'+segName

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
        if(segStr.find("%0") >= 0):
            if connector=='->' and owner!='itr': S="*("+S+")"
            S=segStr.replace("%0", S)
            S=S[len(connector):]
        else: S+=segStr


        # Language specific dereferencing of ->[...], etc.
        S = xlator['LanguageSpecificDecorations'](S, segType, owner)

        objsRefed[canonicalName]=0
        previousSegName = segName
        previousTypeSpec = segType
        segIDX+=1

    # Handle cases where seg's type is flag or mode
    if segType and LorR_Val=='RVAL' and 'fieldType' in segType:
        fieldType=segType['fieldType']
        if fieldType=='flag':
            segName=segStr[len(connector):]
            prefix = staticVarNamePrefix(segName, xlator)
            bitfieldMask=xlator['applyTypecast']('uint64', prefix+segName)
            S='(' + S[0:prevLen] + connector + 'flags & ' + bitfieldMask + ')' # TODO: prevent 'segStr' namespace collisions by prepending object name to field constant
        elif fieldType=='mode':
            segName=segStr[len(connector):]
            prefix = staticVarNamePrefix(segName+"Mask", xlator)
            bitfieldMask  =xlator['applyTypecast']('uint64', prefix+segName+"Mask")
            bitfieldOffset=xlator['applyTypecast']('uint64', prefix+segName+"Offset")
            S="(" + S[0:prevLen] + connector +  "flags&"+bitfieldMask+")"+">>"+bitfieldOffset
            S=xlator['applyTypecast']('int', S)

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


def codeParameterList(name, paramList, modelParams, objsRefed, xlator):
    S=''
    #if(modelParams):  print "CODE-PARAMS:", len(paramList),"=",len(modelParams)
    count = 0
    paramTypeList=[]
    totalParams= len(paramList)
    totalDefaultValue=0
    if (modelParams==[]):
        modelParams = None
    if (modelParams!=None):
        for P in modelParams:
            if P['value']:
                totalDefaultValue=len(modelParams)

    if(totalDefaultValue>0):
        count=0
        for MP in modelParams:
            if not(count<totalParams) and MP['value']:
                paramList.insert(count, MP['value'])
            #print "    paramList[", count, "]: ", paramList[count]
            count+=1

    if(len(paramList)==0 ):
        if name != 'return' and name!='break' and name!='continue' and name!='characters.count':
            S+="()"
    else:
        count = 0
        for P in paramList:
            if(count>0): S+=', '
            [S2, argType]=xlator['codeExpr'](P[0], objsRefed, xlator)
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


def codeFuncCall(funcCallSpec, objsRefed, xlator):
    S=''
   # if(len(funcCallSpec)==1):
       # tmpStr=xlator['codeSpecialFunc'](funcCallSpec)
       # if(tmpStr != ''):
       #     return tmpStr
    [codeStr, typeSpec, LHSParentType, AltIDXFormat]=codeItemRef(funcCallSpec, 'RVAL', objsRefed, xlator)
    S+=codeStr
    return S

def startPointOfNamesLastSegment(name):
    p=len(name)-1
    while(p>0):
        if name[p]=='>' or name[p]=='.':
            return p
        p-=1
    return -1


def genIfBody(ifBody, indent, objsRefed, xlator):
    ifBodyText = ""
    for ifAction in ifBody:
        actionOut = codeAction(ifAction, indent + "    ", objsRefed, xlator)
        #print "If action: ", actionOut
        ifBodyText += actionOut
    return ifBodyText

def encodeConditionalStatement(action, indent, objsRefed, xlator):
    #print "                                         encodeConditionalStatement: "
    [S2, conditionType] =  xlator['codeExpr'](action['ifCondition'][0], objsRefed, xlator)
    ifCondition = S2
    ifBodyText = genIfBody(action['ifBody'], indent, objsRefed, xlator)
    actionText =  indent + "if (" + ifCondition + ") " + "{\n" + ifBodyText + indent + "}\n"
    elseBodyText = ""
    elseBody = action['elseBody']
    if (elseBody):
        if (elseBody[0]=='if'):
            elseAction = elseBody[1]
            elseText = encodeConditionalStatement(elseAction[0], indent, objsRefed, xlator)
            actionText += indent + "else " + elseText.lstrip()
        elif (elseBody[0]=='action'):
            elseAction = elseBody[1]['actionList']
            elseText = codeActionSeq(elseAction, indent, objsRefed, xlator)
            actionText += indent + "else " + elseText.lstrip()
        else:  print"Unrecognized item after else"; exit(2);
    return actionText

def codeAction(action, indent, objsRefed, xlator):
    #make a string and return it
    global localVarsAllocated
    actionText = ""
    action['sideEffects']=[]
    typeOfAction = action['typeOfAction']

    if (typeOfAction =='newVar'):
        fieldDef=action['fieldDef']
        typeSpec= fieldDef['typeSpec']
        varName = fieldDef['fieldName']
        cdlog(5, "Action newVar: {}".format(varName))
        varDeclareStr = xlator['codeNewVarStr'](globalClassStore, typeSpec, varName, fieldDef, indent, objsRefed, xlator)
        actionText = indent + varDeclareStr + ";\n"
        localVarsAllocated.append([varName, typeSpec])  # Tracking local vars for scope
    elif (typeOfAction =='assign'):
        cdlog(5, "PREASSIGN:" + str(action['LHS']))
        # Note: In Java, string A[x]=B must be coded like: A.put(B,x)
        cdlog(5, "Pre-assignment... ")
        [codeStr, typeSpec, LHSParentType, AltIDXFormat] = codeItemRef(action['LHS'], 'LVAL', objsRefed, xlator)
        assignTag = action['assignTag']
        LHS = codeStr
        cdlog(5, "Assignment: {}".format(LHS))
        [S2, rhsType]=xlator['codeExpr'](action['RHS'][0], objsRefed, xlator)
        #print "LHS / RHS:", LHS, ' / ', S2, typeSpec, rhsType
        [LHS_leftMod, LHS_rightMod,  RHS_leftMod, RHS_rightMod]=xlator['determinePtrConfigForAssignments'](typeSpec, rhsType, assignTag)
        LHS = LHS_leftMod+LHS+LHS_rightMod
        RHS = RHS_leftMod+S2+RHS_rightMod
        cdlog(5, "Assignment: {} = {}".format(LHS, RHS))
        if not isinstance (typeSpec, dict):
            #TODO: make test case
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
                    if actionText != '': actionText = indent+actionText
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
        [S2, conditionType] =  xlator['codeExpr'](action['ifCondition'][0], objsRefed, xlator)
        [S2, conditionType] =  xlator['adjustConditional'](S2, conditionType)
        cdlog(5, "If-statement: Condition is ".format(S2))
        ifCondition = S2


        ifBodyText = genIfBody(action['ifBody'], indent, objsRefed, xlator)
        actionText =  indent + "if (" + ifCondition + ") " + "{\n" + ifBodyText + indent + "}\n"
        elseBodyText = ""
        elseBody = action['elseBody']
        if (elseBody):
            if (elseBody[0]=='if'):
                elseAction = elseBody[1][0]
                elseText = encodeConditionalStatement(elseAction, indent, objsRefed, xlator)
                actionText += indent + "else " + elseText.lstrip()
            elif (elseBody[0]=='action'):
                elseAction = elseBody[1]['actionList']
                elseText = codeActionSeq(elseAction, indent, objsRefed, xlator)
                actionText += indent + "else " + elseText.lstrip()
            else:  print"Unrecognized item after else"; exit(2);
    elif (typeOfAction =='repetition'):
        repBody = action['repBody']
        repName = action['repName']
        cdlog(5, "Repetition stmt: loop var is:'{}'".format(repName))
        traversalMode = action['traversalMode']
        rangeSpec = action['rangeSpec']
        whileSpec = action['whileSpec']
        keyRange  = action['keyRange']
        fileSpec  = False #action['fileSpec']
        ctrType=xlator['typeForCounterInt']
        # TODO: add cases for traversing trees and graphs in various orders or ways.
        loopCounterName=''
        if(rangeSpec): # iterate over range
            [S_low, lowValType] = xlator['codeExpr'](rangeSpec[2][0], objsRefed, xlator)
            [S_hi,   hiValType] = xlator['codeExpr'](rangeSpec[4][0], objsRefed, xlator)
            #print "RANGE:", S_low, "..", S_hi
            ctrlVarsTypeSpec = lowValType
            actionText += xlator['codeRangeSpec'](traversalMode, ctrType, repName, S_low, S_hi, indent, xlator)
            localVarsAllocated.append([repName, ctrlVarsTypeSpec])  # Tracking local vars for scope
        elif(whileSpec):
            [whileExpr, whereConditionType] = xlator['codeExpr'](whileSpec[2], objsRefed, xlator)
            [whileExpr, whereConditionType] =  xlator['adjustConditional'](whileExpr, whereConditionType)
            actionText += indent + "while(" + whileExpr + "){\n"
            loopCounterName=repName
        elif(fileSpec):
            [filenameExpr, filenameType] = xlator['codeExpr'](fileSpec[2], objsRefed, xlator)
            if filenameType!='string':
                print "Filename must be a string.\n"; exit(1);
            print "File iteration not implemeted yet.\n"
            exit(2)
        elif(keyRange):
            [repContainer, containerType] = xlator['codeExpr'](keyRange[0][0], objsRefed, xlator)
            [StartKey, StartType] = xlator['codeExpr'](keyRange[2][0], objsRefed, xlator)
            [EndKey,   EndType] = xlator['codeExpr'](keyRange[4][0], objsRefed, xlator)

            [datastructID, keyFieldType, ContainerOwner]=xlator['getContainerType'](containerType)
            wrappedTypeSpec = progSpec.isWrappedType(globalClassStore, containerType['fieldType'][0])
            if(wrappedTypeSpec != None):containerType=wrappedTypeSpec

            [actionTextOut, loopCounterName] = xlator['iterateRangeContainerStr'](globalClassStore,localVarsAllocated, StartKey, EndKey, containerType,repName,repContainer,datastructID,keyFieldType,indent,xlator)
            actionText += actionTextOut

        else: # interate over a container
            [repContainer, containerType] = xlator['codeExpr'](action['repList'][0], objsRefed, xlator)
            if containerType['arraySpec']==None: cdErr("'"+repContainer+"' is not a container so cannot be iterated over.")
            [datastructID, keyFieldType, ContainerOwner]=xlator['getContainerType'](containerType)

            #print "ITERATE OVER", action['repList'][0], datastructID, containerType
            wrappedTypeSpec = progSpec.isWrappedType(globalClassStore, containerType['fieldType'][0])
            if(wrappedTypeSpec != None):containerType=wrappedTypeSpec
            if(traversalMode=='Forward' or traversalMode==None):
                isBackward=False
            elif(traversalMode=='Backward'):
                isBackward=True
            [actionTextOut, loopCounterName] = xlator['iterateContainerStr'](globalClassStore,localVarsAllocated,containerType,repName,repContainer,datastructID,keyFieldType, ContainerOwner, isBackward,indent,xlator)
            actionText += actionTextOut

        if action['whereExpr']:
            [whereExpr, whereConditionType] = xlator['codeExpr'](action['whereExpr'], objsRefed, xlator)
            actionText += indent + "    " + 'if (!' + whereExpr + ') continue;\n'
        if action['untilExpr']:
            [untilExpr, untilConditionType] = xlator['codeExpr'](action['untilExpr'], objsRefed, xlator)
            actionText += indent + '    ' + 'if (' + untilExpr + ') break;\n'
        repBodyText = ''
        for repAction in repBody:
            actionOut = codeAction(repAction, indent + "    ", objsRefed, xlator)
            repBodyText += actionOut
        if loopCounterName!='':
            actionText=indent + ctrType+" " + loopCounterName + "=0;\n" + actionText
            repBodyText += indent + "    " + xlator['codeIncrement'](loopCounterName) + ";\n"
        actionText += repBodyText + indent + '}\n'
    elif (typeOfAction =='funcCall'):
        calledFunc = action['calledFunc']
        if calledFunc[0][0] == 'if' or calledFunc=='withEach' or calledFunc=='until' or calledFunc=='where':
            print "\nERROR: It is not allowed to name a function", calledFunc[0][0]
            exit(2)
        cdlog(5, "Function Call: {}()".format(str(calledFunc[0][0])))
        actionText = indent + codeFuncCall(calledFunc, objsRefed, xlator) + ';\n'
    elif (typeOfAction == 'switchStmt'):
        cdlog(5, "Switch statement: switch({})".format(str(action['switchKey'])))
        [switchKeyExpr, switchKeyType] = xlator['codeExpr'](action['switchKey'][0], objsRefed, xlator)
        actionText += indent+"switch("+ switchKeyExpr + "){\n"
        blockPrefix = xlator['blockPrefix']
        for sCases in action['switchCases']:
            for sCase in sCases[0]:
                [caseKeyValue, caseKeyType] = xlator['codeExpr'](sCase[0], objsRefed, xlator)
                actionText += indent+"    case "+caseKeyValue+": "
                caseAction = sCases[1]
                actionText += blockPrefix + codeActionSeq(caseAction, indent+'    ', objsRefed, xlator)
                actionText += xlator['codeSwitchBreak'](caseAction, indent, xlator)
        defaultCase=action['defaultCase']
        if defaultCase and len(defaultCase)>0:
            actionText+=indent+"default: "
            actionText += blockPrefix + codeActionSeq(defaultCase, indent, objsRefed, xlator)
        else: actionText+=indent+"default: break;\n"
        actionText += indent + "}\n"
    elif (typeOfAction =='actionSeq'):
        cdlog(5, "Action Sequence")
        actionListIn = action['actionList']
        actionListText = ''
        for action in actionListIn:
            actionListOut = codeAction(action, indent + "    ", objsRefed, xlator)
            actionListText += actionListOut
        #print "actionSeq: ", actionListText
        blockPrefix = xlator['blockPrefix']
        actionText += indent + blockPrefix + "{\n" + actionListText + indent + '}\n'
    else:
        print "error in codeAction: ", action
        exit(2)
 #   print "actionText", actionText
    return actionText

def codeActionSeq(actSeq, indent, objsRefed, xlator):
    global localVarsAllocated
    localVarsAllocated.append(["STOP",''])
    actSeqText=''
    actSeqText += '{\n'
    for action in actSeq:
        actionText = codeAction(action, indent + '    ', objsRefed, xlator)
        actSeqText += actionText
    actSeqText += '}\n'
    localVarRecord=['','']
    while(localVarRecord[0] != 'STOP'):
        localVarRecord=localVarsAllocated.pop()
    return actSeqText

def codeConstructor(classes, ClassName, tags, xlator):
    baseType = progSpec.isWrappedType(classes, ClassName)
    if(baseType!=None): return ''
    if not ClassName in classes[0]: return ''
    cdlog(4, "Generating Constructor for: {}".format(ClassName))
    ObjectDef = classes[0][ClassName]
    flatClassName = progSpec.flattenObjectName(ClassName)
    constructorInit=""
    constructorArgs=""
    copyConstructorArgs=""
    count=0
    for field in progSpec.generateListOfFieldsToImplement(classes, ClassName):
        typeSpec =field['typeSpec']
        fieldType=typeSpec['fieldType']
        if(fieldType=='flag' or fieldType=='mode'): continue
        if(typeSpec['argList'] or typeSpec['argList']!=None): continue
        if(typeSpec['arraySpec'] or typeSpec['arraySpec']!=None): continue
        fieldOwner=typeSpec['owner']
        if(fieldOwner=='const' or fieldOwner == 'we'): continue
        [convertedType, innerType] = xlator['convertType'](classes, typeSpec, 'var', xlator)
        fieldName=field['fieldName']

        cdlog(4, "                        Constructing: {} {} {} {}".format(ClassName, fieldName, fieldType, convertedType))
        if not isinstance(fieldType, basestring): fieldType=fieldType[0]
        if(fieldOwner != 'me'):
            if(fieldOwner != 'my'):
                defaultVal = "NULL"
                constructorArgs += xlator['codeConstructorArgText'](fieldName, count, convertedType, defaultVal, xlator)+ ","
                constructorInit += xlator['codeConstructorInit'](fieldName, count, defaultVal, xlator)
                count += 1
        elif (isinstance(fieldType, basestring)):
            if(fieldType[0:3]=="int" or fieldType[0:4]=="uint"):
                defaultVal = "0"
                constructorArgs += xlator['codeConstructorArgText'](fieldName, count, convertedType, defaultVal, xlator)+ ","
                constructorInit += xlator['codeConstructorInit'](fieldName, count, defaultVal, xlator)
                count += 1
            elif(fieldType=="string"):
                defaultVal = '""'
                constructorArgs += xlator['codeConstructorArgText'](fieldName, count, convertedType, defaultVal, xlator)+ ","
                constructorInit += xlator['codeConstructorInit'](fieldName, count, defaultVal, xlator)
                count += 1
        copyConstructorArgs += xlator['codeCopyConstructor'](fieldName, convertedType, xlator)
    if(count>0):
        constructorArgs=constructorArgs[0:-1]
        constructCode = xlator['codeConstructorHeader'](flatClassName, constructorArgs, constructorInit, copyConstructorArgs, xlator)
    else: constructCode=''
    return constructCode

def codeStructFields(classes, className, tags, indent, objsRefed, xlator):
    global currentObjName
    global ForwardDeclsForGlobalFuncs
    cdlog(3, "Coding fields for {}...".format(className))
    ####################################################################
    global localArgsAllocated
    funcBodyIndent   = xlator['funcBodyIndent']
    funcsDefInClass  = xlator['funcsDefInClass']
    MakeConstructors = xlator['MakeConstructors']
    globalFuncsAcc=''
    funcDefCodeAcc=''
    structCodeAcc=""
    for field in progSpec.generateListOfFieldsToImplement(classes, className):
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
        [intermediateType, innerType] = xlator['convertType'](classes, typeSpec, 'var', xlator)
        convertedType = progSpec.flattenObjectName(intermediateType)
        typeDefName = convertedType # progSpec.createTypedefName(fieldType)

        ## ASSIGNMENTS###############################################
        if fieldName=='opAssign':
            fieldName='operator='
            #print "                         opAssign: ", fieldType, fieldName

        # CALCULATE RHS
        if(fieldValue == None):
            fieldValueText=xlator['codeVarFieldRHS_Str'](fieldName, convertedType, fieldOwner, field['paramList'], objsRefed, xlator)
           # print "                            RHS none: ", fieldValueText
        elif(fieldOwner=='const'):
            if isinstance(fieldValue, basestring):
                fieldValueText = ' = "'+ fieldValue + '"'
                #TODO:  make test case
            else:
                fieldValueText = " = "+ xlator['codeExpr'](fieldValue, objsRefed, xlator)[0]
           # print "                            RHS const: ", fieldValueText
        elif(fieldArglist==None):
            fieldValueText = " = " + xlator['codeExpr'](fieldValue[0], objsRefed, xlator)[0]
           # print "                            RHS var: ", fieldValueText
        else:
            fieldValueText = " = "+ str(fieldValue)
            #print "                            RHS func or array"

        ############ CODE MEMBER VARIABLE ##########################################################
        #registerType(className, fieldName, convertedType, "")
        if(fieldOwner=='const'):
            structCode += xlator['codeConstField_Str'](convertedType, fieldName, fieldValueText, indent, xlator )
        elif(fieldArglist==None):
            [structCode, funcDefCode] = xlator['codeVarField_Str'](convertedType, innerType, typeSpec, fieldName, fieldValueText, className, tags, indent)

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
                    if progSpec.typeIsPointer(argTypeSpec): arg
                    [argType, innerType] = xlator['convertType'](classes, argTypeSpec, 'arg', xlator)
                    argListText+= xlator['codeArgText'](argFieldName, argType, xlator)
                    localArgsAllocated.append([argFieldName, argTypeSpec])  # localArgsAllocated is a global variable that keeps track of nested function arguments and local vars.
               # print "                            argListText: (", argListText, ")"

            #### RETURN TYPE
            if(fieldType[0] != '<%'):
                pass #registerType(className, fieldName, convertedType, typeDefName)
            else: typeDefName=convertedType
            if(typeDefName=='none'): typeDefName=''

            #### FUNC HEADER: for both decl and defn.
            inheritMode='normal'
            if currentObjName in progSpec.classHeirarchyInfo:
                classRelationData = progSpec.classHeirarchyInfo[currentObjName]
                # TODO: But it should NOT be virtual if there are no calls of the function from a pointer to the base class
                if (not 'parentClass' in classRelationData or ('parentClass' in classRelationData and classRelationData['parentClass']==None)) and 'childClasses' in classRelationData and len(classRelationData['childClasses'])>0:
                    inheritMode = 'virtual'
                if ('parentClass' in classRelationData and classRelationData['parentClass']!=None):
                    parentClassName = classRelationData['parentClass']
                    #print "OVERRIDE:", fieldName, parentClassName
                    if progSpec.fieldAlreadyDeclaredInStruct(classes[0], parentClassName, fieldName):
                        inheritMode = 'override'

            abstractFunction = not('value' in field) or field['value']==None
            if abstractFunction: inheritMode = 'pure-virtual'
            [structCode, funcDefCode, globalFuncs]=xlator['codeFuncHeaderStr'](className, fieldName, typeDefName, argListText, localArgsAllocated, inheritMode, indent)

            #### FUNC BODY
            if abstractFunction: # i.e., if no function body is given.
                cdlog(5, "Function "+className+":::"+fieldName+" has no implementation defined.")
            else:
                extraCodeForTopOfFuntion = xlator['extraCodeForTopOfFuntion'](argList)
                verbatimText=field['value'][1]
                if (verbatimText!=''):                                      # This function body is 'verbatim'.
                    if(verbatimText[0]=='!'): # This is a code conversion pattern. Don't write a function decl or body.
                        structCode=""
                        funcText=""
                        funcDefCode=""
                        globalFuncs=""
                    else:
                        funcText=verbatimText + "\n\n"
                        if globalFuncs!='': ForwardDeclsForGlobalFuncs += globalFuncs+";       \t\t // Forward Decl\n"
                   # print "                         Verbatim Func Body"
                elif field['value'][0]!='':
                    objsRefed2={}
                    funcText =  codeActionSeq(field['value'][0], funcBodyIndent, objsRefed2, xlator)
                    if extraCodeForTopOfFuntion!='':
                        funcText = '{\n' + extraCodeForTopOfFuntion + funcText[1:]
                 #   print "Called by function " + fieldName +':'
                 #   for rec in sorted(objsRefed2):
                 #       print "     ", rec
                    if globalFuncs!='': ForwardDeclsForGlobalFuncs += globalFuncs+";       \t\t // Forward Decl\n"
                   # print "                         Func Body from Action Sequence"
                else:
                    print "ERROR: In codeFields: no funcText or funcTextVerbatim found"
                    exit(1)

            if(funcsDefInClass=='True' ):
                structCode += funcText

            elif(className=='GLOBAL'):
                if(fieldName=='main'):
                    funcDefCode += funcText
                else:
                    globalFuncs += funcText
            else: funcDefCode += funcText


        ## Accumulate field code
        structCodeAcc  += structCode
        funcDefCodeAcc += funcDefCode
        globalFuncsAcc += globalFuncs

    # NOTE: Remove this Hard Coded widget. It should apply to any abstract class.
    if MakeConstructors=='True' and (className!='GLOBAL')  and (className!='widget'):
        constructCode=codeConstructor(classes, className, tags, xlator)
        structCodeAcc+= "\n"+constructCode
    return [structCodeAcc, funcDefCodeAcc, globalFuncsAcc]

def processDependancies(classes, item, searchList, newList):
    if searchList[item][1]==0:
        searchList[item][1]=1
        className=searchList[item][0]
        depList = progSpec.getClassesDependancies(className)
        sepPos = className.rfind('::')
        if sepPos>=0: # This is a derived class and is dependant on it's parent class
            depList.append(className[:sepPos])
        for dep in depList:
            depIdx=findIDX(searchList, dep)
            processDependancies(classes, depIdx, searchList, newList)
        newList.append(className)
        searchList[item][1]=2
    elif searchList[item][1]==1:
        print "WARNING: Dependancy cycle detected including class "+searchList[item][0]

def findIDX(classList, className):
    # Returns the index in classList of className or -1
    for findIdx in range(0, len(classList)):
        if classList[findIdx][0]==className: return findIdx
    return -1

def sortClassesForDependancies(classes, classList):
    newList=[]
    searchList=[]
    for item in classList:
        searchList.append([item, 0])
    for itemIdx in range(0, len(searchList)):
        processDependancies(classes, itemIdx, searchList, newList)

    return newList

def fetchListOfStructsToImplement(classes, tags):
    global MarkedObjects
    progNameList=[]
    libNameList=[]
    for className in classes[1]:
        if progSpec.isWrappedType(classes, className)!=None: continue
        if(className[0] == '!' or className[0] == '%' or className[0] == '$'): continue   # Filter out "Do Commands", models and strings
        # The next lines skip defining classes that will already be defined by a library
        ObjectDef = progSpec.findSpecOf(classes[0], className, 'struct')
        if(ObjectDef==None): continue
        implMode=progSpec.searchATagStore(ObjectDef['tags'], 'implMode')
        if(implMode): implMode=implMode[0]
        if(implMode!=None and not (implMode=="declare" or implMode[:7]=="inherit" or implMode[:9]=="implement")):  # "useLibrary"
            cdlog(2, "SKIPPING: {} {}".format(className, implMode))
            continue
        if className in progSpec.MarkedObjects: libNameList.append(className)
        else: progNameList.append(className)
    classList=libNameList + progNameList
    classList=sortClassesForDependancies(classes, classList)
    return classList

def codeOneStruct(classes, tags, constFieldCode, className, xlator):
    global currentObjName
    global structsNeedingModification
    cdlog(2, "COMPILING: " + className)
    classRecord=None
    constsEnums=""  # this isn't used. Remove it?
    dependancies=[]
    currentObjName=className
    if((xlator['doesLangHaveGlobals']=='False') or className != 'GLOBAL'): # and ('enumList' not in classes[0][className]['typeSpec'])):
        classDef = progSpec.findSpecOf(classes[0], className, 'struct')
        classAttrs=progSpec.searchATagStore(classDef['tags'], 'attrs')
        if(classAttrs): classAttrs=classAttrs[0]+' '
        else: classAttrs=''
        classInherits=progSpec.searchATagStore(classDef, 'inherits')
        classImplements=progSpec.searchATagStore(classDef, 'implements')

        if (className in structsNeedingModification):
            cdlog(3, "structsNeedingModification: {}".format(str(structsNeedingModification[className])))
            [classToModify, modificationMode, interfaceImplemented, markItem]=structsNeedingModification[className]
            classInherits.append( interfaceImplemented)

        parentClass=''
        seperatorIdx=className.rfind('::')
        if(seperatorIdx != -1):
            parentClass=className[0:seperatorIdx]

        objsRefed={}
        [structCode, funcCode, globalCode]=codeStructFields(classes, className, tags, '    ', objsRefed, xlator)
        structCode+= constFieldCode
        LangFormOfObjName = progSpec.flattenObjectName(className)
        [structCodeOut, forwardDeclsOut] = xlator['codeStructText'](classAttrs, parentClass, classInherits, classImplements, LangFormOfObjName, structCode)
        classRecord = [constsEnums, forwardDeclsOut, structCodeOut, funcCode, className, dependancies]
    currentObjName=''
    return classRecord



def codeAllNonGlobalStructs(classes, tags, xlator):
    global currentObjName
    global structsNeedingModification
    cdlog(2, "CODING FLAGS and MODES...")
    needsFlagsVar=False;
    CodeDogAddendumsAcc=''
    constFieldAccs={}
    fileSpecs={}
    structsToImplement = fetchListOfStructsToImplement(classes, tags)

    # Set up flag and mode fields
    for className in structsToImplement:
        currentObjName=className
        CodeDogAddendumsAcc=''
        [needsFlagsVar, strOut, CodeDogAddendums]=codeFlagAndModeFields(classes, className, tags, xlator)
        objectNameBase=progSpec.flattenObjectName(className) #progSpec.baseStructName(className)
        if not objectNameBase in constFieldAccs: constFieldAccs[objectNameBase]=""
        constFieldAccs[objectNameBase]+=strOut
        CodeDogAddendumsAcc+=CodeDogAddendums
        if(needsFlagsVar):
            CodeDogAddendumsAcc += 'me uint64: flags\n'
        if CodeDogAddendumsAcc!='':
            codeDogParser.AddToObjectFromText(classes[0], classes[1], progSpec.wrapFieldListInObjectDef(className,  CodeDogAddendumsAcc ))
        currentObjName=''

    # Write the class
    for className in structsToImplement:
        classRecord = codeOneStruct(classes, tags, constFieldAccs[progSpec.flattenObjectName(className)], className, xlator)
        if classRecord != None:
            fileSpecs[className]=classRecord

    # Check for final class attributes to add. E.g., 'abstract' or 'mutating'
 #   for className in structsToImplement:
 #       specialAttributes = xlator['addSpecialClassAttributes'](classes, className))
    return fileSpecs

def codeStructureCommands(classes, tags, xlator):
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
                            [newText, argType]=xlator['codeExpr'](P[0], {}, xlator)
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

[libInitCodeAcc, libDeinitCodeAcc] = ['', '']

def integrateLibraries(tags, tagsFromLibFiles, libID, xlator):
    global libInitCodeAcc
    global libDeinitCodeAcc
    global buildStr_libs
    headerStr = ''
    cdlog(2, 'Integrating {}'.format(libID))
    # TODO: Choose static or dynamic linking based on defaults, license tags, availability, etc.

    if 'initCode'   in tagsFromLibFiles[libID]: libInitCodeAcc  += tagsFromLibFiles[libID]['initCode']
    if 'deinitCode' in tagsFromLibFiles[libID]: libDeinitCodeAcc = tagsFromLibFiles[libID]['deinitCode'] + libDeinitCodeAcc

    if 'interface' in tagsFromLibFiles[libID]:
        if 'libFiles' in tagsFromLibFiles[libID]['interface']:
            libFiles = tagsFromLibFiles[libID]['interface']['libFiles']
            for libFile in libFiles:
                buildStr_libs+=' -l'+libFile
        if 'headers' in tagsFromLibFiles[libID]['interface']:
            libHeaders = tagsFromLibFiles[libID]['interface']['headers']
            for libHdr in libHeaders:
                headerStr += xlator['includeDirective'](libHdr)
    return headerStr

def connectLibraries(classes, tags, libsToUse, xlator):
    cdlog(1, "Attaching chosen libraries...")
    headerStr = ''
    tagsFromLibFiles = libraryMngr.getTagsFromLibFiles()
    for libFilename in libsToUse:
        headerStr += integrateLibraries(tags, tagsFromLibFiles, libFilename, xlator)
        macroDefs= {}
        [tagStore, buildSpecs, FileClasses] = loadProgSpecFromDogFile(libFilename, classes[0], classes[1], tags[0], macroDefs)

    return headerStr

def addGLOBALSpecialCode(classes, tags, xlator):
    global libInitCodeAcc
    global libDeinitCodeAcc
    cdlog(1, "Attaching Language Specific Code...")
    xlator['addGLOBALSpecialCode'](classes, tags, xlator)

    initCode=''; deinitCode=''

    if 'initCode'   in tags[0]: initCode  = tags[0]['initCode']
    if 'deinitCode' in tags[0]: deinitCode= tags[0]['deinitCode']
    initCode += libInitCodeAcc
    deinitCode = libDeinitCodeAcc + deinitCode

    GLOBAL_CODE="""
struct GLOBAL{
    me void: initialize(me string: prgArgs) <- {
        %s
    }

    me void: deinitialize() <- {
        %s
    }
}""" % (initCode, deinitCode)
    codeDogParser.AddToObjectFromText(classes[0], classes[1], GLOBAL_CODE )

def generateBuildSpecificMainFunctionality(classes, tags, xlator):
    xlator['generateMainFunctionality'](classes, tags)

def pieceTogetherTheSourceFiles(classes, tags, oneFileTF, fileSpecs, headerInfo, MainTopBottom, xlator):
    global ForwardDeclsForGlobalFuncs
    fileSpecsOut=[]
    fileExtension=xlator['fileExtension']
    constsEnums=''
    forwardDecls="\n";
    structCodeAcc='\n////////////////////////////////////////////\n//   C l a s s   D e c l a r a t i o n s\n\n';
    funcCodeAcc="\n//////////////////////////////////////\n//   M e m b e r   F u n c t i o n s\n\n"
    if oneFileTF: # Generate a single source file
        filename = makeTagText(tags, 'FileName')+fileExtension
        header = makeFileHeader(tags, filename, xlator)
        structsToImplement = fetchListOfStructsToImplement(classes, tags)
        for className in structsToImplement:
            if((xlator['doesLangHaveGlobals']=='False') or className != 'GLOBAL'):
                fileSpec = fileSpecs[className]
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
            [constsEnums, forwardDecls, structCodeAcc, funcCodeAcc, className, dependancies]  = fileSpec
            filename = className+fileExtension
            header = makeFileHeader(tags, filename, xlator)
            outputStr = header + constsEnums + forwardDecls + structCodeAcc + funcCodeAcc
            fileSpecsOut.append([filename, outputStr])

    return fileSpecsOut

def clearBuild():
    global localVarsAllocated
    global localArgsAllocated
    global currentObjName
    global libInterfacesText
    global libInitCodeAcc
    global libDeinitCodeAcc
    global StaticMemberVars
    global globalFuncDeclAcc
    global globalFuncDefnAcc
    global ForwardDeclsForGlobalFuncs

    localVarsAllocated = []
    localArgsAllocated = []
    currentObjName=''
    libInterfacesText=''
    libInitCodeAcc=''
    libDeinitCodeAcc=''
    StaticMemberVars={}
    globalFuncDeclAcc=''
    globalFuncDefnAcc=''
    ForwardDeclsForGlobalFuncs='\n\n// Forward Declarations of global functions\n'

def generate(classes, tags, libsToUse, xlator):
    clearBuild()
    global globalClassStore
    global globalTagStore
    global buildStr_libs
    global libInterfacesText

    buildStr_libs = xlator['BuildStrPrefix']
    globalClassStore=classes
    globalTagStore=tags[0]
    buildStr_libs +=  progSpec.fetchTagValue(tags, "FileName")
    libInterfacesText=connectLibraries(classes, tags, libsToUse, xlator)
    addGLOBALSpecialCode(classes, tags, xlator)

    cdlog(1, "Generating Top-level (e.g., main())...")
    testMode = progSpec.fetchTagValue(tags, 'testMode')
    if progSpec.fetchTagValue(tags, 'ProgramOrLibrary') == "program"  or testMode == "makeTests"  or testMode == "runTests":
        generateBuildSpecificMainFunctionality(classes, tags, xlator)

    codeStructureCommands(classes, tags, xlator)
    cdlog(1, "Generating Classes...")
    fileSpecs=codeAllNonGlobalStructs(classes, tags, xlator)
    topBottomStrings = xlator['codeMain'](classes, tags, {}, xlator)
    typeDefCode = xlator['produceTypeDefs'](typeDefMap, xlator)

    fileSpecStrings = pieceTogetherTheSourceFiles(classes, tags, True, fileSpecs, [], topBottomStrings, xlator)
   # print "\n\n##########################################################\n"
    return fileSpecStrings



###############  Load a file to progspec, processing include files, string-structs, and patterns.

def GroomTags(tags):
    global globalTagStore
    if globalTagStore==None: TopLevelTags=tags
    else: TopLevelTags=globalTagStore
    # Set tag defaults as needed
    if not ('featuresNeeded' in TopLevelTags):
        TopLevelTags['featuresNeeded'] = []
    TopLevelTags['featuresNeeded'].append('CodeDog')
    # TODO: default to localhost for Platform, and CPU, etc. Add more combinations as needed.
    if not ('Platform' in TopLevelTags):
        platformID=platform.system()
        if platformID=='Darwin': platformID="OSX_Devices"
        TopLevelTags['Platform']=platformID

    # Find any needed features based on types used
    for typeName in progSpec.storeOfBaseTypesUsed:
        if(typeName=='BigNum' or typeName=='BigFrac'):
            print 'NOTE: Need Large Numbers'
            progSpec.setFeatureNeeded(TopLevelTags, 'largeNumbers', progSpec.storeOfBaseTypesUsed[typeName])

def ScanAndApplyPatterns(classes, topTags, newTags):
    global globalTagStore
    if globalTagStore==None:
        if topTags!={}: TopLevelTags=topTags
        else: TopLevelTags=newTags
    else: TopLevelTags=globalTagStore
    cdlog(1, "Applying Patterns...")
    itemsToDelete=[]; count=0;
    for item in classes[1]:
        if item[0]=='!':
            itemsToDelete.append(count)
            pattName=item[1:]
            patternArgs=classes[0][pattName]['parameters']
            cdlog(2, "PATTERN: {}: {}".format( pattName, patternArgs))

            if   pattName=='makeGUI':            pattern_GUI_Toolkit.apply(classes, TopLevelTags)
            elif pattName=='ManageCmdLine':      pattern_ManageCmdLine.apply(classes, newTags)
            elif pattName=='GeneratePtrSymbols': pattern_GenSymbols.apply(classes, newTags, patternArgs[0])
            elif pattName=='codeDataDisplay':    pattern_DispData.apply(classes, [newTags, topTags], patternArgs[0], patternArgs[1])
            elif pattName=='makeMenu':           pattern_MakeMenu.apply(classes, [newTags, topTags], patternArgs)
            else: cdErr("\nPattern {} not recognized.\n\n".format(pattName))
        count+=1
    for toDel in reversed(itemsToDelete):
        del(classes[1][toDel])


def loadProgSpecFromDogFile(filename, ProgSpec, objNames, topLvlTags, macroDefs):
    codeDogStr = progSpec.stringFromFile(filename)
    codeDogStr = libraryMngr.processIncludedFiles(codeDogStr)
  #  cdlog(0, "######################   P A R S I N G   F I L E  ({})".format(filename))
    [tagStore, buildSpecs, FileClasses, newClasses] = codeDogParser.parseCodeDogString(codeDogStr, ProgSpec, objNames, macroDefs)
    GroomTags(tagStore)
    ScanAndApplyPatterns(FileClasses, topLvlTags, tagStore)
    stringStructs.CreateStructsForStringModels(FileClasses, newClasses, tagStore)
    return [tagStore, buildSpecs, FileClasses]
