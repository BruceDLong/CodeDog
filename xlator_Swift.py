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
    hasMacros             = False
    useNestedClasses      = False
    nullValue             = "nil"

    ###################################################### CONTAINERS
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

    def getIdxType(self, tSpec):
        progSpec.isOldContainerTempFuncErr(tSpec,"xlator_Swift.getIdxType()")
        idxType = ''
        if progSpec.isNewContainerTempFunc(tSpec):
            ctnrTSpec = progSpec.getContainerSpec(tSpec)
            if 'indexType' in ctnrTSpec:
                if 'IDXowner' in ctnrTSpec['indexType']:
                    idxOwner = ctnrTSpec['indexType']['IDXowner'][0]
                    idxType  = ctnrTSpec['indexType']['idxBaseType'][0][0]
                    idxType  = self.applyOwner(idxOwner, idxType, '')
                else: idxType=ctnrTSpec['indexType']['idxBaseType'][0][0]
            else: idxType = progSpec.getNewContainerFirstElementTypeTempFunc(tSpec)
        return idxType

    def iterateRangeFromTo(self, classes,localVarsAlloc,StartKey,EndKey,ctnrTSpec,repName,ctnrName,indent):
        willBeModifiedDuringTraversal=True   # TODO: Set this programatically later.
        [datastructID, __ctnrOwner]=progSpec.getContainerType_Owner(ctnrTSpec)
        idxTypeKW    = self.getIdxType(ctnrTSpec)
        idxTypeKW    = self.getIdxType(ctnrTSpec)
        actionText   = ""
        loopCntrName = repName+'_key'
        itrIncStr    = ""
        firstOwner   = progSpec.getContainerFirstElementOwner(ctnrTSpec)
        firstType    = progSpec.getContainerFirstElementType(ctnrTSpec)
        firstTSpec   = {'owner':firstOwner, 'fieldType':firstType}
        reqTagList   = progSpec.getReqTagList(ctnrTSpec)
        itrTSpec     = self.codeGen.getDataStructItrTSpec(datastructID)
        itrTypeKW    = progSpec.fieldTypeKeyword(itrTSpec) + ' '
        itrName      = repName + "Itr"
        containerCat = progSpec.getContaineCategory(ctnrTSpec)
        if containerCat=="Map" or containerCat=="Multimap":
            valueFieldType = progSpec.fieldTypeKeyword(ctnrTSpec)
            if(reqTagList != None):
                firstTSpec['owner']     = progSpec.getOwner(reqTagList[1])
                firstTSpec['fieldType'] = progSpec.fieldTypeKeyword(reqTagList[1])
                idxTypeKW      = progSpec.fieldTypeKeyword(reqTagList[0])
                valueFieldType = progSpec.fieldTypeKeyword(reqTagList[1])
            keyVarSpec = {'owner':ctnrTSpec['owner'], 'fieldType':firstType, 'codeConverter':(repName+'.first')}
            firstTSpec['codeConverter'] = (repName+'.value')
            localVarsAlloc.append([repName+'_key', keyVarSpec])  # Tracking local vars for scope
            localVarsAlloc.append([repName, firstTSpec]) # Tracking local vars for scope
            itrDeclStr  = indent + 'var '+itrName+":"+itrTypeKW+' = '+ctnrName+'.lower_bound('+StartKey+')\n'
            localVarsAlloc.append([itrName, itrTypeKW])
            endItrName       = repName + "EndItr"
            endItrStr   = indent + 'var ' + endItrName + ':'+itrTypeKW+' = '+ctnrName+'.upper_bound('+EndKey+')\n'
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
        [datastructID, __ctnrOwner]=progSpec.getContainerType_Owner(ctnrTSpec)
        idxTypeKW    = self.getIdxType(ctnrTSpec)
        actionText   = ""
        loopCntrName = repName+'_key'
        itrIncStr    = ""
        firstOwner   = progSpec.getContainerFirstElementOwner(ctnrTSpec)
        firstType    = progSpec.getContainerFirstElementType(ctnrTSpec)
        firstTSpec   = {'owner':firstOwner, 'fieldType':firstType}
        reqTagList   = progSpec.getReqTagList(ctnrTSpec)
        itrTSpec     = self.codeGen.getDataStructItrTSpec(datastructID)
        itrTypeKW    = progSpec.fieldTypeKeyword(itrTSpec)
        itrOwner     = progSpec.getOwner(itrTSpec)
        itrName      = repName + "Itr"
        containerCat = progSpec.getContaineCategory(ctnrTSpec)
        [LDeclP, RDeclP, LDeclA, RDeclA] = self.ChoosePtrDecorationForSimpleCase(firstOwner)
        [LNodeP, RNodeP, LNodeA, RNodeA] = self.ChoosePtrDecorationForSimpleCase(itrOwner)
        if containerCat=='Map':
            reqTagStr    = self.getReqTagString(classes, ctnrTSpec)
            if(reqTagList != None):
                firstTSpec['owner']     = progSpec.getOwner(reqTagList[1])
                firstTSpec['fieldType'] = progSpec.fieldTypeKeyword(reqTagList[1])
            keyVarSpec  = {'owner':firstOwner, 'fieldType':firstType, 'codeConverter':(repName+'!.key')}
            firstTSpec['codeConverter'] = (repName+'!.value')
            itrTypeKW    = self.codeGen.convertType(itrTSpec, 'var', genericArgs)+' '
            itrDeclStr  = indent + 'var '+itrName+":"+itrTypeKW+' = '+ctnrName+'.front()\n'
            localVarsAlloc.append([itrName, itrTypeKW])
            endItrName       = repName + "EndItr"
            endItrStr   = indent + 'var ' + endItrName + ':'+itrTypeKW+' = '+ctnrName+'.end()\n'
            itrIncStr   = indent + "    " + itrName + " = " + itrName + ".__inc()\n"
            actionText += itrDeclStr + endItrStr
            actionText += (indent + 'while ' + itrName + '.node !== '+endItrName+'.node {\n')
            actionText += (indent + "    var  " + repName + " = " + itrName + ".node\n")
            # TODO: increment ITR
        elif containerCat=="List":
            if willBeModifiedDuringTraversal:
                idxTypeKW        = self.adjustBaseTypes(idxTypeKW, False)
                containedOwner = progSpec.getOwner(ctnrTSpec)
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

    ###### Routines to track types of identifiers and to look up type based on identifier.
    def implOperatorsAsFuncs(self, fTypeKW):
        return False

    def adjustBaseTypes(self, fType, isContainer):
        langType = ''
        if(isinstance(fType, str)):
            if(fType=='uint8' or fType=='uint16'or fType=='uint32'): return 'UInt32'
            elif(fType=='int8' or fType=='int16' or fType=='int32'): return 'Int32'
            elif(fType=='uint64'): return 'UInt64'
            elif(fType=='int64'):  return 'Int64'
            elif(fType=='int'):    return 'Int'
            elif(fType=='bool'):   return 'Bool'
            elif(fType=='void'):   return 'Void'
            elif(fType=='float'):  return 'Float'
            elif(fType=='double'): return 'Double'
            elif(fType=='string'): return 'String'
            elif(fType=='char'):   return 'Character'
            langType=progSpec.flattenObjectName(fType)
        else: langType=progSpec.flattenObjectName(fType[0])
        return langType

    def applyIterator(self, langType, itrTypeKW):
        return langType

    def applyOwner(self, owner, langType, varMode):
        # varMode is 'var' or 'arg' or 'alloc'.
        if owner=='me':         langType = langType
        elif owner=='my':       langType = langType
        elif owner=='our':      langType = langType
        elif owner=='their':    langType = langType
        elif owner=='itr':      langType = langType
        elif owner=='const':    langType = langType
        elif owner=='we':       langType += 'public static'
        else: cdErr("ERROR: Owner of type not valid '" + owner + "'")
        return langType

    def getUnwrappedClassOwner(self, classes, tSpec, fType, varMode, ownerIn):
        ownerOut = ownerIn
        ownerOut = progSpec.getOwner(tSpec)
        baseType = progSpec.isWrappedType(classes, fType)
        if baseType!=None:  # TODO: When this is all tested and stable, un-hardcode and optimize this!!!!!
            if 'ownerMe' in baseType:ownerOut = 'their'
            else:
                if varMode=='var':ownerOut= progSpec.getOwner(baseType)  # TODO: remove this condition: accomodates old list type generated in stringStructs
                else: ownerOut = ownerIn
        return ownerOut

    def getReqTagString(self, classes, tSpec):
        reqTagStr  = ""
        reqTagList = progSpec.getReqTagList(tSpec)
        if(reqTagList != None):
            reqTagStr = "<"
            count = 0
            for reqTag in reqTagList:
                reqOwnr     = progSpec.getOwner(reqTag)
                varTypeKW   = progSpec.fieldTypeKeyword(reqTag)
                unwrappedOwner=self.getUnwrappedClassOwner(classes, tSpec, varTypeKW, 'alloc', reqOwnr)
                unwrappedKW = progSpec.getUnwrappedClassFieldTypeKeyWord(classes, varTypeKW)
                reqType     = self.adjustBaseTypes(unwrappedKW, True)
                if(count>0): reqTagStr += ", "
                reqTagStr += reqType
                count += 1
            reqTagStr += ">"
        return reqTagStr

    def makePtrOpt(self, tSpec):
        # Make pointer field variables optionals
        fTypeKW = progSpec.fieldTypeKeyword(tSpec)
        if progSpec.typeIsPointer(tSpec) and (fTypeKW != 'string' or fTypeKW != 'String'): return('!')
        return('')

    def recodeStringFunctions(self, name, tSpec, lenParams):
        if name == "size":
            tSpec['codeConverter']='%0.count'
            tSpec['fieldType']='int'
        elif name == "subStr":
            tSpec['codeConverter']='substring(from:%1, to:%2)'
        return [name, tSpec]

    def langStringFormatterCommand(self, fmtStr, argStr):
        S='String(format:'+'"'+ fmtStr +'"'+ argStr +')'
        return S

    def LanguageSpecificDecorations(self, S, tSpec, owner, LorRorP_Val):
        if tSpec!= 0 and progSpec.typeIsPointer(tSpec) and tSpec['owner']!='itr' and not 'codeConverter' in tSpec:
            if LorRorP_Val == "PARAM" and S=="nil":
                cvrtType = self.codeGen.convertType(tSpec, 'arg', genericArgs)
                S = 'Optional<'+cvrtType+'>.none'
        return S

    def convertToInt(self, S, tSpec):
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
                owner=progSpec.getOwner(itemTypeSpec)
                if progSpec.isNewContainerTempFunc(itemTypeSpec):
                    if owner=='itr':
                        # OLD: ctnrCat = progSpec.getDatastructID(itemTypeSpec)
                        cdErr("####### TODO: needs to work with new container type #######")
                        ctnrCat = progSpec.getContaineCategory(itemTypeSpec) # NEW
                        if ctnrCat =='map' or ctnrCat == 'multimap':
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
        LeftOwner =progSpec.getOwner(LVAL)
        RightOwner=progSpec.getOwner(RVAL)
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
        LeftOwner =progSpec.getOwner(LVAL)
        RightOwner=progSpec.getOwner(RVAL)
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
        owner = progSpec.getOwner(tSpec)
        cvrtType  = self.codeGen.convertType(tSpec, 'alloc', genericArgs)
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
                    codeStr     = self.nullValue
                    retTypeSpec = {'owner':"PTR"}
                S+=codeStr                                # Code variable reference or function call
        if retTypeSpec == 'noType': print("Warning: type Spec not found.", S)
        return [S, retTypeSpec]

    ###################################################### ADJUST EXPRESSIONS
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
        fType='void'   # default to void
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
                [objName,  fType]=self.codeGen.codeExpr(paramList[1][0], None, None, 'PARAM', genericArgs)
                [interval,  intSpec] = self.codeGen.codeExpr(paramList[2][0], None, None, 'PARAM', genericArgs)
                varTypeSpec= fType['fieldType'][0]
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

        return [S, retOwner, fType]

    def checkIfSpecialAssignmentFormIsNeeded(self, action, indent, AltIDXFormat, RHS, rhsType, LHS, LHSParentType, LHS_FieldType):
        # Check for string A[x] = B;  If so, render A.insert(B,x)
        S = ''
        assignTag = action['assignTag']
        if assignTag == '':
            RHS += self.makePtrOpt(rhsType)
            [containerType, __owner]=progSpec.getContainerType_Owner(AltIDXFormat[1])
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

    def codeArgText(self, argFieldName, argType, argOwner, tSpec, makeConst, typeArgList):
        isTypeArg = False
        if typeArgList:
            for typeArg in typeArgList:
                if argType == typeArg: argType = "[" + argType + "]"
        fieldTypeMod = self.makePtrOpt(tSpec)
        return "_ " + argFieldName + ": " + argType + fieldTypeMod

    def codeStructText(self, classes, attrList, parentClass, classInherits, classImplements, className, structCode, tags):
        classAttrs=''
        if len(attrList)>0:
            for attr in attrList:
                if attr[0]=='@': classAttrs += attr+' '
        if parentClass != "":
            parentClass = ': '+parentClass+' '
            parentClass = progSpec.getUnwrappedClassFieldTypeKeyWord(className)
        if classInherits!=None:
            parentClass=': '
            count =0
            for item in classInherits[0]:
                if count>0:
                    parentClass+= ', '
                parentClass+= progSpec.getUnwrappedClassFieldTypeKeyWord(classes, item)
                count += 1
        typeArgList = progSpec.getTypeArgList(className)
        if(typeArgList != None):
            templateHeader = codeTemplateHeader(className, typeArgList)+" "
            className= className+templateHeader
        S= "\n"+classAttrs+"class "+className+parentClass+"{\n" + structCode + '};\n'
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
    def variableDefaultValueString(self, fType, isTypeArg, owner):
        if (fType == "String"):
            fieldValueText=' = ""'
        elif (fType.startswith("[")):
            fieldValueText=' = '+fType + '()'
        elif (fType == "Bool"):
            fieldValueText=' = false'
        elif (self.isNumericType(fType)):
            fieldValueText=' = 0'
        elif (fType == "Character"):
            fieldValueText=' = "\\0"'
        elif(isTypeArg):
            fieldValueText = ' = ['+fType +']()'
        else:
            if progSpec.ownerIsPointer(owner):fieldValueText = ''
            else:fieldValueText = ' = ' + fType +'()'
        return fieldValueText

    def codeNewVarStr(self, LTSpec, varName, fieldDef, indent, genericArgs, localVarsAlloc):
        varDeclareStr = ''
        assignValue   = ''
        isAllocated   = fieldDef['isAllocated']
        owner         = progSpec.getOwner(LTSpec)
        useCtor       = False
        paramList     = None
        if fieldDef['paramList']: paramList = fieldDef['paramList']
        if paramList and paramList[-1] == "^&useCtor//8":
            del paramList[-1]
            useCtor = True
        cvrtType = self.codeGen.convertType(LTSpec, 'var', genericArgs)
        localVarsAlloc.append([varName, LTSpec])  # Tracking local vars for scope
        allocFieldType = self.codeGen.convertType(LTSpec, 'alloc', genericArgs)
        if(fieldDef['value']):
            [RHS, RTSpec]=self.codeGen.codeExpr(fieldDef['value'][0], None, None, 'RVAL', genericArgs)
            [leftMod, rightMod]=self.chooseVirtualRValOwner(LTSpec, RTSpec)
            RHS = leftMod+RHS+rightMod
            RHS = self.checkForTypeCastNeed(LTSpec, RTSpec, RHS)
            assignValue = " = " + RHS
        elif paramList!=None:       # call constructor  # curly bracket param list
            # Code the constructor's arguments
            modelParams = self.codeGen.chooseCtorModelParams(LTSpec, paramList, genericArgs)
            [CPL, paramTypeList] = self.codeGen.codeParameterList(varName, paramList, modelParams, genericArgs)
            if len(paramTypeList)==1:
                if not isinstance(paramTypeList[0], dict):
                    print("\nPROBLEM: The return type of the parameter '", CPL, "' of "+varName+"(...) cannot be found and is needed. Try to define it.\n",   paramTypeList)
                    exit(1)
                RTSpec  = paramTypeList[0]
                rhsType = progSpec.getFieldType(RTSpec)
                # TODO: Remove the 'True' and make this check object heirarchies or similar solution
                if True or not isinstance(rhsType, str) and cvrtType==rhsType[0]:
                    assignValue = " = " + CPL   # Act like a copy constructor
            if(assignValue==''): assignValue = ' = ' + allocFieldType + CPL
        else: # If no value was given:
            assignValue = self.variableDefaultValueString(allocFieldType, False, owner)
        if assignValue == "":
            assignValue = " = " + allocFieldType + '()'
        fieldTypeMod = self.makePtrOpt(LTSpec)
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

    def codeVarFieldRHS_Str(self, fieldName, cvrtType, tSpec, paramList, isAllocated, typeArgList, genericArgs):
        fieldValueText=""
        fieldOwner=progSpec.getOwner(tSpec)
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
                fieldValueText += self.makePtrOpt(tSpec) # Default String value can't be optional
        return fieldValueText

    def codeConstField_Str(self, convertedType, fieldName, fieldValueText, className, indent):
        decl = ''
        if className=='GLOBAL': defn =  indent  + "let " + fieldName + ':'+ convertedType  + fieldValueText +';\n';
        else: defn =  indent  + "let " + fieldName + ':'+ convertedType  + fieldValueText +';\n';
        return [defn, decl]

    def codeVarField_Str(self, convertedType, tSpec, fieldName, fieldValueText, className, tags, typeArgList, indent):
        # TODO: make test case
        fieldOwner=progSpec.getOwner(tSpec)
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
                convertedType += self.makePtrOpt(tSpec)
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

    def codeCopyConstructor(self, fieldName, isTemplateVar):
        return ""

    def codeConstructorCall(self, className):
        return '        INIT();\n'

    def codeSuperConstructorCall(self, parentClassName):
        return '        super.init();\n'

    def codeFuncHeaderStr(self, className, field, cvrtType, argListText, localArgsAlloc, inheritMode, typeArgList, isNested, indent):
        structCode='\n'; funcDefCode=''; globalFuncs='';
        tSpec        = progSpec.getTypeSpec(field)
        fTypeKW      = progSpec.fieldTypeKeyword(tSpec)
        fieldName    = field['fieldName']
        if fTypeKW =='none': isCtor = True
        else: isCtor = False
        if typeArgList:
            for typeArg in typeArgList:
                if cvrtType == typeArg: cvrtType = '['+cvrtType+']'
        if cvrtType!='': cvrtType = '-> '+cvrtType
        if(className=='AppDelegate'):
            if fieldName=='application':
                structCode += '    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplicationLaunchOptionsKey: Any]?) -> Bool '
                localArgsAlloc.append(['application', {'owner':'me', 'fieldType':'UIApplication', 'arraySpec':None,'argList':None}])
                localArgsAlloc.append(['launchOptions', {'owner':'their', 'fieldType':'int', 'arraySpec':None,'argList':None}])  # TODO: Wrong. launchOptions should be an array.
            else:
                structCode +="func " + fieldName +"("+argListText+") " + cvrtType
        else:
            if fieldName=="init":
                fieldName = "__INIT_"+className
                structCode += indent + "func "  + fieldName +"("+argListText+")" + cvrtType
            else:
                if isCtor:
                    structCode += indent + "init "  +"("+argListText+") " + cvrtType
                else:
                    fieldTypeMod = self.makePtrOpt(tSpec)
                    funcAttrs=''
                    if inheritMode=='override': funcAttrs='override '
                    structCode += indent + funcAttrs + "func " + fieldName +"("+argListText+") " + cvrtType + fieldTypeMod
        return [structCode, funcDefCode, globalFuncs]

    def getVirtualFuncText(self, field):
        field['value'] = '{fatalError("Must Override")}'
        return field['value']+'\n'

    def codeTemplateHeader(self, className, typeArgList):
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
                argTypeSpec  = progSpec.getTypeSpec(arg)
                argFieldName = arg['fieldName']
                topCode     +=  '        var '+argFieldName+' = '+argFieldName+'\n'
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
