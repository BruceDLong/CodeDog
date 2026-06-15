# xlator_Kotlin.py
#
# Kotlin JVM backend.  This intentionally starts close to the Java backend
# because CodeDog's JVM/Android libraries already use that object model.
import progSpec
import codeDogParser
import re
from progSpec import cdErr
from xlator_Java import Xlator_Java


class Xlator_Kotlin(Xlator_Java):
    LanguageName          = "Kotlin"
    BuildStrPrefix        = "kotlinc "
    fileExtension         = ".kt"
    typeForCounterInt     = "Int"
    GlobalVarPrefix       = "GLOBAL.static_Global."
    PtrConnector          = "!!."
    ObjConnector          = "."
    NameSegConnector      = "."
    NameSegFuncConnector  = "."
    modeIdxType           = "Int"
    doesLangHaveGlobals   = False
    funcBodyIndent        = "    "
    funcsDefInClass       = True
    MakeConstructors      = True
    blockPrefix           = ""
    usePrefixOnStatics    = False
    iteratorsUseOperators = False
    renderGenerics        = "True"
    renameInitFuncs       = False
    useAllCtorArgs        = True
    hasMacros             = False
    useNestedClasses      = False
    nullValue             = "null"

    companionMarker       = "__KOTLIN_COMPANION__"
    enumDefaults          = {}
    enumTypes             = set()

    def _cleanType(self, langType):
        if langType.startswith("static "):
            langType = langType[len("static "):]
        if langType.startswith("final "):
            langType = langType[len("final "):]
        return langType

    def _nonNullableType(self, langType):
        langType = self._cleanType(langType)
        if langType.endswith("?"):
            return langType[:-1]
        return langType

    def _isNullableType(self, langType):
        return self._cleanType(langType).endswith("?")

    def _isValueType(self, langType):
        langType = self._nonNullableType(langType)
        return langType in {
            "Int", "Long", "Double", "Float", "Boolean", "Char",
            "Short", "Byte", "UInt", "ULong", "UShort", "UByte",
        }

    def _defaultValueForType(self, langType, owner="me"):
        langType = self._cleanType(langType)
        baseType = self._nonNullableType(langType)
        if self._isNullableType(langType) or progSpec.ownerIsPointer(owner):
            return "null"
        if baseType in ("Int", "Short", "Byte", "UInt", "UShort", "UByte"):
            return "0"
        if baseType in ("Long", "ULong"):
            return "0L"
        if baseType == "Double":
            return "0.0"
        if baseType == "Float":
            return "0.0f"
        if baseType == "Boolean":
            return "false"
        if baseType == "Char":
            return "' '"
        if baseType == "String":
            return '""'
        if baseType in self.enumDefaults:
            return baseType + "." + self.enumDefaults[baseType]
        if len(baseType) == 1 or baseType in ("keyType", "valueType", "nodeType"):
            return "null as " + baseType
        return baseType + "()"

    def _rhsExpr(self, rhs):
        if rhs == "":
            return ""
        rhs = rhs.strip()
        if rhs.startswith("="):
            rhs = rhs[1:].strip()
        return rhs

    def _fieldDecl(self, indent, mutability, name, langType, rhs, owner="me"):
        langType = self._cleanType(langType)
        rhsExpr = self._rhsExpr(rhs)
        if rhsExpr == "":
            rhsExpr = self._defaultValueForType(langType, owner)
        return indent + mutability + " " + name + ": " + langType + " = " + rhsExpr + ";\n"

    ###################################################### CONTAINERS
    def codeArrayIndex(self, idx, containerType, LorR_Val, previousSegName, idxTypeSpec):
        return "[" + idx + "]"

    def emitLoopWithBody(self, header, prologue, body, returnType, mods, genericArgs, indent):
        actionText = indent + header + " {\n"
        if prologue:
            actionText += prologue

        whereExprNode = mods.get("whereExpr") if mods else None
        untilExprNode = mods.get("untilExpr") if mods else None
        if whereExprNode:
            whereExprIn = whereExprNode[0] if not isinstance(whereExprNode, str) else whereExprNode
            [whereExpr, _whereType] = self.codeGen.codeExpr(whereExprIn, None, None, "RVAL", genericArgs)
            actionText += indent + "    if (!(" + whereExpr + ")) continue;\n"
        if untilExprNode:
            untilExprIn = untilExprNode[0] if not isinstance(untilExprNode, str) else untilExprNode
            [untilExpr, _untilType] = self.codeGen.codeExpr(untilExprIn, None, None, "RVAL", genericArgs)
            actionText += indent + "    if (" + untilExpr + ") break;\n"

        for repAction in body:
            actionText += self.codeGen.codeAction(repAction, indent + "    ", returnType, genericArgs)
        actionText += indent + "}\n"
        return actionText

    def codeRangeSpec(self, traversalMode, ctrType, repName, S_low, S_hi, inclusive, indent, body, returnType, mods, genericArgs):
        mode = traversalMode or "Forward"
        if mode == "Backward":
            start = S_hi if inclusive else "(" + S_hi + " - 1)"
            header = "for (" + repName + " in " + start + " downTo " + S_low + ")"
        else:
            op = ".." if inclusive else " until "
            if inclusive:
                header = "for (" + repName + " in " + S_low + op + S_hi + ")"
            else:
                header = "for (" + repName + " in " + S_low + op + S_hi + ")"
        return self.emitLoopWithBody(header, "", body, returnType, mods, genericArgs, indent)

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
        containerCat = progSpec.getContaineCategory(self.codeGen.classStore, ctnrTSpec)
        if rangeMode is not None and rangeMode != "keys":
            cdErr("Kotlin traversal range mode '" + str(rangeMode) + "' is not implemented yet.")
        bkind = binding.get("kind")
        axis = binding.get("axis")

        def makeSpec(owner, fieldType):
            return {"owner": owner, "fieldType": fieldType}

        def reqSpec(idx):
            reqTagList = progSpec.getReqTagList(ctnrTSpec)
            if reqTagList and len(reqTagList) > idx:
                return makeSpec(reqTagList[idx]["tArgOwner"], reqTagList[idx]["tArgType"])
            return makeSpec(progSpec.getContainerFirstElementOwner(ctnrTSpec), progSpec.getContainerFirstElementType(ctnrTSpec))

        def mapEntriesAndRangeFilter(entryName):
            entriesExpr = ctnrName + ".entries"
            rangeFilter = ""
            if rangeMode == "keys":
                if not rangeSpec:
                    cdErr("Kotlin keys traversal requires a range.")
                startPR = rangeSpec.get("rangeStart", None)
                endPR = rangeSpec.get("rangeEnd", None)
                if startPR is None or endPR is None:
                    cdErr("Kotlin keys traversal requires start and end keys.")
                [startExpr, _startTSpec] = self.codeGen.codeExpr(startPR[0], None, None, "RVAL", genericArgs)
                [endExpr, _endTSpec] = self.codeGen.codeExpr(endPR[0], None, None, "RVAL", genericArgs)
                upperOp = ">" if bool(getattr(rangeSpec, "inclusiveOp", False)) else ">="
                entriesExpr += ".sortedBy { it.key }"
                rangeFilter = indent + "    if (" + entryName + ".key < " + startExpr + " || " + entryName + ".key " + upperOp + " " + endExpr + ") continue;\n"
            return [entriesExpr, rangeFilter]

        if bkind == "tuple":
            keyName = binding.get("keyName")
            valName = binding.get("valName")
            if not keyName or not valName:
                cdErr("Kotlin tuple traversal missing key/value binding names.")
            if containerCat not in ("Map", "Multimap"):
                cdErr("Kotlin tuple traversal requires a map-like container.")
            keyTSpec = reqSpec(0)
            valTSpec = reqSpec(1)
            localVarsAlloc.append([keyName, keyTSpec])
            localVarsAlloc.append([valName, valTSpec])
            keyType = self.codeGen.convertType(keyTSpec, "var", genericArgs)
            valType = self.codeGen.convertType(valTSpec, "var", genericArgs)
            entryName = keyName + "_" + valName + "_entry"
            [entriesExpr, rangeFilter] = mapEntriesAndRangeFilter(entryName)
            header = "for (" + entryName + " in " + entriesExpr + ")"
            prologue = (
                rangeFilter
                + indent + "    var " + keyName + ": " + keyType + " = " + entryName + ".key;\n"
                + indent + "    var " + valName + ": " + valType + " = " + entryName + ".value;\n"
            )
            return self.emitLoopWithBody(header, prologue, body, returnType, mods, genericArgs, indent)

        if bkind != "single":
            cdErr("Kotlin traversal binding kind missing or unknown.")
        repName = binding.get("name")
        if not repName:
            cdErr("Kotlin traversal missing loop variable name.")
        if axis is None:
            axis = "value"

        if containerCat in ("Map", "Multimap"):
            keyTSpec = reqSpec(0)
            valTSpec = reqSpec(1)
            entryName = repName + "_entry"
            [entriesExpr, rangeFilter] = mapEntriesAndRangeFilter(entryName)
            header = "for (" + entryName + " in " + entriesExpr + ")"
            if axis == "key":
                localVarsAlloc.append([repName, keyTSpec])
                keyType = self.codeGen.convertType(keyTSpec, "var", genericArgs)
                prologue = rangeFilter + indent + "    var " + repName + ": " + keyType + " = " + entryName + ".key;\n"
            elif axis == "value":
                localVarsAlloc.append([repName, valTSpec])
                localVarsAlloc.append([repName + "_key", keyTSpec])
                keyType = self.codeGen.convertType(keyTSpec, "var", genericArgs)
                valType = self.codeGen.convertType(valTSpec, "var", genericArgs)
                prologue = (
                    rangeFilter
                    + indent + "    var " + repName + ": " + valType + " = " + entryName + ".value;\n"
                    + indent + "    var " + repName + "_key: " + keyType + " = " + entryName + ".key;\n"
                )
            else:
                cdErr("Kotlin map traversal does not support axis '" + str(axis) + "'.")
            return self.emitLoopWithBody(header, prologue, body, returnType, mods, genericArgs, indent)

        firstOwner = progSpec.getContainerFirstElementOwner(ctnrTSpec)
        firstType = progSpec.getContainerFirstElementType(ctnrTSpec)
        repTSpec = {"owner": firstOwner, "fieldType": firstType}
        if containerCat == "string":
            repTSpec = {"owner": "me", "fieldType": "char"}
            localVarsAlloc.append([repName, repTSpec])
            loopCntrName = repName + "_key"
            localVarsAlloc.append([loopCntrName, {"owner": "me", "fieldType": "Int"}])
            header = "for (" + loopCntrName + " in 0 until " + ctnrName + ".length)"
            prologue = indent + "    var " + repName + ": Char = " + ctnrName + "[" + loopCntrName + "];\n"
            return self.emitLoopWithBody(header, prologue, body, returnType, mods, genericArgs, indent)
        localVarsAlloc.append([repName, repTSpec])
        loopCntrName = repName + "_key"
        localVarsAlloc.append([loopCntrName, {"owner": "me", "fieldType": "Int"}])
        elemType = self.codeGen.convertType(repTSpec, "var", genericArgs)
        if containerCat == "List":
            if traversalMode == "Backward":
                header = "for (" + loopCntrName + " in (" + ctnrName + ".size - 1) downTo 0)"
            else:
                header = "for (" + loopCntrName + " in 0 until " + ctnrName + ".size)"
            prologue = indent + "    var " + repName + ": " + elemType + " = " + ctnrName + "[" + loopCntrName + "];\n"
            return self.emitLoopWithBody(header, prologue, body, returnType, mods, genericArgs, indent)

        cdErr("Kotlin traversal for container category '" + str(containerCat) + "' is not implemented yet.")

    ###################################################### TYPES / OWNERS
    def adjustBaseTypes(self, fType, isContainer):
        if fType == "":
            return ""
        if not isinstance(fType, str):
            fType = fType[0]
        if fType in self.enumTypes:
            return "Int"
        if fType in ("int8", "int16", "int32", "int", "uint8", "uint16", "uint32", "uint", "numeric"):
            return "Int"
        if fType in ("int64", "uint64", "long", "timeValue"):
            return "Long"
        if fType == "float":
            return "Float"
        if fType == "double":
            return "Double"
        if fType in ("bool", "boolean"):
            return "Boolean"
        if fType == "void" or fType == "none":
            return "Unit"
        if fType == "string" or fType == "String":
            return "String"
        if fType == "char":
            return "Char"
        return progSpec.flattenObjectName(fType)

    def applyOwner(self, owner, langType, varMode):
        langType = self._cleanType(langType)
        if owner in ("me", "const", "we"):
            return langType
        if owner == "itr":
            return langType
        if owner in ("my", "our", "their", "id_their", "id_our"):
            if not langType.endswith("?"):
                return langType + "?"
            return langType
        cdErr("ERROR: Owner of type not valid '" + owner + "'")

    def makePtrOpt(self, tSpec):
        if isinstance(tSpec, dict) and progSpec.typeIsPointer(tSpec):
            return "!!"
        return ""

    def codeXlatorAllocater(self, tSpec, genericArgs):
        owner = progSpec.getOwner(tSpec)
        if owner == "const":
            cdErr("ERROR: Cannot allocate a 'const' variable.")
        reqTagList = progSpec.getReqTagList(tSpec)
        fTypeKW = progSpec.fieldTypeKeyword(tSpec)
        fTypeKW = self.codeGen.generateGenericStructName(fTypeKW, reqTagList, genericArgs)
        return progSpec.flattenObjectName(fTypeKW)

    def getConstIntFieldStr(self, fieldName, fieldValue, intSize):
        kotlinType = "Int" if intSize == 32 else "Long"
        if intSize != 32 and not fieldValue.endswith("L"):
            fieldValue += "L"
        return self.companionMarker + "    const val " + fieldName + ": " + kotlinType + " = " + fieldValue + ";\n"

    def getEnumStr(self, fieldName, enumList):
        S = ""
        count = 0
        for enumName in enumList:
            S += "    " + self.getConstIntFieldStr(enumName, str(count), 32)
            count += 1
        S += "\n"
        return S

    def getEnumStructStr(self, fieldName, enumList):
        if enumList:
            self.enumDefaults[fieldName] = enumList[0]
        self.enumTypes.add(fieldName)
        S = "object " + fieldName + "{\n"
        count = 0
        for enumName in enumList:
            S += "    const val " + enumName + ": Int = " + str(count) + ";\n"
            count += 1
        S += "}\n"
        return S

    def getEnumStringifyFunc(self, className, enumList):
        return "var " + className + "Strings: ArrayList<String> = arrayListOf(\"" + "\", \"".join(enumList) + "\");\n"

    ###################################################### EXPRESSIONS
    def recodeStringFunctions(self, name, tSpec, lenArgs):
        if name == "size":
            tSpec["fieldType"] = "int"
            tSpec["codeConverter"] = "%0.length"
        elif name == "subStr":
            if lenArgs == 1:
                tSpec["codeConverter"] = "%0.substring(%1, %0.length)"
            else:
                tSpec["codeConverter"] = "%0.substring(%1, %1 + %2)"
        elif name == "append":
            tSpec["codeConverter"] = "%0 += %1"
        return [name, tSpec]

    def convertToInt(self, S, tSpec):
        fTypeKW = progSpec.fieldTypeKeyword(tSpec)
        if fTypeKW in ("numeric", "int", "Int"):
            return S
        if fTypeKW == "char" or fTypeKW == "Char":
            return "Character.getNumericValue(" + S + ")"
        return S

    def checkForTypeCastNeed(self, lhsTSpec, rhsTSpec, RHS):
        LTypeKW = progSpec.fieldTypeKeyword(lhsTSpec)
        RTypeKW = progSpec.fieldTypeKeyword(rhsTSpec)
        if LTypeKW in ("bool", "Boolean", "boolean"):
            if progSpec.typeIsPointer(rhsTSpec):
                return "(" + RHS + " != null)"
            if RTypeKW in ("int", "Int", "numeric", "flag"):
                if RHS and RHS[0] == "!":
                    return "(" + RHS[1:] + " == 0)"
                return "(" + RHS + " != 0)"
            if RHS == "0":
                return "false"
            if RHS == "1":
                return "true"
        if isinstance(lhsTSpec, dict) and isinstance(rhsTSpec, dict):
            if not progSpec.typeIsPointer(lhsTSpec) and progSpec.typeIsPointer(rhsTSpec):
                RHS = "(" + RHS + "!!)"
        if LTypeKW in ("char", "Char") and RTypeKW in ("numeric", "int", "Int"):
            return "(" + RHS + ").toChar()"
        if LTypeKW in ("string", "String") and RTypeKW in ("char", "Char"):
            return "(" + RHS + ").toString()"
        if LTypeKW in ("int", "Int", "numeric") and RTypeKW in ("long", "Long", "int64", "uint64"):
            return "(" + RHS + ").toInt()"
        if LTypeKW in ("long", "Long", "int64") and RTypeKW in ("numeric", "int", "Int"):
            return "(" + RHS + ").toLong()"
        return RHS

    def codePlusOperator(self, S, S2, retType1, retType2, opIn):
        op = " + " if opIn == "+" else " - "
        if opIn == "+":
            fType1 = progSpec.fieldTypeKeyword(retType1)
            fType2 = progSpec.fieldTypeKeyword(retType2)
            if fType2 in ("string", "String") and fType1 not in ("string", "String"):
                S = "(" + S + ").toString()"
        return S + op + S2

    def codeBitwiseOp(self, S, S2, opIn):
        opMap = {"&": "and", "^": "xor", "|": "or"}
        return "(" + S + " " + opMap[opIn] + " " + S2 + ")"

    def codeNotOperator(self, S, S2, retTypeSpec):
        if progSpec.typeIsPointer(retTypeSpec):
            return ["(" + S2 + " == null)", {"owner": "me", "fieldType": "bool"}]
        return [S + "!" + S2, retTypeSpec]

    def codeIdentityCheck(self, S, S2, retType1, retType2, opIn):
        if opIn == "===":
            opIn = "==="
        elif opIn == "!==":
            opIn = "!=="
        elif opIn == "==":
            opIn = "=="
        elif opIn == "!=":
            opIn = "!="
        else:
            cdErr("ERROR: '==' or '!=' or '===' or '!==' expected.")
        S2 = self._coerceComparisonOperand(S2, retType1, retType2)
        return S + " " + opIn + " " + self.adjustQuotesForChar(retType1, retType2, S2)

    def _coerceComparisonOperand(self, S2, retType1, retType2):
        fType1 = progSpec.fieldTypeKeyword(retType1)
        fType2 = progSpec.fieldTypeKeyword(retType2)
        if fType1 in ("double", "Double") and fType2 in ("numeric", "int", "Int", "uint", "long", "Long", "int64", "uint64"):
            return "(" + S2 + ").toDouble()"
        if fType1 in ("float", "Float") and fType2 in ("numeric", "int", "Int", "uint", "long", "Long", "int64", "uint64"):
            return "(" + S2 + ").toFloat()"
        if fType1 in ("long", "Long", "int64", "uint64") and fType2 in ("numeric", "int", "Int", "uint"):
            return "(" + S2 + ").toLong()"
        return S2

    def adjustConditional(self, S, conditionType):
        if isinstance(conditionType, dict):
            fType = progSpec.fieldTypeKeyword(conditionType)
            if progSpec.typeIsPointer(conditionType):
                if S[0] == "!":
                    S = "(" + S[1:] + " == null)"
                else:
                    S = "(" + S + " != null)"
                conditionType = "bool"
            elif fType == "flag" or progSpec.typeIsInteger(fType):
                if S[0] == "!":
                    S = "(" + S[1:] + " == 0)"
                else:
                    S = "(" + S + " != 0)"
                conditionType = "bool"
        return [S, conditionType]

    def codeFactor(self, item, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        if isinstance(item[0], str) and item[0] == "[":
            retTypeSpec = "noType"
            exprTypeSpec = "noType"
            elems = []
            for expr in item[1:-1]:
                [S2, exprTypeSpec] = self.codeGen.codeExpr(expr, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                elems.append(S2)
                if exprTypeSpec != "noType":
                    retTypeSpec = exprTypeSpec
            fTypeKW = "Any"
            if exprTypeSpec != "noType":
                retTypeKW = progSpec.fieldTypeKeyword(exprTypeSpec)
                fTypeKW = self.adjustBaseTypes(retTypeKW, True)
            return ["arrayListOf<" + fTypeKW + ">(" + ", ".join(elems) + ")", retTypeSpec]
        [S, retTypeSpec] = super().codeFactor(item, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
        S = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: "\\u00" + m.group(1).upper(), S)
        return [S, retTypeSpec]

    def codeSpecialReference(self, segSpec, genericArgs):
        funcName = segSpec[0]
        if len(segSpec) > 2 and funcName == "print":
            exprs = []
            for P in segSpec[2]:
                [S2, _argTypeSpec] = self.codeGen.codeExpr(P[0], None, None, "ARG", genericArgs)
                exprs.append("(" + S2 + ").toString()")
            return ["System.out.print(" + " + ".join(exprs) + ")", "me", "String"]
        return super().codeSpecialReference(segSpec, genericArgs)

    ###################################################### STRUCTS / FIELDS
    def codeMain(self, classes, tags):
        platform = progSpec.fetchTagValue(tags, "Platform")
        if platform == "Android":
            return ["", ""]
        return ["", "\nfun main(args: Array<String>) {\n    GLOBAL.static_Global.main(args);\n}\n"]

    def codeArgText(self, argFieldName, argType, argOwner, tSpec, makeConst, typeArgList):
        return "arg_" + argFieldName + ": " + self._cleanType(argType)

    def _extractCompanionLines(self, structCode):
        bodyLines = []
        companionLines = []
        for line in structCode.splitlines(True):
            stripped = line.lstrip()
            if stripped.startswith(self.companionMarker):
                companionLines.append(stripped[len(self.companionMarker):])
            else:
                bodyLines.append(line)
        return ["".join(bodyLines), companionLines]

    def codeStructText(self, classes, attrList, parentClass, classInherits, classImplements, className, structCode, tags):
        structCode = structCode.replace("    _ModeStrings modeStrings = new _ModeStrings();", "    var modeStrings: _ModeStrings = _ModeStrings();")
        [structCode, companionLines] = self._extractCompanionLines(structCode)

        classAttrs = ""
        if len(attrList) > 0:
            for attr in attrList:
                if attr == "abstract" and className != "GLOBAL":
                    classAttrs += "abstract "

        parents = []
        if parentClass != "":
            parents.append(progSpec.getUnwrappedClassFieldTypeKeyWord(classes, className) + "()")
        elif classInherits is not None:
            parents.append(progSpec.getUnwrappedClassFieldTypeKeyWord(classes, classInherits[0][0]) + "()")
        if classImplements is not None:
            for item in classImplements:
                if isinstance(item, list):
                    parents.append(item[0])
                else:
                    parents.append(item)
        parentText = ""
        if parents:
            parentText = " : " + ", ".join(parents)

        if companionLines:
            companionText = "    companion object {\n"
            for line in companionLines:
                companionText += line
            companionText += "    }\n"
            structCode = companionText + structCode

        S = "\n" + classAttrs + "class " + className + parentText + " {\n" + structCode + "}\n"
        typeArgList = progSpec.getTypeArgList(className)
        if typeArgList is not None:
            S = "\n" + classAttrs + self.codeTemplateHeader(className, typeArgList) + parentText + " {\n" + structCode + "}\n"
        return [S, ""]

    def addSpecialCode(self, filename):
        return "\n\n//////////// Kotlin specific code:\n"

    def addGLOBALSpecialCode(self, classes, tags):
        filename = self.codeGen.makeTagText(tags, "FileName")
        specialCode = 'const String: filename <- "' + filename + '"\n'
        GLOBAL_CODE = """
    struct GLOBAL{
        %s
    }
        """ % (specialCode)
        codeDogParser.AddToObjectFromText(classes[0], classes[1], GLOBAL_CODE, "Kotlin special code")

    def codeNewVarStr(self, LTSpec, varName, fieldDef, indent, genericArgs, localVarsAlloc):
        argList = fieldDef["argList"]
        if argList and argList[-1] == "^&useCtor//8":
            del argList[-1]
        cvrtType = self.codeGen.convertType(LTSpec, "var", genericArgs)
        cvrtType = self._cleanType(cvrtType)
        owner = progSpec.getOwner(LTSpec)
        localVarsAlloc.append([varName, LTSpec])
        assignValue = ""
        if fieldDef["value"]:
            [RHS, RTSpec] = self.codeGen.codeExpr(fieldDef["value"][0], LTSpec, None, "RVAL", genericArgs)
            RHS = self.checkForTypeCastNeed(LTSpec, RTSpec, RHS)
            assignValue = RHS
        elif argList is not None:
            modelParams = self.codeGen.chooseCtorModelParams(LTSpec, argList, genericArgs)
            [CPL, paramTypeList] = self.codeGen.codeArgList(varName, argList, modelParams, genericArgs)
            if self._isValueType(cvrtType) or self._nonNullableType(cvrtType) == "String":
                if len(paramTypeList) != 1:
                    cdErr("Kotlin value initialization expects one argument for " + varName + ".")
                assignValue = self.checkForTypeCastNeed(LTSpec, paramTypeList[0], CPL[1:-1])
            else:
                assignValue = self._nonNullableType(cvrtType) + CPL
        elif fieldDef["isAllocated"]:
            assignValue = self._defaultValueForType(self._nonNullableType(cvrtType), "me")
        else:
            assignValue = self._defaultValueForType(cvrtType, owner)
        return "var " + varName + ": " + cvrtType + " = " + assignValue

    def codeVarFieldRHS_Str(self, fieldName, cvrtType, tSpec, argList, isAllocated, typeArgList, genericArgs):
        cvrtType = self._cleanType(cvrtType)
        fieldOwner = progSpec.getOwner(tSpec)
        if argList is not None:
            if argList and argList[-1] == "^&useCtor//8":
                del argList[-1]
            [CPL, _paramTypeList] = self.codeGen.codeArgList(fieldName, argList, None, genericArgs)
            return " = " + self._nonNullableType(cvrtType) + CPL
        return " = " + self._defaultValueForType(cvrtType, fieldOwner)

    def codeConstField_Str(self, convertedType, fieldName, RHS, className, indent):
        convertedType = self._cleanType(convertedType)
        rhsExpr = self._rhsExpr(RHS)
        if convertedType in ("Int", "Long", "Double", "Float", "Boolean", "String", "Char"):
            decl = "    const val " + fieldName + ": " + convertedType + " = " + rhsExpr + ";\n"
        else:
            decl = "    val " + fieldName + ": " + convertedType + " = " + rhsExpr + ";\n"
        return [self.companionMarker + decl, ""]

    def codeVarField_Str(self, convertedType, tSpec, fieldName, RHS, className, tags, typeArgList, indent):
        convertedType = self._cleanType(convertedType)
        fieldOwner = progSpec.getOwner(tSpec)
        if self._rhsExpr(RHS) == "null" and not convertedType.endswith("?"):
            convertedType += "?"
        if fieldOwner == "we":
            decl = self._fieldDecl("    ", "@JvmField var", fieldName, convertedType, RHS, fieldOwner)
            return [self.companionMarker + decl, ""]
        return [self._fieldDecl(indent, "var", fieldName, convertedType, RHS, fieldOwner), ""]

    ###################################################### CONSTRUCTORS / FUNCS
    def codeConstructors(self, className, ctorArgs, ctorOvrRide, ctorInit, copyCtorArgs, funcBody, callSuper):
        if callSuper:
            funcBody = callSuper + funcBody
        withArgConstructor = ""
        if ctorArgs != "" or funcBody != "":
            withArgConstructor = "    constructor(" + ctorArgs + ") {\n" + funcBody + ctorInit + "    }\n"
        copyConstructor = "    constructor(fromVar: " + className + ") {\n" + copyCtorArgs + "    }\n"
        noArgConstructor = "    constructor() {\n" + funcBody + "\n    }\n"
        if className in ("ourSubMenu", "GUI", "CanvasView", "APP", "GUI_ZStack"):
            return ""
        return withArgConstructor + copyConstructor + noArgConstructor

    def codeConstructorInit(self, fieldName, count, defaultVal):
        return "        " + fieldName + " = arg_" + fieldName + ";\n"

    def codeConstructorArgText(self, argFieldName, count, argType, defaultVal):
        return "arg_" + argFieldName + ": " + self._cleanType(argType)

    def codeCopyConstructor(self, fieldName, isTemplateVar):
        if isTemplateVar:
            return ""
        return "        " + fieldName + " = fromVar." + fieldName + ";\n"

    def codeConstructorCall(self, className):
        return "        INIT();\n"

    def codeSuperConstructorCall(self, parentClassName):
        return "        super<" + parentClassName + ">.toString();\n"

    def codeFuncHeaderStr(self, className, fieldName, field, cvrtType, paramListText, localArgsAlloc, inheritMode, typeArgList, isNested, overRideOper, isStatic, indent):
        structCode = "\n"
        funcDefCode = ""
        globalFuncs = ""
        cvrtType = self._cleanType(cvrtType)
        if cvrtType == "Unit":
            retText = ""
        else:
            retText = ": " + cvrtType
        if fieldName == className:
            structCode += indent + "constructor(" + paramListText + ")"
        elif className == "GLOBAL" and fieldName == "main":
            structCode += indent + "fun main(args: Array<String>)"
            localArgsAlloc.append(["args", {"owner": "me", "fieldType": "string", "arraySpec": None, "reqTagList": None, "paramList": None}])
        else:
            prefix = "abstract " if inheritMode == "pure-virtual" else ""
            overrideText = "override " if inheritMode == "override" else ""
            structCode += indent + prefix + overrideText + "fun " + fieldName + "(" + paramListText + ")" + retText
            if inheritMode == "pure-virtual":
                structCode += "\n"
        return [structCode, funcDefCode, globalFuncs]

    def codeTemplateHeader(self, className, typeArgList):
        return "class " + className + "<" + ", ".join(typeArgList) + ">"

    def extraCodeForTopOfFuntion(self, paramList):
        if paramList is None or len(paramList) == 0 or paramList[0] == "<%":
            return ""
        S = ""
        for param in paramList:
            fieldName = param["fieldName"]
            S += "    var " + fieldName + " = arg_" + fieldName + ";\n"
        return S

    ###################################################### STATEMENTS / MISC
    def codeSetBits(self, LHS_Left, LHS_FieldType, prefix, bitMask, RHS, rhsType):
        item = LHS_Left + "flags"
        if LHS_FieldType == "flag":
            mask = prefix + bitMask
            if RHS not in ("true", "false") and progSpec.fieldTypeKeyword(rhsType) != "bool":
                RHS += " != 0"
            val = "if (" + RHS + ") " + mask + " else 0L"
        elif LHS_FieldType == "mode":
            mask = prefix + bitMask + "Mask"
            offset = prefix + bitMask + "Offset"
            if RHS == "false":
                RHS = "0"
            if RHS == "true":
                RHS = "1"
            val = "(" + RHS + ".toLong() shl " + offset + ".toInt())"
        else:
            cdErr("Unknown bit field type: " + LHS_FieldType)
        return item + " = " + item + " and " + mask + ".inv(); " + item + " = " + item + " or (" + val + ");\n"

    def checkIfSpecialAssignmentFormIsNeeded(self, action, indent, AltIDXFormat, RHS, rhsType, LHS, LHSParentType, LHS_FieldType):
        if AltIDXFormat is None:
            return ""
        assignTag = action["assignTag"]
        if not isinstance(assignTag, str):
            assignTag = assignTag[0]
        baseExpr = AltIDXFormat[0]
        idxExpr = AltIDXFormat[2]
        indexed = baseExpr + "[" + idxExpr + "]"
        if assignTag == "":
            if LHSParentType in ("string", "String") and LHS_FieldType in ("char", "Char"):
                return indent + baseExpr + " = " + baseExpr + ".substring(0, " + idxExpr + ") + " + RHS + " + " + baseExpr + ".substring(" + idxExpr + " + 1);\n"
            return indent + indexed + " = " + RHS + ";\n"
        if assignTag == "+":
            return indent + indexed + " = " + indexed + " + " + RHS + ";\n"
        if assignTag == "-":
            return indent + indexed + " = " + indexed + " - " + RHS + ";\n"
        return ""

    def applyTypecast(self, typeInCodeDog, itemToAlterType):
        platformType = self.adjustBaseTypes(typeInCodeDog, False)
        if platformType == "Int":
            return "(" + itemToAlterType + ").toInt()"
        if platformType == "Long":
            return "(" + itemToAlterType + ").toLong()"
        if platformType == "Double":
            return "(" + itemToAlterType + ").toDouble()"
        if platformType == "Float":
            return "(" + itemToAlterType + ").toFloat()"
        if platformType == "Char":
            return "(" + itemToAlterType + ").toChar()"
        return "(" + itemToAlterType + " as " + platformType + ")"

    def codeReadBitField(self, S, connector, prevLen, prefix, segName, fType):
        flagsExpr = S[0:prevLen] + connector + "flags"
        if fType == "flag":
            return "(" + flagsExpr + " and " + prefix + segName + ")"
        return "(((" + flagsExpr + " and " + prefix + segName + "Mask) shr " + prefix + segName + "Offset.toInt()).toInt())"

    def codeSwitchStmt(self, action, indent, returnType, genericArgs):
        [switchKeyExpr, switchKeyTypeSpec] = self.codeGen.codeExpr(action["switchKey"][0], None, None, "RVAL", genericArgs)
        S = indent + "when (" + self.codeSwitchExpr(switchKeyExpr, switchKeyTypeSpec) + ") {\n"
        for sCases in action["switchCases"]:
            caseValues = []
            for sCase in sCases[0]:
                [caseKeyValue, caseKeyTypeSpec] = self.codeGen.codeExpr(sCase[0], None, None, "RVAL", genericArgs)
                caseValues.append(self.codeSwitchCase(caseKeyValue, caseKeyTypeSpec))
            S += indent + "    " + ", ".join(caseValues) + " -> "
            S += self.codeGen.codeActionSeq(sCases[1], indent + "    ", returnType, genericArgs)
        defaultCase = action["defaultCase"]
        if defaultCase and len(defaultCase) > 0:
            S += indent + "    else -> "
            S += self.codeGen.codeActionSeq(defaultCase, indent + "    ", returnType, genericArgs)
        S += indent + "}\n"
        return S

    def includeDirective(self, libHdr):
        return "import " + libHdr + "\n"

    def generateMainFunctionality(self, classes, tags):
        runCode = progSpec.fetchTagValue(tags, "runCode")
        if runCode is None:
            runCode = ""
        platform = progSpec.fetchTagValue(tags, "Platform")
        if platform == "Android":
            mainFuncCode = """
            me void: runDogCode() <- {
                """ + runCode + """
            }
        """
        else:
            mainFuncCode = """
            me void: main() <- {
                initialize("")
                """ + runCode + """
                deinitialize()
            }
        """
        progSpec.addClass(classes[0], classes[1], "GLOBAL", "struct", "SEQ", ["//^", "Main class"])
        codeDogParser.AddToObjectFromText(classes[0], classes[1], progSpec.wrapFieldListInObjectDef("GLOBAL", mainFuncCode), "Kotlin start-up code")

    def __init__(self):
        self.enumDefaults = {}
        self.enumTypes = set()
        print("INIT")
