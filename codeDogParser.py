# This module parses CodeDog syntax

from pprint import pprint
import os
import sys
import re
import progSpec
from progSpec import cdlog, cdErr, logLvl
from pyparsing import *
from timeit import default_timer as timer

ParserElement.enablePackrat()

def _supports_ansi_color(stream):
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("CLICOLOR_FORCE", "0") != "0":
        return True
    try:
        if not stream.isatty():
            return False
    except Exception:
        return False
    term = os.environ.get("TERM", "")
    if term.lower() == "dumb":
        return False
    return True

def _red_caret():
    if _supports_ansi_color(sys.stderr):
        return "\x1b[1;91m^\x1b[0m"
    return "^"

def _flag_enabled(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")

TRACE_PARSE_ALWAYS = _flag_enabled(os.environ.get("CODEDOG_TRACE_PARSE"))
SAVE_ERRFILE_ALWAYS = _flag_enabled(os.environ.get("CODEDOG_SAVE_ERRFILE"))
MACRO_CALL_NAME_PATTERN = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)\s*\(')

def install_furthest_path_tracer(root: ParserElement):
    stack = []  # frames: (expr_id, seq, label)
    best = {"loc": -1, "stack": [], "exc": None}
    visited = set()

    seq_counter = {}   # expr_id -> next seq
    open_frames = {}   # (expr_id, loc) -> list[(expr_id, seq)]

    def is_human(nm: str) -> bool:
        if not nm:
            return False
        noisy = ("{", "}", "(", ")", "[", "]", "W:", "Group:", "Suppress:", "Re:", "SkipTo:")
        return len(nm) <= 60 and not any(t in nm for t in noisy)

    def label(expr: ParserElement):
        nm = getattr(expr, "name", None)
        return nm if (nm and is_human(nm)) else None

    def push(expr, loc):
        lab = label(expr)
        if lab is None:
            return
        eid = id(expr)
        seq = seq_counter.get(eid, 0) + 1
        seq_counter[eid] = seq

        stack.append((eid, seq, lab))
        open_frames.setdefault((eid, loc), []).append((eid, seq))

    def pop(eid, loc):
        lst = open_frames.get((eid, loc))
        if not lst:
            return
        eid_seq = lst.pop()
        if not lst:
            open_frames.pop((eid, loc), None)

        _, seq = eid_seq
        for i in range(len(stack) - 1, -1, -1):
            feid, fseq, _ = stack[i]
            if feid == eid and fseq == seq:
                del stack[i]
                return

    def start_action(instring, loc, expr, *args):
        push(expr, loc)

    def success_action(instring, startloc, endloc, expr, toks, *args):
        eid = id(expr)
        pop(eid, startloc)

    def exception_action(instring, loc, expr, exc, *args):
        if loc > best["loc"]:
            best["loc"] = loc
            best["stack"] = [lab for (_eid, _seq, lab) in stack]
            lab = label(expr)
            if lab is not None:
                best["stack"].append(lab)
            best["exc"] = exc

        # best-effort unwind
        eid = id(expr)
        pop(eid, loc)

    def walk(e):
        if e is None or not isinstance(e, ParserElement):
            return
        eid = id(e)
        if eid in visited:
            return
        visited.add(eid)

        # IMPORTANT: no callDuringTry kwarg (not supported)
        e.setDebugActions(start_action, success_action, exception_action)

        for c in getattr(e, "exprs", None) or []:
            walk(c)
        child = getattr(e, "expr", None)
        if child is not None:
            walk(child)

    walk(root)
    return lambda: best



commentsToActivate = {}
ENABLE_BUILD_SPEC_LOGS = getattr(progSpec, "MaxLogLevelToShow", 1) >= 3
ENABLE_OBJ_PARSE_LOGS = getattr(progSpec, "MaxLogLevelToShow", 1) >= 3
ENABLE_FIELD_PARSE_LOGS = getattr(progSpec, "MaxLogLevelToShow", 1) >= 4

def logBSL(s, loc, toks):
    cdlog(3,"Parsing Tags...")

def logTags(s, loc, toks):
    global commentsToActivate
    for tagValue in toks:
        for tagList in tagValue:
            if tagList[0]=="commentsToActivate":
                for tag in tagList[1][0][1]:
                    tagName = tag[0][0]
                    commentsToActivate[tagName] = 'active'

def logObj(s, loc, toks):
    cdlog(3,"PARSED: {}".format(str(toks[0][0])+' ' + str(toks[0][1][0])))

def logFieldDef(s, loc, toks):
    cdlog(4,"Field: {}".format(str(toks)))

reservedWordSet = set([
    "and", "or", "true", "false",
    "if", "else", "but", "switch", "case", "default", "void",
    "while", "withEach", "where", "until",
    "protect", "do", "mode", "flag",
   # "Forward", "Backward", "Preorder", "Inorder", "Postorder", "BreadthFirst", "DF_Iterative",
   # "keys", "index", "iters", "key", "value", "entry", "index", "iter", "FILE",
   # "void", "bool", "int32", "int64", "double", "char", "uint32", "uint64", "string", "int",
    #"list", "opt", "map", "multimap", "tree", "graph", "iterableList",
    "const", "me", "my", "our", "their", "we", "id_our", "id_their",
    #"model", "struct", "string"
])

# # # # # # # # # # # # #   BNF Parser Productions for CodeDog syntax   # # # # # # # # # # # # #
#######################################   T A G S   A N D   B U I L D - S P E C S
docComment    = Group("/*^" + SkipTo("*/") + Suppress("*/") | "//^" + restOfLine)
identifier    = Word(alphanums + "_") .addCondition(lambda tokens: tokens[0] not in reservedWordSet, message="Reserved keyword used as identifier")
tagID         = identifier("tagID")
tagDefList    = Forward()
tagValue      = Forward()
fullFieldDef  = Forward()
tagMap        = Group('{' + tagDefList + '}')("tagMap")
tagList       = Group('[' + Group(Optional(delimitedList(Group(tagValue), ',')))("tagListContents") + ']')
backTickStr   = Suppress("`") + SkipTo("`") + Suppress("`")
tagValue    <<= Group((Suppress('<') + Group(fullFieldDef)("tagType") + Suppress('>')) | quotedString | backTickStr | Word(alphanums+'-*_./') | tagList | tagMap)("tagValue")
tagDef        = Group(tagID + Suppress("=") + tagValue)("tagDef*")
tagDefList  <<= Group(ZeroOrMore(tagDef))("tagDefList")
buildID       = identifier("buildID")
buildDefList  = Group(tagDefList)("buildDefList")
buildSpec     = Group(buildID + Suppress(":") + buildDefList + ";")("buildSpec")
buildSpecList = Group(OneOrMore(buildSpec))("buildSpecList")

#######################################   B A S I C   T Y P E S
expr      = Forward()
CID       = identifier("CID")
CIDList   = Group(delimitedList(CID, ','))("CIDList")
className = CID("className")
typeClassName = Combine(CID + ZeroOrMore(Literal(".") + CID))("className")
classSpec = Forward()
cppType   = Keyword("void") | Keyword("bool") | Keyword("int32") | Keyword("int64") | Keyword("double") | Keyword("char") | Keyword("uint32") | Keyword("uint64") | Keyword("string") | Keyword("int")
HexNums   = Combine((Literal("0X") | Literal("0x")) + Word(hexnums))
BinNums   = Combine((Literal("0B") | Literal("0b")) + Word("01"))
intNum    = HexNums | BinNums | Word(nums)
numRangeOp = Literal("..=") | Literal("..")
numRange  = Group(intNum + numRangeOp + intNum)("numRange")
varType   = numRange | cppType | classSpec
boolValue = Keyword("true") | Keyword("false")
floatNum  = Combine(intNum + "." + intNum)("floatNum")
value     = Forward()
listVal   = "[" + delimitedList(expr, ",") + "]"
strMapVal = "{" + delimitedList(quotedString + ":" + expr, ",")  + "}"
value   <<= boolValue | floatNum | intNum | quotedString | listVal | strMapVal

#######################################   E X P R E S S I O N S
arguments   = Forward()
owners      = Forward()
varSpec     = Group(Optional(owners)("owner") + varType("varType") )("varSpec")
varSpecList = Group(Optional(delimitedList(varSpec, ',')))("varSpecList")
typeArgList = Group(Literal("<") + CIDList + Literal(">"))("typeArgList")
reqTagList  = Group(Suppress(Literal("<")) + varSpecList + Optional(Literal(":")("optionalTag") + tagDefList) + Suppress(Literal(">")))("reqTagList")
classSpec <<= Group(typeClassName + Optional(reqTagList('reqTagList')))("classSpec")
classDefID  = Group(className + Optional(typeArgList))("classDefID")
arrayRef    = Group('[' + expr('startOffset') + Optional(( ':' + expr('endOffset')) | ('..' + expr('itemLength'))) + ']')
firstRefSeg = NotAny(owners) + Group((CID | arrayRef) + Optional(arguments))
secondRefSeg= Group((Suppress('.') + CID | arrayRef) + Optional(arguments))
varRef = Group(firstRefSeg + ZeroOrMore(secondRefSeg))
lValue = varRef("lValue")
incDecPrefixExpr  = Group((Literal("++") | Literal("--"))("incDecOp") + varRef("incDecTarget"))("incDecPrefixExpr")
incDecPostfixExpr = Group(varRef("incDecTarget") + (Literal("++") | Literal("--"))("incDecOp"))("incDecPostfixExpr")
factor = Group(
    value
    | ('(' + expr + ')')
    | ('!' + expr)
    | incDecPrefixExpr
    | ('-' + expr)
    | incDecPostfixExpr
    | varRef("varFuncRef")
)
term   = Group( factor + Optional(Group(OneOrMore(Group(oneOf('* / %') + factor )))))
plus   = Group( term  + Optional(Group(OneOrMore(Group(oneOf('+ -') + term )))))
comparison = Group( plus + Optional(Group(OneOrMore(Group(oneOf('< > <= >=') + ~FollowedBy("-") + plus )))))
isEQ   = Group( comparison  + Optional(Group(OneOrMore(Group(oneOf('== != === !==') + comparison )))))
iOr    = Group( isEQ  + Optional(Group(OneOrMore(Group('&' + isEQ )))))
xOr    = Group( iOr  + Optional(Group(OneOrMore(Group('^' + iOr )))))
bar    = Group( xOr  + Optional(Group(OneOrMore(Group('|' + xOr )))))
logAnd = Group( bar  + Optional(Group(OneOrMore(Group(Keyword('and') + bar )))))
logOr  = Group( logAnd + Optional(Group(OneOrMore(Group(Keyword('or') + logAnd )))))
expr <<= Group( logOr + Optional(Group(Group(Literal("<-")("assignAsExpr") + logOr ))))("expr")

swap   = Group(lValue + Literal("<->")("swapID") + lValue ("RightLValue"))("swap")
rValue = Group(expr)("rValue")
rValueVerbatim = Group("<%" + SkipTo("%>", include=True))("rValueVerbatim")
assign = lValue + Combine("<" + (Optional((Word(alphanums + '_') | '+' | ('-' + FollowedBy("-")) | '*' | '/' | '%' | '<<' | '>>' | '&' | '^' | '|')("assignTag"))) + "-")("assignID") + rValue
incDecPrefix  = Group((Literal("++") | Literal("--"))("op") + lValue("target"))("incDecPrefix")
incDecPostfix = Group(lValue("target") + (Literal("++") | Literal("--"))("op"))("incDecPostfix")
incDecAction  = Group(incDecPrefix("incDecPrefix") | incDecPostfix("incDecPostfix"))("incDecAction")
arguments <<= "(" + Optional(Group(delimitedList(rValue, ','))) + Suppress(")")
initArgs     = "{" + Optional(Group(delimitedList(rValue, ','))("initArgs")) + Suppress("}")

arraySpec = Forward()
paramSpec = Group(
    Optional(owners)("owner")
    + varType("varType")
    + Optional(arraySpec)("arraySpec")
    + Suppress(":")
    + CID("fieldName")
    + Optional(Literal("<-") - (rValue("defaultValue") | rValueVerbatim("defaultValueVerbatim")))
)("paramSpec")

paramSpecList = Group((delimitedList(paramSpec, ",")))("paramSpecList")

########################################   F U N C T I O N S
verbatim          = Group(Literal(r"<%") + SkipTo(r"%>", include=True))
fieldDef          = Forward()
commentedFieldDef = Group(Optional(docComment) + fieldDef('fieldDef'))
paramList         = Group(verbatim | Optional(paramSpecList))("paramList")
actionSeq         = Forward()
defaultCase       = Group(Keyword("default") + Suppress(":") + actionSeq("caseAction"))("defaultCase")
switchCase        = Group(Keyword("case") + OneOrMore(rValue + Suppress(":"))("caseValues") - actionSeq("caseAction"))
switchStmt        = Group(Keyword("switch")("switchStmt") - "(" - rValue("switchKey") - ")" - "{" - OneOrMore(switchCase)("switchCases") - Optional(defaultCase)("optionalDefaultCase") + "}")
conditionalAction = Forward()
conditionalAction <<= Group(
            Group(Keyword("if") - "(" + rValue("ifCondition") + ")" + actionSeq("ifBody"))("ifStatement")
            + Optional(Group((Keyword("else") | Keyword("but")) + Group(actionSeq | conditionalAction)("elseBody"))("optionalElse"))
        )("conditionalAction")
protectAction  = Group(Keyword("protect")("protectStmt") - "(" + rValue("mutex") + ")" + actionSeq("criticalSection"))("protectAction")

########################################   R E P E A T E D   A C T I O N S
# "withEach n in range startExpr ..= endExpr"
# "withEach item in container Backward iters: startExpr .. endExpr skip skipExpr take numExpr where (expr) until (expr) { actionSeq }"
traversalModes = Keyword("Forward") | Keyword("Backward") | Keyword("Preorder") | Keyword("Inorder") | Keyword("Postorder") | Keyword("BreadthFirst") | Keyword("DF_Iterative")
stringtraversalModes = Keyword("Forward") | Keyword("Backward") | "byte" | Keyword("rune") | Keyword("grapheme") | Keyword('line')("traversalMode")
rangeOp        = (Literal("..=")("inclusiveOp") | Literal("..")("exclusiveOp"))
rangeSpec      = Group(Optional(rValue)('rangeStart') + rangeOp - Optional(rValue)('rangeEnd'))("rangeSpec")
rangeSpecMode  = Keyword("keys") | Keyword("index") | Keyword("iters")
rangeClause    = Group(rangeSpecMode("rangeMode") + Suppress(':') + rangeSpec("range"))("rangeClause")
loopBindMode   = Keyword("key") | Keyword("value") | Keyword("entry")| Keyword("index") | Keyword("iter")
tupleBinding   = Group(  # (key, val)  binding. Mode is 'entry', associative containers only
    Suppress("(") + CID("keyName") + Suppress(",") + CID("valName") + Suppress(")")
)("tupleBinding")
singleBinding  = Group(Optional(loopBindMode)("axis") + CID("repName"))("singleBinding")
bindingSpec    = Group(tupleBinding | singleBinding)("bindingSpec")
whileSpec      = Group(Keyword('while') - '(' + expr + ')')
whileAction    = Group(whileSpec('whileSpec') + actionSeq)("whileAction")
fileSpec       = Group(Keyword('FILE')  + '(' + expr + ')')
numRangeSpec   = Group(
    Keyword("in")
    + Group(
        (
            (Keyword("range") + Optional(stringtraversalModes("traversalMode")))
            | (stringtraversalModes("traversalMode") + Keyword("range"))
        )
        + rValue('rangeStart')
        + rangeOp
        + rValue('rangeEnd')
    )("rangeSpec")
)("numRangeSpec").setName("numeric range spec")
traversalSpec  = Group( Keyword('in') + rValue("container") + Optional(traversalModes("traversalMode")) + Optional(rangeClause))("traversalSpec")
withEachAction = Group(
        Keyword("withEach")("repeatedActionID") - bindingSpec
            + (numRangeSpec('numRangeSpec') | traversalSpec('traversalSpec') | fileSpec('fileSpec')) 
            + Optional(Keyword("skip") - rValue("skipExpr"))
            + Optional(Keyword("take") - rValue("takeExpr"))
            + Optional(Keyword("where") - "(" + expr("whereExpr") + ")")
            + Optional(Keyword("until") - "(" + expr("untilExpr") + ")")
        + actionSeq)("withEachAction")

action         = Group((assign("assign") | swap('swap') | incDecAction("incDecAction") | varRef("funcCall") | fieldDef('fieldDef'))) + Optional(";").suppress()
actComment     = Group(Combine(r"//:"- Word(alphanums + r"/")("filterTag") + r"::")("actComment") + action)
actionSeq    <<= Group(Literal("{")("actSeqID") + (ZeroOrMore(switchStmt | conditionalAction | withEachAction | whileAction | protectAction | actionSeq | action | actComment))("actionList") + "}")("actionSeq").setName("loop body '{ ... }'")
funcBody       = Group(actionSeq | rValueVerbatim)("funcBody")

#########################################   F I E L D   D E S C R I P T I O N S
nameTypeArgList = Optional(typeArgList("nameTypeArgList"))
nameAndVal   = Group(
          (":" + CID("fieldName") + nameTypeArgList + "(" + paramList + Literal(")")('paramListTag') + Optional(Literal(":")("optionalTag").setName("tag or '<-'") + tagDefList) + "<-" - funcBody )         # Function Definition
        | (":" + CID("fieldName") + nameTypeArgList + Group(initArgs)("arguments"))
        | (":" + CID("fieldName") + nameTypeArgList + "<-" + (rValue("givenValue") | funcBody))
        | (":" + "<-" - (rValue("givenValue") | funcBody))
        | (":" + CID("fieldName") + nameTypeArgList + Optional("(" + paramList + Literal(")")('paramListTag')) - ~Word("{"))
        | (Literal("::")('allocDoubleColon') + CID("fieldName") + Group(initArgs)("arguments"))
        | (Literal("::")('allocDoubleColon') + CID("fieldName") + "<-" - (rValue("givenValue")))
        | (Literal("::")('deprecateDoubleColon') + CID("fieldName") + Group(arguments)("arguments"))# deprecated
        | (Literal("::")('allocDoubleColon') + CID("fieldName"))
    )("nameAndVal")
datastructID = Group(Keyword("list") | Keyword("opt") | Keyword("map") | Keyword("multimap") | Keyword("tree") | Keyword("graph") | Keyword("iterableList"))('datastructID')
arraySpec    = Group('[' + Optional(owners)('owner') + datastructID + Optional(Group(intNum | Optional(Group(owners)('IDXowner')) + varType('idxBaseType'))('indexType')) + ']')("arraySpec")
meOrMy       = Keyword("me") | Keyword("my")
modeSpec     = Optional(meOrMy)('owner') + Keyword("mode")("modeIndicator") - "[" - CIDList("modeList") + "]" + nameAndVal
altModeSpec  = Keyword("mode")("altModeIndicator") - "[" - Group(delimitedList(CID, ','))("altModeList") + "]"
flagDef      = Optional(meOrMy)('owner') + Keyword("flag")("flagIndicator") - nameAndVal
baseType     = cppType | numRange

#########################################   O B J E C T   D E S C R I P T I O N S
fieldDefs    = ZeroOrMore(commentedFieldDef)("fieldDefs")
SetFieldStmt = Group(Word(alphanums + "_.") + '=' + Word(alphanums + r"_. */+-(){}[]\|<>,./?`~@#$%^&*=:!'" + '"'))
coFactualEl  = Group("(" + Group(fieldDef + "<=>" + Group(OneOrMore(SetFieldStmt + Suppress(';'))))  + ")")("coFactualEl")
sequenceEl   = "{" - fieldDefs + "}"
alternateEl  = "[" - Group(OneOrMore((coFactualEl | fieldDef) + Optional("|").suppress()))("fieldDefs") + "]"
anonModel    = sequenceEl("sequenceEl") | alternateEl("alternateEl")
owners     <<= Keyword("const") | Keyword("me") | Keyword("my") | Keyword("our") | Keyword("their") | Keyword("we") | Keyword("id_our") | Keyword("id_their")
fullFieldDef <<= Optional('>')('isNext') + Optional(owners)('owner') + Group(baseType | altModeSpec | classSpec | Group(anonModel) | datastructID)('fieldType') + Optional(arraySpec) + Optional(nameAndVal)
fieldDef   <<= Group(flagDef('flagDef') | modeSpec('modeDef') | (quotedString('constStr') + Optional("[opt]") + Optional(":"+CID)) | intNum('constNum') | nameAndVal('nameVal') | fullFieldDef('fullFieldDef'))("fieldDef")

paramDef     = Group(flagDef('flagDef') | modeSpec('modeDef') | nameAndVal('nameVal'))
modelTypes   = (Keyword("model") | Keyword("struct") | Keyword("string") | Keyword("stream"))
classDef     = Group(modelTypes + classDefID + Optional(Literal(":")("optionalTag") + tagDefList) + (Keyword('auto') | anonModel))("classDef")
doPattern    = Group(Keyword("do") + classSpec + Suppress("(") + CIDList + Suppress(")"))("doPattern")
macroDef     = Group(Keyword("#define") + CID('macroName') + Suppress("(") + Optional(CIDList('macroArgs')) + Suppress(")") + Group("<%" + SkipTo("%>", include=True))("macroBody"))
classList    = Group(ZeroOrMore(docComment | classDef | doPattern | macroDef))("classList")

#########################################   P A R S E R   S T A R T   S Y M B O L
buildSpecListForParse = buildSpecList
if ENABLE_BUILD_SPEC_LOGS:
    buildSpecListForParse = buildSpecList.copy().set_parse_action(logBSL)
progSpecParser = Group(Optional(buildSpecListForParse) + tagDefList.set_parse_action(logTags) + classList)("progSpecParser")
libTagParser   = Group(Optional(buildSpecListForParse) + tagDefList.set_parse_action(logTags) + (modelTypes|Keyword("do")|Keyword("#define")|StringEnd()))("libTagParser")

if ENABLE_OBJ_PARSE_LOGS:
    classDef.set_parse_action(logObj)
if ENABLE_FIELD_PARSE_LOGS:
    fieldDef.set_parse_action(logFieldDef)

progSpecParser.setName("Proteus file")
sequenceEl.setName("sequenceEl")
fieldDef.setName("field definition")
rangeSpec.set_name("range specification (e.g., start..end)")
bindingSpec.set_name("loop binding (e.g., item or (key, val))")
traversalSpec.set_name("container traversal spec")
fileSpec.set_name("file specification")
withEachAction.set_name("withEach loop")
actionSeq.set_name("action sequence block")
conditionalAction.set_name("if/else conditional")
protectAction.set_name("protected block")
funcBody.set_name("function body")
classDef.set_name("class definition")
action.setName("action statement")
nameAndVal.setName("variable or function declaration")

################## parser metrics
parseTime = 0
macroSubTime = 0
macroSubCalls = 0
macroSubPasses = 0
macroRegexCache = {}

BUILTIN_MACROS = {
    'BlowPOP': {'ArgList': ['dummyArg'], 'Body': 'dummyArg'},
    'DESLASH': {'ArgList': ['dummyArg'], 'Body': 'dummyArg'},
}

def _saveErrFileMaybe(text):
    if SAVE_ERRFILE_ALWAYS:
        progSpec.saveTextToErrFile(text)

def _find_macro_calls_outside_defines(text, candidateNames):
    if not candidateNames:
        return set()
    candidateSet = set(candidateNames)
    calledNames = set()
    for line in text.splitlines():
        if line.lstrip().startswith("#define"):
            continue
        for match in MACRO_CALL_NAME_PATTERN.finditer(line):
            macroName = match.group(1)
            if macroName in candidateSet:
                calledNames.add(macroName)
    return calledNames

def _expand_macro_dependencies(seedNames, macroSpecMap):
    macroNames = set(macroSpecMap.keys())
    expandedNames = set(seedNames)
    pendingNames = list(seedNames)
    while pendingNames:
        macroName = pendingNames.pop()
        if macroName not in macroNames:
            continue
        macroBody = macroSpecMap[macroName]['Body']
        for match in MACRO_CALL_NAME_PATTERN.finditer(macroBody):
            depName = match.group(1)
            if depName in macroNames and depName not in expandedNames:
                expandedNames.add(depName)
                pendingNames.append(depName)
    return expandedNames

def _build_traced_prog_parser():
    buildSpecForTrace = buildSpecList
    if ENABLE_BUILD_SPEC_LOGS:
        buildSpecForTrace = buildSpecList.copy().setParseAction(logBSL)
    tracedParser = Group(
        Optional(buildSpecForTrace) + tagDefList.setParseAction(logTags) + classList
    )("progSpecParser").setName("Proteus file")
    return tracedParser, install_furthest_path_tracer(tracedParser)

# # # # # # # # # # # # #   E x t r a c t   P a r s e   R e s u l t s   # # # # # # # # # # # # #
def parseInput(inputStr, sourceLineMap=None):
    global parseTime
    cdlog(2, "Parsing build-specs...")
    _saveErrFileMaybe(inputStr)
    startTime = timer()
    get_best = None
    localResults = None
    try:
        if TRACE_PARSE_ALWAYS:
            tracedParser, get_best = _build_traced_prog_parser()
            localResults = tracedParser.parseString(inputStr, parseAll=True)
        else:
            localResults = progSpecParser.parseString(inputStr, parseAll=True)
        parseTime += timer()-startTime
        #print("P_TIME-a:",parseTime)
    except ParseBaseException as pe:
        parseTime += timer()-startTime
        best = {"stack": [], "exc": pe}
        if TRACE_PARSE_ALWAYS and get_best is not None:
            best = get_best()
        else:
            tracedParser, trace_get_best = _build_traced_prog_parser()
            try:
                tracedParser.parseString(inputStr, parseAll=True)
            except ParseBaseException:
                pass
            best = trace_get_best()

        # Trace the furthest failure
        # prefer the tracer’s exception if it captured something more specific
        b_exc = best["exc"] if best["exc"] else pe

        errExplaination = ""
        prevItem = None
        for n in best["stack"]:
            if n.startswith("Forward:"): continue
            if n == prevItem: continue
            prevItem = n
            errExplaination += "  - {}\n".format(n)
        lineNum = int(getattr(b_exc, "lineno", 1) or 1)
        pointerCol = max(1, int(getattr(b_exc, "column", 1) or 1))
        sourceLoc = progSpec.formatResolvedSourceLocation(sourceLineMap, lineNum, pointerCol)
        locationText = '    (at line:' + str(lineNum) + ', col:' + str(pointerCol) + ')'
        if sourceLoc != "":
            locationText += '  (source: ' + sourceLoc + ')'
        errExplaination += "\n{}".format(
            str(b_exc.line)
            + "\n"
            + " " * (pointerCol - 1)
            + _red_caret()
            + "\n"
            + b_exc.msg + ", found "+ (repr(b_exc.found) if hasattr(b_exc, "found") else "end of input")
            + locationText
        )
        if SAVE_ERRFILE_ALWAYS or progSpec.shouldWriteErrFileForVirtualLine(sourceLineMap, lineNum):
            progSpec.saveTextToErrFile(inputStr)
        cdErr( "While parsing:\n{}".format( errExplaination), False)
    return localResults

autoClassNameIdx = 1
def extractTagDefs(tagResults):
    global autoClassNameIdx
    localTagStore = {}

    for tagSpec in tagResults:
        tagVal = tagSpec.tagValue[0]
        if ((not isinstance(tagVal, str)) and len(tagVal)>=2):
            if(tagVal.tagListContents): #tagVal is tagList
                tagValues=[]
                for each in tagVal.tagListContents:
                    tagValues.append(each.tagValue[0])
            elif(tagVal.tagDefList):   #tagVal is tagMap
                tagValues=extractTagDefs(tagVal.tagDefList)
            elif("tagType" in tagVal):
                autoClassName = "autoClass" + str(autoClassNameIdx)
                autoClassNameIdx += 1
                tagValues=packFieldDef(tagVal, autoClassName, '')
            else:   #tagVal is an empty parseResult
                tagValues = []
            tagVal=tagValues
        # Remove quotes
        elif (len(tagVal)>=2 and (tagVal[0] == '"' or tagVal[0] == "'") and (tagVal[0]==tagVal[-1])):
            tagVal = tagVal[1:-1]
        #print(tagSpec.tagID, " is ", tagVal)
        localTagStore[tagSpec.tagID] = tagVal
    return localTagStore

def extractTypeArgList(typeArgList):
    localListStore = []
    for typeArg in typeArgList[1]:
        localListStore.append(typeArg)
    return localListStore

def _extractReqTagTypeKeyword(reqTag):
    rawVarType = reqTag['varType'][0]
    if isinstance(rawVarType, str):
        return rawVarType

    # varType for class refs can be nested ParseResults wrappers
    # (e.g. [[['INK_Image']]]). Normalize to the canonical class key.
    normalizedType = progSpec.normalizeClassNameKey(rawVarType)
    if isinstance(normalizedType, str):
        return normalizedType

    return rawVarType[0]

def _extractReqTagConstraints(reqTagList):
    if reqTagList and "optionalTag" in reqTagList and reqTagList.optionalTag:
        return extractTagDefs(reqTagList.tagDefList)
    return None

nameIDX=1
def packParamSpec(paramSpec, className, indent):
    """Convert parsed paramSpec into a packed *parameter* structure.

    IMPORTANT: This is *not* a fieldDef. Keeping params distinct avoids the old
    "parameter-as-fieldDef" confusion and prevents accidental acceptance of
    function definitions as parameter specifications.
    """

    owner = paramSpec.owner if paramSpec.owner else 'me'
    arraySpec = paramSpec.arraySpec if "arraySpec" in paramSpec and paramSpec.arraySpec else None

    fieldType = None
    packedTArgList = None
    packedReqTags = None
    if paramSpec.varType:
        fieldType = paramSpec.varType[0]
        if not isinstance(fieldType, str) and 'reqTagList' in fieldType:
            reqTagList = fieldType['reqTagList']
            packedReqTags = _extractReqTagConstraints(reqTagList)
            packedTArgList = []
            for reqTag in reqTagList[0]:
                reqTagVarType = _extractReqTagTypeKeyword(reqTag)
                reqTagOwner = 'me'
                if 'owner' in reqTag:
                    reqTagOwner = reqTag['owner']
                packedTArgList.append({'tArgOwner': reqTagOwner, 'tArgType': reqTagVarType})
            # Preserve existing convention used by packFieldDef
            fieldType=[fieldType[0],packedTArgList]

    fieldName = paramSpec.fieldName if "fieldName" in paramSpec else None

    defaultValue = None
    if "defaultValue" in paramSpec and paramSpec.defaultValue:
        defaultValue = paramSpec.defaultValue
    elif "defaultValueVerbatim" in paramSpec and paramSpec.defaultValueVerbatim:
        # store verbatim text in the same two-element shape used elsewhere
        defaultValue = ['', paramSpec.defaultValueVerbatim[1]]

    packedParam = progSpec.packParamSpec(owner, fieldType, arraySpec, packedTArgList, fieldName, defaultValue)
    if packedReqTags != None:
        packedParam['typeSpec']['reqTags'] = packedReqTags
    return packedParam

def packFieldDef(fieldResult, className, indent, comment=None):
    global nameIDX
    #  ['(', [['>', 'me', ['CID'], [':', 'tag']], '<=>', [[[['hasTag']], '=', [[[[[[[['54321'], []], []], []], []], []], []]]]]], ')']
    coFactuals=None
    if fieldResult[0]=='(':             # Reorganize Cofactuals if they are here
        coFactuals = fieldResult[1][2]
        fieldResult= fieldResult[1][0]

    fieldDef={}
    paramList=[]
    argList=[]
    innerDefs=[]
    optionalTags=None
    nameTypeArgs=None
    isNext=False;
    if(fieldResult.isNext): isNext=True
    if(fieldResult.owner): owner=fieldResult.owner;
    else: owner='me';
    isAllocated = False
    hasFuncBody = False
    packedTArgList = None
    packedReqTags = None

    if(fieldResult.fieldType):
        fieldType=fieldResult.fieldType[0];
        if not isinstance(fieldType, str):
            if 'reqTagList' in fieldType:
                reqTagList = fieldType['reqTagList']
                packedReqTags = _extractReqTagConstraints(reqTagList)
                packedTArgList = []
                for reqTag in reqTagList[0]:
                    reqTagVarType = _extractReqTagTypeKeyword(reqTag)
                    reqTagOwner = 'me'
                    if 'owner' in reqTag: reqTagOwner = reqTag['owner']
                    packedReqTag={'tArgOwner': reqTagOwner, 'tArgType': reqTagVarType}
                    packedTArgList.append(packedReqTag)
                fieldType=[fieldType[0],packedTArgList]
            if(fieldType[0]=='[' or fieldType[0]=='{'):
                if   fieldType[0]=='{': fieldList=fieldType[1:-1]
                elif fieldType[0]=='[': fieldList=fieldType[1]
                for innerField in fieldList:
                    innerFieldDef=packFieldDef(innerField, className, indent+'    ')
                    innerDefs.append(innerFieldDef)
                #print("FIELDTYPE is an inline SEQ or ALT:",innerFieldDef)
    else: fieldType=None;

    isAContainer = False
    if(fieldResult.arraySpec):
        arraySpec=fieldResult.arraySpec
        isAContainer = True
        print("         ****Deprecated ArraySpec found: ", arraySpec)
    else: arraySpec=None

    varOwner = owner
    if isAContainer:
        if "owner" in arraySpec:
            varOwner = arraySpec['owner']
        else: varOwner = 'me'

    if(fieldResult.nameAndVal):
        nameAndVal = fieldResult.nameAndVal
        #print("nameAndVal = ", nameAndVal.dump())

        if(nameAndVal.fieldName):
            fieldName = nameAndVal.fieldName
            #print("FIELD NAME", fieldName)
        else: fieldName=None;

        if "nameTypeArgList" in nameAndVal and nameAndVal.nameTypeArgList:
            nameTypeArgs = extractTypeArgList(nameAndVal.nameTypeArgList)

        if(nameAndVal.allocDoubleColon):
            if varOwner == 'me' or varOwner == 'we':
                print("Error: unable to allocate variable with owner me or we: ", fieldName)
                exit(1)
            else: isAllocated = True

        if(nameAndVal.givenValue):
            givenValue = nameAndVal.givenValue
        elif(nameAndVal.funcBody):
            [funcBodyOut, funcTextVerbatim] = extractFuncBody(fieldName, nameAndVal.funcBody)
            givenValue=[funcBodyOut, funcTextVerbatim]
            hasFuncBody = True
            #print("\n\n[funcBodyOut, funcTextVerbatim] ", givenValue)
        elif(nameAndVal.rValueVerbatim):
            givenValue = ['', nameAndVal.rValueVerbatim[1]]
        else: givenValue = None;

        if(nameAndVal.paramListTag):
            # nameAndVal.paramList can be either:
            #  1) verbatim  -> tokens start with "<%"
            #  2) paramSpecList

            # Case 1: verbatim inside the parens
            if len(nameAndVal.paramList) > 0 and nameAndVal.paramList[0] == "<%":
                paramList = nameAndVal.paramList.asList()

            # Case 2: paramSpecList
            elif "paramSpecList" in nameAndVal.paramList and nameAndVal.paramList.paramSpecList:
                for argSpec in nameAndVal.paramList.paramSpecList:
                    # Skip empty ParseResults just in case
                    if len(argSpec) == 0:
                        continue
                    paramList.append(packParamSpec(argSpec, className, indent + "    "))

            if len(paramList) == 0: paramList = []

        else: paramList=None;

        if 'arguments' in nameAndVal:
            if('deprecateDoubleColon'in nameAndVal):
                print("            ***deprecated doubleColon in nameAndVal at: ", fieldName)
                exit(1)

            if(str(nameAndVal.arguments)=="['(']"): parsedArgs={}
            else: parsedArgs=nameAndVal.arguments[1]
            for arg in parsedArgs:
                argList.append(arg)
            if(isAllocated==False):     # use a constructor instead of assignment
                argList.append("^&useCtor//8")
        else: argList=None

        if(nameAndVal.optionalTag): optionalTags=extractTagDefs(nameAndVal.tagDefList)
    else:
        givenValue = None;
        fieldName=None;

    if(fieldResult.flagDef):
        cdlog(3,"FLAG: {}".format(fieldResult))
        if(arraySpec): cdErr("Lists of flags are not allowed")
        fieldDef=progSpec.packField(className, False, owner, 'flag', arraySpec, packedTArgList, fieldName, None, argList, givenValue, isAllocated, hasFuncBody)
    elif(fieldResult.modeDef):
        cdlog(3,"MODE: {}".format(fieldResult))
        modeList=fieldResult.modeList
        if(arraySpec): cdErr("Lists of modes are not allowed")
        fieldDef=progSpec.packField(className, False, owner, 'mode', arraySpec, packedTArgList, fieldName, None, argList, givenValue, isAllocated, hasFuncBody)
        fieldDef['typeSpec']['enumList']=modeList
    elif(fieldResult.constStr):
        if fieldName==None: fieldName="constStr"+str(nameIDX); nameIDX+=1;
        if(len(fieldResult)>1 and fieldResult[1]=='[opt]'):
            arraySpec={'datastructID': 'opt'};
            if(len(fieldResult)>3 and fieldResult[3]!=''):
                fieldName=fieldResult[3]
        givenValue = fieldResult.constStr[1:-1]
        fieldDef=progSpec.packField(className, True, 'const', 'string', arraySpec, packedTArgList, fieldName, None, argList, givenValue, isAllocated, hasFuncBody)
    elif(fieldResult.constNum):
        cdlog(3,"CONST Num: {}".format(fieldResult))
        if fieldName==None: fieldName="constNum"+str(nameIDX); nameIDX+=1;
        fieldDef=progSpec.packField(className, True, 'const', 'int', arraySpec, packedTArgList, fieldName, None, argList, givenValue, isAllocated, hasFuncBody)
    elif(fieldResult.nameVal):
        cdlog(3,"NameAndVal: {}".format(fieldResult))
        fieldDef=progSpec.packField(className, None, None, None, arraySpec, packedTArgList, fieldName, paramList, argList, givenValue, isAllocated, hasFuncBody)
    elif(fieldResult.fullFieldDef):
        fieldTypeStr=str(fieldType)[:50]
        cdlog(3,"FULL FIELD: {}".format(str([isNext, owner, fieldTypeStr+'... ', arraySpec, packedTArgList, fieldName])))
        fieldDef=progSpec.packField(className, isNext, owner, fieldType, arraySpec, packedTArgList, fieldName, paramList, argList, givenValue, isAllocated, hasFuncBody)
    else: cdErr("Error in packing FieldDefs: {}".format(fieldResult))
    if len(innerDefs)>0:   fieldDef['innerDefs']  = innerDefs
    if coFactuals!=None:   fieldDef['coFactuals'] = coFactuals
    if optionalTags!=None: fieldDef['tags']       = optionalTags
    if nameTypeArgs!=None: fieldDef['nameTypeArgs'] = nameTypeArgs
    if packedReqTags!=None: fieldDef['typeSpec']['reqTags'] = packedReqTags
    if comment!=None:      fieldDef['comment']    = comment
    return fieldDef

def parseResultsToListOfParseResults(parseSegment):
    """This splits a ParseResults into a list of the top level ParseResults
    """
    myList = []
    for seg in parseSegment:
        if "__len__" in seg and len(seg) > 0 and isinstance(seg[0], (list, ParseResults)):
            myList.append(seg)
        else:
            myList.append(seg)
    return myList

def extractActItem(funcName, actionItem):
    global funcsCalled
    global commentsToActivate
    thisActionItem=None
    if actionItem.fieldDef:
        thisActionItem = {'typeOfAction':"newVar", 'fieldDef':packFieldDef(actionItem.fieldDef, '', '    LOCAL:')}
    elif actionItem.switchStmt:
        switchKey = actionItem.switchKey
        switchCases = actionItem.switchCases
        defaultCaseAction = None
        if actionItem.optionalDefaultCase:
            defaultCaseAction = extractActSeq(funcName, actionItem.defaultCase.caseAction)
        casesList=[]
        for sCase in switchCases:
            caseVals = []
            for cVal in sCase.caseValues:
                caseVals.append(cVal)
            CaseActSeq = extractActSeq(funcName, sCase.caseAction)
            casesList.append([caseVals, CaseActSeq])

        thisActionItem = {'typeOfAction':'switchStmt', 'switchKey':switchKey, 'switchCases':casesList, 'defaultCase':defaultCaseAction}
    elif actionItem.ifStatement:    # Conditional
        ifCondition = actionItem.ifStatement.ifCondition
        IfBodyIn = actionItem.ifStatement.ifBody
        ifBodyOut = extractActSeq(funcName, IfBodyIn)
        elseBodyOut = {}
        if (actionItem.optionalElse):
            elseBodyIn = actionItem.optionalElse.elseBody
            if (elseBodyIn.conditionalAction):
                elseBodyOut = ['if' , [extractActItem(funcName, elseBodyIn.conditionalAction)] ]
            elif (elseBodyIn.actionSeq):
                elseBodyOut = ['action', extractActItem(funcName, elseBodyIn.actionSeq)]

        thisActionItem = {'typeOfAction':"conditional", 'ifCondition':ifCondition, 'ifBody':ifBodyOut, 'elseBody':elseBodyOut}
    elif "whileSpec" in actionItem and actionItem.whileSpec:
        # WHILE
        whileSpec = actionItem.whileSpec
        bodyOut = extractActSeq(funcName, actionItem.actionSeq)
        thisActionItem = {
            'typeOfAction': "repetition",
            'kind': "while",
            'whileSpec': whileSpec,
            'body': bodyOut,
        }

    elif "repeatedActionID" in actionItem and actionItem.repeatedActionID:
        # withEach
        bodyOut = extractActSeq(funcName, actionItem.actionSeq)

        # ---- bindingSpec ----
        bs = actionItem.bindingSpec
        if "tupleBinding" in bs and bs.tupleBinding:
            binding = {
                "kind": "tuple",
                "keyName": bs.tupleBinding.keyName,
                "valName": bs.tupleBinding.valName,
                "axis": "entry",  # implied
            }
        else:
            axis = bs.singleBinding.axis if "axis" in bs.singleBinding and bs.singleBinding.axis else None
            binding = {
                "kind": "single",
                "name": bs.singleBinding.repName,
                "axis": axis,
            }

        # ---- source ----
        if actionItem.numRangeSpec:
            rangeSpec = actionItem.numRangeSpec.rangeSpec
            source = {
                "kind": "numRange",
                "rangeSpec": rangeSpec,
            }
        elif actionItem.traversalSpec:
            ts = actionItem.traversalSpec

            rangeClause = None
            if ts.rangeClause:
                rangeSpec = ts.rangeClause.range
                rangeClause = {
                    "mode": ts.rangeClause.rangeMode,  # keys/index/iters
                    "range": rangeSpec,
                }

            source = {
                "kind": "traversal",
                "container": ts.container,
                "traversalMode": (ts.traversalMode if ts.traversalMode else None),
                "rangeClause": rangeClause,
            }
        elif actionItem.fileSpec:
            source = {
                "kind": "file",
                "fileSpec": actionItem.fileSpec,
            }
        else:
            source = {"kind": "unknown"}

        # ---- modifiers ----
        mods = {
            "skipExpr":  (actionItem.skipExpr if actionItem.skipExpr else None),
            "takeExpr":  (actionItem.takeExpr if actionItem.takeExpr else None),
            "whereExpr": (actionItem.whereExpr if actionItem.whereExpr else None),
            "untilExpr": (actionItem.untilExpr if actionItem.untilExpr else None),
        }

        thisActionItem = {
            'typeOfAction': "repetition",
            'kind': "withEach",
            'binding': binding,
            'source': source,
            'mods': mods,
            'body': bodyOut,
        }

    elif actionItem.actSeqID:
        actionListIn = actionItem
        actionListOut = extractActSeq(funcName, actionListIn)
        thisActionItem = {'typeOfAction':"actionSeq", 'actionList':actionListOut}
    # Increment / decrement action
    elif actionItem.incDecAction:
        incDecSpec = actionItem.incDecAction
        incDecItem = None
        position = None
        if "incDecPrefix" in incDecSpec and incDecSpec.incDecPrefix:
            incDecItem = incDecSpec.incDecPrefix
            position = "prefix"
        elif "incDecPostfix" in incDecSpec and incDecSpec.incDecPostfix:
            incDecItem = incDecSpec.incDecPostfix
            position = "postfix"

        if incDecItem == None:
            cdErr("Invalid increment/decrement action: {}".format(incDecSpec))

        op = incDecItem.op
        if not isinstance(op, str):
            op = op[0]
        target = parseResultsToListOfParseResults(incDecItem.target)

        thisActionItem = {
            'typeOfAction': "incDec",
            'target': target,
            'op': op,
            'position': position,
        }
    # Assign
    elif (actionItem.assign):
        RHS = parseResultsToListOfParseResults(actionItem.rValue)
        LHS = parseResultsToListOfParseResults(actionItem.lValue)
        assignTag = ''
        if (actionItem.assignID[0] != '<-'): # e.g.: A <+- B
            if not isinstance(actionItem.assignID, str): # e.g., A <+- B, assignID is ['<+-']
                assignTag = actionItem.assignID.assignTag
                if not isinstance(assignTag, str): # e.g., A <deep- B, assignTag is ['deep']
                    assignTag = assignTag[0]

        #print(RHS, LHS)
        thisActionItem = {'typeOfAction':"assign", 'LHS':LHS, 'RHS':RHS, 'assignTag':assignTag}
    # Swap
    elif (actionItem.swap):
        print("swap: ", actionItem[0][0][0])
        RHS = actionItem[0][2][0]
        LHS = actionItem[0][0][0]
        thisActionItem = {'typeOfAction':"swap", 'LHS':LHS, 'RHS':RHS}
    # Function Call
    elif actionItem.funcCall:
        calledFunc = actionItem.funcCall

        # Verify that calledFunc is a function and error out if not. (The last segment should have '(' as its second item.)
        calledFuncLastSegment = calledFunc[-1]
        if len(calledFuncLastSegment)<2 or calledFuncLastSegment[1] != '(':
            cdErr("Expected a function, not a variable: {}".format(calledFuncLastSegment))
        thisActionItem = {'typeOfAction':"funcCall", 'calledFunc':calledFunc}

        calledFuncName = calledFuncLastSegment[0]
        if(len(calledFuncLastSegment)<=2): calledFuncParams=[]
        else:
            calledFuncParams = calledFuncLastSegment[2]

        progSpec.appendToFuncsCalled(calledFuncName, calledFuncParams)
# Function Call
    elif actionItem.protectStmt:
        protectStmt     = actionItem.protectStmt
        mutex           = actionItem.mutex
        critSectionIn   = actionItem.criticalSection
        critSectionOut  = extractActSeq(funcName, critSectionIn)
        thisActionItem = {'typeOfAction':"protect", 'mutex':mutex, 'criticalSection':critSectionOut}
    elif actionItem.actComment:
        filterTag = actionItem.actComment.filterTag
        for tag in commentsToActivate:
            if tag[-1]=="/":
                filterCpy = filterTag+"/"
                if tag == filterCpy[0:len(tag)]:
                    thisActionItem = extractActItem(funcName, actionItem[1])
                    break
            elif filterTag==tag:
                thisActionItem = extractActItem(funcName, actionItem[1])
                break
    else:
        cdErr("problem in extractActItem: actionItem:".format(pprint(actionItem)))
        exit(1)
    return thisActionItem

def extractActSeq(funcName, childActSeq):
    actionList = childActSeq.actionList
    actSeq = []
    for actionItem in actionList:
        thisActionItem = extractActItem(funcName, actionItem)
        if thisActionItem!=None: actSeq.append(thisActionItem)
    return actSeq

def extractFuncBody(funcName, funcBodyIn):
    '''Extract body of funcName (str) from funcBodyIn (parseResults)

    Returns two values: funcBodyOut for CodeDog defined body & funcTextVerbatim for verbatim text.
    If body is verbatim: funcBodyOut is an empty string, funcTextVerbatim is a string
    If body is CodeDog: funcBodyOut is a list of stuff, funcTextVerbatim is an empty string
    '''
    if funcBodyIn.rValueVerbatim:
        funcBodyOut = ""
        funcTextVerbatim = funcBodyIn.rValueVerbatim[1] # opening and closing verbatim symbols are indices 0 and 2
    elif funcBodyIn.actionSeq:
        funcBodyOut = extractActSeq(funcName, funcBodyIn.actionSeq)
        funcTextVerbatim = ""
    else:
        cdErr("problem in extractFuncBody: funcBodyIn has no rValueVerbatim or actionSeq")
        exit(1)
    return funcBodyOut, funcTextVerbatim

def extractFieldDefs(ProgSpec, className, stateType, fieldResults, libName=None):
    cdlog(logLvl(), "EXTRACTING {}".format(className))
    for fieldResult in fieldResults:
        comment = None
        if(fieldResult[0][0]=='/*^' or fieldResult[0][0]=='//^' ): comment = fieldResult[0]
        fieldDef=packFieldDef(fieldResult.fieldDef, className, '', comment)
        if libName != None:
            fieldDef['libName'] = libName
            fieldDef['libLevel'] = progSpec.getLibLevel(libName)
        progSpec.addField(ProgSpec, className, stateType, fieldDef)

def extractBuildSpecs(buildSpecResults):    # buildSpecResults is sometimes a parseResult, often an empty string
    resultOfExtractBuildSpecs = []
    #print("buildSpecResults: ", buildSpecResults)
    if (len(buildSpecResults)==0):
        return resultOfExtractBuildSpecs
    else:
        for each_buildSpec in buildSpecResults:
            # If this doesn't loop when expected, it may be a result of a ZeroOrMore/deLimitedList call in parser
            # chain of buildSpec without trailing * in name, causing each new builSpec to overwrite previous value.
            # Or it may be that another loop is needed over contents of tagDefList
            spec = [each_buildSpec.buildID, extractTagDefs(each_buildSpec.buildDefList.tagDefList)]
            resultOfExtractBuildSpecs.append(spec)
    return resultOfExtractBuildSpecs

def extractObjectSpecs(ProgSpec, classNames, spec, stateType,description, comments):
    className=spec.classDefID[0]
    configType="unknown"
    if(spec.sequenceEl): configType="SEQ"
    elif(spec.alternateEl):configType="ALT"
    ###########Grab optional Object Tags
    if 'tagDefList' in spec:  #change so it generates an empty one if no field defs
        #print("spec.tagDefList = ",spec.tagDefList)
        objTags = extractTagDefs(spec.tagDefList)
    else: objTags = {}
    taggedName = progSpec.addClass(ProgSpec, classNames, className, stateType, configType,description, comments)
    progSpec.addObjTags(ProgSpec, className, stateType, objTags)
    extractFieldDefs(ProgSpec, className, stateType, spec.fieldDefs, description)
    ############Grab optional typeArgList
    if 'typeArgList' in spec[1]:
        typeArgList = extractTypeArgList(spec[1].typeArgList)
        progSpec.addTypeArgList(className, typeArgList)
    return taggedName

def extractPatternSpecs(ProgSpec, classNames, spec):
    patternName=spec.classSpec[0]
    if isinstance(patternName, (ParseResults, list, tuple)) and len(patternName) == 1 and isinstance(patternName[0], str):
        patternName = patternName[0]
    patternArgWords=spec.CIDList
    progSpec.addPattern(ProgSpec, classNames, patternName, patternArgWords)
    return

def extractMacroSpec(macroDefs, spec, comments):
    MacroName=spec.macroName
    if 'macroArgs' in spec: MacroArgs=spec.macroArgs
    else: MacroArgs=[]
    MacroBody=spec.macroBody[1]
    macroDefs[MacroName] = {'ArgList':MacroArgs,  'Body':MacroBody}

def extractMacroDefs(macroDefMap, inputString):
    global parseTime
    macroDefs = re.findall('#define.*%>', inputString)
    for macroStr in macroDefs:
        try:
            startTime = timer()
            localResults = macroDef.parseString(macroStr, parseAll = True)
            parseTime += timer()-startTime
            #print("P_TIME-b:",parseTime, "   MACRO:",macroStr)
        except ParseException as pe:
            cdErr("Error Extracting Macro: {} In: {}".format(pe, macroStr))
            exit(1)
        extractMacroSpec(macroDefMap, localResults[0], ["//^", ""])

def isCID(ch):
    return (ch.isalnum() or ch=='_')

def BlowPOPMacro(replacement):
    updatedStr = ""
    scanMode='identifier'
    for ch in replacement:
        if scanMode=='identifier':
            if isCID(ch):
                updatedStr += ch
            else:
                updatedStr += ' + "'+ch
                scanMode='filler'
        elif scanMode=='filler':
            if not (ch.isalpha() or ch=='_'):
                updatedStr += ch
            else:
                updatedStr += '" + '+ch
                scanMode='identifier'
    if scanMode=='filler':
        updatedStr+='" '
    return updatedStr

def deSlashMacro(replacement):
    return replacement.replace('/', '_')

def findMacroEnd(inputString, StartPosOfParens):
    nestLvl=0
    if(inputString[StartPosOfParens] != '('): cdErr("NO PAREN!"); exit(2);
    ISLen=len(inputString)
    for pos in range(StartPosOfParens, ISLen):
        ch = inputString[pos]
        if ch=='(': nestLvl+=1
        if ch==')': nestLvl-=1
        if nestLvl==0:
            #print("MACRO-ARGS:", inputString[StartPosOfParens:pos+1])
            return pos+1
    return -1

def doMacroSubstitutions(macros, inputString):
    global macroSubTime, macroSubCalls, macroSubPasses, macroRegexCache
    macroSubCalls += 1
    activeMacroSpecs = dict(macros)
    activeMacroSpecs.update(BUILTIN_MACROS)
    seedMacroNames = _find_macro_calls_outside_defines(inputString, activeMacroSpecs.keys())
    if not seedMacroNames:
        return inputString

    startTime = timer()
    macroNames = sorted(_expand_macro_dependencies(seedMacroNames, activeMacroSpecs), key=len, reverse=True)
    patternKey = tuple(macroNames)
    if patternKey in macroRegexCache:
        macroRefPattern = macroRegexCache[patternKey]
    else:
        macroRefPattern = re.compile(
            r'(?<!#define)([^a-zA-Z0-9_]+)(' + "|".join(re.escape(name) for name in macroNames) + r')(\s*)\('
        )
        macroRegexCache[patternKey] = macroRefPattern

    subsWereMade=True
    while(subsWereMade ==True):
        macroSubPasses += 1
        subsWereMade=False
        newString=''
        currentPos=0
        for match in macroRefPattern.finditer(inputString):
            macroStart = match.start()+len(match.group(1))
            if macroStart < currentPos:
                continue
            thisMacro = match.group(2)
            macroSpec = activeMacroSpecs[thisMacro]
            #print("     %s: %s %s" % (match.start(), match.group(1), match.group(2)))
            newText=macroSpec['Body']
            #print("     START TEXT:", newText)
            StartPosOfParens = match.end()-1
            EndPos=findMacroEnd(inputString, StartPosOfParens)
            if EndPos==-1: print("\nERROR: Parentheses problem in macro", thisMacro, "\n"); exit(2);
            paramStr=inputString[StartPosOfParens+1 : EndPos-1]
            params=paramStr.split(',')
            #print('     PARAMS:', params)
            idx=0;
            numMacroArgs = len(macroSpec['ArgList'])
            if((numMacroArgs>0 and numMacroArgs != len(params)) or (numMacroArgs==0 and len(params)!=1)):
                cdErr("The macro {} has {} parameters, but is called with {}.".format(thisMacro, len(macroSpec['ArgList']), len(params)))
            for arg in macroSpec['ArgList']:
                #print("   SUBS:", arg, ', ', params[idx], ', ', thisMacro)
                replacement=params[idx]
                if thisMacro=='BlowPOP':
                    replacement=BlowPOPMacro(replacement)
                elif thisMacro=='DESLASH':
                    replacement=deSlashMacro(replacement)
                newText=newText.replace(arg, replacement)
                idx+=1
            #print("     NEW TEXT:", newText)
            newString += inputString[currentPos:macroStart]+ newText
            currentPos=EndPos
            subsWereMade=True
        if subsWereMade:
            newString+=inputString[currentPos:]
            inputString=newString
    #print("     RETURN STRING:[", inputString, ']')
    # Last, replace the text into inputString
    elapsed = timer()-startTime
    macroSubTime += elapsed
    if elapsed>1: print("MACRO_TIME:", elapsed)
    return inputString

def extractObjectsOrPatterns(ProgSpec, clsNames, macroDefs, objectSpecResults,description):
    newClassNames = []
    comments = []
    for spec in objectSpecResults:
        s=spec[0]
        if s == "model" or s == "struct" or s == "string" or s == "stream":
            newName=extractObjectSpecs(ProgSpec, clsNames, spec, s,description, comments)
            if newName!=None: newClassNames.append(newName)
            comments = []
        elif s == "do":
            extractPatternSpecs(ProgSpec, clsNames, spec)
            comments = []
        elif s == "#define":
            extractMacroSpec(macroDefs, spec, comments)
            comments = []
        elif s == '/*^' or s == '//^':
            comments.append(spec)
        else:
            cdErr("Error in extractObjectsOrPatterns; expected 'object' or 'do' and got '{}'".format(spec[0]))
    return newClassNames


# # # # # # # # # # # # #   P a r s e r   I n t e r f a c e   # # # # # # # # # # # # #
def scanQuoteStr(text, idx, endChar):
    size = len(text)
    quoteStr = ""
    while idx < size:
        char = text[idx]
        quoteStr += char
        if char=="\\":
            if idx+2 >=size: cdErr("Quote Not Ended at end of file: '"+quoteStr[:30]+" ...'")
            nextChar = text[idx+1]
            if nextChar==endChar or nextChar=="\\":
                idx+=2
                continue
        elif char==endChar: return idx
        if idx+1 >= size: cdErr("Quote Not Ended: '"+quoteStr[:30]+" ...'")
        idx += 1
    return idx
def comment_remover(textIn):
    text = textIn
    size = len(text)
    commentType = None
    idx = 0
    while idx < size:
        char = text[idx]
        if char=='"' or char=="'":
            idx = scanQuoteStr(text, idx+1, char)
        elif char=="/":
            if size <= idx: continue
            nextChar    = text[idx+1]
            commentType = None
            if nextChar=="/":   commentType = "//"
            elif nextChar=="*": commentType = "/*"
            if commentType!=None:
                keepComments = False
                startPos     = idx
                replaceStr   = ""
                if idx+2 < size:
                    nextChar2 = text[idx+2]
                    if nextChar2==":" or nextChar2=="^":
                        keepComments = True
                if not keepComments: replaceStr += "  " #text = text[:idx] + "  " + text[idx+2:]
                cmtStr = ""
                idx += 2
                while idx < size:
                    char = text[idx]
                    if commentType=="//" and (char=="\n" or idx+1==size): commentType = None; break
                    elif commentType=="/*":
                        if idx+1 >= size: break
                        nextChar = char + text[idx+1]
                        if nextChar=="*/":
                            if not keepComments: replaceStr += "  "
                            commentType = None
                            break
                    cmtStr += char
                    if not keepComments:
                         if text[idx]!="\n": replaceStr += " "
                         else: replaceStr += "\n"
                    idx += 1
                if not keepComments:
                    endPos = startPos + len(replaceStr)
                    text = text[:startPos]+replaceStr+text[endPos:]
                if commentType!=None: cdErr("Comment did not end:'"+cmtStr+"'")
        idx += 1
    return(text)

def parseCodeDogLibTags(inputString, sourceLineMap=None):
    global parseTime
    tmpMacroDefs={}
    inputString = comment_remover(inputString)
    extractMacroDefs(tmpMacroDefs, inputString)
    #inputString = doMacroSubstitutions(tmpMacroDefs, inputString)

    _saveErrFileMaybe(inputString)
    try:
        startTime = timer()
        localResults = libTagParser.parseString(inputString, parseAll = False)
        parseTime += timer()-startTime
        #print("P_TIME-c:",parseTime)
    except ParseException as pe:
        lineNum = int(getattr(pe, "lineno", 1) or 1)
        colNum = max(1, int(getattr(pe, "column", 1) or 1))
        sourceLoc = progSpec.formatResolvedSourceLocation(sourceLineMap, lineNum, colNum)
        if SAVE_ERRFILE_ALWAYS or progSpec.shouldWriteErrFileForVirtualLine(sourceLineMap, lineNum):
            progSpec.saveTextToErrFile(inputString)
        errMsg = "While parsing lib tags: {}".format(pe)
        if sourceLoc != "":
            errMsg += " [source: {}]".format(sourceLoc)
        cdErr(errMsg)

    tagStore = extractTagDefs(localResults.libTagParser.tagDefList)
    return tagStore

def parseCodeDogString(inputString, ProgSpec, clsNames, macroDefs, description, sourceLineMap=None):
    tmpMacroDefs={}
    inputString = comment_remover(inputString)
    newLineCountBeforeMacros = inputString.count("\n")
    extractMacroDefs(tmpMacroDefs, inputString)
    inputString = doMacroSubstitutions(tmpMacroDefs, inputString)
    if sourceLineMap != None and inputString.count("\n") != newLineCountBeforeMacros:
        sourceLineMap = None
    LogLvl=logLvl()
    cdlog(LogLvl, "PARSING: "+description+"...")
    results = parseInput(inputString, sourceLineMap)
    cdlog(LogLvl, "EXTRACTING: "+description+"...")
    tagStore = extractTagDefs(results.progSpecParser.tagDefList)
    buildSpecs = extractBuildSpecs(results.progSpecParser.buildSpecList)
    newClassNames = extractObjectsOrPatterns(ProgSpec, clsNames, macroDefs, results.progSpecParser.classList,description)
    classes = [ProgSpec, clsNames]
    return[tagStore, buildSpecs, classes, newClassNames]

def AddToObjectFromText(ProgSpec, clsNames, inputStr, description):
    global parseTime
    macroDefs = {} # This var is not used here. If needed, make it an argument.
    inputStr = comment_remover(inputStr)
    #print('####################\n',inputStr, "\n######################^\n\n\n")
    errLevl=logLvl(); cdlog(errLevl, 'Parsing: '+description)
    _saveErrFileMaybe(inputStr)
    # (map of classes, array of objectNames, string to parse)
    try:
        startTime = timer()
        results = classList.parseString(inputStr, parseAll = True)
        parseTime += timer()-startTime
        #print("P_TIME-d:",parseTime)
    except ParseException as pe:
        progSpec.saveTextToErrFile(inputStr)
        cdErr("Error parsing generated class {}: {}".format(description, pe))
    cdlog(errLevl, 'Completed parsing: '+description)
    extractObjectsOrPatterns(ProgSpec, clsNames, macroDefs, results[0], description)
