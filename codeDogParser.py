# This module parses CodeDog syntax

import re
import progSpec
from pyparsing import Word, alphas, nums, Literal, Keyword, Optional, OneOrMore, oneOf, ZeroOrMore, delimitedList, Group, ParseException, quotedString, Forward, StringStart, StringEnd, SkipTo, Combine

def reportParserPlace(s, loc, toks):
    print "    PARSING AT char",loc, toks

# BNF Parser Productions for CodeDog syntax
identifier = Word(alphas + nums + "_-")("identifier")
CID = identifier("CID")
CIDList = Group(delimitedList(CID, ','))("CIDList")
objectName = CID("objectName")
cppType = (Keyword("void") | Keyword("bool") | Keyword("int32") | Keyword("int64") | Keyword("double") | Keyword("char") | Keyword("uint32") | Keyword("uint64") | Keyword("string"))("cppType")
intNum = Word(nums)("intNum")
numRange = intNum + ".." + intNum("numRange")
value = Forward()
varType = (objectName | cppType | numRange | Keyword("mesg"))("varType")
boolValue = (Keyword("true") | Keyword("false"))("boolValue")
floatNum = intNum + Optional("." + intNum)("floatNum")
listVal = "[" + delimitedList(value, ",") + "]"
strMapVal = "{" + delimitedList( quotedString() + ":" + value, ",")  + "}"
value <<= (boolValue | intNum | floatNum | quotedString() | listVal | strMapVal)("value")
backTickString = Literal("`").suppress() + SkipTo("`") + Literal("`").suppress()("backTickString")
tagID = identifier("tagID")
tagDefList = Forward()
tagValue = Forward()
tagMap  = Group('{' + tagDefList + '}')
tagList = Group('[' + Group(Optional(delimitedList(Group(tagValue), ','))) + ']')
tagValue <<= (quotedString() | backTickString | Word(alphas+nums+'-_.') | tagList | tagMap)("tagValue")
tagDef = Group(tagID + Literal("=").suppress() + tagValue)("tagDef")
tagDefList <<= Group(ZeroOrMore(tagDef))("tagDefList")
buildID = identifier("buildID")
buildDefList = tagDefList("buildDefList")
buildSpec = Group(buildID + Literal(":").suppress() + buildDefList + ";")("buildSpec")
buildSpecList = Group(OneOrMore(buildSpec))("buildSpecList")
#######################################
verbatim = Group(Literal(r"<%") + SkipTo(r"%>", include=True))
#verbatim.setParseAction( reportParserPlace)

#varName = Group(CID ("varName")+Optional("(" + argList + ")"))("varName")
varName = CID ("varName")
typeSpec = Forward()
typeSpec <<= Group((Keyword("var")| Keyword("sPtr") | Keyword("uPtr") | Keyword("rPtr") | Keyword("list")) + (typeSpec | varType))("typeSpec")
varSpec = Group(typeSpec + Literal(":").suppress() + varName)("varSpec")
argList =  (verbatim | Group(Optional(delimitedList(Group(varSpec)))))("argList")

constName = CID("constName")
constValue = value("constValue")
constSpec = Group(Keyword("const")("constIndicator") + cppType + ":" + constName + "=" + constValue)("constSpec")

#######################################
expr = Forward()
funcCall = Forward()
#factor = (value | ('(' + expr + ')') | funcCall)("factor")
#term = (factor + ZeroOrMore(oneOf('* / %') + factor))("term")
#expr <<= (term + ZeroOrMore(oneOf('+ -') + term))("expr")
arrayRef = Group('[' + expr('startOffset') + Optional(( ':' + expr('endOffset')) | ('..' + expr('itemLength'))) + ']')
secondRefSegment = (Literal('.').suppress() + CID | arrayRef)
firstRefSegment = (CID | arrayRef)
#varRef = Group(firstRefSegment + ZeroOrMore(secondRefSegment))("varRef")
varRef = Group(CID + Optional(Literal('.').suppress() + CID))("varRef")
lValue = varRef("lValue")
factor = (value | ('(' + expr + ')') | funcCall | ('!' + expr) | ('-' + expr) | varRef)("factor")
term = ( factor + ZeroOrMore(oneOf('* / %') + factor ))("term")
plus = ( term  + ZeroOrMore(oneOf('+ -') + term ))("plus")
comparison = ( plus + ZeroOrMore(oneOf('< > <= >=') + plus ))("comparison")
isEQ = ( comparison  + ZeroOrMore(oneOf('= !=') + comparison ))("isEQ")
logAnd = ( isEQ  + ZeroOrMore('and' + isEQ ))("logAnd")
expr <<= ( logAnd + ZeroOrMore('or' + logAnd ))("expr")
swap = Group(lValue + Literal("<->")("swapID") + lValue ("RightLValue"))("swap")
rValue = (expr)("rValue")
assign = Group(lValue + (Literal("<")("assignID") + Optional(Word(alphas + nums + '_')("assignTag")) + Literal("-")) + rValue)("assign")
parameters = Group(delimitedList(rValue, ','))("parameters")
funcCall <<= (CID("calledFunc") + Literal("(") + parameters + ")")("funcCall")
########################################
actionSeq = Forward()
conditionalAction = Forward()
conditionalAction <<= Group(Group(Keyword("if") + "(" + expr("ifCondition") + ")" + actionSeq("ifBody"))("ifStatement")+ Optional(Keyword("else") + (actionSeq | conditionalAction)("elseBody"))("optionalElse"))("conditionalAction")
repeatedAction = Group(Keyword("withEach")("repeatedActionID")  + CID("repName") + "in"+ lValue("repList") + ":" + Optional(Keyword("where") + "(" + expr("whereExpr") + ")") + Optional(Keyword("until") + "(" + expr("untilExpr") + ")") + actionSeq)("elseBody")("repeatedAction")
action = (varSpec | Group(funcCall) | assign | swap)("action")
actionSeq <<=  Group(Literal("{")("actSeqID") + Group( ZeroOrMore (conditionalAction | repeatedAction | actionSeq | action))("actionList") + Literal("}")) ("actionSeq")
#########################################
funcBodyVerbatim = Group( "<%" + SkipTo("%>", include=True))("funcBodyVerbatim")
returnType = (verbatim("returnTypeVerbatim")| typeSpec("returnTypeSpec"))("returnType")
optionalTag = Literal(":")("optionalTag")
#funcName = CID("funcName")
funcBody = (actionSeq | funcBodyVerbatim)("funcBody")
#funcSpec = Group(Keyword("func")("funcIndicator") + returnType + ":" + CID("funcName") + "(" + argList + ")" + Optional(optionalTag + tagDefList) + funcBody)("funcSpec")
#funcSpec.setParseAction( reportParserPlace)
nameAndVal = (
          (Literal(":") + CID("name") + "(" + argList + ")" + "=" + funcBody )
        | (Literal(":") + CID("name")  + "=" + value )
        | (Literal(":") + "=" + (value | funcBody))
        | (Literal(":") + CID("name")  + Optional("(" + argList + ")")))("nameAndVal")

arraySpec = Group ('[' + Optional(intNum | numRange) + ']')("arraySpec")
meOrMy = (Keyword("me") | Keyword("my"))
owners = (Keyword("const") | Keyword("me") | Keyword("my") | Keyword("our") | Keyword("their"))
modeSpec = (Optional(meOrMy)('owner') + Keyword("mode")("modeIndicator") + Literal("[") + CIDList("modeList") + Literal("]") + nameAndVal("modeName"))("modeSpec")
flagDef  = (Optional(meOrMy)('owner') + Keyword("flag")("flagIndicator") + nameAndVal )("flagDef")
#fieldDef = (Optional('>')('isNext') + (flagDef | modeSpec | varSpec | constSpec | funcSpec))("fieldDef")
baseType = (cppType)("baseType")
objectName = Combine(CID + Optional('::' + CID))("objectName")

#########################################
SetFieldStmt = Group(lValue + '=' + rValue)
fieldDefs = Forward()
coFactualEL  = (Literal("(") + Group(fieldDefs + "<=>" + Group(OneOrMore(SetFieldStmt + Literal(';').suppress())))  + ")") ("coFactualEL")
alternateEl  = (Literal("[") + Group(OneOrMore(fieldDefs + Optional("|").suppress())) + Literal("]"))("alternateEl")
anonModel = (fieldDefs | alternateEl | coFactualEL ) ("anonModel")
fullFieldDef = (Optional('>')('isNext') + Optional(owners)('owner') + (baseType | objectName | anonModel)('fieldVarType') +Optional(arraySpec) + Optional(nameAndVal))("fullFieldDef")
fieldDef = Group(flagDef('flagDef') | modeSpec('modeDef') | quotedString()('constStr') | intNum('constNum') | nameAndVal('nameVal') | fullFieldDef('fullFieldDef'))("fieldDef")
fieldDefs <<=  (Literal("{").suppress() + (ZeroOrMore(fieldDef))+ Literal("}").suppress())("fieldDefs")
modelTypes = (Keyword("model") | Keyword("struct") | Keyword("string") | Keyword("stream"))
objectDef = Group(modelTypes + objectName + Optional(optionalTag + tagDefList) + (Keyword('auto') | anonModel))("objectDef")
doPattern = Group(Keyword("do") + objectName + Literal("(").suppress() + CIDList + Literal(")").suppress())("doPattern")
objectList = Group(ZeroOrMore(objectDef | doPattern))("objectList")
progSpecParser = (tagDefList + buildSpecList + objectList)("progSpecParser")


def parseInput(inputStr):
    try:
        localResults = progSpecParser.parseString(inputStr, parseAll = True)

    except ParseException , pe:
        print "error parsing: " , pe
        exit(1)
    return localResults

def extractTagDefs(tagResults):
    localTagStore = {}

    for tagSpec in tagResults:
        tagVal = tagSpec.tagValue
        if ((not isinstance(tagVal, basestring)) and len(tagVal)>=2):
            if(tagVal[0]=='['):
                print "LIST OF VALUES"
                tagValues=[]
                for multiVal in tagVal[1]:
                    tagValues.append(multiVal[0])
                print tagValues

            elif(tagVal[0]=='{'):
                print "MAP OF VALUES"
                tagValues=extractTagDefs(tagVal[1])
            tagVal=tagValues
        # Remove quotes
        elif (len(tagVal)>=2 and (tagVal[0] == '"' or tagVal[0] == "'") and (tagVal[0]==tagVal[-1])):
            tagVal = tagVal[1:-1]
        print tagSpec.tagID, " is ", tagVal
        localTagStore[tagSpec.tagID] = tagVal
    return localTagStore

def extractActSeqToActSeq(funcName, childActSeq):
    #print "QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQUextractActSeqToActSeq"
    #print childActSeq
    #print "QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQextractActSeqToActSeq"
    actSeqData = extractActSeq(funcName, childActSeq)
    return actSeqData


def extractActItem(funcName, actionItem):
    #print "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIextractActItem"
    #print "actionItem: ", actionItem
    #print "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIextractActItem"
    thisActionItem='error'
    # Create Variable: var | sPtr | uPtr | rPtr | list
    if actionItem.varName:
        thisTypeSpec = actionItem.typeSpec
        thisVarName = actionItem.varName
        #print thisTypeSpec, thisVarName
        thisActionItem = {'typeOfAction':"newVar", 'typeSpec':thisTypeSpec, 'varName':thisVarName}
    # Conditional if
    elif actionItem.ifStatement:
        ifCondition = actionItem.ifStatement.ifCondition
        IfBodyIn = actionItem.ifStatement.ifBody
        ifBodyOut = extractActSeqToActSeq(funcName, IfBodyIn)
        #elseBody = {"if":'xxx', "act":'xxx'}
        elseBodyOut = {}
        #print elseBody
        if (actionItem.optionalElse):
            elseBodyIn = actionItem.optionalElse
            if (elseBodyIn.conditionalAction):
                elseBodyOut = extractActItem(funcName, elseBodyIn.conditionalAction)
                #elseBody['if'] = elseBodyOut
                #print "\n ELSE IF........ELSE IF........ELSE IF........ELSE IF: ", elseBody
            elif (elseBodyIn.actionSeq):
                elseBodyOut = extractActItem(funcName, elseBodyIn.actionSeq)
                #elseBody['act']  = elseBodyOut
                #print "\n ELSE........ELSE........ELSE........ELSE........ELSE: ", elseBody
        #print "\n IF........IF........IF........IF........IF: ", ifCondition, ifBodyOut, elseBody
        thisActionItem = {'typeOfAction':"conditional", 'ifCondition':ifCondition, 'ifBody':ifBodyOut, 'elseBody':elseBodyOut}
    # Repeated Action withEach
    elif actionItem.repeatedActionID:
        repName = actionItem.repName
        repList = actionItem.repList
        repBodyIn = actionItem.actionSeq
        repBodyOut = extractActSeqToActSeq(funcName, repBodyIn)
        whereExpr = ''
        untilExpr = ''
        if actionItem.whereExpr:
            whereExpr = actionItem.whereExpr
        if actionItem.untilExpr:
            untilExpr = actionItem.untilExpr
        #print "REP...REP...REP...REP...REP...REP...REP...REP: ", repName, repList, whereExpr, untilExpr, repBodyOut
        thisActionItem = {'typeOfAction':"repetition" ,'repName':repName, 'whereExpr':whereExpr, 'untilExpr':untilExpr, 'repBody':repBodyOut, 'repList':repList}
    # Action sequence
    elif actionItem.actSeqID:
        actionListIn = actionItem
        #print "ACT_SEQ...ACT_SEQ...ACT_SEQ...ACT_SEQ...ACT_SEQ: ", actionListIn
        actionListOut = extractActSeqToActSeq(funcName, actionListIn)
        #print "ACT_SEQ...ACT_SEQ...ACT_SEQ...ACT_SEQ...ACT_SEQ: ", actionListOut
        thisActionItem = {'typeOfAction':"actionSeq", 'actionList':actionListOut}
    # Assign
    elif (actionItem.assignID):
        RHS = actionItem.rValue
        LHS = actionItem.lValue
        assignTag = ''
        print "ASSIGN...ASSIGN...ASSIGN...ASSIGN...ASSIGN...ASSIGN: ", RHS, LHS
        if (actionItem.assignTag):
            assignTag = actionItem.assignTag
        thisActionItem = {'typeOfAction':"assign", 'LHS':LHS, 'RHS':RHS, 'assignTag':assignTag}
    # Swap
    elif (actionItem.swapID):
        RHS = actionItem.RightLValue
        LHS = actionItem.lValue
        #print "SWAP...SWAP...SWAP...SWAP...SWAP...SWAP...SWAP...SWAP: ", swapRightLValue, swapLeftLValue
        thisActionItem = {'typeOfAction':"swap", 'LHS':LHS, 'RHS':RHS}
    # Function Call
    elif actionItem.calledFunc:
        calledFunc = actionItem.calledFunc
        parameters = actionItem.parameters
        #for param in actionItem.parameters:
            #print "param: ", rValue
            #parameters += rValue[0]
        #print "FUNC_CALL...FUNC_CALL...FUNC_CALL...FUNC_CALL...FUNC_CALL: ", calledFunc, parameters
        thisActionItem = {'typeOfAction':"funcCall", 'calledFunc':calledFunc, 'parameters':parameters}
    else:
        print "error in extractActItem"
        exit(1)
    #print "thisActionItem...thisActionItem...thisActionItem...thisActionItem: ", thisActionItem
    return thisActionItem

def extractActSeq( funcName, childActSeq):
    #print childActSeq
    actionList = childActSeq.actionList
    #print "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAextractActSeq"
    #print funcName, "****", actionList
    #print "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    actSeq = []
    for actionItem in actionList:
        thisActionItem = extractActItem(funcName, actionItem)
        #print "%%%%%%%%%%%%%%%%%%thisActionItem: ", thisActionItem
        actSeq.append(thisActionItem)
    #print "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAactSeq", actSeq
    return actSeq

def extractActSeqToFunc(funcName, funcBodyIn):
    #print "UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUextractActSeqToFunc"
    #print "objectName: ", objectName
    #print "funcName: ", funcName
    #print "funcBodyIn: ", funcBodyIn
    #print "UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUextractActSeqToFunc"
    childActSeq = extractActSeq( funcName, funcBodyIn)
    #print "UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUextractActSeqToFunc"
    #print childActSeq
    return childActSeq


def extractFuncBody(localObjectName,funcName, funcBodyIn):
    #ifBodyprint "EEEEEEEEEEEEEEEEEEEEEextractFuncBody"
    #print "localObjectName: ", localObjectName
    #print "funcName: ", funcName
    #print "funcBodyIn: ", funcBodyIn
    #print "EEEEEEEEEEEEEEEEEEEEEextractFuncBody"
    if funcBodyIn[0] == "<%":
        funcBodyOut = ""
        funcTextVerbatim = funcBodyIn[1][0]
    else:
        funcBodyOut = extractActSeqToFunc(funcName, funcBodyIn)
        funcTextVerbatim = ""
    return funcBodyOut, funcTextVerbatim

def extractFuncDef(localObjectName, localFieldResults):
    funcSpecs = []
    print "FFFFFFFFFFFFFFFFFFFFFFFFFextractFuncDef:"
    print localObjectName, "****", localFieldResults
    if (localFieldResults.fieldVarType =='<%'):
        returnType = localFieldResults.returnType[1][0]
    else:
        returnType = localFieldResults.fieldVarType
    #else: print 'Bad return type', localFieldResults.returnType[1]; exit(1);
    funcName = localFieldResults.funcName
    argList = localFieldResults.argList
    funcBodyIn = localFieldResults.funcBody
    print "FFFFFFFFFFFFFFFFFFFFFFFFFextractFuncDef:"
    print "returnType: ", returnType
    print "funcName: ", funcName
    print "argList: ", argList
    print "funcBody: ", funcBodyIn
    print "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    if localFieldResults.optionalTag:
        tagList = localFieldResults[tagDefList]
    else:
        tagList = []
    [funcBodyOut, funcTextVerbatim] = extractFuncBody(localObjectName,funcName, funcBodyIn)
    return [returnType, funcName, argList, tagList, funcBodyOut, funcTextVerbatim]

def extractFieldDefs(ProgSpec, ObjectName, fieldResults):
    print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXxextractFieldDefs"
    #print fieldResults
    for fieldResult in fieldResults:

        isNext=False;
        if(fieldResult.isNext): isNext=fieldResult.isNext
        if(fieldResult.owner): owner=fieldResult.owner;
        else: owner='me';
        if(fieldResult.fieldType): fieldType=fieldResult.fieldType;
        else: fieldType=None;
        if(fieldResult.fieldName): fieldName=fieldResult.fieldName;
        else: fieldName=None;
        if(fieldResult.givenValue): givenValue=fieldResult.givenValue
        else: givenValue=None;
        if(fieldResult.argList): argList=fieldResult.argList
        else: argList=None;

        if(fieldResult.flagDef):
            print "FLAG: ", fieldResult
            progSpec.addField(ProgSpec, ObjectName, False, owner, 'flag', fieldName, None, givenValue)
        elif(fieldResult.modeDef):
            print "MODE: ", fieldResult
            progSpec.addMode(ProgSpec, ObjectName, False, owner, 'mode', fieldName, givenValue, enumList)
        elif(fieldResult.constStr):
            print "CONST String: ", fieldResult
            progSpec.addField(ProgSpec, ObjectName, isNext, 'const', 'string', None, None, givenValue)
        elif(fieldResult.constNum):
            print "CONST Num: ", fieldResult
            progSpec.addField(ProgSpec, ObjectName, isNext, 'const', 'int', None, None, givenValue)
        elif(fieldResult.nameVal):
            print "NameAndVal: ", fieldResult
            progSpec.addField(ProgSpec, ObjectName, None, None, None, fieldName, argList, givenValue)
        elif(fieldResult.fullFieldDef):
            print "FULL: ", fieldResult
            progSpec.addField(ProgSpec, ObjectName, isNext, owner, fieldType, fieldName, argList, givenValue)
        else:
            print "Error in extractFieldDefs:", fieldResult
            exit(1)
    exit(1)


def extractBuildSpecs(buildSpecResults):
    resultBuildSpecs = []
    #print buildSpecResults
    for localBuildSpecs in buildSpecResults:
        spec = [localBuildSpecs.buildID, extractTagDefs(localBuildSpecs.buildDefList)]
        resultBuildSpecs.append(spec)
        #print spec
    return resultBuildSpecs

def extractObjectSpecs(localProgSpec, objNames, spec, stateType):
    #print spec
    objectName=spec.objectName[0]
    progSpec.addObject(localProgSpec, objNames, objectName, stateType)
    ###########Grab optional Object Tags
    #print "SSSSSSSSSSSSSSSSSSSSSSSSSspec.fieldDefs = ",spec.fieldDefs
    if spec.optionalTag:  #change so it generates an empty one if no field defs
        #print "SSSSSSSSSSSSSSSSSSSSSSSSSspec.tagDefList = ",spec.tagDefList
        objTags = extractTagDefs(spec.tagDefList)
        #fieldIDX = 4
    else:
        objTags = {}
        #fieldIDX = 3
    progSpec.addObjTags(localProgSpec, objectName, objTags)
    ###########Grab field defs
    extractFieldDefs(localProgSpec, objectName, spec.fieldDefs)

    return

def extractPatternSpecs(localProgSpec, objNames, spec):
    #print spec
    patternName=spec.objectName[0]
    patternArgWords=spec.CIDList
    progSpec.addPattern(localProgSpec, objNames, patternName, patternArgWords)
    return

def extractObjectOrPattern(localProgSpec, objNames, objectSpecResults):
    for spec in objectSpecResults:
        s=spec[0]
        if s == "model" or s == "struct" or s == "string" or s == "stream":
            extractObjectSpecs(localProgSpec, objNames, spec, s)
        elif s == "do":
            extractPatternSpecs(localProgSpec, objNames, spec)
        else:
            print "Error in extractObjectOrPattern; expected 'object' or 'do' and got '",spec[0],"'"
            exit(1)


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

def parseCodeDogString(inputString):
    inputString = comment_remover(inputString)
    results = parseInput(inputString)
    #print results.tagDefList
    tagStore = extractTagDefs(results.tagDefList)
    #print results.buildSpecList
    buildSpecs = extractBuildSpecs(results.buildSpecList)
    #print results.objectList
    localProgSpec = {}
    objNames = []
    extractObjectOrPattern(localProgSpec, objNames, results.objectList)
    objectSpecs = [localProgSpec, objNames]
    return[tagStore, buildSpecs, objectSpecs]

def AddToObjectFromText(spec, objNames, inputStr):
    inputStr = comment_remover(inputStr)
    print '####################\n',inputStr, "\n######################^\n\n\n"

    # (map of objects, array of objectNames, string to parse)
    results = objectList.parseString(inputStr, parseAll = True)
    print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n',results,'%%%%%%%%%%%%%%%%%%%%%%'
    extractObjectOrPattern(spec, objNames, results[0])
