# codeGenerator.py
import re
import copy
import datetime
import platform
import codeDogParser
import libraryMngr
import progSpec
import buildDog
from progSpec import cdlog, cdErr, logLvl, dePythonStr
from progSpec import structsNeedingModification
from pyparsing import ParseResults
from pprint import pprint

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
import os
import errno


class CodeGenerator(object):
    buildStr_libs=''
    funcDeclAcc=''
    funcDefnAcc=''
    ForwardDeclsForGlobalFuncs=''

    listOfFuncsWithUnknownArgTypes = {}

    def appendGlobalFuncAcc(self, decl, defn):
        if decl!="":
            self.funcDeclAcc+=decl+';      \t// Forward function declaration\n'
            self.funcDefnAcc+=decl+defn

    def bitsNeeded(self, n):
        if n <= 1:
            return 0
        else:
            return 1 + self.bitsNeeded((n + 1) // 2)
    ###### Routines to track types of identifiers and to look up type based on identifier.

    classStore     = []
    tagStore       = None
    localVarsAllocated   = []   # Format: [varName, typeSpec]
    localArgsAllocated   = []   # Format: [varName, typeSpec]
    currentObjName       = ''
    inheritedEnums       = {}
    constFieldAccs       = {}
    modeStringsAcc = ''
    genericStructsGenerated = [ {}, [] ]

    def typeIsInteger(self, fieldType):
        # NOTE: If you need this to work for wrapped types as well use the version in CodeGenerator.py
        if fieldType == None: return False
        if progSpec.typeIsNumRange(fieldType): return True
        if not isinstance(fieldType, str):
            fieldType= fieldType[0]
        fieldType=progSpec.getUnwrappedClassFieldTypeKeyWord(self.classStore, fieldType)
        if fieldType=="int" or fieldType=="BigInt" or fieldType=="uint" or fieldType=="uint64" or fieldType=="uint32"or fieldType=="int64" or fieldType=="int32" or fieldType=="FlexNum":
            return True
        return False

    def typeIsRational(self, fieldType):
        # NOTE: If you need this to work for wrapped types as well use the version in CodeGenerator.py
        if fieldType == None: return False
        #if progSpec.typeIsNumRange(fieldType): return True
        if not isinstance(fieldType, str):
            fieldType= fieldType[0]
        fieldType=progSpec.getUnwrappedClassFieldTypeKeyWord(self.classStore, fieldType)
        if fieldType=="double" or fieldType=="float" or fieldType=="BigFloat" or fieldType=="FlexNum":
            return True
        return False

    def CheckBuiltinItems(self, currentObjName, segSpec, objsRefed, genericArgs):
        # Handle print, return, break, etc.
        itemName=segSpec[0]
        [code, retOwner, retType]=self.xlator.codeSpecialReference(segSpec, objsRefed, genericArgs)
        if code == '': return None
        if itemName=='self':
            classDef =  progSpec.findSpecOf(self.classStore[0], currentObjName, "struct")
            if 'typeSpec' in classDef:
                typeSpecOut = classDef['typeSpec']
                typeSpecOut['owner']='their' # TODO: write test case for containers
                print("SHOULDNT MATCH:", typeSpecOut['owner'],classDef['typeSpec']['owner'])
            else: typeSpecOut={'owner':'their', 'fieldType':retType, 'arraySpec':None, 'argList':None}
        else: typeSpecOut={'owner':retOwner, 'fieldType':retType, 'arraySpec':None, 'argList':None}
        typeSpecOut['codeConverter']=code
        return [typeSpecOut, 'BUILTIN']

    def CheckFunctionsLocalVarArgList(self, itemName):
        for item in reversed(self.localVarsAllocated):
            if item[0]==itemName:
                return [item[1], 'LOCAL']
        for item in reversed(self.localArgsAllocated):
            if item[0]==itemName:
                return [item[1], 'FUNCARG']
        return 0

    def disassembleFieldID(self, fullFieldID):
        openParenPos   = fullFieldID.find("(")
        if(openParenPos == -1): return(fullFieldID, None)
        closeParenPos  = fullFieldID.find(")")
        classAndFuncName = fullFieldID[:openParenPos]
        argListString  = fullFieldID[openParenPos+1:closeParenPos]
        argList        = argListString.split(",")
        return(classAndFuncName, argList)

    def reassembleFieldID(self, classAndFuncName, argList):
        fullFieldID = classAndFuncName
        fullFieldID += "("
        count = 0
        for arg in argList:
            if count > 0: fullFieldID += " ,"
            fullFieldID += arg
            count += 1
        fullFieldID += ")"
        return(fullFieldID)

    def convertFieldIDType(self, fieldID, cvrtType):
        [classAndFuncName, argList] = self.disassembleFieldID(fieldID)
        if(argList != None):
            newArgList= []
            for arg in argList:
                if(arg == 'uint64_t' or arg == 'uint64' or arg == 'uint32' or arg == 'double' or arg == 'uint' or arg == 'int64' or arg == 'mode' or arg == 'int' or arg == 'int64_t'):
                    newArgList.append('number_type')
                else:
                    newArgList.append(arg)
            fieldID = self.reassembleFieldID(classAndFuncName, newArgList)
        return(fieldID)

    def isArgNumeric(self, arg):
        if arg=='numeric' or arg=='int' or arg=='int32' or arg=='int64'  or arg=='uint' or arg=='uint32' or arg=='uint64' or arg=='BigInt':
            return True
        return False

    def doFieldIDsMatch(self, foundFieldID, fullSearchFieldID):
        if(foundFieldID!=fullSearchFieldID):
            [foundClassAndFunc, foundArgs]  = self.disassembleFieldID(foundFieldID)
            [searchClassAndFunc, searchArgs] = self.disassembleFieldID(fullSearchFieldID)
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
                        elif self.isArgNumeric(searchArg) and self.isArgNumeric(foundArg):argsMatch = True
                        if not argsMatch:
                            print("  args don't match:  "+ foundArg+"  !=  "+searchArg)
                            return False
                    count += 1
            return True

    def CheckObjectVars(self, className, itemName, fieldIDArgList):
        # also used to fetch codeConverter
        # if returning wrong overloaded codeConverter check fieldIDArgList
        searchFieldID = className+'::'+itemName
        fullSearchFieldID = className+'::'+itemName+fieldIDArgList
        #print("Searching",className,"for", itemName, fullSearchFieldID)
        classDef =  progSpec.findSpecOf(self.classStore[0], className, "struct")
        if classDef==None:
            message = "ERROR: definition not found for: "+ str(className) + " : " + str(itemName)
            progSpec.setCurrentCheckObjectVars(message)
            return 0
        retVal=None
        #if("libLevel" in classDef and classDef["libLevel"] == 2 and not 'implements' in classDef): if(classDef["libLevel"] == 2): cdErr(searchFieldID+ " is not defined in parent library of "+str(classDef["libName"]))

        wrappedTypeSpec = progSpec.isWrappedType(self.classStore, className)
        if(wrappedTypeSpec != None):
            actualFieldType=progSpec.getFieldType(wrappedTypeSpec)
            if not isinstance(actualFieldType, str):
                retVal = self.CheckObjectVars(actualFieldType[0], itemName, "")
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
        progSpec.populateCallableStructFields(callableStructFields, self.classStore, className)
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
                num_typeFieldID = self.convertFieldIDType(fullSearchFieldID, "number_type")
                if(field['fieldID'] == num_typeFieldID):
                    return field
            if fieldName==itemName:
                foundFieldID = field
        if foundFieldID != 'None':
            #doIDsMatch = self.doFieldIDsMatch(foundFieldID['fieldID'], fullSearchFieldID)
            #print ("Found", itemName)
            return foundFieldID

        ### Check inherited enum values for a match after GLOBAL
        if searchFieldID.startswith("GLOBAL::"):
            searchFieldID = searchFieldID[8:]
        for enumInheritedType, enumValues in self.inheritedEnums.items():
            for value in enumValues:
                if value == searchFieldID:
                    newField = {'typeSpec': {'owner': 'me', 'fieldType': enumInheritedType}, 'fieldName': itemName}
                    newField['fieldID'] = "{}::{}".format(enumInheritedType, searchFieldID)
                    newField['typeSpec']['isGlobalEnum'] = True
                    return newField

        #print("WARNING: Could not find field", itemName ,"in", className, "or inherited enums")
        return 0 # Field not found in model

    def CheckClassStaticVars(self, className, itemName):
        classDef =  progSpec.findSpecOf(self.classStore[0], itemName, "struct")
        if classDef==None:
            return None
        return [{'owner':'me', 'fieldType':[itemName], 'StaticMode':'yes'}, "CLASS:"+itemName]

    StaticMemberVars={} # Used to find parent-class of const and enums

    def staticVarNamePrefix(self, staticVarName, parentClass):
        if staticVarName in self.StaticMemberVars:
            crntBaseName = progSpec.baseStructName(self.currentObjName)
            if parentClass!="": refedClass=parentClass
            else: refedClass=progSpec.baseStructName(self.StaticMemberVars[staticVarName])
            if refedClass=="GLOBAL": return ''
            if(crntBaseName != refedClass or self.xlator.LanguageName=='Swift'):   #TODO Make this part of xlators
                return refedClass + self.xlator.ObjConnector
        return ''

    def getFieldIDArgList(self, segSpec, objsRefed, genericArgs):
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
                [S2, argTypeSpec]=self.codeExpr(arg[0], objsRefed, None, None, 'LVAL', genericArgs)
                #print(argTypeSpec)
                keyWord = progSpec.fieldTypeKeyword(argTypeSpec)
                if keyWord == 'flag':keyWord ='bool'
                if keyWord == None:keyWord ='NULL'
                if(count >0 ):
                    fieldIDArgList += ','
                    argListStr     += ', '
                fieldIDArgList += keyWord
                argListStr     += S2
                count += 1
            fieldIDArgList += ')'
            argListStr     += ')'
        return [argListStr, fieldIDArgList]

    def fetchItemsTypeSpec(self, segSpec, objsRefed, genericArgs):
        # also used to fetch codeConverter
        # return format: [{typeSpec}, 'OBJVAR']. Substitute for wrapped types.
        RefType=""
        useClassTag=""
        itemName=segSpec[0]
        [argListStr, fieldIDArgList] = self.getFieldIDArgList(segSpec, objsRefed, genericArgs)
        #print ("FETCHING TYPESPEC OF:", self.currentObjName+'::'+itemName+fieldIDArgList)
        if self.currentObjName != "":
            fieldID = self.currentObjName+'::'+itemName
            tagToFind       = "classOptions."+progSpec.flattenObjectName(fieldID)
            classOptionsTag = progSpec.fetchTagValue([self.tagStore], tagToFind)
            if classOptionsTag != None and "useClass" in classOptionsTag:
                useClassTag     = classOptionsTag["useClass"]
        REF=self.CheckBuiltinItems(self.currentObjName, segSpec, objsRefed, genericArgs)
        if (REF): # RefType="BUILTIN"
            return REF
        else:
            REF=self.CheckFunctionsLocalVarArgList(itemName)
            if (REF): # RefType="LOCAL" or "FUNCARG"
                return REF
            else:
                REF=self.CheckObjectVars(self.currentObjName, itemName, fieldIDArgList)
                if (REF):
                    if useClassTag != "":
                        fieldType=progSpec.fieldTypeKeyword(REF['typeSpec'])
                        if progSpec.doesClassHaveProperty(self.classStore, fieldType, 'metaClass'):
                            REF['typeSpec']['fieldType'][0] = useClassTag
                    RefType="OBJVAR"
                    if(self.currentObjName=='GLOBAL'): RefType="GLOBAL"
                    if self.xlator.LanguageName=='Swift':  #TODO Make this part of xlators
                        RefOwner = progSpec.getTypeSpecOwner(REF['typeSpec'])
                        if RefOwner=='we': RefType = "STATIC:" + self.currentObjName + self.xlator.ObjConnector
                else:
                    REF=self.CheckObjectVars("GLOBAL", itemName, fieldIDArgList)
                    if (REF):
                        RefType="GLOBAL"
                    else:
                        REF=self.CheckClassStaticVars(self.currentObjName, itemName)
                        if(REF):
                            progSpec.addDependencyToStruct(self.currentObjName, REF[0])
                            return REF

                        elif(itemName in self.StaticMemberVars):
                            parentClassName = self.staticVarNamePrefix(itemName, '')
                            retTypeSpec     = {'owner': 'me', 'fieldType': ['List', [{'tArgOwner': 'me', 'tArgType': 'string'}]], 'note':'not generated from parse', 'reqTagList': [{'tArgOwner': 'me', 'tArgType': 'string'}]}
                            if(parentClassName != ''):
                                return [retTypeSpec, "STATIC:"+parentClassName]  # 'string' is probably not always correct.
                            else: return [retTypeSpec, "CONST"]
                        if itemName=='NULL': return [{'owner':'their', 'fieldType':"pointer", 'arraySpec':None}, "CONST"]
                        cdlog(logLvl(), "Variable {} could not be found.".format(itemName))
                        return [None, "LIB"]      # TODO: Return correct type
        return [REF['typeSpec'], RefType]
        # Example: [{typeSpec}, 'OBJVAR']

    ###### End of type tracking code
    modeStateNames={}

    def getModeStateNames(self):
        return self.modeStateNames

    def getInheritedEnums(self):
        return self.inheritedEnums

    typeDefMap={}
    ObjectsFieldTypeMap={}
    def registerType(self, objName, fieldName, typeOfField, typeDefTag):
        ObjectsFieldTypeMap[objName+'::'+fieldName]={'rawType':typeOfField, 'typeDef':typeDefTag}
        self.typeDefMap[typeOfField]=typeDefTag

    def checkForReservedWord(self, identifier, currentObjName):
        # TODO: other cases such as class names and enum values are not checked.
        if identifier in ['auto', 'and', 'or', 'const', 'me', 'my', 'our', 'their', 'we', 'itr', 'while', 'withEach'
                'do', 'else', 'flag', 'mode', 'for', 'if', 'model', 'struct', 'switch', 'typedef', 'void']:
            if currentObjName!="": currentObjName = " in "+currentObjName
            cdErr("Reserved word '"+identifier+"' cannot be used as an identifier"+ currentObjName)
        if currentObjName!="":
            if identifier in ['break', 'continue', 'return', 'false', 'NULL', 'true']:
                cdErr("Reserved word '"+identifier+"' cannot be an identifier in "+ currentObjName)

    #### GENERIC TYPE HANDLING #############################################
    def makeFromImpl(self, className, implName):
        retVal   = {}
        retVal['implements'] = implName
        typeArgs = progSpec.getTypeArgList(className)
        retVal["typeArgList"] = typeArgs
        fieldDefAt  = self.CheckObjectVars(className, "at", "")
        if fieldDefAt:
            typeSpecAt = fieldDefAt['typeSpec']
            atTypeSpec = {"owner":progSpec.getOwnerFromTypeSpec(typeSpecAt), "fieldType":progSpec.fieldTypeKeyword(typeSpecAt)}
            retVal["atTypeSpec"] = atTypeSpec
            # Now try to get the 'key' typeSpec
            if 'argList' in typeSpecAt and typeSpecAt['argList']!=None:
                firstParametersSpec = typeSpecAt['argList'][0]
                firstParametersTypeSpec = firstParametersSpec['typeSpec']
                keyTypeSpec = {"owner":progSpec.getOwnerFromTypeSpec(firstParametersTypeSpec), "fieldType":progSpec.fieldTypeKeyword(firstParametersTypeSpec)}
                retVal["atKeyTypeSpec"] = keyTypeSpec
        fieldDefFind = self.CheckObjectVars(className, "find", "")
        if fieldDefFind:
            itrTypeSpec = {"owner":progSpec.getOwnerFromTypeSpec(fieldDefFind['typeSpec']), "fieldType":progSpec.fieldTypeKeyword(fieldDefFind['typeSpec'])}
            retVal['itrTypeSpec'] = itrTypeSpec
        return retVal

    def chooseStructImplementationToUse(self, typeSpec,className,fieldName):
        fieldType = progSpec.getFieldType(typeSpec)
        if not isinstance(fieldType, str) and  len(fieldType) >1:
            ctnrCat = fieldType[0]
            if ('chosenType' in fieldType):
                return(None, None, None)
            implOptions = progSpec.getImplementationOptionsFor(ctnrCat)
            if(implOptions == None):
                if ctnrCat=="List" or ctnrCat=="Map" or ctnrCat=="Multimap" :
                    print("******WARNING: no implementation options found for container ", ctnrCat ,className,"::",fieldName)
                    # Check to confirm container type is in features needed
            else:
                reqTags = progSpec.getReqTags(fieldType)
                hiScoreVal = -1
                hiScoreName = None
                for option in implOptions:
                    optionClassDef =  progSpec.findSpecOf(self.classStore[0], option, "struct")
                    if 'tags' in optionClassDef and 'specs' in optionClassDef['tags']:
                        optionTags  = optionClassDef['tags']
                        optionSpecs = optionTags['specs']
                        [implScore, errorMsg] = progSpec.scoreImplementation(optionSpecs, reqTags)
                        if 'native' in optionTags:
                            nativeTag   = optionTags['native']
                            if nativeTag == "lang": implScore += 6
                            if nativeTag == "platform": implScore += 5
                        if(errorMsg != ""): cdErr(errorMsg)
                        if(implScore > hiScoreVal):
                            hiScoreVal = implScore
                            hiScoreName = optionClassDef['name']
                if hiScoreName != None:
                    fromImpl = self.makeFromImpl(hiScoreName, ctnrCat)
                else: fromImpl = None
                #print("IMPLEMENTS:", ctnrCat, '->', hiScoreName)
                return(hiScoreName,fromImpl)
        return(None, None)
        #    choose highest score and mark the typedef

    def applyStructImplemetation(self, typeSpec,currentObjName,fieldName):
        self.checkForReservedWord(fieldName, currentObjName)
        [structToImplement, fromImpl] = self.chooseStructImplementationToUse(typeSpec,currentObjName,fieldName)
        if(structToImplement != None):
            typeSpec['fieldType'][0] = structToImplement
            if fromImpl != None: typeSpec['fromImplemented']  = fromImpl
        return typeSpec

    def copyFieldType(self, fType):
        if isinstance(fType,str):retVal = copy.copy(fType)
        else:
            retVal=[]
            for prop in fType:retVal.append(copy.copy(prop))
        return retVal

    def copyTypeSpec(self, typeSpec):
        retVal = {}
        for prop in typeSpec:
            if prop=='fieldType': retVal[prop]=self.copyFieldType(typeSpec[prop])
            else: retVal[prop]=copy.copy(typeSpec[prop])
        return retVal

    def copyFields(self, fields):
        retVal = []
        for field in fields:
            copyField = {}
            for prop in field:
                if prop=='typeSpec':
                    copyField[prop] = self.copyTypeSpec(field[prop])
                else:
                    copyField[prop] = copy.copy(field[prop])
            retVal.append(copyField)
        return retVal

    def copyClassDef(self, classDef):
        retVal = {}
        for itm in classDef:
            if itm == "fields":
                retVal[itm] = self.copyFields(classDef[itm])
            elif classDef[itm]==None:
                retVal[itm] = None
            else:
                retVal[itm] = copy.copy(classDef[itm])
        return retVal

    def generateGenericStructName(self, className, reqTagList, genericArgs):
        classDef = progSpec.findSpecOf(self.classStore[0], className, "struct")
        if classDef == None: classDef = progSpec.findSpecOf(self.classStore[0], className, "model")
        if classDef == None: print("NO CLASS DEF FOR: ", className)
        typeArgList  = progSpec.getTypeArgList(className)
        if typeArgList == None: return className
        genericStructName = "__"+className
        if genericArgs == None:
            genericArgs = {}
            count = 0
            for reqTag in reqTagList:
                genericType        = progSpec.getTypeFromTemplateArg(reqTag)
                unwrappedKW        = progSpec.getUnwrappedClassFieldTypeKeyWord(self.classStore, genericType)
                genericStructName += "_"+unwrappedKW
                genericArgs[typeArgList[count]]=reqTag
                count += 1
        else:
            for gArg in genericArgs:
                genericType        = progSpec.getTypeFromTemplateArg(genericArgs[gArg])
                unwrappedKW        = progSpec.getUnwrappedClassFieldTypeKeyWord(self.classStore, genericType)
                genericStructName += "_"+unwrappedKW
        if not genericStructName in self.genericStructsGenerated[1]:
            print("ADD:",genericStructName)
            self.genericStructsGenerated[1].append(genericStructName)
            self.classStore[1].append(genericStructName)
            genericClassDef = self.copyClassDef(classDef)
            if 'implements' in genericClassDef: genericClassDef.pop('implements')
            if 'vFields' in genericClassDef: genericClassDef['vFields'] = None
            if 'tags' in genericClassDef and 'implements' in genericClassDef['tags']:genericClassDef['tags'].pop('implements')
            genericClassDef['name'] = genericStructName
            genericClassDef['genericArgs'] = genericArgs
            for field in genericClassDef["fields"]: # handle constructors and function return types
                typeSpec  = field['typeSpec']
                if 'argList' in typeSpec:
                    fieldName = field['fieldName']
                    fTypeKW = progSpec.fieldTypeKeyword(typeSpec)
                    if typeSpec['reqTagList']:
                        typeSpec['reqTagList'] = reqTagList
                    typeSpec = self.getGenericFieldsTypeSpec(genericArgs, typeSpec)
                    if not isinstance(typeSpec['fieldType'], str) and len(typeSpec['fieldType'])>1:
                        fTypeKW = self.generateGenericStructName(fTypeKW, reqTagList, genericArgs)
                        typeSpec['fieldType'] = [fTypeKW]
                    if fTypeKW == "none": field['fieldName'] = genericStructName
            self.genericStructsGenerated[0][genericStructName] = genericClassDef
            self.classStore[0][genericStructName] = genericClassDef
            previousObjName=self.currentObjName
            self.setUpFlagAndModeFields(self.tagStore, [genericStructName])
            self.currentObjName=previousObjName
        return genericStructName

    def getGenericFieldsTypeSpec(self, genericArgs, typeSpec):
        if genericArgs == None: return typeSpec
        fTypeKW = progSpec.fieldTypeKeyword(typeSpec)
        if fTypeKW in genericArgs:
            typeSpec = self.copyTypeSpec(typeSpec)
            genericType = genericArgs[fTypeKW]
            fTypeOut    = progSpec.getTypeFromTemplateArg(genericType)
            ownerOut    = progSpec.getOwnerFromTemplateArg(genericType)
            typeSpec['fieldType'] = fTypeOut
            typeSpec['owner']     = ownerOut
            typeSpec['generic']   = fTypeKW
        return typeSpec

    def getGenericTypeSpec(self, genericArgs, typeSpec):
        fTypeKW = progSpec.fieldTypeKeyword(typeSpec)
        reqTagList = progSpec.getReqTagList(typeSpec)
        if reqTagList and self.xlator.renderGenerics=='True' and not progSpec.isWrappedType(self.classStore, fTypeKW) and not progSpec.isAbstractStruct(self.classStore[0], fTypeKW):
            typeSpecOut = self.copyTypeSpec(typeSpec)
            cvrtType = self.generateGenericStructName(fTypeKW, reqTagList, genericArgs)
            typeSpecOut['fieldType'] = [copy.copy(cvrtType)]
            fromImplIn = progSpec.getFromImpl(typeSpecOut)
            if fromImplIn:
                tArgList = fromImplIn['typeArgList']
                if tArgList:
                    genericArgsOut = progSpec.getGenericArgsFromTypeSpec(typeSpecOut)
                    fromImplIn['genericArgs'] = genericArgsOut
                    for implName in fromImplIn:
                        if implName == 'atTypeSpec' or implName=='atKeyTypeSpec':
                            implSpec  = fromImplIn[implName]
                            implTypeKW = progSpec.fieldTypeKeyword(implSpec)
                            if implTypeKW in genericArgsOut:
                                implSpec['owner']     = genericArgsOut[implTypeKW]['tArgOwner']
                                implSpec['fieldType'] = genericArgsOut[implTypeKW]['tArgType']
                        elif implName=='itrTypeSpec':
                            implSpec  = fromImplIn[implName]
                            if 'fromGeneric' not in implSpec:
                                implTypeKW = progSpec.fieldTypeKeyword(implSpec)
                                implSpec['fieldType'] = self.generateGenericStructName(implTypeKW, reqTagList, genericArgs)
                                implSpec['fromGeneric'] = True
                    fromImplOut = fromImplIn
                else:
                    fromImplOut = self.makeFromImpl(fTypeKW, fromImplIn['implements'])
                    if fromImplOut['typeArgList']==None: fromImplOut['typeArgList'] = tArgList
                typeSpecOut['fromImplemented'] = fromImplOut
            else:
                fromImplOut = self.makeFromImpl(fTypeKW, '')
                typeSpecOut['fromImplemented'] = fromImplOut
            typeSpecOut['generic'] = True
        else:
            typeSpecOut = self.getGenericFieldsTypeSpec(genericArgs, typeSpec)
        return typeSpecOut

    ########################################################################
    def convertType(self, typeSpec, varMode, actionOrField, genericArgs):
        # varMode is 'var' or 'arg' or 'alloc'. Large items are passed as pointers
        isOldCtnr = progSpec.isOldContainerTempFuncErr(typeSpec, "convertType1", self.xlator.renderGenerics)
        typeSpec  = self.getGenericFieldsTypeSpec(genericArgs, typeSpec)
        ownerIn   = progSpec.getOwnerFromTypeSpec(typeSpec)
        fTypeKW   = progSpec.fieldTypeKeyword(typeSpec)
        unwrappedKW = progSpec.getUnwrappedClassFieldTypeKeyWord(self.classStore, fTypeKW)
        ownerOut  = self.xlator.getUnwrappedClassOwner(self.classStore, typeSpec, fTypeKW, varMode, ownerIn)
        reqTagList = progSpec.getReqTagList(typeSpec)
        if reqTagList and self.xlator.renderGenerics=='True':
            if not progSpec.isWrappedType(self.classStore, fTypeKW) and not progSpec.isAbstractStruct(self.classStore[0], fTypeKW):
                unwrappedKW = self.generateGenericStructName(fTypeKW, reqTagList, genericArgs)
            else:
                reqTagStr   = self.xlator.getReqTagString(self.classStore, typeSpec)
                unwrappedKW = unwrappedKW + reqTagStr
        retVal   = self.xlator.xlateLangType(self.classStore, typeSpec, ownerOut, unwrappedKW, varMode, actionOrField)
        return retVal

    def codeAllocater(self, typeSpec, genericArgs):
        S     = ''
        owner = progSpec.getTypeSpecOwner(typeSpec)
        fieldType = progSpec.fieldTypeKeyword(typeSpec)
        [cvrtType, innerType]  = self.convertType(typeSpec, 'alloc', '', genericArgs)
        S= self.xlator.getCodeAllocStr(cvrtType, owner);
        return S

    def convertNameSeg(self, typeSpecOut, name, paramList, objsRefed, genericArgs):
        newName = typeSpecOut['codeConverter']
        if newName == "":
            cdErr("ERROR: empty codeConverter for: "+name)
        if paramList != None:
            count=1
            for P in paramList:
                oldTextTag='%'+str(count)
                [S2, argTypeSpec]=self.codeExpr(P[0], objsRefed, None, None, 'RVAL', genericArgs)
                if S2!='self':S2 += self.xlator.makePtrOpt(argTypeSpec)
                if(isinstance(newName, str)):
                    newName=newName.replace(oldTextTag, S2)
                else: exit(2)
                count+=1
            paramList=None
        return [newName, paramList]

    ################################  C o d e   E x p r e s s i o n s

    def codeNameSeg(self, segSpec, typeSpecIn, connector, LorR_Val, previousSegName, previousTypeSpec, objsRefed, returnType, LorRorP_Val, genericArgs):
        # if TypeSpecIn has 'dummyType', this is a non-member (or self) and the first segment of the reference.
        # return example: ['getData()', <typeSpec>, <alternate form>, 'OBJVAR']
        S           = ''
        S_alt       = ''
        SRC         = ''
        namePrefix  = ''  # For static_Global vars
        typeSpecOut = {'owner':'', 'fieldType':'void'}
        name        = segSpec[0]
        owner       = progSpec.getTypeSpecOwner(typeSpecIn)
        fTypeKW     = progSpec.fieldTypeKeyword(typeSpecIn)
        isOldCtnr   = progSpec.isOldContainerTempFuncErr(typeSpecIn, 'codeNameSeg1 '+self.currentObjName+' ' +str(name), self.xlator.renderGenerics)
        isNewCtnr   = progSpec.isAContainer(typeSpecIn)
        isContainer = isOldCtnr or isNewCtnr

        paramList   = None
        if len(segSpec) > 1 and segSpec[1]=='(':
            if(len(segSpec)==2):
                paramList=[]
            else:
                paramList=segSpec[2]

        if (fTypeKW!=None and not isContainer):
            if fTypeKW=="string":
                [name, tmpTypeSpec] = self.xlator.recodeStringFunctions(name, typeSpecOut)
                typeSpecOut = copy.copy(tmpTypeSpec)

        if owner=='itr':
            fieldTypeOut=progSpec.fieldTypeKeyword(typeSpecIn)
            codeCvrtText = self.xlator.codeIteratorOperation(name, fieldTypeOut)
            if codeCvrtText!='':
                if name=='key':
                    [valOwner, valFieldType] = progSpec.getContainerKeyOwnerAndType(typeSpecIn)
                    typeSpecOut={'owner':valOwner, 'fieldType': valFieldType}
                elif name=='val':
                    [valOwner, valFieldType] = progSpec.getContainerValueOwnerAndType(typeSpecIn)
                    typeSpecOut={'owner':valOwner, 'fieldType': valFieldType}
                else:
                    typeSpecOut = copy.copy(typeSpecIn)
                    if typeSpecOut['owner']=='itr': typeSpecOut['owner']='me'
                typeSpecOut['codeConverter'] = codeCvrtText

        elif isOldCtnr or (isNewCtnr and name[0]=='['):
            [containerType, idxTypeSpec, owner]=self.xlator.getContainerType(typeSpecIn, '')
            [valOwner, valFieldType]=progSpec.getContainerValueOwnerAndType(typeSpecIn)
            typeSpecOut={'owner':valOwner, 'fieldType': valFieldType}
            if(name[0]=='['):
                [S2, idxTypeSpec] = self.codeExpr(name[1], objsRefed, None, None, LorRorP_Val, genericArgs)
                S += self.xlator.codeArrayIndex(S2, containerType, LorR_Val, previousSegName, idxTypeSpec)
                return [S, typeSpecOut, S2,'']
            progSpec.isOldContainerTempFuncErr(typeSpecOut, 'codeNameSeg2' +self.currentObjName+' '+str(name), self.xlator.renderGenerics)
            [name, tmpTypeSpec, paramList, convertedIdxType]= self.xlator.getContainerTypeInfo(containerType, name, idxTypeSpec, typeSpecOut, paramList, genericArgs)
            typeSpecOut = copy.copy(tmpTypeSpec)

        elif ('dummyType' in typeSpecIn): # This is the first segment of a name
            if name=="return":
                SRC = "RETURN_TYPE"
                typeSpecOut['argList'] = [{'typeSpec':returnType}]
            elif(name=='resetFlagsAndModes'):
                typeSpecOut={'owner':'me', 'fieldType': 'void', 'codeConverter':'flags=0'}
                # TODO: if flags or modes have a non-zero default this should account for that.
            else:
                [typeSpecOut, SRC]=self.fetchItemsTypeSpec(segSpec, objsRefed, genericArgs) # Possibly adds a codeConversion to typeSpecOut
                if typeSpecOut: typeSpecOut = self.getGenericTypeSpec(genericArgs, typeSpecOut)
                if self.xlator.doesLangHaveGlobals=='False':
                    if typeSpecOut and 'isGlobalEnum' in typeSpecOut and typeSpecOut['isGlobalEnum']:namePrefix = progSpec.fieldTypeKeyword(typeSpecOut)+ '.'
                    elif(SRC=="GLOBAL"): namePrefix = self.xlator.GlobalVarPrefix
                    elif name in self.modeStateNames and self.modeStateNames[name]=='modeStrings': namePrefix = self.xlator.GlobalVarPrefix+self.modeStateNames[name]+'.'
            if(SRC[:6]=='STATIC'): namePrefix = SRC[7:];
        else:
            if isNewCtnr == True: fType = progSpec.fieldTypeKeyword(typeSpecIn['fieldType'][0])
            else: fType=progSpec.fieldTypeKeyword(fTypeKW)
            if(name=='allocate'):
                S_alt=' = '+self.codeAllocater(typeSpecIn, genericArgs)
                typeSpecOut={'owner':'me', 'fieldType': 'void'}
            elif(name=='resetFlagsAndModes'):
                typeSpecOut={'owner':'me', 'fieldType': 'void', 'codeConverter':'flags=0'}
                # TODO: if flags or modes have a non-zero default this should account for that.
            elif(name[0]=='[' and fType=='string'):
                typeSpecOut={'owner':owner, 'fieldType': 'char'}
                [S2, idxTypeSpec] = self.codeExpr(name[1], objsRefed, None, None, 'RVAL', genericArgs)
                S += self.xlator.codeArrayIndex(S2, 'string', LorR_Val, previousSegName, idxTypeSpec)
                return [S, typeSpecOut, S2, '']  # Here we return S2 for use in code forms other than [idx]. e.g. f(idx)
            elif(name[0]=='[' and (fType=='uint' or fType=='int')):
                print("Error: integers can't be indexed: ", previousSegName,  ":", name)
                exit(2)
            else:
                if fType!='string':
                    [argListStr, fieldIDArgList] = self.getFieldIDArgList(segSpec, objsRefed, genericArgs)
                    typeSpecOut = self.CheckObjectVars(fType, name, fieldIDArgList)
                    if typeSpecOut!=0:
                        typeSpecOut = self.copyTypeSpec(self.getGenericTypeSpec(genericArgs, typeSpecOut['typeSpec']))
                        if isNewCtnr == True:
                            segTypeKeyWord = progSpec.fieldTypeKeyword(typeSpecOut)
                            segTypeOwner   = progSpec.getOwnerFromTypeSpec(typeSpecOut)
                            [innerTypeOwner, innerTypeKeyWord] = progSpec.queryTagFunction(self.classStore, fType, "__getAt", segTypeKeyWord, typeSpecIn)
                            if(innerTypeOwner and segTypeOwner != 'itr'):
                                typeSpecOut['owner'] = innerTypeOwner
                            if(innerTypeKeyWord):
                                typeSpecOut['fieldType'][0] = innerTypeKeyWord
                        typeSpecOut = self.copyTypeSpec(typeSpecOut)
                    else: print("typeSpecOut = 0 for: "+previousSegName+"."+name, " fType:",fType)

        if typeSpecOut and 'codeConverter' in typeSpecOut:
            [convertedName, paramList]=self.convertNameSeg(typeSpecOut, name, paramList, objsRefed, genericArgs)
            typeSpecOutKeyWord = progSpec.fieldTypeKeyword(typeSpecOut)
            reqTagList = progSpec.getReqTagList(typeSpecIn)
            if typeSpecOutKeyWord == "keyType":
                if typeSpecOut['owner']!="itr":typeSpecOut['owner'] = progSpec.getOwnerFromTemplateArg(reqTagList[0])
                typeSpecOut['fieldType'] = progSpec.getTypeFromTemplateArg(reqTagList[0])
            elif typeSpecOutKeyWord == "valueType":
                if typeSpecOut['owner']!="itr":typeSpecOut['owner'] = progSpec.getOwnerFromTemplateArg(reqTagList[1])
                typeSpecOut['fieldType'] = progSpec.getTypeFromTemplateArg(reqTagList[1])
            if "%T0Type" in convertedName:
                if(reqTagList != None):
                    T0Type  = progSpec.getTypeFromTemplateArg(reqTagList[0])
                    T0Type  = progSpec.getUnwrappedClassFieldTypeKeyWord(self.classStore, T0Type)
                    T0Type  = self.xlator.adjustBaseTypes(T0Type)
                    T0Owner = progSpec.getOwnerFromTemplateArg(reqTagList[0])
                    T0Type  = self.xlator.applyOwner(typeSpecOut, T0Owner, T0Type)
                    convertedName = convertedName.replace("%T0Type",T0Type)
                else: cdErr("ERROR: looking for T0Type in codeConverter but reqTagList found in TypeSpec.")
            if "%T1Type" in convertedName:
                if(reqTagList != None):
                    T1Type  = progSpec.getTypeFromTemplateArg(reqTagList[1])
                    T1Type  = progSpec.getUnwrappedClassFieldTypeKeyWord(self.classStore, T1Type)
                    T1Type  = self.xlator.adjustBaseTypes(T1Type)
                    T1Owner = progSpec.getOwnerFromTemplateArg(reqTagList[1])
                    T1Type  = self.xlator.applyOwner(typeSpecOut, T1Owner, T1Type)
                    convertedName = convertedName.replace("%T1Type",T1Type)
                else: cdErr("ERROR: looking for T1Type in codeConverter but reqTagList found in TypeSpec.")
            #print("codeConverter ",name,"->",convertedName, typeSpecOut)
            name = convertedName
            callAsGlobal=name.find("%G")
            if(callAsGlobal >= 0): namePrefix=''

        if S_alt=='': S+=namePrefix+connector+name
        else: S += S_alt

        # Add parameters if this is a function call
        if(paramList != None):
            modelParams=None
            if typeSpecOut and ('argList' in typeSpecOut): modelParams=typeSpecOut['argList'];
            [CPL, paramTypeList] = self.codeParameterList(name, paramList, modelParams, objsRefed, genericArgs)
            if self.xlator.renameInitFuncs=='True' and name=='init':
                if not 'dummyType' in typeSpecIn:
                    fTypeKW=progSpec.fieldTypeKeyword(typeSpecIn)
                else: fTypeKW=self.currentObjName
                S=S.replace('init','__INIT_'+fTypeKW)
            S+= CPL
        if(typeSpecOut==None): cdlog(logLvl(), "Type for {} was not found.".format(name))
        return [S,  typeSpecOut, None, SRC]

    def codeUnknownNameSeg(self, segSpec, objsRefed, genericArgs):
        S=''
        paramList=None
        segName=segSpec[0]
        segConnector = ''
        if(len(segSpec)>1):
            segConnector = self.xlator.NameSegFuncConnector
        else:
            segConnector = self.xlator.NameSegConnector
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
                [CPL, paramTypeList] = self.codeParameterList("", paramList, None, objsRefed, genericArgs)
                S+= CPL
        print("UNKNOWN NAME SEGMENT:", S)
        return S;

    #### codeItemRef ##################################################
    def codeItemRef(self, name, LorR_Val, objsRefed, returnType, LorRorP_Val, genericArgs):
        # Returns information related to a variable, function, etc.
        # NOTE: objsRefed is used to accumulate a list of which vars are read and/or written by a function.
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
        numNameSegs = len(name)
        for segSpec in name:
            LHSParentType='#'
            owner=progSpec.getTypeSpecOwner(segTypeSpec)
            segName=segSpec[0]
            isLastSeg = numNameSegs == segIDX+1
            if(segIDX>0):
                # Detect connector to use '.' '->', '', (*...).
                connector='.'
                if(segTypeSpec): # This is where to detect type of vars not found to determine whether to use '.' or '->'
                    if 'StaticMode' in segTypeSpec and segTypeSpec['StaticMode']=='yes':
                        connector = self.xlator.ObjConnector
                    elif progSpec.wrappedTypeIsPointer(self.classStore, segTypeSpec, segName):
                        connector = self.xlator.PtrConnector
                        if previousSegName and previousSegName[-1] == ']' and connector=='!.':
                            connector = self.xlator.ObjConnector

            AltFormat=None
            if segTypeSpec!=None:
                if segTypeSpec and 'fieldType' in segTypeSpec:
                    LHSParentType = progSpec.fieldTypeKeyword(segTypeSpec)
                else: LHSParentType = progSpec.fieldTypeKeyword(self.currentObjName)   # Landed here because this is the first segment
                [segStr, segTypeSpec, AltIDXFormat, nameSource]=self.codeNameSeg(segSpec, segTypeSpec, connector, LorR_Val, previousSegName, previousTypeSpec, objsRefed, returnType, LorRorP_Val, genericArgs)
                if nameSource!='': canonicalName+=nameSource
                if AltIDXFormat!=None:
                    AltFormat=[S, previousTypeSpec, AltIDXFormat]   # This is in case of an alternate index format such as Java's string.put(idx, val)
            else:
                segStr= self.codeUnknownNameSeg(segSpec, objsRefed, genericArgs)
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
                lenConnector = len(connector)
                if S[:lenConnector]==connector: S=S[lenConnector:]
            else: S+=segStr


            # Language specific dereferencing of ->[...], etc.
            S = self.xlator.LanguageSpecificDecorations(S, segTypeSpec, owner, LorRorP_Val)

            objsRefed[canonicalName]=0
            previousSegName = segName
            previousTypeSpec = segTypeSpec
            segIDX+=1

        # Handle cases where seg's type is flag or mode
        if segTypeSpec and LorR_Val=='RVAL' and 'fieldType' in segTypeSpec:
            fieldType=progSpec.fieldTypeKeyword(segTypeSpec)
            if fieldType=='flag':
                segName=segStr[len(connector):]
                prefix = self.staticVarNamePrefix(segName, LHSParentType)
                bitfieldMask=self.xlator.applyTypecast('uint64', prefix+segName)
                flagReadCode = '('+S[0:prevLen] + connector + 'flags & ' + bitfieldMask+')'
                S=self.xlator.applyTypecast('uint64', flagReadCode)
            elif fieldType=='mode':
                segName=segStr[len(connector):]
                prefix = self.staticVarNamePrefix(segName+"Mask", LHSParentType)
                bitfieldMask  =self.xlator.applyTypecast('uint64', prefix+segName+"Mask")
                bitfieldOffset=self.xlator.applyTypecast('uint64', prefix+segName+"Offset")
                S="((" + S[0:prevLen] + connector +  "flags&"+bitfieldMask+")"+">>"+bitfieldOffset+')'
                S=self.xlator.applyTypecast('uint64', S)

        return [S, segTypeSpec, LHSParentType, AltFormat]

    def codeUserMesg(self, item):
        # TODO: Make 'user messages'interpolate and adjust for locale.
        S=''; fmtStr=''; argStr='';
        pos=0
        for m in re.finditer(r"%[ilscp]`.+?`", item):
            fmtStr += item[pos:m.start()+2]
            argStr += ', ' + item[m.start()+3:m.end()-1]
            pos=m.end()
        fmtStr += item[pos:]
        fmtStr=fmtStr.replace('"', r'\"')
        S=self.xlator.langStringFormatterCommand(fmtStr, argStr)
        return S

    def codeParameterList(self, name, paramList, modelParams, objsRefed, genericArgs):
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
                [S2, argTypeSpec]=self.codeExpr(P[0], objsRefed, None, None, 'PARAM', genericArgs)
                paramTypeList.append(argTypeSpec)
                if modelParams and (len(modelParams)>count) and ('typeSpec' in modelParams[count]):
                    paramTypeSpec  = modelParams[count]['typeSpec']
                    if name == 'return' and S2 == 'nil':  # Swift return nil, provide context and make optional
                        paramTypeKW = progSpec.fieldTypeKeyword(paramTypeSpec)
                        S2 = paramTypeKW +"?("+S2+")"
                    else:
                        [leftMod, rightMod] = self.xlator.chooseVirtualRValOwner(paramTypeSpec, argTypeSpec)
                        S2 = leftMod+S2+rightMod
                    S += S2
                else:
                    self.listOfFuncsWithUnknownArgTypes[(name+'()')]=1
                    S += S2
                count+=1
            S='(' + S + ')'
        return [S, paramTypeList]

    #################################################################
    def codeTerm(self, item, objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec]=self.xlator.codeFactor(item[0], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if (not(isinstance(item, str))) and (len(item) > 1) and len(item[1])>0:
            [S, isDerefd]=self.xlator.derefPtr(S, retTypeSpec)
            for i in item[1]:
                #print '               term:', i
                if   (i[0] == '*'): S+=' * '
                elif (i[0] == '/'): S+=' / '
                elif (i[0] == '%'): S+=' % '
                else: print("ERROR: One of '*', '/' or '%' expected in code generator."); exit(2)
                [S2, retType2] = self.xlator.codeFactor(i[1], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                [S2, isDerefd]=self.xlator.derefPtr(S2, retType2)
                S+=S2
        return [S, retTypeSpec]

    def codePlus(self, item, objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec]=self.codeTerm(item[0], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if len(item) > 1 and len(item[1])>0:
            [S, isDerefd]=self.xlator.derefPtr(S, retTypeSpec)
            if isDerefd:
                keyType = progSpec.varTypeKeyWord(retTypeSpec)
                retTypeSpec={'owner': 'me', 'fieldType': keyType}
            for  i in item[1]:
                if   (i[0] == '+'): S+=' + '
                elif (i[0] == '-'): S+=' - '
                else: print("ERROR: '+' or '-' expected in code generator."); exit(2)
                [S2, retType2] = self.codeTerm(i[1], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                [S2, isDerefd]=self.xlator.derefPtr(S2, retType2)
                if i[0]=='+' :S2 = self.xlator.checkForTypeCastNeed('string', retType2, S2)
                S+=S2
        return [S, retTypeSpec]

    def codeComparison(self, item, objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec]=self.codePlus(item[0], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if len(item) > 1 and len(item[1])>0:
            if len(item[1])>1: print("Error: Chained comparisons.\n"); exit(1);
            [S, isDerefd]=self.xlator.derefPtr(S, retTypeSpec)
            for i in item[1]:
                [S2, retType2] = self.codePlus(i[1], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                S = self.xlator.codeComparisonStr(S, S2, retTypeSpec, retType2, i[0])
                retTypeSpec = {'owner': 'me', 'fieldType': 'bool'}
        return [S, retTypeSpec]

    def codeIsEQ(self, item, objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec]=self.codeComparison(item[0], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if len(item) > 1 and len(item[1])>0:
            if len(item[1])>1: print("Error: Chained == or !=.\n"); exit(1);
            if (isinstance(retTypeSpec, int)): cdlog(logLvl(), "Invalid item in ==: {}".format(item[0]))
            for i in item[1]:
                [S2, retType2] = self.codeComparison(i[1], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                S  = self.xlator.codeIdentityCheck(S, S2, retTypeSpec, retType2, i[0])
                retTypeSpec = {'owner': 'me', 'fieldType': 'bool'}
        return [S, retTypeSpec]

    def codeBitwiseAnd(self, item, objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec] = self.codeIsEQ(item[0], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if len(item) > 1 and len(item[1])>0:
            if (isinstance(retTypeSpec, int)): cdlog(logLvl(), "Invalid item in ==: {}".format(item[0]))
            [S_derefd, isDerefd] = self.xlator.derefPtr(S, retTypeSpec)
            S = self.xlator.convertToInt(S, retTypeSpec)
            for i in item[1]:
                [S2, retType2] = self.codeIsEQ(i[1], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                S2 = self.xlator.convertToInt(S2, retType2)
                S+= ' & '+S2
        return [S, retTypeSpec]

    def codeBitwiseXOR(self, item, objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec]=self.codeBitwiseAnd(item[0], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if len(item) > 1 and len(item[1])>0:
            if (isinstance(retTypeSpec, int)): cdlog(logLvl(), "Invalid item in ==: {}".format(item[0]))
            [S_derefd, isDerefd] = self.xlator.derefPtr(S, retTypeSpec)
            for i in item[1]:
                [S2, retType2] = self.codeBitwiseAnd(i[1], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                S+= ' ^ '+S2
        return [S, retTypeSpec]

    def codeBitwiseOr(self, item, objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec] = self.codeBitwiseXOR(item[0], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if len(item) > 1 and len(item[1])>0:
            if (isinstance(retTypeSpec, int)): cdlog(logLvl(), "Invalid item in ==: {}".format(item[0]))
            [S_derefd, isDerefd] = self.xlator.derefPtr(S, retTypeSpec)
            for i in item[1]:
                [S2, retType2] = self.codeBitwiseXOR(i[1], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                S+= ' | '+S2
        return [S, retTypeSpec]

    def codeLogicalAnd(self, item, objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec] = self.codeBitwiseOr(item[0], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if len(item) > 1 and len(item[1])>0:
            [S, isDerefd]=self.xlator.derefPtr(S, retTypeSpec)
            for i in item[1]:
                if (i[0] == 'and'):
                    S = self.xlator.checkForTypeCastNeed('bool', retTypeSpec, S)
                    [S2, retTypeSpec] = self.codeBitwiseOr(i[1], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                    S2 = self.xlator.checkForTypeCastNeed('bool', retTypeSpec, S2)
                    [S2, isDerefd]=self.xlator.derefPtr(S2, retTypeSpec)
                    S+=' && ' + S2
                else: print("ERROR: 'and' expected in code generator."); exit(2)
                retTypeSpec = {'owner': 'me', 'fieldType': 'bool'}
        return [S, retTypeSpec]

    def codeLogicalOr(self, item, objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec] = self.codeLogicalAnd(item[0], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if len(item) > 1 and len(item[1])>0:
            [S, isDerefd]=self.xlator.derefPtr(S, retTypeSpec)
            for i in item[1]:
                if (i[0] == 'or'):
                    S = self.xlator.checkForTypeCastNeed('bool', retTypeSpec, S)
                    [S2, retTypeSpec] = self.codeLogicalAnd(i[1], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                    [S2, isDerefd]=self.xlator.derefPtr(S2, retTypeSpec)
                    S2 = self.xlator.checkForTypeCastNeed('bool', retTypeSpec, S2)
                    S+=' || ' + S2
                else: print("ERROR: 'or' expected in code generator."); exit(2)
                retTypeSpec = {'owner': 'me', 'fieldType': 'bool'}
        return [S, retTypeSpec]

    def codeExpr(self, item, objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec] = self.codeLogicalOr(item[0], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if not isinstance(item, str) and len(item) > 1 and len(item[1])>0:
            [S, isDerefd]=self.xlator.derefPtr(S, retTypeSpec)
            for i in item[1]:
                if (i[0] == '<-'):
                    [S2, retTypeSpec] = self.codeLogicalOr(i[1], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                    [S2, isDerefd]=self.xlator.derefPtr(S2, retTypeSpec)
                    S+=' = ' + S2
                else: print("ERROR: '<-' expected in code generator."); exit(2)
                retTypeSpec = {'owner': 'me', 'fieldType': 'bool'}
        return [S, retTypeSpec]

    #### ACTIONS ###########################################################
    def codeRepetition(self, action, objsRefed, returnType, indent, genericArgs):
        actionText = ""
        repBody    = action['repBody']
        repName    = action['repName']
        cdlog(5, "Repetition stmt: loop var is:'{}'".format(repName))
        traversalMode = action['traversalMode']
        rangeSpec  = action['rangeSpec']
        whileSpec  = action['whileSpec']
        keyRange   = action['keyRange']
        fileSpec   = False #action['fileSpec']
        ctrType    = self.xlator.typeForCounterInt
        itrIncStr  = ""
        # TODO: add cases for traversing trees and graphs in various orders or ways.
        loopCounterName=''
        if(rangeSpec): # iterate over range
            [S_low, lowValTypeSpec] = self.codeExpr(rangeSpec[2][0], objsRefed, None, None, 'RVAL', genericArgs)
            [S_hi,   hiValTypeSpec] = self.codeExpr(rangeSpec[4][0], objsRefed, None, None, 'RVAL', genericArgs)
            ctrlVarsTypeSpec = lowValTypeSpec
            actionText += self.xlator.codeRangeSpec(traversalMode, ctrType, repName, S_low, S_hi, indent)
            self.localVarsAllocated.append([repName, ctrlVarsTypeSpec])  # Tracking local vars for scope
        elif(whileSpec):
            [whileExpr, whereConditionTypeSpec] = self.codeExpr(whileSpec[2], objsRefed, None, None, 'RVAL', genericArgs)
            [whileExpr, whereConditionTypeSpec] =  self.xlator.adjustConditional(whileExpr, whereConditionTypeSpec)
            actionText += indent + "while(" + whileExpr + "){\n"
            loopCounterName=repName
        elif(fileSpec):
            [filenameExpr, filenameTypeSpec] = self.codeExpr(fileSpec[2], objsRefed, None, None, 'RVAL', genericArgs)
            if filenameTypeSpec!='string':
                cdErr("Filename must be a string.\n")
            print("File iteration not implemeted yet.\n")
            exit(2)
        elif(keyRange):
            [ctnrName, containerTSpec] = self.codeExpr(keyRange[0][0], objsRefed, None, None, 'RVAL', genericArgs)
            isOldCtnr = progSpec.isOldContainerTempFuncErr(containerTSpec, 'codeRepetition1 '+self.currentObjName+' '+ctnrName, self.xlator.renderGenerics)
            [StartKey, StartTypeSpec] = self.codeExpr(keyRange[2][0], objsRefed, None, None, 'RVAL', genericArgs)
            [EndKey,   EndTypeSpec] = self.codeExpr(keyRange[4][0], objsRefed, None, None, 'RVAL', genericArgs)
            [datastructID, idxTypeKW, ctnrOwner]=self.xlator.getContainerType(containerTSpec, '')
            wrappedTypeSpec = progSpec.isWrappedType(self.classStore, progSpec.fieldTypeKeyword(containerTSpec)[0])
            if(wrappedTypeSpec != None):containerTSpec=wrappedTypeSpec
            [actionTextOut, loopCounterName] = self.xlator.iterateRangeFromTo(self.classStore,self.localVarsAllocated, StartKey, EndKey, containerTSpec,repName,ctnrName,indent)
            actionText += actionTextOut
        else: # interate over a container
            [ctnrName, containerTSpec] = self.codeExpr(action['repList'][0], objsRefed, None, None, 'RVAL', genericArgs)
            isOldCtnr = progSpec.isOldContainerTempFuncErr(containerTSpec, 'codeRepetition2 '+self.currentObjName+' '+ctnrName, self.xlator.renderGenerics)
            isNewCtnr = progSpec.isAContainer(containerTSpec)
            isContainer = isOldCtnr or isNewCtnr
            if containerTSpec==None or not isContainer: cdErr("'"+ctnrName+"' is not a container so cannot be iterated over."+str(containerTSpec))
            if(traversalMode=='Forward' or traversalMode==None):
                isBackward=False
            elif(traversalMode=='Backward'):
                isBackward=True
            [actionTextOut, loopCounterName, itrIncStr] = self.xlator.iterateContainerStr(self.classStore,self.localVarsAllocated,containerTSpec,repName,ctnrName, isBackward, indent, genericArgs)
            actionText += actionTextOut
        if action['whereExpr']:
            [whereExpr, whereConditionTypeSpec] = self.codeExpr(action['whereExpr'], objsRefed, None, None, 'RVAL', genericArgs)
            actionText += indent + "    " + 'if (!' + whereExpr + ') continue;\n'
        if action['untilExpr']:
            [untilExpr, untilConditionTypeSpec] = self.codeExpr(action['untilExpr'], objsRefed, None, None, 'RVAL', genericArgs)
            actionText += indent + '    ' + 'if (' + untilExpr + ') break;\n'
        repBodyText = ''
        for repAction in repBody:
            actionOut = self.codeAction(repAction, indent + "    ", objsRefed, returnType, genericArgs)
            repBodyText += actionOut
        if loopCounterName!='':
            actionText=indent + ctrType+" " + loopCounterName + "=0;\n" + actionText
            repBodyText += indent + "    " + self.xlator.codeIncrement(loopCounterName) + ";\n"
            ctrlVarsTypeSpec = {'owner':'me', 'fieldType':'uint'}
            self.localVarsAllocated.append([loopCounterName, ctrlVarsTypeSpec])  # Tracking local vars for scope
        actionText += repBodyText + itrIncStr + indent + '}\n'
        return actionText

    def codeFuncCall(self, funcCallSpec, objsRefed, returnType, genericArgs):
        S=''
        [codeStr, typeSpec, LHSParentType, AltIDXFormat]=self.codeItemRef(funcCallSpec, 'RVAL', objsRefed, returnType, 'RVAL', genericArgs)
        S+=codeStr
        return S

    def startPointOfNamesLastSegment(self, name):
        p=len(name)-1
        while(p>0):
            if name[p]=='>' or name[p]=='.':
                return p
            p-=1
        return -1

    def genIfBody(self, ifBody, indent, objsRefed, returnType, genericArgs):
        ifBodyText = ""
        for ifAction in ifBody:
            actionOut = self.codeAction(ifAction, indent + "    ", objsRefed, returnType, genericArgs)
            ifBodyText += actionOut
        return ifBodyText

    def codeCriticalSection(self, criticalSection, indent, objsRefed, returnType, genericArgs):
        criticalText = ""
        for criticalStmt in criticalSection:
            actionOut = self.codeAction(criticalStmt, indent + "    ", objsRefed, returnType, genericArgs)
            criticalText += actionOut
        return criticalText

    def encodeConditionalStatement(self, action, indent, objsRefed, returnType, genericArgs):
        [S2, conditionTypeSpec] =  self.codeExpr(action['ifCondition'][0], objsRefed, None, None, 'RVAL', genericArgs)
        [S2, conditionTypeSpec] =  self.xlator.adjustConditional(S2, conditionTypeSpec)
        ifCondition = S2
        ifBodyText = self.genIfBody(action['ifBody'], indent, objsRefed, returnType, genericArgs)
        actionText =  indent + "if (" + ifCondition + ") " + "{\n" + ifBodyText + indent + "}\n"
        elseBodyText = ""
        elseBody = action['elseBody']
        if (elseBody):
            if (elseBody[0]=='if'):
                elseAction = elseBody[1]
                elseText = self.encodeConditionalStatement(elseAction[0], indent, objsRefed, returnType, genericArgs)
                actionText += indent + "else " + elseText.lstrip()
            elif (elseBody[0]=='action'):
                elseAction = elseBody[1]['actionList']
                elseText = self.codeActionSeq(elseAction, indent, objsRefed, returnType, genericArgs)
                actionText += indent + "else " + elseText.lstrip()
            else:  print("Unrecognized item after else"); exit(2);
        return actionText

    #### codeAction ##################################################
    def codeAction(self, action, indent, objsRefed, returnType, genericArgs):
        #make a string and return it
        actionText = ""
        action['sideEffects']=[]
        typeOfAction = action['typeOfAction']

        if (typeOfAction =='newVar'):
            fieldDef = action['fieldDef']
            typeSpec  = fieldDef['typeSpec']
            fieldName = fieldDef['fieldName']
            isOldCtnr = progSpec.isOldContainerTempFuncErr(typeSpec, 'codeAction '+self.currentObjName+' '+fieldName, self.xlator.renderGenerics)
            self.applyStructImplemetation(typeSpec,self.currentObjName,fieldName)
            cdlog(5, "Action newVar: {}".format(fieldName))
            varDeclareStr = self.xlator.codeNewVarStr(self.classStore, self.tagStore, typeSpec, fieldName, fieldDef, indent, objsRefed, 'action', genericArgs, self.localVarsAllocated)
            actionText = indent + varDeclareStr + ";\n"
        elif (typeOfAction =='assign'):
            cdlog(5, "PREASSIGN:" + str(action['LHS']))
            # Note: In Java, string A[x]=B must be coded like: A.put(B,x)
            cdlog(5, "Pre-assignment... ")
            [LHS, lhsTypeSpec, LHSParentType, AltIDXFormat] = self.codeItemRef(action['LHS'], 'LVAL', objsRefed, returnType, 'LVAL', genericArgs)
            assignTag = action['assignTag']
            cdlog(5, "Assignment: {}".format(LHS))
            [S2, rhsTypeSpec]=self.codeExpr(action['RHS'][0], objsRefed, None, lhsTypeSpec, 'RVAL', genericArgs)
            [LHS_leftMod, LHS_rightMod,  RHS_leftMod, RHS_rightMod]=self.xlator.determinePtrConfigForAssignments(lhsTypeSpec, rhsTypeSpec, assignTag,LHS)
            LHS = LHS_leftMod+LHS+LHS_rightMod
            RHS = RHS_leftMod+S2+RHS_rightMod
            cdlog(5, "Assignment: {} = {}".format(lhsTypeSpec, rhsTypeSpec))
            RHS = self.xlator.checkForTypeCastNeed(lhsTypeSpec, rhsTypeSpec, RHS)
            if not isinstance (lhsTypeSpec, dict):
                #TODO: make test case
                print('Problem: lhsTypeSpec is', lhsTypeSpec, '\n');
                LHS_FieldType='string'
            else: LHS_FieldType=progSpec.fieldTypeKeyword(lhsTypeSpec)

            if assignTag == '':
                if LHS_FieldType=='flag':
                    divPoint=self.startPointOfNamesLastSegment(LHS)
                    LHS_Left=LHS[0:divPoint+1] # The '+1' makes this get the connector too. e.g. '.' or '->'
                    bitMask =LHS[divPoint+1:]
                    prefix = self.staticVarNamePrefix(bitMask, LHSParentType)
                    setBits = self.xlator.codeSetBits(LHS_Left, LHS_FieldType, prefix, bitMask, RHS, rhsTypeSpec)
                    actionText=indent + setBits
                elif LHS_FieldType=='mode':
                    divPoint=self.startPointOfNamesLastSegment(LHS)
                    if (divPoint == 0):
                        LHS_Left=""
                        bitMask =LHS
                    else:
                        LHS_Left=LHS[0:divPoint+1]
                        bitMask =LHS[divPoint+1:]
                    prefix = self.staticVarNamePrefix(bitMask+"Mask", LHSParentType)
                    setBits = self.xlator.codeSetBits(LHS_Left, LHS_FieldType, prefix, bitMask, RHS, rhsTypeSpec)
                    actionText=indent + setBits
                else:
                    if AltIDXFormat!=None:
                        # Handle special forms of assignment such as LVal(idx, RVal)
                        actionText = self.xlator.checkIfSpecialAssignmentFormIsNeeded(AltIDXFormat, RHS, rhsTypeSpec, LHS, LHSParentType, LHS_FieldType)
                        if actionText != '': actionText = indent+actionText
                    if actionText=="":
                        # Handle the normal assignment case
                        if RHS=='nil' and LHS[-1]=='!': LHS=LHS[:-1]  #TODO: Move this code to swift self.xlator
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
            typeSpec   = self.fetchItemsTypeSpec(LHS, objsRefed, genericArgs)
            [LCvrtType, innerType] = self.convertType(typeSpec[0], 'var', 'action', genericArgs)
            typeSpec   = self.fetchItemsTypeSpec(RHS, objsRefed, genericArgs)
            LHS = LHS[0]
            RHS = RHS[0]
            actionText = indent + LCvrtType + " tmp = " + LHS + ";\n"
            actionText += indent + LHS + " = " + RHS + ";\n"
            actionText += indent + RHS + " = " + "tmp;\n"
        elif (typeOfAction =='conditional'):
            cdlog(5, "If-statement...")
            [S2, conditionTypeSpec] =  self.codeExpr(action['ifCondition'][0], objsRefed, None, None, 'RVAL', genericArgs)
            if conditionTypeSpec==None: cdErr("Found typeSpec None in codeAction():   "+S2)
            [S2, conditionTypeSpec] =  self.xlator.adjustConditional(S2, conditionTypeSpec)
            cdlog(5, "If-statement: Condition is ".format(S2))
            ifCondition = S2
            ifBodyText = self.genIfBody(action['ifBody'], indent, objsRefed, returnType, genericArgs)
            actionText =  indent + "if (" + ifCondition + ") " + "{\n" + ifBodyText + indent + "}\n"
            elseBodyText = ""
            elseBody = action['elseBody']
            if (elseBody):
                if (elseBody[0]=='if'):
                    elseAction = elseBody[1][0]
                    elseText = self.encodeConditionalStatement(elseAction, indent, objsRefed, returnType, genericArgs)
                    actionText += indent + "else " + elseText.lstrip()
                elif (elseBody[0]=='action'):
                    elseAction = elseBody[1]['actionList']
                    elseText = self.codeActionSeq(elseAction, indent, objsRefed, returnType, genericArgs)
                    actionText += indent + "else " + elseText.lstrip()
                else:  print("Unrecognized item after else"); exit(2);
        elif (typeOfAction =='repetition'):
            actionText = self.codeRepetition(action, objsRefed, returnType, indent, genericArgs)
        elif (typeOfAction =='funcCall'):
            calledFunc = action['calledFunc']
            if calledFunc[0][0] == 'if' or calledFunc=='withEach' or calledFunc=='until' or calledFunc=='where':
                print("\nERROR: It is not allowed to name a function", calledFunc[0][0])
                exit(2)
            cdlog(5, "Function Call: {}()".format(str(calledFunc[0][0])))
            funcCallText = self.codeFuncCall(calledFunc, objsRefed, returnType, genericArgs)
            funcCallTextStriped = funcCallText.strip()
            if (funcCallTextStriped!=''):
                actionText = indent + funcCallText + ';\n'
        elif (typeOfAction == 'switchStmt'):
            cdlog(5, "Switch statement: switch({})".format(str(action['switchKey'])))
            [switchKeyExpr, switchKeyTypeSpec] = self.codeExpr(action['switchKey'][0], objsRefed, None, None, 'RVAL', genericArgs)
            actionText += indent+"switch("+ self.xlator.codeSwitchExpr(switchKeyExpr, switchKeyTypeSpec)  + "){\n"
            blockPrefix = self.xlator.blockPrefix
            for sCases in action['switchCases']:
                actionText += indent
                for sCase in sCases[0]:
                    [caseKeyValue, caseKeyTypeSpec] = self.codeExpr(sCase[0], objsRefed, None, None, 'RVAL', genericArgs)
                    actionText += "    case "+self.xlator.codeSwitchCase(caseKeyValue, caseKeyTypeSpec)+": "
                caseAction = sCases[1]
                actionText += blockPrefix + self.codeActionSeq(caseAction, indent+'    ', objsRefed, returnType, genericArgs)
                actionText += self.xlator.codeSwitchBreak(caseAction, indent)
            defaultCase=action['defaultCase']
            if defaultCase and len(defaultCase)>0:
                actionText+=indent+"default: "
                actionText += blockPrefix + self.codeActionSeq(defaultCase, indent, objsRefed, returnType, genericArgs)
            else: actionText+=indent+"default: break;\n"
            actionText += indent + "}\n"
        elif (typeOfAction =='actionSeq'):
            cdlog(5, "Action Sequence")
            actionListIn = action['actionList']
            actionListText = ''
            for action in actionListIn:
                actionListOut = self.codeAction(action, indent + "    ", objsRefed, returnType, genericArgs)
                actionListText += actionListOut
            blockPrefix = self.xlator.blockPrefix
            actionText += indent + blockPrefix + "{\n" + actionListText + indent + '}\n'
        elif (typeOfAction =='protect'):
            cdlog(5, "Protect Statement")
            mutex           = action['mutex'][0]
            criticalSection = action['criticalSection']
            criticalText    = self.codeCriticalSection(action['criticalSection'], indent, objsRefed, returnType, genericArgs)
            [mutex, mtxTypeSpec]=self.codeExpr(mutex, objsRefed, None, None, 'RVAL', genericArgs)
            actionText = self.xlator.codeProtectBlock(mutex, criticalText, indent)
        else:
            print("error in codeAction: ", action)
            exit(2)
        return actionText

    def codeActionSeq(self, actSeq, indent, objsRefed, returnType, genericArgs):
        self.localVarsAllocated.append(["STOP",''])
        actSeqText=''
        actSeqText += '{\n'
        for action in actSeq:
            actionText = self.codeAction(action, indent + '    ', objsRefed, returnType, genericArgs)
            actSeqText += actionText
        actSeqText += indent + '}\n'
        localVarRecord=['','']
        while(localVarRecord[0] != 'STOP'):
            localVarRecord=self.localVarsAllocated.pop()
        return actSeqText

    #### CONSTRUCTORS ######################################################
    def getCtorArgTypes(self, className, genericArgs):
        ctorArgTypes = []
        count=0
        for field in progSpec.generateListOfFieldsToImplement(self.classStore, className):
            tSpec     = field['typeSpec']
            fType     = progSpec.fieldTypeKeyword(tSpec)
            fOwner    = progSpec.getOwnerFromTypeSpec(tSpec)
            isOldCtnr = progSpec.isOldContainerTempFuncErr(tSpec, 'getCtorArgTypes '+self.currentObjName, self.xlator.renderGenerics)
            isNewCtnr = progSpec.isAContainer(tSpec)
            isContainer = isOldCtnr or isNewCtnr
            if fType=='flag' or fType=='mode' or fOwner=='const' or fOwner == 'we' or (tSpec['argList'] or tSpec['argList']!=None) or (isContainer and not progSpec.typeIsPointer(tSpec)):
                continue
            if(fOwner != 'me' and fOwner != 'my') or (isinstance(fType, str) and ((self.isArgNumeric(fType) or fType=="string") or ('value' in field and field['value']!=None))):
                [cvrtType, innerType] = self.convertType(tSpec, 'var', 'constructor', genericArgs)
                ctorArgTypes.append(cvrtType)
        return ctorArgTypes

    def codeConstructor(self, className, tags, objsRefed, typeArgList, genericArgs):
        baseType = progSpec.isWrappedType(self.classStore, className)
        if(baseType!=None): return ''
        if not className in self.classStore[0]: return ''
        cdlog(4, "Generating Constructor for: {}".format(className))
        ObjectDef = self.classStore[0][className]
        flatClassName = progSpec.flattenObjectName(className)
        genericArgs =  progSpec.getGenericArgs(ObjectDef)
        ctorInit=""
        ctorArgs=""
        copyCtorArgs=""
        count=0
        for field in progSpec.generateListOfFieldsToImplement(self.classStore, className):
            typeSpec =field['typeSpec']
            fieldType=progSpec.fieldTypeKeyword(typeSpec)
            if(fieldType=='flag' or fieldType=='mode'): continue
            if(typeSpec['argList'] or typeSpec['argList']!=None): continue
            isOldCtnr = progSpec.isOldContainerTempFuncErr(typeSpec, 'codeConstructor '+self.currentObjName, self.xlator.renderGenerics)
            isNewCtnr = progSpec.isAContainer(typeSpec)
            isContainer = isOldCtnr or isNewCtnr
            if isContainer and not progSpec.typeIsPointer(typeSpec): continue
            fieldOwner=progSpec.getOwnerFromTypeSpec(typeSpec)
            if(fieldOwner=='const' or fieldOwner == 'we'): continue
            [cvrtType, innerType] = self.convertType(typeSpec, 'var', 'constructor', genericArgs)
            fieldName=field['fieldName']
            if(typeArgList != None and fieldType in typeArgList):isTemplateVar = True
            else: isTemplateVar = False

            cdlog(4, "Coding Constructor: {} {} {} {}".format(className, fieldName, fieldType, cvrtType))
            defaultVal=''
            if(fieldOwner != 'me'):
                if(fieldOwner != 'my'):
                    defaultVal = "NULL"
            elif (isinstance(fieldType, str)):
                if 'value' in field and field['value']!=None:
                    [defaultVal, defaultValueTypeSpec] = self.codeExpr(field['value'][0], objsRefed, None, typeSpec, 'RVAL', genericArgs)
                else:
                    if(self.typeIsInteger(fieldType)):
                        defaultVal = "0"
                    elif(self.typeIsRational(fieldType)):
                        defaultVal = "0.0"
                    elif(fieldType=="string"):
                        defaultVal = '""'
                    else: # handle structs if needed
                        if 'value' in field and field['value']!=None:
                            [defaultVal, defaultValueTypeSpec] = self.codeExpr(field['value'][0], objsRefed, None, typeSpec, 'RVAL', genericArgs)
            if defaultVal != '':
            #    if count == 0: defaultVal = ''  # uncomment this line to NOT generate a default value for the first constructor argument.
                ctorArgs += self.xlator.codeConstructorArgText(fieldName, count, cvrtType, defaultVal)+ ","
                ctorInit += self.xlator.codeConstructorInit(fieldName, count, defaultVal)

                count += 1
            copyCtorArgs += self.xlator.codeCopyConstructor(fieldName, cvrtType, isTemplateVar)

        funcBody    = ''
        ctorCode    = ''
        callSuper   = ''
        ctorOvrRide = ''
        parentClass = ''
        parentClasses = progSpec.getParentClassList(self.classStore, className)
        if parentClasses:
            parentClass = progSpec.filterClassesToString(parentClasses[0])
            callSuper = self.xlator.codeSuperConstructorCall(parentClass)


        fieldID  = className+'::INIT'
        if(progSpec.doesClassDirectlyImlementThisField(self.classStore[0], className, fieldID)):
            funcBody += self.xlator.codeConstructorCall(className)
        if(count>0):
            ctorArgs=ctorArgs[0:-1]
        if ctorArgs and parentClass:
            ctorArgTypes       = self.getCtorArgTypes(className, genericArgs)
            parentCtorArgTypes = self.getCtorArgTypes(parentClass, genericArgs)
            if ctorArgTypes == parentCtorArgTypes:
                ctorOvrRide = 'override '
        if count>0 or funcBody != '':
            ctorCode += self.xlator.codeConstructors(flatClassName, ctorArgs, ctorOvrRide, ctorInit, copyCtorArgs, funcBody, callSuper)
        return ctorCode

    #### STRUCT FIELDS #####################################################
    def codeStructFields(self, className, tags, indent, objsRefed):
        cdlog(3, "Coding fields for {}...".format(className))
        ####################################################################
        funcBodyIndent   = self.xlator.funcBodyIndent
        funcsDefInClass  = self.xlator.funcsDefInClass
        makeCtors = self.xlator.MakeConstructors
        globalFuncsAcc=""
        funcDefCodeAcc=""
        structCodeAcc=""
        topFuncDefCodeAcc="" # For defns that must appear first in the code. TODO: sort items instead
        ObjectDef = self.classStore[0][className]
        typeArgList = progSpec.getTypeArgList(className)
        genericArgs =  progSpec.getGenericArgs(ObjectDef)
        for field in progSpec.generateListOfFieldsToImplement(self.classStore, className):
            ################################################################
            ### extracting FIELD data
            ################################################################
            self.localArgsAllocated= []
            funcDefCode       = ""
            structCode        = ""
            globalFuncs       = ""
            topFuncDefCode    = ""
            funcText          = ""
            fieldID           = field['fieldID']
            typeSpec          = field['typeSpec']
            fieldName         = field['fieldName']
            self.applyStructImplemetation(typeSpec,className,fieldName)
            fieldType=progSpec.fieldTypeKeyword(typeSpec)
            if progSpec.doesClassHaveProperty(self.classStore, fieldType, 'metaClass'):
                tagToFind       = "classOptions."+progSpec.flattenObjectName(fieldID)
                classOptionsTag = progSpec.fetchTagValue(tags, tagToFind)
                if classOptionsTag != None and "useClass" in classOptionsTag:
                    useClassTag     = classOptionsTag["useClass"]
                    fieldType[0]    = useClassTag
            if(fieldType=='flag' or fieldType=='mode'): continue
            isAllocated = field['isAllocated']
            cdlog(4, "FieldName: {}".format(fieldName))
            fieldValue=field['value']
            fieldArglist = typeSpec['argList']
            paramList = field['paramList']
            [intermediateType, innerType] = self.convertType(typeSpec, 'var', 'field', genericArgs)
            cvrtType = progSpec.flattenObjectName(intermediateType)
            typeSpec = self.getGenericTypeSpec(genericArgs, typeSpec)
            fieldOwner=progSpec.getTypeSpecOwner(typeSpec)
            typeDefName = cvrtType # progSpec.createTypedefName(fieldType)
            ## ASSIGNMENTS###############################################

            if 'value' in field and field['value']!=None and len(field['value'])>1:
                verbatimText=field['value'][1]
                if (verbatimText!=''):                                      # This function body is 'verbatim'.
                    if(verbatimText[0]=='!'): # This is a code conversion pattern. Don't write a function decl or body.
                        structCode=""
                        funcText=""
                        funcDefCode=""
                        globalFuncs=""
                        continue

            if fieldName=='opAssign':
                fieldName='operator='

            # CALCULATE RHS
            if(fieldValue == None):
                if className == "GLOBAL" and isAllocated==True: # Allocation for GLOBAL handled in appendGLOBALInitCode()
                    isAllocated = False
                    paramList = None
                fieldValueText=self.xlator.codeVarFieldRHS_Str(fieldName, cvrtType, innerType, typeSpec, paramList, objsRefed, isAllocated, typeArgList, genericArgs)
                #print ("    RHS none: ", fieldValueText)
            elif(fieldOwner=='const'):
                if isinstance(fieldValue, str):
                    fieldValueText = ' = "'+ fieldValue + '"'
                    #TODO:  make test case
                else:
                    fieldValueText = " = "+ self.codeExpr(fieldValue[0], objsRefed, typeSpec, typeSpec, 'RVAL', genericArgs)[0]
                #print ("    RHS const: ", fieldValueText)
            elif(fieldArglist==None):
                fieldValueText = " = " + self.codeExpr(fieldValue[0], objsRefed, typeSpec, typeSpec, 'RVAL', genericArgs)[0]
                #print ("    RHS var: ", fieldValueText)
            else:
                fieldValueText = " = "+ str(fieldValue)
                #print ("    RHS func or array")


            ############ CODE MEMBER VARIABLE ##########################################################
            if(fieldOwner=='const'):
                [structCode, topFuncDefCode] = self.xlator.codeConstField_Str(cvrtType, fieldName, fieldValueText, className, indent)
            elif(fieldArglist==None):
                [structCode, funcDefCode] = self.xlator.codeVarField_Str(cvrtType, typeSpec, fieldName, fieldValueText, className, tags, typeArgList, indent)

            ###### ArgList exists so this is a FUNCTION###########
            else:
                overRideOper = False
                if fieldName[0:2] == "__" and self.xlator.iteratorsUseOperators == "True":
                    fieldName = self.xlator.specialFunction(fieldName)
                    overRideOper = True
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
                        argOwner    =argTypeSpec['owner']
                        argFieldName=arg['fieldName']
                        argFieldType=progSpec.fieldTypeKeyword(argTypeSpec)
                        if progSpec.typeIsPointer(argTypeSpec): arg
                        self.applyStructImplemetation(argTypeSpec,className,argFieldName)
                        [argCvrtType, innerType] = self.convertType(argTypeSpec, 'arg', 'field', genericArgs)
                        argListText+= self.xlator.codeArgText(argFieldName, argCvrtType, argOwner, argTypeSpec, overRideOper, typeArgList)
                        self.localArgsAllocated.append([argFieldName, argTypeSpec])  # localArgsAllocated is a global variable that keeps track of nested function arguments and local vars.
                #### RETURN TYPE ###########################################
                FirstReturnType = copy.copy(typeSpec) # TODO: Un-Hardcode FirstReturnType, typeSpec?
                if(fieldType[0] != '<%'):
                    pass #self.registerType(className, fieldName, cvrtType, typeDefName)
                else: typeDefName=cvrtType
                if(typeDefName=='none'):
                    typeDefName=''

                #### FUNC HEADER: for both decl and defn. ##################
                inheritMode='normal'
                # TODO: But it should NOT be virtual if there are no calls of the function from a pointer to the base class
                if not progSpec.doesParentClassImplementFunc(self.classStore, className, fieldID) and progSpec.doesChildClassImplementFunc(self.classStore, className, fieldID):
                    inheritMode = 'virtual'
                if self.currentObjName in progSpec.classHeirarchyInfo:
                    classRelationData = progSpec.classHeirarchyInfo[self.currentObjName]
                    if ('parentClass' in classRelationData and classRelationData['parentClass']!=None):
                        parentClassName = classRelationData['parentClass']
                        if progSpec.fieldNameInStructHierachy(self.classStore[0], parentClassName, fieldName):
                            inheritMode = 'override'
                abstractFunction = (not('value' in field) or field['value']==None)
                if abstractFunction: # and not 'abstract' in self.classStore[0][className]['attrList']:
                    inheritMode = 'pure-virtual'
                    self.classStore[0][className]['attrList'].append('abstract')

                # ####################################################################
                fTypeKW=progSpec.fieldTypeKeyword(typeSpec)
                if fTypeKW =='none': isCtor = True
                else: isCtor = False
                [structCode, funcDefCode, globalFuncs]=self.xlator.codeFuncHeaderStr(className, fieldName, typeDefName, argListText, self.localArgsAllocated, inheritMode, overRideOper, isCtor, typeArgList, typeSpec, indent)

                #### FUNC BODY #############################################
                if abstractFunction: # i.e., if no function body is given.
                    cdlog(5, "Function "+fieldID+" has no implementation defined.")
                    funcText = self.xlator.getVirtualFuncText(field)
                    #cdErr("Function "+fieldID+" has no implementation defined.")
                else:
                    extraCodeForTopOfFuntion = self.xlator.extraCodeForTopOfFuntion(argList)
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
                            if globalFuncs!='': self.ForwardDeclsForGlobalFuncs += globalFuncs+";       \t\t // Forward Decl\n"
                    elif field['value'][0]!='':
                        objsRefed2={}
                        funcText =  self.codeActionSeq(field['value'][0], funcBodyIndent, objsRefed2, FirstReturnType, genericArgs)
                        if extraCodeForTopOfFuntion!='':
                            funcText = '{\n' + extraCodeForTopOfFuntion + funcText[1:]
                     #   for rec in sorted(objsRefed2):
                        if globalFuncs!='': self.ForwardDeclsForGlobalFuncs += globalFuncs+";       \t\t // Forward Decl\n"
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
        if makeCtors=='True' and (className!='GLOBAL')  and (className!='widget'):
            ctorCode=self.codeConstructor(className, tags, objsRefed, typeArgList, genericArgs)
            structCodeAcc+= "\n"+ctorCode
        funcDefCodeAcc = topFuncDefCodeAcc + funcDefCodeAcc
        return [structCodeAcc, funcDefCodeAcc, globalFuncsAcc]

    def findIDX(self, classList, className):
        # Returns the index in classList of className or -1
        for findIdx in range(0, len(classList)):
            if classList[findIdx][0]==className: return findIdx
        return -1

    def processDependancies(self, item, searchList, newList):
        if searchList[item][1]==0:
            searchList[item][1]=1
            className=searchList[item][0]
            depList = progSpec.getClassesDependancies(className)
            for dep in depList:
                depIdx=self.findIDX(searchList, dep)
                self.processDependancies(depIdx, searchList, newList)
            newList.append(className)
            searchList[item][1]=2
        elif searchList[item][1]==1:
            pass
            #print("WARNING: Dependancy cycle detected including class "+searchList[item][0])

    def sortClassesForDependancies(self, classList):
        newList=[]
        searchList=[]
        for item in classList:
            if(item=="GLOBAL"): searchList.insert(0, [item, 0])
            else: searchList.append([item, 0])
        for itemIdx in range(0, len(searchList)):
            self.processDependancies(itemIdx, searchList, newList)

        return newList

    def fetchListOfStructsToImplement(self, tags):
        progNameList=[]
        libNameList=[]
        for className in self.classStore[1]:
            if progSpec.isWrappedType(self.classStore, className)!=None: continue
            if(className[0] == '!' or className[0] == '%' or className[0] == '$'): continue   # Filter out "Do Commands", models and strings
            # The next lines skip defining C that will already be defined by a library
            ObjectDef = progSpec.findSpecOf(self.classStore[0], className, 'struct')
            if(ObjectDef==None): continue
            implMode=progSpec.searchATagStore(ObjectDef['tags'], 'implMode')
            if(implMode): implMode=implMode[0]
            if(implMode!=None and not (implMode=="declare" or implMode[:7]=="inherit" or implMode[:9]=="implement")):  # "useLibrary"
                cdlog(2, "SKIPPING: {} {}".format(className, implMode))
                continue
            if className in progSpec.MarkedObjects: libNameList.append(className)
            else: progNameList.append(className)
        classList=libNameList + progNameList
        # TODO: make list global then return early if global list the same size as classList
        classList=self.sortClassesForDependancies(classList)
        return classList

    def codeOneStruct(self, tags, constFieldCode, className):
        classRecord    = None
        constsEnums    = ""  # this isn't used. Remove it?
        dependancies   = []
        self.currentObjName = className
        funcCode       = ''
        if((self.xlator.doesLangHaveGlobals=='False') or className != 'GLOBAL'): # and ('enumList' not in self.classStore[0][className]['typeSpec'])):
            inheritsMode = False
            try:
                if self.classStore[0][className]['tags']['inherits']['fieldType']['altModeIndicator']:
                    inheritsMode = True
            except (TypeError, KeyError) as e:
                cdlog(6, "{}\n failed dict lookup in codeOneStruct".format(e))
            if inheritsMode:     # struct is an enum
                cdlog(1, "   Class that inherits mode: " + className)
                forwardDeclsOut = ""
                enumVals = self.classStore[0][className]['tags']['inherits']['fieldType']['altModeList']
                if self.xlator.doesLangHaveGlobals=='True':
                    structCodeOut = "\n" + self.xlator.getEnumStr(className, enumVals).lstrip()
                    funcCode = self.xlator.getEnumStringifyFunc(className, enumVals)
                    self.modeStateNames[className+'Strings']    = "GLOBAL"
                else:
                    structCodeOut = "\n" + self.xlator.getEnumStructStr(className, enumVals).lstrip()
                    self.modeStringsAcc += self.xlator.getEnumStringifyFunc(className, enumVals)
                    self.modeStateNames[className+'Strings']    = "modeStrings"
                self.inheritedEnums[className] = enumVals
                self.StaticMemberVars[className+'Strings']  = "GLOBAL"
            else:
                cdlog(1, "   Class: " + className)
                classDef = progSpec.findSpecOf(self.classStore[0], className, 'struct')
                modelDef = progSpec.findSpecOf(self.classStore[0], className, 'model')
                classAttrs=progSpec.searchATagStore(classDef['tags'], 'attrs')
                if(classAttrs): classAttrs=classAttrs[0]+' '
                else: classAttrs=''
                classInherits=progSpec.searchATagStore(classDef, 'inherits')
                if modelDef != None:
                    if classInherits is None: classInherits=progSpec.searchATagStore(modelDef, 'inherits')
                    else: classInherits.append(progSpec.searchATagStore(modelDef, 'inherits'))
                classImplements=progSpec.searchATagStore(classDef, 'implements')

                if (className in progSpec.structsNeedingModification):
                    cdlog(3, "structsNeedingModification: {}".format(str(structsNeedingModification[className])))
                    [classToModify, modificationMode, interfaceImplemented, markItem]=progSpec.structsNeedingModification[className]
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
                callableStructFields=[]
                progSpec.populateCallableStructFields(callableStructFields, self.classStore, className)
                [structCode, funcCode, globalCode]=self.codeStructFields(className, tags, '    ', objsRefed)
                structCode+= constFieldCode
                if className=='GLOBAL' and self.xlator.doesLangHaveGlobals=='False': structCode += '\n    _ModeStrings modeStrings = new _ModeStrings();\n'

                attrList = classDef['attrList']
                if classAttrs!='': attrList.append(classAttrs)  # TODO: should append all items from classAttrs
                LangFormOfObjName = progSpec.flattenObjectName(className)
                [structCodeOut, forwardDeclsOut] = self.xlator.codeStructText(self.classStore, attrList, parentClass, classInherits, classImplements, LangFormOfObjName, structCode, tags)
            classRecord = [constsEnums, forwardDeclsOut, structCodeOut, funcCode, className, dependancies]
        self.currentObjName=''
        return classRecord

    #### FLAGS and MODES ###################################################
    def codeFlagAndModeFields(self, className, tags):
        cdlog(5, "                    Coding flags and modes for: {}".format(className))
        flagsVarNeeded = False
        bitCursor=0
        structEnums=""
        CodeDogAddendums = ""
        classDef = self.classStore[0][className]
        for field in progSpec.generateListOfFieldsToImplement(self.classStore, className):
            fieldType=progSpec.getFieldType(field['typeSpec'])
            fieldName=field['fieldName'];
            inheritsMode = False

            if isinstance(fieldType, list) and len(fieldType) == 1:
                fieldType = fieldType[0]
            try:
                if self.classStore[0][fieldType]['tags']['inherits']['fieldType'].get('altModeIndicator', 0):
                    inheritsMode = True
            except (KeyError, TypeError) as e:
                cdlog(6, "{}\n failed dict lookup in codeFlagAndModeFields".format(e))

            if fieldType=='flag' or fieldType=='mode' or inheritsMode:
                flagsVarNeeded=True

                fieldName = progSpec.flattenObjectName(fieldName)
                if fieldType=='flag':
                    cdlog(6, "flag: {}".format(fieldName))
                    structEnums += "    " + self.xlator.getConstIntFieldStr(fieldName, hex(1<<bitCursor), 64) +" \t// Flag: "+fieldName+"\n"
                    self.StaticMemberVars[fieldName]  =className
                    bitCursor += 1;
                elif fieldType=='mode':
                    cdlog(6, "mode: {}[]".format(fieldName))
                    structEnums += "\n// For Mode "+fieldName+"\n"
                    # calculate field and bit position
                    enumSize= len(field['typeSpec']['enumList'])
                    numEnumBits=self.bitsNeeded(enumSize)
                    #field[3]=enumSize;
                    #field[4]=numEnumBits;
                    enumMask=((1 << numEnumBits) - 1) << bitCursor

                    offsetVarName = fieldName+"Offset"
                    maskVarName   = fieldName+"Mask"
                    structEnums += "    "+self.xlator.getConstIntFieldStr(offsetVarName, hex(bitCursor), 64)
                    structEnums += "    "+self.xlator.getConstIntFieldStr(maskVarName,   hex(enumMask), 64) + "\n"

                    # enum
                    enumList=field['typeSpec']['enumList']
                    structEnums += self.xlator.getEnumStr(fieldName, enumList)
                    CodeDogAddendums += "    we List<me string>: "+fieldName+'Strings' + ' <- ' + '["'+('", "'.join(enumList))+'"]\n'

                    # Record the utility vars' parent-Classes
                    self.StaticMemberVars[offsetVarName]=className
                    self.StaticMemberVars[maskVarName]  =className
                    self.StaticMemberVars[fieldName+'Strings']  = className
                    self.modeStateNames[fieldName+'Strings']=className
                    for eItem in enumList:
                        self.StaticMemberVars[eItem]=className

                    bitCursor=bitCursor+numEnumBits;
                elif inheritsMode:
                    cdlog(6, "mode inherited: {}[]".format(fieldName))
                    structEnums += "\n// For Inherited Mode "+fieldName+"\n"
                    enumSize= len(self.classStore[0][fieldType]['tags']['inherits']['fieldType']['altModeList'].asList())
                    numEnumBits=self.bitsNeeded(enumSize)
                    enumMask=((1 << numEnumBits) - 1) << bitCursor

                    offsetVarName = fieldName+"Offset"
                    maskVarName   = fieldName+"Mask"
                    structEnums += "    "+self.xlator.getConstIntFieldStr(offsetVarName, hex(bitCursor), 64)
                    structEnums += "    "+self.xlator.getConstIntFieldStr(maskVarName,   hex(enumMask), 64) + "\n"

                    enumList=self.classStore[0][fieldType]['tags']['inherits']['fieldType']['altModeList'].asList()
                    self.StaticMemberVars[offsetVarName]=className
                    self.StaticMemberVars[maskVarName]  =className
                    self.StaticMemberVars[fieldName+'Strings']  = className
                    self.modeStateNames[fieldName+'Strings']=className
                    for eItem in enumList:
                        self.StaticMemberVars[eItem]=className

                    bitCursor=bitCursor+numEnumBits;

        try:
            if self.classStore[0][className]['tags']['inherits']['fieldType']['altModeIndicator']:
                enumList=self.classStore[0][className]['tags']['inherits']['fieldType']['altModeList'].asList()
                CodeDogAddendums += "    we List<me string>: "+className+'Strings' + ' <- ' + '["'+('", "'.join(enumList))+'"]\n'
        except (KeyError, TypeError) as e:
            cdlog(6, "Warning: caught an exception error in codeFlagAndModeFields")

        if structEnums!="": structEnums="\n\n// *** Code for manipulating "+className+' flags and modes ***\n'+structEnums
        classDef['flagsVarNeeded'] = flagsVarNeeded
        return [flagsVarNeeded, structEnums, CodeDogAddendums]

    def setUpFlagAndModeFields(self, tags, structsToSetUp):
        needsFlagsVar  = False
        CodeDogAddendumsAcc=''
        # Set up flag and mode fields
        for className in structsToSetUp:
            self.currentObjName=className
            CodeDogAddendumsAcc=''
            [needsFlagsVar, strOut, CodeDogAddendums]=self.codeFlagAndModeFields(className, tags)
            objectNameBase=progSpec.flattenObjectName(className) #progSpec.baseStructName(className)
            if not objectNameBase in self.constFieldAccs: self.constFieldAccs[objectNameBase]=""
            self.constFieldAccs[objectNameBase]+=strOut
            CodeDogAddendumsAcc+=CodeDogAddendums
            if(needsFlagsVar):
                CodeDogAddendumsAcc += 'me uint64: flags\n'
            if CodeDogAddendumsAcc!='':
                codeDogParser.AddToObjectFromText(self.classStore[0], self.classStore[1], progSpec.wrapFieldListInObjectDef(className,  CodeDogAddendumsAcc ), 'Flags and Modes for class '+className)
            self.currentObjName=''

    def codeAllNonGlobalStructs(self, tags, classRecords, structsToImplement):
        cdlog(2, "CODING FLAGS and MODES...")
        # Write the class
        for className in structsToImplement:
            typeArgList = progSpec.getTypeArgList(className)
            classDef = progSpec.findSpecOf(self.classStore[0], className, "struct")
            if self.xlator.renderGenerics=='False' or typeArgList == None or progSpec.isWrappedType(self.classStore, className):
                classRecord = self.codeOneStruct(tags, self.constFieldAccs[progSpec.flattenObjectName(className)], className)
                if classRecord != None:
                    classRecords[className]=classRecord

        # Check for final class attributes to add. E.g., 'abstract' or 'mutating'
     #   for className in structsToImplement:
     #       specialAttributes = self.xlator.addSpecialClassAttributes(self.classStore, className))
        return classRecords

    def codeStructureCommands(self, tags):
        for command in progSpec.ModifierCommands:
            if (command[3] == 'addImplements'):
                calledFuncID = command[1]
                calledFuncName = progSpec.fieldNameID(calledFuncID)
                if calledFuncName in progSpec.funcsCalled:
                    calledFuncInstances = progSpec.funcsCalled[calledFuncName]
                    for funcCalledParams in calledFuncInstances:
                        paramList = funcCalledParams[0]
                        commandArgs = command[2]
                        if paramList != None:
                            count=1
                            for P in paramList:
                                oldTextTag='%'+str(count)
                                [newText, argTypeSpec]= self.codeExpr(P[0], {}, None, None, 'PARAM', genericArgs)
                                commandArgs=commandArgs.replace(oldTextTag, newText)
                                count+=1
                            #print commandArgs
                        firstColonPos=commandArgs.find(':')
                        secondColonPos=commandArgs.find(':', firstColonPos+1)
                        interfaceImplemented=commandArgs[:firstColonPos]
                        classToModify=commandArgs[secondColonPos+1:]
                        progSpec.structsNeedingModification[classToModify] = [classToModify, "implement", interfaceImplemented, progSpec.MarkItems]
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
                    pattern_WriteCallProxy.apply(self.classStore, tags, proxyStyle, className, funcName, platformTag)

    def codeModeStringsStruct(self):
        return('\nclass _ModeStrings{\n    '+self.modeStringsAcc+'}\n')

    def makeTagText(self, tags, tagName):
        tagVal=progSpec.fetchTagValue(tags, tagName)
        if tagVal==None: return "Tag '"+tagName+"' is not set in the dog file."
        return tagVal

    libInterfacesText =''
    def makeFileHeader(self, tags, filename):
        if self.libEmbedAboveIncludes!='': self.libEmbedAboveIncludes+='\n\n'
        filename = self.makeTagText(tags, 'FileName')
        platform = self.makeTagText(tags, 'Platform')
        buildName = progSpec.fetchTagValue(tags,"buildName")
        buildStr = buildDog.getBuildSting(filename,self.buildStr_libs,platform,buildName)

        header  = "// " + self.makeTagText(tags, 'Title') + " "+ self.makeTagText(tags, 'Version') + '\n'
        header += "// " + self.makeTagText(tags, 'CopyrightMesg') +'\n'
        header += "// This file: " + filename +'\n'
        header += "// Dog File: " + self.makeTagText(tags, 'dogFilename') +'\n'
        header += "// Authors of CodeDog file: " + self.makeTagText(tags, 'Authors') +'\n'
        header += "// Build time: " + datetime.datetime.today().strftime('%c') + '\n'
        header += "\n// " + self.makeTagText(tags, 'Description') +'\n'
        header += "\n/*  " + self.makeTagText(tags, 'LicenseText') +'\n*/\n'
        header += "\n// Build Options Used: " +'Not Implemented'+'\n'
        header += "\n// Build Command: " +buildStr+'\n\n'
        header += self.libEmbedAboveIncludes
        header += self.libInterfacesText
        header += self.xlator.addSpecialCode(filename)
        return header

    [libInitCodeAcc,  libDeinitCodeAcc] = ['', '']
    [libEmbedAboveIncludes, libEmbedVeryHigh, libEmbedCodeHigh, libEmbedCodeLow] = ['', '', '', '']

    def integrateLibrary(self, tags, tagsFromLibFiles, libID):
        headerStr = ''
        headerTopStr = ''
        #cdlog(2, 'Integrating {}'.format(libID))
        # TODO: Choose static or dynamic linking based on defaults, license tags, availability, etc.

        if 'embedAboveIncludes'in tagsFromLibFiles[libID]: self.libEmbedAboveIncludes+= tagsFromLibFiles[libID]['embedAboveIncludes']
        if 'embedVeryHigh'     in tagsFromLibFiles[libID]: self.libEmbedVeryHigh     += tagsFromLibFiles[libID]['embedVeryHigh']
        if 'embedHigh'         in tagsFromLibFiles[libID]: self.libEmbedCodeHigh     += tagsFromLibFiles[libID]['embedHigh']
        if 'embedLow'          in tagsFromLibFiles[libID]: self.libEmbedCodeLow      += tagsFromLibFiles[libID]['embedLow']
        if 'initCode'          in tagsFromLibFiles[libID]: self.libInitCodeAcc       += tagsFromLibFiles[libID]['initCode']
        if 'deinitCode'        in tagsFromLibFiles[libID]: self.libDeinitCodeAcc      = tagsFromLibFiles[libID]['deinitCode'] + self.libDeinitCodeAcc + "\n"

        if 'interface' in tagsFromLibFiles[libID]:
            if 'libFiles' in tagsFromLibFiles[libID]['interface']:
                libFiles = tagsFromLibFiles[libID]['interface']['libFiles']

                for libFile in libFiles:
                    if libFile.startswith('pkg-config'):
                        self.buildStr_libs += "`"
                        self.buildStr_libs += libFile
                        self.buildStr_libs += "` "
                    else:
                        if libFile =='pthread': self.buildStr_libs += '-pthread ';
                        else: self.buildStr_libs += "-l"+libFile+ " "

            if 'headers' in tagsFromLibFiles[libID]['interface']:
                libHeaders = tagsFromLibFiles[libID]['interface']['headers']
                for libHdr in libHeaders:
                    if libHdr == '"stdafx.h"':
                        headerTopStr = self.xlator.includeDirective(libHdr)
                    else:
                        headerStr += self.xlator.includeDirective(libHdr)
        return [headerStr, headerTopStr]

    def connectLibraries(self, tags, libsToUse):
        headerStr = ''
        tagsFromLibFiles = libraryMngr.getTagsFromLibFiles()
        for libFilename in libsToUse:
            cdlog(1, 'ATTACHING LIBRARY: '+libFilename)
            [headerStrOut, headerTopStr] = self.integrateLibrary(tags, tagsFromLibFiles, libFilename)
            headerStr = headerTopStr + headerStr + headerStrOut
            macroDefs= {}
            [tagStore, buildSpecs, FileClasses, newClasses] = self.loadProgSpecFromDogFile(libFilename, self.classStore[0], self.classStore[1], tags[0], macroDefs)
        return headerStr

    def convertTemplateClasses(self, tags):
        for className in self.classStore[1]:
            for field in progSpec.generateListOfFieldsToImplement(self.classStore, className):
                typeSpec =field['typeSpec']
                fieldName =field['fieldName']
                self.applyStructImplemetation(typeSpec,className,fieldName)

    def appendGLOBALInitCode(self, tags):
        for field in progSpec.generateListOfFieldsToImplement(self.classStore, "GLOBAL"):
            isAllocated = field['isAllocated']
            if isAllocated:
                fieldName =field['fieldName']
                paramList = field['paramList']
                paramStr  = ''
                #if paramList != None:
                    #if(len(paramList)>0 ):
                        #for param in paramList:
                            # TODO: grab base parameter in codeDog, similar to self.codeExpr but through codeDog self.xlator
                        #paramStr = ' <- (' + paramStr + ')'
                allocStr = '    Allocate('+fieldName+')' + paramStr
                progSpec.addCodeToInit(tags[0], allocStr)

    def addGLOBALSpecialCode(self, tags):
        self.xlator.addGLOBALSpecialCode(self.classStore, tags)
        initCode=''; deinitCode=''
        if 'initCode'   in tags[0]: initCode  = tags[0]['initCode']
        if 'deinitCode' in tags[0]: deinitCode= tags[0]['deinitCode']
        initCode += self.libInitCodeAcc
        deinitCode = self.libDeinitCodeAcc + deinitCode

        GLOBAL_CODE="""
    struct GLOBAL{
        me void: initialize(me string: prgArgs) <- {
            %s
        }

        me void: deinitialize() <- {
            %s
        }
    }""" % (initCode, deinitCode)
        codeDogParser.AddToObjectFromText(self.classStore[0], self.classStore[1], GLOBAL_CODE, 'Global special code (initialize(), deinitialize())' )

    def generateBuildSpecificMainFunctionality(self, tags):
        self.xlator.generateMainFunctionality(self.classStore, tags)

    def pieceTogetherTheSourceFiles(self, tags, oneFileTF, classRecords, headerInfo, MainTopBottom):
        classRecordsOut=[]
        fileExtension=self.xlator.fileExtension
        constsEnums=''
        forwardDecls="\n";
        structCodeAcc='\n////////////////////////////////////////////\n//   C l a s s   D e c l a r a t i o n s\n\n';
        funcCodeAcc="\n//////////////////////////////////////\n//   M e m b e r   F u n c t i o n s\n\n"
        if oneFileTF: # Generate a single source file
            filename = self.makeTagText(tags, 'FileName')+fileExtension
            header = self.makeFileHeader(tags, filename)
            structsToImplement = self.fetchListOfStructsToImplement(tags)
            for className in structsToImplement:
                typeArgList = progSpec.getTypeArgList(className)
                if(self.xlator.doesLangHaveGlobals=='False' or className != 'GLOBAL') and (self.xlator.renderGenerics=='False' or typeArgList == None):
                        classRecord    = classRecords[className]
                        constsEnums   += classRecord[0]
                        forwardDecls  += classRecord[1]
                        structCodeAcc += classRecord[2]
                        funcCodeAcc   += classRecord[3]

            forwardDecls += self.funcDeclAcc
            funcCodeAcc  += self.funcDefnAcc
            if self.xlator.doesLangHaveGlobals=='False': structCodeAcc += self.codeModeStringsStruct()

            outputStr = header + constsEnums + forwardDecls + self.libEmbedVeryHigh + structCodeAcc + self.ForwardDeclsForGlobalFuncs + self.libEmbedCodeHigh + MainTopBottom[0] + funcCodeAcc + self.libEmbedCodeLow + MainTopBottom[1]
            filename = progSpec.fetchTagValue(tags, "FileName")
            classRecordsOut.append([filename, outputStr])

        else: # Generate a file for each class
            for classRecord in classRecords:
                [constsEnums, forwardDecls, structCodeAcc, funcCodeAcc, className, dependancies]  = classRecord
                filename = className+fileExtension
                header = self.makeFileHeader(tags, filename)
                outputStr = header + constsEnums + forwardDecls + structCodeAcc + funcCodeAcc
                classRecordsOut.append([filename, outputStr])

        return classRecordsOut

    def clearBuild(self):
        self.localVarsAllocated = []
        self.localArgsAllocated = []
        self.currentObjName=''
        self.libInterfacesText=''
        self.libInitCodeAcc=''
        self.libDeinitCodeAcc=''
        self.StaticMemberVars={}
        self.funcDeclAcc=''
        self.funcDefnAcc=''
        self.ForwardDeclsForGlobalFuncs='\n\n// Forward Declarations of global functions\n'
        self.listOfFuncsWithUnknownArgTypes = {}

    def generate(self, classes, tags, libsToUse, langName):
        self.clearBuild()
        self.xlator = self.xlator

        # self.buildStr_libs = self.xlator.BuildStrPrefix
        self.classStore=classes
        self.tagStore=tags[0]
        # self.buildStr_libs +=  progSpec.fetchTagValue(tags, "FileName")
        self.libInterfacesText=self.connectLibraries(tags, libsToUse)

        cdlog(0, "\n##############  G E N E R A T I N G   "+langName+"   C O D E . . .")
        self.convertTemplateClasses(tags)
        cdlog(1, "GENERATING: Top-level (e.g., main())...")
        self.appendGLOBALInitCode(tags)
        self.addGLOBALSpecialCode(tags)
        testMode = progSpec.fetchTagValue(tags, 'testMode')
        if progSpec.fetchTagValue(tags, 'ProgramOrLibrary') == "program"  or testMode == "makeTests"  or testMode == "runTests":
            self.generateBuildSpecificMainFunctionality(tags)

        self.codeStructureCommands(tags)
        cdlog(1, "GENERATING: Classes...")
        structsToImpl = self.fetchListOfStructsToImplement(tags)
        self.setUpFlagAndModeFields(tags, structsToImpl)
        classRecords=self.codeAllNonGlobalStructs(tags, {}, structsToImpl)
        topBottomStrings = self.xlator.codeMain(self.classStore, tags, {})
        classRecords=self.codeAllNonGlobalStructs(tags, classRecords, self.genericStructsGenerated[1])
        typeDefCode = self.xlator.produceTypeDefs(self.typeDefMap)

        fileSpecStrings = self.pieceTogetherTheSourceFiles(tags, True, classRecords, [], topBottomStrings)
        showNote = False
        if showNote:
            print("\n\nNOTE: The following functions were used but CodeDog couldn't determine the type of their arguments:")
            for funcName in self.listOfFuncsWithUnknownArgTypes: print(funcName, end=' ')
            print("\n");
        return fileSpecStrings

    ###############  Load a file to progspec, processing include files, string-structs, and patterns.
    def GroomTags(self, tags):
        if self.tagStore==None: TopLevelTags=tags
        else: TopLevelTags=self.tagStore
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
        #TODO: fix automatic featuresNeeded
        for typeName in progSpec.storeOfBaseTypesUsed:
            if(typeName=='BigInt' or typeName=='BigFrac'):
                print('NOTE: Need Large Numbers')
                progSpec.setFeatureNeeded(TopLevelTags, 'BigNumbers', progSpec.storeOfBaseTypesUsed[typeName])

    def ScanAndApplyPatterns(self, classes, topTags, newTags):
        if self.tagStore==None:
            if topTags!={}: TopLevelTags=topTags
            else: TopLevelTags=newTags
        else: TopLevelTags=self.tagStore
        #if len(self.classStore[1])>0: cdlog(1, "Applying Patterns...")
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

    def loadProgSpecFromDogFile(self, filename, ProgSpec, objNames, topLvlTags, macroDefs):
        codeDogStr = progSpec.stringFromFile(filename)
        codeDogStr = libraryMngr.processIncludedFiles(codeDogStr, filename)
        [tagStore, buildSpecs, FileClasses, newClasses] = codeDogParser.parseCodeDogString(codeDogStr, ProgSpec, objNames, macroDefs, filename)
        self.GroomTags(tagStore)
        self.ScanAndApplyPatterns(FileClasses, topLvlTags, tagStore)
        stringStructs.CreateStructsForStringModels(FileClasses, newClasses, tagStore)
        return [tagStore, buildSpecs, FileClasses,newClasses]

    def __init_(self):
        print("INIT")
