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
    typeForCounterInt     = "int"
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
    swiftReservedWords    = {
                                "associatedtype", "class", "deinit", "enum", "extension",
                                "fileprivate", "func", "import", "init", "inout",
                                "internal", "let", "open", "operator", "private",
                                "precedencegroup", "protocol", "public", "rethrows",
                                "static", "struct", "subscript", "typealias", "var",
                                "break", "case", "catch", "continue", "default", "defer",
                                "do", "else", "fallthrough", "for", "guard", "if",
                                "in", "repeat", "return", "throw", "switch", "where",
                                "while", "as", "Any", "false", "is", "nil", "self",
                                "Self", "super", "throws", "true", "try", "_",
                            }

    def getLangSpecificImplements(self, implName):
        if implName in self.langSpecificImpl:
            return self.langSpecificImpl[implName]
        return None

    def swiftIdentifier(self, name):
        if not isinstance(name, str):
            return name
        if name.startswith("`") and name.endswith("`"):
            return name
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name) and name in self.swiftReservedWords:
            return "`" + name + "`"
        return name

    def codeIdentifier(self, name):
        if name in ["return", "break", "continue", "nil", "true", "false", "self", "Self", "super"]:
            return name
        return self.swiftIdentifier(name)

    def swiftListParamUsesInout(self, tSpec):
        if tSpec == None or not isinstance(tSpec, dict):
            return False
        if not progSpec.typeIsPointer(tSpec):
            return False
        if progSpec.fieldTypeKeyword(tSpec) == "List":
            return True
        if not progSpec.isAContainer(tSpec):
            return False
        try:
            return progSpec.getDatastructID(tSpec) == "list"
        except Exception:
            return False

    def swiftValueParamUsesInout(self, tSpec):
        if tSpec == None or not isinstance(tSpec, dict):
            return False
        if not progSpec.typeIsPointer(tSpec):
            return False
        return progSpec.fieldTypeKeyword(tSpec) in ["bool", "boolean"]

    def swiftParamUsesPointerOut(self, tSpec, paramName=None):
        if tSpec == None or not isinstance(tSpec, dict):
            return False
        if not progSpec.typeIsPointer(tSpec):
            return False
        fieldType = progSpec.fieldTypeKeyword(tSpec)
        if progSpec.isAContainer(tSpec):
            return True
        return fieldType in [
            "bool", "boolean", "flag", "mode",
            "int", "int32", "int64",
            "uint", "uint32", "uint64",
            "float", "double", "numeric",
            "char", "string", "String",
            "FlexNum", "BigInt", "BigFrac", "BigFloat",
        ]

    def swiftScalarParamUsesPointerOut(self, tSpec, paramName=None):
        return self.swiftParamUsesPointerOut(tSpec, paramName)

    def swiftParamUsesInout(self, tSpec):
        return False

    def localParamTypeSpec(self, tSpec, paramName=None):
        if self.swiftParamUsesPointerOut(tSpec, paramName):
            localTSpec = tSpec.copy()
            localTSpec["owner"] = "me"
            if paramName != None:
                emitName = self.swiftIdentifier(paramName)
                localTSpec["codeConverter"] = emitName + "!.pointee"
                localTSpec["swiftPointerOutParamName"] = emitName
            return localTSpec
        if not self.swiftParamUsesInout(tSpec):
            return tSpec
        localTSpec = tSpec.copy()
        localTSpec["owner"] = "me"
        return localTSpec

    def codePointerOutArg(self, argText, argTypeSpec, modelTypeSpec):
        if argText == "nil" or argText == "NULL" or argText == "nullptr":
            return "nil"
        if argTypeSpec != None and isinstance(argTypeSpec, dict):
            rawParam = argTypeSpec.get("swiftPointerOutParamName")
            if rawParam != None:
                return rawParam
        return "&" + argText

    ###################################################### CONTAINERS
    def codeArrayIndex(self, idx, containerType, LorR_Val, previousSegName, idxTypeSpec):
        if idxTypeSpec != None and not isinstance(idxTypeSpec, str) and progSpec.typeIsPointer(idxTypeSpec) and not idx.endswith('!'):
            idx += '!'
        fTypeKW = progSpec.fieldTypeKeyword(containerType)
        if fTypeKW == 'string':
            return '[index: ' + idx + ']'
        if progSpec.isAContainer(containerType) and progSpec.typeIsPointer(containerType):
            return '![' + idx + ']'
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
            cmpOp = "<=" if inclusive else "<"
            step = " += 1"
            startExpr = f"Int({S_low})"
            endExpr = f"Int({S_hi})"

        elif mode == 'Backward':
            cmpOp = ">="
            step = " -= 1"
            startExpr = f"Int({S_hi})" if inclusive else f"(Int({S_hi})-1)"
            endExpr = f"Int({S_low})"
        else:
            cdErr(f"Unknown traversalMode for range: {traversalMode}")

        endName = repName + "_end"
        header = "while " + repName + " " + cmpOp + " " + endName
        prologue = indent + "    defer { " + repName + step + " }\n"
        return (
            indent + "var " + repName + ": Int = " + startExpr + "\n"
            + indent + "let " + endName + ": Int = " + endExpr + "\n"
            + self.emitLoopWithBody(header, prologue, body, returnType, mods, genericArgs, indent)
        )

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

        def containerExpr(expr):
            if progSpec.isAContainer(ctnrTSpec) and progSpec.typeIsPointer(ctnrTSpec) and not expr.endswith("!"):
                return expr + "!"
            return expr

        if fTypeKW == "string":
            if rangeMode is not None:
                cdErr("Swift string traversal ranges are not implemented yet.")
            if bkind != "single" or (axis is not None and axis != "value"):
                cdErr("Swift string traversal requires a single value binding.")
            repName = binding.get("name")
            if not repName:
                cdErr("Swift string traversal missing loop variable name.")
            localVarsAlloc.append([repName, {'owner': 'me', 'fieldType': 'char'}])
            sequenceBase = containerExpr(ctnrName)
            sequenceExpr = sequenceBase + ".reversed()" if traversalMode == "Backward" else sequenceBase
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
                expr = containerExpr(ctnrName) + ".subEntries(" + startExpr + ", " + endExpr + ", " + inclusive + ")"
            elif containerCat == "Multimap":
                expr = containerExpr(ctnrName) + ".entries()"
            elif "ordered_keys" in caps.get("tags", set()):
                expr = containerExpr(ctnrName) + ".entries()"
            else:
                expr = containerExpr(ctnrName)
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
            emitKeyName = self.swiftIdentifier(keyName)
            emitValName = self.swiftIdentifier(valName)
            prologue = (
                indent + "    var " + emitKeyName + ": " + keyType + " = " + entryName + ".key\n"
                + indent + "    var " + emitValName + ": " + valType + " = " + entryName + ".value\n"
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
            emitRepName = self.swiftIdentifier(repName)
            if axis == "key":
                localVarsAlloc.append([repName, keyTSpec])
                keyType = localBindingType(keyTSpec)
                prologue = indent + "    var " + emitRepName + ": " + keyType + " = " + entryName + ".key\n"
            elif axis == "value":
                localVarsAlloc.append([repName, valTSpec])
                localVarsAlloc.append([repName + "_key", keyTSpec])
                keyType = localBindingType(keyTSpec)
                valType = localBindingType(valTSpec)
                prologue = (
                    indent + "    var " + emitRepName + ": " + valType + " = " + entryName + ".value\n"
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
        sequenceBase = containerExpr(ctnrName)
        sequenceExpr = sequenceBase + ".reversed()" if traversalMode == "Backward" else sequenceBase
        valType = localBindingType(valTSpec)
        entryName = repName + "_entry"
        prologue = indent + "    var " + self.swiftIdentifier(repName) + ": " + valType + " = " + entryName + "\n"
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
        elif owner=='const':    langType = langType
        elif owner=='we':       langType = langType
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

    def recodeStringFunctions(self, name, tSpec, lenArgs):
        if name == "size":
            tSpec['codeConverter']='%0.count'
            tSpec['fieldType']='int'
        elif name == "subStr":
            if lenArgs==1: tSpec['codeConverter']='%0.substring(from:%1, to:%0.count)'
            else: tSpec['codeConverter']='%0.substring(from:%1, to:Int(%1)+Int(%2))'
        return [name, tSpec]

    def langStringFormatterCommand(self, fmtStr, argStr):
        S='String(format:'+'"'+ fmtStr +'"'+ argStr +')'
        return S

    def LanguageSpecificDecorations(self, S, tSpec, owner, LorRorP_Val):
        if tSpec!= 0 and progSpec.typeIsPointer(tSpec) and not 'codeConverter' in tSpec:
            if LorRorP_Val == "ARG" and S=="nil":
                cvrtType = self.codeGen.convertType(tSpec, 'arg', genericArgs)
                S = 'Optional<'+cvrtType+'>.none'
        return S

    def convertToInt(self, S, tSpec):
        return S

    def swiftExprIsStaticIntegerConstant(self, expr):
        if not isinstance(expr, str):
            return False
        expr = expr.strip()
        match = re.fullmatch(r"(?:[A-Za-z_][A-Za-z0-9_]*\.)?([A-Za-z_][A-Za-z0-9_]*)", expr)
        if match == None:
            return False
        memberName = match.group(1)
        if memberName.endswith("Strings"):
            return False
        return memberName in self.codeGen.StaticMemberVars

    def checkForTypeCastNeed(self, lhsTSpec, rhsTSpec, RHS):
        LTypeKW = progSpec.fieldTypeKeyword(lhsTSpec)
        RTypeKW = progSpec.fieldTypeKeyword(rhsTSpec)
        if LTypeKW == 'bool'or LTypeKW == 'boolean':
            if lhsTSpec != None and not isinstance(lhsTSpec, str) and progSpec.typeIsPointer(lhsTSpec):
                return RHS
            if progSpec.typeIsPointer(rhsTSpec):
                return '(' + RHS + ' != nil)'
            if (RTypeKW=='int' or RTypeKW=='int32' or RTypeKW=='int64' or RTypeKW=='uint' or RTypeKW=='uint64' or RTypeKW=='flag' or RTypeKW=='mode' or RTypeKW=='numeric' or self.swiftExprIsStaticIntegerConstant(RHS)):
                if RHS[0]=='!': return '(' + RHS[1:] + ' == 0)'
                else: return '(' + RHS + ' != 0)'
            if RHS == "0": return "false"
            if RHS == "1": return "true"
        elif LTypeKW == 'FlexNum' and RTypeKW=='uint64':
            RHS = 'FlexNum(UInt64('+RHS+'))'
        elif LTypeKW == 'FlexNum' and RTypeKW=='BigInt':
            RHS = 'FlexNum('+RHS+')'
        elif LTypeKW == 'FlexNum' and (RTypeKW=='int' or RTypeKW=='int64' or RTypeKW=='numeric'):
            RHS = 'FlexNum(Int64('+RHS+'))'
        elif LTypeKW == 'FlexNum' and RTypeKW=='string':
            RHS = 'FlexNum('+RHS+')'
        elif LTypeKW == 'BigInt' and RTypeKW == 'string':
            RHS = 'CodeDogBigInt('+RHS+', radix: 10)'
        elif LTypeKW == 'BigInt' and (RTypeKW=='int' or RTypeKW=='int64' or RTypeKW=='uint64' or RTypeKW=='numeric'):
            RHS = 'CodeDogBigInt('+RHS+')'
        elif (LTypeKW == 'BigFrac' or LTypeKW == 'BigFloat') and RTypeKW=='string':
            RHS = 'CodeDogBigFrac(decimal: '+RHS+', radix: 10)'
        elif (LTypeKW == 'BigFrac' or LTypeKW == 'BigFloat') and RTypeKW == 'BigInt':
            RHS = 'CodeDogBigFrac('+RHS+')'
        elif (LTypeKW == 'BigFrac' or LTypeKW == 'BigFloat') and (RTypeKW=='int' or RTypeKW=='int64' or RTypeKW=='uint64' or RTypeKW=='numeric' or RTypeKW=='double' or RTypeKW=='float'):
            RHS = 'CodeDogBigFrac('+RHS+')'
        elif LTypeKW == 'double' and (RTypeKW == 'BigFrac' or RTypeKW == 'BigFloat'):
            RHS = RHS + '.toDouble()'
        elif LTypeKW == 'double' and RTypeKW=='string':
            RHS = '(Double('+RHS+') ?? 0.0)'
        elif LTypeKW == 'uint64' and RTypeKW=='int':
            RHS = 'UInt64('+RHS+')'
        elif LTypeKW == 'uint64' and RTypeKW=='int64':
            RHS = 'UInt64('+RHS+')'
        elif LTypeKW == 'uint64' and RTypeKW=='mode':
            RHS = 'UInt64('+RHS+')'
        elif LTypeKW == 'uint' and RTypeKW=='int':
            RHS = 'UInt('+RHS+')'
        elif LTypeKW == 'int64' and RTypeKW=='int':
            RHS = 'Int64('+RHS+')'
        elif LTypeKW == 'int64' and RTypeKW=='uint64':
            RHS = 'Int64('+RHS+')'
        elif LTypeKW == 'int64' and (RTypeKW=='BigFloat' or RTypeKW=='BigFrac'):
            RHS = RHS + '.toInt64()'
        elif LTypeKW == 'int64' and RTypeKW=='double':
            RHS = 'Int64('+RHS+')'
        elif LTypeKW == 'int64' and RTypeKW=='bool':
            RHS = '('+RHS+' ? 1 : 0)'
        elif (LTypeKW == 'int' or LTypeKW == 'int32') and RTypeKW=='bool':
            RHS = '('+RHS+' ? 1 : 0)'
        elif (LTypeKW == 'int' or LTypeKW == 'int32') and RTypeKW=='flag':
            RHS = '(('+RHS+') != 0 ? 1 : 0)'
        elif LTypeKW == 'double' and RTypeKW=='int':
            RHS = 'Double('+RHS+')'
        elif LTypeKW == 'double' and (RTypeKW=='float' or RTypeKW=='numeric'):
            RHS = 'Double('+RHS+')'
        elif (LTypeKW == 'int' or LTypeKW == 'int32') and RTypeKW=='char':
            RHS = RHS+'.asciiValue'
        elif LTypeKW == 'string' and RTypeKW=='char':
            RHS = "String(" + RHS+ ")"
        #elif LTypeKW != RTypeKW and LTypeKW != "mode" and LTypeKW != "flag" and RTypeKW != "ERROR" and LTypeKW != "struct" and LTypeKW != "bool":
        return RHS

    def getTheDerefPtrMods(self, itemTypeSpec):
        if itemTypeSpec!=None and isinstance(itemTypeSpec, dict) and 'owner' in itemTypeSpec:
            if progSpec.isAContainer(itemTypeSpec):
                if progSpec.typeIsPointer(itemTypeSpec): return ['', '!', False]
                return ['', '', False]
            if progSpec.typeIsPointer(itemTypeSpec):
                owner=progSpec.getOwner(itemTypeSpec)
                if progSpec.isAContainer(itemTypeSpec):
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
        if varRef=='self' or varRef=='self!': return ['self', False]
        [leftMod, rightMod, isDerefd] = self.getTheDerefPtrMods(itemTypeSpec)
        S = leftMod + varRef + rightMod
        return [S, isDerefd]

    def codeExplicitDeref(self, varRef, itemTypeSpec):
        return varRef + "!"

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
        def unwrapOptionalContainerSubscript(expr):
            if "![" in expr or "[" not in expr:
                return expr
            baseName = expr.split("[", 1)[0]
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", baseName):
                return expr
            ref = self.codeGen.CheckFunctionsLocalVarArgList(baseName)
            if ref and len(ref) > 0:
                tSpec = ref[0]
                if progSpec.isAContainer(tSpec) and progSpec.typeIsPointer(tSpec):
                    return baseName + "![" + expr.split("[", 1)[1]
            return expr

        if opIn == '===' or opIn == '!==':
            if retType1 != None and not isinstance(retType1, str) and progSpec.typeIsPointer(retType1) and S.endswith('!'):
                S = S[:-1]
            if retType2 != None and not isinstance(retType2, str) and progSpec.typeIsPointer(retType2) and S2.endswith('!'):
                S2 = S2[:-1]
            opOut = ' === ' if opIn == '===' else ' !== '
            return S + opOut + S2
        else:
            LTypeKW = progSpec.fieldTypeKeyword(retType1)
            RTypeKW = progSpec.fieldTypeKeyword(retType2)
            if LTypeKW == 'flag' and (S2 == 'false' or S2 == 'true'):
                if opIn == '==':
                    return '(' + S + (' == 0)' if S2 == 'false' else ' != 0)')
                if opIn == '!=':
                    return '(' + S + (' != 0)' if S2 == 'false' else ' == 0)')
            if RTypeKW == 'flag' and (S == 'false' or S == 'true'):
                if opIn == '==':
                    return '(' + S2 + (' == 0)' if S == 'false' else ' != 0)')
                if opIn == '!=':
                    return '(' + S2 + (' != 0)' if S == 'false' else ' == 0)')
            if LTypeKW == 'BigInt' and (RTypeKW == 'int' or RTypeKW == 'int64' or RTypeKW == 'uint64' or RTypeKW == 'numeric'):
                S2 = 'CodeDogBigInt(' + S2 + ')'
            elif RTypeKW == 'BigInt' and (LTypeKW == 'int' or LTypeKW == 'int64' or LTypeKW == 'uint64' or LTypeKW == 'numeric'):
                S = 'CodeDogBigInt(' + S + ')'
            elif (LTypeKW == 'BigFrac' or LTypeKW == 'BigFloat') and (RTypeKW == 'int' or RTypeKW == 'int64' or RTypeKW == 'uint64' or RTypeKW == 'numeric' or RTypeKW == 'double' or RTypeKW == 'float'):
                S2 = 'CodeDogBigFrac(' + S2 + ')'
            elif (RTypeKW == 'BigFrac' or RTypeKW == 'BigFloat') and (LTypeKW == 'int' or LTypeKW == 'int64' or LTypeKW == 'uint64' or LTypeKW == 'numeric' or LTypeKW == 'double' or LTypeKW == 'float'):
                S = 'CodeDogBigFrac(' + S + ')'
            elif LTypeKW == 'double' and (RTypeKW == 'BigFrac' or RTypeKW == 'BigFloat'):
                S2 = S2 + '.toDouble()'
            elif RTypeKW == 'double' and (LTypeKW == 'BigFrac' or LTypeKW == 'BigFloat'):
                S = S + '.toDouble()'
            if progSpec.varsTypeCategory(retType1) == 'bool' and S2 == 'false':
                if opIn == '==':
                    return '(!(' + S + '))'
                if opIn == '!=':
                    return '(' + S + ')'
            if   (opIn == '=='): opOut=' == '
            elif (opIn == '!='): opOut=' != '
            elif (opIn == '!=='): opOut=' !== '
            else: print("ERROR: '==' or '!=' or '===' or '!==' expected."); exit(2)
            rawPointerOut = None
            if retType1 != None and isinstance(retType1, dict):
                rawPointerOut = retType1.get("swiftPointerOutParamName")
            if rawPointerOut != None and S2 == "nil":
                return rawPointerOut + opOut + S2
            [S_derefd, isDerefd] = self.derefPtr(S, retType1)
            if S2!='nil':
                S=S_derefd
                [S2, isDerefd]=self.derefPtr(S2, retType2)
            elif S[-1]=='!':
                S=S[:-1]   # Todo: Better detect this
            elif S2=='nil':
                S=unwrapOptionalContainerSubscript(S)
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
        if retTypeSpec != None and not isinstance(retTypeSpec, str):
            fType = progSpec.fieldTypeKeyword(retTypeSpec)
            owner = progSpec.getOwner(retTypeSpec)
            if fType == 'flag' or progSpec.typeIsInteger(fType):
                return ['(' + S2 + ' == 0)', {'owner': 'me', 'fieldType': 'bool'}]
            if progSpec.ownerIsPointer(owner) or progSpec.isStruct(fType):
                if S2[-1]=='!': S2=S2[:-1]   # Todo: Better detect this
                return ['(' + S2 + ' == nil)', {'owner': 'me', 'fieldType': 'bool'}]
        if progSpec.varsTypeCategory(retTypeSpec) != 'bool':
            if S2[-1]=='!': S2=S2[:-1]   # Todo: Better detect this
            S='('+S2+' == nil)'
            retTypeSpec='bool'
        else:
            if '&&' in S2 or '||' in S2:
                S+='!' + S2
            else:
                S+='!(' + S2 + ')'
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
                [S2, retTypeSpec] = self.codeGen.codeExpr(item[1], returnType, None, LorRorP_Val, genericArgs)
                if S2 == 'true':
                    S2 = '1'
                    retTypeSpec = {'owner': 'literal', 'fieldType': 'numeric'}
                elif S2 == 'false':
                    S2 = '0'
                    retTypeSpec = {'owner': 'literal', 'fieldType': 'numeric'}
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
                tmp="["
                idx=1
                while idx < len(item)-1:
                    valExpr = item[idx+2]
                    [S2, retTypeSpec] = self.codeGen.codeExpr(valExpr, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                    if len(tmp)>1: tmp+=", "
                    tmp+=item[idx] + ": " + S2
                    idx += 3
                tmp+="]"
                S+=tmp
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
                if(codeStr=="NULL" or codeStr=="nullptr"):
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
        if lhsType == "string" and rhsType == "int32":
            return LHS + " += String(UnicodeScalar(" + RHS + ") ?? UnicodeScalar(0)!)"
        if lhsType == "string" and rhsType != "string":
            return LHS + " += String(" + RHS + ")"
        if lhsType == "int64" and rhsType == "int":
            return LHS + " += Int64(" + RHS + ")"
        if lhsType == "uint64" and rhsType == "int":
            return LHS + " += UInt64(" + RHS + ")"
        if lhsType == "uint" and rhsType == "int":
            return LHS + " += UInt(" + RHS + ")"
        if lhsType == "double" and rhsType == "int":
            return LHS + " += Double(" + RHS + ")"
        if lhsType == "FlexNum" and rhsType == "int":
            return LHS + " += FlexNum(Int64(" + RHS + "))"
        if lhsType == "FlexNum" and rhsType == "int64":
            return LHS + " += FlexNum(Int64(" + RHS + "))"
        return LHS + " += " + RHS

    ######################################################
    def codeProtectBlock(self, mutex, criticalText, indent):
        return (
            indent + "do {\n"
            + indent + "    " + mutex + ".lock()\n"
            + indent + "    defer { " + mutex + ".unlock() }\n"
            + criticalText
            + indent + "}\n"
        )

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
        if self.swiftScalarParamUsesPointerOut(tSpec, argFieldName):
            return "_ " + self.swiftIdentifier(argFieldName) + ": UnsafeMutablePointer<" + argType + ">?"
        if self.swiftParamUsesInout(tSpec):
            return "_ " + self.swiftIdentifier(argFieldName) + ": inout " + argType
        fieldTypeMod = self.makePtrOpt(tSpec)
        return "_ " + self.swiftIdentifier(argFieldName) + ": " + argType + fieldTypeMod

    def swiftClassHasMethod(self, classes, className, methodName):
        if classes == None or className == None:
            return False
        classDef = progSpec.findSpecOf(classes[0], className, "struct")
        if classDef == None:
            return False
        for field in progSpec.generateListOfFieldsToImplement(classes, className):
            if field.get("fieldName") != methodName:
                continue
            tSpec = progSpec.getTypeSpec(field)
            if isinstance(tSpec, dict) and tSpec.get("paramList") != None:
                return True
        return False

    def isSwiftModeAlias(self, classes, fTypeKW):
        if classes == None or fTypeKW == None:
            return False
        classDef = progSpec.findSpecOf(classes[0], fTypeKW, "struct")
        if classDef == None:
            return False
        try:
            return bool(classDef["tags"]["inherits"]["fieldType"]["altModeIndicator"])
        except (KeyError, TypeError):
            return False

    def isSwiftCopyFromContainer(self, tSpec):
        fTypeKW = progSpec.fieldTypeKeyword(tSpec)
        return fTypeKW in ["Swift_TreeMap", "Swift_TreeMultimap"]

    def swiftGeneratedStorageType(self, classes, tSpec):
        fTypeKW = progSpec.fieldTypeKeyword(tSpec)
        if fTypeKW == None:
            return None
        if self.isSwiftModeAlias(classes, fTypeKW):
            return None
        if self.isSwiftCopyFromContainer(tSpec):
            return None
        storageType = progSpec.getUnwrappedClassFieldTypeKeyWord(classes, fTypeKW)
        if self.isSwiftModeAlias(classes, storageType):
            return None
        classDef = progSpec.findSpecOf(classes[0], storageType, "struct")
        if classDef == None:
            return None
        return progSpec.flattenObjectName(storageType)

    def isGeneratedSwiftClass(self, classes, tSpec):
        return self.swiftGeneratedStorageType(classes, tSpec) != None

    def codeDeepCopyAssignment(self, LHS, RHS, lhsTypeSpec, rhsTypeSpec, indent, genericArgs):
        if lhsTypeSpec == None or isinstance(lhsTypeSpec, str):
            return indent + LHS + " = " + RHS + ";\n"
        fTypeKW = progSpec.fieldTypeKeyword(lhsTypeSpec)
        if self.isSwiftCopyFromContainer(lhsTypeSpec):
            return indent + LHS + ".copyFrom(" + RHS + ");\n"
        if self.swiftClassHasMethod(self.codeGen.classStore, fTypeKW, "__opAssign"):
            return indent + LHS + ".__opAssign(" + RHS + ");\n"
        if fTypeKW == "infon" and self.swiftClassHasMethod(self.codeGen.classStore, fTypeKW, "copyAsTypeTo"):
            return indent + RHS + ".copyAsTypeTo(" + LHS + ", true, true);\n"
        if self.isGeneratedSwiftClass(self.codeGen.classStore, lhsTypeSpec):
            return indent + LHS + ".__cdCopyFrom(" + RHS + ");\n"
        return indent + LHS + " = " + RHS + ";\n"

    def codeCopyFromField(self, classes, field, genericArgs):
        tSpec = progSpec.getTypeSpec(field)
        if tSpec == None or not isinstance(tSpec, dict):
            return ""
        if tSpec.get("paramList") != None:
            return ""
        fieldName = field.get("fieldName")
        if fieldName == None or fieldName == "flags":
            return ""
        fTypeKW = progSpec.fieldTypeKeyword(tSpec)
        if fTypeKW in ["flag", "mode"]:
            return ""
        owner = progSpec.getOwner(tSpec)
        if owner in ["we", "const"]:
            return ""
        emitName = self.swiftIdentifier(fieldName)
        src = "other!." + emitName
        if owner == "me":
            if self.isSwiftCopyFromContainer(tSpec):
                return "        " + emitName + ".copyFrom(" + src + ")\n"
            if self.swiftClassHasMethod(classes, fTypeKW, "__opAssign"):
                return "        " + emitName + ".__opAssign(" + src + ")\n"
            if self.isGeneratedSwiftClass(classes, tSpec):
                return "        " + emitName + ".__cdCopyFrom(" + src + ")\n"
        return "        " + emitName + " = " + src + "\n"

    def codeCopyFromMethod(self, classes, className, genericArgs):
        if className == "GLOBAL":
            return ""
        classDef = progSpec.findSpecOf(classes[0], className, "struct")
        if classDef == None:
            return ""
        typeArgList = progSpec.getTypeArgList(className)
        if typeArgList != None:
            return ""
        copyLines = ""
        if classDef.get("flagsVarNeeded", False):
            copyLines += "        flags = other!.flags\n"
        for field in progSpec.generateListOfFieldsToImplement(classes, className):
            copyLines += self.codeCopyFromField(classes, field, genericArgs)
        if copyLines == "":
            return ""
        return (
            "\n"
            + "    func __cdCopyFrom(_ other: " + progSpec.flattenObjectName(className) + "!) -> Void{\n"
            + "        if other == nil { return }\n"
            + copyLines
            + "    }\n"
        )

    def swiftGeneratedValueElementType(self, reqTagList):
        if reqTagList == None or len(reqTagList) == 0:
            return None
        elemSpec = reqTagList[0]
        if progSpec.getOwner(elemSpec) != "me":
            return None
        if not self.isGeneratedSwiftClass(self.codeGen.classStore, elemSpec):
            return None
        elemType = self.swiftGeneratedStorageType(self.codeGen.classStore, elemSpec)
        if elemType == None:
            return None
        return elemType

    def swiftCopiedValueExpr(self, elemType, valueExpr):
        return "({ () -> " + elemType + " in let _cdCopy = " + elemType + "(); _cdCopy.__cdCopyFrom(" + valueExpr + "); return _cdCopy })()"

    def adjustCodeConverterForCall(self, tSpec, name, newName, argList, reqTagList, genericArgs):
        elemType = self.swiftGeneratedValueElementType(reqTagList)
        if elemType == None:
            return None
        if name in ["append", "pushLast"]:
            return "%0.append(" + self.swiftCopiedValueExpr(elemType, "%1") + ")"
        if name in ["prepend", "pushFirst"]:
            return "%0.insert(" + self.swiftCopiedValueExpr(elemType, "%1") + ", at: 0)"
        if name in ["insert", "insertIdx"]:
            return "%0.insert(" + self.swiftCopiedValueExpr(elemType, "%2") + ", at: %1)"
        return None

    def codeStructText(self, classes, attrList, parentClass, classInherits, classImplements, className, structCode, tags):
        classAttrs=''
        originalClassName = className
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
        genericArgs = None
        classDef = progSpec.findSpecOf(classes[0], originalClassName, "struct")
        if classDef != None:
            genericArgs = progSpec.getGenericArgs(classDef)
        structCode += self.codeCopyFromMethod(classes, originalClassName, genericArgs)
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

        func index(from: Int64) -> Index {
            return self.index(startIndex, offsetBy: Int(from))
        }

        private func clampedSubstring(from: Int, to: Int) -> String {
            let start = Swift.max(0, Swift.min(from, self.count))
            let end = Swift.max(start, Swift.min(to, self.count))
            return String(self[index(from: start)..<index(from: end)])
        }

        func substring(from: Int, to:Int) -> String {
            return clampedSubstring(from: from, to: to)
        }

        func substring(from: Int64, to:Int) -> String {
            return clampedSubstring(from: Int(from), to: to)
        }

        func substring(from: Int, to:Int64) -> String {
            return clampedSubstring(from: from, to: Int(to))
        }

        func substring(from: Int64, to:Int64) -> String {
            return clampedSubstring(from: Int(from), to: Int(to))
        }

        mutating func insert(_ offset: Int, _ text: String) {
            self.insert(contentsOf: text, at: index(from: offset))
        }

        mutating func erase(_ offset: Int, _ count: Int) {
            let start = index(from: offset)
            let end = index(from: Swift.min(offset + count, self.count))
            removeSubrange(start..<end)
        }

        func find(_ needle: String) -> Int {
            guard let range = self.range(of: needle) else {
                return -1
            }
            return self.distance(from: self.startIndex, to: range.lowerBound)
        }

        private func asciiCharacter(at value: Int) -> Character? {
            if value < 0 || value >= self.utf8.count {
                return nil
            }
            let idx = self.utf8.index(self.utf8.startIndex, offsetBy: value)
            let byte = self.utf8[idx]
            if byte < 128 {
                return Character(UnicodeScalar(byte))
            }
            return nil
        }

        subscript(index value: Int) -> Element {
            get {
                if let ch = asciiCharacter(at: value) {
                    return ch
                }
                let i = index(startIndex, offsetBy: value)
                return self[i]
            } set {
                var array = Array(self)
                array[value] = newValue
                self = String(array)
            }
        }

        subscript(index value: Int64) -> Element {
            get {
                if let ch = asciiCharacter(at: Int(value)) {
                    return ch
                }
                let i = index(startIndex, offsetBy: Int(value))
                return self[i]
            } set {
                var array = Array(self)
                array[Int(value)] = newValue
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

    func asClass<T>(_ type: T.Type, _ value: AnyObject?) -> T! {
        return value as? T
    }

    func + (lhs: Int64, rhs: Int) -> Int64 { return lhs &+ Int64(rhs) }
    func + (lhs: Int, rhs: Int64) -> Int64 { return Int64(lhs) &+ rhs }
    func - (lhs: Int64, rhs: Int) -> Int64 { return lhs &- Int64(rhs) }
    func - (lhs: Int, rhs: Int64) -> Int64 { return Int64(lhs) &- rhs }
    func += (lhs: inout Int64, rhs: Int) { lhs &+= Int64(rhs) }
    func -= (lhs: inout Int64, rhs: Int) { lhs &-= Int64(rhs) }
    func < (lhs: Int64, rhs: Int) -> Bool { return lhs < Int64(rhs) }
    func < (lhs: Int, rhs: Int64) -> Bool { return Int64(lhs) < rhs }
    func <= (lhs: Int64, rhs: Int) -> Bool { return lhs <= Int64(rhs) }
    func <= (lhs: Int, rhs: Int64) -> Bool { return Int64(lhs) <= rhs }
    func > (lhs: Int64, rhs: Int) -> Bool { return lhs > Int64(rhs) }
    func > (lhs: Int, rhs: Int64) -> Bool { return Int64(lhs) > rhs }
    func >= (lhs: Int64, rhs: Int) -> Bool { return lhs >= Int64(rhs) }
    func >= (lhs: Int, rhs: Int64) -> Bool { return Int64(lhs) >= rhs }
    func == (lhs: Bool, rhs: Int) -> Bool { return lhs == (rhs != 0) }
    func == (lhs: Int, rhs: Bool) -> Bool { return (lhs != 0) == rhs }
    func != (lhs: Bool, rhs: Int) -> Bool { return lhs != (rhs != 0) }
    func != (lhs: Int, rhs: Bool) -> Bool { return (lhs != 0) != rhs }
    func == (lhs: Character, rhs: String) -> Bool { return String(lhs) == rhs }
    func == (lhs: String, rhs: Character) -> Bool { return lhs == String(rhs) }
    func != (lhs: Character, rhs: String) -> Bool { return String(lhs) != rhs }
    func != (lhs: String, rhs: Character) -> Bool { return lhs != String(rhs) }
    func == (lhs: Int, rhs: String) -> Bool { return String(UnicodeScalar(lhs) ?? UnicodeScalar(0)!) == rhs }
    func == (lhs: String, rhs: Int) -> Bool { return lhs == String(UnicodeScalar(rhs) ?? UnicodeScalar(0)!) }
    func != (lhs: Int, rhs: String) -> Bool { return String(UnicodeScalar(lhs) ?? UnicodeScalar(0)!) != rhs }
    func != (lhs: String, rhs: Int) -> Bool { return lhs != String(UnicodeScalar(rhs) ?? UnicodeScalar(0)!) }

    func CodeDogStringifyFlexNumValue(_ val: Double) -> String {
        if val.isFinite {
            let rounded = val.rounded()
            if rounded == val && rounded >= Double(Int64.min) && rounded <= Double(Int64.max) {
                return String(Int64(rounded))
            }
        }
        return String(val)
    }

    func printf(_ text: String) { print(text, separator:"", terminator:"") }
    func input(_ data: inout String) { data = readLine() ?? "" }
    func convertToFloatVal(_ value: Int) -> Float { return Float(value) }
    func convertToFloatVal(_ value: Int64) -> Float { return Float(value) }
    func convertToFloatVal(_ value: UInt64) -> Float { return Float(value) }
    func convertToFloatVal(_ value: Double) -> Float { return Float(value) }

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
        outputText = outputText.replace("-true", "-1")
        outputText = outputText.replace("-false", "-0")
        outputText = outputText.replace("-(1 != 0)", "-1")
        outputText = outputText.replace("-(0 != 0)", "-0")
        outputText = re.sub(
            r"^(\s*)([A-Za-z_][A-Za-z0-9_]*(?:!|\.[A-Za-z_][A-Za-z0-9_]*)*)\.trimmingCharacters\(in: \.whitespacesAndNewlines\);",
            r"\1\2 = \2.trimmingCharacters(in: .whitespacesAndNewlines);",
            outputText,
            flags=re.MULTILINE,
        )
        def replPointerSymbolMethods(match):
            className = match.group(1)
            return (
                "    func mySymbol() -> String{\n"
                "        let objID = UInt(bitPattern: ObjectIdentifier(self))\n"
                "        " + className + ".chkMySymbol.lock()\n"
                "        defer { " + className + ".chkMySymbol.unlock() }\n"
                "        if let symbolID = " + className + ".ptrToUint[objID] {\n"
                "            return(" + className + ".classTag + symbolID.decimalString())\n"
                "        }\n"
                "        " + className + ".symbolCount += 1\n"
                "        let symbolID = " + className + ".symbolCount\n"
                "        " + className + ".ptrToUint[objID] = symbolID\n"
                "        return(" + className + ".classTag + symbolID.decimalString())\n"
                "    }\n\n"
                "    func clearSymbol(_ obj: " + className + "!) -> Void{\n"
                "        if obj == nil { return }\n"
                "        let objID = UInt(bitPattern: ObjectIdentifier(obj))\n"
                "        " + className + ".chkMySymbol.lock()\n"
                "        defer { " + className + ".chkMySymbol.unlock() }\n"
                "        _ = " + className + ".ptrToUint.removeValue(forKey: objID)\n"
                "    }"
            )
        outputText = re.sub(
            r"    func mySymbol\(\) -> String\{\n.*?\n    \}\n\n    func clearSymbol\(_ obj: ([A-Za-z_][A-Za-z0-9_]*)!\) -> Void\{\n.*?\n    \}",
            replPointerSymbolMethods,
            outputText,
            flags=re.DOTALL,
        )
        outputText = outputText.replace("self!", "self")
        outputText = outputText.replace("val = num;", "val = Double(num);")
        outputText = outputText.replace("var idx64: Int64 = idx;", "var idx64: Int64 = Int64(idx);")
        outputText = outputText.replace("subscribers[0]!", "subscribers[0]")
        outputText = outputText.replace("return(String(val));", "return(CodeDogStringifyFlexNumValue(val));")
        outputText = outputText.replace("skipDots - 1", "skipDots &- 1")
        outputText = outputText.replace("""var ch: Int = 0;
            var bytesUsed: Int64 = scrapeUTF8Char(pos, ch);
            if (charsUsed == 0 && bytesUsed <= 0) {
                return(-1);
            }""", """var ch: Int = Int(txtItr!.ch().asciiValue);
            var bytesUsed: Int64 = 1;""")
        outputText = outputText.replace("""var ch: Int = 0;
        var bytesUsed: Int64 = scrapeUTF8Char(pos, ch);
        if (bytesUsed <= 0) {
            return(-1);
        }""", """var ch: Int = Int(at(pos).asciiValue);
        var bytesUsed: Int64 = 1;""")
        outputText = outputText.replace("""var ch: Int = 0;
        cPos += text!.scrapeUTF8Char(cPos, ch);
        if (cPos == pos) {
            return(-1);
        }""", """var ch: Int = Int(text!.at(cPos).asciiValue);
        cPos += 1;""")
        outputText = outputText.replace("var len: Int64 = text!.scrapeUTF8Char(cPos, ch);", "var len: Int64 = 1;\n                ch = Int(text!.at(cPos).asciiValue);")
        outputText = outputText.replace("Styler.DarkGray", "styler!.DarkGray")
        outputText = outputText.replace("Styler.White", "styler!.White")
        outputText = outputText.replace("Styler.", "styler!.")
        outputText = outputText.replace("boardInfons[crntBoardIdx]", "boardInfons[Int(crntBoardIdx)]")
        outputText = outputText.replace("boardInfons[slipView!.crntBoardIdx]", "boardInfons[Int(slipView!.crntBoardIdx)]")
        outputText = outputText.replace("var retVal: Int = info!.pItem!.fetchInt();", "var retVal: Int = Int(info!.pItem!.fetchInt());")
        outputText = outputText.replace("posX = xPov!.pItem!.fetchDouble();", "posX = Int(xPov!.pItem!.fetchDouble());")
        outputText = outputText.replace("posY = yPov!.pItem!.fetchDouble();", "posY = Int(yPov!.pItem!.fetchDouble());")
        outputText = outputText.replace("var colonPos: Int = buffer.find(\":\");", "var colonPos: Int = buffer.firstIndex(of: \":\").map { buffer.distance(from: buffer.startIndex, to: $0) } ?? -1;")
        outputText = outputText.replace("var charPos: UInt64 = Int64(buffer.substring(from:0, to:Int(0)+Int(colonPos)))!;", "var charPos: UInt64 = UInt64(buffer.substring(from:0, to:Int(0)+Int(colonPos))) ?? 0;")
        outputText = outputText.replace("var angle: Float = iterNum * 2 * pi / tessellation;", "var angle: Float = Float(iterNum) * 2.0 * Float(pi) / Float(tessellation);")
        outputText = outputText.replace("var hArg: Double = Double(arg / 2);", "var hArg: Float = Float(arg / 2);")
        outputText = outputText.replace("var nArg: Double = -hArg;", "var nArg: Float = -hArg;")
        outputText = outputText.replace("switch(parseStatus){", "switch(Int(parseStatus)){")
        outputText = outputText.replace("isActive = false;", "isActive = 0;")
        outputText = outputText.replace("var cmd: Int = event!.keyval;", "var cmd: Int = Int(event!.keyval);")
        outputText = outputText.replace("insertChar(event!.keyval);", "insertChar(Int(event!.keyval));")
        outputText = outputText.replace("crntLineNum += numLines;", "crntLineNum += Int(numLines);")
        outputText = outputText.replace("innerPR!.`__INIT_ParamRec`(dataItems!.back(), xCur, yCur, width - 10, lineHeight);", "innerPR!.`__INIT_ParamRec`(dataItems!.back(), xCur, yCur, width - 10, Int(lineHeight));")
        outputText = outputText.replace("\" culled:\" + reactGuiDiagPathShapeCulled + reactGuiDiagDirectCulled.decimalString()", "\" culled:\" + (reactGuiDiagPathShapeCulled + reactGuiDiagDirectCulled).decimalString()")
        outputText = outputText.replace('        S += String("\\t" + m00.decimalString() + "\\t" + m01.decimalString() + "\\t" + m02.decimalString() + "\\t" + m03.decimalString() + "\\n");', '        S += "\\t" + [m00.decimalString(), m01.decimalString(), m02.decimalString(), m03.decimalString()].joined(separator: "\\t") + "\\n";')
        outputText = outputText.replace('        S += String("\\t" + m10.decimalString() + "\\t" + m11.decimalString() + "\\t" + m12.decimalString() + "\\t" + m13.decimalString() + "\\n");', '        S += "\\t" + [m10.decimalString(), m11.decimalString(), m12.decimalString(), m13.decimalString()].joined(separator: "\\t") + "\\n";')
        outputText = outputText.replace('        S += String("\\t" + m20.decimalString() + "\\t" + m21.decimalString() + "\\t" + m22.decimalString() + "\\t" + m23.decimalString() + "\\n");', '        S += "\\t" + [m20.decimalString(), m21.decimalString(), m22.decimalString(), m23.decimalString()].joined(separator: "\\t") + "\\n";')
        outputText = outputText.replace('        S += String("\\t" + m30.decimalString() + "\\t" + m31.decimalString() + "\\t" + m32.decimalString() + "\\t" + m33.decimalString() + "\\n");', '        S += "\\t" + [m30.decimalString(), m31.decimalString(), m32.decimalString(), m33.decimalString()].joined(separator: "\\t") + "\\n";')
        outputText = outputText.replace("roundedRectangle(cr, x, y, w, h, arg1);", "roundedRectangle(cr, Double(x), Double(y), Double(w), Double(h), Double(arg1));")
        outputText = outputText.replace("roundedTopRect(cr, x, y, w, h, arg1);", "roundedTopRect(cr, Double(x), Double(y), Double(w), Double(h), Double(arg1));")
        outputText = outputText.replace("roundedBotmRect(cr, x, y, w, h, arg1);", "roundedBotmRect(cr, Double(x), Double(y), Double(w), Double(h), Double(arg1));")
        outputText = outputText.replace("renderTextCentered(cr, text, font, x, y);", "renderTextCentered(cr, text, font, Double(x), Double(y));")
        outputText = outputText.replace("displayImage(cr, text, x, y, arg1);", "displayImage(cr, text, Double(x), Double(y), Double(arg1));")
        outputText = outputText.replace("CodeDogSetContextColor(cr, x, y, w, h);", "CodeDogSetContextColor(cr, Double(x), Double(y), Double(w), Double(h));")
        outputText = outputText.replace("Drawel(C.red, C.green, C.blue, C.alpha)", "Drawel(Int(C.red), Int(C.green), Int(C.blue), Int(C.alpha))")
        outputText = outputText.replace("var timeIdx: Int = proactiveGUI.presenter.modelMgr!.getInt64(timeIdxID, 0);", "var timeIdx: Int = Int(proactiveGUI.presenter.modelMgr!.getInt64(timeIdxID, 0));")
        outputText = outputText.replace("prevTimeEvent!.setGUI_Store_Int1(timeIdxID, max(FlexNum(Int64(0)), FlexNum(Int64(timeIdx - 1))));", "prevTimeEvent!.setGUI_Store_Int1(timeIdxID, Int64(Swift.max(0, timeIdx - 1)));")
        outputText = outputText.replace("var minIdx: Int = max(FlexNum(Int64(0)), FlexNum(Int64(PR!.sourcePov!.pItem!.value!.items.size() - 1)));", "var minIdx: Int = Swift.max(0, Int(PR!.sourcePov!.pItem!.value!.items.size() - 1));")
        outputText = outputText.replace("var hue: Int = huePov!.pItem!.fetchInt();", "var hue: Int = Int(huePov!.pItem!.fetchInt());")
        outputText = outputText.replace("xOri += Double(Double(frameNumber * 0.03));", "xOri += Double(frameNumber) * 0.03;")
        outputText = outputText.replace("yOri += Double(Double(frameNumber * 0.06));", "yOri += Double(frameNumber) * 0.06;")
        outputText = outputText.replace("zOri += Double(Double(frameNumber * 0.00));", "zOri += Double(frameNumber) * 0.00;")
        outputText = outputText.replace("thing!.rotateX(xOri);", "thing!.rotateX(Float(xOri));")
        outputText = outputText.replace("thing!.rotateY(yOri);", "thing!.rotateY(Float(yOri));")
        outputText = outputText.replace("thing!.rotateZ(zOri);", "thing!.rotateZ(Float(zOri));")
        outputText = outputText.replace("thing!.setLocation(xLoc, yLoc, zLoc);", "thing!.setLocation(Float(xLoc), Float(yLoc), Float(zLoc));")
        outputText = outputText.replace('        S += p1.x.decimalString() + ", " + p1.y.decimalString() + ", " + p1.z.decimalString() + ",      ";', '        S += [p1.x.decimalString(), p1.y.decimalString(), p1.z.decimalString()].joined(separator: ", ") + ",      ";')
        outputText = outputText.replace('        S += p2.x.decimalString() + ", " + p2.y.decimalString() + ", " + p2.z.decimalString() + ",      ";', '        S += [p2.x.decimalString(), p2.y.decimalString(), p2.z.decimalString()].joined(separator: ", ") + ",      ";')
        outputText = outputText.replace('        S += p3.x.decimalString() + ", " + p3.y.decimalString() + ", " + p3.z.decimalString();', '        S += [p3.x.decimalString(), p3.y.decimalString(), p3.z.decimalString()].joined(separator: ", ");')
        outputText = outputText.replace("dragInfonTargetX!.value!.num = newX;", "dragInfonTargetX!.value!.num = FlexNum(Int64(newX));")
        outputText = outputText.replace("dragInfonTargetY!.value!.num = newY;", "dragInfonTargetY!.value!.num = FlexNum(Int64(newY));")
        outputText = outputText.replace("preDragX = numInfonX!.fetchDouble();", "preDragX = Int(numInfonX!.fetchDouble());")
        outputText = outputText.replace("preDragY = numInfonY!.fetchDouble();", "preDragY = Int(numInfonY!.fetchDouble());")
        outputText = outputText.replace("return(`__INIT_ProactiveGUIWidget`(\"ProactiveGUI\"));", "return(`__INIT_DashboardWidget`(\"ProactiveGUI\"));")
        outputText = outputText.replace("cr!.move(to:CGPoint(x:p1.x, y:p1.y));", "cr!.move(to:CGPoint(x:CGFloat(p1.x), y:CGFloat(p1.y)));")
        outputText = outputText.replace("cr!.addLine(to:CGPoint(x:p2.x, y:p2.y));", "cr!.addLine(to:CGPoint(x:CGFloat(p2.x), y:CGFloat(p2.y)));")
        outputText = outputText.replace("cr!.addLine(to:CGPoint(x:p3.x, y:p3.y));", "cr!.addLine(to:CGPoint(x:CGFloat(p3.x), y:CGFloat(p3.y)));")
        outputText = outputText.replace("cr!.addLine(to:CGPoint(x:p1.x, y:p1.y));", "cr!.addLine(to:CGPoint(x:CGFloat(p1.x), y:CGFloat(p1.y)));")
        outputText = outputText.replace("var halfScreenWidth: Float = 0.5 * win3D!.windowWidth3D;", "var halfScreenWidth: Float = 0.5 * Float(win3D!.windowWidth3D);")
        outputText = outputText.replace("var halfScreenHeight: Float = 0.5 * win3D!.windowHeight3D;", "var halfScreenHeight: Float = 0.5 * Float(win3D!.windowHeight3D);")
        outputText = outputText.replace("var vOffsetView: Vec3D = Vec3D(win3D!.windowXPos, win3D!.windowYPos, 0);", "var vOffsetView: Vec3D = Vec3D(Float(win3D!.windowXPos), Float(win3D!.windowYPos), 0.0);")
        outputText = outputText.replace("ambRed = light!.color.red / 255.0;", "ambRed = Float(light!.color.red) / 255.0;")
        outputText = outputText.replace("ambGreen = light!.color.green / 255.0;", "ambGreen = Float(light!.color.green) / 255.0;")
        outputText = outputText.replace("ambBlue = light!.color.blue / 255.0;", "ambBlue = Float(light!.color.blue) / 255.0;")
        outputText = outputText.replace("nRed += intensity * (light!.color.red / 255.0);", "nRed += intensity * (Float(light!.color.red) / 255.0);")
        outputText = outputText.replace("nGreen += intensity * (light!.color.green / 255.0);", "nGreen += intensity * (Float(light!.color.green) / 255.0);")
        outputText = outputText.replace("nBlue += intensity * (light!.color.blue / 255.0);", "nBlue += intensity * (Float(light!.color.blue) / 255.0);")
        outputText = outputText.replace("faceColor.red = faceColor.red * nRed;", "faceColor.red = UInt(Float(faceColor.red) * nRed);")
        outputText = outputText.replace("faceColor.green = faceColor.green * nGreen;", "faceColor.green = UInt(Float(faceColor.green) * nGreen);")
        outputText = outputText.replace("faceColor.blue = faceColor.blue * nBlue;", "faceColor.blue = UInt(Float(faceColor.blue) * nBlue);")
        outputText = outputText.replace("var bytesUsed: UInt64 = fileStream.read(qStream!.buff);", "var bytesUsed: UInt64 = 0;")
        outputText = outputText.replace("input(data);", "input(&data);")
        outputText = outputText.replace("start(name);", "start();")
        outputText = outputText.replace("normerThread.start(name + \"_NRM\");", "normerThread.start();")
        outputText = outputText.replace('S += String("  <outerPOV:" + ((outerPOV == nil) ? "NULL" : outerPOV!.mySymbol()) + " " + ((outerPOV == nil) ? "NULL" : outerPOV!.stringify()) + ">");', 'let outerSymbol = ((outerPOV == nil) ? "NULL" : outerPOV!.mySymbol());\n                let outerString = ((outerPOV == nil) ? "NULL" : outerPOV!.stringify());\n                S += "  <outerPOV:" + outerSymbol + " " + outerString + ">";')
        outputText = outputText.replace('        print("BASE::allocNewStream!\\n",separator:"", terminator:"");\n        return(0);', '        print("BASE::allocNewStream!\\n",separator:"", terminator:"");\n        return(nil);')
        outputText = outputText.replace("""        var bytesUsed: UInt64 = 0;
        if (!(readNotDone)) {
            readNotDone = true;
            readBuffer = "";
        }
        bytesUsed = dataIn.find("\\n");
        if (bytesUsed < 0) {
            readBuffer += dataIn;
            bytesUsed = UInt64(dataIn.count);
        }
        else {
            readNotDone = false;
            readBuffer += String(dataIn.substring(from:0, to:Int(0)+Int(bytesUsed)));
            bytesUsed += 1;
        }
        return(bytesUsed);""", """        var bytesUsed: UInt64 = 0;
        if (!(readNotDone)) {
            readNotDone = true;
            readBuffer = "";
        }
        let linePos = dataIn.find("\\n");
        if (linePos < 0) {
            readBuffer += dataIn;
            bytesUsed = UInt64(dataIn.count);
        }
        else {
            readNotDone = false;
            readBuffer += String(dataIn.substring(from:0, to:Int(0)+Int(linePos)));
            bytesUsed = UInt64(linePos + 1);
        }
        return(bytesUsed);""")
        outputText = re.sub(r"asClass\(([A-Za-z_][A-Za-z0-9_]*),", r"asClass(\1.self,", outputText)
        return outputText

    def replacementVerbatimFunctionBody(self, className, fieldName, field, verbatimText, indent):
        if fieldName == "appendFrameDiagnosticsLogRow":
            return """{
        let path = "SlipstreamFrameDiagnostics.csv"
        let header = "sample_ms,draw_fps,draw_total_ms,build_ms,render_ms,draw_count,cmd_visited,cmd_rendered,cmd_path_culled,cmd_direct_culled,cmd_paint_skipped,cmd_text,cmd_image,cmd_bg,cmd_subdraw,cmd_3d,anim_fps,anim_dt_ms,anim_tween_ms,anim_requests,anim_full_requests,anim_rect_requests,anim_scheduled,anim_coalesced,anim_callbacks,anim_full_redraws,anim_rect_redraws,anim_pending,anim_has_rect,anim_rect_x,anim_rect_y,anim_rect_w,anim_rect_h,window_w,window_h,board_index\\n"
        if !FileManager.default.fileExists(atPath: path) {
            try? header.write(toFile: path, atomically: true, encoding: .utf8)
        }
        if let handle = FileHandle(forWritingAtPath: path) {
            handle.seekToEndOfFile()
            if let data = (row + "\\n").data(using: .utf8) {
                handle.write(data)
            }
            if #available(macOS 10.15.4, *) {
                try? handle.close()
            } else {
                handle.closeFile()
            }
        }
    }

"""
        if fieldName == "diagnosticsScalarToString":
            return """{
        return String(Double(value))
    }

"""
        if fieldName in ["slipstream_shutdown_CB", "connectSlipstreamShutdownCB"]:
            return """{
    }

"""
        return None

    def parentHasStoredField(self, classes, className, fieldName):
        return self.parentStoredField(classes, className, fieldName) != None

    def parentStoredField(self, classes, className, fieldName):
        if progSpec.findSpecOf(classes[0], className, "struct") == None:
            return None
        for parent in progSpec.getParentClassList(classes, className):
            parentName = progSpec.filterClassesToString(parent)
            parentStruct = progSpec.findSpecOf(classes[0], parentName, "struct")
            parentModel = progSpec.findSpecOf(classes[0], parentName, "model")
            for spec in [parentModel, parentStruct]:
                if spec == None:
                    continue
                for field in spec["fields"]:
                    if field.get("fieldName") == fieldName and progSpec.getParamList(field) == None:
                        return field
            inheritedField = self.parentStoredField(classes, parentName, fieldName)
            if inheritedField != None:
                return inheritedField
        return None

    def skipFieldDefinition(self, classes, className, field):
        if progSpec.getParamList(field) != None:
            return False
        fieldName = field.get("fieldName")
        if not fieldName:
            return False
        return self.parentHasStoredField(classes, className, fieldName)

    def extraConstructorBody(self, classes, className, genericArgs):
        if progSpec.findSpecOf(classes[0], className, "struct") == None:
            return ""
        initLines = ""
        for field in progSpec.generateListOfFieldsToImplement(classes, className):
            if progSpec.getParamList(field) != None:
                continue
            fieldName = field.get("fieldName")
            if not fieldName:
                continue
            tSpec = progSpec.getTypeSpec(field)
            if progSpec.getOwner(tSpec) != "me":
                continue
            parentField = self.parentStoredField(classes, className, fieldName)
            if parentField == None:
                continue
            parentTSpec = progSpec.getTypeSpec(parentField)
            if not progSpec.typeIsPointer(parentTSpec):
                continue
            cvrtType = self.codeGen.convertType(tSpec, 'alloc', genericArgs)
            emitName = self.swiftIdentifier(fieldName)
            initLines += "        if " + emitName + " == nil { " + emitName + " = " + cvrtType + "() }\n"
        return initLines

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

    def defaultFieldValueForType(self, classes, tSpec, fType):
        unwrappedType = progSpec.getUnwrappedClassFieldTypeKeyWord(classes, fType)
        swiftType = self.adjustBaseTypes(unwrappedType, False)
        if self.isNumericType(swiftType):
            return "0"
        if swiftType == "Bool":
            return "false"
        if swiftType == "String":
            return '""'
        return ""

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
                rhsType = ''
                if progSpec.getOwner(RTSpec) != 'literal':
                    rhsType = self.codeGen.convertType(RTSpec, 'var', genericArgs)
                if cvrtType==rhsType:
                    assignValue = " = " + CPL   # Act like a copy constructor
            if(assignValue==''): assignValue = ' = ' + allocFieldType + CPL
        else: # If no value was given:
            assignValue = self.variableDefaultValueString(allocFieldType, False, owner)
        if assignValue == "":
            if progSpec.ownerIsPointer(owner) and not isAllocated:
                assignValue = " = nil"
            else:
                assignValue = " = " + allocFieldType + '()'
        fieldTypeMod = self.makePtrOpt(LTSpec)
        varDeclareStr= "var " + self.swiftIdentifier(varName) + ": "+ cvrtType + fieldTypeMod + assignValue
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
        emitName = self.swiftIdentifier(fieldName)
        if className=='GLOBAL': defn =  indent  + "let " + emitName + ':'+ convertedType  + fieldValueText +';\n';
        else: defn =  indent  + "let " + emitName + ':'+ convertedType  + fieldValueText +';\n';
        return [defn, decl]

    def codeVarField_Str(self, convertedType, tSpec, fieldName, fieldValueText, className, tags, typeArgList, indent):
        # TODO: make test case
        fieldOwner=progSpec.getOwner(tSpec)
        emitName = self.swiftIdentifier(fieldName)
        if fieldOwner=='we':
            defn = indent + "public static var "+ indent + emitName + ": " +  convertedType  +  fieldValueText + '\n'
            decl = ''
        else:
            isTypeArg = False
            if typeArgList:
                for typeArg in typeArgList:
                    if convertedType == typeArg: isTypeArg = True
            if isTypeArg: defn = indent + "var "+ emitName + fieldValueText + '\n'
            else:
                convertedType += self.makePtrOpt(tSpec)
                varPrefix = "lazy var " if self.isInstanceMemberDefault(fieldValueText) else "var "
                defn = indent + varPrefix + emitName + ": " +  convertedType + fieldValueText + '\n'
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
        S = ''
        if callSuper != "": prefix = 'override '
        if ctorArgs != "":
            S = '    init(' + ctorArgs+'){\n'+callSuper+ctorInit+funcBody+'    }\n'
        S += '    '+prefix+'init(){\n'+callSuper+funcBody+'    }\n'
        return S

    def codeConstructorInit(self, fieldName, count, defaultVal):
        return "        self." + self.swiftIdentifier(fieldName) +" = arg_"+fieldName+";\n"

    def codeConstructorArgType(self, tSpec, argType):
        fTypeKW = progSpec.fieldTypeKeyword(tSpec)
        if progSpec.typeIsPointer(tSpec) and fTypeKW != "string" and not argType.endswith("!") and not argType.endswith("?"):
            return argType + "!"
        return argType

    def codeNullablePointerMethodCall(self, connector, name, argList, retTypeSpec):
        if connector != self.PtrConnector:
            return None
        if argList != []:
            return None
        if name not in ["stringify", "mySymbol"]:
            return None
        if progSpec.fieldTypeKeyword(retTypeSpec) != "string":
            return None
        return "((%0 == nil) ? \"NULL\" : %0!." + name + "())"

    def useFieldAsConstructorArg(self, className, field, defaultVal):
        if className == "Drawel":
            return field.get("fieldName") in ["x", "y", "w", "h", "arg1", "arg2"]
        if className in ["arrow", "GuiCoords"]:
            return True
        return defaultVal != '' and not self.isInstanceMemberDefault("=" + defaultVal)

    def codeConstructorArgText(self, argFieldName, count, argType, defaultVal):
        if defaultVal == "nil" and not argType.endswith("!") and not argType.endswith("?"):
            defaultVal = ""
        if defaultVal and not self.isInstanceMemberDefault("=" + defaultVal):
            if argType == "FlexNum" and progSpec.isStringNumeric(defaultVal):
                defaultVal = "FlexNum(Int64(" + defaultVal + "))"
            argType = argType + ' = ' + defaultVal
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
                structCode +="func " + self.swiftIdentifier(fieldName) +"("+paramListText+") " + cvrtType
        else:
            if fieldName=="init":
                fieldName = "__INIT_"+className
                structCode += indent + "func "  + self.swiftIdentifier(fieldName) +"("+paramListText+")" + cvrtType
            else:
                if isCtor:
                    structCode += indent + "init "  +"("+paramListText+") " + cvrtType
                else:
                    fieldTypeMod = self.makePtrOpt(tSpec)
                    funcAttrs = ''
                    staticKW  = ''
                    if isStatic: staticKW = 'static '
                    if inheritMode=='override': funcAttrs='override '
                    structCode += indent + funcAttrs + staticKW + "func " + self.swiftIdentifier(fieldName) +"("+paramListText+") " + cvrtType + fieldTypeMod
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
                if self.swiftScalarParamUsesPointerOut(paramTypeSpec, param['fieldName']):
                    continue
                if self.swiftParamUsesInout(paramTypeSpec):
                    continue
                paramFieldName = param['fieldName']
                paramRHS = self.swiftIdentifier(paramFieldName)
                topCode     +=  '        var '+self.swiftIdentifier(paramFieldName)+' = '+paramRHS+'\n'
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
            initialize(commandLineArgs())
            """ + runCode + """
            deinitialize()
        }

    """
        progSpec.addClass(classes[0], classes[1], 'GLOBAL', 'struct', 'SEQ',["//^", "Main class"])
        codeDogParser.AddToObjectFromText(classes[0], classes[1], progSpec.wrapFieldListInObjectDef('GLOBAL',  mainFuncCode ), 'Swift start-up code')

    def __init__(self):
        print("INIT")
