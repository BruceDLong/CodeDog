# This module parses CodeDog syntax

import re
import progSpec
from pyparsing import Word, alphas, nums, Literal, Keyword, Optional, OneOrMore, oneOf, ZeroOrMore, delimitedList, Group, ParseException, quotedString, Forward, StringStart, StringEnd, SkipTo

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
strMapVal = Forward()
value <<= (boolValue | intNum | floatNum | quotedString() | listVal | strMapVal)("value")
strMapVal <<= "{" + delimitedList( quotedString() + ":" + value, ",")  + "}"
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
modeSpec = Group(Keyword("mode")("modeIndicator") + ":" + CID ("modeName")+ "[" + CIDList("modeList") + "]")("modeSpec")
varName = CID ("varName")
typeSpec = Forward()
typeSpec <<= Group((Keyword("var")| Keyword("sPtr") | Keyword("uPtr") | Keyword("rPtr") | Keyword("list")) + (typeSpec | varType))("typeSpec")
varSpec = Group(typeSpec + Literal(":").suppress() + varName)("varSpec")
argList =  (verbatim | Group(Optional(delimitedList(Group(varSpec)))))("argList")

constName = CID("constName")
constValue = value("constValue")
constSpec = Group(Keyword("const")("constIndicator") + cppType + ":" + constName + "=" + constValue)("constSpec")
flagName = CID("flagName")
flagDef = Group(Keyword("flag")("flagIndicator") + ":" + flagName)("flagDef")
#######################################
lValue = Group(CID + Optional(Literal('.').suppress() + CID))("lValue")
swap = Group(lValue + Literal("<->")("swapID") + lValue ("RightLValue"))("swap")
expr = Forward()
funcCall = Forward()
factor = (value | ('(' + expr + ')') | funcCall)("factor")
term = (factor + ZeroOrMore(oneOf('* /') + factor))("term")
expr <<= (term + ZeroOrMore(oneOf('+ -') + term))("expr")
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
funcName = CID("funcName")
funcBody = (actionSeq | funcBodyVerbatim)("funcBody")
funcSpec = Group(Keyword("func")("funcIndicator") + returnType + ":" + CID("funcName") + "(" + argList + ")" + Optional(optionalTag + tagDefList) + funcBody)("funcSpec")
#funcSpec.setParseAction( reportParserPlace)
fieldDef = (flagDef | modeSpec | varSpec | constSpec | funcSpec)("fieldDef")
objectName = CID("objectName")
#########################################
fieldDefs = Group(ZeroOrMore(fieldDef))("fieldDefs")
objectDef = Group(Keyword("object") + objectName + Optional(optionalTag + tagDefList) + Literal("{").suppress() + fieldDefs + Literal("}").suppress())("objectDef")
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
    #print "FFFFFFFFFFFFFFFFFFFFFFFFFextractFuncDef:"
    #print localObjectName, "****", localFieldResults
    if (localFieldResults.returnType[0]=='<%'):
        returnType = localFieldResults.returnType[1][0]
    else:
        returnType = localFieldResults.returnType
    #else: print 'Bad return type', localFieldResults.returnType[1]; exit(1);
    funcName = localFieldResults.funcName
    argList = localFieldResults.argList
    funcBodyIn = localFieldResults.funcBody
    #print "FFFFFFFFFFFFFFFFFFFFFFFFFextractFuncDef:"
    #print "returnType: ", returnType
    #print "funcName: ", funcName
    #print "argList: ", argList
    #print "funcBody: ", funcBodyIn
    #print "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    if localFieldResults.optionalTag:
        tagList = localFieldResults[tagDefList]
    else:
        tagList = []
    [funcBodyOut, funcTextVerbatim] = extractFuncBody(localObjectName,funcName, funcBodyIn)
    return [returnType, funcName, argList, tagList, funcBodyOut, funcTextVerbatim]

def extractFieldDefs(localProgSpec, localObjectName, fieldResults):
    print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXxextractFieldDefs"
    print fieldResults
    for fieldResult in fieldResults:

        fieldTag = fieldResult[0]
       # varType =fieldResult.varType
        if(not isinstance(fieldTag, basestring)):
            varType=fieldTag[1]
            fieldTag=fieldTag[0]
        if (fieldResult.flagIndicator):
            thisFlagName = fieldResult.flagName
            #print "thisFlagName", thisFlagName
            progSpec.addFlag(localProgSpec, localObjectName, fieldResult[2])
        elif fieldResult.modeIndicator:
            thisModeName = fieldResult.modeName
            thisModeList = fieldResult.modeList
            #print "Mode: ", thisModeName, thisModeList
            progSpec.addMode(localProgSpec, localObjectName, thisModeName, thisModeList)
        elif fieldResult.constIndicator:
            constValue = fieldResult.constValue
            #print"@@@@@"
            #print fieldTag
            #print constValue
            progSpec.addConst(localProgSpec, localObjectName, fieldResult.cppType, fieldResult.constName, constValue)
            #exit(1)
        elif fieldResult.funcIndicator:
            # extract function into an array
            [returnType, funcName, argList, tagList, funcBodyOut, funcTextVerbatim] = extractFuncDef( localObjectName, fieldResult)
            #print "FUNCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"
            #print returnType
            #print funcName
            #print argList
            #print tagList
            #print funcBodyOut
            #print "FUNCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"
            progSpec.addFunc(localProgSpec, localObjectName, returnType, funcName, argList, tagList, funcBodyOut, funcTextVerbatim)
        elif (fieldResult.varName):
            thisTypeSpec = fieldResult.typeSpec
            thisVarName = fieldResult.varName
            kindOfField = thisTypeSpec[0]
            print "VAR FIELD: ", kindOfField, thisTypeSpec, thisVarName
            progSpec.addField(localProgSpec, localObjectName, kindOfField, thisTypeSpec, thisVarName)
        else:
            print "Error in extractFieldDefs"
            print fieldResult
            exit(1)


def extractBuildSpecs(buildSpecResults):
    resultBuildSpecs = []
    #print buildSpecResults
    for localBuildSpecs in buildSpecResults:
        spec = [localBuildSpecs.buildID, extractTagDefs(localBuildSpecs.buildDefList)]
        resultBuildSpecs.append(spec)
        #print spec
    return resultBuildSpecs

def extractObjectSpecs(localProgSpec, objNames, spec):
    #print spec
    ##########Grab object name
    progSpec.addObject(localProgSpec, objNames, spec.objectName)
    ###########Grab optional Object Tags
    #print "SSSSSSSSSSSSSSSSSSSSSSSSSspec.fieldDefs = ",spec.fieldDefs
    if spec.optionalTag:  #change so it generates an empty one if no field defs
        #print "SSSSSSSSSSSSSSSSSSSSSSSSSspec.tagDefList = ",spec.tagDefList
        objTags = extractTagDefs(spec.tagDefList)
        #fieldIDX = 4
    else:
        objTags = {}
        #fieldIDX = 3
    progSpec.addObjTags(localProgSpec, spec.objectName, objTags)
    ###########Grab field defs
    extractFieldDefs(localProgSpec, spec.objectName, spec.fieldDefs)

    return

def extractPatternSpecs(localProgSpec, objNames, spec):
    #print spec
    patternName=spec.objectName
    patternArgWords=spec.CIDList
    progSpec.addPattern(localProgSpec, objNames, patternName, patternArgWords)
    return

def extractObjectOrPattern(localProgSpec, objNames, objectSpecResults):
    for spec in objectSpecResults:
        if spec[0] == "object":
            extractObjectSpecs(localProgSpec, objNames, spec)
        elif spec[0] == "do":
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
