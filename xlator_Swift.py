#xlator_Swift.py
import progSpec
import codeDogParser
from xlator import Xlator
from progSpec import cdlog, cdErr, isStruct
from codeGenerator import CodeGenerator

class Xlator_Swift(Xlator):
    codeGen               = CodeGenerator()
    LanguageName          = "Swift"
    BuildStrPrefix        = ""
    fileExtension         = ".swift"
    typeForCounterInt     = "var"
    GlobalVarPrefix       = ""
    PtrConnector          = "!."                     # Name segment connector for pointers.
    ObjConnector          = "."                      # Name segment connector for classes.
    NameSegConnector      = "."
    NameSegFuncConnector  = "()."
    doesLangHaveGlobals   = True
    funcBodyIndent        = "    "
    funcsDefInClass       = True
    MakeConstructors      = True
    blockPrefix           = "do"
    usePrefixOnStatics    = True
    iteratorsUseOperators = False
    renderGenerics        = "True"
    renameInitFuncs       = True
    useAllCtorArgs        = False
    nullValue             = "nil"
    hasMacros             = False

    ###### Routines to track types of identifiers and to look up type based on identifier.
    def implOperatorsAsFuncs(self, fTypeKW):
        return False
    def getContainerType(self, typeSpec, actionOrField):
        idxType=''
        if progSpec.isNewContainerTempFunc(typeSpec):
            ctnrTSpec = progSpec.getContainerSpec(typeSpec)
            if 'owner' in ctnrTSpec: owner=progSpec.getOwnerFromTypeSpec(ctnrTSpec)
            else: owner = 'me'
            if 'indexType' in ctnrTSpec:
                if 'IDXowner' in ctnrTSpec['indexType']:
                    idxOwner = ctnrTSpec['indexType']['IDXowner'][0]
                    idxType  = ctnrTSpec['indexType']['idxBaseType'][0][0]
                    idxType  = self.applyOwner(typeSpec, idxOwner, idxType)
                else:
                    idxType=ctnrTSpec['indexType']['idxBaseType'][0][0]
            else:
                idxType = progSpec.getFieldType(typeSpec)
            if(isinstance(ctnrTSpec['datastructID'], str)):
                datastructID = ctnrTSpec['datastructID']
            else:   # it's a parseResult
                datastructID = ctnrTSpec['datastructID'][0]
        else:
            owner = progSpec.getOwnerFromTypeSpec(typeSpec)
            datastructID = 'None'
        return [datastructID, idxType, owner]

    def adjustBaseTypes(self, fieldType, isContainer):
        langType = ''
        if(isinstance(fieldType, str)):
            if(fieldType=='uint8' or fieldType=='uint16'or fieldType=='uint32'): return 'UInt32'
            elif(fieldType=='int8' or fieldType=='int16' or fieldType=='int32'): return 'Int32'
            elif(fieldType=='uint64'): return 'UInt64'
            elif(fieldType=='int64'):  return 'Int64'
            elif(fieldType=='int'):    return 'Int'
            elif(fieldType=='bool'):   return 'Bool'
            elif(fieldType=='void'):   return 'Void'
            elif(fieldType=='float'):  return 'Float'
            elif(fieldType=='double'): return 'Double'
            elif(fieldType=='string'): return 'String'
            elif(fieldType=='char'):   return 'Character'
            langType=progSpec.flattenObjectName(fieldType)
        else: langType=progSpec.flattenObjectName(fieldType[0])
        return langType

    def applyOwner(self, typeSpec, owner, langType):
        if owner=='me':
            langType = langType
        elif owner=='my':
            langType = langType
        elif owner=='our':
            langType = langType
        elif owner=='their':
            langType = langType
        elif owner=='itr':
            reqTagList  = progSpec.getReqTagList(typeSpec)
            itrType     = progSpec.fieldTypeKeyword(progSpec.getItrTypeOfDataStruct(typeSpec))
            genericArgs = progSpec.getGenericArgsFromTypeSpec(typeSpec)
            langType    = self.codeGen.generateGenericStructName(itrType, reqTagList, genericArgs)
        elif owner=='const':
            langType = langType
        elif owner=='we':
            langType += 'public static'
        else: cdErr("ERROR: Owner of type not valid '" + owner + "'")
        return langType

    def getUnwrappedClassOwner(self, classes, typeSpec, fieldType, varMode, ownerIn):
        ownerOut = ownerIn
        owner=typeSpec['owner']
        baseType = progSpec.isWrappedType(classes, fieldType)
        if baseType!=None:  # TODO: When this is all tested and stable, un-hardcode and optimize this!!!!!
            if 'ownerMe' in baseType:
                if owner=='their':
                    if varMode=='arg': owner='their'
                    else: owner = 'their'
                elif owner=='me':
                    owner = 'their'
            else:
                if varMode=='var':owner=baseType['owner']   # TODO: remove this condition: accomodates old list type generated in stringStructs
                else: owner=ownerIn
        return owner

    def getReqTagString(self, classes, typeSpec):
        reqTagStr  = ""
        reqTagList = progSpec.getReqTagList(typeSpec)
        if(reqTagList != None):
            reqTagStr = "<"
            count = 0
            for reqTag in reqTagList:
                reqOwnr     = progSpec.getOwnerFromTemplateArg(reqTag)
                varTypeKW   = progSpec.getTypeFromTemplateArg(reqTag)
                unwrappedOwner=self.getUnwrappedClassOwner(classes, typeSpec, varTypeKW, 'alloc', reqOwnr)
                unwrappedKW = progSpec.getUnwrappedClassFieldTypeKeyWord(classes, varTypeKW)
                reqType     = self.adjustBaseTypes(unwrappedKW, True)
                if(count>0): reqTagStr += ", "
                reqTagStr += reqType
                count += 1
            reqTagStr += ">"
        return reqTagStr

    def xlateLangType(self, classes, typeSpec, owner, fTypeKW, varMode, actionOrField):
        # varMode is 'var' or 'arg' or 'alloc'. Large items are passed as pointers
        innerType=''
        langType = self.adjustBaseTypes(fTypeKW, progSpec.isNewContainerTempFunc(typeSpec))
        langType = self.applyOwner(typeSpec, owner, langType)
        if langType=='TYPE ERROR': print(langType, owner, fTypeKW);
        innerType = langType
        if progSpec.isNewContainerTempFunc(typeSpec): return [langType, innerType]
        if varMode != 'alloc': innerType = self.applyOwner(typeSpec, owner, langType)
        return [langType, innerType]

    def makePtrOpt(self, typeSpec):
        # Make pointer field variables optionals
        fTypeKW = progSpec.fieldTypeKeyword(typeSpec)
        if progSpec.typeIsPointer(typeSpec) and (fTypeKW != 'string' or fTypeKW != 'String'): return('!')
        return('')

    def codeIteratorOperation(self, itrCommand, fieldType):
        result = ''
        if itrCommand=='goNext':  result='%0.next()'
        elif itrCommand=='goPrev':result='%0.Swift ERROR!'
        elif itrCommand=='key':   result='%0.getKey()'
        elif itrCommand=='val':   result='%0.getValue()'
        return result

    def recodeStringFunctions(self, name, typeSpec, lenParams):
        if name == "size":
            typeSpec['codeConverter']='%0.count'
            typeSpec['fieldType']='int'
        elif name == "subStr":
            typeSpec['codeConverter']='substring(from:%1, to:%2)'
        return [name, typeSpec]

    def langStringFormatterCommand(self, fmtStr, argStr):
        S='String(format:'+'"'+ fmtStr +'"'+ argStr +')'
        return S

    def LanguageSpecificDecorations(self, S, typeSpec, owner, LorRorP_Val):
        if typeSpec!= 0 and progSpec.typeIsPointer(typeSpec) and typeSpec['owner']!='itr' and not 'codeConverter' in typeSpec:
            if LorRorP_Val == "PARAM" and S=="nil":
                [cvrtType, innerType] = self.codeGen.convertType(typeSpec, 'arg', '', genericArgs)
                S = 'Optional<'+cvrtType+'>.none'
        return S

    def convertToInt(self, S, typeSpec):
        return S

    def checkForTypeCastNeed(self, lhsTSpec, rhsTSpec, RHS):
        LTypeKW = progSpec.fieldTypeKeyword(lhsTSpec)
        RTypeKW = progSpec.fieldTypeKeyword(rhsTSpec)
        if LTypeKW == 'bool'or LTypeKW == 'boolean':
            if progSpec.typeIsPointer(rhsTSpec):
                return '(' + RHS + ' == nil)'
            if (RTypeKW=='int' or RTypeKW=='flag'):
                if RHS[0]=='!': return '(' + codeStr[1:] + ' == 0)'
                else: return '(' + RHS + ' != 0)'
            if RHS == "0": return "false"
            if RHS == "1": return "true"
        elif LTypeKW == 'uint64' and RTypeKW=='int':
            RHS = 'UInt64('+RHS+')'
        elif LTypeKW == 'double' and RTypeKW=='int':
            RHS = 'Double('+RHS+')'
        elif LTypeKW == 'int' and RTypeKW=='char':
            RHS = RHS+'.asciiValue'
        elif LTypeKW == 'string' and RTypeKW=='char':
            RHS = "String(" + RHS+ ")"
        #elif LTypeKW != RTypeKW and LTypeKW != "mode" and LTypeKW != "flag" and RTypeKW != "ERROR" and LTypeKW != "struct" and LTypeKW != "bool":
        return RHS

    def getTheDerefPtrMods(self, itemTypeSpec):
        if itemTypeSpec!=None and isinstance(itemTypeSpec, dict) and 'owner' in itemTypeSpec:
            if progSpec.isNewContainerTempFunc(itemTypeSpec): return ['', '', False]
            if progSpec.typeIsPointer(itemTypeSpec):
                owner=progSpec.getTypeSpecOwner(itemTypeSpec)
                if progSpec.isAContainer(itemTypeSpec):
                    if owner=='itr':
                        containerType = progSpec.getDatastructID(itemTypeSpec)
                        if containerType =='map' or containerType == 'multimap':
                            return ['', '', False]
                    # OPTIONALS
                    return ['', '!', False]
                else:
                    if owner!='itr':
                        # OPTIONALS
                        return ['', '!', True]
        return ['', '', False]

    def derefPtr(self, varRef, itemTypeSpec):
        if varRef=='NULL': return varRef
        [leftMod, rightMod, isDerefd] = self.getTheDerefPtrMods(itemTypeSpec)
        S = leftMod + varRef + rightMod
        return [S, isDerefd]

    def ChoosePtrDecorationForSimpleCase(self, owner):
        if(owner=='our' or owner=='my' or owner=='their'):
            # OPTIONALS
            return ['','',  '', '!']
        else: return ['','',  '','']

    def chooseVirtualRValOwner(self, LVAL, RVAL):
        # Returns left and right text decorations for RHS of function arguments, return values, etc.
        if RVAL==0 or RVAL==None or isinstance(RVAL, str): return ['',''] # This happens e.g., string.size() # TODO: fix this.
        if LVAL==0 or LVAL==None or isinstance(LVAL, str): return ['', '']
        LeftOwner =progSpec.getTypeSpecOwner(LVAL)
        RightOwner=progSpec.getTypeSpecOwner(RVAL)
        if LeftOwner == RightOwner: return ["", ""]
        if LeftOwner!='itr' and RightOwner=='itr':
            return ["", ""]
        if LeftOwner=='me' and progSpec.typeIsPointer(RVAL):
            return ['', '!']             # OPTIONALS
        if progSpec.typeIsPointer(LVAL) and RightOwner=='me':
            return ['', '']
        #if LeftOwner=='their' and (RightOwner=='our' or RightOwner=='my'): return ['','.get()']
        return ['','']

    def determinePtrConfigForNewVars(self, LSpec, RSpec, useCtor):
        return ['','']

    def determinePtrConfigForAssignments(self, LVAL, RVAL, assignTag, codeStr):
        #TODO: make test case
        # Returns left and right text decorations for both LHS and RHS of assignment
        if RVAL==0 or RVAL==None or isinstance(RVAL, str): return ['','',  '',''] # This happens e.g., string.size() # TODO: fix this.
        if LVAL==0 or LVAL==None or isinstance(LVAL, str): return ['','',  '','']
        LeftOwner =progSpec.getTypeSpecOwner(LVAL)
        RightOwner=progSpec.getTypeSpecOwner(RVAL)
        if not isinstance(assignTag, str):
            assignTag = assignTag[0]
        if progSpec.typeIsPointer(LVAL) and progSpec.typeIsPointer(RVAL):
            # OPTIONALS
            if assignTag=='deep' :return ['','!',  '','!']
            elif LeftOwner=='their' and (RightOwner=='our' or RightOwner=='my'): return ['','', '','']
            else: return ['','',  '', '']
        if LeftOwner == RightOwner: return ['','',  '','']
        if LeftOwner=='me' and progSpec.typeIsPointer(RVAL):
            [leftMod, rightMod, isDerefd] = self.getTheDerefPtrMods(RVAL)
            # OPTIONALS
            return ['','',  leftMod, rightMod]
        if progSpec.typeIsPointer(LVAL) and RightOwner=='me':
            # OPTIONALS
            if assignTag!="" or assignTag=='deep':return ['','!',  '', '']
            else: return ['','',  "", '']
        # OPTIONALS
        if progSpec.typeIsPointer(LVAL) and RightOwner=='literal':return ['','!',  '', '']
        return ['','',  '','']

    def codeSpecialParamList(self, tSpec, CPL):
        return CPL

    def codeXlatorAllocater(self, tSpec, genericArgs):
        owner = progSpec.getTypeSpecOwner(tSpec)
        [cvrtType, innerType]  = self.codeGen.convertType(tSpec, 'alloc', '', genericArgs)
        if(owner=='our'):     S=cvrtType
        elif(owner=='my'):    S=cvrtType
        elif(owner=='their'): S=cvrtType
        elif(owner=='me'):    cdErr("ERROR: Cannot allocate a 'me' variable.")
        elif(owner=='const'): cdErr("ERROR: Cannot allocate a 'const' variable.")
        else: cdErr("ERROR: Cannot allocate variable because owner is", owner+".")
        return S

    def getConstIntFieldStr(self, fieldName, fieldValue, intSize):
        S= "static let "+fieldName+ ": Int = " + fieldValue+ ";\n"
        return(S)

    def getEnumStr(self, fieldName, enumList):
        S = ''
        count=0
        for enumName in enumList:
            S += "    " + self.getConstIntFieldStr(enumName, str(count), 32)
            count=count+1
        S += "\n"
        return(S)

    def codeIdentityCheck(self, S, S2, retType1, retType2, opIn):
        if opIn == '===':
            return S+' === '+S2
        else:
            if   (opIn == '=='): opOut=' == '
            elif (opIn == '!='): opOut=' != '
            elif (opIn == '!=='): opOut=' !== '
            else: print("ERROR: '==' or '!=' or '===' or '!==' expected."); exit(2)
            [S_derefd, isDerefd] = self.derefPtr(S, retType1)
            if S2!='nil':
                S=S_derefd
                [S2, isDerefd]=self.derefPtr(S2, retType1)
            elif S[-1]=='!':
                S=S[:-1]   # Todo: Better detect this
            S+= opOut+S2
            return S

    def codeComparisonStr(self, S, S2, retType1, retType2, op):
        if (op == '<'): S+=' < '
        elif (op == '>'): S+=' > '
        elif (op == '<='): S+=' <= '
        elif (op == '>='): S+=' >= '
        else: print("ERROR: One of <, >, <= or >= expected in code generator."); exit(2)
        S2 = self.adjustQuotesForChar(retType1, retType2, S2)
        [S2, isDerefd]=self.derefPtr(S2, retType2)
        S+=S2
        return S

    ###################################################### CONTAINERS
    def getContaineCategory(self, containerSpec):
        fromImpl=progSpec.getFromImpl(containerSpec)
        if fromImpl and 'implements' in fromImpl: return fromImpl['implements']
        fTypeKW = progSpec.fieldTypeKeyword(containerSpec)
        if fTypeKW=='string':  return 'string'
        if fTypeKW=='List':    return 'List'        # TODO: un-hardcode this
        if fTypeKW=='TreeMap': return 'Map'         # TODO: un-hardcode this
        if fTypeKW=='PovList': return 'PovList'     # TODO: un-hardcode this
        print("WARNING: Container Category not recorded for:",fTypeKW)
        return None

    def getContainerTypeInfo(self, containerType, name, idxType, typeSpecIn, paramList, genericArgs):
        convertedIdxType = ""
        typeSpecOut = typeSpecIn
        if progSpec.isNewContainerTempFunc(typeSpecIn): return(name, typeSpecOut, paramList, convertedIdxType)
        return(name, typeSpecOut, paramList, convertedIdxType)

    def codeArrayIndex(self, idx, containerType, LorR_Val, previousSegName, idxTypeSpec):
        fTypeKW = progSpec.fieldTypeKeyword(containerType)
        if (fTypeKW == 'string'):
            S= '[index: '+idx+']'
        else:
            fieldDefAt = self.codeGen.CheckObjectVars(fTypeKW, "at", "")
            if fieldDefAt: S= '.at(' + idx +')'
            else: S= '[' + idx +']'
        return S
    ###################################################### CONTAINER REPETITIONS
    def codeRangeSpec(self, traversalMode, ctrType, repName, S_low, S_hi, indent):
        if(traversalMode=='Forward' or traversalMode==None):
            S = indent + "for "+ repName+' in '+ S_low + "..<Int(" + S_hi + "){\n"
        elif(traversalMode=='Backward'):
            S = indent + "for " + repName + " in stride(from:"+ S_hi+"-1" + ", through: " + S_low + ", by: -1){\n"
        return (S)

    def iterateRangeFromTo(self, classes,localVarsAlloc,StartKey,EndKey,ctnrTSpec,repName,ctnrName,indent):
        willBeModifiedDuringTraversal=True   # TODO: Set this programatically later.
        [datastructID, idxTypeKW, ctnrOwner]=self.getContainerType(ctnrTSpec, 'action')
        actionText   = ""
        loopCntrName = repName+'_key'
        itrIncStr    = ""
        firstOwner   = progSpec.getContainerFirstElementOwner(ctnrTSpec)
        firstType    = progSpec.getContainerFirstElementType(ctnrTSpec)
        firstTSpec   = {'owner':firstOwner, 'fieldType':firstType}
        reqTagList   = progSpec.getReqTagList(ctnrTSpec)
        itrTSpec     = progSpec.getItrTypeOfDataStruct(ctnrTSpec)
        itrType = progSpec.fieldTypeKeyword(progSpec.getItrTypeOfDataStruct(ctnrTSpec)) + ' '
        itrName      = repName + "Itr"
        containerCat = self.getContaineCategory(ctnrTSpec)
        if containerCat=="Map" or containerCat=="Multimap":
            valueFieldType = progSpec.fieldTypeKeyword(ctnrTSpec)
            if(reqTagList != None):
                firstTSpec['owner']     = progSpec.getOwnerFromTemplateArg(reqTagList[1])
                firstTSpec['fieldType'] = progSpec.getTypeFromTemplateArg(reqTagList[1])
                idxTypeKW      = progSpec.getTypeFromTemplateArg(reqTagList[0])
                valueFieldType = progSpec.getTypeFromTemplateArg(reqTagList[1])
            keyVarSpec = {'owner':ctnrTSpec['owner'], 'fieldType':firstType, 'codeConverter':(repName+'.first')}
            firstTSpec['codeConverter'] = (repName+'.value')
            localVarsAlloc.append([repName+'_key', keyVarSpec])  # Tracking local vars for scope
            localVarsAlloc.append([repName, firstTSpec]) # Tracking local vars for scope
            itrDeclStr  = indent + 'var '+itrName+":"+itrType+' = '+ctnrName+'.lower_bound('+StartKey+')\n'
            localVarsAlloc.append([itrName, itrType])
            endItrName       = repName + "EndItr"
            endItrStr   = indent + 'var ' + endItrName + ':'+itrType+' = '+ctnrName+'.upper_bound('+EndKey+')\n'
            itrIncStr   = indent + "    " + itrName + " = " + itrName + ".__inc()\n"

            actionText += itrDeclStr + endItrStr
            actionText += (indent + 'while ' + itrName + '.node !== '+endItrName+'.node {\n')
            actionText += (indent + "    var  " + repName + " = " + itrName + ".node\n")
        elif datastructID=='List' and not willBeModifiedDuringTraversal: pass;
        elif datastructID=='List' and willBeModifiedDuringTraversal: pass;
        else: cdErr("DSID iterateRangeFromTo:"+datastructID+" "+containerCat)
        return [actionText, loopCntrName]

    def iterateContainerStr(self, classes,localVarsAlloc,ctnrTSpec,repName,ctnrName,isBackward,indent,genericArgs):
        #TODO: handle isBackward
        willBeModifiedDuringTraversal=True   # TODO: Set this programatically later.
        [datastructID, idxTypeKW, ctnrOwner]=self.getContainerType(ctnrTSpec, 'action')
        actionText   = ""
        loopCntrName = repName+'_key'
        itrIncStr    = ""
        firstOwner   = progSpec.getContainerFirstElementOwner(ctnrTSpec)
        firstType    = progSpec.getContainerFirstElementType(ctnrTSpec)
        firstTSpec   = {'owner':firstOwner, 'fieldType':firstType}
        reqTagList   = progSpec.getReqTagList(ctnrTSpec)
        itrTSpec     = progSpec.getItrTypeOfDataStruct(ctnrTSpec)
        itrType    = progSpec.fieldTypeKeyword(itrTSpec)
        itrOwner     = progSpec.getOwnerFromTypeSpec(itrTSpec)
        itrName      = repName + "Itr"
        containerCat = self.getContaineCategory(ctnrTSpec)
        [LDeclP, RDeclP, LDeclA, RDeclA] = self.ChoosePtrDecorationForSimpleCase(firstOwner)
        [LNodeP, RNodeP, LNodeA, RNodeA] = self.ChoosePtrDecorationForSimpleCase(itrOwner)
        if containerCat=='PovList': cdErr("TODO: handle PovList")
        if containerCat=='Map':
            reqTagStr    = self.getReqTagString(classes, ctnrTSpec)
            if(reqTagList != None):
                firstTSpec['owner']     = progSpec.getOwnerFromTemplateArg(reqTagList[1])
                firstTSpec['fieldType'] = progSpec.getTypeFromTemplateArg(reqTagList[1])
            keyVarSpec  = {'owner':firstOwner, 'fieldType':firstType, 'codeConverter':(repName+'!.key')}
            firstTSpec['codeConverter'] = (repName+'!.value')
            itrType    = self.codeGen.convertType(itrTSpec, 'var', 'action', genericArgs)[0]+' '
            itrDeclStr  = indent + 'var '+itrName+":"+itrType+' = '+ctnrName+'.front()\n'
            localVarsAlloc.append([itrName, itrType])
            endItrName       = repName + "EndItr"
            endItrStr   = indent + 'var ' + endItrName + ':'+itrType+' = '+ctnrName+'.end()\n'
            itrIncStr   = indent + "    " + itrName + " = " + itrName + ".__inc()\n"
            actionText += itrDeclStr + endItrStr
            actionText += (indent + 'while ' + itrName + '.node !== '+endItrName+'.node {\n')
            actionText += (indent + "    var  " + repName + " = " + itrName + ".node\n")
            # TODO: increment ITR
        elif containerCat=="List":
            if willBeModifiedDuringTraversal:
                idxTypeKW        = self.adjustBaseTypes(idxTypeKW, False)
                containedOwner = progSpec.getOwnerFromTypeSpec(ctnrTSpec)
                keyVarSpec     = {'owner':containedOwner, 'fieldType':firstType}
                loopVarName=repName+"Idx";
                if(isBackward):
                    actionText += (indent + "for " + repName+' in '+ ctnrName +".reversed() {\n")
                else:
                    actionText += (indent + "for " + loopVarName + " in 0..<" +  ctnrName+".count {\n"
                                + indent+"    var "+repName + ':' + idxTypeKW + " = "+ctnrName+"["+loopVarName+"];\n")
            else:
                keyVarSpec = {'owner':'me', 'fieldType':'Int'}
                if(isBackward):
                    actionText += (indent + "for " + repName+' in ('+ ctnrName +".count - 1).stride(through: 0, by: -1) {\n")
                else:
                    actionText += (indent + "for " + repName+' in '+ ctnrName + " {\n")
        elif containerCat=='string':
            keyVarSpec   = {'owner':'me', 'fieldType':'char'}
            firstTSpec   = {'owner':'me', 'fieldType':'char'}
            actionText += indent + "for "+ repName + " in " + ctnrName + "{\n"
        else: cdErr("iterateContainerStr() datastructID = " + datastructID)
        localVarsAlloc.append([loopCntrName, keyVarSpec])  # Tracking local vars for scope
        localVarsAlloc.append([repName, firstTSpec]) # Tracking local vars for scope
        return [actionText, loopCntrName, itrIncStr]

    def codeSwitchExpr(self, switchKeyExpr, switchKeyTypeSpec):
        return switchKeyExpr

    def codeSwitchCase(self, caseKeyValue, caseKeyTypeSpec):
        return caseKeyValue

    ###################################################### EXPRESSION CODING
    def codeNotOperator(self, S, S2,retTypeSpec):
        if progSpec.varsTypeCategory(retTypeSpec) != 'bool':
            if S2[-1]=='!': S2=S2[:-1]   # Todo: Better detect this
            S2='('+S2+' != nil)'
            retTypeSpec='bool'
        else: S+='!' + S2
        return [S, retTypeSpec]

    def codeFactor(self, item, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        ####  ( value | ('(' + expr + ')') | ('!' + expr) | ('-' + expr) | varRef("varFunRef"))
        #print('                  factor: ', item)
        S=''
        retTypeSpec='noType'
        item0 = item[0]
        #print("ITEM0=", item0, ">>>>>", item)
        if (isinstance(item0, str)):
            if item0=='(':
                [S2, retTypeSpec] = self.codeGen.codeExpr(item[1], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                S+='(' + S2 +')'
            elif item0=='!':
                [S2, retTypeSpec] = self.codeGen.codeExpr(item[1], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                [S, retTypeSpec]  = self.codeNotOperator(S, S2,retTypeSpec)
            elif item0=='-':
                [S2, retTypeSpec] = self.codeGen.codeExpr(item[1], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                S+='-' + S2
            elif item0=='[':
                tmp="["
                for expr in item[1:-1]:
                    [S2, retTypeSpec] = self.codeGen.codeExpr(expr, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                    if len(tmp)>1: tmp+=", "
                    tmp+=S2
                tmp+="]"
                S+=tmp
            elif item0=='{':
                cdErr("TODO: finish Swift initialize new map")
            else:
                fTypeKW = progSpec.varTypeKeyWord(expectedTypeSpec)
                if fTypeKW == "BigInt":
                    S += item0
                    retTypeSpec='BigInt'
                elif fTypeKW == "BigFloat":
                    S += item0 + "_mpf"
                    retTypeSpec='BigFloat'
                elif fTypeKW == "BigFrac":
                    S += item0 + "_mpq"
                    retTypeSpec='BigFrac'
                elif(item0[0]=="'"):
                    retTypeSpec='string'
                    S+=self.codeGen.codeUserMesg(item0[1:-1])
                elif (item0[0]=='"'):
                    if returnType != None and returnType["fieldType"]=="char":
                        retTypeSpec='char'
                        innerS=item0[1:-1]
                        if len(innerS)==1:
                            S+="'"+item0[1:-1] +"'"
                        else:
                            cdErr("Characters must have exactly 1 character.")
                    else:
                        S+='"'+item0[1:-1] +'"'
                        retTypeSpec='String'
                else:
                    S+=item0;
                    if item0=='false' or item0=='true': retTypeSpec={'owner': 'literal', 'fieldType': 'bool'}
                    if retTypeSpec == 'noType' and progSpec.isStringNumeric(item0): retTypeSpec={'owner': 'literal', 'fieldType': 'numeric'}
                    if retTypeSpec == 'noType' and progSpec.typeIsInteger(fTypeKW): retTypeSpec=fTypeKW

        else: # CODEDOG LITERALS
            if isinstance(item0[0], str):
                S+=item0[0]
                if '"' in S or "'" in S: retTypeSpec = 'string'
                if '.' in S: retTypeSpec = 'double'
                if isinstance(S, int): retTypeSpec = 'int64'
                else:  retTypeSpec = 'int32'
            else:
                [codeStr, retTypeSpec, prntType, AltIDXFormat]=self.codeGen.codeItemRef(item0, 'RVAL', returnType, LorRorP_Val, genericArgs)
                if(codeStr=="NULL"):
                    codeStr="nil"
                    retTypeSpec={'owner':"PTR"}
                S+=codeStr                                # Code variable reference or function call
        return [S, retTypeSpec]

    ######################################################
    def adjustQuotesForChar(self, typeSpec1, typeSpec2, S):
        return(S)

    def adjustConditional(self, S, conditionType):
        if conditionType!=None and not isinstance(conditionType, str):
            if conditionType['owner']=='our' or conditionType['owner']=='their' or conditionType['owner']=='my' or progSpec.isStruct(conditionType['fieldType']):
                if S[-1]=='!': S=S[:-1]   # Todo: Better detect this
                S+=" != nil"
            elif conditionType['owner']=='me' and (conditionType['fieldType']=='flag' or progSpec.typeIsInteger(conditionType['fieldType'])):
                if S[-1]=='!': S=S[:-1]   # Todo: Better detect this
                S+=" != 0"
            conditionType='bool'
        return [S, conditionType]

    def codeSpecialReference(self, segSpec, genericArgs):
        S=''
        fieldType='void'   # default to void
        retOwner='me'    # default to 'me'
        funcName=segSpec[0]
        if(len(segSpec)>2):  # If there are arguments...
            paramList=segSpec[2]
            if(funcName=='print'):
                S+='print('
                count = 0
                for P in paramList:
                    [S2, argTypeSpec]=self.codeGen.codeExpr(P[0], None, None, 'PARAM', genericArgs)
                    [S2, isDerefd]=self.derefPtr(S2, argTypeSpec)
                    if(count>0): S+=', '
                    S+=S2
                    count= count + 1
                S+=',separator:"", terminator:"")'
            elif(funcName=='AllocateOrClear'):
                [varName,  varTypeSpec]=self.codeGen.codeExpr(paramList[0][0], None, None, 'PARAM', genericArgs)
                if(varTypeSpec==0): cdErr("Name is undefined: " + varName)
                if(varName[-1]=='!'): varNameUnRefed=varName[:-1]  # Remove a reference. It would be better to do this in self.codeGen.codeExpr but may take some work.
                else: varNameUnRefed=varName
                S+='if('+varNameUnRefed+' != nil){'+varName+'.clear();} else {'+varName+" = "+self.codeXlatorAllocater(varTypeSpec, genericArgs)+"();}"
            elif(funcName=='Allocate'):
                [varName,  varTypeSpec]=self.codeGen.codeExpr(paramList[0][0], None, None, 'LVAL', genericArgs)
                if(varTypeSpec==0): cdErr("Name is Undefined: " + varName)
                S+=varName+" = "+self.codeXlatorAllocater(varTypeSpec, genericArgs)+'('
                count=0   # TODO: As needed, make this call CodeParameterList() with modelParams of the constructor.
                for P in paramList[1:]:
                    if(count>0): S+=', '
                    [S2, argType]=self.codeGen.codeExpr(P[0], None, None, 'PARAM', genericArgs)
                    S+=S2
                    count=count+1
                S+=")"
            elif(funcName=='callPeriodically'):
                [objName,  fieldType]=self.codeGen.codeExpr(paramList[1][0], None, None, 'PARAM', genericArgs)
                [interval,  intSpec] = self.codeGen.codeExpr(paramList[2][0], None, None, 'PARAM', genericArgs)
                varTypeSpec= fieldType['fieldType'][0]
                wrapperName="cb_wraps_"+varTypeSpec
                S+='g_timeout_add('+interval+', '+wrapperName+', '+objName+')'

                # Create a global function wrapping the class
                decl='\nint '+wrapperName+'(void* data)'
                defn='{'+varTypeSpec+'* self = ('+varTypeSpec+'*)data; self.run(); return true;}\n\n'
                self.codeGen.appendGlobalFuncAcc(decl, defn)
            elif(funcName=='break'):
                if len(paramList)==0: S='break'
            elif(funcName=='return'):
                if len(paramList)==0: S+='return'
            elif(funcName=='toStr'):
                if len(paramList)==1:
                    [S2, argType]=self.codeGen.codeExpr(P[0][0], None, None, 'PARAM', genericArgs)
                    S2=self.derefPtr(S2, argType)
                    S+='to_string('+S2+')'
                    returnType='string'
        else: # Not parameters, i.e., not a function
            if(funcName=='self'):
                S+='self'

        return [S, retOwner, fieldType]

    def checkIfSpecialAssignmentFormIsNeeded(self, action, indent, AltIDXFormat, RHS, rhsType, LHS, LHSParentType, LHS_FieldType):
        # Check for string A[x] = B;  If so, render A.insert(B,x)
        S = ''
        assignTag = action['assignTag']
        [containerType, idxType, owner]=self.getContainerType(AltIDXFormat[1], "")
        if assignTag == '':
            RHS += self.makePtrOpt(rhsType)
            [containerType, idxTypeKW, owner]=self.getContainerType(AltIDXFormat[1], "")
            if containerType == 'RBTreeMap' or containerType[:2]=="__" and 'Map' in containerType:
                S = indent+AltIDXFormat[0]+'.insert('+AltIDXFormat[2]+', '+RHS+');\n'
        #else: assignTag = assignTag[0]
        return S

    ######################################################
    def codeProtectBlock(self, mutex, criticalText, indent):
        return(criticalText)

    def codeMain(self, classes, tags):
        cdlog(3, "\n            Generating GLOBAL...")
        if("GLOBAL" in classes[1]):
            if(classes[0]["GLOBAL"]['stateType'] != 'struct'):
                print("ERROR: GLOBAL must be a 'struct'.")
                exit(2)
            [structCode, funcCode, globalFuncs]=self.codeGen.codeStructFields("GLOBAL", tags, '')
            if(funcCode==''): funcCode="// No main() function.\n"
            if(structCode==''): structCode="// No Main Globals.\n"
            funcCode = "\n\n"+funcCode+"\nmain();" # TODO: figure out why call to main isn't generated and un-hardcode this
            return ["\n\n// Globals\n" + structCode + globalFuncs, funcCode]
        return ["// No Main Globals.\n", "// No main() function defined.\n"]

    def codeArgText(self, argFieldName, argType, argOwner, typeSpec, makeConst, typeArgList):
        isTypeArg = False
        if typeArgList:
            for typeArg in typeArgList:
                if argType == typeArg: argType = "[" + argType + "]"
        fieldTypeMod = self.makePtrOpt(typeSpec)
        return "_ " + argFieldName + ": " + argType + fieldTypeMod

    def codeStructText(self, classes, attrList, parentClass, classInherits, classImplements, structName, structCode, tags):
        classAttrs=''
        if len(attrList)>0:
            for attr in attrList:
                if attr[0]=='@': classAttrs += attr+' '
        if parentClass != "":
            parentClass = ': '+parentClass+' '
            parentClass = progSpec.getUnwrappedClassFieldTypeKeyWord(structName)
        if classInherits!=None:
            parentClass=': '
            count =0
            for item in classInherits[0]:
                if count>0:
                    parentClass+= ', '
                parentClass+= progSpec.getUnwrappedClassFieldTypeKeyWord(classes, item)
                count += 1
        typeArgList = progSpec.getTypeArgList(structName)
        if(typeArgList != None):
            templateHeader = codeTemplateHeader(structName, typeArgList)+" "
            structName= structName+templateHeader
        S= "\n"+classAttrs+"class "+structName+parentClass+"{\n" + structCode + '};\n'
        forwardDecls=""
        return([S,forwardDecls])

    def produceTypeDefs(self, typeDefMap):
        typeDefCode="\n// Typedefs:\n"
        for key in typeDefMap:
            val=typeDefMap[key]
            #sprint '['+key+']='+val+']'
            if(val != '' and val != key):
                typeDefCode += 'typedef '+key+' '+val+';\n'
        return typeDefCode

    def addSpecialCode(self, filename):
        S='\n\n//////////// SWIFT specific code:\n'
        S+="""
    extension String {
        func index(from: Int) -> Index {
            return self.index(startIndex, offsetBy: from)
        }

        func substring(from: Int, to:Int) -> String {
            return String(self[index(from: from)..<index(from: to)])
        }

        subscript(index value: Int) -> Element {
            get {
                let i = index(startIndex, offsetBy: value)
                return self[i]
            } set {
                var array = Array(self)
                array[value] = newValue
                self = String(array)
            }
        }
    }

    extension Character {
        var asciiValue: Int {
            get {
                let s = String(self).unicodeScalars
                return Int(s[s.startIndex].value)
            }
        }
    }

    func joinCmdStrings(count: Int, argv: [Character]) -> String{
        var acc: String=""
        for i in 1...count{
            if(i>1){acc+=" "}
            acc += String(argv[i])
        }
        return(acc)
    }
        """

        decl ="string readFileAsString(string filename)"
        defn="""{
            string S="";
            std::ifstream file(filename);
            if(file.eof() || file.fail()) {return "";}
            file.seekg(0, std::ios::end);
            S.resize(file.tellg());
            file.seekg(0, std::ios::beg);
            file.read((char*)S.c_str(), S.count);
            return S;  //No errors
        }"""
        #self.codeGen.appendGlobalFuncAcc(decl, defn)

        return S

    def addGLOBALSpecialCode(self, classes, tags):
        specialCode =''

        GLOBAL_CODE="""
    struct GLOBAL{
        %s
    }
        """ % (specialCode)

        #codeDogParser.AddToObjectFromText(classes[0], classes[1], GLOBAL_CODE)
    def variableDefaultValueString(self, fieldType, isTypeArg, owner):
        if (fieldType == "String"):
            fieldValueText=' = ""'
        elif (fieldType.startswith("[")):
            fieldValueText=' = '+fieldType + '()'
        elif (fieldType == "Bool"):
            fieldValueText=' = false'
        elif (self.isNumericType(fieldType)):
            fieldValueText=' = 0'
        elif (fieldType == "Character"):
            fieldValueText=' = "\\0"'
        elif(isTypeArg):
            fieldValueText = ' = ['+fieldType +']()'
        else:
            if progSpec.ownerIsPointer(owner):fieldValueText = ''
            else:fieldValueText = ' = ' + fieldType +'()'
        return fieldValueText

    def codeNewVarStr(self, classes, tags, lhsTypeSpec, varName, fieldDef, indent, actionOrField, genericArgs, localVarsAllocated):
        varDeclareStr = ''
        assignValue   = ''
        isAllocated   = fieldDef['isAllocated']
        owner         = progSpec.getTypeSpecOwner(lhsTypeSpec)
        useCtor       = False
        if fieldDef['paramList'] and fieldDef['paramList'][-1] == "^&useCtor//8":
            del fieldDef['paramList'][-1]
            useCtor = True
        [cvrtType, innerType] = self.codeGen.convertType(lhsTypeSpec, 'var', actionOrField, genericArgs)
        localVarsAllocated.append([varName, lhsTypeSpec])  # Tracking local vars for scope
        [allocFieldType, innerType] = self.codeGen.convertType(lhsTypeSpec, 'alloc', '', genericArgs)
        if(fieldDef['value']):
            [RHS, rhsTypeSpec]=self.codeGen.codeExpr(fieldDef['value'][0], None, None, 'RVAL', genericArgs)
            [leftMod, rightMod]=self.chooseVirtualRValOwner(lhsTypeSpec, rhsTypeSpec)
            RHS = leftMod+RHS+rightMod
            RHS = self.checkForTypeCastNeed(lhsTypeSpec, rhsTypeSpec, RHS)
            assignValue = " = " + RHS
        else: # If no value was given:
            CPL=''
            if fieldDef['paramList'] != None:       # call constructor  # curly bracket param list
                # Code the constructor's arguments
                [CPL, paramTypeList] = self.codeGen.codeParameterList(varName, fieldDef['paramList'], None, genericArgs)
                if len(paramTypeList)==1:
                    if not isinstance(paramTypeList[0], dict):
                        print("\nPROBLEM: The return type of the parameter '", CPL, "' of "+varName+"(...) cannot be found and is needed. Try to define it.\n",   paramTypeList)
                        exit(1)
                    rhsTypeSpec = paramTypeList[0]
                    rhsType     = progSpec.getFieldType(rhsTypeSpec)
                    # TODO: Remove the 'True' and make this check object heirarchies or similar solution
                    if True or not isinstance(rhsType, str) and cvrtType==rhsType[0]:
                        assignValue = " = " + CPL   # Act like a copy constructor
                if(assignValue==''): assignValue = ' = ' + allocFieldType + CPL
            else:
                assignValue = self.variableDefaultValueString(allocFieldType, False, owner)
        fieldTypeMod = self.makePtrOpt(lhsTypeSpec)
        if (assignValue == ""):
            varDeclareStr= "var " + varName + ": "+ cvrtType + fieldTypeMod + " = " + allocFieldType + '()'
        else:
            varDeclareStr= "var " + varName + ": "+ cvrtType + fieldTypeMod + assignValue
        return(varDeclareStr)

    def codeIncrement(self, varName):
        return varName + " += 1"

    def codeDecrement(self, varName):
        return varName + " -= 1"

    def isNumericType(self, convertedType):
        if(convertedType == "UInt32" or convertedType == "UInt64" or convertedType == "Float" or convertedType == "Int" or convertedType == "Int32" or convertedType == "Int64" or convertedType == "Double"):
            return True
        return False

    def codeVarFieldRHS_Str(self, fieldName, cvrtType, innerType, typeSpec, paramList, isAllocated, typeArgList, genericArgs):
        fieldValueText=""
        fieldOwner=progSpec.getTypeSpecOwner(typeSpec)
        isTypeArg = False
        if typeArgList:
            for typeArg in typeArgList:
                if cvrtType == typeArg: isTypeArg = True
        if paramList!=None:
            if paramList[-1] == "^&useCtor//8":
                del paramList[-1]
            [CPL, paramTypeList] = self.codeGen.codeParameterList(fieldName, paramList, None, genericArgs)
            fieldValueText=" = " + cvrtType + CPL
        else:
            fieldValueText = self.variableDefaultValueString(cvrtType, isTypeArg, fieldOwner)
            if fieldValueText and cvrtType != 'String':
                fieldValueText += self.makePtrOpt(typeSpec) # Default String value can't be optional
        return fieldValueText

    def codeConstField_Str(self, convertedType, fieldName, fieldValueText, className, indent):
        decl = ''
        if className=='GLOBAL': defn =  indent  + "let " + fieldName + ':'+ convertedType  + fieldValueText +';\n';
        else: defn =  indent  + "let " + fieldName + ':'+ convertedType  + fieldValueText +';\n';
        return [defn, decl]

    def codeVarField_Str(self, convertedType, typeSpec, fieldName, fieldValueText, className, tags, typeArgList, indent):
        # TODO: make test case
        fieldOwner=progSpec.getTypeSpecOwner(typeSpec)
        if fieldOwner=='we':
            defn = indent + "public static var "+ indent + fieldName + ": " +  convertedType  +  fieldValueText + '\n'
            decl = ''
        else:
            isTypeArg = False
            if typeArgList:
                for typeArg in typeArgList:
                    if convertedType == typeArg: isTypeArg = True
            if isTypeArg: defn = indent + "var "+ fieldName + fieldValueText + '\n'
            else:
                convertedType += self.makePtrOpt(typeSpec)
                defn = indent + "var "+ fieldName + ": " +  convertedType + fieldValueText + '\n'
            decl = ''
        return [defn, decl]

    ###################################################### CONSTRUCTORS
    def codeConstructor(self, className, ctorArgs, callSuper, ctorInit, funcBody):
        if callSuper != '':
            callSuper = ':' + callSuper
            if ctorInit != '':
                callSuper = callSuper + ', '
        elif ctorInit != '':
            ctorInit = ': ' + ctorInit
        S = '    init(' + ctorArgs + ') {\n' + funcBody + '    };\n'
        return (S)

    def codeConstructors(self, className, ctorArgs, ctorOvrRide, ctorInit, copyCtorArgs, funcBody, callSuper):
        #TODO: Swift should only have constructors if they are called somewhere.
        prefix = ''
        if callSuper != "": prefix = 'override '
        if ctorArgs != "":
            S = '    '+ctorOvrRide+'init(' + ctorArgs+'){\n'+callSuper+ctorInit+funcBody+'    }\n'
        S += '    '+prefix+'init(){\n'+callSuper+funcBody+'    }\n'
        return S

    def codeConstructorInit(self, fieldName, count, defaultVal):
        return "        self." + fieldName +" = arg_"+fieldName+";\n"

    def codeConstructorArgText(self, argFieldName, count, argType, defaultVal):
        if defaultVal == "nil": defaultVal = ""
        if defaultVal: argType = argType + '=' + defaultVal
        return "_ arg_" + argFieldName  + ': ' +argType

    def codeCopyConstructor(self, fieldName, convertedType, isTemplateVar):
        return ""

    def codeConstructorCall(self, className):
        return '        INIT();\n'

    def codeSuperConstructorCall(self, parentClassName):
        return '        super.init();\n'

    def codeFuncHeaderStr(self, className, fieldName, returnType, argListText, localArgsAllocated, inheritMode, overRideOper, isConstructor, typeArgList, typeSpec, indent):
        #TODO: add \n before func
        structCode=''; funcDefCode=''; globalFuncs='';
        if typeArgList:
            for typeArg in typeArgList:
                if returnType == typeArg: returnType = '['+returnType+']'
        if returnType!='': returnType = '-> '+returnType
        if(className=='AppDelegate'):
            if fieldName=='application':
                structCode += '    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplicationLaunchOptionsKey: Any]?) -> Bool '
                localArgsAllocated.append(['application', {'owner':'me', 'fieldType':'UIApplication', 'arraySpec':None,'argList':None}])
                localArgsAllocated.append(['launchOptions', {'owner':'their', 'fieldType':'int', 'arraySpec':None,'argList':None}])  # TODO: Wrong. launchOptions should be an array.
            else:
                structCode +="func " + fieldName +"("+argListText+") " + returnType
        else:
            if fieldName=="init":
                fieldName = "__INIT_"+className
                structCode += indent + "func "  + fieldName +"("+argListText+")" + returnType
            else:
                if isConstructor:
                    structCode += indent + "init "  +"("+argListText+") " + returnType
                else:
                    fieldTypeMod = self.makePtrOpt(typeSpec)
                    funcAttrs=''
                    if inheritMode=='override': funcAttrs='override '
                    structCode += indent + funcAttrs + "func " + fieldName +"("+argListText+") " + returnType + fieldTypeMod
        return [structCode, funcDefCode, globalFuncs]

    def getVirtualFuncText(self, field):
        field['value'] = '{fatalError("Must Override")}'
        return field['value']+'\n'

    def codeTemplateHeader(self, structName, typeArgList):
        templateHeader = "<"
        count = 0
        for typeArg in typeArgList:
            if(count>0):templateHeader+=", "
            templateHeader+=typeArg
            count+=1
        templateHeader+=">"
        return(templateHeader)

    def extraCodeForTopOfFuntion(self, argList):
        if len(argList)==0:
            topCode=''
        else:
            topCode=""
            for arg in argList:
                argTypeSpec =arg['typeSpec']
                argFieldName=arg['fieldName']
                topCode+=  '        var '+argFieldName+' = '+argFieldName+'\n'
        return topCode

    def codeSetBits(self, LHS_Left, LHS_FieldType, prefix, bitMask, RHS, rhsType):
        if (LHS_FieldType =='flag' ):
            item = LHS_Left+"flags"
            mask = prefix+bitMask
            if (RHS != 'true' and RHS !='false'):
                RHS += ' != 0'
            val = '('+ RHS +') ? '+mask+':0'
        elif (LHS_FieldType =='mode' ):
            item = LHS_Left+"flags"
            mask = prefix+bitMask+"Mask"
            val = RHS+"<<"+prefix+bitMask+"Offset"
        return 'do{'+item+" &= ~UInt64("+mask+"); "+item+" |= UInt64("+val+");}\n"

    def codeSwitchBreak(self, caseAction, indent):
        return indent+"    break;\n"

    def applyTypecast(self, typeInCodeDog, itemToAlterType):
        platformType = self.adjustBaseTypes(typeInCodeDog, False)
        return platformType+'('+itemToAlterType+')';

    #######################################################

    def includeDirective(self, libHdr):
        S = 'import '+libHdr+'\n'
        return S

    def generateMainFunctionality(self, classes, tags):
        # TODO: Make initCode, runCode and deInitCode work better and more automated by patterns.
        # TODO: Some deInitialize items should automatically run during abort().
        # TODO: Deinitialize items should happen in reverse order.

        runCode = progSpec.fetchTagValue(tags, 'runCode')
        if runCode==None: runCode=""
        mainFuncCode="""
        me void: main() <- {
            initialize("")        // TODO: get command line args and pass to initialize(joinCmdStrings(argc, argv))
            """ + runCode + """
            deinitialize()
        }

    """
        progSpec.addObject(classes[0], classes[1], 'GLOBAL', 'struct', 'SEQ')
        codeDogParser.AddToObjectFromText(classes[0], classes[1], progSpec.wrapFieldListInObjectDef('GLOBAL',  mainFuncCode ), 'Swift start-up code')

    def __init__(self):
        print("INIT")
