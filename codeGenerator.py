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
    buildStr_libs      = ''
    funcDeclAcc        = ''
    funcDefnAcc        = ''
    classStore         = []
    tagStore           = None
    localVarsAllocated = []   # Format: [varName, typeSpec]
    localArgsAllocated = []   # Format: [varName, typeSpec]
    currentObjName     = ''
    inheritedEnums     = {}
    constFieldAccs     = {}
    modeStringsAcc     = ''
    nestedClasses      = {}
    isNestedClass      = False
    genericStructsGenerated = [ {}, [] ]
    codeDogSpecificImpl     = ["List", "Map", "MapNode","MapItr", "Multimap", ]
    ForwardDeclsForGlobalFuncs = ''
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
    def typeIsInteger(self, fType):
        # NOTE: If you need this to work for wrapped types as well use the version in CodeGenerator.py
        if fType == None: return False
        if progSpec.typeIsNumRange(fType): return True
        if not isinstance(fType, str):
            fType= fType[0]
        fType=progSpec.getUnwrappedClassFieldTypeKeyWord(self.classStore, fType)
        if fType=="int" or fType=="BigInt" or fType=="uint" or fType=="uint64" or fType=="uint32"or fType=="int64" or fType=="int32" or fType=="FlexNum":
            return True
        return False

    def typeIsRational(self, fType):
        # NOTE: If you need this to work for wrapped types as well use the version in CodeGenerator.py
        if fType == None: return False
        #if progSpec.typeIsNumRange(fType): return True
        if not isinstance(fType, str):
            fType= fType[0]
        fType=progSpec.getUnwrappedClassFieldTypeKeyWord(self.classStore, fType)
        if fType=="double" or fType=="float" or fType=="BigFloat" or fType=="FlexNum" or fType=="BigFrac":
            return True
        return False

    def CheckBuiltinItems(self, currentObjName, segSpec, genericArgs):
        # Handle print, return, break, etc.
        itemName=segSpec[0]
        [code, retOwner, retType]=self.xlator.codeSpecialReference(segSpec, genericArgs)
        if code == '': return None
        if itemName=='self':
            classDef =  progSpec.findSpecOf(self.classStore[0], currentObjName, "struct")
            if 'typeSpec' in classDef:
                tSpecOut = progSpec.getTypeSpec(classDef)
                tSpecOut['owner']='their' # TODO: write test case for containers
                print("SHOULDNT MATCH:", tSpecOut['owner'],classDef['typeSpec']['owner'])
            else: tSpecOut={'owner':'their', 'fieldType':retType, 'arraySpec':None, 'argList':None}
        else: tSpecOut={'owner':retOwner, 'fieldType':retType, 'arraySpec':None, 'argList':None}
        tSpecOut['codeConverter']=code
        return [tSpecOut, 'BUILTIN']

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
        classDef = progSpec.findSpecOf(self.classStore[0], className, "struct")
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
                    wrappedOwner=progSpec.getOwner(wrappedTypeSpec)
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
        classDef = progSpec.findSpecOf(self.classStore[0], itemName, "struct")
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
            return(self.xlator.langVarNamePrefix(crntBaseName, refedClass))
        return ''

    def getFieldIDArgList(self, segSpec, genericArgs):
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
                [S2, argTSpec]=self.codeExpr(arg[0], None, None, 'LVAL', genericArgs)
                #print(argTSpec)
                keyWord = progSpec.fieldTypeKeyword(argTSpec)
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

    def fetchItemsTypeSpec(self, segSpec, genericArgs):
        # also used to fetch codeConverter
        # return format: [{typeSpec}, 'OBJVAR']. Substitute for wrapped types.
        RefType=""
        useClassTag=""
        itemName=segSpec[0]
        [argListStr, fieldIDArgList] = self.getFieldIDArgList(segSpec, genericArgs)
        #print ("FETCHING TYPESPEC OF:", self.currentObjName+'::'+itemName+fieldIDArgList)
        if self.currentObjName != "":
            fieldID = self.currentObjName+'::'+itemName
            tagToFind       = "classOptions."+progSpec.flattenObjectName(fieldID)
            classOptionsTag = progSpec.fetchTagValue([self.tagStore], tagToFind)
            if classOptionsTag != None and "useClass" in classOptionsTag:
                useClassTag     = classOptionsTag["useClass"]
        REF=self.CheckBuiltinItems(self.currentObjName, segSpec, genericArgs)
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
                        fTypeKW = progSpec.fieldTypeKeyword(REF)
                        if progSpec.doesClassHaveProperty(self.classStore, fTypeKW, 'metaClass'):
                            REF['typeSpec']['fieldType'][0] = useClassTag
                    RefType="OBJVAR"
                    if(self.currentObjName=='GLOBAL'): RefType="GLOBAL"
                    if self.xlator.LanguageName=='Swift':  #TODO Make this part of xlators
                        RefOwner = progSpec.getOwner(REF)
                        if RefOwner=='we': RefType = "STATIC:" + self.currentObjName + self.xlator.ObjConnector
                else:
                    REF=self.CheckObjectVars("GLOBAL", itemName, fieldIDArgList)
                    if (REF):
                        RefType="GLOBAL"
                    else:
                        REF=self.CheckClassStaticVars(self.currentObjName, itemName)
                        if(REF):
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
        return [REF['typeSpec'], RefType]   # Example: [{typeSpec}, 'OBJVAR']

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
    def getDataStructItrTSpec(self, datastructID):
        fieldDefFind = self.CheckObjectVars(datastructID, "find", "")
        if fieldDefFind==0: fieldDefFind = None
        elif 'typeSpec' in fieldDefFind: fieldDefFind = fieldDefFind['typeSpec']
        return fieldDefFind

    def chooseStructImplementationToUse(self, tSpec,className,fieldName):
        fType = progSpec.getFieldType(tSpec)
        if not isinstance(fType, str) and  len(fType) >1:
            fTypeKW  = progSpec.fieldTypeKeyword(tSpec)
            classDef = progSpec.findSpecOf(self.classStore[0], fTypeKW, "struct")
            ctnrCat  = progSpec.getTagSpec(self.classStore, fTypeKW, 'implements')
            if ('chosenType' in fType):
                return(None, None, None, None)
            implOptions = progSpec.getImplementationOptionsFor(fTypeKW)
            if(implOptions == None):
                if fTypeKW=="List" or fTypeKW=="Map" or fTypeKW=="Multimap" :
                    print("******WARNING: no implementation options found for container ", fTypeKW ,className,"::",fieldName)
                    # Check to confirm container type is in features needed
            else:
                reqTags = progSpec.getReqTags(fType)
                hiScoreVal = -1
                hiScoreName = None
                for option in implOptions:
                    classDef = progSpec.findSpecOf(self.classStore[0], option, "struct")
                    if 'tags' in classDef and 'specs' in classDef['tags']:
                        optionTags  = classDef['tags']
                        optionSpecs = optionTags['specs']
                        [implScore, errorMsg] = progSpec.scoreImplementation(optionSpecs, reqTags)
                        if 'native' in optionTags:
                            nativeTag   = optionTags['native']
                            if nativeTag == "lang": implScore += 6
                            if nativeTag == "platform": implScore += 5
                        if(errorMsg != ""): cdErr(errorMsg)
                        if(implScore > hiScoreVal):
                            hiScoreVal = implScore
                            hiScoreName = classDef['name']
                if hiScoreName != None:
                    implTArgs = progSpec.getTypeArgList(hiScoreName)
                else: implTArgs = None
                #print("IMPLEMENTS:", fTypeKW, '->', hiScoreName)
                if hiScoreName!=None:progSpec.addDependencyToStruct(className,hiScoreName)
                return(hiScoreName,fTypeKW,ctnrCat,implTArgs)
        return(None, None, None, None)

    def applyStructImplemetation(self, tSpec,className,fieldName):
        self.checkForReservedWord(fieldName, className)
        [structToImplement, cntrTypeKW, ctnrCat, implTArgs] = self.chooseStructImplementationToUse(tSpec,className,fieldName)
        if(structToImplement != None):
            tSpec['fieldType'][0] = structToImplement
            if cntrTypeKW != None:tSpec['fromImplemented'] = cntrTypeKW
            if ctnrCat != None:tSpec['containerCategory'] = ctnrCat
            if implTArgs != None:tSpec['implTypeArgs'] = implTArgs
        return tSpec

    def copyFieldType(self, fType):
        if isinstance(fType,str):retVal = copy.copy(fType)
        else:
            retVal=[]
            for prop in fType:retVal.append(copy.copy(prop))
        return retVal

    def copyTypeSpec(self, tSpec):
        retVal = {}
        for prop in tSpec:
            if prop=='fieldType': retVal[prop]=self.copyFieldType(tSpec[prop])
            else: retVal[prop]=copy.copy(tSpec[prop])
        return retVal

    def copyField(self, field):
        copyField = {}
        for prop in field:
            if prop=='typeSpec':
                copyField[prop] = self.copyTypeSpec(field[prop])
            else:
                copyField[prop] = copy.copy(field[prop])
        return copyField

    def copyFields(self, fields):
        retVal = []
        for field in fields:
            copyField = self.copyField(field)
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

    def removeCodeDogImplTags(self, className, genericStructName, implTags):
        if isinstance(implTags,str):
            tagName = implTags
            if tagName in self.codeDogSpecificImpl:
                implTags = None
            if implTags!=None:
                implTags = self.xlator.getLangSpecificImplements(implTags)
                if implTags=="": implTags = None
        elif isinstance(implTags,list):
            for implTag in implTags:
                tagName = implTag
                if tagName in self.codeDogSpecificImpl:
                    implTags.remove(tagName)
                else:
                    tagName = self.xlator.getLangSpecificImplements(tagName)
                    if tagName=="":
                        implTags.remove(implTag)
            if len(implTags)==0: implTags = None
        return implTags

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
                genericType        = progSpec.fieldTypeKeyword(reqTag)
                unwrappedKW        = progSpec.getUnwrappedClassFieldTypeKeyWord(self.classStore, genericType)
                genericStructName += "_"+unwrappedKW
                genericArgs[typeArgList[count]]=reqTag
                count += 1
        else:
            for gArg in genericArgs:
                genericType        = progSpec.fieldTypeKeyword(genericArgs[gArg])
                unwrappedKW        = progSpec.getUnwrappedClassFieldTypeKeyWord(self.classStore, genericType)
                genericStructName += "_"+unwrappedKW
        if not genericStructName in self.genericStructsGenerated[1]:
            self.genericStructsGenerated[1].append(genericStructName)
            self.classStore[1].append(genericStructName)
            genericClassDef = self.copyClassDef(classDef)
            if 'vFields' in genericClassDef: genericClassDef['vFields'] = None
            if 'implements' in genericClassDef:
                implTags = self.removeCodeDogImplTags(className, genericStructName, genericClassDef['implements'])
                genericClassDef['tags'].pop('implements')
                if implTags!=None: genericClassDef['tags']['implements'] = implTags
            if 'tags' in genericClassDef and 'implements' in genericClassDef['tags']:
                implTags = self.removeCodeDogImplTags(className, genericStructName, genericClassDef['tags']['implements'])
                genericClassDef['tags'].pop('implements')
                if implTags!=None:
                    genericClassDef['tags']['implements'] = implTags
            genericClassDef['name'] = genericStructName
            genericClassDef['genericArgs'] = genericArgs
            for field in genericClassDef["fields"]: # handle constructors and function return types
                tSpec  = progSpec.getTypeSpec(field)
                if 'argList' in tSpec:
                    fieldName = field['fieldName']
                    fTypeKW = progSpec.fieldTypeKeyword(tSpec)
                    if tSpec['reqTagList']: tSpec['reqTagList'] = reqTagList
                    tSpec = self.getGenericFieldsTypeSpec(genericArgs, tSpec)
                    if not isinstance(tSpec['fieldType'], str) and len(tSpec['fieldType'])>1:
                        fTypeKW = self.generateGenericStructName(fTypeKW, reqTagList, genericArgs)
                        tSpec['fieldType'] = [fTypeKW]
                    if fTypeKW == "none": field['fieldName'] = genericStructName
            self.genericStructsGenerated[0][genericStructName] = genericClassDef
            self.classStore[0][genericStructName] = genericClassDef
            previousObjName=self.currentObjName
            self.setUpFlagAndModeFields(self.tagStore, [genericStructName])
            self.currentObjName=previousObjName
        return genericStructName

    def copyGenericsToArgList(self, tSpec, genericArgs):
        argListIn  = progSpec.getArgList(tSpec)
        argListOut = None
        if argListIn and genericArgs:
            argListOut = []
            for arg in argListIn:
                argTypeKW = progSpec.fieldTypeKeyword(arg)
                if argTypeKW in genericArgs:
                    argOut = self.copyField(arg)
                    genericType = genericArgs[argTypeKW]
                    fTypeOut    = progSpec.fieldTypeKeyword(genericType)
                    ownerOut    = progSpec.getOwner(genericType)
                    tSpecOut    = {'owner':ownerOut, 'fieldType':fTypeOut}
                    argOut['typeSpec'] = tSpecOut
                    argListOut.append(argOut)
        return(argListOut)

    def getGenericFieldsTypeSpec(self, genericArgs, tSpec):
        if genericArgs == None: return tSpec
        if genericArgs == {}:   return tSpec
        fTypeKW = progSpec.fieldTypeKeyword(tSpec)
        if fTypeKW in genericArgs:
            tSpec = self.copyTypeSpec(tSpec)
            genericType = genericArgs[fTypeKW]
            fTypeOut    = progSpec.fieldTypeKeyword(genericType)
            ownerIn     = progSpec.getOwner(tSpec)
            ownerOut    = progSpec.getOwner(genericType)
            if ownerIn=='itr': ownerOut = 'itr'
            tSpec['fieldType'] = fTypeOut
            tSpec['owner']     = ownerOut
            tSpec['generic']   = fTypeKW
        argListOut = self.copyGenericsToArgList(tSpec, genericArgs)
        if argListOut and self.xlator.useNestedClasses:
            tSpec = self.copyTypeSpec(tSpec)
            tSpec['argList']=argListOut
        return tSpec

    def getGenericTypeSpec(self, genericArgs, tSpec):
        fTypeKW = progSpec.fieldTypeKeyword(tSpec)
        reqTagList = progSpec.getReqTagList(tSpec)
        if reqTagList==None or progSpec.isWrappedType(self.classStore, fTypeKW) or progSpec.isAbstractStruct(self.classStore[0], fTypeKW):
            tSpecOut = self.getGenericFieldsTypeSpec(genericArgs, tSpec)
        elif self.xlator.renderGenerics=='True':
            tSpecOut = self.copyTypeSpec(tSpec)
            cvrtType = self.generateGenericStructName(fTypeKW, reqTagList, genericArgs)
            tSpecOut['fieldType'] = [copy.copy(cvrtType)]
            fromImpl = progSpec.getFromImpl(tSpecOut)
            if fromImpl:
                implTArgs = progSpec.getImplementationTypeArgs(tSpecOut)
                if implTArgs: tSpecOut['implTypeArgs'] = implTArgs
                tSpecOut['fromImplemented'] = fromImpl
            else:
                tArgList = progSpec.getTypeArgList(fTypeKW)
                tSpecOut['fromImplemented'] = fTypeKW
                tSpecOut['implTypeArgs']    = tArgList
            ctnrCat  = progSpec.getTagSpec(self.classStore, fTypeKW, 'implements')
            if ctnrCat:
                tSpecOut['containerCategory'] = ctnrCat
            tSpecOut['generic'] = True
        else: #renderGenerics=='False'
            tSpecOut = self.getGenericFieldsTypeSpec(genericArgs, tSpec)
        return tSpecOut

    def getContainerValueOwnerAndType(self, tSpec):
        fTypeKW    = progSpec.fieldTypeKeyword(tSpec)
        keyOwner   = progSpec.getContainerFirstElementOwner(tSpec)
        keyTypeKW  = progSpec.getContainerFirstElementType(tSpec)
        reqTagList = progSpec.getReqTagList(tSpec)
        implTArgs  = progSpec.getImplementationTypeArgs(tSpec)
        fDefAt     = self.CheckObjectVars(fTypeKW, "at", "")
        if implTArgs and fDefAt:
            atOwner  = progSpec.getOwner(fDefAt)
            atTypeKW = progSpec.fieldTypeKeyword(fDefAt)
            if atTypeKW in implTArgs:
                idxAt   = implTArgs.index(atTypeKW)
                valType = reqTagList[idxAt]
                return[valType['tArgOwner'], valType['tArgType']]
            else: return[atOwner, atTypeKW]
        if reqTagList:
            keyOwner    = reqTagList[0]['tArgOwner']
            keyTypeKW   = reqTagList[0]['tArgType']
        return[keyOwner, keyTypeKW]

    ########################################################################
    def getUnwrappedIteratorTypeKW(self, owner, fTypeKW):
        itrTypeKW   = None
        if owner=='itr' and not progSpec.isItrType(fTypeKW):
            itrTypeKW   = progSpec.convertItrType(self.classStore, owner, fTypeKW)
            itrTypeKW   = progSpec.getUnwrappedClassFieldTypeKeyWord(self.classStore, itrTypeKW)
        return itrTypeKW

    def getNestedOutter(self, innerKW):
        outerKW = None
        if innerKW in self.nestedClasses:
            outerKW = self.nestedClasses[innerKW]
        return outerKW

    def convertType(self, tSpec, varMode, genericArgs):
        # varMode is 'var' or 'arg' or 'alloc' or 'func' for function Header. Large items are passed as pointers
        progSpec.isOldContainerTempFuncErr(tSpec, "convertType")
        tSpec    = self.getGenericFieldsTypeSpec(genericArgs, tSpec)
        fTypeKW  = progSpec.fieldTypeKeyword(tSpec)
        ownerIn  = progSpec.getOwner(tSpec)
        ownerOut = self.xlator.getUnwrappedClassOwner(self.classStore, tSpec, fTypeKW, varMode, ownerIn)
        unwrappedKW = progSpec.getUnwrappedClassFieldTypeKeyWord(self.classStore, fTypeKW)
        reqTagList  = progSpec.getReqTagList(tSpec)
        itrTypeKW   = self.getUnwrappedIteratorTypeKW(ownerOut, fTypeKW)
        reqTagStr = self.xlator.getReqTagString(self.classStore, tSpec)
        if self.xlator.renderGenerics=='True':
            if reqTagList and not progSpec.isWrappedType(self.classStore, fTypeKW) and not progSpec.isAbstractStruct(self.classStore[0], fTypeKW):
                if itrTypeKW: fTypeKW = itrTypeKW
                unwrappedKW = self.generateGenericStructName(fTypeKW, reqTagList, genericArgs)
            else: unwrappedKW += reqTagStr
        else:
            if self.xlator.useNestedClasses:
                if fTypeKW in self.nestedClasses: # is a nested Class
                    if fTypeKW==self.currentObjName and self.isNestedClass:
                        unwrappedKW = unwrappedKW
                    elif self.currentObjName==self.getNestedOutter(fTypeKW):
                        itrTypeKW = unwrappedKW
                        unwrappedKW = self.currentObjName+reqTagStr
                    elif self.isNestedClass and self.getNestedOutter(fTypeKW)==self.getNestedOutter(self.currentObjName):
                        unwrappedKW = unwrappedKW
                    else:
                        unwrappedKW = unwrappedKW+reqTagStr
                elif fTypeKW in self.nestedClasses.values(): # contains a nested class
                    if fTypeKW==self.currentObjName:
                        unwrappedKW = unwrappedKW
                    else:
                        unwrappedKW = unwrappedKW+reqTagStr
                else: unwrappedKW += reqTagStr
            else: unwrappedKW += reqTagStr
        langType = self.xlator.adjustBaseTypes(unwrappedKW, progSpec.isNewContainerTempFunc(tSpec))
        langType = self.xlator.applyIterator(langType, itrTypeKW, varMode)
        langType = self.xlator.applyOwner(ownerOut, langType, varMode)
        return langType

    def codeAllocater(self, tSpec, paramList, genericArgs):
        CPL = '()'
        if paramList!=None:
            if isinstance(paramList, str): CPL = '('+paramList+')'
            elif len(paramList)>0:
                fTypeKW      = progSpec.fieldTypeKeyword(tSpec)
                classDef     = progSpec.findSpecOf(self.classStore[0], fTypeKW, "struct")
                if genericArgs==None: genericArgs  = progSpec.getGenericArgs(classDef)
                modelParams  = self.getCtorModelParams(fTypeKW)
                if len(paramList)>len(modelParams): modelParams  = []
                [CPL, paramTypeList]  = self.codeParameterList('Allocate', paramList, modelParams, genericArgs)
                if self.xlator.useAllCtorArgs and len(paramList)<len(modelParams):
                    CPL2 = '('
                    count = 0
                    for modParam in modelParams:
                        modTypeKW = progSpec.fieldTypeKeyword(modParam)
                        if count>0: CPL2+=', '
                        if len(paramTypeList)>count:
                            paramTypeKW = progSpec.fieldTypeKeyword(paramTypeList[count])
                            if modTypeKW!=paramTypeKW and paramTypeKW!=None:
                                CPL2 = ''
                                break
                            [S2, argTSpec]=self.codeExpr(paramList[count][0], None, modParam, 'PARAM', genericArgs)
                            CPL2 += S2
                        else:
                            defaultVal = self.getFieldDefaultVal(modParam, genericArgs)
                            CPL2 += defaultVal
                        count += 1
                    if CPL2!="": CPL= CPL2+')'
        CPL = self.xlator.codeSpecialParamList(tSpec, CPL)
        S = self.xlator.codeXlatorAllocater(tSpec, genericArgs) + CPL
        return S

    def convertNameSeg(self, tSpec, name, connector, paramList, reqTagList, genericArgs):
        newName = tSpec['codeConverter']
        fTypeKW = progSpec.fieldTypeKeyword(tSpec)
        if newName == "": cdErr("ERROR: empty codeConverter for: "+name)
        if paramList != None:
            count=1
            for P in paramList:
                oldTextTag='%'+str(count)
                [S2, argTSpec]=self.codeExpr(P[0], None, None, 'RVAL', genericArgs)
                if S2!='self':S2 += self.xlator.makePtrOpt(argTSpec)
                if(isinstance(newName, str)):
                    newName=newName.replace(oldTextTag, S2)
                else: exit(2)
                count+=1
            paramList=None
        if '%0.' in newName and connector==self.xlator.PtrConnector:
            newName = newName.replace('%0.', '%0'+self.xlator.PtrConnector)
        if "%T0Type" in newName:
            if(reqTagList != None):
                T0Type  = progSpec.fieldTypeKeyword(reqTagList[0])
                T0Type  = progSpec.getUnwrappedClassFieldTypeKeyWord(self.classStore, T0Type)
                T0Type  = self.xlator.adjustBaseTypes(T0Type,True)
                T0Owner = progSpec.getOwner(reqTagList[0])
                T0Type  = self.xlator.applyOwner(T0Owner, T0Type,'')
                newName = newName.replace("%T0Type",T0Type)
            else: cdErr("ERROR: looking for T0Type in codeConverter but reqTagList found in TypeSpec.")
        if "%T1Type" in newName:
            if(reqTagList != None):
                T1Type  = progSpec.fieldTypeKeyword(reqTagList[1])
                T1Type  = progSpec.getUnwrappedClassFieldTypeKeyWord(self.classStore, T1Type)
                T1Type  = self.xlator.adjustBaseTypes(T1Type,True)
                T1Owner = progSpec.getOwner(reqTagList[1])
                T1Type  = self.xlator.applyOwner(T1Owner, T1Type,'')
                newName = newName.replace("%T1Type",T1Type)
            else: cdErr("ERROR: looking for T1Type in codeConverter but reqTagList found in TypeSpec.")
        return [newName, paramList]

    def codeComment(self, commentType, commentStr):
        if commentType=='/**': return '\n/* ' + commentStr+ '*/'
        elif commentType=='//*': return '// ' + commentStr + '\n'
        else: cdErr("unknown comment type: "+ commentType)
    ################################  C o d e   E x p r e s s i o n s
    def codeNameSeg(self, segSpec, tSpecIn, connector, LorR_Val, previousSegName, previousTypeSpec, returnType, LorRorP_Val, genericArgs):
        # if tSpecIn has 'dummyType', this is a non-member (or self) and the first segment of the reference.
        # return example: ['getData()', <typeSpec>, <alternate form>, 'OBJVAR']
        S          = ''
        SRC        = ''
        namePrefix = ''  # For static_Global vars
        tSpecOut   = {'owner':'', 'fieldType':'void'}
        name       = segSpec[0]
        owner      = progSpec.getOwner(tSpecIn)
        fTypeKW    = progSpec.fieldTypeKeyword(tSpecIn)
        progSpec.isOldContainerTempFuncErr(tSpecIn, 'codeNameSeg1 '+self.currentObjName+' ' +str(name))
        isCtnr     = progSpec.isNewContainerTempFunc(tSpecIn)
        if genericArgs==None and previousTypeSpec!=None: genericArgs = progSpec.getGenericArgsFromTypeSpec(previousTypeSpec)
        if(name=='allocate'): cdErr("Deprecated use of allocate()")

        paramList  = None
        if len(segSpec) > 1 and segSpec[1]=='(':
            if(len(segSpec)==2): paramList=[]
            else: paramList=segSpec[2]

        if fTypeKW!=None and not isCtnr:
            if fTypeKW=="string":
                lenParams = 0
                if paramList: lenParams = len(paramList)
                [name, tmpTypeSpec] = self.xlator.recodeStringFunctions(name, tSpecOut, lenParams)
                tSpecOut = copy.copy(tmpTypeSpec)

        if isCtnr and name[0]=='[':
            idxTSpec = self.xlator.getIdxType(tSpecIn)
            [valOwner, valFType] = self.getContainerValueOwnerAndType(tSpecIn)
            tSpecOut = {'owner':valOwner, 'fieldType': valFType}
            [S2, idxTSpec] = self.codeExpr(name[1], None, None, LorRorP_Val, genericArgs)
            S += self.xlator.codeArrayIndex(S2, tSpecIn, LorR_Val, previousSegName, idxTSpec)
            return [S, tSpecOut, S2,'']
        elif ('dummyType' in tSpecIn): # This is the first segment of a name
            if name=="return":
                SRC = "RETURN_TYPE"
                tSpecOut['argList'] = [{'typeSpec':returnType}]
            elif(name=='resetFlagsAndModes'):
                tSpecOut={'owner':'me', 'fieldType': 'void', 'codeConverter':'flags=0'}
                # TODO: if flags or modes have a non-zero default this should account for that.
            else:
                [tSpecOut, SRC]=self.fetchItemsTypeSpec(segSpec, genericArgs) # Possibly adds a codeConversion to tSpecOut
                if tSpecOut: tSpecOut = self.getGenericTypeSpec(genericArgs, tSpecOut)
                if not self.xlator.doesLangHaveGlobals:
                    if tSpecOut and 'isGlobalEnum' in tSpecOut and tSpecOut['isGlobalEnum']:namePrefix = progSpec.fieldTypeKeyword(tSpecOut)+ '.'
                    elif(SRC=="GLOBAL"): namePrefix = self.xlator.GlobalVarPrefix
                    elif name in self.modeStateNames and self.modeStateNames[name]=='modeStrings': namePrefix = self.xlator.GlobalVarPrefix+self.modeStateNames[name]+'.'
            if(SRC[:6]=='STATIC'): namePrefix = SRC[7:];
        else:
            if(name=='resetFlagsAndModes'):
                tSpecOut={'owner':'me', 'fieldType': 'void', 'codeConverter':'flags=0'}
                # TODO: if flags or modes have a non-zero default this should account for that.
            elif(name[0]=='[' and fTypeKW=='string'):
                tSpecOut={'owner':'me', 'fieldType': 'char'}
                [S2, idxTypeSpec] = self.codeExpr(name[1], None, None, 'RVAL', genericArgs)
                S += self.xlator.codeArrayIndex(S2, 'string', LorR_Val, previousSegName, idxTypeSpec)
                return [S, tSpecOut, S2, '']  # Here we return S2 for use in code forms other than [idx]. e.g. f(idx)
            elif(name[0]=='[' and (fTypeKW=='uint' or fTypeKW=='int')):
                print("Error: integers can't be indexed: ", previousSegName,  ":", name)
                exit(2)
            else:
                if fTypeKW!="string":
                    itrTypeKW = progSpec.convertItrType(self.classStore, owner, fTypeKW)
                    if itrTypeKW!=None: fTypeKW = itrTypeKW
                    [argListStr, fieldIDArgList] = self.getFieldIDArgList(segSpec, genericArgs)
                    tSpecOut = self.CheckObjectVars(fTypeKW, name, fieldIDArgList)
                    if tSpecOut!=0:
                        tSpecOut = self.copyTypeSpec(self.getGenericTypeSpec(genericArgs, tSpecOut['typeSpec']))
                        if isCtnr:
                            segTypeKeyWord = progSpec.fieldTypeKeyword(tSpecOut)
                            segTypeOwner   = progSpec.getOwner(tSpecOut)
                            [innerTypeOwner, innerTypeKeyWord] = progSpec.queryTagFunction(self.classStore, fTypeKW, "__getAt", segTypeKeyWord, tSpecIn)
                            if(innerTypeOwner and segTypeOwner != 'itr'):
                                tSpecOut['owner'] = innerTypeOwner
                            if(innerTypeKeyWord): tSpecOut['fieldType'][0] = innerTypeKeyWord
                        tSpecOut = self.copyTypeSpec(tSpecOut)
                    else: print("tSpecOut = 0 for: "+previousSegName+"."+name, " fTypeKW:",fTypeKW)

        if tSpecOut and 'codeConverter' in tSpecOut and tSpecOut['codeConverter']!=None:
            reqTagList = progSpec.getReqTagList(tSpecIn)
            [convertedName, paramList]=self.convertNameSeg(tSpecOut, name, connector, paramList, reqTagList, genericArgs)
            #print("codeConverter ",name,"->",convertedName, tSpecOut)
            name = convertedName
            callAsGlobal=name.find("%G")
            if(callAsGlobal >= 0): namePrefix=''

        S+=namePrefix+connector+name

        # Add parameters if this is a function call
        if(paramList != None):
            modelParams = progSpec.getArgList(tSpecOut)
            [CPL, paramTypeList] = self.codeParameterList(name, paramList, modelParams, genericArgs)
            if self.xlator.renameInitFuncs and name=='init':
                if not 'dummyType' in tSpecIn:
                    fTypeKW=progSpec.fieldTypeKeyword(tSpecIn)
                else: fTypeKW=self.currentObjName
                S=S.replace('init','__INIT_'+fTypeKW)
            S+= CPL
        if(tSpecOut==None): cdlog(logLvl(), "Type for {} was not found.".format(name))
        return [S, tSpecOut, None, SRC]

    def codeUnknownNameSeg(self, segSpec, genericArgs):
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
                [CPL, paramTypeList] = self.codeParameterList("", paramList, None, genericArgs)
                S+= CPL
        print("UNKNOWN NAME SEGMENT:", S)
        return S;

    #### codeItemRef ##################################################
    def codeItemRef(self, name, LorR_Val, returnType, LorRorP_Val, genericArgs):
        # Returns information related to a variable, function, etc.
        previousSegName = ""
        previousTypeSpec = None
        S=''
        segStr=''
        if(LorR_Val=='RVAL'): canonicalName ='>'
        else: canonicalName = '<'
        segTSpec={'owner':'', 'dummyType':True}
        connector=''
        prevLen=len(S)
        segIDX=0
        AltFormat=None
        AltIDXFormat=''
        numNameSegs = len(name)
        for segSpec in name:
            LHSParentType='#'
            owner=progSpec.getOwner(segTSpec)
            segName=segSpec[0]
            isLastSeg = numNameSegs == segIDX+1
            if(segIDX>0):
                # Detect connector to use '.' '->', '', (*...).
                connector='.'
                if(segTSpec): # This is where to detect type of vars not found to determine whether to use '.' or '->'
                    if 'StaticMode' in segTSpec and segTSpec['StaticMode']=='yes':
                        connector = self.xlator.ObjConnector
                    elif progSpec.wrappedTypeIsPointer(self.classStore, segTSpec, segName):
                        connector = self.xlator.PtrConnector
                        if previousSegName and previousSegName[-1] == ']' and connector=='!.':
                            connector = self.xlator.ObjConnector

            AltFormat=None
            if segTSpec!=None:
                if segTSpec and 'fieldType' in segTSpec:
                    LHSParentType = progSpec.fieldTypeKeyword(segTSpec)
                else: LHSParentType = progSpec.fieldTypeKeyword(self.currentObjName)   # Landed here because this is the first segment
                [segStr, segTSpec, AltIDXFormat, nameSource]=self.codeNameSeg(segSpec, segTSpec, connector, LorR_Val, previousSegName, previousTypeSpec, returnType, LorRorP_Val, genericArgs)
                if nameSource!='': canonicalName+=nameSource
                if AltIDXFormat!=None:
                    AltFormat=[S, previousTypeSpec, AltIDXFormat]   # This is in case of an alternate index format such as Java's string.put(idx, val)
            else:
                segStr= self.codeUnknownNameSeg(segSpec, genericArgs)
            prevLen=len(S)

            if(isinstance(segTSpec, int)):
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
            S = self.xlator.LanguageSpecificDecorations(S, segTSpec, owner, LorRorP_Val)
            previousSegName = segName
            previousTypeSpec = segTSpec
            segIDX+=1

        # Handle cases where seg's type is flag or mode
        if segTSpec and LorR_Val=='RVAL' and 'fieldType' in segTSpec:
            fType=progSpec.fieldTypeKeyword(segTSpec)
            if fType=='flag':
                segName=segStr[len(connector):]
                prefix = self.staticVarNamePrefix(segName, LHSParentType)
                if self.xlator.hasMacros:
                    S='getFlagBit('+S[0:prevLen]+connector+'flags' + ', ' + prefix+segName+')'
                else:
                    bitfieldMask=self.xlator.applyTypecast('uint64', prefix+segName)
                    flagReadCode = '('+S[0:prevLen] + connector + 'flags & ' + bitfieldMask+')'
                    S=self.xlator.applyTypecast('uint64', flagReadCode)
            elif fType=='mode':
                segName=segStr[len(connector):]
                prefix = self.staticVarNamePrefix(segName+"Mask", LHSParentType)
                if self.xlator.hasMacros:
                    S='getModeBits('+S[0:prevLen]+connector+'flags' + ', ' + prefix+segName+')'
                else:
                    bitfieldMask  =self.xlator.applyTypecast('uint64', prefix+segName+"Mask")
                    bitfieldOffset=self.xlator.applyTypecast('uint64', prefix+segName+"Offset")
                    S="((" + S[0:prevLen] + connector +  "flags&"+bitfieldMask+")"+">>"+bitfieldOffset+')'
                    S=self.xlator.applyTypecast(self.xlator.modeIdxType, S)

        return [S, segTSpec, LHSParentType, AltFormat]

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

    def codeParameterList(self, name, paramList, modelParams, genericArgs):
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
                modelTSpec = None
                if modelParams and (len(modelParams)>count) and ('typeSpec' in modelParams[count]):
                    modelTSpec = progSpec.getTypeSpec(modelParams[count])
                [S2, argTSpec]=self.codeExpr(P[0], None, modelTSpec, 'PARAM', genericArgs)
                paramTypeList.append(argTSpec)
                if modelTSpec!=None:
                    modelTypeKW   = progSpec.fieldTypeKeyword(modelTSpec)
                    argTypeKW     = progSpec.fieldTypeKeyword(argTSpec)
                    if self.xlator.implOperatorsAsFuncs(modelTypeKW):
                        if argTypeKW=='numeric':
                            S2 = 'new '+modelTypeKW+'('+S2+')'
                    if name == 'return' and S2 == 'nil':  # Swift return nil, provide context and make optional
                        S2 = modelTypeKW +"?("+S2+")"
                    else:
                        [leftMod, rightMod] = self.xlator.chooseVirtualRValOwner(modelTSpec, argTSpec)
                        S2 = leftMod+S2+rightMod
                        S2 = self.xlator.checkForTypeCastNeed(modelTSpec,argTSpec,S2)
                    S += S2
                else:
                    self.listOfFuncsWithUnknownArgTypes[(name+'()')]=1
                    S += S2
                count+=1
            S='(' + S + ')'
        return [S, paramTypeList]

    #################################################################
    def codeTerm(self, item, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec]=self.xlator.codeFactor(item[0], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if (not(isinstance(item, str))) and (len(item) > 1) and len(item[1])>0:
            [S, isDerefd]=self.xlator.derefPtr(S, retTypeSpec)
            fType1 = progSpec.fieldTypeKeyword(retTypeSpec)
            for i in item[1]:
                #print '               term:', i
                if   (i[0] == '*'): op = ' * '
                elif (i[0] == '/'): op = ' / '
                elif (i[0] == '%'): op = ' % '
                else: print("ERROR: One of '*', '/' or '%' expected in code generator."); exit(2)
                [S2, retType2] = self.xlator.codeFactor(i[1], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)

                if not self.xlator.implOperatorsAsFuncs(fType1):
                    [S2, isDerefd]=self.xlator.derefPtr(S2, retType2)
                    S+= op + S2
                else:
                    fType2 = progSpec.fieldTypeKeyword(retType2)
                    S = self.xlator.codeTermAsFunc(S, S2, fType1, fType2, op)
        return [S, retTypeSpec]

    def codePlus(self, item, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec]=self.codeTerm(item[0], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if len(item) > 1 and len(item[1])>0:
            [S, isDerefd]=self.xlator.derefPtr(S, retTypeSpec)
            fType1 = progSpec.fieldTypeKeyword(retTypeSpec)
            if isDerefd:
                keyType = progSpec.varTypeKeyWord(retTypeSpec)
                retTypeSpec={'owner': 'me', 'fieldType': keyType}
            for  i in item[1]:
                [S2, retType2] = self.codeTerm(i[1], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                [S2, isDerefd]=self.xlator.derefPtr(S2, retType2)
                if self.xlator.implOperatorsAsFuncs(fType1):
                    fType2 = progSpec.fieldTypeKeyword(retType2)
                    S = self.xlator.codePlusAsFunc(S, S2, fType1, i[0])
                else:
                    if   (i[0] == '+'): op = ' + '
                    elif (i[0] == '-'): op = ' - '
                    else: print("ERROR: '+' or '-' expected in code generator."); exit(2)
                    if i[0]=='+' :S2 = self.xlator.checkForTypeCastNeed('string', retType2, S2)
                    S += op+S2
        return [S, retTypeSpec]

    def codeComparison(self, item, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec]=self.codePlus(item[0], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if len(item) > 1 and len(item[1])>0:
            if len(item[1])>1: print("Error: Chained comparisons.\n"); exit(1);
            [S, isDerefd]=self.xlator.derefPtr(S, retTypeSpec)
            for i in item[1]:
                [S2, retType2] = self.codePlus(i[1], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                S = self.xlator.codeComparisonStr(S, S2, retTypeSpec, retType2, i[0])
                retTypeSpec = {'owner': 'me', 'fieldType': 'bool'}
        return [S, retTypeSpec]

    def codeIsEQ(self, item, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec]=self.codeComparison(item[0], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if len(item) > 1 and len(item[1])>0:
            if len(item[1])>1: print("Error: Chained == or !=.\n"); exit(1);
            if (isinstance(retTypeSpec, int)): cdlog(logLvl(), "Invalid item in ==: {}".format(item[0]))
            for i in item[1]:
                [S2, retType2] = self.codeComparison(i[1], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                S  = self.xlator.codeIdentityCheck(S, S2, retTypeSpec, retType2, i[0])
                retTypeSpec = {'owner': 'me', 'fieldType': 'bool'}
        return [S, retTypeSpec]

    def codeBitwiseAnd(self, item, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec] = self.codeIsEQ(item[0], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if len(item) > 1 and len(item[1])>0:
            if (isinstance(retTypeSpec, int)): cdlog(logLvl(), "Invalid item in ==: {}".format(item[0]))
            [S_derefd, isDerefd] = self.xlator.derefPtr(S, retTypeSpec)
            S = self.xlator.convertToInt(S, retTypeSpec)
            for i in item[1]:
                [S2, retType2] = self.codeIsEQ(i[1], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                S2 = self.xlator.convertToInt(S2, retType2)
                S+= ' & '+S2
            retTypeSpec = {'owner': 'me', 'fieldType': 'int', 'arraySpec': None, 'reqTagList': None, 'argList': None}
        return [S, retTypeSpec]

    def codeBitwiseXOR(self, item, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec]=self.codeBitwiseAnd(item[0], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if len(item) > 1 and len(item[1])>0:
            if (isinstance(retTypeSpec, int)): cdlog(logLvl(), "Invalid item in ==: {}".format(item[0]))
            [S_derefd, isDerefd] = self.xlator.derefPtr(S, retTypeSpec)
            for i in item[1]:
                [S2, retType2] = self.codeBitwiseAnd(i[1], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                S+= ' ^ '+S2
        return [S, retTypeSpec]

    def codeBitwiseOr(self, item, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec] = self.codeBitwiseXOR(item[0], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if len(item) > 1 and len(item[1])>0:
            if (isinstance(retTypeSpec, int)): cdlog(logLvl(), "Invalid item in ==: {}".format(item[0]))
            [S_derefd, isDerefd] = self.xlator.derefPtr(S, retTypeSpec)
            for i in item[1]:
                [S2, retType2] = self.codeBitwiseXOR(i[1], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                S+= ' | '+S2
        return [S, retTypeSpec]

    def codeLogicalAnd(self, item, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec] = self.codeBitwiseOr(item[0], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if len(item) > 1 and len(item[1])>0:
            [S, isDerefd]=self.xlator.derefPtr(S, retTypeSpec)
            for i in item[1]:
                if (i[0] == 'and'):
                    S = self.xlator.checkForTypeCastNeed('bool', retTypeSpec, S)
                    [S2, retTypeSpec] = self.codeBitwiseOr(i[1], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                    S2 = self.xlator.checkForTypeCastNeed('bool', retTypeSpec, S2)
                    [S2, isDerefd]=self.xlator.derefPtr(S2, retTypeSpec)
                    S+=' && ' + S2
                else: print("ERROR: 'and' expected in code generator."); exit(2)
                retTypeSpec = {'owner': 'me', 'fieldType': 'bool'}
        return [S, retTypeSpec]

    def codeLogicalOr(self, item, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec] = self.codeLogicalAnd(item[0], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if len(item) > 1 and len(item[1])>0:
            [S, isDerefd]=self.xlator.derefPtr(S, retTypeSpec)
            for i in item[1]:
                if (i[0] == 'or'):
                    S = self.xlator.checkForTypeCastNeed('bool', retTypeSpec, S)
                    [S2, retTypeSpec] = self.codeLogicalAnd(i[1], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                    [S2, isDerefd]=self.xlator.derefPtr(S2, retTypeSpec)
                    S2 = self.xlator.checkForTypeCastNeed('bool', retTypeSpec, S2)
                    S+=' || ' + S2
                else: print("ERROR: 'or' expected in code generator."); exit(2)
                retTypeSpec = {'owner': 'me', 'fieldType': 'bool'}
        return [S, retTypeSpec]

    def codeExpr(self, item, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        [S, retTypeSpec] = self.codeLogicalOr(item[0], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        if not isinstance(item, str) and len(item) > 1 and len(item[1])>0:
            [S, isDerefd]=self.xlator.derefPtr(S, retTypeSpec)
            for i in item[1]:
                if (i[0] == '<-'):
                    [S2, retTypeSpec] = self.codeLogicalOr(i[1], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                    [S2, isDerefd]=self.xlator.derefPtr(S2, retTypeSpec)
                    S+=' = ' + S2
                else: print("ERROR: '<-' expected in code generator."); exit(2)
                retTypeSpec = {'owner': 'me', 'fieldType': 'bool'}
        return [S, retTypeSpec]

    #### ACTIONS ###########################################################
    def codeRepetition(self, action, returnType, indent, genericArgs):
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
            [S_low, lowValTypeSpec] = self.codeExpr(rangeSpec[2][0], None, None, 'RVAL', genericArgs)
            [S_hi,   hiValTypeSpec] = self.codeExpr(rangeSpec[4][0], None, None, 'RVAL', genericArgs)
            ctrlVarsTypeSpec = {'owner': 'me', 'fieldType': ctrType}
            actionText += self.xlator.codeRangeSpec(traversalMode, ctrType, repName, S_low, S_hi, indent)
            self.localVarsAllocated.append([repName, ctrlVarsTypeSpec])  # Tracking local vars for scope
        elif(whileSpec):
            [whileExpr, whereConditionTypeSpec] = self.codeExpr(whileSpec[2], None, None, 'RVAL', genericArgs)
            [whileExpr, whereConditionTypeSpec] =  self.xlator.adjustConditional(whileExpr, whereConditionTypeSpec)
            actionText += indent + "while(" + whileExpr + "){\n"
            loopCounterName=repName
        elif(fileSpec):
            [filenameExpr, filenameTypeSpec] = self.codeExpr(fileSpec[2], None, None, 'RVAL', genericArgs)
            if filenameTypeSpec!='string':
                cdErr("Filename must be a string.\n")
            print("File iteration not implemeted yet.\n")
            exit(2)
        elif(keyRange):
            [ctnrName, ctnrTSpec] = self.codeExpr(keyRange[0][0], None, None, 'RVAL', genericArgs)
            progSpec.isOldContainerTempFuncErr(ctnrTSpec, 'codeRepetition1 '+self.currentObjName+' '+ctnrName)
            [StartKey, StartTypeSpec] = self.codeExpr(keyRange[2][0], None, None, 'RVAL', genericArgs)
            [EndKey,   EndTypeSpec] = self.codeExpr(keyRange[4][0], None, None, 'RVAL', genericArgs)
            wrappedTypeSpec = progSpec.isWrappedType(self.classStore, progSpec.fieldTypeKeyword(ctnrTSpec)[0])
            if(wrappedTypeSpec != None):ctnrTSpec=wrappedTypeSpec
            [actionTextOut, loopCounterName] = self.xlator.iterateRangeFromTo(self.classStore,self.localVarsAllocated, StartKey, EndKey, ctnrTSpec,repName,ctnrName,indent)
            actionText += actionTextOut
        else: # interate over a container
            [ctnrName, ctnrTSpec] = self.codeExpr(action['repList'][0], None, None, 'RVAL', genericArgs)
            fTypeKW     = progSpec.fieldTypeKeyword(ctnrTSpec)
            progSpec.isOldContainerTempFuncErr(ctnrTSpec, 'codeRepetition2 '+self.currentObjName+' '+ctnrName)
            isCtnr = fTypeKW=='string' or progSpec.isNewContainerTempFunc(ctnrTSpec)
            if ctnrTSpec==None or not isCtnr: cdErr("'"+ctnrName+"' is not a container so cannot be iterated over."+str(ctnrTSpec))
            isBackward = False
            if(traversalMode=='Backward'): isBackward=True
            [actionTextOut, loopCounterName, itrIncStr] = self.xlator.iterateContainerStr(self.classStore,self.localVarsAllocated,ctnrTSpec,repName,ctnrName, isBackward, indent, genericArgs)
            actionText += actionTextOut
        if action['whereExpr']:
            [whereExpr, whereConditionTypeSpec] = self.codeExpr(action['whereExpr'], None, None, 'RVAL', genericArgs)
            actionText += indent + "    " + 'if (!' + whereExpr + ') continue;\n'
        if action['untilExpr']:
            [untilExpr, untilConditionTypeSpec] = self.codeExpr(action['untilExpr'], None, None, 'RVAL', genericArgs)
            actionText += indent + '    ' + 'if (' + untilExpr + ') break;\n'
        repBodyText = ''
        for repAction in repBody:
            actionOut = self.codeAction(repAction, indent + "    ", returnType, genericArgs)
            repBodyText += actionOut
        if loopCounterName!='':
            actionText=indent + ctrType+" " + loopCounterName + "=0;\n" + actionText
            repBodyText += indent + "    " + self.xlator.codeIncrement(loopCounterName) + ";\n"
            ctrlVarsTypeSpec = {'owner':'me', 'fieldType':'uint'}
            self.localVarsAllocated.append([loopCounterName, ctrlVarsTypeSpec])  # Tracking local vars for scope
        actionText += repBodyText + itrIncStr + indent + '}\n'
        return actionText

    def codeFuncCall(self, funcCallSpec, returnType, genericArgs):
        [S, tSpec, LHSParentType, AltIDXFormat]=self.codeItemRef(funcCallSpec, 'RVAL', returnType, 'RVAL', genericArgs)
        return S

    def startPointOfNamesLastSegment(self, name):
        p=len(name)-1
        while(p>0):
            if name[p]=='>' or name[p]=='.':
                return p
            p-=1
        return -1

    def genIfBody(self, ifBody, indent, returnType, genericArgs):
        ifBodyText = ""
        for ifAction in ifBody:
            actionOut = self.codeAction(ifAction, indent + "    ", returnType, genericArgs)
            ifBodyText += actionOut
        return ifBodyText

    def codeCriticalSection(self, criticalSection, indent, returnType, genericArgs):
        criticalText = ""
        for criticalStmt in criticalSection:
            actionOut = self.codeAction(criticalStmt, indent + "    ", returnType, genericArgs)
            criticalText += actionOut
        return criticalText

    def encodeConditionalStatement(self, action, indent, returnType, genericArgs):
        [S2, conditionTypeSpec] =  self.codeExpr(action['ifCondition'][0], None, None, 'RVAL', genericArgs)
        [S2, conditionTypeSpec] =  self.xlator.adjustConditional(S2, conditionTypeSpec)
        ifCondition = S2
        ifBodyText = self.genIfBody(action['ifBody'], indent, returnType, genericArgs)
        actionText =  indent + "if (" + ifCondition + ") " + "{\n" + ifBodyText + indent + "}\n"
        elseBodyText = ""
        elseBody = action['elseBody']
        if (elseBody):
            if (elseBody[0]=='if'):
                elseAction = elseBody[1]
                elseText = self.encodeConditionalStatement(elseAction[0], indent, returnType, genericArgs)
                actionText += indent + "else " + elseText.lstrip()
            elif (elseBody[0]=='action'):
                elseAction = elseBody[1]['actionList']
                elseText = self.codeActionSeq(elseAction, indent, returnType, genericArgs)
                actionText += indent + "else " + elseText.lstrip()
            else:  print("Unrecognized item after else"); exit(2);
        return actionText

    #### codeAction ##################################################
    def codeAction(self, action, indent, returnType, genericArgs):
        #make a string and return it
        actionText = ""
        action['sideEffects']=[]
        typeOfAction = action['typeOfAction']

        if (typeOfAction =='newVar'):
            fieldDef  = action['fieldDef']
            tSpec     = progSpec.getTypeSpec(fieldDef)
            fieldName = fieldDef['fieldName']
            progSpec.isOldContainerTempFuncErr(tSpec, 'codeAction '+self.currentObjName+' '+fieldName)
            self.applyStructImplemetation(tSpec,self.currentObjName,fieldName)
            cdlog(5, "Action newVar: {}".format(fieldName))
            varDeclareStr = self.xlator.codeNewVarStr(tSpec, fieldName, fieldDef, indent, genericArgs, self.localVarsAllocated)
            actionText = indent + varDeclareStr + ";\n"
        elif (typeOfAction =='assign'):
            cdlog(5, "PREASSIGN:" + str(action['LHS']))
            # Note: In Java, string A[x]=B must be coded like: A.put(B,x)
            cdlog(5, "Pre-assignment... ")
            [LHS, lhsTypeSpec, LHSParentType, AltIDXFormat] = self.codeItemRef(action['LHS'], 'LVAL', returnType, 'LVAL', genericArgs)
            assignTag = action['assignTag']
            cdlog(5, "Assignment: {}".format(LHS))
            [S2, rhsTypeSpec]=self.codeExpr(action['RHS'][0], None, lhsTypeSpec, 'RVAL', genericArgs)
            [LHS_leftMod, LHS_rightMod,  RHS_leftMod, RHS_rightMod]=self.xlator.determinePtrConfigForAssignments(lhsTypeSpec, rhsTypeSpec, assignTag,LHS)
            LHS = LHS_leftMod+LHS+LHS_rightMod
            RHS = RHS_leftMod+S2+RHS_rightMod
            cdlog(5, "Assignment: {} = {}".format(lhsTypeSpec, rhsTypeSpec))
            RHS = self.xlator.checkForTypeCastNeed(lhsTypeSpec, rhsTypeSpec, RHS)
            LHS_FieldType=progSpec.fieldTypeKeyword(lhsTypeSpec)
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
                    if AltIDXFormat!=None: # Handle special forms of assignment such as LVal(idx, RVal)
                        actionText = self.xlator.checkIfSpecialAssignmentFormIsNeeded(action, indent, AltIDXFormat, RHS, rhsTypeSpec, LHS, LHSParentType, LHS_FieldType)
                    if actionText=="":     # Handle the normal assignment case
                        if RHS=='nil' and LHS[-1]=='!': LHS=LHS[:-1]  #TODO: Move this code to swift self.xlator
                        actionText = indent + LHS + " = " + RHS + ";\n"
            else:
                if AltIDXFormat!=None: # Handle special forms of assignment such as LVal(idx, RVal)
                    actionText = self.xlator.checkIfSpecialAssignmentFormIsNeeded(action, indent, AltIDXFormat, RHS, rhsTypeSpec, LHS, LHSParentType, LHS_FieldType)
                if actionText=='':     # Handle the normal assignment case
                    assignTag = assignTag[0]
                    if(assignTag=='deep'):
                        actionText = indent + LHS + " = " + RHS + ";\n"
                    elif(assignTag=='+'):
                        if self.xlator.implOperatorsAsFuncs(LHS_FieldType):
                            actionText = self.xlator.codePlusAsFunc(LHS, RHS, LHS_FieldType, assignTag) + ";\n"
                        else: actionText = indent + LHS + " += " + RHS + ";\n"
                    elif(assignTag=='-'):  actionText = indent + LHS + " -= " + RHS + ";\n"
                    elif(assignTag=='*'):  actionText = indent + LHS + " *= " + RHS + ";\n"
                    elif(assignTag=='/'):  actionText = indent + LHS + " /= " + RHS + ";\n"
                    elif(assignTag=='%'):  actionText = indent + LHS + " %= " + RHS + ";\n"
                    elif(assignTag=='<<'): actionText = indent + LHS + " <<= " + RHS + ";\n"
                    elif(assignTag=='>>'): actionText = indent + LHS + " >>= " + RHS + ";\n"
                    elif(assignTag=='&'):  actionText = indent + LHS + " &= " + RHS + ";\n"
                    elif(assignTag=='^'):  actionText = indent + LHS + " ^= " + RHS + ";\n"
                    elif(assignTag=='|'):  actionText = indent + LHS + " |= " + RHS + ";\n"
                    else: actionText = indent + "opAssign" + assignTag + '(' + LHS + ", " + RHS + ");\n"
        elif (typeOfAction =='swap'):
            LHS   = action['LHS']
            RHS   =  action['RHS']
            tSpec = self.fetchItemsTypeSpec(LHS, genericArgs)
            LCvrtType = self.convertType(tSpec[0], 'var', genericArgs)
            tSpec = self.fetchItemsTypeSpec(RHS, genericArgs)
            LHS   = LHS[0]
            RHS   = RHS[0]
            actionText = indent + LCvrtType + " tmp = " + LHS + ";\n"
            actionText += indent + LHS + " = " + RHS + ";\n"
            actionText += indent + RHS + " = " + "tmp;\n"
        elif (typeOfAction =='conditional'):
            cdlog(5, "If-statement...")
            [S2, conditionTypeSpec] =  self.codeExpr(action['ifCondition'][0], None, None, 'RVAL', genericArgs)
            if conditionTypeSpec==None: cdErr("Found typeSpec None in codeAction():   "+S2)
            [S2, conditionTypeSpec] =  self.xlator.adjustConditional(S2, conditionTypeSpec)
            cdlog(5, "If-statement: Condition is ".format(S2))
            ifCondition = S2
            ifBodyText = self.genIfBody(action['ifBody'], indent, returnType, genericArgs)
            actionText =  indent + "if (" + ifCondition + ") " + "{\n" + ifBodyText + indent + "}\n"
            elseBodyText = ""
            elseBody = action['elseBody']
            if (elseBody):
                if (elseBody[0]=='if'):
                    elseAction = elseBody[1][0]
                    elseText = self.encodeConditionalStatement(elseAction, indent, returnType, genericArgs)
                    actionText += indent + "else " + elseText.lstrip()
                elif (elseBody[0]=='action'):
                    elseAction = elseBody[1]['actionList']
                    elseText = self.codeActionSeq(elseAction, indent, returnType, genericArgs)
                    actionText += indent + "else " + elseText.lstrip()
                else:  print("Unrecognized item after else"); exit(2);
        elif (typeOfAction =='repetition'):
            actionText = self.codeRepetition(action, returnType, indent, genericArgs)
        elif (typeOfAction =='funcCall'):
            calledFunc = action['calledFunc']
            if calledFunc[0][0] == 'if' or calledFunc=='withEach' or calledFunc=='until' or calledFunc=='where':
                print("\nERROR: It is not allowed to name a function", calledFunc[0][0])
                exit(2)
            cdlog(5, "Function Call: {}()".format(str(calledFunc[0][0])))
            funcCallText = self.codeFuncCall(calledFunc, returnType, genericArgs)
            funcCallTextStriped = funcCallText.strip()
            if (funcCallTextStriped!=''):
                actionText = indent + funcCallText + ';\n'
        elif (typeOfAction == 'switchStmt'):
            cdlog(5, "Switch statement: switch({})".format(str(action['switchKey'])))
            [switchKeyExpr, switchKeyTypeSpec] = self.codeExpr(action['switchKey'][0], None, None, 'RVAL', genericArgs)
            actionText += indent+"switch("+ self.xlator.codeSwitchExpr(switchKeyExpr, switchKeyTypeSpec)  + "){\n"
            blockPrefix = self.xlator.blockPrefix
            for sCases in action['switchCases']:
                actionText += indent
                for sCase in sCases[0]:
                    [caseKeyValue, caseKeyTypeSpec] = self.codeExpr(sCase[0], None, None, 'RVAL', genericArgs)
                    actionText += "    case "+self.xlator.codeSwitchCase(caseKeyValue, caseKeyTypeSpec)+": "
                caseAction = sCases[1]
                actionText += blockPrefix + self.codeActionSeq(caseAction, indent+'    ', returnType, genericArgs)
                actionText += self.xlator.codeSwitchBreak(caseAction, indent)
            defaultCase=action['defaultCase']
            if defaultCase and len(defaultCase)>0:
                actionText+=indent+"default: "
                actionText += blockPrefix + self.codeActionSeq(defaultCase, indent, returnType, genericArgs)
            else: actionText+=indent+"default: break;\n"
            actionText += indent + "}\n"
        elif (typeOfAction =='actionSeq'):
            cdlog(5, "Action Sequence")
            actionListIn = action['actionList']
            actionListText = ''
            for action in actionListIn:
                actionListOut = self.codeAction(action, indent + "    ", returnType, genericArgs)
                actionListText += actionListOut
            blockPrefix = self.xlator.blockPrefix
            actionText += indent + blockPrefix + "{\n" + actionListText + indent + '}\n'
        elif (typeOfAction =='protect'):
            cdlog(5, "Protect Statement")
            mutex           = action['mutex'][0]
            criticalSection = action['criticalSection']
            criticalText    = self.codeCriticalSection(action['criticalSection'], indent, returnType, genericArgs)
            [mutex, mtxTypeSpec]=self.codeExpr(mutex, None, None, 'RVAL', genericArgs)
            actionText = self.xlator.codeProtectBlock(mutex, criticalText, indent)
        else:
            print("error in codeAction: ", action)
            exit(2)
        return actionText

    def codeActionSeq(self, actSeq, indent, returnType, genericArgs):
        self.localVarsAllocated.append(["STOP",''])
        actSeqText=''
        actSeqText += '{\n'
        for action in actSeq:
            actionText = self.codeAction(action, indent + '    ', returnType, genericArgs)
            actSeqText += actionText
        actSeqText += indent + '}\n'
        localVarRecord=['','']
        while(localVarRecord[0] != 'STOP'):
            localVarRecord=self.localVarsAllocated.pop()
        return actSeqText

    #### CONSTRUCTORS ######################################################
    def getCtorModelParams(self, className):
        modelParams  = []
        for field in progSpec.generateListOfFieldsToImplement(self.classStore, className):
            tSpec       = progSpec.getTypeSpec(field)
            fType       = progSpec.fieldTypeKeyword(tSpec)
            fOwner      = progSpec.getOwner(tSpec)
            progSpec.isOldContainerTempFuncErr(tSpec, 'getCtorModelParams '+self.currentObjName)
            isCtnr = progSpec.isNewContainerTempFunc(tSpec)
            if fType=='flag' or fType=='mode' or fOwner=='const' or fOwner=='we' or (tSpec['argList'] or tSpec['argList']!=None) or (isCtnr and not progSpec.typeIsPointer(tSpec)):
                continue
            modelParams.append(field)
        return modelParams

    def chooseCtorModelParams(self, tSpec, paramList,genericArgs):
        fTypeKW      = progSpec.fieldTypeKeyword(tSpec)
        [argListStr, fieldIDArgList] = self.getFieldIDArgList(fTypeKW, genericArgs)
        REF = self.CheckObjectVars(fTypeKW, fTypeKW, "")
        if REF: modelParams = progSpec.getArgList(REF)
        else: modelParams  = self.getCtorModelParams(fTypeKW)
        return modelParams

    def getCtorArgTypes(self, className, genericArgs):
        ctorArgTypes = []
        modelParams  = self.getCtorModelParams(className)
        for field in modelParams:
            tSpec     = progSpec.getTypeSpec(field)
            fType     = progSpec.fieldTypeKeyword(tSpec)
            fOwner    = progSpec.getOwner(tSpec)
            if(fOwner != 'me' and fOwner != 'my') or (isinstance(fType, str) and ((self.isArgNumeric(fType) or fType=="string") or ('value' in field and field['value']!=None))):
                cvrtType = self.convertType(tSpec, 'var', genericArgs)
                ctorArgTypes.append(cvrtType)
        return ctorArgTypes

    def getFieldDefaultVal(self, field, genericArgs):
        defaultVal  = ''
        tSpec       = progSpec.getTypeSpec(field)
        fType       = progSpec.fieldTypeKeyword(tSpec)
        fOwner      = progSpec.getOwner(tSpec)
        fieldName   = field['fieldName']
        cvrtType = self.convertType(tSpec, 'var', genericArgs)
        if(fOwner != 'me'):
            if(fOwner != 'my'):
                defaultVal = self.xlator.nullValue
        elif (isinstance(fType, str)):
            if 'value' in field and field['value']!=None:
                [defaultVal, defaultValueTypeSpec] = self.codeExpr(field['value'][0], None, tSpec, 'RVAL', genericArgs)
            else:
                if(self.typeIsInteger(fType)):    defaultVal = "0"
                elif(self.typeIsRational(fType)): defaultVal = "0.0"
                elif(fType=="_atomic_uint64"):    defaultVal = '0'
                elif(fType=="string"):            defaultVal = '""'
                elif(fType=="bool"):              defaultVal = 'false'
                else: # handle structs if needed
                    if 'value' in field and field['value']!=None:
                        [defaultVal, defaultValueTypeSpec] = self.codeExpr(field['value'][0], None, tSpec, 'RVAL', genericArgs)
        return defaultVal

    def getStructFieldsForCtor(self, className, typeArgList):
        classDef     = progSpec.findSpecOf(self.classStore[0], className, "struct")
        genericArgs  = progSpec.getGenericArgs(classDef)
        ctorInit     = ""
        ctorArgs     = ""
        copyCtorArgs = ""
        count        = 0
        modelParams  = self.getCtorModelParams(className)
        for field in modelParams:
            tSpec       = progSpec.getTypeSpec(field)
            fType       = progSpec.fieldTypeKeyword(tSpec)
            fOwner      = progSpec.getOwner(tSpec)
            fieldName   = field['fieldName']
            cvrtType = self.convertType(tSpec, 'var', genericArgs)
            cdlog(4, "Coding Constructor: {} {} {} {}".format(className, fieldName, fType, cvrtType))
            if(typeArgList != None and fType in typeArgList):isTemplateVar = True
            else: isTemplateVar = False
            defaultVal  = self.getFieldDefaultVal(field, genericArgs)
            if defaultVal != '':
            #    if count == 0: defaultVal = ''  # uncomment this line to NOT generate a default value for the first constructor argument.
                if count>0: ctorArgs +=  ', '
                ctorArgs += self.xlator.codeConstructorArgText(fieldName, count, cvrtType, defaultVal)
                ctorInit += self.xlator.codeConstructorInit(fieldName, count, defaultVal)
                count += 1
            copyCtorArgs += self.xlator.codeCopyConstructor(fieldName, isTemplateVar)
        return [ctorInit, ctorArgs, copyCtorArgs, count]

    def codeConstructor(self, className, tags, typeArgList, genericArgs):
        baseType = progSpec.isWrappedType(self.classStore, className)
        flatClassName = progSpec.flattenObjectName(className)
        if(baseType!=None): return ''
        if not className in self.classStore[0]: return ''
        cdlog(4, "Generating Constructor for: {}".format(className))
        [ctorInit, ctorArgs, copyCtorArgs, count] = self.getStructFieldsForCtor(className,typeArgList)
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
        if ctorArgs and parentClass:
            ctorArgTypes       = self.getCtorArgTypes(className, genericArgs)
            parentCtorArgTypes = self.getCtorArgTypes(parentClass, genericArgs)
            if ctorArgTypes == parentCtorArgTypes: ctorOvrRide = 'override '
        if count>0 or funcBody != '':
            ctorCode += self.xlator.codeConstructors(flatClassName, ctorArgs, ctorOvrRide, ctorInit, copyCtorArgs, funcBody, callSuper)
        return ctorCode

    #### STRUCT FIELDS #####################################################
    def codeFunction(self, className, classDef, field, typeArgList, genericArgs, indent):
        structCode   = ""
        funcDefCode  = ""
        globalFuncs  = ""
        tSpec        = progSpec.getTypeSpec(field)
        fTypeKW      = progSpec.fieldTypeKeyword(tSpec)
        fieldName    = field['fieldName']
        fieldID      = field['fieldID']
        argList      = progSpec.getArgList(field)
        sizeArgList  = len(argList)
        overRideOper = False
        isStatic     = False
        if fieldName[0:2] == "__" and self.xlator.iteratorsUseOperators:
            fieldNameIn  = fieldName
            fieldName    = self.xlator.specialFunction(fieldName, classDef)
            if fieldNameIn != fieldName: isStatic = True
            overRideOper = True
        #### ARGLIST
        argListText  = ""
        argListCount = 0
        if sizeArgList==0: argListText='' #'void'
        elif argList[0]=='<%': argListText=argList[1][0]        # Verbatim.arguments
        else:
            for arg in argList:
                if(argListCount>0): argListText+=", "
                argListCount+=1
                argTSpec     = progSpec.getTypeSpec(arg)
                argOwner     = progSpec.getOwner(argTSpec)
                argFieldName = arg['fieldName']
                argFieldType = progSpec.fieldTypeKeyword(argTSpec)
                if progSpec.typeIsPointer(argTSpec): arg
                self.applyStructImplemetation(argTSpec,className,argFieldName)
                argCvrtType  = self.convertType(argTSpec, 'arg', genericArgs)
                argListText += self.xlator.codeArgText(argFieldName, argCvrtType, argOwner, argTSpec, overRideOper, typeArgList)
                self.localArgsAllocated.append([argFieldName, argTSpec])  # localArgsAllocated is a global variable that keeps track of nested function arguments and local vars.
        #### RETURN TYPE ###########################################
        FirstReturnType = copy.copy(tSpec) # TODO: Un-Hardcode FirstReturnType, typeSpec?
        if(fTypeKW[0] != '<%'): pass #self.registerType(className, fieldName, cvrtType, typeDefName)

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
        cvrtType     = self.convertType(tSpec, 'func', genericArgs)
        if(cvrtType=='none'): cvrtType = ''
        [structCode, funcDefCode, globalFuncs]=self.xlator.codeFuncHeaderStr(className, fieldName, field, cvrtType, argListText, self.localArgsAllocated, inheritMode, typeArgList, self.isNestedClass, overRideOper, isStatic, indent)
        #### FUNC BODY #############################################
        if abstractFunction: # i.e., if no function body is given.
            cdlog(5, "Function "+fieldID+" has no implementation defined.")
            funcText = self.xlator.getVirtualFuncText(field)
            #cdErr("Function "+fieldID+" has no implementation defined.")
        else:
            extraCodeForTopOfFuntion = self.xlator.extraCodeForTopOfFuntion(argList)
            if cvrtType=='' and 'flagsVarNeeded' in classDef and classDef['flagsVarNeeded']==True:
                extraCodeForTopOfFuntion+="    flags=0;"
            verbatimText=field['value'][1]
            if (verbatimText!=''):                                      # This function body is 'verbatim'.
                if(verbatimText[0]=='!'): # This is a code conversion pattern. Don't write a function decl or body.
                    structCode  = ""
                    funcText    = ""
                    funcDefCode = ""
                    globalFuncs = ""
                else:
                    funcText=verbatimText + "\n\n"
                    if globalFuncs!='': self.ForwardDeclsForGlobalFuncs += globalFuncs+";       \t\t // Forward Decl\n"
            elif field['value'][0]!='':
                funcBodyIndent = self.xlator.funcBodyIndent
                if self.xlator.useNestedClasses and self.isNestedClass: funcBodyIndent = indent
                funcText =  self.codeActionSeq(field['value'][0], funcBodyIndent, FirstReturnType, genericArgs)
                if extraCodeForTopOfFuntion!='':
                    funcText = '{\n' + extraCodeForTopOfFuntion + funcText[1:]
                if globalFuncs!='': self.ForwardDeclsForGlobalFuncs += globalFuncs+";       \t\t // Forward Decl\n"
            else: cdErr("ERROR: In codeFields: no funcText or funcTextVerbatim found")

        if self.xlator.funcsDefInClass or self.isNestedClass: structCode += funcText
        elif(className=='GLOBAL'):
            if(fieldName=='main'): funcDefCode += funcText
            else: globalFuncs += funcText
        else: funcDefCode += funcText
        return [structCode, funcDefCode, globalFuncs]

    def codeSpaceSeq(self, className, field, indent):
        structCode      = ""
        funcDefCode     = ""
        globalFuncs     = ""
        topFuncDefCode  = ""
        if self.xlator.useNestedClasses:
            fieldName       = field['fieldName']
            tags            = field['tags']
            self.isNestedClass = True
            self.currentObjName = fieldName
            [innerStructCode, funcCode, globalCode]=self.codeStructFields(fieldName, tags, indent+'    ')
            innerStructCode = indent + 'struct ' + fieldName + '{\n' +innerStructCode + indent + '};\n'
            structCode = innerStructCode
            self.currentObjName = className
            self.isNestedClass = False
        return [structCode, funcDefCode, globalFuncs, topFuncDefCode]

    def codeTimeSeq(self, className, classDef, field, typeArgList, genericArgs, tags, indent):
        funcDefCode    = ""
        structCode     = ""
        globalFuncs    = ""
        topFuncDefCode = ""
        funcText       = ""
        tSpec          = progSpec.getTypeSpec(field)
        fTypeKW        = progSpec.fieldTypeKeyword(tSpec)
        fieldID        = field['fieldID']
        fieldName      = field['fieldName']
        isAllocated    = field['isAllocated']
        fieldValue     = field['value']
        fieldArglist   = progSpec.getArgList(tSpec)
        paramList      = field['paramList']
        cdlog(4, "FieldName: {}".format(fieldName))

        self.applyStructImplemetation(tSpec,className,fieldName)
        if progSpec.doesClassHaveProperty(self.classStore, fTypeKW, 'metaClass'):
            tagToFind       = "classOptions."+progSpec.flattenObjectName(fieldID)
            classOptionsTag = progSpec.fetchTagValue(tags, tagToFind)
            if classOptionsTag != None and "useClass" in classOptionsTag:
                useClassTag = classOptionsTag["useClass"]
                fTypeKW[0]  = useClassTag
        cvrtType    = self.convertType(tSpec, 'var', genericArgs)
        tSpec       = self.getGenericTypeSpec(genericArgs, tSpec)
        fieldOwner  = progSpec.getOwner(tSpec)
        ## ASSIGNMENTS###############################################
        if fieldName=='opAssign': fieldName='operator='

        # CALCULATE RHS
        if(fieldValue == None):
            if className == "GLOBAL" and isAllocated==True: # Allocation for GLOBAL handled in appendGLOBALInitCode()
                isAllocated = False
                paramList   = None
            RHS=self.xlator.codeVarFieldRHS_Str(fieldName, cvrtType, tSpec, paramList, isAllocated, typeArgList, genericArgs)
            # print("    RHS none: ", RHS)
        elif(fieldOwner=='const'):
            if isinstance(fieldValue, str): RHS = ' = "'+ fieldValue + '"'       #TODO:  make test case
            else: RHS = " = "+ self.codeExpr(fieldValue[0], tSpec, tSpec, 'RVAL', genericArgs)[0]
            #print("    RHS const: ", RHS)
        elif(fieldArglist==None):
            RHS = " = " + self.codeExpr(fieldValue[0], tSpec, tSpec, 'RVAL', genericArgs)[0]
            #print("    RHS var: ", RHS)
        else:
            RHS = " = "+ str(fieldValue)
            #print("    RHS func or array")

        ############ CODE MEMBER VARIABLE ##########################################################
        if(fieldOwner=='const'):
            [structCode, topFuncDefCode] = self.xlator.codeConstField_Str(cvrtType, fieldName, RHS, className, indent)
        elif(fieldArglist==None):
            [structCode, funcDefCode] = self.xlator.codeVarField_Str(cvrtType, tSpec, fieldName, RHS, className, tags, typeArgList, indent)
        ###### ArgList exists so this is a FUNCTION###########
        else: [structCode, funcDefCode, globalFuncs] = self.codeFunction(className, classDef, field, typeArgList, genericArgs, indent)
        return [structCode, funcDefCode, globalFuncs, topFuncDefCode]

    def codeStructFields(self, className, tags, indent):
        cdlog(3, "Coding fields for {}...".format(className))
        ####################################################################
        globalFuncsAcc   = ""
        funcDefCodeAcc   = ""
        structCodeAcc    = ""
        topFuncDefCodeAcc= "" # For defns that must appear first in the code. TODO: sort items instead
        classDef    = progSpec.findSpecOf(self.classStore[0], className, "struct")
        typeArgList = progSpec.getTypeArgList(className)
        genericArgs = progSpec.getGenericArgs(classDef)
        for field in progSpec.generateListOfFieldsToImplement(self.classStore, className):
            ################################################################
            ### extracting FIELD data
            ################################################################
            self.localArgsAllocated = []
            tSpec   = progSpec.getTypeSpec(field)
            fTypeKW = progSpec.fieldTypeKeyword(tSpec)
            if(fTypeKW=='flag' or fTypeKW=='mode'): continue
            if 'value' in field and field['value']!=None and len(field['value'])>1:
                verbatimText=field['value'][1]      # This function body is 'verbatim'.
                if (verbatimText!='' and verbatimText[0]=='!'): continue  # This is a code conversion pattern. Don't write a function decl or body.
            if(fTypeKW=='model' or fTypeKW=='struct'):
                [structCode, funcDefCode, globalFuncs, topFuncDefCode] = self.codeSpaceSeq(className, field, indent)
            else:
                [structCode, funcDefCode, globalFuncs, topFuncDefCode] = self.codeTimeSeq(className, classDef, field, typeArgList, genericArgs, tags, indent)
            ## Accumulate field code
            structCodeAcc     += structCode
            funcDefCodeAcc    += funcDefCode
            globalFuncsAcc    += globalFuncs
            topFuncDefCodeAcc += topFuncDefCode

        # TODO: Remove this Hard Coded widget. It should apply to any abstract class.
        if self.xlator.MakeConstructors and (className!='GLOBAL')  and (className!='widget'):
            ctorCode       = self.codeConstructor(className, tags, typeArgList, genericArgs)
            structCodeAcc += "\n"+ctorCode
        funcDefCodeAcc     = topFuncDefCodeAcc + funcDefCodeAcc
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
            classDef = progSpec.findSpecOf(self.classStore[0], className, 'struct')
            if(classDef==None): continue
            implMode=progSpec.searchATagStore(classDef['tags'], 'implMode')
            if(implMode): implMode=implMode[0]
            if(implMode!=None and not (implMode=="declare" or implMode[:7]=="inherit" or implMode[:9]=="implement")):  # "useLibrary"
                cdlog(2, "SKIPPING: {} {}".format(className, implMode))
                continue
            if className in progSpec.MarkedObjects: libNameList.append(className)
            else: progNameList.append(className)
        classList=libNameList + progNameList
        # TODO: make list global then return early if global list the same size as classList
        classList=self.sortClassesForDependancies(classList)
        if self.xlator.LanguageName=='Java':
            classList.pop(classList.index('GLOBAL'))
            classList.insert(0,'GLOBAL')
        return classList

    def codeOneStruct(self, tags, constFieldCode, className):
        classRecord    = None
        constsEnums    = ""  # this isn't used. Remove it?
        dependancies   = []
        self.currentObjName = className
        funcCode       = ''
        if((not self.xlator.doesLangHaveGlobals) or className != 'GLOBAL'): # and ('enumList' not in self.classStore[0][className]['typeSpec'])):
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
                if self.xlator.doesLangHaveGlobals:
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
                if isinstance(classImplements, list):
                    if len(classImplements)==0:   classImplements = None
                    elif len(classImplements)==1:
                        classImplements = classImplements[0]
                        if len(classImplements)==0:   classImplements = None

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

                callableStructFields=[]
                progSpec.populateCallableStructFields(callableStructFields, self.classStore, className)
                [structCode, funcCode, globalCode]=self.codeStructFields(className, tags, '    ')
                structCode+= constFieldCode
                if className=='GLOBAL' and not self.xlator.doesLangHaveGlobals: structCode += '\n    _ModeStrings modeStrings = new _ModeStrings();\n'

                attrList = classDef['attrList']
                if classAttrs!='': attrList.append(classAttrs)  # TODO: should append all items from classAttrs
                LangFormOfObjName = progSpec.flattenObjectName(className)
                [structCodeOut, forwardDeclsOut] = self.xlator.codeStructText(self.classStore, attrList, parentClass, classInherits, classImplements, LangFormOfObjName, structCode, tags)
                comments = classDef['comments']
                commentStr = ''
                if comments:
                    for comment in comments:
                        commentStr += self.codeComment(comment[0], comment[1])
                    structCodeOut = commentStr + structCodeOut
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
        classDef = progSpec.findSpecOf(self.classStore[0], className, "struct")
        for field in progSpec.generateListOfFieldsToImplement(self.classStore, className):
            fTypeKW      = progSpec.fieldTypeKeyword(field)
            fieldName    = field['fieldName'];
            inheritsMode = False

            try:
                if self.classStore[0][fTypeKW]['tags']['inherits']['fieldType'].get('altModeIndicator', 0):
                    inheritsMode = True
            except (KeyError, TypeError) as e:
                cdlog(6, "{}\n failed dict lookup in codeFlagAndModeFields".format(e))

            if fTypeKW=='flag' or fTypeKW=='mode' or inheritsMode:
                flagsVarNeeded=True
                fieldName = progSpec.flattenObjectName(fieldName)
                if fTypeKW=='flag':
                    cdlog(6, "flag: {}".format(fieldName))
                    structEnums += "    " + self.xlator.getConstIntFieldStr(fieldName, hex(1<<bitCursor), 64) +" \t// Flag: "+fieldName+"\n"
                    self.StaticMemberVars[fieldName]  =className
                    bitCursor += 1;
                elif fTypeKW=='mode':
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
                    enumSize= len(self.classStore[0][fTypeKW]['tags']['inherits']['fieldType']['altModeList'].asList())
                    numEnumBits=self.bitsNeeded(enumSize)
                    enumMask=((1 << numEnumBits) - 1) << bitCursor

                    offsetVarName = fieldName+"Offset"
                    maskVarName   = fieldName+"Mask"
                    structEnums += "    "+self.xlator.getConstIntFieldStr(offsetVarName, hex(bitCursor), 64)
                    structEnums += "    "+self.xlator.getConstIntFieldStr(maskVarName,   hex(enumMask), 64) + "\n"

                    enumList=self.classStore[0][fTypeKW]['tags']['inherits']['fieldType']['altModeList'].asList()
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
            try:
                if self.classStore[0][className]['tags']['inherits']['fieldType']['altModeIndicator']:
                    enumVals = self.classStore[0][className]['tags']['inherits']['fieldType']['altModeList']
                    self.inheritedEnums[className] = enumVals
            except (TypeError, KeyError) as e:
                cdlog(6, "{}\n failed dict lookup in codeOneStruct".format(e))
            self.currentObjName=className
            CodeDogAddendumsAcc=''
            [needsFlagsVar, structEnums, CodeDogAddendums]=self.codeFlagAndModeFields(className, tags)
            objectNameBase=progSpec.flattenObjectName(className) #progSpec.baseStructName(className)
            if not objectNameBase in self.constFieldAccs: self.constFieldAccs[objectNameBase]=""
            self.constFieldAccs[objectNameBase]+=structEnums
            CodeDogAddendumsAcc+=CodeDogAddendums
            if(needsFlagsVar):
                CodeDogAddendumsAcc += 'me _atomic_uint64: flags\n'
            if CodeDogAddendumsAcc!='':
                codeDogParser.AddToObjectFromText(self.classStore[0], self.classStore[1], progSpec.wrapFieldListInObjectDef(className,  CodeDogAddendumsAcc ), 'Flags and Modes for class '+className)
            self.currentObjName=''

    def codeAllNonGlobalStructs(self, tags, classRecords, structsToImplement):
        cdlog(2, "CODING FLAGS and MODES...")
        # Write the class
        for className in structsToImplement:
            typeArgList = progSpec.getTypeArgList(className)
            classDef = progSpec.findSpecOf(self.classStore[0], className, "struct")
            if self.xlator.useNestedClasses and 'fromNested' in classDef:
                classRecords[className]='skip'
            elif self.xlator.renderGenerics=='False' or typeArgList == None or progSpec.isWrappedType(self.classStore, className):
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
                                [newText, argTSpec]= self.codeExpr(P[0], {}, None, None, 'PARAM', genericArgs)
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
        if libID in tagsFromLibFiles:
            libFileTags = tagsFromLibFiles[libID]
            if 'embedAboveIncludes'in libFileTags: self.libEmbedAboveIncludes+= libFileTags['embedAboveIncludes']
            if 'embedVeryHigh'     in libFileTags: self.libEmbedVeryHigh     += libFileTags['embedVeryHigh']
            if 'embedHigh'         in libFileTags: self.libEmbedCodeHigh     += libFileTags['embedHigh']
            if 'embedLow'          in libFileTags: self.libEmbedCodeLow      += libFileTags['embedLow']
            if 'initCode'          in libFileTags: self.libInitCodeAcc       += libFileTags['initCode']
            if 'deinitCode'        in libFileTags: self.libDeinitCodeAcc      = libFileTags['deinitCode'] + self.libDeinitCodeAcc + "\n"

            if 'interface' in libFileTags:
                if 'libFiles' in libFileTags['interface']:
                    libFiles = libFileTags['interface']['libFiles']

                    for libFile in libFiles:
                        if libFile.startswith('pkg-config'):
                            self.buildStr_libs += "`"
                            self.buildStr_libs += libFile
                            self.buildStr_libs += "` "
                        else:
                            if libFile =='pthread': self.buildStr_libs += '-pthread ';
                            else: self.buildStr_libs += "-l"+libFile+ " "

                if 'headers' in libFileTags['interface']:
                    libHeaders = libFileTags['interface']['headers']
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
            cdlog(1, 'ATTACHING LIBRARY: '+str(libFilename))
            [headerStrOut, headerTopStr] = self.integrateLibrary(tags, tagsFromLibFiles, libFilename)
            headerStr = headerTopStr + headerStr + headerStrOut
            macroDefs= {}
            [tagStore, buildSpecs, FileClasses, newClasses] = self.loadProgSpecFromDogFile(libFilename, self.classStore[0], self.classStore[1], tags[0], macroDefs)
        return headerStr

    def convertTemplateClasses(self, tags):
        for className in self.classStore[1]:
            for field in progSpec.generateListOfFieldsToImplement(self.classStore, className):
                tSpec     = progSpec.getTypeSpec(field)
                fieldName = field['fieldName']
                self.applyStructImplemetation(tSpec,className,fieldName)

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
                if(not self.xlator.doesLangHaveGlobals or className != 'GLOBAL') and (self.xlator.renderGenerics=='False' or typeArgList == None):
                    if not isinstance(classRecords[className],str): # if not 'skip'
                        classRecord    = classRecords[className]
                        constsEnums   += classRecord[0]
                        forwardDecls  += classRecord[1]
                        structCodeAcc += classRecord[2]
                        funcCodeAcc   += classRecord[3]

            forwardDecls += self.funcDeclAcc
            funcCodeAcc  += self.funcDefnAcc
            if not self.xlator.doesLangHaveGlobals: structCodeAcc += self.codeModeStringsStruct()

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
        self.applyPatterns(classes, tags)
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
        topBottomStrings = self.xlator.codeMain(self.classStore, tags)
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
        if not ('CodeDog' in TopLevelTags['featuresNeeded']):
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
                progSpec.setFeatureNeeded(TopLevelTags, 'BigNumbers', progSpec.storeOfBaseTypesUsed[typeName])

    patternsToApply = []
    def applyPatterns(self, classes, tags):
        for patternSpec in self.patternsToApply:
            pattName   =patternSpec['patternName']
            patternArgs=patternSpec['patternParams']
            patternTags=patternSpec['patternTags']   # [newTags, topTags]
            if self.tagStore==None:
                if patternTags[1] != {}: TopLevelTags=patternTags[1] # topTags
                else: TopLevelTags=patternTags[0] # newTags
            else: TopLevelTags=self.tagStore
            cdlog(1, "APPLYING PATTERN: {}: {}".format( pattName, patternArgs))

            if   pattName=='makeGUI':            pattern_GUI_Toolkit.apply(classes, TopLevelTags)
            elif pattName=='codeModelToGUI':     pattern_MakeGUI.apply(classes, patternTags, patternArgs[0])
            elif pattName=='ManageCmdLine':      pattern_ManageCmdLine.apply(classes, tags[0])
            elif pattName=='GeneratePtrSymbols': pattern_GenSymbols.apply(classes, patternTags[0], patternArgs)
            elif pattName=='codeModelDashes':    pattern_DispData.apply(classes, patternTags, patternArgs[0], patternArgs[1])
            elif pattName=='codeDataDisplay':    pattern_DispData.apply(classes, patternTags, patternArgs[0], patternArgs[1])
            elif pattName=='codeModelToString':  pattern_DispData.apply(classes, patternTags, patternArgs[0], 'text')
            elif pattName=='codeModelToProteus': pattern_DispData.apply(classes, patternTags, patternArgs[0], 'Proteus')
            elif pattName=='makeMenu':           pattern_MakeMenu.apply(classes, patternTags, patternArgs)
            elif pattName=='makeRBMap':          pattern_RBMap.apply(   classes, patternTags, patternArgs[0], patternArgs[1])
            elif pattName=='makeStyler':         pattern_MakeStyler.apply(classes, patternTags, patternArgs[0])
            else: cdErr("\nPattern {} not recognized.\n\n".format(pattName))
        self.patternsToApply.clear()

    def ScanAndEnquePatterns(self, classes, topTags, newTags):
        #if len(self.classStore[1])>0: cdlog(1, "Enqueing Patterns...")
        itemsToDelete=[]; count=0;
        for item in classes[1]:
            if item[0]=='!':
                itemsToDelete.append(count)
                pattNameIdx=item[1:]
                pattParse = classes[0][pattNameIdx]
                patternSpec = {'patternName':pattParse['name'], 'patternParams':pattParse['parameters'], 'patternTags':[newTags, topTags]}
                self.patternsToApply.append(patternSpec)
            count+=1
        for toDel in reversed(itemsToDelete):
            del(classes[1][toDel])

    def extractNestedClasses(self, fileClasses, newClassNames):
        for className in newClassNames:
            for field in fileClasses[0][className]['fields']:
                tSpec        = progSpec.getTypeSpec(field)
                fTypeKW      = progSpec.fieldTypeKeyword(tSpec)
                if(fTypeKW=='model' or fTypeKW=='struct'):
                    if tSpec['owner']!='const': cdErr("Non const classes are not currently supported.")
                    fields       = []
                    fieldName    = field['fieldName']
                    structFields = field['value'][0]
                    fieldTSpec   = progSpec.getTypeSpec(field)
                    argList      = progSpec.getArgList(field)
                    for fieldVal in structFields:
                        if not 'fieldDef' in fieldVal: cdErr("No fieldDef in inner class.")
                        newField = fieldVal['fieldDef']
                        newField['fieldID'] = fieldName+newField['fieldID']
                        fields.append(newField)
                    if argList!=None:
                        newArgList = []
                        for arg in argList:
                            argTypeKW = progSpec.fieldTypeKeyword(arg)
                            newArgList.append(argTypeKW)
                        progSpec.addTypeArgList(fieldName, newArgList)

                    progSpec.addObject(fileClasses[0], fileClasses[1], fieldName, 'struct', 'SEQ',fileClasses[0][className]['libName'],["//*", "Added nested class."])
                    fieldTags = []
                    if 'tags' in field: fieldTags = field['tags']
                    progSpec.addObjTags(fileClasses[0], fieldName, 'struct', fieldTags)
                    fileClasses[0][fieldName]['fields']     = fields
                    fileClasses[0][fieldName]['libLevel']   = fileClasses[0][className]['libLevel']
                    fileClasses[0][fieldName]['fromNested'] = className
                    self.nestedClasses[fieldName] = className

    def loadProgSpecFromDogFile(self, filename, ProgSpec, objNames, topLvlTags, macroDefs):
        codeDogStr = progSpec.stringFromFile(filename)
        codeDogStr = libraryMngr.processIncludedFiles(codeDogStr, filename)
        [tagStore, buildSpecs, fileClasses, newClassNames] = codeDogParser.parseCodeDogString(codeDogStr, ProgSpec, objNames, macroDefs, filename)
        self.GroomTags(tagStore)
        self.extractNestedClasses(fileClasses, newClassNames)
        self.ScanAndEnquePatterns(fileClasses, topLvlTags, tagStore)
        stringStructs.CreateStructsForStringModels(fileClasses, newClassNames, tagStore)
        return [tagStore, buildSpecs, fileClasses,newClassNames]

    def __init_(self):
        print("INIT")
