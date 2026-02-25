#xlator_CPP.py
import progSpec
import codeDogParser
from xlator import Xlator
from progSpec import cdlog, cdErr, logLvl
from codeGenerator import CodeGenerator

class Xlator_CPP(Xlator):
    codeGen               = CodeGenerator()
    LanguageName          = "C++"
    BuildStrPrefix        = "g++ -g -std=gnu++17  "
    fileExtension         = ".cpp"
    typeForCounterInt     = "int64_t"
    GlobalVarPrefix       = ""
    PtrConnector          = "->"                      # Name segment connector for pointers.
    ObjConnector          = "::"                      # Name segment connector for Classes.
    NameSegConnector      = "."
    NameSegFuncConnector  = "."
    modeIdxType           = 'uint64'
    doesLangHaveGlobals   = True
    funcBodyIndent        = ""
    funcsDefInClass       = False
    MakeConstructors      = True
    blockPrefix           = ""
    usePrefixOnStatics    = False
    iteratorsUseOperators = True
    renderGenerics        = "False"
    renameInitFuncs       = False
    useAllCtorArgs        = False
    hasMacros             = True
    useNestedClasses      = True
    nullValue             = "nullptr"
    langSpecificImpl      = {
                                "Equatable": "",
                            }

    def getLangSpecificImplements(self, implName):
        if implName in self.langSpecificImpl:
            return self.langSpecificImpl[implName]
        return None

    ###################################################### Helpers

    def makeUniqueLocalName(self, base, localVarsAlloc):
        used = {name for (name, _ts) in localVarsAlloc}
        if base not in used:
            return base
        i = 2
        while f"{base}_{i}" in used:
            i += 1
        return f"{base}_{i}"

    ###################################################### CONTAINERS
    def getIteratorValueCodeConverter(self, tSpec, prevNameSeg):
        fTypeKW    = progSpec.fieldTypeKeyword(tSpec)
        itrTSpec   = self.codeGen.getDataStructItrTSpec(fTypeKW)
        itrTypeKW  = progSpec.fieldTypeKeyword(itrTSpec)
        reqTagList = progSpec.getReqTagList(tSpec)
        valOwner   = progSpec.getOwner(reqTagList[1])
        [LNodeP, RNodeP, LNodeA, RNodeA] = self.ChoosePtrDecorationForSimpleCase(valOwner)
        itrVal     = progSpec.getCodeConverterByFieldID(self.codeGen.classStore, itrTypeKW, 'val', prevNameSeg ,RNodeP)
        return itrVal

    def codeArrayIndex(self, idx, containerType, LorR_Val, previousSegName, idxTypeSpec):
        owner = progSpec.getOwner(idxTypeSpec)
        if owner=='their' or owner=='our' or owner=='itr': idx = "*"+idx
        S= '[' + idx +']'
        return S

    ###################################################### CONTAINER REPETITIONS
    def getRangeLoopParts(self, traversalMode, ctrType, repName, S_low, S_hi, inclusive, indent):
        mode = traversalMode or 'Forward'

        if mode == 'Backward':
            init = S_hi if inclusive else f"({S_hi}-1)"
            cmp  = ">="
            bound = S_low
            step = self.codeDecrement(repName)  # e.g. --repName
        else:
            # Forward (default)
            init = S_low
            cmp  = "<=" if inclusive else "<"
            bound = S_hi
            step = self.codeIncrement(repName)  # e.g. ++repName

        return {
            "kind": "c_for",
            "init": f"{ctrType} {repName}={init}",
            "cond": f"{repName} {cmp} {bound}",
            "step": f"{step}",
            "prologue": "",
            "epilogue": "",
            "needsContinueRewrite": False,
        }

    def emitLoopWithBody(self, parts, body, returnType, mods, genericArgs, indent):
        actionText = ""

        # ---- modifiers ----
        skipExpr = mods.get('skipExpr') if mods else None
        takeExpr = mods.get('takeExpr') if mods else None
        whereExprNode = mods.get('whereExpr') if mods else None
        untilExprNode = mods.get('untilExpr') if mods else None

        if skipExpr or takeExpr:
            cdErr("skip/take not implemented yet in emitLoopWithBody().")

        # ---- emit loop header ----
        if parts.get("kind") == "foreach":
            header = parts.get("foreach")
            if not header: cdErr("foreach loop missing header")
            actionText += indent + header + "{\n"
        else:
            actionText += indent + f"for({parts['init']}; {parts['cond']}; {parts['step']}){{\n"

        actionText += parts.get("prologue", "")

        # ---- where / until (runs after binding prologue) ----
        if whereExprNode:
            whereExprIn = whereExprNode[0] if not isinstance(whereExprNode, str) else whereExprNode
            [whereExpr, _whereType] = self.codeGen.codeExpr(whereExprIn, None, None, 'RVAL', genericArgs)
            actionText += indent + "    " + f"if (!({whereExpr})) continue;\n"

        if untilExprNode:
            untilExprIn = untilExprNode[0] if not isinstance(untilExprNode, str) else untilExprNode
            [untilExpr, _untilType] = self.codeGen.codeExpr(untilExprIn, None, None, 'RVAL', genericArgs)
            actionText += indent + "    " + f"if ({untilExpr}) break;\n"

        # ---- body ----
        for repAction in body:
            actionText += self.codeGen.codeAction(repAction, indent + "    ", returnType, genericArgs)

        # ---- epilogue + close ----
        actionText += parts.get("epilogue", "")
        actionText += indent + "}\n"
        return actionText

    def codeRangeSpec(self, traversalMode, ctrType, repName, S_low, S_hi, inclusive, indent, body, returnType, mods, genericArgs):
        parts = self.getRangeLoopParts(traversalMode, ctrType, repName, S_low, S_hi, inclusive, indent)
        return self.emitLoopWithBody(parts, body, returnType, mods, genericArgs, indent)

    def getIdxType(self, tSpec):
        progSpec.isOldContainerTempFuncErr(tSpec,"xlator_CPP.getIdxType()")
        idxType = ''
        if progSpec.isNewContainerTempFunc(tSpec):
            ctnrTSpec = progSpec.getContainerSpec(tSpec)
            if 'indexType' in ctnrTSpec:
                if 'IDXowner' in ctnrTSpec['indexType']:
                    idxOwner = ctnrTSpec['indexType']['IDXowner'][0]
                    idxType  = ctnrTSpec['indexType']['idxBaseType'][0][0]
                    idxType  = self.applyOwner(idxOwner, idxType,'')
                else: idxType=ctnrTSpec['indexType']['idxBaseType'][0][0]
            if idxType[0:4]=='uint': idxType+='_t'
        return idxType
    
    # C++ xlator helper: build a for-loop + binding prologue from capabilities + binding + (optional) rangeClause.
    #
    # Supports:
    #   - plain traversal (no rangeClause): begin/end (or rbegin/rend if Backward)
    #   - iters:   start..end   (iterator to iterator)
    #   - keys:    k1..k2 / k1..=k2   (ordered associative; lower/upper bound)
    #
    # Returns LoopParts dict:
    #   {
    #     "kind": "c_for",
    #     "init": "...",
    #     "cond": "...",
    #     "step": "...",
    #     "prologue": "...",  # already indented with bodyIndent
    #     "epilogue": "",
    #     "needsContinueRewrite": False,
    #   }
    #
    # NOTE: This is an internal helper; you can call it from:
    #   - iterateContainerStr (plain traversal path)
    #   - rangeTraversalStr   (rangeClause path)
    #   - or directly from codeWithEachRepetition() if you want
    #
    def getForLoopSegStrs(
        self,
        classes,
        localVarsAlloc,
        ctnrTSpec,
        ctnrName,
        binding,
        traversalMode=None,     # "Backward" or None
        rangeMode=None,         # None | "iters" | "keys"
        rangeSpec=None,         # parsed rangeSpec node (has rangeStart/rangeEnd and inclusiveOp/exclusiveOp)
        genericArgs=None,
        indent=""
    ):
        # ---- capabilities ----
        caps = progSpec.getContainerCapabilities(classes, ctnrTSpec)
        tags = caps.get("tags", set())
        iterCaps = caps.get("iter", {})
        yields = iterCaps.get("yields", "value")  # "value" or "entry"
        bodyIndent = indent + "    "

        isBackward = (traversalMode == "Backward")

        #---- So we need . or ->, etc to access members ----
        [datastructID, ctnrOwner] = progSpec.getContainerType_Owner(ctnrTSpec)
        [LDeclP, RDeclP, LDeclA, RDeclA] = self.ChoosePtrDecorationForSimpleCase(ctnrOwner)

        # ---- basic iterable validation ----
        if progSpec.fieldTypeKeyword(ctnrTSpec) != "string" and not iterCaps.get("hasBeginEnd", True):
            cdErr(f"Container '{ctnrName}' is not iterable in C++ backend (missing begin/end).")

        if isBackward and not (("bidirectional" in tags) or iterCaps.get("rbegin_rend", False)):
            cdErr(f"Container '{ctnrName}' does not support Backward traversal.")

        # ---- binding decode ----
        bkind = binding.get("kind")
        axis = binding.get("axis")  # may be None for single; tuple implies entry
        keyName = None
        valName = None
        loopVarName = None

        if bkind == "tuple":
            keyName = binding.get("keyName")
            valName = binding.get("valName")
            if not keyName or not valName: cdErr("Tuple binding missing keyName/valName.")
            axis = "entry"  # implied
        elif bkind == "single":
            loopVarName = binding.get("name")
            if not loopVarName: cdErr("Single binding missing name.")
            if axis is None:
                axis = "value"
        else:
            cdErr("Unknown binding kind for withEach.")

        # tuple implies associative entry semantics
        if bkind == "tuple":
            if "associative" not in tags and yields != "entry":
                cdErr("Tuple binding (k,v) requires an associative container yielding entries.")

        # ---- register loop locals for type tracking ----
        def _make_tspec(owner, ftype):
            return {'owner': owner, 'fieldType': ftype}

        # Derive key/value specs from container type
        keySpec = None
        valSpec = None
        containerCat = progSpec.getContaineCategory(classes, ctnrTSpec)
        reqTagList = progSpec.getReqTagList(ctnrTSpec)

        if progSpec.fieldTypeKeyword(ctnrTSpec) == "string":
            valSpec = _make_tspec('me', 'char')
        elif reqTagList:
            if containerCat in ("Map", "Multimap"):
                if len(reqTagList) > 0:
                    keySpec = _make_tspec(reqTagList[0]['tArgOwner'], reqTagList[0]['tArgType'])
                if len(reqTagList) > 1:
                    valSpec = _make_tspec(reqTagList[1]['tArgOwner'], reqTagList[1]['tArgType'])
            else:
                valSpec = _make_tspec(reqTagList[0]['tArgOwner'], reqTagList[0]['tArgType'])
        else:
            firstType = progSpec.getContainerFirstElementType(ctnrTSpec)
            if firstType:
                firstOwner = progSpec.getContainerFirstElementOwner(ctnrTSpec)
                valSpec = _make_tspec(firstOwner, firstType)

        if bkind == "tuple":
            if keyName and keySpec:
                localVarsAlloc.append([keyName, keySpec])
            if valName and valSpec:
                localVarsAlloc.append([valName, valSpec])
        elif bkind == "single":
            if axis == "key" and keySpec:
                localVarsAlloc.append([loopVarName, keySpec])
            elif axis == "value" and valSpec:
                localVarsAlloc.append([loopVarName, valSpec])
            elif axis == "entry" and valSpec:
                # Best-effort: treat entry as value for type tracking.
                localVarsAlloc.append([loopVarName, valSpec])
            elif axis == "iter":
                itrTSpec = self.codeGen.getDataStructItrTSpec(progSpec.fieldTypeKeyword(ctnrTSpec))
                if itrTSpec:
                    localVarsAlloc.append([loopVarName, itrTSpec])

        # ---- helper: choose internal iterator var name ----
        def _chooseItrName():
            # If user asked for an iterator variable, prefer using their name as the iterator name
            # (lets some languages bind without extra statements; in C++ it simplifies too).
            if bkind == "single" and axis == "iter" and loopVarName:
                return loopVarName

            if bkind == "tuple":
                base = f"{keyName}_{valName}"
            else:
                base = loopVarName or "it"
            return self.makeUniqueLocalName(f"__cd_itr_{base}", localVarsAlloc)

        # ---- helper: emit binding prologue from iterator variable ----
        def _emitBindingFromItr(itrName):
            pro = ""

            # axis == iter means the loop variable already IS the iterator if we chose itrName==loopVarName.
            if axis == "iter":
                # If itrName != loopVarName (because tuple or internal name), alias it
                if bkind == "single" and axis == "iter" and loopVarName:
                    # Prefer using the user name if it is unique; otherwise create an internal and alias in prologue.
                    unique = self.makeUniqueLocalName(loopVarName, localVarsAlloc)
                    if unique == loopVarName:
                        return loopVarName
                    # Use an internal iterator name; prologue will alias loopVarName to it.
                    return unique


            # string special-cased elsewhere; for containers, bind from *itr
            if axis == "entry":
                if "associative" not in tags and yields != "entry":
                    cdErr("entry binding requires an associative container yielding entries.")
                if bkind == "tuple":
                    # C++17 structured binding, mutable value
                    pro += bodyIndent + f"auto& [{keyName}, {valName}] = *{itrName};\n"
                else:
                    pro += bodyIndent + f"auto {loopVarName} = *{itrName};\n"
                return pro

            if axis == "key":
                if "associative" not in tags and yields != "entry":
                    cdErr("key binding requires an associative container.")
                pro += bodyIndent + f"auto {loopVarName} = (*{itrName}).first;\n"
                return pro

            if axis == "value":
                if ("associative" in tags or yields == "entry"):
                    pro += bodyIndent + f"auto {loopVarName} = (*{itrName}).second;\n"
                else:
                    pro += bodyIndent + f"auto {loopVarName} = *{itrName};\n"
                return pro

            if axis == "index":
                cdErr("index axis not supported in iterator-based C++ lowering yet.")

            cdErr(f"Unknown binding axis: {axis}")
            return pro

        # ---- rangeSpec helpers ----
        def _range_is_inclusive(rs):
            return bool(getattr(rs, "inclusiveOp", False))

        def _range_start_end_exprs(rs):
            # returns (startNode, endNode) parse results or None
            startPR = rs.get("rangeStart", None) if rs else None
            endPR = rs.get("rangeEnd", None) if rs else None
            return (startPR, endPR)

        # ---- build loop parts ----
        parts = {
            "kind": "c_for",
            "init": "",
            "cond": "",
            "step": "",
            "prologue": "",
            "epilogue": "",
            "needsContinueRewrite": False,
        }

        # ---- string: simplest C++ foreach ----
        if progSpec.fieldTypeKeyword(ctnrTSpec) == "string":
            if bkind != "single" or axis not in ("value", None):
                cdErr("String traversal only supports single value binding.")
            # Use a "c_for" equivalent? For now, keep it in init/cond/step as empty and put full header in init
            # but if you prefer, you can add parts["kind"]="foreach" later.
            # We'll emulate with init as full header and leave others blank (caller must handle if you use this path).
            parts["kind"] = "foreach"
            parts["foreach"] = f"for(char const &{loopVarName}: {ctnrName})"
            parts["prologue"] = ""
            return parts

        # ---- mode: None => plain traversal ----
        if rangeMode is None:
            itrName = _chooseItrName()

            if isBackward:
                beginExpr = f"{LDeclP}{ctnrName}{RDeclP}rbegin()"
                endExpr = f"{LDeclP}{ctnrName}{RDeclP}rend()"
            else:
                beginExpr = f"{LDeclP}{ctnrName}{RDeclP}begin()"
                endExpr = f"{LDeclP}{ctnrName}{RDeclP}end()"

            parts["init"] = f"auto {itrName} = {beginExpr}"
            parts["cond"] = f"{itrName} != {endExpr}"
            parts["step"] = f"++{itrName}"
            parts["prologue"] = _emitBindingFromItr(itrName)
            return parts

        # ---- mode: iters (iterator range) ----
        if rangeMode == "iters":
            if not rangeSpec:
                cdErr("iters: requires a rangeSpec.")
            if _range_is_inclusive(rangeSpec):
                cdErr("Inclusive ranges (..=) are not allowed for iters: ranges. Use '..' instead.")

            itrName = _chooseItrName()

            startPR, endPR = _range_start_end_exprs(rangeSpec)

            # Defaults
            if startPR:
                [startExpr, _] = self.codeGen.codeExpr(startPR[0], None, None, 'RVAL', genericArgs)
            else:
                startExpr = f"{LDeclP}{ctnrName}{RDeclP}begin()"

            if endPR:
                [endExpr, _] = self.codeGen.codeExpr(endPR[0], None, None, 'RVAL', genericArgs)
            else:
                endExpr = f"{LDeclP}{ctnrName}{RDeclP}end()"

            # NOTE: Backward with explicit iterator endpoints is ambiguous (are these reverse iters?).
            # For now, error rather than guess.
            if isBackward:
                cdErr("Backward iters: ranges are not supported yet (ambiguous iterator direction).")

            parts["init"] = f"auto {itrName} = {startExpr}"
            parts["cond"] = f"{itrName} != {endExpr}"
            parts["step"] = f"++{itrName}"
            parts["prologue"] = _emitBindingFromItr(itrName)
            return parts

        # ---- mode: keys (ordered associative key range) ----
        if rangeMode == "keys":
            if "ordered_keys" not in tags:
                cdErr(f"keys: range requires ordered_keys capability for container '{ctnrName}'.")
            if not rangeSpec:
                cdErr("keys: requires a rangeSpec.")

            inclusive = _range_is_inclusive(rangeSpec)
            startPR, endPR = _range_start_end_exprs(rangeSpec)

            # Compute begin iterator
            if startPR:
                [startKeyExpr, _] = self.codeGen.codeExpr(startPR[0], None, None, 'RVAL', genericArgs)
                beginExpr = f"{LDeclP}{ctnrName}{RDeclP}lower_bound({startKeyExpr})"
            else:
                beginExpr = f"{LDeclP}{ctnrName}{RDeclP}begin()"

            # Compute end iterator (exclusive iterator bound).
            if endPR:
                [endKeyExpr, _] = self.codeGen.codeExpr(endPR[0], None, None, 'RVAL', genericArgs)
                if inclusive:
                    endExpr = f"{LDeclP}{ctnrName}{RDeclP}upper_bound({endKeyExpr})"
                else:
                    endExpr = f"{LDeclP}{ctnrName}{RDeclP}lower_bound({endKeyExpr})"
            else:
                endExpr = f"{LDeclP}{ctnrName}{RDeclP}end()"

            if isBackward:
                cdErr("Backward keys: ranges not supported yet (needs reverse-iterator key range design).")

            itrName = _chooseItrName()
            endName = self.makeUniqueLocalName(f"__cd_end_{itrName}", localVarsAlloc)

            # Declare both iterators in init so cond can reference endName without extra scope tricks
            parts["init"] = f"auto {itrName} = {beginExpr}, {endName} = {endExpr}"
            parts["cond"] = f"{itrName} != {endName}"
            parts["step"] = f"++{itrName}"
            parts["prologue"] = _emitBindingFromItr(itrName)
            return parts
        
        if rangeMode == "index":
            cdErr("index: ranges not implemented for C++ yet (needs indexable lowering).")


        cdErr(f"Unsupported rangeMode: {rangeMode}")
        return parts

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
        traversalMode=None,   # "Backward" or None
        rangeMode=None,       # None | "iters" | "keys" | "index"
        rangeSpec=None,       # parse node
    ):
        # ---- build loop parts ----
        parts = self.getForLoopSegStrs(
            classes=classes,
            localVarsAlloc=localVarsAlloc,
            ctnrTSpec=ctnrTSpec,
            ctnrName=ctnrName,
            binding=binding,
            traversalMode=traversalMode,
            rangeMode=rangeMode,
            rangeSpec=rangeSpec,
            genericArgs=genericArgs,
            indent=indent,
        )
        return self.emitLoopWithBody(parts, body, returnType, mods, genericArgs, indent)

    def codeSwitchExpr(self, switchKeyExpr, switchKeyTypeSpec):
        switchKeyTypeKW = progSpec.fieldTypeKeyword(switchKeyTypeSpec)
        if switchKeyTypeKW == 'string':
            switchKeyExpr = '_strHash(' + switchKeyExpr + '.data())'
        return switchKeyExpr

    def codeSwitchCase(self, caseKeyValue, caseKeyTypeSpec):
        caseKeyTypeKW = progSpec.fieldTypeKeyword(caseKeyTypeSpec)
        if caseKeyTypeKW == 'string':
            caseKeyValue = '_strHash(' + caseKeyValue + ')'
        return caseKeyValue

    ###### Routines to track types of identifiers and to look up type based on identifier.
    def implOperatorsAsFuncs(self, fTypeKW):
        return False

    def adjustBaseTypes(self, fType, isContainer):
        if(isinstance(fType, str)):
            if(fType=='uint8' or fType=='uint16'): fType='uint32'
            elif(fType=='int8' or fType=='int16'): fType='int32'
            if(fType=='uint32' or fType=='uint64' or fType=='int32' or fType=='int64'):
                langType=fType+'_t'
            else:
                langType=progSpec.flattenObjectName(fType)
        else: langType=progSpec.flattenObjectName(fType[0])
        return langType

    def applyIterator(self, langType, itrTypeKW, varMode):
        # varMode is 'var' or 'arg' or 'alloc' or 'func' for function Header.
        if itrTypeKW==None: return langType
        if varMode=='func': langType = 'typename ' + langType
        return langType +'::' + itrTypeKW

    def applyOwner(self, owner, langType, varMode):
        # varMode is 'var' or 'arg' or 'alloc' or 'func' for function Header.
        if varMode!='alloc':
            if owner=='me':         langType = langType
            elif owner=='my':       langType = "unique_ptr<"+langType + ' >'
            elif owner=='our':      langType = "shared_ptr<"+langType + ' >'
            elif owner=='their':    langType += '*'
            elif owner=='itr' :     langType
            elif owner=='const':    langType = "static const "+langType
            elif owner=='we':       langType = 'static '+langType
            elif owner=='id_our':   langType="shared_ptr<"+langType + '>*'
            elif owner=='id_their': langType += '**'
            elif owner=='dblTheir': langType += '**'
            else: cdErr("ERROR: Owner of type not valid '" + owner + "'")
        return langType

    def getUnwrappedClassOwner(self, classes, tSpec, fType, varMode, ownerIn):
        ownerOut = ownerIn
        baseType = progSpec.isWrappedType(classes, fType)
        if baseType!=None:  # TODO: When this is all tested and stable, un-hardcode and optimize this!!!!!
            if 'ownerMe' in baseType: ownerOut = 'their'
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
                unwrappedKW = self.adjustBaseTypes(unwrappedKW, progSpec.isNewContainerTempFunc(tSpec))
                reqType     = self.applyOwner(unwrappedOwner, unwrappedKW, '')
                if(count>0): reqTagStr += ", "
                reqTagStr += reqType
                count += 1
            reqTagStr += ">"
        return reqTagStr

    def makePtrOpt(self, tSpec):
        return('')

    def recodeStringFunctions(self, name, tSpec, lenArgs):
        if name == "size": name = "length"
        elif name == "subStr": name = "substr"
        return [name, tSpec]

    def langStringFormatterCommand(self, fmtStr, argStr):
        S='strFmt('+'"'+ fmtStr +'"'+ argStr +')'
        return S

    def LanguageSpecificDecorations(self, S, tSpec, owner, LorRorP_Val):
        return S

    def convertToInt(self, S, tSpec):
        return S

    def checkForTypeCastNeed(self, lhsTSpec, rhsTSpec, RHS):
        return RHS

    def getTheDerefPtrMods(self, tSpec):
        if tSpec!=None and isinstance(tSpec, dict) and 'owner' in tSpec:
            owner=progSpec.getOwner(tSpec)
            if progSpec.isNewContainerTempFunc(tSpec):
                if owner=='itr':
                    itrVal = self.getIteratorValueCodeConverter(tSpec, '')
                    return ['', itrVal, False]
                return ['', '', False]
            if progSpec.typeIsPointer(owner):
                if owner!='itr':
                    return ['(*', ')', True]
        return ['', '', False]

    def derefPtr(self, varRef, tSpec):
        [leftMod, rightMod, isDerefd] = self.getTheDerefPtrMods(tSpec)
        S = leftMod + varRef + rightMod
        return [S, isDerefd]

    def ChoosePtrDecorationForSimpleCase(self, owner):
        if(owner=='our' or owner=='my' or owner=='their'):
            return ['','->',  '(*', ')']
        else: return ['','.',  '','']

    def chooseVirtualRValOwner(self, LVAL, RVAL):
        # Returns left and right text decorations for RHS of function arguments, return values, etc.
        if RVAL==0 or RVAL==None or isinstance(RVAL, str): return ['',''] # This happens e.g., string.size() # TODO: fix this.
        if LVAL==0 or LVAL==None or isinstance(LVAL, str): return ['', '']
        LeftOwner =progSpec.getOwner(LVAL)
        RightOwner=progSpec.getOwner(RVAL)
        if(LeftOwner=="id_their" and RightOwner=="id_their"): return ["&", ""]
        if LeftOwner == RightOwner: return ["", ""]
        if LeftOwner!='itr' and RightOwner=='itr':
            # TODO: test this change.  This looks like code that handled codeDog 1.0 container iterators, which is now handled in codeConverters
            #return ["", "->second"]
            return ["", ""]
        if LeftOwner=='me' and progSpec.typeIsPointer(RVAL):
            return ["(*", "   )"]
        if progSpec.typeIsPointer(LVAL) and RightOwner=='me':
            return ["&", '']
        if LeftOwner=='their' and (RightOwner=='our' or RightOwner=='my'): return ['','.get()']
        return ['','']

    def determinePtrConfigForNewVars(self, LTSpec, RTSpec, useCtor):
        leftOwner =progSpec.getOwner(LTSpec)
        rightOwner=progSpec.getOwner(RTSpec)
        if ((leftOwner=="me" or leftOwner=="literal") and rightOwner=="our"):
            return["*", ""]
        elif leftOwner=='their' and rightOwner == 'our' and not useCtor:
            return["*", ""]
        elif leftOwner=='their' and rightOwner == 'our' :
            return["", ".get()"]
        return["", ""]

    def determinePtrConfigForAssignments(self, LTSpec, RTSpec, assignTag, codeStr):
        #TODO: make test case
        # Returns left and right text decorations for both LHS and RHS of assignment
        if RTSpec==0 or RTSpec==None or isinstance(RTSpec, str): return ['','',  '',''] # This happens e.g., string.size() # TODO: fix this.
        if LTSpec==0 or LTSpec==None or isinstance(LTSpec, str): return ['','',  '','']
        LeftOwner =progSpec.getOwner(LTSpec)
        RightOwner=progSpec.getOwner(RTSpec)
        if not isinstance(assignTag, str):
            assignTag = assignTag[0]
        # Iterators in C++ are value-like types; avoid implicit address/deref
        # rewrites when one side is tagged 'itr' and the other is 'me'.
        if (LeftOwner == 'itr' and RightOwner == 'me') or (LeftOwner == 'me' and RightOwner == 'itr'):
            return ['','',  '','']
        if progSpec.typeIsPointer(LTSpec) and progSpec.typeIsPointer(RTSpec):
            if assignTag=='deep' :return ['(*',')',  '(*',')']
            elif LeftOwner=='their' and (RightOwner=='our' or RightOwner=='my'): return ['','', '','.get()']
            else: return ['','',  '', '']
        if LeftOwner == RightOwner: return ['','',  '','']
        if LeftOwner=='me' and progSpec.typeIsPointer(RTSpec):
            [leftMod, rightMod, isDerefd] = self.getTheDerefPtrMods(RTSpec)
            return ['','',  leftMod, rightMod]  # ['', '', "(*", ")"]
        if progSpec.typeIsPointer(LTSpec) and RightOwner=='me':
            if assignTag!="" or assignTag=='deep':return ['(*',')',  '', '']
            else: return ['','',  "&", '']
        if progSpec.typeIsPointer(LTSpec) and RightOwner=='literal':return ['(*',')',  '', '']
        if progSpec.typeIsPointer(LTSpec) and RightOwner=='const':return ['(*',')', '','']
        return ['','',  '','']

    def codeSpecialParamList(self, tSpec, CPL):
        return CPL

    def codeXlatorAllocater(self, tSpec, genericArgs):
        S     = ''
        owner = progSpec.getOwner(tSpec)
        cvrtType  = self.codeGen.convertType(tSpec, 'alloc', genericArgs)
        if(owner=='our'): S="make_shared<"+cvrtType+">"
        elif(owner=='my'): S="make_unique<"+cvrtType+">"
        elif(owner=='their'): S="new "+cvrtType
        elif(owner=='me'): cdErr("Cannot allocate a 'me' variable. (" + cvrtType + ')')
        elif(owner=='we'): cdErr("Cannot allocate a 'we' variable. (" + varTypeStr + ')')
        elif(owner=='const'): cdErr("Cannot allocate a 'const' variable.")
        else: cdErr("Cannot allocate variable because owner is " + owner+".")
        return S

    def getConstIntFieldStr(self, fieldName, fieldValue, intSize):
        S= "static const uint64_t "+fieldName+ " = " + fieldValue+ ";"
        return(S)

    def langVarNamePrefix(self, crntBaseName, refedClass):
        if crntBaseName!=refedClass:
            return(refedClass + self.ObjConnector)
        return('')

    def getEnumStr(self, fieldName, enumList):
        S = "\n    enum " + fieldName +" {"
        enumSize = len (enumList)
        count=0
        for enumName in enumList:
            S += enumName+"="+hex(count)
            count=count+1
            if(count<enumSize): S += ", "
        S += "};\n";
        return(S)

    def getEnumStringifyFunc(self, className, enumList):
        S = "deque<string> {}Strings = {{".format(className)
        S += '"{}"'.format('", "'.join(enumList))
        S += '};\n\n'
        return S

    def codeIdentityCheck(self, S, S2, retType1, retType2, opIn):
        S2 = self.adjustQuotesForChar(retType1, retType2, S2)
        leftOwner  = progSpec.getOwner(retType1)
        rightOwner = progSpec.getOwner(retType2)
        if opIn == '===' or opIn == '!==':
            if progSpec.typeSpecsAreCompatible(retType1, retType2):
                return S+ opIn[:2] +S2
            elif progSpec.typeIsPointer(retType1) and progSpec.typeIsPointer(retType2):
                if leftOwner =='our' or leftOwner =='my': S+='.get()'
                if rightOwner=='our' or rightOwner=='my': S2+='.get()'
                return "(void*)("+ S +") "+opIn[:2]+" (void*)("+S2+")"
            else:
                return S+ opIn[:2] +S2
        else:
            if (opIn == '=='): opOut=' == '
            elif (opIn == '!='): opOut=' != '
            if not(leftOwner=='itr' and rightOwner=='itr'):
                [S_derefd, isDerefd] = self.derefPtr(S, retType1)
                if S2!='NULL' and S2!=self.nullValue: S=S_derefd
                [S2, isDerefd]=self.derefPtr(S2, retType2)
            return S+ opOut+S2
        return S

    def codeComparisonStr(self, S, S2, retType1, retType2, op):
        if (op == '<'): S+=' < '
        elif (op == '>'): S+=' > '
        elif (op == '<='): S+=' <= '
        elif (op == '>='): S+=' >= '
        else: cdErr("ERROR: One of <, >, <= or >= expected in code generator.")
        S2 = self.adjustQuotesForChar(retType1, retType2, S2)
        [S2, isDerefd]=self.derefPtr(S2, retType2)
        S+=S2
        return S

    ###################################################### EXPRESSION CODING
    def codeNotOperator(self, S, S2,retTypeSpec):
        S+='!' + S2
        return [S, retTypeSpec]

    def codeFactor(self, item, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        ####  ( value | ('(' + expr + ')') | ('!' + expr) | ('-' + expr) | varRef("varFunRef"))
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
                tmp="{"
                for expr in item[1:-1]:
                    [S2, retTypeSpec] = self.codeGen.codeExpr(expr, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                    if len(tmp)>1: tmp+=", "
                    tmp+=S2
                tmp+="}"
                S+=tmp
            elif item0=='{':
                tmp="{"
                idx=1
                while idx <  len(item)-1:
                    valExpr = item[idx+2]
                    [S2, retTypeSpec] = self.codeGen.codeExpr(valExpr, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                    if len(tmp)>1: tmp+=", "
                    tmp+="{" + item[idx] + ", " + S2 + "}"
                    idx += 3
                tmp+="}"
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
                    if returnType != None and returnType["fieldType"]=="char":
                        retTypeSpec='char'
                        innerS=item0[1:-1]
                        if len(innerS)==1:
                            if innerS=="'": innerS="\\'"
                            S+="'"+innerS +"'"
                        else:
                            cdErr("Characters must have exactly 1 character.")
                    else:
                        S+='"'+item0[1:-1] +'"'
                    retTypeSpec='string'
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
        fieldType1 = progSpec.fieldTypeKeyword(typeSpec1)
        fieldType2 = progSpec.fieldTypeKeyword(typeSpec2)
        if fieldType1 == "char" and (fieldType2 == 'string' or fieldType2 == 'String') and S[0] == '"':
            innerS = S[1:-1]
            if innerS=="'": innerS = "\\'"
            return("'" + innerS + "'")
        return(S)

    def adjustConditional(self, S2, conditionType):
        return [S2, conditionType]

    def codeSpecialReference(self, segSpec, genericArgs):
        S=''
        fType='void'   # default to void
        retOwner='me'    # default to 'me'
        funcName=segSpec[0]
        if(len(segSpec)>2):  # If there are arguments...
            argList=segSpec[2]
            if(funcName=='print'):
                # TODO: have a tag to choose cout vs printf()
                S+='cout'
                for P in argList:
                    [S2, argTypeSpec]=self.codeGen.codeExpr(P[0], None, None, 'ARG', genericArgs)
                    [S2, isDerefd]=self.derefPtr(S2, argTypeSpec)
                    S+=' << '+S2
                S+=" << flush"
            elif(funcName=='input'):
                P=argList[0]
                [S2, argTypeSpec]=self.codeGen.codeExpr(P[0], None, None, 'ARG', genericArgs)
                [S2, isDerefd]=self.derefPtr(S2, argTypeSpec)
                S+='getline(cin, '+S2+')'
            elif(funcName=='AllocateOrClear'):
                [varName,  varTypeSpec]=self.codeGen.codeExpr(argList[0][0], None, None, 'ARG', genericArgs)
                if(varTypeSpec==0): cdErr("Name is undefined: " + varName)
                S+='if('+varName+'){'+varName+'->clear();} else {'+varName+" = "+self.codeXlatorAllocater(varTypeSpec, genericArgs)+"();}"
            elif(funcName=='Allocate'):
                [varName,  varTypeSpec]=self.codeGen.codeExpr(argList[0][0], None, None, 'LVAL', genericArgs)
                if(varTypeSpec==0): cdErr("Name is Undefined: " + varName)
                S+=varName+" = "+self.codeXlatorAllocater(varTypeSpec, genericArgs)+'('
                count=0   # TODO: As needed, make this call codeArgList() with modelParams of the constructor.
                for P in argList[1:]:
                    if(count>0): S+=', '
                    [S2, argTypeSpec]=self.codeGen.codeExpr(P[0], None, None, 'ARG', genericArgs)
                    S+=S2
                    count=count+1
                S+=")"
            elif(funcName=='callPeriodically'):
                [objName,  tSpec]=self.codeGen.codeExpr(argList[1][0], None, None, 'ARG', genericArgs)
                [interval,  intTypeSpec]   =self.codeGen.codeExpr(argList[2][0], None, None, 'ARG', genericArgs)
                fType = progSpec.fieldTypeKeyword(tSpec)
                varTypeSpec= fType
                wrapperName="cb_wraps_"+varTypeSpec
                S+='g_timeout_add('+interval+', '+wrapperName+', '+objName+')'

                # Create a global function wrapping the class
                decl='\nint '+wrapperName+'(void* data)'
                defn='{'+varTypeSpec+'* self = ('+varTypeSpec+'*)data; self->run(); return true;}\n\n'
                self.codeGen.appendGlobalFuncAcc(decl, defn)
            elif(funcName=='break'):
                if len(argList)==0: S='break'
            elif(funcName=='return'):
                if len(argList)==0: S+='return'
            elif(funcName=='toStr'):
                if len(argList)==1:
                    [S2, argTypeSpec]=self.codeGen.codeExpr(P[0][0], None, None, 'ARG', genericArgs)
                    [S2, isDerefd]=self.derefPtr(S2, argTypeSpec)
                    S+='to_string('+S2+')'
                    fType='string'
            elif(funcName=='asClass'):
                if len(argList)==2:
                    [newTypeStr, argTypeSpec]=self.codeGen.codeExpr(argList[0][0], None, None, 'ARG', genericArgs)
                    [newTypeStr, isDerefd]=self.derefPtr(newTypeStr, argTypeSpec)
                    [toCvtStr, toCvtTypeSpec]=self.codeGen.codeExpr(argList[1][0], None, None, 'ARG', genericArgs)
                   # [toCvtStr, isDerefd]=self.derefPtr(toCvtStr, toCvtTypeSpec)
                    varOwner=progSpec.getOwner(toCvtTypeSpec)
                    if(varOwner=='their'): S="static_cast<"+newTypeStr+"*>("+toCvtStr+")"
                    elif(varOwner=='our'): S="static_pointer_cast<"+newTypeStr+">("+toCvtStr+")"
                    elif(varOwner=='my'):  S="static_pointer_cast<"+newTypeStr+">("+toCvtStr+")"
                    elif(varOwner=='me'):  S="static_cast<"+newTypeStr+">("+toCvtStr+")"
                    else: cdErr("Casting that to "+str(newTypeStr)+" is not yet supported.")
                    fType = newTypeStr
                    retOwner= varOwner

        else: # Not parameters, i.e., not a function
            if(funcName=='self'):
                S+='this'

        return [S, retOwner, fType]

    def checkIfSpecialAssignmentFormIsNeeded(self, action, indent, AltIDXFormat, RHS, rhsType, LHS, LHSParentType, LHS_FieldType):
        # Check for string A[x] = B;  If so, render A.insert(B,x)
        S = ''
        assignTag = action['assignTag']
        if assignTag == '':
            [containerType, owner]=progSpec.getContainerType_Owner(AltIDXFormat[1])
            if containerType == 'RBTreeMap':
                connector = '.'
                if progSpec.ownerIsPointer(owner): connector = self.PtrConnector
                S = indent+AltIDXFormat[0]+connector+'insert('+AltIDXFormat[2]+', '+RHS+');\n'
        #else: assignTag = assignTag[0]
        return S

    ############################################
    def codeProtectBlock(self, mutex, criticalText, indent):
        S = indent+'{\n'
        S += indent+'    Unique_Lock_Mutex mtxMgr('+mutex+');\n'
        S += criticalText
        S += indent+'}\n'
        return(S)

    def codeMain(self, classes, tags):
        cdlog(3, "\n            Generating GLOBAL...")
        if("GLOBAL" in classes[1]):
            if(classes[0]["GLOBAL"]['stateType'] != 'struct'):
                cdErr("ERROR: GLOBAL must be a 'struct'.")
            [structCode, funcCode, globalFuncs]=self.codeGen.codeStructFields("GLOBAL", tags, '')
            if(funcCode==''): funcCode="// No main() function.\n"
            if(structCode==''): structCode="// No Main Globals.\n"
            funcCode = "\n\n"+funcCode
            return ["\n\n// Globals\n" + structCode + "\n// Global Functions\n" + globalFuncs, funcCode]
        return ["// No Main Globals.\n", "// No main() function defined.\n"]

    def codeArgText(self, argFieldName, argType, argOwner, tSpec, makeConst, typeArgList):
        argTypeStr = argType
        if makeConst:
            if argOwner == "me": argMod = "&"
            else: argMod = ""
            argTypeStr = "const "+argTypeStr+argMod
        return argTypeStr + " " +argFieldName

    def codeStructText(self, classes, attrList, parentClass, classInherits, classImplements, className, structCode, tags):
        if parentClass != "":
            parentClass = parentClass.replace('::', '_')
            parentClass = progSpec.getUnwrappedClassFieldTypeKeyWord(classes, className)
            parentClass=': public '+parentClass+' '
            print("Warning: old style inheritance used: " , parentClass)
        if classInherits!=None:
            parentClass=': public '
            count =0
            for item in classInherits[0]:
                if count>0:
                    parentClass+= ', '
                parentClass+= progSpec.getUnwrappedClassFieldTypeKeyWord(classes, item)
                count += 1
        S= "\nstruct "+className+parentClass+"{\n" + structCode + '};\n'
        typeArgList = progSpec.getTypeArgList(className)
        templateHeader = ""
        if(typeArgList != None):
            forwardDecls = ""
            templateHeader = self.codeTemplateHeader(className, typeArgList)+" "
            S=templateHeader+S
        forwardDecls=templateHeader+"struct " + className + ";  \t// Forward declaration\n"
        return([S,forwardDecls])

    def produceTypeDefs(self, typeDefMap):
        typeDefCode="\n// Typedefs:\n"
        for key in typeDefMap:
            val=typeDefMap[key]
            if(val != '' and val != key):
                typeDefCode += 'typedef '+key+' '+val+';\n'
        return typeDefCode

    def addSpecialCode(self, filename):
        S='\n\n//////////// C++ specific code:\n'
        S += "\n\nusing namespace std;\n\n"
        S += "typedef unsigned int uint;\n\n"
        S += 'const string filename = "' + filename + '";\n'
        S += r'static void reportFault(int Signal){cout<<"\nSegmentation Fault.\n"; fflush(stdout); abort();}'+'\n\n'

        S += "string enumText(string* array, int enumVal, int enumOffset){return array[enumVal >> enumOffset];}\n";
        S += "#define SetBitsMACRO(item, mask, val) {(item) &= ~((uint64_t)mask); (item)|=((uint64_t)val);}\n"
        S += "#define SetFlagBit(item, mask, val) SetBits(item, mask, ((val)?mask:0))\n"
        S += "#define SetModeBits(item, mask, val) SetBits(item, mask##Mask, ((uint64_t)val << mask##Offset))\n"
        S += "#define getFlagBit(item, mask) (bool)(item & (uint64_t)mask)\n"
        S += "#define getModeBits(item, mask) (uint64_t)((item & (uint64_t)mask##Mask)>>(uint64_t)mask##Offset)\n"

        S += '''
template<class T> class CopyableAtomic : public std::atomic<T>{
public:
    //defaultinitializes value
    CopyableAtomic() = default;

    constexpr CopyableAtomic(T desired) :
        std::atomic<T>(desired)
    {}

    constexpr CopyableAtomic(const CopyableAtomic<T>& other) :
        CopyableAtomic(other.load(std::memory_order_relaxed))
    {}

    CopyableAtomic& operator=(const CopyableAtomic<T>& other) {
        this->store(other.load(std::memory_order_relaxed), std::memory_order_relaxed);
        return *this;
    }
};

void SetBits(CopyableAtomic<uint64_t>& target, uint64_t mask, uint64_t value) {
    uint64_t original_value = target.load();
    uint64_t new_value = original_value;
    SetBitsMACRO(new_value, mask, value);
    while(!target.compare_exchange_weak(original_value, new_value)){
        new_value = original_value;
        SetBitsMACRO(new_value, mask, value);
    }
}

'''
        decl ="string readFileAsString(string filename)"
        defn="""{
            string S="";
            std::ifstream file(filename);
            if(file.eof() || file.fail()) {return "";}
            file.seekg(0, std::ios::end);
            S.resize(file.tellg());
            file.seekg(0, std::ios::beg);
            file.read((char*)S.c_str(), S.length());
            return S;  //No errors
        }

        """
        self.codeGen.appendGlobalFuncAcc(decl, defn)

        return S

    def addGLOBALSpecialCode(self, classes, tags):
        specialCode =''

        GLOBAL_CODE="""
    struct GLOBAL{
        %s
    }
        """ % (specialCode)
        #codeDogParser.AddToObjectFromText(classes[0], classes[1], GLOBAL_CODE )

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
        if(fieldDef['value']):
            [RHS, RTSpec]=self.codeGen.codeExpr(fieldDef['value'][0], LTSpec, None, 'RVAL', genericArgs)
            [LHS_leftMod, LHS_rightMod,  RHS_leftMod, RHS_rightMod] = self.determinePtrConfigForAssignments(LTSpec, RTSpec, "" , RHS)
            if(isAllocated and not progSpec.typeIsPointer(RTSpec)):
                RHS = self.codeGen.codeAllocater(LTSpec, RHS, genericArgs)
            else: RHS = RHS_leftMod+RHS+RHS_rightMod
            if(isAllocated or useCtor==False): assignValue = " = " + RHS
            else: assignValue = RHS
        elif argList!=None:
            # Code the constructor's arguments
            ### TODO: CHoose the best constructor and get modelParams to pass in instead of None.
            modelParams = self.codeGen.chooseCtorModelParams(LTSpec, argList, genericArgs)
            [CPL, paramTypeList] = self.codeGen.codeArgList(varName, argList, modelParams, genericArgs)
            if len(paramTypeList)==1:
                if not isinstance(paramTypeList[0], dict):
                    cdErr("\nPROBLEM: The return type of the parameter '", CPL, "' of "+varName+"(...) cannot be found and is needed. Try to define it.\n",   paramTypeList)
                RTSpec  = paramTypeList[0]
                rhsType = progSpec.fieldTypeKeyword(RTSpec)
                # TODO: Remove the 'True' and make this check object heirarchies or similar solution
                if True or not isinstance(rhsType, str) and cvrtType==rhsType[0]:
                    [leftMod, rightMod] = self.determinePtrConfigForNewVars(LTSpec, RTSpec, useCtor)
                    if(not useCtor): assignValue += " = "    # Use a copy constructor
                    if(isAllocated):
                        assignValue += self.codeXlatorAllocater(LTSpec, genericArgs)
                    assignValue += "(" + leftMod + CPL[1:-1] + rightMod + ")"
            if(assignValue==''):
                if(owner == 'their' or owner == 'our' or owner == 'my'): assignValue = ' = '+self.codeXlatorAllocater(LTSpec, genericArgs)+CPL
                else: assignValue = CPL # add "(x, y, z...) to make this into a constructor call.
        else: # If no value was given:
            if(progSpec.typeIsPointer(LTSpec)):
                if(isAllocated):
                    assignValue = " = " + self.codeGen.codeAllocater(LTSpec, argList, genericArgs)
                else:
                    assignValue = '= NULL'
            elif(progSpec.isNewContainerTempFunc(LTSpec)):
                assignValue = ''
            else:
                fieldTypeCat= progSpec.fieldsTypeCategory(LTSpec)
                if(fieldTypeCat=='int' or fieldTypeCat=='char' or fieldTypeCat=='double' or fieldTypeCat=='float'):
                    assignValue = ' = 0'
                elif(fieldTypeCat=='bool'):
                    assignValue = '= false'
        varDeclareStr= cvrtType + " " + varName + assignValue
        return(varDeclareStr)

    def codeIncrement(self, varName):
        return "++" + varName

    def codePostIncrement(self, varName):
        return varName + "++"

    def codePreIncrementExpr(self, varName):
        return "++" + varName

    def codePostIncrementExpr(self, varName):
        return varName + "++"

    def codeDecrement(self, varName):
        return "--" + varName

    def codePostDecrement(self, varName):
        return varName + "--"

    def codePreDecrementExpr(self, varName):
        return "--" + varName

    def codePostDecrementExpr(self, varName):
        return varName + "--"

    def codeVarFieldRHS_Str(self, fieldName, cvrtType, tSpec, argList, isAllocated, typeArgList, genericArgs):
        fieldValueText=""
        fieldOwner=progSpec.getOwner(tSpec)
        #TODO: make test case
        if argList!=None:
            if len(argList)==0: print("Error Parameter:",fieldName)
            if argList[-1] == "^&useCtor//8":
                del argList[-1]
            [CPL, paramTypeList] = self.codeGen.codeArgList(fieldName, argList, None, genericArgs)
            fieldValueText += CPL
        if isAllocated == True:
            fieldValueText = " = " + self.codeGen.codeAllocater(tSpec, argList, genericArgs)
        return fieldValueText

    def codeConstField_Str(self, convertedType, fieldName, fieldValueText, className, indent):
        if className=='GLOBAL':
            defn = indent + convertedType + ' ' + fieldName + fieldValueText +';\n';
            decl = ''
        else:
            defn = indent + convertedType + ' ' + fieldName +';\n'
            decl = convertedType[7:] + ' ' + progSpec.flattenObjectName(className) + "::"+ fieldName + fieldValueText +';\n\n'
        return [defn, decl]

    def codeVarField_Str(self, convertedType, tSpec, fieldName, fieldValueText, className, tags, typeArgList, indent):
        #TODO: make test case
        fieldOwner=progSpec.getOwner(tSpec)
        if fieldOwner=='we':
            defn = indent + convertedType + ' ' + fieldName +';\n'
            decl = convertedType[7:] + ' ' + progSpec.flattenObjectName(className) + "::"+ fieldName + fieldValueText +';\n\n'
        else:
            defn = indent + convertedType + ' ' + fieldName + fieldValueText +';\n'
            decl = ''
        return [defn, decl]

    ###################################################### CONSTRUCTORS
    def codeConstructor(self, className, ctorArgs, callSuper, ctorInit, funcBody):
        if callSuper != '':
            callSuper = ':' + callSuper
            if ctorInit != '':
                callSuper = callSuper + ', '
        elif ctorInit != '':
            ctorInit = ':' + ctorInit
        S = "    " + className + "(" + ctorArgs + ")" + callSuper + ctorInit +"{\n" + funcBody + "    };\n"
        return (S)

    def codeConstructors(self, className, ctorArgs, ctorOvrRide, ctorInit, copyCtorArgs, funcBody, callSuper):
        S = ''
        if ctorArgs != '' or funcBody!='':
            S += self.codeConstructor(className, ctorArgs, callSuper, ctorInit, funcBody)
      #  S += self.codeConstructor(className, '', callSuper, '', funcBody)
        return S

    def codeConstructorInit(self, fieldName, count, defaultVal):
        if (count > 0):
            return "," + fieldName+"("+" _"+fieldName+")"
        elif(count == 0):
            return fieldName+"("+" _"+fieldName+")"
        else:
            cdErr("Error in codeConstructorInit.")

    def codeConstructorArgText(self, argFieldName, count, argType, defaultVal):
        if defaultVal == "NULL":
            defaultVal = "0"
        if defaultVal != '':
            defaultVal = "=" + defaultVal
        return argType + "  _" +argFieldName + defaultVal

    def codeCopyConstructor(self, fieldName, isTemplateVar):
        return ""

    def codeConstructorCall(self, className):
        return '        INIT();\n'

    def codeSuperConstructorCall(self, parentClassName):
        return parentClassName+'()'

    def specialFunction(self, fieldName, classDef):
        if fieldName == "__plus": newFieldName = "operator+"
        elif fieldName == "__minus": newFieldName = "operator-"
        elif fieldName == "__times": newFieldName = "operator*"
        elif fieldName == "__divide": newFieldName = "operator/"
        elif fieldName == "__negate": newFieldName = "operator-"
        elif fieldName == "__plusEqual": newFieldName = "operator+="
        elif fieldName == "__lessThan": newFieldName = "operator<"
        elif fieldName == "__lessOrEq": newFieldName = "operator<="
        elif fieldName == "__greaterThan": newFieldName = "operator>"
        elif fieldName == "__greaterOrEq": newFieldName = "operator>="
        elif fieldName == "__isEqual": newFieldName = "operator=="
        elif fieldName == "__notEqual": newFieldName = "operator!="
        elif fieldName == "__inc": newFieldName = "operator++"
        elif fieldName == "__opAssign": newFieldName = "operator="
        elif fieldName == "__derefPtr": newFieldName = "operator*"
        elif fieldName == "__index": newFieldName = "operator[]"
        elif fieldName == "__opPtr": newFieldName = "operator->"
        else:  newFieldName = fieldName
        return newFieldName

    def codeFuncHeaderStr(self, className, fieldName, field, cvrtType, paramListText, localArgsAlloc, inheritMode, typeArgList, isNested, overRideOper, isStatic, indent):
        structCode=''; funcDefCode=''; globalFuncs='';
        tSpec        = progSpec.getTypeSpec(field)
        fTypeKW      = progSpec.fieldTypeKeyword(tSpec)
        fieldName    = field['fieldName']
        overRideOper = False
        if fieldName[0:2] == "__" and self.iteratorsUseOperators:
            sizeArgList  = len(progSpec.getParamList(field))
            fieldName    = self.specialFunction(fieldName, className)
            overRideOper = True
        if(className=='GLOBAL'):
            if fieldName=='main':
                if not isNested:funcDefCode += 'int main(int argc, char *argv[])'
                localArgsAlloc.append(['argc', {'owner':'me', 'fieldType':'int', 'arraySpec':None, 'paramList':None}])
                localArgsAlloc.append(['argv', {'owner':'their', 'fieldType':'char', 'arraySpec':None,'paramList':None}])  # TODO: Wrong. argv should be an array.
            else:
                if not isNested:globalFuncs += cvrtType +' ' + fieldName +"("+paramListText+")"
        else:
            typeArgList = progSpec.getTypeArgList(className)
            if(typeArgList != None):
                templateHeader = self.codeTemplateHeader(className, typeArgList) +"\n"
                className = className + self.codeTypeArgs(typeArgList)
            else:
                templateHeader = ""
            if overRideOper:
                if fieldName == "operator[]":
                    cvrtType += "&"
            if inheritMode=='normal' or inheritMode=='override':
                structCode += indent + cvrtType +' ' + fieldName +"("+paramListText+")";
                objPrefix = progSpec.flattenObjectName(className) +'::'
                if not isNested:funcDefCode += templateHeader + cvrtType +' ' + objPrefix + fieldName +"("+paramListText+")"
            elif inheritMode=='virtual':
                structCode += indent + 'virtual '+cvrtType +' ' + fieldName +"("+paramListText +")";
                objPrefix = progSpec.flattenObjectName(className) +'::'
                if not isNested:funcDefCode += templateHeader + cvrtType +' ' + objPrefix + fieldName +"("+paramListText+")"
            elif inheritMode=='pure-virtual':
                structCode +=  indent + 'virtual ' + cvrtType +' ' + fieldName +"("+paramListText +") = 0";
            else: cdErr("Invalid inherit mode found: "+inheritMode)
            if funcDefCode[:7]=="static ": funcDefCode=funcDefCode[7:]
            if not isNested:structCode += ';\n';
        return [structCode, funcDefCode, globalFuncs]

    def getVirtualFuncText(self, field):
        return ""

    def codeTypeArgs(self, typeArgList):
        typeArgsCode = "<"
        count = 0
        for typeArg in typeArgList:
            if(count>0):typeArgsCode+=", "
            typeArgsCode+=typeArg
            count+=1
        typeArgsCode+=">"
        return(typeArgsCode)

    def codeTemplateHeader(self, className, typeArgList):
        templateHeader = "\ntemplate<"
        count = 0
        for typeArg in typeArgList:
            if(count>0):templateHeader+=","
            templateHeader+="typename "+typeArg
            count+=1
        templateHeader+=">"
        return(templateHeader)

    def extraCodeForTopOfFuntion(self, paramList):
        return ''

    def codeSetBits(self, LHS_Left, LHS_FieldType, prefix, bitMask, RHS, rhsType):
        if (LHS_FieldType =='flag' ):
            return "SetFlagBit("+LHS_Left+"flags, "+prefix+bitMask+", "+ RHS + ");\n"
        elif (LHS_FieldType =='mode' ):
            return "SetModeBits("+LHS_Left+"flags, "+prefix+bitMask+", "+ RHS +");\n"

    def codeSwitchBreak(self, caseAction, indent):
        return indent+"    break;\n"

    def applyTypecast(self, typeInCodeDog, itemToAlterType):
        platformType = self.adjustBaseTypes(typeInCodeDog, None)
        return '('+platformType+')'+itemToAlterType;

    #######################################################
    def includeDirective(self, libHdr):
        if libHdr[0] == '"' or libHdr[0] == "'":
            S = '#include "'+libHdr[1:-1]+'"\n'
        else:
            S = '#include <'+libHdr+'>\n'
        return S

    def generateMainFunctionality(self, classes, tags):
        # TODO: Some deInitialize items should automatically run during abort().
        # TODO: System initCode should happen first in initialize, last in deinitialize.

        runCode = progSpec.fetchTagValue(tags, 'runCode')
        if runCode==None: runCode=""
        mainFuncCode="""
        me int32: main(me int32: argc, their char: argv ) <- {
            initialize(joinCmdStrings(argc, argv))
            """ + runCode + """
            deinitialize()
            endFunc()
        }

    """
        progSpec.addClass(classes[0], classes[1], 'GLOBAL', 'struct', 'SEQ',["//^", "Main class"])
        codeDogParser.AddToObjectFromText(classes[0], classes[1], progSpec.wrapFieldListInObjectDef('GLOBAL',  mainFuncCode ), "C++ main()")

    def __init__(self):
        print("INIT")
