# This module parses CodeDog syntax

import re
import progSpec
from pyparsing import Word, alphas, nums, Literal, Keyword, Optional, OneOrMore, ZeroOrMore, delimitedList, Group, ParseException, quotedString, Forward, StringStart, StringEnd, SkipTo

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
tagValue = (quotedString() | backTickString | Word(nums))("tagValue")
tagDef = Group(tagID + Literal("=").suppress() + tagValue)("tagDef")
tagDefList = Group(ZeroOrMore(tagDef))("tagDefList")
buildID = identifier("buildID")
buildDefList = tagDefList("buildDefList")
buildSpec = Group(buildID + Literal(":").suppress() + buildDefList + ";")("buildSpec")
buildSpecList = Group(OneOrMore(buildSpec))("buildSpecList")
#######################################
verbatim = Group(Literal(r"<%") + SkipTo(r"%>", include=True))
verbatim.setParseAction( reportParserPlace)
modeSpec = Keyword("mode") + ":" + CID + "[" + CIDList + "]"
varName = CID ("varName")
typeSpec = Forward()
typeSpec <<= Group((Keyword("var") | Keyword("sPtr") | Keyword("uPtr") | Keyword("rPtr") ) + (typeSpec | varType))
varSpec = (typeSpec + ":" + varName)("varSpec")
argList =  verbatim | Group(ZeroOrMore(Group(varSpec)))("argList")
createVar = varSpec("createVar")
constName = CID("constName")
constValue = value("constValue")
constSpec = Keyword("const") + cppType + ":" + constName + "=" + constValue("constSpec")
flagName = CID("flagName")
flagDef = Keyword("flag") + ":" + flagName("flagDef")
#######################################
lValue = Literal("lValue")("lValue")
rValue = Literal("rValue")("rValue")
rValueList = Group(delimitedList(rValue, ','))("rValueList")
funcCall = Group(CID + "(" + rValueList + ")")("funcCall")
assign = Group(lValue + Literal("<-") + rValue)("assign")
swap = Group(lValue + Literal("<->") + lValue)("l")
expr = Literal("expr")("expr")
########################################
actionSeq = Forward()
conditionalAction = Forward()
conditionalAction <<= Group(Keyword("if") + "(" + expr + ")" + actionSeq + Optional(Keyword("else") + ( actionSeq | conditionalAction)))("conditionalAction")
repeatedAction = Group(Keyword("withEach") + "(" + lValue + ")" + Keyword("where") + "(" + expr + ")" + Keyword("until") + "(" + expr + ")" + actionSeq)("repeatedAction")
action = (createVar | funcCall | assign | swap)("action")
actionSeq <<=  Group("{" + Group(ZeroOrMore(conditionalAction | repeatedAction | actionSeq | action)) + "}")("actionSeq")
#########################################
funcBody = Group( "<%" + SkipTo("%>", include=True))("funcBody")
returnType = typeSpec("returnType")
funcSpec = Keyword("func") + returnType + ":" + CID + "(" + argList + ")" + Optional(":" + tagDefList) + (actionSeq | funcBody)("funcSpec")
funcSpec.setParseAction( reportParserPlace)
fieldDef = Group(flagDef | modeSpec | varSpec | constSpec | funcSpec)("fieldDef")
objectName = CID("objectName")
objectDef = Group(Keyword("object") + objectName + Optional(":" + tagDefList) + "{" + Group(ZeroOrMore(fieldDef)) + "}")("objectDef")
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
        # Remove quotes
        if (len(tagVal)>=2 and (tagVal[0] == '"' or tagVal[0] == "'") and (tagVal[0]==tagVal[-1])):
            tagVal = tagVal[1:-1]
        #print tagSpec.tagID, " is ", tagVal
        localTagStore[tagSpec.tagID] = tagVal
    return localTagStore

def extractActSeq(localProgSpec, localObjectName, localFuncResults):
    print '<<<',localFuncResults,">>>"
    for actionList in localFuncResults:
        print 'AL[', localObjectName, ']'
        if (actionList != "{" and  actionList != "}"):
            for actionItems in actionList:
                print '[', actionItems, ']'
                if (actionItems[0] == 'var' or actionItems[0] == 'rPtr' or actionItems[0] == 'sPtr' or actionItems[0] == 'uPtr'):
                    fieldTag = actionItems[0]
                    fieldType = actionItems[1]
                    fieldName = actionItems[3]
                    print '**Create Local Var'
                elif (actionItems[0]== 'if'):
                    print '**Conditional Sequence'
                elif (actionItems[0]== 'withEach'):
                    print '**Repeated Action'
                elif (actionItems[0]== '{'):
                    print '**Action sequence'
                elif (actionItems[1]== '<-'):
                    print '**Assign'
                elif (actionItems[1]== '<->'):
                    print '**Swap'
                elif (actionItems[1]== '('):
                    print '**Function call'
                else:
                    print "error in extractActSeq"
                    exit(1)
    return "actionSeq"

def extractFuncBody(localProgSpec, localObjectName, localFuncResults):
    if localFuncResults[0] == "<%":
        funcActSeq = ""
        funcText = localFuncResults[1][0]
    else:
        funcActSeq = extractActSeq(localProgSpec, localObjectName, localFuncResults)
        funcText = ""
    return [funcActSeq, funcText]

def extractFuncDef(localProgSpec, localObjectName, localFieldResults):
    funcSpecs = []
    returnType = localFieldResults[1]
    funcName = localFieldResults[3]
    argList = localFieldResults[5]
    print "********************************************> ", argList
    if localFieldResults[7] == ":":
        tagList = localFieldResults[8]
        funcBody = extractFuncBody(localFieldResults[9])
    else:
        tagList = []
        print "LFR:", localFieldResults
        funcBody = extractFuncBody(localProgSpec, localObjectName, localFieldResults[7])
    return [returnType, funcName, argList, tagList, funcBody]

def extractFieldDefs(localProgSpec, localObjectName, fieldResults):
    print "^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^"
    print "Extracting fields for", localObjectName
    print "^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^"
    for fieldResult in fieldResults:

        fieldTag = fieldResult[0]
        varType =fieldResult.varType
        if(not isinstance(fieldTag, basestring)):
            varType=fieldTag[1]
            fieldTag=fieldTag[0]
        print 'fieldTag', fieldTag, varType
        if fieldTag == 'flag':
            #print fieldResult[2]
            progSpec.addFlag(localProgSpec, localObjectName, fieldResult[2])
        elif fieldTag == 'mode':
            progSpec.addMode(localProgSpec, localObjectName, fieldResult[2], fieldResult[4])
        elif (fieldTag == 'var' or fieldTag == 'rPtr' or fieldTag == 'sPtr' or fieldTag == 'uPtr'):
            print "TYPESPEC:", fieldResult
            progSpec.addField(localProgSpec, localObjectName, fieldTag, [fieldTag, varType], fieldResult.varName)
        elif fieldTag == 'const':
            constValue = fieldResult.constValue
            print"@@@@@"
            print fieldTag
            print constValue
            progSpec.addConst(localProgSpec, localObjectName, fieldResult.cppType, fieldResult.constName, constValue)
            #exit(1)
        elif fieldTag == 'func':
            localFuncSpecs = extractFuncDef(localProgSpec, localObjectName, fieldResult)
            #print localFuncSpecs[4]
            progSpec.addFunc(localProgSpec, localObjectName, localFuncSpecs[0], localFuncSpecs[1], localFuncSpecs[2], localFuncSpecs[3], localFuncSpecs[4])
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
    if spec[2] == ':':  #change so it generates an empty one if no field defs
        objTags = extractTagDefs(spec[3])
        fieldIDX = 4
    else:
        objTags = {}
        fieldIDX = 3
    progSpec.addObjTags(localProgSpec, spec.objectName, objTags)
    ###########Grab field defs
    extractFieldDefs(localProgSpec, spec.objectName, spec[fieldIDX])

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


