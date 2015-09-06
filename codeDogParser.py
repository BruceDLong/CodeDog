# This module parses CodeDog syntax

import re
import progSpec
from pyparsing import Word, alphas, nums, Literal, Keyword, Optional, OneOrMore, ZeroOrMore, delimitedList, Group, ParseException, quotedString, Forward, StringStart, StringEnd, SkipTo

# BNF Parser Productions for CodeDog syntax
identifier = Word(alphas + nums + "_-")
CID = identifier
CIDList = Group(delimitedList(CID, ','))
objectName = CID
cppType = (Keyword("int32") | Keyword("int64") | Keyword("double") | Keyword("char") | Keyword("uint32") | Keyword("uint64") | Keyword("string"))
numRange = Forward()
value = Forward()
varType = (objectName | cppType | numRange | "string" | "mesg")
boolValue = (Keyword("true") | Keyword("false"))
intNum = Word(nums)
numRange <<= intNum + ".." + intNum
floatNum = intNum + Optional("." + intNum)
listVal = "[" + delimitedList(value, ",") + "]"
strMapVal = Forward()
value <<= (boolValue | intNum | floatNum | quotedString() | listVal | strMapVal)
strMapVal <<= "{" + delimitedList( quotedString() + ":" + value, ",")  + "}"
backTickString = Literal("`").suppress() + SkipTo("`") + Literal("`").suppress()
tagDef = Group(identifier + Literal("=").suppress() + (quotedString() | backTickString | Word(nums)))
tagDefList = Group(ZeroOrMore(tagDef))
buildSpec = Group(identifier + Literal(":").suppress() + tagDefList + ";")
buildSpecList = Group(OneOrMore(buildSpec))
returnType = varType
actionSeq = Literal("actionSeq")
argList =  Literal("argList")
modeSpec = Keyword("mode") + ":" + CID + "[" + CIDList + "]"
varSpec = (Keyword("var") | Keyword("sPtr") | Keyword("uPtr") | Keyword("rPtr") ) + varType + ":" + CID
constSpec = Keyword("const") + cppType + ":" + CID + "=" + value
flagDef = Keyword("flag") + ":" + CID
funcBody = Group( SkipTo("FEND", include=True))
funcSpec = Keyword("func") + returnType + ":" + CID + "(" + argList + ")" + Optional(":" + tagDefList) + (actionSeq | funcBody)
fieldDef = Group(flagDef | modeSpec | varSpec | constSpec | funcSpec)
objectDef = Group(Keyword("object") + CID + Optional(":" + tagDefList) + "{" + Group(ZeroOrMore(fieldDef)) + "}")
#######################
doPattern = Group(Keyword("do") + CID + Literal("(").suppress() + CIDList + Literal(")").suppress())
objectList = Group(ZeroOrMore(objectDef | doPattern))
progSpecParser = tagDefList + buildSpecList + objectList

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
        tagVal = tagSpec[1]
        if (len(tagVal)>=2 and (tagVal[0] == '"' or tagVal[0] == "'") and (tagVal[0]==tagVal[-1])):
            tagVal = tagVal[1:-1]
        localTagStore[tagSpec[0]] = tagVal
    return localTagStore

def extractFuncBody(localFuncResults):
    print localFuncResults
    if localFuncResults == "actionSeq":
        funcActSeq = localFuncResults
        funcText = ""
    else:
        funcActSeq = ""
        funcText = localFuncResults
    return [funcActSeq, funcText]

def extractFuncDef(localFieldResults):

    funcSpecs = []
    returnType = localFieldResults[1]
    funcName = localFieldResults[3]
    argList = localFieldResults[5]
    if localFieldResults[7] == ":":
        tagList = localFieldResults[8]
        funcBody = extractFuncBody(localFieldResults[9])
    else:
        tagList = []
        funcBody = extractFuncBody(localFieldResults[7])
    return [returnType, funcName, argList, tagList, funcBody]

def extractFieldDefs(localProgSpec, localObjectName, fieldResults):
    for fieldResult in fieldResults:
        fieldTag = fieldResult[0]
        if fieldTag == 'flag':
            progSpec.addFlag(localProgSpec, localObjectName, fieldResult[2])
        elif fieldTag == 'mode':
            progSpec.addMode(localProgSpec, localObjectName, fieldResult[2], fieldResult[4])
        elif (fieldTag == 'var' or fieldTag == 'rPtr' or fieldTag == 'sPtr' or fieldTag == 'uPtr'):
            fieldType = fieldResult[1]
            fieldName = fieldResult[3]
            progSpec.addField(localProgSpec, localObjectName, fieldTag, fieldType, fieldName)
        elif fieldTag == 'const':
            cppType = fieldResult[1]
            constName = fieldResult[3]
            constValue = fieldResult[5]
            progSpec.addConst(localProgSpec, localObjectName, cppType, constName, constValue)
            #exit(1)
        elif fieldTag == 'func':
            localFuncSpecs = extractFuncDef(fieldResult)
            #print localFuncSpecs[4]
            progSpec.addFunc(localProgSpec, localObjectName, localFuncSpecs[0], localFuncSpecs[1], localFuncSpecs[2], localFuncSpecs[3], localFuncSpecs[4])
        else:
            print "Error in extractFieldDefs"
            print fieldResult
            exit(1)


def extractBuildSpecs(buildSpecResults):
    resultBuildSpecs = []
    for localBuildSpecs in buildSpecResults:
        spec = [localBuildSpecs[0], extractTagDefs(localBuildSpecs[1])]
        resultBuildSpecs.append(spec)
        #print spec
    return resultBuildSpecs

def extractObjectSpecs(localProgSpec, objNames, spec):
    print "extractObjectSpecs"
    ##########Grab object name
    objectName = spec[1]
    progSpec.addObject(localProgSpec, objNames, objectName)

    ###########Grab optional Object Tags
    if spec[2] == ':':  #change so it generates an empty one if no field defs
        objTags = extractTagDefs(spec[3])
        fieldIDX = 4
    else:
        objTags = {}
        fieldIDX = 3
    progSpec.addObjTags(localProgSpec, objectName, objTags)
    ###########Grab field defs
    extractFieldDefs(localProgSpec, objectName, spec[fieldIDX])

    return

def extractPatternSpecs(localProgSpec, objNames, spec):
    #print "extractPatternSpecs"
    patternName=spec[1]
    patternArgWords=spec[2]
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
    #print "parse"
    tagStore = extractTagDefs(results[0])
    #print tagStore["BuildCmd"]
    buildSpecs = extractBuildSpecs(results[1])
    #print buildSpecs[2]
    localProgSpec = {}
    objNames = []
    extractObjectOrPattern(localProgSpec, objNames, results[2])
    objectSpecs = [localProgSpec, objNames]
    return[tagStore, buildSpecs, objectSpecs]

def AddToObjectFromText(spec, objNames, inputStr):
    print '####################\n',inputStr, "\n######################^\n\n\n"
    # (map of objects, array of objectNames, string to parse)
    results = objectList.parseString(inputStr, parseAll = True)
    print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n',results,'%%%%%%%%%%%%%%%%%%%%%%'
    extractObjectOrPattern(spec, objNames, results[0])


