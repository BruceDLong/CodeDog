# This module parses CodeDog syntax

import re
import progSpec
from pyparsing import *
ParserElement.enablePackrat()


def reportParserPlace(s, loc, toks):
    print "    PARSING AT char",loc, toks

# # # # # # # # # # # # #   BNF Parser Productions for CodeDog syntax   # # # # # # # # # # # # #
ParserElement.enablePackrat()
#######################################   T A G S   A N D   B U I L D - S P E C S
identifier = Word(alphas + nums + "_")("identifier")
tagID = identifier("tagID")
tagDefList = Forward()
tagValue = Forward()
tagMap  = Group('{' + tagDefList + '}')
tagList = Group('[' + Group(Optional(delimitedList(Group(tagValue), ','))) + ']')
backTickString = Literal("`").suppress() + SkipTo("`") + Literal("`").suppress()("backTickString")
tagValue <<= (quotedString() | backTickString | Word(alphas+nums+'-*_./') | tagList | tagMap)("tagValue")
tagDef = Group(tagID + Literal("=").suppress() + tagValue)("tagDef")
tagDefList <<= Group(ZeroOrMore(tagDef))("tagDefList")
#tagDefList.setParseAction(reportParserPlace)

buildID = identifier("buildID")
buildDefList = tagDefList("buildDefList")
buildSpec = Group(buildID + Literal(":").suppress() + buildDefList + ";")("buildSpec")
buildSpecList = Group(OneOrMore(buildSpec))("buildSpecList")
#buildSpec.setParseAction(reportParserPlace)

#######################################   B A S I C   T Y P E S
expr = Forward()
CID = identifier("CID")
CIDList = Group(delimitedList(CID, ','))("CIDList")
objectName = CID("objectName")
cppType = (Keyword("void") | Keyword("bool") | Keyword("int32") | Keyword("int64") | Keyword("double") | Keyword("char") | Keyword("uint32") | Keyword("uint64") | Keyword("string"))("cppType")
intNum = Word(nums)("intNum")
numRange = Group(intNum + ".." + intNum)("numRange")
varType = (objectName | cppType | numRange)("varType")
boolValue = (Keyword("true") | Keyword("false"))("boolValue")
floatNum = Combine(intNum + "." + intNum)("floatNum")
value = Forward()
listVal = "[" + delimitedList(expr, ",") + "]"
strMapVal = "{" + delimitedList( quotedString() + ":" + expr, ",")  + "}"
value <<= (boolValue | floatNum | intNum | quotedString() | listVal | strMapVal)("value")

#######################################   E X P R E S S I O N S
parameters = Forward()
owners = Forward()
arrayRef = Group('[' + expr('startOffset') + Optional(( ':' + expr('endOffset')) | ('..' + expr('itemLength'))) + ']')
firstRefSegment = NotAny(owners) + Group((CID | arrayRef) + Optional(parameters))
secondRefSegment = Group((Literal('.').suppress() + CID | arrayRef) + Optional(parameters))
varRef = Group(firstRefSegment + (ZeroOrMore(secondRefSegment)))
varFuncRef = varRef("varFuncRef")
lValue = varRef("lValue")
factor = Group( value | ('(' + expr + ')') | ('!' + expr) | ('-' + expr) | varFuncRef)
term = Group( factor + Group(Optional(OneOrMore(Group(oneOf('* / %') + factor )))))
plus = Group( term  + Group(Optional(OneOrMore(Group(oneOf('+ -') + term )))))
comparison = Group( plus + Group(Optional(OneOrMore(Group(oneOf('< > <= >=') + plus )))))
isEQ = Group( comparison  + Group(Optional(OneOrMore(Group(oneOf('== !=') + comparison )))))
logAnd = Group( isEQ  + Group(Optional(OneOrMore(Group('and' + isEQ )))))
expr <<= Group( logAnd + Group(Optional(OneOrMore(Group('or' + logAnd )))))("expr")
swap = Group(lValue + Literal("<->")("swapID") + lValue ("RightLValue"))("swap")
rValue = Group(expr)("rValue")
assign = (lValue + Combine(Literal("<") + (Optional(Word(alphas + nums + '_')("assignTag"))) + Literal("-"))("assignID") + rValue)("assign")
parameters <<= (Literal("(") + Optional(Group(delimitedList(rValue, ','))) + Literal(")").suppress())("parameters")

########################################   F U N C T I O N S
funcCall = varRef("funcCall")
verbatim = Group(Literal(r"<%") + SkipTo(r"%>", include=True))
fieldDef = Forward()
argList =  (verbatim | Group(Optional(delimitedList(Group( fieldDef)))))("argList")
actionSeq = Forward()
conditionalAction = Forward()
conditionalAction <<= Group(
            Group(Keyword("if") + "(" + rValue("ifCondition") + ")" + actionSeq("ifBody"))("ifStatement")
            + Optional((Keyword("else") | Keyword("but")) + (actionSeq | conditionalAction)("elseBody"))("optionalElse")
        )("conditionalAction")
traversalModes = (Keyword("Forward") | Keyword("Backward") | Keyword("Preorder") | Keyword("Inorder") | Keyword("Postorder") | Keyword("BreadthFirst") | Keyword("DF_Iterative"))
rangeSpec = Group(Keyword("RANGE") + '(' + rValue + ".." + rValue + ')')
whileSpec = Group(Keyword('WHILE') + '(' + expr + ')')
fileSpec  = Group(Keyword('FILE')  + '(' + expr + ')')
keyRange  = Group(rValue("repList") + Keyword('from') + rValue('fromPart')  + Keyword('to') + rValue('toPart'))
repeatedAction = Group(
            Keyword("withEach")("repeatedActionID")  + CID("repName") + "in"+ Optional(traversalModes("traversalMode")) + (whileSpec('whileSpec') | rangeSpec('rangeSpec') | keyRange('keyRange') | fileSpec('fileSpec') | rValue("repList"))('itemsToIter') + ":"
            + Optional(Keyword("where") + "(" + expr("whereExpr") + ")")
            + Optional(Keyword("until") + "(" + expr("untilExpr") + ")")
            + actionSeq
        )("repeatedAction")

action = Group(assign("assign") | funcCall("funcCall") | fieldDef('fieldDef'))
actionSeq <<=  Group(Literal("{")("actSeqID") + ( ZeroOrMore (conditionalAction | repeatedAction | actionSeq | action))("actionList") + Literal("}")) ("actionSeq")
funcBodyVerbatim = Group( "<%" + SkipTo("%>", include=True))("funcBodyVerbatim")
funcBody = (actionSeq | funcBodyVerbatim)("funcBody")

#########################################   F I E L D   D E S C R I P T I O N S
nameAndVal = Group(
          (Literal(":") + CID("fieldName") + "(" + argList + Literal(")")('argListTag') + Optional(Literal(":")("optionalTag") + tagDefList) + "<-" + funcBody )         # Function Definition
        | (Literal(":") + CID("fieldName")  + "<-" + rValue("givenValue"))
        | (Literal(":") + "<-" + (rValue("givenValue") | funcBody))
        | (Literal(":") + CID("fieldName")  + Optional("(" + argList + Literal(")")('argListTag')))
        | (Literal("::") + CID("fieldName")  + parameters("parameters"))
    )("nameAndVal")

datastructID = (Keyword("list") | Keyword("opt") | Keyword("map") | Keyword("multimap") | Keyword("tree") | Keyword("graph"))('datastructID')
arraySpec = Group (Literal('[')  + Optional(owners)('owner') + datastructID + Optional(intNum | varType)('indexType') + Literal(']'))("arraySpec")
meOrMy = (Keyword("me") | Keyword("my"))
modeSpec = (Optional(meOrMy)('owner') + Keyword("mode")("modeIndicator") + Literal("[") + CIDList("modeList") + Literal("]") + nameAndVal)("modeSpec")
flagDef  = (Optional(meOrMy)('owner') + Keyword("flag")("flagIndicator") + nameAndVal )("flagDef")
baseType = (cppType | numRange)("baseType")

#########################################   O B J E C T   D E S C R I P T I O N S
objectName = Combine(CID + Optional('::' + CID))("objectName")
fieldDefs = ZeroOrMore(fieldDef)("fieldDefs")
SetFieldStmt = Group(Word(alphas + nums + "_.") + '=' + Word(alphas + nums + r"_. */+-(){}[]\|<>,./?`~@#$%^&*=:!'" + '"'))
coFactualEl  = Group(Literal("(") + Group(fieldDef + "<=>" + Group(OneOrMore(SetFieldStmt + Literal(';').suppress())))  + ")") ("coFactualEl")
sequenceEl = (Literal("{") + fieldDefs + Literal("}"))("sequenceEl")
alternateEl  = (Literal("[") + Group(OneOrMore((coFactualEl | fieldDef) + Optional("|").suppress()))("fieldDefs") + Literal("]"))("alternateEl")
anonModel = (sequenceEl | alternateEl) ("anonModel")
owners <<= (Keyword("const") | Keyword("me") | Keyword("my") | Keyword("our") | Keyword("their") | Keyword("itr"))
fullFieldDef = (Optional('>')('isNext') + Optional(owners)('owner') + (baseType | objectName | Group(anonModel))('fieldType') +Optional(arraySpec) + Optional(nameAndVal))("fullFieldDef")
fieldDef <<= Group(flagDef('flagDef') | modeSpec('modeDef') | (quotedString()('constStr')+Optional("[opt]")) | intNum('constNum') | nameAndVal('nameVal') | fullFieldDef('fullFieldDef'))("fieldDef")
modelTypes = (Keyword("model") | Keyword("struct") | Keyword("string") | Keyword("stream"))
objectDef = Group(modelTypes + objectName + Optional(Literal(":")("optionalTag") + tagDefList) + (Keyword('auto') | anonModel))("objectDef")
doPattern = Group(Keyword("do") + objectName + Literal("(").suppress() + CIDList + Literal(")").suppress())("doPattern")
macroDef  = Group(Keyword("#define") + CID('macroName') + Literal("(").suppress() + CIDList('macroArgs') + Literal(")").suppress() + Group( "<%" + SkipTo("%>", include=True))("macroBody"))
objectList = Group(ZeroOrMore(objectDef | doPattern | macroDef))("objectList")

#########################################   P A R S E R   S T A R T   S Y M B O L
progSpecParser = (Optional(buildSpecList) + tagDefList + objectList)("progSpecParser")

# # # # # # # # # # # # #   E x t r a c t   P a r s e   R e s u l t s   # # # # # # # # # # # # #
def parseInput(inputStr):
    try:
        localResults = progSpecParser.parseString(inputStr, parseAll = True)

    except ParseException , pe:
        print "error parsing: " , pe
        exit(1)
    return localResults

def extractTagDefs(tagResults):
    localTagStore = {}
    #print tagResults

    for tagSpec in tagResults:
        tagVal = tagSpec.tagValue
        if ((not isinstance(tagVal, basestring)) and len(tagVal)>=2):
            if(tagVal[0]=='['):
                #print "LIST OF VALUES"
                tagValues=[]
                for multiVal in tagVal[1]:
                    tagValues.append(multiVal[0])
                #print tagValues

            elif(tagVal[0]=='{'):
                #print "MAP OF VALUES"
                tagValues=extractTagDefs(tagVal[1])
            tagVal=tagValues
        # Remove quotes
        elif (len(tagVal)>=2 and (tagVal[0] == '"' or tagVal[0] == "'") and (tagVal[0]==tagVal[-1])):
            tagVal = tagVal[1:-1]
        #print tagSpec.tagID, " is ", tagVal
        localTagStore[tagSpec.tagID] = tagVal
    return localTagStore

nameIDX=1
def packFieldDef(fieldResult, ObjectName, indent):
    global nameIDX
    #  ['(', [['>', 'me', ['CID'], [':', 'tag']], '<=>', [[[['hasTag']], '=', [[[[[[[['54321'], []], []], []], []], []], []]]]]], ')']
    coFactuals=None
    if fieldResult[0]=='(':             # Reorganize Cofactuals if they are here
        coFactuals = fieldResult[1][2]
        fieldResult= fieldResult[1][0]
        print"        ##", fieldResult, "{", ObjectName, "}"

    fieldDef={}
    argList=[]
    paramList=[]
    innerDefs=[]
    optionalTags=None
    isNext=False;
    if(fieldResult.isNext): isNext=True
    if(fieldResult.owner): owner=fieldResult.owner;
    else: owner='me';
    if(fieldResult.fieldType):
        fieldType=fieldResult.fieldType;
        if not isinstance(fieldType, basestring) and (fieldType[0]=='[' or fieldType[0]=='{'):
            print "FIELDTYPE is an inline SEQ or ALT:"

            if   fieldType[0]=='{': fieldList=fieldType[1:-1]
            elif fieldType[0]=='[': fieldList=fieldType[1]
            for innerField in fieldList:
                innerFieldDef=packFieldDef(innerField, ObjectName, indent+'    ')
                innerDefs.append(innerFieldDef)

    else: fieldType=None;
    if(fieldResult.arraySpec): arraySpec=fieldResult.arraySpec;
    else: arraySpec=None;
    if(fieldResult.nameAndVal):
        nameAndVal = fieldResult.nameAndVal
        #print "nameAndVal = ", nameAndVal
        if(nameAndVal.fieldName):
            fieldName = nameAndVal.fieldName
            #print "FIELD NAME", fieldName
        else: fieldName=None;
        if(nameAndVal.givenValue):
            givenValue = nameAndVal.givenValue

        elif(nameAndVal.funcBody):
            [funcBodyOut, funcTextVerbatim] = extractFuncBody(ObjectName, fieldName, nameAndVal.funcBody)
            givenValue=[funcBodyOut, funcTextVerbatim]
            #print "\n\n[funcBodyOut, funcTextVerbatim] ", givenValue

        else: givenValue=None;
        if(nameAndVal.argListTag):
            for argSpec in nameAndVal.argList:
                argList.append(packFieldDef(argSpec[0], ObjectName, indent+"    "))
        else: argList=None;
        if 'parameters' in nameAndVal:
            for param in nameAndVal.parameters[1]:
                paramList.append(param)
        else: paramList=None

        if(nameAndVal.optionalTag): optionalTags=extractTagDefs(nameAndVal.tagDefList)
    else:
        givenValue=None;
        fieldName=None;



    if(fieldResult.flagDef):
        print indent+"        FLAG: ", fieldResult
        if(arraySpec): print"Lists of flags are not allowed.\n"; exit(2);
        fieldDef=progSpec.packField(False, owner, 'flag', arraySpec, fieldName, None, paramList, givenValue)
    elif(fieldResult.modeDef):
        print indent+"        MODE: ", fieldResult
        modeList=fieldResult.modeList
        if(arraySpec): print"Lists of modes are not allowed.\n"; exit(2);
        fieldDef=progSpec.packField(False, owner, 'mode', arraySpec, fieldName, None, paramList, givenValue)
        fieldDef['typeSpec']['enumList']=modeList
    elif(fieldResult.constStr):
        if fieldName==None: fieldName="constStr"+str(nameIDX); nameIDX+=1;
        if(len(fieldResult)>1 and fieldResult[1]=='[opt]'): arraySpec={'datastructID': 'opt'}
        givenValue=fieldResult.constStr[1:-1]
        fieldDef=progSpec.packField(True, 'const', 'string', arraySpec, fieldName, None, paramList, givenValue)
    elif(fieldResult.constNum):
        print indent+"        CONST Num: ", fieldResult
        if fieldName==None: fieldName="constNum"+str(nameIDX); nameIDX+=1;
        fieldDef=progSpec.packField(True, 'const', 'int', arraySpec, fieldName, None, paramList, givenValue)
    elif(fieldResult.nameVal):
        print indent+"        NameAndVal: ", fieldResult
        fieldDef=progSpec.packField(None, None, None, arraySpec, fieldName, argList, paramList, givenValue)
    elif(fieldResult.fullFieldDef):
        fieldTypeStr=str(fieldType)[:50]
        print indent+"        FULL FIELD: ", [isNext, owner, fieldTypeStr+'... ', arraySpec, fieldName]
        fieldDef=progSpec.packField(isNext, owner, fieldType, arraySpec, fieldName, argList, paramList, givenValue)
    else:
        print "Error in packing FieldDefs:", fieldResult
        exit(1)
    if len(innerDefs)>0:
        fieldDef['innerDefs']=innerDefs
    if coFactuals!=None:
        fieldDef['coFactuals']=coFactuals
    if optionalTags!=None:
        fieldDef['optionalTags']=optionalTags
    return fieldDef

def extractActSeqToActSeq(funcName, childActSeq):
    actSeqData = extractActSeq(funcName, childActSeq)
    return actSeqData

def parseResultToArray(parseSegment):
    myList = []
    for seg in parseSegment:
        myList.append(seg)
    return myList


def extractActItem(funcName, actionItem):
    global funcsCalled
    thisActionItem='error'
    #print "ACTIONITEM:", actionItem
    if actionItem.fieldDef:
        thisActionItem = {'typeOfAction':"newVar", 'fieldDef':packFieldDef(actionItem.fieldDef, '', '    LOCAL:')}
    elif actionItem.ifStatement:    # Conditional
        ifCondition = actionItem.ifStatement.ifCondition
        IfBodyIn = actionItem.ifStatement.ifBody
        ifBodyOut = extractActSeqToActSeq(funcName, IfBodyIn)
        #elseBody = {"if":'xxx', "act":'xxx'}
        elseBodyOut = {}
        #print elseBody
        if (actionItem.optionalElse):
            elseBodyIn = actionItem.optionalElse
            if (elseBodyIn.conditionalAction):
                elseBodyOut = ['if' , [extractActItem(funcName, elseBodyIn.conditionalAction)] ]
                #print "\n ELSE IF........ELSE IF........ELSE IF........ELSE IF: ", elseBodyOut
            elif (elseBodyIn.actionSeq):
                elseBodyOut = ['action', extractActItem(funcName, elseBodyIn.actionSeq)]
                #elseBody['act']  = elseBodyOut
                #print "\n ELSE........ELSE........ELSE........ELSE........ELSE: ", elseBody
        #print "\n IF........IF........IF........IF........IF: ", ifCondition, ifBodyOut, elseBodyOut

        thisActionItem = {'typeOfAction':"conditional", 'ifCondition':ifCondition, 'ifBody':ifBodyOut, 'elseBody':elseBodyOut}
    # Repeated Action withEach
    elif actionItem.repeatedActionID:
        repName = actionItem.repName
        repList = actionItem.repList
        repBodyIn = actionItem.actionSeq
        repBodyOut = extractActSeqToActSeq(funcName, repBodyIn)
        traversalMode=None
        if actionItem.traversalMode:
            traversalMode = actionItem.traversalMode
        whileSpec=None
        if actionItem.whileSpec:
            whileSpec = actionItem.whileSpec
        rangeSpec=None
        if actionItem.rangeSpec:
            rangeSpec = actionItem.rangeSpec
        keyRange=None
        if actionItem.keyRange:
            keyRange = actionItem.keyRange
        whereExpr = ''
        untilExpr = ''
        if actionItem.whereExpr:
            whereExpr = actionItem.whereExpr
        if actionItem.untilExpr:
            untilExpr = actionItem.untilExpr
        thisActionItem = {'typeOfAction':"repetition" ,'repName':repName, 'whereExpr':whereExpr, 'untilExpr':untilExpr, 'repBody':repBodyOut,
                            'repList':repList, 'traversalMode':traversalMode, 'rangeSpec':rangeSpec, 'whileSpec':whileSpec, 'keyRange':keyRange}
    # Action sequence
    elif actionItem.actSeqID:
        actionListIn = actionItem
        #print "ACT_SEQ...ACT_SEQ...ACT_SEQ...ACT_SEQ...ACT_SEQ: ", actionListIn
        actionListOut = extractActSeqToActSeq(funcName, actionListIn)
        #print "ACT_SEQ...ACT_SEQ...ACT_SEQ...ACT_SEQ...ACT_SEQ: ", actionListOut
        thisActionItem = {'typeOfAction':"actionSeq", 'actionList':actionListOut}
    # Assign
    elif (actionItem.assign):
        RHS = parseResultToArray(actionItem.rValue)
        LHS = parseResultToArray(actionItem.lValue)
        assignTag = ''
        if (actionItem.assign[1] != '<-'):
            assignTag = actionItem.assign[1][0][1:-1]
            print "assignTag:",assignTag

        #print RHS, LHS
        thisActionItem = {'typeOfAction':"assign", 'LHS':LHS, 'RHS':RHS, 'assignTag':assignTag}
    # Swap
    elif (actionItem.swapID):
        RHS = actionItem.RightLValue
        LHS = actionItem.lValue
        thisActionItem = {'typeOfAction':"swap", 'LHS':LHS, 'RHS':RHS}
    # Function Call
    elif actionItem.funcCall:
        calledFunc = (actionItem.funcCall)
        # TODO: Verify that calledFunc is a function and error out if not. (The last segment should have '(' as its second item.)
        calledFuncLastSegment = calledFunc[-1]
        if len(calledFuncLastSegment)<2 or calledFuncLastSegment[1] != '(':
            print "Expected a function, not a variable:", calledFuncLastSegment; exit(2)
        thisActionItem = {'typeOfAction':"funcCall", 'calledFunc':calledFunc}

        calledFuncName = calledFuncLastSegment[0]
        if(len(calledFuncLastSegment)<=2): calledFuncParams=[]
        else:
            #print 'calledFuncLastSegment', calledFuncLastSegment, ', len:',
            calledFuncParams = calledFuncLastSegment[2]

        progSpec.appendToFuncsCalled(calledFuncName, calledFuncParams)
    else:
        print "error in extractActItem"
        print "actionItem", str(actionItem)
        exit(1)
    return thisActionItem

def extractActSeq( funcName, childActSeq):
    #print childActSeq
    actionList = childActSeq.actionList
    actSeq = []
    for actionItem in actionList:
        thisActionItem = extractActItem(funcName, actionItem)
        actSeq.append(thisActionItem)
    return actSeq

def extractActSeqToFunc(funcName, funcBodyIn):
    #print "extractActSeqToFunc"
    #print "objectName: ", objectName
    #print "funcName: ", funcName
    #print "funcBodyIn: ", funcBodyIn
    childActSeq = extractActSeq( funcName, funcBodyIn)
    #print childActSeq
    return childActSeq


def extractFuncBody(localObjectName,funcName, funcBodyIn):
    if funcBodyIn[0] == "<%":
        funcBodyOut = ""
        if len(funcBodyIn)== 3: # handles new pyparsing
            funcTextVerbatim = funcBodyIn[1]
        elif len(funcBodyIn)== 2: # handles old pyparsing
            funcTextVerbatim = funcBodyIn[1][0]
        else:
            print "error in funcTextVerbatim: ", "len(funcBodyIn): ", len(funcBodyIn)
            exit(1)
    else:
        funcBodyOut = extractActSeqToFunc(funcName, funcBodyIn)
        funcTextVerbatim = ""
    #print funcBodyOut
    return funcBodyOut, funcTextVerbatim


def extractFieldDefs(ProgSpec, ObjectName, fieldResults):
    print "    EXTRACTING Field Defs for", ObjectName
    #print fieldResults
    for fieldResult in fieldResults:
        fieldDef=packFieldDef(fieldResult, ObjectName, '')
        progSpec.addField(ProgSpec, ObjectName, fieldDef)



def extractBuildSpecs(buildSpecResults):
    resultBuildSpecs = []
    print "buildSpecResults: ", buildSpecResults
    if (len(buildSpecResults)==0):
        resultBuildSpecs = [['LinuxBuild', {'': ''}]]
        print "len 0";
    else:
        for localBuildSpecs in buildSpecResults:
            print "localBuildSpecs.buildDefList: ", localBuildSpecs.buildDefList
            spec = [localBuildSpecs.buildID, extractTagDefs(localBuildSpecs.buildDefList[0])]
            resultBuildSpecs.append(spec)
            print "spec: ", spec,  localBuildSpecs.buildDefList
        print "len > 0: ", len(buildSpecResults);
    print "resultBuildSpecs: ",resultBuildSpecs
    return resultBuildSpecs

def extractObjectSpecs(ProgSpec, objNames, spec, stateType):
    #print spec
    objectName=spec.objectName[0]
    configType="unknown"
    if(spec.sequenceEl): configType="SEQ"
    elif(spec.alternateEl):configType="ALT"
    ###########Grab optional Object Tags
    if spec.optionalTag:  #change so it generates an empty one if no field defs
        #print "spec.tagDefList = ",spec.tagDefList
        objTags = extractTagDefs(spec.tagDefList)
        #fieldIDX = 4
    else:
        objTags = {}
        #fieldIDX = 3
 #   if 'ctxTag' in objTags: objectName+="#"+objTags['ctxTag']
    progSpec.addObject(ProgSpec, objNames, objectName, stateType, configType)
    progSpec.addObjTags(ProgSpec, objectName, objTags)
    ###########Grab field defs
    if(spec[2]=='auto'):
        progSpec.markStructAuto(ProgSpec, objectName)
    else:
        #print "SPEC.FIELDDEFS",spec.fieldDefs
        extractFieldDefs(ProgSpec, objectName, spec.fieldDefs)

    return

def extractPatternSpecs(ProgSpec, objNames, spec):
    #print spec
    patternName=spec.objectName[0]
    patternArgWords=spec.CIDList
    progSpec.addPattern(ProgSpec, objNames, patternName, patternArgWords)
    return

def extractMacroSpec(macroDefs, spec):
    MacroName=spec.macroName
    MacroArgs=spec.macroArgs
    MacroBody=spec.macroBody[1]
    macroDefs[MacroName] = {'ArgList':MacroArgs,  'Body':MacroBody}

def extractMacroDefs(macroDefMap, inputString):
    macroDefs = re.findall('#define.*%>', inputString)
    #print "extractMacroDefs: ", macroDefs
    for macroStr in macroDefs:
        try:
            localResults = macroDef.parseString(macroStr, parseAll = True)
        except ParseException , pe:
            print "error parsing: " , pe
            exit(1)
        extractMacroSpec(macroDefMap, localResults[0])

def doMacroSubstitutions(macros, inputString):
    #print "\n\nMACRO-MAP:", macros
    subsWereMade=True
    while(subsWereMade ==True):
        subsWereMade=False
        for thisMacro in macros:
            macRefPattern=re.compile('(?<!#define)\s+('+thisMacro+')\s*\((.*)\)')
            print "MAC NAME:", thisMacro
            for match in macRefPattern.finditer(inputString):
                #print "     %s: %s %s" % (match.start(), match.group(1), match.group(2))
                newText=macros[thisMacro]['Body']
                print "     START TEXT:", newText
                paramStr=match.group(2)
                params=paramStr.split(',')
                print '     PARAMS:', params
                idx=0;
                for arg in macros[thisMacro]['ArgList']:
                    #print "   SUBS:", arg, params[idx]
                    newText=newText.replace(arg, params[idx])
                    idx+=1
                print "     NEW TEXT:", newText
                inputString = inputString[:match.start()]+ newText + inputString[match.end():]
                subsWereMade=True
    print "     RETURN STRING:", inputString
    # Last, replace the text into inputString
    return inputString

def extractObjectsOrPatterns(ProgSpec, objNames, macroDefs, objectSpecResults):
    for spec in objectSpecResults:
        s=spec[0]
        if s == "model" or s == "struct" or s == "string" or s == "stream":
            extractObjectSpecs(ProgSpec, objNames, spec, s)
        elif s == "do":
            extractPatternSpecs(ProgSpec, objNames, spec)
        elif s == "#define":
            extractMacroSpec(macroDefs, spec)
        else:
            print "Error in extractObjectsOrPatterns; expected 'object' or 'do' and got '",spec[0],"'"
            exit(1)


# # # # # # # # # # # # #   P a r s e r   I n t e r f a c e   # # # # # # # # # # # # #

def comment_remover(text):
    def replacer(match):
        s = match.group(0)
        if s.startswith('/'):
            return " " # note: a space and not an empty string
        else:
            return s
    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )
    return re.sub(pattern, replacer, text)

def parseCodeDogString(inputString, ProgSpec, objNames, macroDefs):
    tmpMacroDefs={}
    inputString = comment_remover(inputString)
    extractMacroDefs(tmpMacroDefs, inputString)
    inputString = doMacroSubstitutions(tmpMacroDefs, inputString)
    results = parseInput(inputString)
    #print results.tagDefList
    tagStore = extractTagDefs(results.tagDefList)
    #print results.buildSpecList
    buildSpecs = extractBuildSpecs(results.buildSpecList)
    #print results.objectList
    extractObjectsOrPatterns(ProgSpec, objNames, macroDefs, results.objectList)
    objectSpecs = [ProgSpec, objNames]
    return[tagStore, buildSpecs, objectSpecs]

def AddToObjectFromText(spec, objNames, inputStr):
    macroDefs = {} # This var is not used here. If needed, make it an argument.
    inputStr = comment_remover(inputStr)
    #print '####################\n',inputStr, "\n######################^\n\n\n"

    # (map of objects, array of objectNames, string to parse)
    results = objectList.parseString(inputStr, parseAll = True)
    #print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n',results,'%%%%%%%%%%%%%%%%%%%%%%'
    extractObjectsOrPatterns(spec, objNames, macroDefs, results[0])
