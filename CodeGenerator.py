# CodeGenerator.py
import re
import copy
import datetime
import platform
import codeDogParser
import libraryMngr
import progSpec
from progSpec import cdlog, cdErr, logLvl, dePythonStr
from progSpec import structsNeedingModification
from pyparsing import ParseResults


import pattern_GUI_Toolkit
import pattern_ManageCmdLine
import pattern_DispData
import pattern_GenSymbols
import pattern_MakeMenu
import pattern_MakeGUI
import pattern_RBMap
import pattern_MakeStyler
import pattern_WriteCallProxy

import stringStructs


buildStr_libs=''
globalFuncDeclAcc=''
globalFuncDefnAcc=''
ForwardDeclsForGlobalFuncs=''

listOfFuncsWithUnknownArgTypes = {}

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
        return 1 + bitsNeeded((n + 1) // 2)
###### Routines to track types of identifiers and to look up type based on identifier.

globalClassStore=[]
globalTagStore=None
localVarsAllocated = []   # Format: [varName, typeSpec]
localArgsAllocated = []   # Format: [varName, typeSpec]
currentObjName=''
inheritedEnums = {}

def CheckBuiltinItems(currentObjName, segSpec, objsRefed, xlator):
    # Handle print, return, break, etc.
    itemName=segSpec[0]
    [code, retOwner, retType]=xlator['codeSpecialReference'](segSpec, objsRefed, xlator)
    if code == '': return None
    if itemName=='self':
        classDef =  progSpec.findSpecOf(globalClassStore[0], currentObjName, "struct")
        if 'typeSpec' in classDef:
            typeSpecOut = classDef['typeSpec']
            typeSpecOut['owner']='their' # TODO: write test case for containers
            print("SHOULDNT MATCH:", typeSpecOut['owner'],classDef['typeSpec']['owner'])
        else: typeSpecOut={'owner':'their', 'fieldType':retType, 'arraySpec':None, 'containerSpec':None,'argList':None}
    else: typeSpecOut={'owner':retOwner, 'fieldType':retType, 'arraySpec':None, 'containerSpec':None,'argList':None}
    typeSpecOut['codeConverter']=code
    return [typeSpecOut, 'BUILTIN']

def CheckFunctionsLocalVarArgList(itemName):
    global localVarsAllocated
    for item in reversed(localVarsAllocated):
        if item[0]==itemName:
            return [item[1], 'LOCAL']
    global localArgsAllocated
    for item in reversed(localArgsAllocated):
        if item[0]==itemName:
            return [item[1], 'FUNCARG']
    return 0

def disassembleFieldID(fullFieldID):
    openParenPos   = fullFieldID.find("(")
    if(openParenPos == -1): return(fullFieldID, None)
    closeParenPos  = fullFieldID.find(")")
    classAndFuncName = fullFieldID[:openParenPos]
    argListString  = fullFieldID[openParenPos+1:closeParenPos]
    argList        = argListString.split(",")
    return(classAndFuncName, argList)

def reassembleFieldID(classAndFuncName, argList):
    fullFieldID = classAndFuncName
    fullFieldID += "("
    count = 0
    for arg in argList:
        if count > 0: fullFieldID += " ,"
        fullFieldID += arg
        count += 1
    fullFieldID += ")"
    return(fullFieldID)

def convertFieldIDType(fieldID, convertType):
    [classAndFuncName, argList] = disassembleFieldID(fieldID)
    if(argList != None):
        newArgList= []
        for arg in argList:
            if(arg == 'uint64_t' or arg == 'uint64' or arg == 'uint32' or arg == 'double' or arg == 'uint' or arg == 'int64' or arg == 'mode' or arg == 'int' or arg == 'int64_t'):
                newArgList.append('number_type')
            else:
                newArgList.append(arg)
        fieldID = reassembleFieldID(classAndFuncName, newArgList)
    return(fieldID)
def isArgNumeric(arg):
    if arg=='numeric' or arg=='int' or arg=='uint' or arg=='uint32' or arg=='BigInt' or arg=='int64' or arg=='uint':
        return True
    return False

def doFieldIDsMatch(foundFieldID, fullSearchFieldID):
    if(foundFieldID!=fullSearchFieldID):
        [foundClassAndFunc, foundArgs]  = disassembleFieldID(foundFieldID)
        [searchClassAndFunc, searchArgs] = disassembleFieldID(fullSearchFieldID)
        if foundClassAndFunc != searchClassAndFunc:
            return False
        if foundArgs != searchArgs:
            #print("  args don't match:  "+ str(foundFieldID)+"  !=  "+str(fullSearchFieldID))
            if(len(foundArgs) != len(searchArgs)):
                print("  # arg lists not same length: "+ foundFieldID+"  !=  "+fullSearchFieldID)
                return False
            count = 0
            while count < len(foundArgs):
                foundArg=foundArgs[count]
                searchArg=searchArgs[count]
                if(foundArg != searchArg):
                    argsMatch = False
                    if(foundArg=='any'):argsMatch = True
                    elif(searchArg=='NULL'):argsMatch = True
                    elif(searchArg=='BigInt' and foundArg=='string')or(searchArg=='string' and foundArg=='BigInt'):argsMatch = True
                    elif isArgNumeric(searchArg) and isArgNumeric(foundArg):argsMatch = True
                    if not argsMatch:
                        print("  args don't match:  "+ foundArg+"  !=  "+searchArg)
                        return False
                count += 1
        return True

def CheckObjectVars(className, itemName, fieldIDArgList):
    # also used to fetch codeConverter
    # if returning wrong overloaded codeConverter check fieldIDArgList
    searchFieldID = className+'::'+itemName
    fullSearchFieldID = className+'::'+itemName+fieldIDArgList
    #print("Searching",className,"for", itemName, fullSearchFieldID)
    ClassDef =  progSpec.findSpecOf(globalClassStore[0], className, "struct")
    if ClassDef==None:
        message = "ERROR: definition not found for: "+ str(className) + " : " + str(itemName)
        progSpec.setCurrentCheckObjectVars(message)
        return 0
    retVal=None

    wrappedTypeSpec = progSpec.isWrappedType(globalClassStore, className)
    if(wrappedTypeSpec != None):
        actualFieldType=progSpec.getFieldType(wrappedTypeSpec)
        if not isinstance(actualFieldType, str):
            retVal = CheckObjectVars(actualFieldType[0], itemName, "")
            if retVal!=0:
                wrappedOwner=progSpec.getOwnerFromTypeSpec(wrappedTypeSpec)
                retVal['typeSpec']['owner']=wrappedOwner
                return retVal
        else:
            if 'fieldName' in wrappedTypeSpec and wrappedTypeSpec['fieldName']==itemName:
                return wrappedTypeSpec
            else:
                message = "ERROR: MODEL def not found for: "+ str(className) + " : " + str(itemName)
                progSpec.setCurrentCheckObjectVars(message)
                return 0

    callableStructFields=[]
    progSpec.populateCallableStructFields(callableStructFields, globalClassStore, className)
    foundFieldID = 'None'
    # TODO: Need to complete but fix, should search callableStructFields
    #       by inheritance hierarchy.  Currently searches child class
    #       then all other fields returned.  Should find hierarchy then
    #       search child, parent, grandparent etc.
    #       commit 2111d27664f99c2b4aad289586438efa1846e355 (HEAD -> master, origin/master, origin/HEAD, patternMakeGUI)
    for field in callableStructFields:
        fieldName=field['fieldName']
        if fullSearchFieldID== field['fieldID']:
            #print("fullSearchFieldID:",fullSearchFieldID)
            return field
        if fieldName==itemName and 'number_type' in field['fieldID']:
            num_typeFieldID = convertFieldIDType(fullSearchFieldID, "number_type")
            if(field['fieldID'] == num_typeFieldID):
                return field
        if fieldName==itemName:
            foundFieldID = field
    if foundFieldID != 'None':
        #doIDsMatch = doFieldIDsMatch(foundFieldID['fieldID'], fullSearchFieldID)
        #print ("Found", itemName)
        return foundFieldID

    ### Check inherited enum values for a match after GLOBAL
    if searchFieldID.startswith("GLOBAL::"):
        searchFieldID = searchFieldID[8:]
    for enumInheritedType, enumValues in inheritedEnums.items():
        for value in enumValues:
            if value == searchFieldID:
                field['fieldID'] = "{}::{}".format(enumInheritedType, searchFieldID)
                return field

    #print("WARNING: Could not find field", itemName ,"in", className, "or inherited enums")
    return 0 # Field not found in model

def CheckClassStaticVars(className, itemName):
    ClassDef =  progSpec.findSpecOf(globalClassStore[0], itemName, "struct")
    if ClassDef==None:
        return None
    return [{'owner':'me', 'fieldType':[itemName], 'StaticMode':'yes'}, "CLASS:"+itemName]

StaticMemberVars={} # Used to find parent-class of const and enums

def staticVarNamePrefix(staticVarName, parentClass, xlator):
    global StaticMemberVars
    if staticVarName in StaticMemberVars:
        crntBaseName = progSpec.baseStructName(currentObjName)
        if parentClass!="": refedClass=parentClass
        else: refedClass=progSpec.baseStructName(StaticMemberVars[staticVarName])
        if(crntBaseName != refedClass or xlator['LanguageName']=='Swift'):   #TODO Make this part of xlators
            return refedClass + xlator['ObjConnector']
    return ''

def getFieldIDArgList(segSpec, objsRefed, xlator):
    argList=None
    fieldIDArgList = ""
    argListStr = ""
    if len(segSpec) > 1 and segSpec[1]=='(':
        if(len(segSpec)==2):
            argList=[]
        else:
            argList=segSpec[2]
    if(argList):
        count = 0
        fieldIDArgList += '('
        argListStr     += '('
        for arg in argList:
            [S2, argTypeSpec]=xlator['codeExpr'](arg[0], objsRefed, None, None, xlator)
            #print(argTypeSpec)
            keyWord = progSpec.fieldTypeKeyword(argTypeSpec)
            if keyWord == 'flag':keyWord ='bool'
            if keyWord == 'NONE':keyWord ='NULL'
            if(count >0 ):
                fieldIDArgList += ','
                argListStr     += ', '
            fieldIDArgList += keyWord
            argListStr     += S2
            count += 1
        fieldIDArgList += ')'
        argListStr     += ')'
        #print("fieldIDArgList:",fieldIDArgList)
        #print("argListStr:",argListStr)
    return [argListStr, fieldIDArgList]

def fetchItemsTypeSpec(segSpec, objsRefed, xlator):
    # also used to fetch codeConverter
    # return format: [{typeSpec}, 'OBJVAR']. Substitute for wrapped types.
    global currentObjName
    global StaticMemberVars
    global globalTagStore
    RefType=""
    useClassTag=""
    itemName=segSpec[0]
    [argListStr, fieldIDArgList] = getFieldIDArgList(segSpec, objsRefed, xlator)
    #print ("FETCHING TYPESPEC OF:", currentObjName+'::'+itemName+fieldIDArgList)
    if currentObjName != "":
        fieldID = currentObjName+'::'+itemName
        tagToFind       = "classOptions."+progSpec.flattenObjectName(fieldID)
        classOptionsTag = progSpec.fetchTagValue([globalTagStore], tagToFind)
        if classOptionsTag != None and "useClass" in classOptionsTag:
            useClassTag     = classOptionsTag["useClass"]
    REF=CheckBuiltinItems(currentObjName, segSpec, objsRefed, xlator)
    if (REF): # RefType="BUILTIN"
        return REF
    else:
        REF=CheckFunctionsLocalVarArgList(itemName)
        if (REF): # RefType="LOCAL" or "FUNCARG"
            return REF
        else:
            REF=CheckObjectVars(currentObjName, itemName, fieldIDArgList)
            if (REF):
                if useClassTag != "":
                    fieldType=progSpec.getFieldType(REF['typeSpec'])
                    if progSpec.doesClassHaveProperty(globalClassStore, fieldType, 'metaClass'):
                        REF['typeSpec']['fieldType'][0] = useClassTag
                RefType="OBJVAR"
                if(currentObjName=='GLOBAL'): RefType="GLOBAL"
                if xlator['LanguageName']=='Swift':  #TODO Make this part of xlators
                    RefOwner = progSpec.getTypeSpecOwner(REF['typeSpec'])
                    if RefOwner=='we': RefType = "STATIC:" + currentObjName + xlator['ObjConnector']
            else:
                REF=CheckObjectVars("GLOBAL", itemName, fieldIDArgList)
                if (REF):
                    RefType="GLOBAL"
                else:
                    REF=CheckClassStaticVars(currentObjName, itemName)
                    if(REF):
                        progSpec.addDependancyToStruct(currentObjName, itemName)
                        return REF

                    elif(itemName in StaticMemberVars):
                        parentClassName = staticVarNamePrefix(itemName, '', xlator)
                        if(parentClassName != ''):
                            return [{'owner':'me', 'fieldType':"string", 'arraySpec':{'note':'not generated from parse', 'owner':'me', 'datastructID':'list'}}, "STATIC:"+parentClassName]  # 'string' is probably not always correct.
                        else: return [{'owner':'me', 'fieldType':"string", 'arraySpec':{'note':'not generated from parse', 'owner':'me', 'datastructID':'list'}}, "CONST"]
                    if itemName=='NULL': return [{'owner':'their', 'fieldType':"pointer", 'arraySpec':None, 'containerSpec':None}, "CONST"]
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
    ClassDef = classes[0][className]
    for field in progSpec.generateListOfFieldsToImplement(classes, className):
        fieldType=progSpec.getFieldType(field['typeSpec'])
        fieldName=field['fieldName'];
        inheritsMode = False

        if isinstance(fieldType, list) and len(fieldType) == 1:
            fieldType = fieldType[0]
        try:
            if classes[0][fieldType]['tags']['inherits']['fieldType'].get('altModeIndicator', 0):
                inheritsMode = True
        except (KeyError, TypeError) as e:
            cdlog(6, "{}\n failed dict lookup in codeFlagAndModeFields".format(e))

        if fieldType=='flag' or fieldType=='mode' or inheritsMode:
            flagsVarNeeded=True

            fieldName = progSpec.flattenObjectName(fieldName)
            if fieldType=='flag':
                cdlog(6, "flag: {}".format(fieldName))
                structEnums += "    " + xlator['getConstIntFieldStr'](fieldName, hex(1<<bitCursor)) +" \t// Flag: "+fieldName+"\n"
                StaticMemberVars[fieldName]  =className
                bitCursor += 1;
            elif fieldType=='mode':
                cdlog(6, "mode: {}[]".format(fieldName))
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
            elif inheritsMode:
                cdlog(6, "mode inherited: {}[]".format(fieldName))
                structEnums += "\n// For Inherited Mode "+fieldName+"\n"
                enumSize= len(classes[0][fieldType]['tags']['inherits']['fieldType']['altModeList'].asList())
                numEnumBits=bitsNeeded(enumSize)
                enumMask=((1 << numEnumBits) - 1) << bitCursor

                offsetVarName = fieldName+"Offset"
                maskVarName   = fieldName+"Mask"
                structEnums += "    "+xlator['getConstIntFieldStr'](offsetVarName, hex(bitCursor))
                structEnums += "    "+xlator['getConstIntFieldStr'](maskVarName,   hex(enumMask)) + "\n"

                enumList=classes[0][fieldType]['tags']['inherits']['fieldType']['altModeList'].asList()
                StaticMemberVars[offsetVarName]=className
                StaticMemberVars[maskVarName]  =className
                StaticMemberVars[fieldName+'Strings']  = className
                modeStateNames[fieldName+'Strings']=className
                for eItem in enumList:
                    StaticMemberVars[eItem]=className

                bitCursor=bitCursor+numEnumBits;

    try:
        if classes[0][className]['tags']['inherits']['fieldType']['altModeIndicator']:
            enumList=classes[0][className]['tags']['inherits']['fieldType']['altModeList'].asList()
            CodeDogAddendums += "    me string[we list]: "+className+'Strings' + ' <- ' + '["'+('", "'.join(enumList))+'"]\n'
    except (KeyError, TypeError) as e:
        cdlog(6, "Warning: caught an exception error in codeFlagAndModeFields")

    if structEnums!="": structEnums="\n\n// *** Code for manipulating "+className+' flags and modes ***\n'+structEnums
    ClassDef['flagsVarNeeded'] = flagsVarNeeded
    return [flagsVarNeeded, structEnums, CodeDogAddendums]

typeDefMap={}
ObjectsFieldTypeMap={}
def registerType(objName, fieldName, typeOfField, typeDefTag):
    ObjectsFieldTypeMap[objName+'::'+fieldName]={'rawType':typeOfField, 'typeDef':typeDefTag}
    typeDefMap[typeOfField]=typeDefTag

def chooseStructImplementationToUse(typeSpec,className,fieldName):
    fieldType = progSpec.getFieldType(typeSpec)
    if not isinstance(fieldType, str) and  len(fieldType) >1:
        if ('chosenType' in fieldType):
            return(None)
        implementationOptions = progSpec.getImplementationOptionsFor(fieldType[0])
        if(implementationOptions == None):
            if fieldType[0]=="List":
                print("******WARNING: no implementationOptions found for LIST ",className,"::",fieldName)
                # Check to confirm List is in features needed
        else:
            reqTags = progSpec.getReqTags(fieldType)
            highestScore = -1
            highestScoreClassName = None
            for option in implementationOptions:
                optionClassDef =  progSpec.findSpecOf(globalClassStore[0], option, "struct")
                if 'tags' in optionClassDef and 'specs' in optionClassDef['tags']:
                    optionSpecs = optionClassDef['tags']['specs']
                    [implScore, errorMsg] = progSpec.scoreImplementation(optionSpecs, reqTags)
                    if(errorMsg != ""): cdErr(errorMsg)
                    if(implScore > highestScore):
                        highestScore = implScore
                        highestScoreClassName = optionClassDef['name']
            return(highestScoreClassName)
    return(None)
    #    choose highest score and mark the typedef

def codeAllocater(typeSpec, xlator):
    S=''
    owner           = progSpec.getTypeSpecOwner(typeSpec)
    fType               = progSpec.getFieldType(typeSpec)
    containerSpec   = progSpec.getContainerSpec(typeSpec)
    if isinstance(fType, str): varTypeStr1=fType;
    else: varTypeStr1=fType[0]

    [varTypeStr, innerType] = xlator['convertType'](globalClassStore, typeSpec, 'alloc', '', xlator)
    S= xlator['getCodeAllocStr'](varTypeStr, owner);
    return S

def convertNameSeg(typeSpecOut, name, paramList, objsRefed, xlator):
    newName = typeSpecOut['codeConverter']
    if paramList != None:
        count=1
        for P in paramList:
            oldTextTag='%'+str(count)
            [S2, argTypeSpec]=xlator['codeExpr'](P[0], objsRefed, None, None, xlator)
            if(isinstance(newName, str)):
                newName=newName.replace(oldTextTag, S2)
            else: exit(2)
            count+=1
        paramList=None
    return [newName, paramList]
################################  C o d e   E x p r e s s i o n s

def codeNameSeg(segSpec, typeSpecIn, connector, LorR_Val, previousSegName, previousTypeSpec, objsRefed, returnType, xlator):
    # if TypeSpecIn has 'dummyType', this is a non-member (or self) and the first segment of the reference.
    # return example: ['getData()', <typeSpec>, <alternate form>, 'OBJVAR']
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
    if 'fieldType' in typeSpecIn:
        fieldTypeIn = progSpec.getFieldType(typeSpecIn)
    else: fieldTypeIn = None


    isStructLikeContainer = False
    if progSpec.isNewContainerTempFunc(typeSpecIn): isStructLikeContainer = True

    IsAContainer = progSpec.isAContainer(typeSpecIn)
    if (fieldTypeIn!=None and isinstance(fieldTypeIn, str) and not IsAContainer):
        if fieldTypeIn=="string":
            [name, typeSpecOut] = xlator['recodeStringFunctions'](name, typeSpecOut)

    if owner=='itr':
        typeSpecOut = copy.copy(typeSpecIn)
        typeSpecOut['arraySpec'] = None
        fieldTypeOut=progSpec.getFieldTypeNew(typeSpecOut)
        codeCvrtText = xlator['codeIteratorOperation'](name, fieldTypeOut)
        if codeCvrtText!='':
            typeSpecOut['codeConverter'] = codeCvrtText
            if typeSpecOut['owner']=='itr': typeSpecOut['owner']='me'

    elif IsAContainer and (not isStructLikeContainer or name[0]=='['):
        [containerType, idxTypeSpec, owner]=xlator['getContainerType'](typeSpecIn, '')
        ownerOut=progSpec.getContainerFirstElementOwner(typeSpecIn)
        typeSpecOut={'owner':ownerOut, 'fieldType': fieldTypeIn}
        if(name[0]=='['):
            [S2, idxTypeSpec] = xlator['codeExpr'](name[1], objsRefed, None, None, xlator)
            S += xlator['codeArrayIndex'](S2, containerType, LorR_Val, previousSegName, idxTypeSpec)
            return [S, typeSpecOut, S2,'']
        [name, typeSpecOut, paramList, convertedIdxType]= xlator['getContainerTypeInfo'](globalClassStore, containerType, name, idxTypeSpec, typeSpecOut, paramList, xlator)

    elif ('dummyType' in typeSpecIn): # This is the first segment of a name
        if name=="return":
            SRC = "RETURN_TYPE"
            typeSpecOut['argList'] = [{'typeSpec':returnType}]
        elif(name=='resetFlagsAndModes'):
            typeSpecOut={'owner':'me', 'fieldType': 'void', 'codeConverter':'flags=0'}
            # TODO: if flags or modes have a non-zero default this should account for that.
        else:
            [typeSpecOut, SRC]=fetchItemsTypeSpec(segSpec, objsRefed, xlator) # Possibly adds a codeConversion to typeSpecOut
        if(SRC=="GLOBAL"): namePrefix = xlator['GlobalVarPrefix']
        if(SRC[:6]=='STATIC'): namePrefix = SRC[7:];
    else:
        if isStructLikeContainer == True: fType = progSpec.fieldTypeKeyword(typeSpecIn['fieldType'][0])
        else: fType=progSpec.fieldTypeKeyword(fieldTypeIn)
        if(name=='allocate'):
            S_alt=' = '+codeAllocater(typeSpecIn, xlator)
            typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif(name=='resetFlagsAndModes'):
            typeSpecOut={'owner':'me', 'fieldType': 'void', 'codeConverter':'flags=0'}
            # TODO: if flags or modes have a non-zero default this should account for that.
        elif(name[0]=='[' and fType=='string'):
            typeSpecOut={'owner':owner, 'fieldType': 'char'}
            [S2, idxTypeSpec] = xlator['codeExpr'](name[1], objsRefed, None, None, xlator)
            S += xlator['codeArrayIndex'](S2, 'string', LorR_Val, previousSegName, idxTypeSpec)
            return [S, typeSpecOut, S2, '']  # Here we return S2 for use in code forms other than [idx]. e.g. f(idx)
        elif(name[0]=='[' and (fType=='uint' or fType=='int')):
            print("Error: integers can't be indexed: ", previousSegName,  ":", name)
            exit(2)
        else:
            if fType!='string':
                [argListStr, fieldIDArgList] = getFieldIDArgList(segSpec, objsRefed, xlator)
                typeSpecOut=CheckObjectVars(fType, name, fieldIDArgList)
                if typeSpecOut!=0:
                    if isStructLikeContainer == True:
                        segTypeKeyWord = progSpec.fieldTypeKeyword(typeSpecOut['typeSpec'])
                        segTypeOwner   = progSpec.getOwnerFromTypeSpec(typeSpecOut['typeSpec'])
                        [innerTypeOwner, innerTypeKeyWord] = progSpec.queryTagFunction(globalClassStore, fType, "__getAt", segTypeKeyWord, typeSpecIn)
                        if(innerTypeOwner and segTypeOwner != 'itr'):
                            typeSpecOut['typeSpec']['owner'] = innerTypeOwner
                        if(innerTypeKeyWord):
                            typeSpecOut['typeSpec']['fieldType'][0] = innerTypeKeyWord
                    name=typeSpecOut['fieldName']
                    typeSpecOut=typeSpecOut['typeSpec']
                else: print("typeSpecOut = 0 for: "+previousSegName+"."+name)

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
        if typeSpecOut and ('argList' in typeSpecOut): modelParams=typeSpecOut['argList'];
        [CPL, paramTypeList] = codeParameterList(name, paramList, modelParams, objsRefed, xlator)
        S+= CPL
    if(typeSpecOut==None): cdlog(logLvl(), "Type for {} was not found.".format(name))
    return [S,  typeSpecOut, None, SRC]

def codeUnknownNameSeg(segSpec, objsRefed, xlator):
    S=''
    paramList=None
    segName=segSpec[0]
    segConnector = ''
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
    print("UNKNOWN NAME SEGMENT:", S)
    return S;

def codeItemRef(name, LorR_Val, objsRefed, returnType, xlator):
    # Returns information related to a variable, function, etc.
    # NOTE: objsRefed is used to accumulate a list of which vars are read and/or written by a function.
    global currentObjName
    previousSegName = ""
    previousTypeSpec = ""
    S=''
    segStr=''
    if(LorR_Val=='RVAL'): canonicalName ='>'
    else: canonicalName = '<'
    segTypeSpec={'owner':'', 'dummyType':True}

    connector=''
    prevLen=len(S)
    segIDX=0
    AltFormat=None
    AltIDXFormat=''
    for segSpec in name:
        LHSParentType='#'
        owner=progSpec.getTypeSpecOwner(segTypeSpec)
        segName=segSpec[0]
        if(segIDX>0):
            # Detect connector to use '.' '->', '', (*...).
            connector='.'
            if(segTypeSpec): # This is where to detect type of vars not found to determine whether to use '.' or '->'
                if 'StaticMode' in segTypeSpec and segTypeSpec['StaticMode']=='yes':
                    connector = xlator['ObjConnector']
                elif progSpec.wrappedTypeIsPointer(globalClassStore, segTypeSpec, segName):
                    connector = xlator['PtrConnector']

        AltFormat=None
        if segTypeSpec!=None:
            if segTypeSpec and 'fieldType' in segTypeSpec:
                LHSParentType = progSpec.fieldTypeKeyword(progSpec.getFieldType(segTypeSpec))
            else: LHSParentType = progSpec.fieldTypeKeyword(currentObjName)   # Landed here because this is the first segment
            [segStr, segTypeSpec, AltIDXFormat, nameSource]=codeNameSeg(segSpec, segTypeSpec, connector, LorR_Val, previousSegName, previousTypeSpec, objsRefed, returnType, xlator)
            if nameSource!='': canonicalName+=nameSource
            if AltIDXFormat!=None:
                AltFormat=[S, previousTypeSpec, AltIDXFormat]   # This is in case of an alternate index format such as Java's string.put(idx, val)
        else:
            segStr= codeUnknownNameSeg(segSpec, objsRefed, xlator)
        prevLen=len(S)


        if(isinstance(segTypeSpec, int)):
            cdErr("Segment '{}' in the name '{}' is not recognized.".format(segSpec[0], dePythonStr(name)))

        # Record canonical name for record keeping
        if not isinstance(segName, str):
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
    #        if connector=='->' and owner!='itr': S="*("+S+")"
            S=segStr.replace("%0", S)
            S=S[len(connector):]
        else: S+=segStr


        # Language specific dereferencing of ->[...], etc.
        S = xlator['LanguageSpecificDecorations'](S, segTypeSpec, owner)

        objsRefed[canonicalName]=0
        previousSegName = segName
        previousTypeSpec = segTypeSpec
        segIDX+=1

    # Handle cases where seg's type is flag or mode
    if segTypeSpec and LorR_Val=='RVAL' and 'fieldType' in segTypeSpec:
        fieldType=progSpec.getFieldType(segTypeSpec)
        if fieldType=='flag':
            segName=segStr[len(connector):]
            prefix = staticVarNamePrefix(segName, LHSParentType, xlator)
            bitfieldMask=xlator['applyTypecast']('uint64', prefix+segName)
            flagReadCode = '('+S[0:prevLen] + connector + 'flags & ' + bitfieldMask+')'
            S=xlator['applyTypecast']('int', flagReadCode)
        elif fieldType=='mode':
            segName=segStr[len(connector):]
            prefix = staticVarNamePrefix(segName+"Mask", LHSParentType, xlator)
            bitfieldMask  =xlator['applyTypecast']('uint64', prefix+segName+"Mask")
            bitfieldOffset=xlator['applyTypecast']('uint64', prefix+segName+"Offset")
            S="((" + S[0:prevLen] + connector +  "flags&"+bitfieldMask+")"+">>"+bitfieldOffset+')'
            S=xlator['applyTypecast']('int', S)

    return [S, segTypeSpec, LHSParentType, AltFormat]

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
    global listOfFuncsWithUnknownArgTypes
    S=''
    count = 0
    paramTypeList=[]
    totalParams= len(paramList)
    totalDefaultValue=0
    if (modelParams==[]):
        modelParams = None
    if (modelParams!=None):
        for P in modelParams:
            if 'value' in P and P['value']:
                totalDefaultValue=len(modelParams)

    if(totalDefaultValue>0):
        count=0
        for MP in modelParams:
            if not(count<totalParams) and MP['value']:
                paramList.insert(count, MP['value'])
            count+=1

    if(len(paramList)==0 ):
        if name != 'return' and name!='break' and name!='continue' and name!='characters.count':
            S+="()"
    else:
        count = 0
        for P in paramList:
            if(count>0): S+=', '
            [S2, argTypeSpec]=xlator['codeExpr'](P[0], objsRefed, None, None, xlator)
            paramTypeList.append(argTypeSpec)
            if modelParams and (len(modelParams)>count) and ('typeSpec' in modelParams[count]):
                [leftMod, rightMod]=xlator['chooseVirtualRValOwner'](modelParams[count]['typeSpec'], argTypeSpec)
                S += leftMod+S2+rightMod
            else:
                listOfFuncsWithUnknownArgTypes[(name+'()')]=1
                S += S2
            count+=1
        S='(' + S + ')'
    return [S, paramTypeList]

def codeFuncCall(funcCallSpec, objsRefed, returnType, xlator):
    S=''
    [codeStr, typeSpec, LHSParentType, AltIDXFormat]=codeItemRef(funcCallSpec, 'RVAL', objsRefed, returnType, xlator)
    S+=codeStr
    return S

def startPointOfNamesLastSegment(name):
    p=len(name)-1
    while(p>0):
        if name[p]=='>' or name[p]=='.':
            return p
        p-=1
    return -1

def genIfBody(ifBody, indent, objsRefed, returnType, xlator):
    ifBodyText = ""
    for ifAction in ifBody:
        actionOut = codeAction(ifAction, indent + "    ", objsRefed, returnType, xlator)
        ifBodyText += actionOut
    return ifBodyText

def encodeConditionalStatement(action, indent, objsRefed, returnType, xlator):
    [S2, conditionTypeSpec] =  xlator['codeExpr'](action['ifCondition'][0], objsRefed, None, None, xlator)
    [S2, conditionTypeSpec] =  xlator['adjustConditional'](S2, conditionTypeSpec)
    ifCondition = S2
    ifBodyText = genIfBody(action['ifBody'], indent, objsRefed, returnType, xlator)
    actionText =  indent + "if (" + ifCondition + ") " + "{\n" + ifBodyText + indent + "}\n"
    elseBodyText = ""
    elseBody = action['elseBody']
    if (elseBody):
        if (elseBody[0]=='if'):
            elseAction = elseBody[1]
            elseText = encodeConditionalStatement(elseAction[0], indent, objsRefed, returnType, xlator)
            actionText += indent + "else " + elseText.lstrip()
        elif (elseBody[0]=='action'):
            elseAction = elseBody[1]['actionList']
            elseText = codeActionSeq(elseAction, indent, objsRefed, returnType, xlator)
            actionText += indent + "else " + elseText.lstrip()
        else:  print("Unrecognized item after else"); exit(2);
    return actionText

def codeAction(action, indent, objsRefed, returnType, xlator):
    #make a string and return it
    global localVarsAllocated
    global globalClassStore
    actionText = ""
    action['sideEffects']=[]
    typeOfAction = action['typeOfAction']

    if (typeOfAction =='newVar'):
        fieldDef=action['fieldDef']
        typeSpec= fieldDef['typeSpec']
        fieldName =fieldDef['fieldName']
        structToImplement = chooseStructImplementationToUse(typeSpec,currentObjName,fieldName)
        if(structToImplement != None):
            typeSpec['fieldType'][0] = structToImplement
        varName = fieldDef['fieldName']
        cdlog(5, "Action newVar: {}".format(varName))
        varDeclareStr = xlator['codeNewVarStr'](globalClassStore, typeSpec, varName, fieldDef, indent, objsRefed, 'action', xlator)
        actionText = indent + varDeclareStr + ";\n"
        localVarsAllocated.append([varName, typeSpec])  # Tracking local vars for scope
    elif (typeOfAction =='assign'):
        cdlog(5, "PREASSIGN:" + str(action['LHS']))
        # Note: In Java, string A[x]=B must be coded like: A.put(B,x)
        cdlog(5, "Pre-assignment... ")
        [codeStr, lhsTypeSpec, LHSParentType, AltIDXFormat] = codeItemRef(action['LHS'], 'LVAL', objsRefed, returnType, xlator)
        assignTag = action['assignTag']
        LHS = codeStr
        cdlog(5, "Assignment: {}".format(LHS))
        [S2, rhsTypeSpec]=xlator['codeExpr'](action['RHS'][0], objsRefed, None, lhsTypeSpec, xlator)
        [LHS_leftMod, LHS_rightMod,  RHS_leftMod, RHS_rightMod]=xlator['determinePtrConfigForAssignments'](lhsTypeSpec, rhsTypeSpec, assignTag,codeStr)
        LHS = LHS_leftMod+LHS+LHS_rightMod
        RHS = RHS_leftMod+S2+RHS_rightMod
        cdlog(5, "Assignment: {} = {}".format(lhsTypeSpec, rhsTypeSpec))
        RHS = xlator['checkForTypeCastNeed'](lhsTypeSpec, rhsTypeSpec, RHS)
        if not isinstance (lhsTypeSpec, dict):
            #TODO: make test case
            print('Problem: lhsTypeSpec is', lhsTypeSpec, '\n');
            LHS_FieldType='string'
        else: LHS_FieldType=progSpec.getFieldType(lhsTypeSpec)

        if assignTag == '':
            if LHS_FieldType=='flag':
                divPoint=startPointOfNamesLastSegment(LHS)
                LHS_Left=LHS[0:divPoint+1] # The '+1' makes this get the connector too. e.g. '.' or '->'
                bitMask =LHS[divPoint+1:]
                prefix = staticVarNamePrefix(bitMask, LHSParentType, xlator)
                setBits = xlator['codeSetBits'](LHS_Left, LHS_FieldType, prefix, bitMask, RHS, rhsTypeSpec)
                actionText=indent + setBits
            elif LHS_FieldType=='mode':
                divPoint=startPointOfNamesLastSegment(LHS)
                if (divPoint == 0):
                    LHS_Left=""
                    bitMask =LHS
                else:
                    LHS_Left=LHS[0:divPoint+1]
                    bitMask =LHS[divPoint+1:]
                prefix = staticVarNamePrefix(bitMask+"Mask", LHSParentType, xlator)
                setBits = xlator['codeSetBits'](LHS_Left, LHS_FieldType, prefix, bitMask, RHS, rhsTypeSpec)
                actionText=indent + setBits
            else:
                if AltIDXFormat!=None:
                    # Handle special forms of assignment such as LVal(idx, RVal)
                    actionText = xlator['checkIfSpecialAssignmentFormIsNeeded'](AltIDXFormat, RHS, rhsTypeSpec, LHS, LHSParentType, LHS_FieldType)
                    if actionText != '': actionText = indent+actionText
                if actionText=="":
                    # Handle the normal assignment case
                    if RHS=='nil' and LHS[-1]=='!': LHS=LHS[:-1]  #TODO: Move this code to swift xlator
                    actionText = indent + LHS + " = " + RHS + ";\n"
        else:
            assignTag = assignTag[0]
            if(assignTag=='deep'):
                actionText = indent + LHS + " = " + RHS + ";\n"
            elif(assignTag=='+'):
                actionText = indent + LHS + " += " + RHS + ";\n"
            elif(assignTag=='-'):
                actionText = indent + LHS + " -= " + RHS + ";\n"
            elif(assignTag=='*'):
                actionText = indent + LHS + " *= " + RHS + ";\n"
            elif(assignTag=='/'):
                actionText = indent + LHS + " /= " + RHS + ";\n"
            elif(assignTag=='%'):
                actionText = indent + LHS + " %= " + RHS + ";\n"
            elif(assignTag=='<<'):
                actionText = indent + LHS + " <<= " + RHS + ";\n"
            elif(assignTag=='>>'):
                actionText = indent + LHS + " >>= " + RHS + ";\n"
            elif(assignTag=='&'):
                actionText = indent + LHS + " &= " + RHS + ";\n"
            elif(assignTag=='^'):
                actionText = indent + LHS + " ^= " + RHS + ";\n"
            elif(assignTag=='|'):
                actionText = indent + LHS + " |= " + RHS + ";\n"
            else:
                actionText = indent + "opAssign" + assignTag + '(' + LHS + ", " + RHS + ");\n"
    elif (typeOfAction =='swap'):
        LHS = action['LHS']
        RHS =  action['RHS']
        typeSpec   = fetchItemsTypeSpec(LHS, objsRefed, xlator)
        print("swap LHS RHS: ", LHS, RHS,typeSpec)
        [typeLHS, innerTypeLHS] = xlator['convertType'](globalClassStore, typeSpec[0], 'var', 'action', xlator)
        print("typeLHS: ", typeLHS, " --- ", innerTypeLHS)
        typeSpec   = fetchItemsTypeSpec(RHS, objsRefed, xlator)
        [typeRHS, innerTypeRHS] = xlator['convertType'](globalClassStore, typeSpec[0], 'var', 'action', xlator)
        LHS = LHS[0]
        RHS = RHS[0]
        actionText = indent + typeLHS + " tmp = " + LHS + ";\n"
        actionText += indent + LHS + " = " + RHS + ";\n"
        actionText += indent + RHS + " = " + "tmp;\n"
        print("actionText: ", actionText)
    elif (typeOfAction =='conditional'):
        cdlog(5, "If-statement...")
        [S2, conditionTypeSpec] =  xlator['codeExpr'](action['ifCondition'][0], objsRefed, None, None, xlator)
        [S2, conditionTypeSpec] =  xlator['adjustConditional'](S2, conditionTypeSpec)
        cdlog(5, "If-statement: Condition is ".format(S2))
        ifCondition = S2


        ifBodyText = genIfBody(action['ifBody'], indent, objsRefed, returnType, xlator)
        actionText =  indent + "if (" + ifCondition + ") " + "{\n" + ifBodyText + indent + "}\n"
        elseBodyText = ""
        elseBody = action['elseBody']
        if (elseBody):
            if (elseBody[0]=='if'):
                elseAction = elseBody[1][0]
                elseText = encodeConditionalStatement(elseAction, indent, objsRefed, returnType, xlator)
                actionText += indent + "else " + elseText.lstrip()
            elif (elseBody[0]=='action'):
                elseAction = elseBody[1]['actionList']
                elseText = codeActionSeq(elseAction, indent, objsRefed, returnType, xlator)
                actionText += indent + "else " + elseText.lstrip()
            else:  print("Unrecognized item after else"); exit(2);
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
            [S_low, lowValTypeSpec] = xlator['codeExpr'](rangeSpec[2][0], objsRefed, None, None, xlator)
            [S_hi,   hiValTypeSpec] = xlator['codeExpr'](rangeSpec[4][0], objsRefed, None, None, xlator)
            ctrlVarsTypeSpec = lowValTypeSpec
            actionText += xlator['codeRangeSpec'](traversalMode, ctrType, repName, S_low, S_hi, indent, xlator)
            localVarsAllocated.append([repName, ctrlVarsTypeSpec])  # Tracking local vars for scope
        elif(whileSpec):
            [whileExpr, whereConditionTypeSpec] = xlator['codeExpr'](whileSpec[2], objsRefed, None, None, xlator)
            [whileExpr, whereConditionTypeSpec] =  xlator['adjustConditional'](whileExpr, whereConditionTypeSpec)
            actionText += indent + "while(" + whileExpr + "){\n"
            loopCounterName=repName
        elif(fileSpec):
            [filenameExpr, filenameTypeSpec] = xlator['codeExpr'](fileSpec[2], objsRefed, None, None, xlator)
            if filenameTypeSpec!='string':
                cdErr("Filename must be a string.\n")
            print("File iteration not implemeted yet.\n")
            exit(2)
        elif(keyRange):
            [repContainer, containerTypeSpec] = xlator['codeExpr'](keyRange[0][0], objsRefed, None, None, xlator)
            [StartKey, StartTypeSpec] = xlator['codeExpr'](keyRange[2][0], objsRefed, None, None, xlator)
            [EndKey,   EndTypeSpec] = xlator['codeExpr'](keyRange[4][0], objsRefed, None, None, xlator)

            [datastructID, keyFieldType, ContainerOwner]=xlator['getContainerType'](containerTypeSpec, '')
            wrappedTypeSpec = progSpec.isWrappedType(globalClassStore, progSpec.getFieldType(containerTypeSpec)[0])
            if(wrappedTypeSpec != None):containerTypeSpec=wrappedTypeSpec

            [actionTextOut, loopCounterName] = xlator['iterateRangeContainerStr'](globalClassStore,localVarsAllocated, StartKey, EndKey, containerTypeSpec,ContainerOwner,repName,repContainer,datastructID,keyFieldType,indent,xlator)
            actionText += actionTextOut

        else: # interate over a container
            [repContainer, containerTypeSpec] = xlator['codeExpr'](action['repList'][0], objsRefed, None, None, xlator)
            if containerTypeSpec==None or not progSpec.isAContainer(containerTypeSpec): cdErr("'"+repContainer+"' is not a container so cannot be iterated over.")
            [datastructID, keyFieldType, ContainerOwner]=xlator['getContainerType'](containerTypeSpec, 'action')

            wrappedTypeSpec = progSpec.isWrappedType(globalClassStore, progSpec.getFieldType(containerTypeSpec)[0])
            if(wrappedTypeSpec != None):containerTypeSpec=wrappedTypeSpec
            if(traversalMode=='Forward' or traversalMode==None):
                isBackward=False
            elif(traversalMode=='Backward'):
                isBackward=True
            [actionTextOut, loopCounterName] = xlator['iterateContainerStr'](globalClassStore,localVarsAllocated,containerTypeSpec,repName,repContainer,datastructID,keyFieldType, ContainerOwner, isBackward, 'action', indent,xlator)
            actionText += actionTextOut

        if action['whereExpr']:
            [whereExpr, whereConditionTypeSpec] = xlator['codeExpr'](action['whereExpr'], objsRefed, None, None, xlator)
            actionText += indent + "    " + 'if (!' + whereExpr + ') continue;\n'
        if action['untilExpr']:
            [untilExpr, untilConditionTypeSpec] = xlator['codeExpr'](action['untilExpr'], objsRefed, None, None, xlator)
            actionText += indent + '    ' + 'if (' + untilExpr + ') break;\n'
        repBodyText = ''
        for repAction in repBody:
            actionOut = codeAction(repAction, indent + "    ", objsRefed, returnType, xlator)
            repBodyText += actionOut
        if loopCounterName!='':
            actionText=indent + ctrType+" " + loopCounterName + "=0;\n" + actionText
            repBodyText += indent + "    " + xlator['codeIncrement'](loopCounterName) + ";\n"
        actionText += repBodyText + indent + '}\n'
    elif (typeOfAction =='funcCall'):
        calledFunc = action['calledFunc']
        if calledFunc[0][0] == 'if' or calledFunc=='withEach' or calledFunc=='until' or calledFunc=='where':
            print("\nERROR: It is not allowed to name a function", calledFunc[0][0])
            exit(2)
        cdlog(5, "Function Call: {}()".format(str(calledFunc[0][0])))
        funcCallText = codeFuncCall(calledFunc, objsRefed, returnType, xlator)
        funcCallTextStriped = funcCallText.strip()
        if (funcCallTextStriped!=''):
            actionText = indent + funcCallText + ';\n'
    elif (typeOfAction == 'switchStmt'):
        cdlog(5, "Switch statement: switch({})".format(str(action['switchKey'])))
        [switchKeyExpr, switchKeyTypeSpec] = xlator['codeExpr'](action['switchKey'][0], objsRefed, None, None, xlator)
        actionText += indent+"switch("+ switchKeyExpr + "){\n"
        blockPrefix = xlator['blockPrefix']
        for sCases in action['switchCases']:
            actionText += indent
            for sCase in sCases[0]:
                [caseKeyValue, caseKeyTypeSpec] = xlator['codeExpr'](sCase[0], objsRefed, None, None, xlator)
                actionText += "    case "+caseKeyValue+": "
            caseAction = sCases[1]
            actionText += blockPrefix + codeActionSeq(caseAction, indent+'    ', objsRefed, returnType, xlator)
            actionText += xlator['codeSwitchBreak'](caseAction, indent, xlator)
        defaultCase=action['defaultCase']
        if defaultCase and len(defaultCase)>0:
            actionText+=indent+"default: "
            actionText += blockPrefix + codeActionSeq(defaultCase, indent, objsRefed, returnType, xlator)
        else: actionText+=indent+"default: break;\n"
        actionText += indent + "}\n"
    elif (typeOfAction =='actionSeq'):
        cdlog(5, "Action Sequence")
        actionListIn = action['actionList']
        actionListText = ''
        for action in actionListIn:
            actionListOut = codeAction(action, indent + "    ", objsRefed, returnType, xlator)
            actionListText += actionListOut
        blockPrefix = xlator['blockPrefix']
        actionText += indent + blockPrefix + "{\n" + actionListText + indent + '}\n'
    else:
        print("error in codeAction: ", action)
        exit(2)
    return actionText

def codeActionSeq(actSeq, indent, objsRefed, returnType, xlator):
    global localVarsAllocated
    localVarsAllocated.append(["STOP",''])
    actSeqText=''
    actSeqText += '{\n'
    for action in actSeq:
        actionText = codeAction(action, indent + '    ', objsRefed, returnType, xlator)
        actSeqText += actionText
    actSeqText += indent + '}\n'
    localVarRecord=['','']
    while(localVarRecord[0] != 'STOP'):
        localVarRecord=localVarsAllocated.pop()
    return actSeqText

def codeConstructor(classes, ClassName, tags, objsRefed, xlator):
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
        fieldType=progSpec.getFieldType(typeSpec)
        if(fieldType=='flag' or fieldType=='mode'): continue
        if(typeSpec['argList'] or typeSpec['argList']!=None): continue
        if progSpec.isAContainer(typeSpec): continue
        fieldOwner=progSpec.getOwnerFromTypeSpec(typeSpec)
        if(fieldOwner=='const' or fieldOwner == 'we'): continue
        [convertedType, innerType] = xlator['convertType'](classes, typeSpec, 'var', 'constructor', xlator)
        fieldName=field['fieldName']

        cdlog(4, "Coding Constructor: {} {} {} {}".format(ClassName, fieldName, fieldType, convertedType))
        if not isinstance(fieldType, str): fieldType=fieldType[0]
        defaultVal=''
        if(fieldOwner != 'me'):
            if(fieldOwner != 'my'):
                defaultVal = "NULL"
        elif (isinstance(fieldType, str)):
            if(fieldType=="int" or fieldType=="uint" or fieldType=="uint64" or fieldType=="uint32"or fieldType=="int64" or fieldType=="int32"):
                defaultVal = "0"
            elif(fieldType=="string"):
                defaultVal = '""'
            else: # handle structs if needed
                if 'value' in field and field['value']!=None:
                    [defaultVal, defaultValueTypeSpec] = xlator['codeExpr'](field['value'][0], objsRefed, None, None, xlator)
        if defaultVal != '':
        #    if count == 0: defaultVal = ''  # uncomment this line to NOT generate a default value for the first constructor argument.
            constructorArgs += xlator['codeConstructorArgText'](fieldName, count, convertedType, defaultVal, xlator)+ ","
            constructorInit += xlator['codeConstructorInit'](fieldName, count, defaultVal, xlator)

            count += 1
        copyConstructorArgs += xlator['codeCopyConstructor'](fieldName, convertedType, xlator)

    funcBody = ''
    constructCode=''
    callSuperConstructor=''
    parentClasses = progSpec.getParentClassList(classes, ClassName)
    if parentClasses:
        parentClasses[0] = progSpec.filterClassesToString(parentClasses[0])
        callSuperConstructor = xlator['codeSuperConstructorCall'](parentClasses[0])

    fieldID  = ClassName+'::INIT'
    if(progSpec.doesClassDirectlyImlementThisField(classes[0], ClassName, fieldID)):
        funcBody += xlator['codeConstructorCall'](ClassName)
    if(count>0):
        constructorArgs=constructorArgs[0:-1]
    if count>0 or funcBody != '':
        constructCode += xlator['codeConstructors'](flatClassName, constructorArgs, constructorInit, copyConstructorArgs, funcBody, callSuperConstructor, xlator)

    return constructCode

def codeStructFields(classes, className, tags, indent, objsRefed, xlator):
    global currentObjName
    global ForwardDeclsForGlobalFuncs
    global globalClassStore
    cdlog(3, "Coding fields for {}...".format(className))
    ####################################################################
    global localArgsAllocated
    funcBodyIndent   = xlator['funcBodyIndent']
    funcsDefInClass  = xlator['funcsDefInClass']
    MakeConstructors = xlator['MakeConstructors']
    globalFuncsAcc=""
    funcDefCodeAcc=""
    structCodeAcc=""
    topFuncDefCodeAcc="" # For defns that must appear first in the code. TODO: sort items instead
    ObjectDef = classes[0][className]
    for field in progSpec.generateListOfFieldsToImplement(classes, className):
        ################################################################
        ### extracting FIELD data
        ################################################################
        localArgsAllocated=[]
        funcDefCode=""
        structCode=""
        globalFuncs=""
        topFuncDefCode=""
        funcText=""
        fieldID  =field['fieldID']
        typeSpec =field['typeSpec']
        fieldType=progSpec.getFieldType(typeSpec)
        if progSpec.doesClassHaveProperty(globalClassStore, fieldType, 'metaClass'):
            tagToFind       = "classOptions."+progSpec.flattenObjectName(fieldID)
            classOptionsTag = progSpec.fetchTagValue(tags, tagToFind)
            if classOptionsTag != None and "useClass" in classOptionsTag:
                useClassTag     = classOptionsTag["useClass"]
                fieldType[0] = useClassTag
        if(fieldType=='flag' or fieldType=='mode'): continue
        fieldOwner=progSpec.getTypeSpecOwner(typeSpec)
        fieldName =field['fieldName']
        isAllocated = field['isAllocated']
        cdlog(4, "FieldName: {}".format(fieldName))
        fieldValue=field['value']
        fieldArglist = typeSpec['argList']
        paramList = field['paramList']
        [intermediateType, innerType] = xlator['convertType'](classes, typeSpec, 'var', 'field', xlator)
        convertedType = progSpec.flattenObjectName(intermediateType)
        typeDefName = convertedType # progSpec.createTypedefName(fieldType)

        ## ASSIGNMENTS###############################################
        if fieldName=='opAssign':
            fieldName='operator='

        # CALCULATE RHS
        if(fieldValue == None):
            if className == "GLOBAL" and isAllocated==True: # Allocation for GLOBAL handled in appendGLOBALInitCode()
                isAllocated = False
                paramList = None
            fieldValueText=xlator['codeVarFieldRHS_Str'](fieldName, convertedType, innerType, fieldOwner, paramList, objsRefed, isAllocated, xlator)
            #print ("    RHS none: ", fieldValueText)
        elif(fieldOwner=='const'):
            if isinstance(fieldValue, str):
                fieldValueText = ' = "'+ fieldValue + '"'
                #TODO:  make test case
            else:
                fieldValueText = " = "+ xlator['codeExpr'](fieldValue[0], objsRefed, None, None, xlator)[0]
            #print ("    RHS const: ", fieldValueText)
        elif(fieldArglist==None):
            fieldValueText = " = " + xlator['codeExpr'](fieldValue[0], objsRefed, None, None, xlator)[0]
            #print ("    RHS var: ", fieldValueText)
        else:
            fieldValueText = " = "+ str(fieldValue)
            #print ("    RHS func or array")

        ############ CODE MEMBER VARIABLE ##########################################################
        if(fieldOwner=='const'):
            [structCode, topFuncDefCode] = xlator['codeConstField_Str'](convertedType, fieldName, fieldValueText, className, indent, xlator )
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
                    structToImplement = chooseStructImplementationToUse(argTypeSpec,className,argFieldName)
                    if(structToImplement != None):
                        argTypeSpec['fieldType'][0] = structToImplement
                    [argType, innerType] = xlator['convertType'](classes, argTypeSpec, 'arg', 'field', xlator)
                    argListText+= xlator['codeArgText'](argFieldName, argType, xlator)
                    localArgsAllocated.append([argFieldName, argTypeSpec])  # localArgsAllocated is a global variable that keeps track of nested function arguments and local vars.

            #### RETURN TYPE
            FirstReturnType = {'owner':fieldOwner, 'fieldType':fieldType}
            if(fieldType[0] != '<%'):
                pass #registerType(className, fieldName, convertedType, typeDefName)
            else: typeDefName=convertedType
            if(typeDefName=='none'):
                typeDefName=''

            #### FUNC HEADER: for both decl and defn.
            inheritMode='normal'
            # TODO: But it should NOT be virtual if there are no calls of the function from a pointer to the base class
            if not progSpec.doesParentClassImplementFunc(classes, className, fieldID) and progSpec.doesChildClassImplementFunc(classes, className, fieldID):
                inheritMode = 'virtual'
            if currentObjName in progSpec.classHeirarchyInfo:
                classRelationData = progSpec.classHeirarchyInfo[currentObjName]
                if ('parentClass' in classRelationData and classRelationData['parentClass']!=None):
                    parentClassName = classRelationData['parentClass']
                    if progSpec.fieldIDAlreadyDeclaredInStruct(classes[0], parentClassName, fieldID):
                        inheritMode = 'override'

            abstractFunction = (not('value' in field) or field['value']==None)
            if abstractFunction and not 'abstract' in classes[0][className]['attrList']:
                inheritMode = 'pure-virtual'
                classes[0][className]['attrList'].append('abstract')
            # TODO: this is hard coded to compensate for when virtual func class has base class and child class
            if className == 'dash' and (fieldName == 'addDependent' or fieldName == 'requestRedraw' or fieldName == 'setPos' or fieldName == 'addRelation' or fieldName == 'dependentIsRegistered'):inheritMode = 'virtual'
            # ####################################################################
            [structCode, funcDefCode, globalFuncs]=xlator['codeFuncHeaderStr'](className, fieldName, typeDefName, argListText, localArgsAllocated, inheritMode, indent)

            #### FUNC BODY
            if abstractFunction: # i.e., if no function body is given.
                cdlog(5, "Function "+fieldID+" has no implementation defined.")
            else:
                extraCodeForTopOfFuntion = xlator['extraCodeForTopOfFuntion'](argList)
                if typeDefName=='' and 'flagsVarNeeded' in ObjectDef and ObjectDef['flagsVarNeeded']==True:
                    extraCodeForTopOfFuntion+="    flags=0;"
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
                elif field['value'][0]!='':
                    objsRefed2={}
                    funcText =  codeActionSeq(field['value'][0], funcBodyIndent, objsRefed2, FirstReturnType, xlator)
                    if extraCodeForTopOfFuntion!='':
                        funcText = '{\n' + extraCodeForTopOfFuntion + funcText[1:]
                 #   for rec in sorted(objsRefed2):
                    if globalFuncs!='': ForwardDeclsForGlobalFuncs += globalFuncs+";       \t\t // Forward Decl\n"
                else:
                    cdErr("ERROR: In codeFields: no funcText or funcTextVerbatim found")

            if(funcsDefInClass=='True' ):
                structCode += funcText

            elif(className=='GLOBAL'):
                if(fieldName=='main'):
                    funcDefCode += funcText
                else:
                    globalFuncs += funcText
            else: funcDefCode += funcText


        ## Accumulate field code
        structCodeAcc     += structCode
        funcDefCodeAcc    += funcDefCode
        globalFuncsAcc    += globalFuncs
        topFuncDefCodeAcc += topFuncDefCode

    # TODO: Remove this Hard Coded widget. It should apply to any abstract class.
    if MakeConstructors=='True' and (className!='GLOBAL')  and (className!='widget'):
        constructCode=codeConstructor(classes, className, tags, objsRefed, xlator)
        structCodeAcc+= "\n"+constructCode
    funcDefCodeAcc = topFuncDefCodeAcc + funcDefCodeAcc
    return [structCodeAcc, funcDefCodeAcc, globalFuncsAcc]

def processDependancies(classes, item, searchList, newList):
    if searchList[item][1]==0:
        searchList[item][1]=1
        className=searchList[item][0]
        depList = progSpec.getClassesDependancies(className)
        for dep in depList:
            depIdx=findIDX(searchList, dep)
            processDependancies(classes, depIdx, searchList, newList)
        newList.append(className)
        searchList[item][1]=2
    elif searchList[item][1]==1:
        print("WARNING: Dependancy cycle detected including class "+searchList[item][0])

def findIDX(classList, className):
    # Returns the index in classList of className or -1
    for findIdx in range(0, len(classList)):
        if classList[findIdx][0]==className: return findIdx
    return -1

def sortClassesForDependancies(classes, classList):
    newList=[]
    searchList=[]
    for item in classList:
        if(item=="GLOBAL"): searchList.insert(0, [item, 0])
        else: searchList.append([item, 0])
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
    classRecord=None
    constsEnums=""  # this isn't used. Remove it?
    dependancies=[]
    currentObjName=className
    if((xlator['doesLangHaveGlobals']=='False') or className != 'GLOBAL'): # and ('enumList' not in classes[0][className]['typeSpec'])):
        inheritsMode = False
        try:
            if classes[0][className]['tags']['inherits']['fieldType']['altModeIndicator']:
                inheritsMode = True
        except (TypeError, KeyError) as e:
            cdlog(6, "{}\n failed dict lookup in codeOneStruct".format(e))
        if inheritsMode:     # struct is an enum
            cdlog(1, "   Class that inherits mode: " + className)
            forwardDeclsOut = ""
            enumVals = classes[0][className]['tags']['inherits']['fieldType']['altModeList']
            structCodeOut = "\n" + xlator['getEnumStr'](className, enumVals).lstrip()
            funcCode = xlator['getEnumStringifyFunc'](className, enumVals)
            inheritedEnums[className] = enumVals
        else:
            cdlog(1, "   Class: " + className)
            classDef = progSpec.findSpecOf(classes[0], className, 'struct')
            modelDef = progSpec.findSpecOf(classes[0], className, 'model')
            classAttrs=progSpec.searchATagStore(classDef['tags'], 'attrs')
            if(classAttrs): classAttrs=classAttrs[0]+' '
            else: classAttrs=''
            classInherits=progSpec.searchATagStore(classDef, 'inherits')
            if modelDef != None:
                if classInherits is None: classInherits=progSpec.searchATagStore(modelDef, 'inherits')
                else: classInherits.append(progSpec.searchATagStore(modelDef, 'inherits'))
            classImplements=progSpec.searchATagStore(classDef, 'implements')

            if (className in structsNeedingModification):
                cdlog(3, "structsNeedingModification: {}".format(str(structsNeedingModification[className])))
                [classToModify, modificationMode, interfaceImplemented, markItem]=structsNeedingModification[className]
                if modificationMode == 'implement':
                    if classImplements is None:
                        classImplements=[]
                    classImplements.append( [interfaceImplemented])
                else: classInherits.append( interfaceImplemented)

            parentClass=''
            seperatorIdx=className.rfind('::')
            if(seperatorIdx != -1):
                parentClass=className[0:seperatorIdx]

            objsRefed={}
            [structCode, funcCode, globalCode]=codeStructFields(classes, className, tags, '    ', objsRefed, xlator)
            structCode+= constFieldCode

            attrList = classDef['attrList']
            if classAttrs!='': attrList.append(classAttrs)  # TODO: should append all items from classAttrs
            LangFormOfObjName = progSpec.flattenObjectName(className)
            [structCodeOut, forwardDeclsOut] = xlator['codeStructText'](classes, attrList, parentClass, classInherits, classImplements, LangFormOfObjName, structCode, tags)
            typeArgList = progSpec.getTypeArgList(className)
            if(typeArgList != None):
                forwardDeclsOut = ""
                templateHeader = xlator['codeTemplateHeader'](typeArgList)
                structCodeOut=templateHeader+structCodeOut
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
            codeDogParser.AddToObjectFromText(classes[0], classes[1], progSpec.wrapFieldListInObjectDef(className,  CodeDogAddendumsAcc ), 'Flags and Modes for class '+className)
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
            calledFuncID = command[1]
            calledFuncName = progSpec.fieldNameID(calledFuncID)
            if calledFuncName in progSpec.funcsCalled:
                calledFuncInstances = progSpec.funcsCalled[calledFuncName]
                #print '     addImplements:'
                #print '          calledFuncName:', calledFuncName
                for funcCalledParams in calledFuncInstances:
                    #print '\n funcCalledParams:',funcCalledParams
                    paramList = funcCalledParams[0]
                    commandArgs = command[2]
                    if paramList != None:
                        count=1
                        for P in paramList:
                            oldTextTag='%'+str(count)
                            [newText, argTypeSpec]=xlator['codeExpr'](P[0], {}, None, None, xlator)
                            commandArgs=commandArgs.replace(oldTextTag, newText)
                            count+=1
                        #print commandArgs
                    firstColonPos=commandArgs.find(':')
                    secondColonPos=commandArgs.find(':', firstColonPos+1)
                    interfaceImplemented=commandArgs[:firstColonPos]
                    classToModify=commandArgs[secondColonPos+1:]
                    structsNeedingModification[classToModify] = [classToModify, "implement", interfaceImplemented, progSpec.MarkItems]
        if (command[3] == 'addCallProxy'):
            className       = command[0]
            funcBundle      = command[2]
            platformTag      = tags[1]['Platform']
            for itm in funcBundle:
                itm = itm[1:-1]
                funcArgs        = itm.split(":")
                proxyStyle      = funcArgs[0]
                funcName        = funcArgs[1]
                #print '     addCallProxy:', className, funcName, proxyStyle, platformTag
                pattern_WriteCallProxy.apply(classes, tags, proxyStyle, className, funcName, platformTag)

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

[libInitCodeAcc,  libDeinitCodeAcc] = ['', '']
[libEmbedVeryHigh, libEmbedCodeHigh, libEmbedCodeLow] = ['', '', '']

def integrateLibrary(tags, tagsFromLibFiles, libID, xlator):
    global libInitCodeAcc
    global libDeinitCodeAcc
    global buildStr_libs
    global libEmbedCodeHigh
    global libEmbedCodeLow
    global libEmbedVeryHigh
    headerStr = ''
    headerTopStr = ''
    #cdlog(2, 'Integrating {}'.format(libID))
    # TODO: Choose static or dynamic linking based on defaults, license tags, availability, etc.

    if 'initCode'     in tagsFromLibFiles[libID]: libInitCodeAcc  += tagsFromLibFiles[libID]['initCode']
    if 'deinitCode'   in tagsFromLibFiles[libID]: libDeinitCodeAcc = tagsFromLibFiles[libID]['deinitCode'] + libDeinitCodeAcc + "\n"
    if 'embedVeryHigh'in tagsFromLibFiles[libID]: libEmbedVeryHigh+= tagsFromLibFiles[libID]['embedVeryHigh']
    if 'embedHigh'    in tagsFromLibFiles[libID]: libEmbedCodeHigh+= tagsFromLibFiles[libID]['embedHigh']
    if 'embedLow'     in tagsFromLibFiles[libID]: libEmbedCodeLow += tagsFromLibFiles[libID]['embedLow']

    if 'interface' in tagsFromLibFiles[libID]:
        if 'libFiles' in tagsFromLibFiles[libID]['interface']:
            libFiles = tagsFromLibFiles[libID]['interface']['libFiles']
            for libFile in libFiles:
                buildStr_libs+=libFile
        if 'headers' in tagsFromLibFiles[libID]['interface']:
            libHeaders = tagsFromLibFiles[libID]['interface']['headers']
            for libHdr in libHeaders:
                if libHdr == '"stdafx.h"':
                    headerTopStr = xlator['includeDirective'](libHdr)
                else:
                    headerStr += xlator['includeDirective'](libHdr)
    return [headerStr, headerTopStr]

def connectLibraries(classes, tags, libsToUse, xlator):
    headerStr = ''
    tagsFromLibFiles = libraryMngr.getTagsFromLibFiles()
    for libFilename in libsToUse:
        cdlog(1, 'ATTACHING LIBRARY: '+libFilename)
        [headerStrOut, headerTopStr] = integrateLibrary(tags, tagsFromLibFiles, libFilename, xlator)
        headerStr = headerTopStr + headerStr + headerStrOut
        macroDefs= {}
        [tagStore, buildSpecs, FileClasses] = loadProgSpecFromDogFile(libFilename, classes[0], classes[1], tags[0], macroDefs)

    return headerStr

def convertTemplateClasses(classes, tags):
    structsToImplement = fetchListOfStructsToImplement(classes, tags)
    for className in structsToImplement:
        for field in progSpec.generateListOfFieldsToImplement(classes, className):
            typeSpec =field['typeSpec']
            fieldName =field['fieldName']
            structToImplement = chooseStructImplementationToUse(typeSpec,className,fieldName)
            if(structToImplement != None):
                typeSpec['fieldType'][0] = structToImplement

def appendGLOBALInitCode(classes, tags, xlator):
    for field in progSpec.generateListOfFieldsToImplement(classes, "GLOBAL"):
        isAllocated = field['isAllocated']
        if isAllocated:
            fieldName =field['fieldName']
            paramList = field['paramList']
            paramStr  = ''
            #if paramList != None:
                #if(len(paramList)>0 ):
                    #for param in paramList:
                        # TODO: grab base parameter in codeDog, similar to codeExpr but through codeDog xlator
                    #paramStr = ' <- (' + paramStr + ')'
            allocStr = '    Allocate('+fieldName+')' + paramStr
            progSpec.addCodeToInit(tags[0], allocStr)

def addGLOBALSpecialCode(classes, tags, xlator):
    global libInitCodeAcc
    global libDeinitCodeAcc
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
    codeDogParser.AddToObjectFromText(classes[0], classes[1], GLOBAL_CODE, 'Global special code (initialize(), deinitialize())' )

def generateBuildSpecificMainFunctionality(classes, tags, xlator):
    xlator['generateMainFunctionality'](classes, tags)

def pieceTogetherTheSourceFiles(classes, tags, oneFileTF, fileSpecs, headerInfo, MainTopBottom, xlator):
    global ForwardDeclsForGlobalFuncs
    global libEmbedVeryHigh
    global libEmbedCodeHigh
    global libEmbedCodeLow
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

        outputStr = header + constsEnums + forwardDecls + libEmbedVeryHigh + structCodeAcc + ForwardDeclsForGlobalFuncs + libEmbedCodeHigh + MainTopBottom[0] + funcCodeAcc + libEmbedCodeLow + MainTopBottom[1]
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
    global listOfFuncsWithUnknownArgTypes

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
    listOfFuncsWithUnknownArgTypes = {}

def generate(classes, tags, libsToUse, langName, xlator):
    clearBuild()
    global globalClassStore
    global globalTagStore
    global buildStr_libs
    global libInterfacesText
    global listOfFuncsWithUnknownArgTypes

    buildStr_libs = xlator['BuildStrPrefix']
    globalClassStore=classes
    globalTagStore=tags[0]
    buildStr_libs +=  progSpec.fetchTagValue(tags, "FileName")
    libInterfacesText=connectLibraries(classes, tags, libsToUse, xlator)

    cdlog(0, "\n##############  C O N V E R T I N G    T E M P L A T E S")
    convertTemplateClasses(classes, tags)

    cdlog(0, "\n##############  G E N E R A T I N G   "+langName+"   C O D E . . .")
    cdlog(1, "GENERATING: Top-level (e.g., main())...")
    appendGLOBALInitCode(classes, tags, xlator)
    addGLOBALSpecialCode(classes, tags, xlator)
    testMode = progSpec.fetchTagValue(tags, 'testMode')
    if progSpec.fetchTagValue(tags, 'ProgramOrLibrary') == "program"  or testMode == "makeTests"  or testMode == "runTests":
        generateBuildSpecificMainFunctionality(classes, tags, xlator)

    codeStructureCommands(classes, tags, xlator)
    cdlog(1, "GENERATING: Classes...")
    fileSpecs=codeAllNonGlobalStructs(classes, tags, xlator)
    topBottomStrings = xlator['codeMain'](classes, tags, {}, xlator)
    typeDefCode = xlator['produceTypeDefs'](typeDefMap, xlator)

    fileSpecStrings = pieceTogetherTheSourceFiles(classes, tags, True, fileSpecs, [], topBottomStrings, xlator)
    print("\n\nNOTE: The following functions were used but CodeDog couldn't determine the type of their arguments:")
    for funcName in listOfFuncsWithUnknownArgTypes: print(funcName, end=' ')
    print("\n");
    return fileSpecStrings

###############  Load a file to progspec, processing include files, string-structs, and patterns.
def GroomTags(tags):
    global globalTagStore
    if globalTagStore==None: TopLevelTags=tags
    else: TopLevelTags=globalTagStore
    # Set tag defaults as needed
    if not ('featuresNeeded' in TopLevelTags):
        TopLevelTags['featuresNeeded'] = []
    TopLevelTags['featuresNeeded'].insert(0, 'CodeDog')
    # TODO: default to localhost for Platform, and CPU, etc. Add more combinations as needed.
    if not ('Platform' in TopLevelTags):
        platformID=platform.system()
        if platformID=='Darwin': platformID="OSX_Devices"
        TopLevelTags['Platform']=platformID

    # Find any needed features based on types used
    for typeName in progSpec.storeOfBaseTypesUsed:
        if(typeName=='BigNum' or typeName=='BigFrac'):
            print('NOTE: Need Large Numbers')
            progSpec.setFeatureNeeded(TopLevelTags, 'largeNumbers', progSpec.storeOfBaseTypesUsed[typeName])

def ScanAndApplyPatterns(classes, topTags, newTags):
    global globalTagStore
    if globalTagStore==None:
        if topTags!={}: TopLevelTags=topTags
        else: TopLevelTags=newTags
    else: TopLevelTags=globalTagStore
    #if len(classes[1])>0: cdlog(1, "Applying Patterns...")
    itemsToDelete=[]; count=0;
    for item in classes[1]:
        if item[0]=='!':
            itemsToDelete.append(count)
            pattNameIdx=item[1:]
            pattName=classes[0][pattNameIdx]['name']
            patternArgs=classes[0][pattNameIdx]['parameters']
            cdlog(1, "APPLYING PATTERN: {}: {}".format( pattName, patternArgs))

            if   pattName=='makeGUI':            pattern_GUI_Toolkit.apply(classes, TopLevelTags)
            elif pattName=='codeModelToGUI':     pattern_MakeGUI.apply(classes, [newTags, topTags], patternArgs[0])
            elif pattName=='ManageCmdLine':      pattern_ManageCmdLine.apply(classes, newTags)
            elif pattName=='GeneratePtrSymbols': pattern_GenSymbols.apply(classes, newTags, patternArgs)
            elif pattName=='codeModelDashes':    pattern_DispData.apply(classes, [newTags, topTags], patternArgs[0], patternArgs[1])
            elif pattName=='codeDataDisplay':    pattern_DispData.apply(classes, [newTags, topTags], patternArgs[0], patternArgs[1])
            elif pattName=='codeModelToString':  pattern_DispData.apply(classes, [newTags, topTags], patternArgs[0], 'text')
            elif pattName=='codeModelToProteus': pattern_DispData.apply(classes, [newTags, topTags], patternArgs[0], 'Proteus')
           # elif pattName=='codeModelToGUI':     pattern_DispData.apply(classes, [newTags, topTags], patternArgs[0], 'toGUI')
            elif pattName=='makeMenu':           pattern_MakeMenu.apply(classes, [newTags, topTags], patternArgs)
            elif pattName=='makeRBMap':          pattern_RBMap.apply(classes, [newTags, topTags], patternArgs[0], patternArgs[1])
            elif pattName=='makeStyler':         pattern_MakeStyler.apply(classes, [newTags, topTags], patternArgs[0])
            else: cdErr("\nPattern {} not recognized.\n\n".format(pattName))
        count+=1
    for toDel in reversed(itemsToDelete):
        del(classes[1][toDel])

def loadProgSpecFromDogFile(filename, ProgSpec, objNames, topLvlTags, macroDefs):
    codeDogStr = progSpec.stringFromFile(filename)
    codeDogStr = libraryMngr.processIncludedFiles(codeDogStr, filename)
    [tagStore, buildSpecs, FileClasses, newClasses] = codeDogParser.parseCodeDogString(codeDogStr, ProgSpec, objNames, macroDefs, filename)
    GroomTags(tagStore)
    ScanAndApplyPatterns(FileClasses, topLvlTags, tagStore)
    stringStructs.CreateStructsForStringModels(FileClasses, newClasses, tagStore)
    return [tagStore, buildSpecs, FileClasses]
