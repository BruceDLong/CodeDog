#xlator_Swift.py
import re

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
    modeIdxType           = 'int'
    doesLangHaveGlobals   = True
    funcBodyIndent        = "    "
    funcsDefInClass       = True
    MakeConstructors      = True
    blockPrefix           = "do"
    usePrefixOnStatics    = True
    iteratorsUseOperators = True
    renderGenerics        = "True"
    renameInitFuncs       = True
    useAllCtorArgs        = False
    hasMacros             = False
    useNestedClasses      = False
    nullValue             = "nil"
    langSpecificImpl      = {
                                "Equatable": "Equatable",
                            }

    def getLangSpecificImplements(self, implName):
        if implName in self.langSpecificImpl:
            return self.langSpecificImpl[implName]
        return None

    ###################################################### CONTAINERS
    def codeArrayIndex(self, idx, containerType, LorR_Val, previousSegName, idxTypeSpec):
        fTypeKW = progSpec.fieldTypeKeyword(containerType)
        if fTypeKW == 'string':
            return '[index: ' + idx + ']'
        if progSpec.isNewContainerTempFunc(containerType):
            containerInfo = progSpec.getContainerInfo(self.codeGen.classStore, containerType)
            if containerInfo["isAssociative"] and LorR_Val == "RVAL":
                return '[' + idx + ']!'
        return '[' + idx + ']'

    ###################################################### CONTAINER REPETITIONS
    def emitLoopWithBody(self, header, prologue, body, returnType, mods, genericArgs, indent):
        actionText = indent + header + " {\n"
        if prologue:
            actionText += prologue

        whereExprNode = mods.get("whereExpr") if mods else None
        untilExprNode = mods.get("untilExpr") if mods else None
        if whereExprNode:
            whereExprIn = whereExprNode[0] if not isinstance(whereExprNode, str) else whereExprNode
            [whereExpr, _whereType] = self.codeGen.codeExpr(whereExprIn, None, None, "RVAL", genericArgs)
            actionText += indent + "    if !(" + whereExpr + ") { continue }\n"
        if untilExprNode:
            untilExprIn = untilExprNode[0] if not isinstance(untilExprNode, str) else untilExprNode
            [untilExpr, _untilType] = self.codeGen.codeExpr(untilExprIn, None, None, "RVAL", genericArgs)
            actionText += indent + "    if " + untilExpr + " { break }\n"

        for repAction in body:
            actionText += self.codeGen.codeAction(repAction, indent + "    ", returnType, genericArgs)
        actionText += indent + "}\n"
        return actionText

    def codeRangeSpec(self, traversalMode, ctrType, repName, S_low, S_hi, inclusive, indent, body, returnType, mods, genericArgs):
        mode = traversalMode or 'Forward'
        if mode == 'Forward':
            if inclusive:
                header = f"for {repName} in Int({S_low})...Int({S_hi})"
            else:
                header = f"for {repName} in Int({S_low})..<Int({S_hi})"
            return self.emitLoopWithBody(header, "", body, returnType, mods, genericArgs, indent)

        elif mode == 'Backward':
            start = f"Int({S_hi})" if inclusive else f"(Int({S_hi})-1)"
            header = f"for {repName} in stride(from: {start}, through: Int({S_low}), by: -1)"
            return self.emitLoopWithBody(header, "", body, returnType, mods, genericArgs, indent)
        else:
            cdErr(f"Unknown traversalMode for range: {traversalMode}")

    def traversalLoopWithBodyStr(
        self,
        classes,
        localVarsAlloc,
        ctnrTSpec,
        binding,
        ctnrName,
        body,
        returnType,
        mods,
        genericArgs,
        indent,
        traversalMode=None,
        rangeMode=None,
        rangeSpec=None,
    ):
        fTypeKW = progSpec.fieldTypeKeyword(ctnrTSpec)
        bkind = binding.get("kind")
        axis = binding.get("axis")

        def requireSpec(spec, message):
            if spec == None:
                cdErr(message)
            return spec

        if fTypeKW == "string":
            if rangeMode is not None:
                cdErr("Swift string traversal ranges are not implemented yet.")
            if bkind != "single" or (axis is not None and axis != "value"):
                cdErr("Swift string traversal requires a single value binding.")
            repName = binding.get("name")
            if not repName:
                cdErr("Swift string traversal missing loop variable name.")
            localVarsAlloc.append([repName, {'owner': 'me', 'fieldType': 'char'}])
            sequenceExpr = ctnrName + ".reversed()" if traversalMode == "Backward" else ctnrName
            return self.emitLoopWithBody("for " + repName + " in " + sequenceExpr, "", body, returnType, mods, genericArgs, indent)

        containerInfo = progSpec.getContainerInfo(self.codeGen.classStore, ctnrTSpec)
        containerCat = containerInfo["category"]
        isAssociative = containerInfo["isAssociative"] or containerInfo["entryShape"] == "entry"
        if rangeMode is not None and rangeMode != "keys":
            cdErr("Swift traversal range mode '" + str(rangeMode) + "' is not implemented yet.")

        def localBindingType(tSpec):
            return self.codeGen.convertType(tSpec, "var", genericArgs) + self.makePtrOpt(tSpec)

        def keysRangeExpr():
            if not rangeSpec:
                cdErr("Swift keys traversal requires a range.")
            startPR = rangeSpec.get("rangeStart", None)
            endPR = rangeSpec.get("rangeEnd", None)
            if startPR is None or endPR is None:
                cdErr("Swift keys traversal requires start and end keys.")
            [startExpr, _startTSpec] = self.codeGen.codeExpr(startPR[0], None, None, "RVAL", genericArgs)
            [endExpr, _endTSpec] = self.codeGen.codeExpr(endPR[0], None, None, "RVAL", genericArgs)
            inclusive = "true" if bool(getattr(rangeSpec, "inclusiveOp", False)) else "false"
            return [startExpr, endExpr, inclusive]

        def mapEntriesExpr():
            caps = progSpec.getContainerCapabilities(classes, ctnrTSpec)
            if rangeMode == "keys":
                if "ordered_keys" not in caps.get("tags", set()):
                    cdErr("keys: range requires ordered_keys capability for container '" + ctnrName + "'.")
                [startExpr, endExpr, inclusive] = keysRangeExpr()
                expr = ctnrName + ".subEntries(" + startExpr + ", " + endExpr + ", " + inclusive + ")"
            elif containerCat == "Multimap":
                expr = ctnrName + ".entries()"
            elif "ordered_keys" in caps.get("tags", set()):
                expr = ctnrName + ".entries()"
            else:
                expr = ctnrName
            if traversalMode == "Backward":
                expr += ".reversed()"
            return expr

        if bkind == "tuple":
            keyName = binding.get("keyName")
            valName = binding.get("valName")
            if not keyName or not valName:
                cdErr("Swift tuple traversal missing key/value binding names.")
            if not isAssociative:
                cdErr("Swift tuple traversal requires a map-like container.")
            keyTSpec = requireSpec(containerInfo["keyTypeSpec"], "Swift tuple traversal requires a key type.")
            valTSpec = requireSpec(containerInfo["valueTypeSpec"], "Swift tuple traversal requires a value type.")
            localVarsAlloc.append([keyName, keyTSpec])
            localVarsAlloc.append([valName, valTSpec])
            keyType = localBindingType(keyTSpec)
            valType = localBindingType(valTSpec)
            entryName = keyName + "_" + valName + "_entry"
            prologue = (
                indent + "    var " + keyName + ": " + keyType + " = " + entryName + ".key\n"
                + indent + "    var " + valName + ": " + valType + " = " + entryName + ".value\n"
            )
            return self.emitLoopWithBody("for " + entryName + " in " + mapEntriesExpr(), prologue, body, returnType, mods, genericArgs, indent)

        if bkind != "single":
            cdErr("Swift traversal binding kind missing or unknown.")
        repName = binding.get("name")
        if not repName:
            cdErr("Swift traversal missing loop variable name.")
        if axis is None:
            axis = "value"

        if isAssociative:
            keyTSpec = requireSpec(containerInfo["keyTypeSpec"], "Swift map traversal requires a key type.")
            valTSpec = requireSpec(containerInfo["valueTypeSpec"], "Swift map traversal requires a value type.")
            entryName = repName + "_entry"
            header = "for " + entryName + " in " + mapEntriesExpr()
            if axis == "key":
                localVarsAlloc.append([repName, keyTSpec])
                keyType = localBindingType(keyTSpec)
                prologue = indent + "    var " + repName + ": " + keyType + " = " + entryName + ".key\n"
            elif axis == "value":
                localVarsAlloc.append([repName, valTSpec])
                localVarsAlloc.append([repName + "_key", keyTSpec])
                keyType = localBindingType(keyTSpec)
                valType = localBindingType(valTSpec)
                prologue = (
                    indent + "    var " + repName + ": " + valType + " = " + entryName + ".value\n"
                    + indent + "    var " + repName + "_key: " + keyType + " = " + entryName + ".key\n"
                )
            else:
                cdErr("Swift map traversal axis '" + str(axis) + "' is not implemented.")
            return self.emitLoopWithBody(header, prologue, body, returnType, mods, genericArgs, indent)

        if rangeMode is not None:
            cdErr("Swift list traversal ranges are not implemented yet.")
        if axis != "value":
            cdErr("Swift list traversal only supports value bindings.")
        valTSpec = requireSpec(containerInfo["valueTypeSpec"], "Swift list traversal requires a value type.")
        localVarsAlloc.append([repName, valTSpec])
        sequenceExpr = ctnrName + ".reversed()" if traversalMode == "Backward" else ctnrName
        valType = localBindingType(valTSpec)
        entryName = repName + "_entry"
        prologue = indent + "    var " + repName + ": " + valType + " = " + entryName + "\n"
        return self.emitLoopWithBody("for " + entryName + " in " + sequenceExpr, prologue, body, returnType, mods, genericArgs, indent)


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
            else:
                indexSpec = progSpec.getContainerInfo(self.codeGen.classStore, tSpec)["indexTypeSpec"]
                if indexSpec != None:
                    idxType = progSpec.fieldTypeKeyword(indexSpec)
        return idxType

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
            elif(fType=='uint'):   return 'UInt'
            elif(fType=='int8' or fType=='int16' or fType=='int32'): return 'Int'
            elif(fType=='uint64'): return 'UInt64'
            elif(fType=='int64'):  return 'Int64'
            elif(fType=='long'):   return 'Int64'
            elif(fType=='int'):    return 'Int'
            elif(fType=='bool'):   return 'Bool'
            elif(fType=='void'):   return 'Void'
            elif(fType=='float'):  return 'Float'
            elif(fType=='double'): return 'Double'
            elif(fType=='string'): return 'String'
            elif(fType=='char'):   return 'Character'
            elif(fType=='any'):    return 'AnyObject'
            langType=progSpec.flattenObjectName(fType)
        else: langType=progSpec.flattenObjectName(fType[0])
        return langType

    def applyIterator(self, langType, itrTypeKW, varMode):
        if itrTypeKW:
            genericSuffix = ''
            genericStart = langType.find('<')
            if genericStart != -1:
                genericSuffix = langType[genericStart:]
            return itrTypeKW + genericSuffix
        return langType

    def applyOwner(self, owner, langType, varMode):
        # varMode is 'var' or 'arg' or 'alloc'.
        if owner=='me':         langType = langType
        elif owner=='my':       langType = langType
        elif owner=='our':      langType = langType
        elif owner=='their':    langType = langType
        elif owner=='itr':
            if langType.startswith("Dictionary<") and langType.endswith(">"):
                langType = "SwiftMapCursor" + langType[len("Dictionary"):]
            elif langType.startswith("SwiftTreeMap<") and langType.endswith(">"):
                langType = "SwiftTreeMapCursor" + langType[len("SwiftTreeMap"):]
            elif langType.startswith("SwiftTreeMultimap<") and langType.endswith(">"):
                langType = "SwiftTreeMultimapCursor" + langType[len("SwiftTreeMultimap"):]
        elif owner=='const':    langType = langType
        elif owner=='we':       langType += 'public static'
        else: cdErr("ERROR: Owner of type not valid '" + owner + "'")
        return langType

    def getUnwrappedClassOwner(self, classes, tSpec, fType, varMode, ownerIn):
        ownerOut = ownerIn
        ownerOut = progSpec.getOwner(tSpec)
        if ownerOut == 'itr':
            return ownerOut
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

    def recodeStringFunctions(self, name, tSpec, lenArgs):
        if name == "size":
            tSpec['codeConverter']='%0.count'
            tSpec['fieldType']='int'
        elif name == "subStr":
            if lenArgs==1: tSpec['codeConverter']='%0.substring(from:%1, to:%0.count)'
            else: tSpec['codeConverter']='substring(from:%1, to:%2)'
        return [name, tSpec]

    def langStringFormatterCommand(self, fmtStr, argStr):
        S='String(format:'+'"'+ fmtStr +'"'+ argStr +')'
        return S

    def LanguageSpecificDecorations(self, S, tSpec, owner, LorRorP_Val):
        if tSpec!= 0 and progSpec.typeIsPointer(tSpec) and tSpec['owner']!='itr' and not 'codeConverter' in tSpec:
            if LorRorP_Val == "ARG" and S=="nil":
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
        elif (LTypeKW == 'int' or LTypeKW == 'int32') and RTypeKW=='char':
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
                        ctnrCat = progSpec.getContaineCategory(self.codeGen.classStore, itemTypeSpec) # NEW
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

    def langVarNamePrefix(self, crntBaseName, refedClass):
        return(refedClass + self.ObjConnector)

    def getEnumStr(self, fieldName, enumList):
        S = "typealias " + fieldName + " = Int\n"
        count=0
        for enumName in enumList:
            S += "static let " + enumName + ": Int = " + str(count) + ";\n"
            count=count+1
        S += "\n"
        return(S)

    def getEnumGlobalStr(self, fieldName, enumList):
        S = "typealias " + fieldName + " = Int\n"
        count=0
        for enumName in enumList:
            S += "let " + enumName + ": Int = " + str(count) + ";\n"
            count=count+1
        S += "\n"
        return(S)

    def getEnumStringifyFunc(self, className, enumList):
        return "let " + className + "Strings: [String] = [\"" + "\", \"".join(enumList) + "\"]\n"

    def codeIdentityCheck(self, S, S2, retType1, retType2, opIn):
        if opIn == '===':
            return S+' === '+S2
        else:
            if progSpec.varsTypeCategory(retType1) == 'bool' and S2 == 'false':
                if opIn == '==':
                    return '(!(' + S + '))'
                if opIn == '!=':
                    return '(' + S + ')'
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
    def swiftStringLiteralContent(self, text):
        return text.replace("\\x1b", "\\u{1B}").replace("\\x1B", "\\u{1B}")

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
        incDecExpr = None
        incDecPos = None
        if "incDecPrefixExpr" in item and item.incDecPrefixExpr:
            incDecExpr = item.incDecPrefixExpr
            incDecPos = "prefix"
        elif "incDecPostfixExpr" in item and item.incDecPostfixExpr:
            incDecExpr = item.incDecPostfixExpr
            incDecPos = "postfix"

        if incDecExpr != None:
            op = incDecExpr.incDecOp
            if not isinstance(op, str):
                op = op[0]
            targetRef = incDecExpr.incDecTarget
            [targetExpr, retTypeSpec, prntType, AltIDXFormat] = self.codeGen.codeItemRef(targetRef, 'LVAL', returnType, LorRorP_Val, genericArgs)
            if op == '++':
                if incDecPos == "postfix":
                    S = self.codePostIncrementExpr(targetExpr)
                else:
                    S = self.codePreIncrementExpr(targetExpr)
            elif op == '--':
                if incDecPos == "postfix":
                    S = self.codePostDecrementExpr(targetExpr)
                else:
                    S = self.codePreDecrementExpr(targetExpr)
            else:
                cdErr("Unknown increment/decrement operator '{}'".format(op))
            return [S, retTypeSpec]

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
                    innerS = self.swiftStringLiteralContent(item0[1:-1])
                    if returnType != None and returnType["fieldType"]=="char":
                        retTypeSpec='char'
                        if len(innerS)==1:
                            S+='"'+innerS +'"'
                        else:
                            cdErr("Characters must have exactly 1 character.")
                    else:
                        S+='"'+innerS +'"'
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
            argList=segSpec[2]
            if(funcName=='print'):
                S+='print('
                count = 0
                for P in argList:
                    [S2, argTypeSpec]=self.codeGen.codeExpr(P[0], None, None, 'ARG', genericArgs)
                    [S2, isDerefd]=self.derefPtr(S2, argTypeSpec)
                    if(count>0): S+=', '
                    S+=S2
                    count= count + 1
                S+=',separator:"", terminator:"")'
            elif(funcName=='AllocateOrClear'):
                [varName,  varTypeSpec]=self.codeGen.codeExpr(argList[0][0], None, None, 'ARG', genericArgs)
                if(varTypeSpec==0): cdErr("Name is undefined: " + varName)
                if(varName[-1]=='!'): varNameUnRefed=varName[:-1]  # Remove a reference. It would be better to do this in self.codeGen.codeExpr but may take some work.
                else: varNameUnRefed=varName
                S+='if('+varNameUnRefed+' != nil){'+varName+'.clear();} else {'+varName+" = "+self.codeXlatorAllocater(varTypeSpec, genericArgs)+"();}"
            elif(funcName=='Allocate'):
                [varName,  varTypeSpec]=self.codeGen.codeExpr(argList[0][0], None, None, 'LVAL', genericArgs)
                if(varTypeSpec==0): cdErr("Name is Undefined: " + varName)
                S+=varName+" = "+self.codeXlatorAllocater(varTypeSpec, genericArgs)+'('
                count=0   # TODO: As needed, make this call codeArgList() with modelParams of the constructor.
                for P in argList[1:]:
                    if(count>0): S+=', '
                    [S2, argType]=self.codeGen.codeExpr(P[0], None, None, 'ARG', genericArgs)
                    S+=S2
                    count=count+1
                S+=")"
            elif(funcName=='callPeriodically'):
                [callbackClassName, callbackClassTypeSpec]=self.codeGen.codeExpr(argList[0][0], None, None, 'ARG', genericArgs)
                [objName,  fType]=self.codeGen.codeExpr(argList[1][0], None, None, 'ARG', genericArgs)
                [interval,  intSpec] = self.codeGen.codeExpr(argList[2][0], None, None, 'ARG', genericArgs)
                varTypeSpec = progSpec.fieldTypeKeyword(fType)
                if varTypeSpec == None or varTypeSpec == 'void':
                    varTypeSpec = callbackClassName.strip('"').strip("'")
                callbackTargetExpr = objName
                if progSpec.ownerIsPointer(progSpec.getOwner(fType)) and objName != 'self' and not objName.endswith('!'):
                    callbackTargetExpr = objName + '!'
                callbackBody = 'callbackTarget.run()'
                S += 'let callbackTarget = ' + callbackTargetExpr + '; Timer.scheduledTimer(withTimeInterval: Double(' + interval + ') / 1000.0, repeats: true) { timer in ' + callbackBody + ' }'
                fType = 'void'
            elif(funcName=='callOnce'):
                [callbackClassName, callbackClassTypeSpec]=self.codeGen.codeExpr(argList[0][0], None, None, 'ARG', genericArgs)
                [objName,  fType]=self.codeGen.codeExpr(argList[1][0], None, None, 'ARG', genericArgs)
                [methodName,  methodSpec]=self.codeGen.codeExpr(argList[2][0], None, None, 'ARG', genericArgs)
                [interval,  intSpec] = self.codeGen.codeExpr(argList[3][0], None, None, 'ARG', genericArgs)
                callbackTargetExpr = objName
                if progSpec.ownerIsPointer(progSpec.getOwner(fType)) and objName != 'self' and not objName.endswith('!'):
                    callbackTargetExpr = objName + '!'
                methodName = methodName.strip('"').strip("'")
                callbackBody = 'callbackTarget.' + methodName + '()'
                S += 'let callbackTarget = ' + callbackTargetExpr + '; Timer.scheduledTimer(withTimeInterval: Double(' + interval + ') / 1000.0, repeats: false) { timer in ' + callbackBody + ' }'
                fType = 'void'
            elif(funcName=='break'):
                if len(argList)==0: S='break'
            elif(funcName=='return'):
                if len(argList)==0: S+='return'
            elif(funcName=='toStr'):
                if len(argList)==1:
                    [S2, argType]=self.codeGen.codeExpr(P[0][0], None, None, 'ARG', genericArgs)
                    S2=self.derefPtr(S2, argType)
                    S+='to_string('+S2+')'
                    returnType='string'
        else: # Not parameters, i.e., not a function
            if(funcName=='self'):
                S+='self'

        return [S, retOwner, fType]

    def checkIfSpecialAssignmentFormIsNeeded(self, action, indent, AltIDXFormat, RHS, rhsType, LHS, LHSParentType, LHS_FieldType):
        return ''

    def codePlusEquals(self, LHS, RHS, LHS_FieldType, rhsTypeSpec):
        lhsType = progSpec.fieldTypeKeyword(LHS_FieldType)
        rhsType = progSpec.fieldTypeKeyword(rhsTypeSpec)
        if lhsType == "string" and rhsType != "string":
            return LHS + " += String(" + RHS + ")"
        return LHS + " += " + RHS

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
            if parentClass != "": parentClass+= ', '
            else: parentClass=': '
            count = 0
            for item in classInherits[0]:
                if count>0:
                    parentClass+= ', '
                parentClass+= progSpec.getUnwrappedClassFieldTypeKeyWord(classes, item)
                count += 1
        if classImplements!=None:
            if parentClass != "": parentClass+= ', '
            else: parentClass=': '
            count = 0
            for item in classImplements:
                if count>0:
                    parentClass+= ', '
                parentClass+= item
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

    def postProcessOutput(self, outputText):
        while "!!" in outputText:
            outputText = outputText.replace("!!", "!")
        return outputText

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
        argList       = None
        if fieldDef['argList']: argList = fieldDef['argList']
        if argList and argList[-1] == "^&useCtor//8":
            del argList[-1]
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
        elif argList!=None:       # call constructor  # curly bracket arg list
            # Code the constructor's arguments
            modelParams = self.codeGen.chooseCtorModelParams(LTSpec, argList, genericArgs)
            [CPL, paramTypeList] = self.codeGen.codeArgList(varName, argList, modelParams, genericArgs)
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

    def codePostIncrement(self, varName):
        return varName + " += 1"

    def codePreIncrementExpr(self, varName):
        return "({ " + varName + " += 1; return " + varName + " }())"

    def codePostIncrementExpr(self, varName):
        return "({ let __cdPostIncOld = " + varName + "; " + varName + " += 1; return __cdPostIncOld }())"

    def codeDecrement(self, varName):
        return varName + " -= 1"

    def codePostDecrement(self, varName):
        return varName + " -= 1"

    def codePreDecrementExpr(self, varName):
        return "({ " + varName + " -= 1; return " + varName + " }())"

    def codePostDecrementExpr(self, varName):
        return "({ let __cdPostDecOld = " + varName + "; " + varName + " -= 1; return __cdPostDecOld }())"

    def isNumericType(self, convertedType):
        if(convertedType == "UInt32" or convertedType == "UInt64" or convertedType == "Float" or convertedType == "Int" or convertedType == "Int32" or convertedType == "Int64" or convertedType == "Double"):
            return True
        return False

    def codeVarFieldRHS_Str(self, fieldName, cvrtType, tSpec, argList, isAllocated, typeArgList, genericArgs):
        fieldValueText=""
        fieldOwner=progSpec.getOwner(tSpec)
        isTypeArg = False
        if typeArgList:
            for typeArg in typeArgList:
                if cvrtType == typeArg: isTypeArg = True
        if argList!=None:
            if argList[-1] == "^&useCtor//8":
                del argList[-1]
            [CPL, paramTypeList] = self.codeGen.codeArgList(fieldName, argList, None, genericArgs)
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
                varPrefix = "lazy var " if self.isInstanceMemberDefault(fieldValueText) else "var "
                defn = indent + varPrefix + fieldName + ": " +  convertedType + fieldValueText + '\n'
            decl = ''
        return [defn, decl]

    def isInstanceMemberDefault(self, defaultText):
        if defaultText == None:
            return False
        expr = defaultText.strip()
        if not expr.startswith("="):
            return False
        expr = expr[1:].strip()
        if expr in ["", "nil", "true", "false"]:
            return False
        return re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", expr) != None

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
            S = '    init(' + ctorArgs+'){\n'+callSuper+ctorInit+funcBody+'    }\n'
        S += '    '+prefix+'init(){\n'+callSuper+funcBody+'    }\n'
        return S

    def codeConstructorInit(self, fieldName, count, defaultVal):
        return "        self." + fieldName +" = arg_"+fieldName+";\n"

    def useFieldAsConstructorArg(self, className, field, defaultVal):
        if className == "arrow":
            return True
        return defaultVal != '' and not self.isInstanceMemberDefault("=" + defaultVal)

    def codeConstructorArgText(self, argFieldName, count, argType, defaultVal):
        if defaultVal == "nil": defaultVal = ""
        if defaultVal and not self.isInstanceMemberDefault("=" + defaultVal):
            argType = argType + '=' + defaultVal
        return "_ arg_" + argFieldName  + ': ' +argType

    def codeCopyConstructor(self, fieldName, isTemplateVar):
        return ""

    def codeConstructorCall(self, className):
        return '        INIT();\n'

    def codeSuperConstructorCall(self, parentClassName):
        return '        super.init();\n'

    def specialFunction(self, fieldName, classDef):
        if fieldName == "__plus": newFieldName = fieldName
        elif fieldName == "__minus": newFieldName = fieldName
        elif fieldName == "__times": newFieldName = fieldName
        elif fieldName == "__divide": newFieldName = fieldName
        elif fieldName == "__negate": newFieldName = fieldName
        elif fieldName == "__plusEqual": newFieldName = fieldName
        elif fieldName == "__lessThan": newFieldName = fieldName
        elif fieldName == "__lessOrEq": newFieldName = fieldName
        elif fieldName == "__greaterThan": newFieldName = fieldName
        elif fieldName == "__greaterOrEq": newFieldName = fieldName
        elif fieldName == "__isEqual":
            newFieldName = fieldName
            if 'tags' in classDef:
                classImplements = progSpec.searchATagStore(classDef['tags'], 'implements')
                if classImplements!=None:
                    if 'Equatable' in classImplements[0]:
                        newFieldName = "=="
        elif fieldName == "__notEqual": newFieldName = fieldName
        elif fieldName == "__inc": newFieldName = fieldName
        elif fieldName == "__opAssign": newFieldName = fieldName
        elif fieldName == "__derefPtr": newFieldName = fieldName
        elif fieldName == "__index": newFieldName = fieldName
        elif fieldName == "__opPtr": newFieldName = fieldName
        else:  newFieldName = fieldName
        return newFieldName

    def codeFuncHeaderStr(self, className, fieldName, field, cvrtType, paramListText, localArgsAlloc, inheritMode, typeArgList, isNested, overRideOper, isStatic, indent):
        structCode='\n'; funcDefCode=''; globalFuncs='';
        tSpec        = progSpec.getTypeSpec(field)
        fTypeKW      = progSpec.fieldTypeKeyword(tSpec)
        if fTypeKW =='none': isCtor = True
        else: isCtor = False
        if typeArgList:
            for typeArg in typeArgList:
                if cvrtType == typeArg: cvrtType = '['+cvrtType+']'
        if cvrtType!='': cvrtType = '-> '+cvrtType
        if(className=='AppDelegate'):
            if fieldName=='application':
                structCode += '    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplicationLaunchOptionsKey: Any]?) -> Bool '
                localArgsAlloc.append(['application', {'owner':'me', 'fieldType':'UIApplication', 'arraySpec':None,'paramList':None}])
                localArgsAlloc.append(['launchOptions', {'owner':'their', 'fieldType':'int', 'arraySpec':None,'paramList':None}])  # TODO: Wrong. launchOptions should be an array.
            else:
                structCode +="func " + fieldName +"("+paramListText+") " + cvrtType
        else:
            if fieldName=="init":
                fieldName = "__INIT_"+className
                structCode += indent + "func "  + fieldName +"("+paramListText+")" + cvrtType
            else:
                if isCtor:
                    structCode += indent + "init "  +"("+paramListText+") " + cvrtType
                else:
                    fieldTypeMod = self.makePtrOpt(tSpec)
                    funcAttrs = ''
                    staticKW  = ''
                    if isStatic: staticKW = 'static '
                    if inheritMode=='override': funcAttrs='override '
                    structCode += indent + funcAttrs + staticKW + "func " + fieldName +"("+paramListText+") " + cvrtType + fieldTypeMod
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

    def extraCodeForTopOfFuntion(self, paramList):
        if len(paramList)==0:
            topCode=''
        else:
            topCode=""
            for param in paramList:
                paramTypeSpec  = progSpec.getTypeSpec(param)
                paramFieldName = param['fieldName']
                topCode     +=  '        var '+paramFieldName+' = '+paramFieldName+'\n'
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
        progSpec.addClass(classes[0], classes[1], 'GLOBAL', 'struct', 'SEQ',["//^", "Main class"])
        codeDogParser.AddToObjectFromText(classes[0], classes[1], progSpec.wrapFieldListInObjectDef('GLOBAL',  mainFuncCode ), 'Swift start-up code')

    def __init__(self):
        print("INIT")
