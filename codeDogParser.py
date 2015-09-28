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
verbatim.setParseAction( reportParserPlace)
modeSpec = (Keyword("mode")("modeIndicator") + ":" + CID ("modeName")+ "[" + CIDList("modeList") + "]")("modeSpec")
varName = CID ("varName")
typeSpec = Forward()
typeSpecKind = (Keyword("var") | Keyword("sPtr") | Keyword("uPtr") | Keyword("rPtr"))("typeSpecKind")
typeSpec <<=  typeSpecKind + (typeSpec | varType)
varSpec = Group(typeSpec + Literal(":").suppress() + varName)("varSpec")
argList =  verbatim | Group(Optional(delimitedList(Group(varSpec))))("argList")
createVar = varSpec("createVar")
constName = CID("constName")
constValue = value("constValue")
constSpec = Keyword("const")("constIndicator") + cppType + ":" + constName + "=" + constValue("constSpec")
flagName = CID("flagName")
flagDef = Keyword("flag")("flagIndicator") + ":" + flagName("flagDef")
#######################################
lValue = Literal("lValue")("lValue")
rValue = Literal("rValue")("rValue")
rValueList = Group(delimitedList(rValue, ','))("rValueList")
funcCallIndicator = Literal("(") ("funcCallIndicator")
funcCall = Group(CID + funcCallIndicator + rValueList + ")")("funcCall")
actionID = ("actionID")
assign = Group(lValue + Literal("<-") + rValue)("assign")
RightLValue = lValue ("RightLValue")
swap = Group(lValue + Literal("<->") + RightLValue)("swap")
expr = (Literal("expr"))("expr")
########################################
actionSeq = Forward()
conditionalAction = Forward()
conditionalID = Keyword("if")("conditionalID")
optionalElse = (Keyword("else")  + ( actionSeq | conditionalAction) )("optionalElse")
conditionalAction <<= Group(conditionalID + "(" + expr + ")" + actionSeq + Optional(optionalElse))("conditionalAction")
repeatedActionID = Keyword("withEach")("repeatedActionID")
untilExpr = expr ("untilExpr")
whereExpr = expr ("whereExpr")
repeatedAction = Group(repeatedActionID + "(" + lValue + ")" + Keyword("where") + "(" + whereExpr + ")" + Keyword("until") + "(" + untilExpr + ")" + actionSeq)("repeatedAction")
action = (createVar | funcCall | assign | swap)("action")
actionList = Group( ZeroOrMore (conditionalAction | repeatedAction | actionSeq | action))("actionList")
actionSeqIndicator = Literal("{") ("actionSeqIndicator")
actionSeq <<=  Group(actionSeqIndicator + actionList + Literal("}")) ("actionSeq")
#########################################
funcBodyVerbatim = Group( "<%" + SkipTo("%>", include=True))("funcBodyVerbatim")
returnType = verbatim | typeSpec("returnTypeSpec")("returnType")
optionalTag = Literal(":")("optionalTag")
funcName = CID("funcName")
funcBody = (actionSeq | funcBodyVerbatim)("funcBody")
funcSpec = (Keyword("func")("funcIndicator") + returnType + ":" + funcName + "(" + argList + ")" + Optional(optionalTag + tagDefList) + funcBody)("funcSpec")
#funcSpec.setParseAction( reportParserPlace)
fieldDef = Group(flagDef | modeSpec | varSpec("fieldVar") | constSpec | funcSpec)("fieldDef")
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


def extractActSeqToActSeq(objectName, funcName, childActSeqRef):
    #print "QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQUextractActSeqToActSeq"
    #print objectName
    #print funcName
    #print childActSeqRef
    #print "QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQextractActSeqToActSeq"
    childActSeq = extractActSeq( objectName, funcName, childActSeqRef)
    return childActSeq
    ##progSpec.addActionSeqToActionSeq(objectName, funcName, childActSeq)

def extractActSeq( objectName, funcName, childActSeqRef):
    actionList = childActSeqRef.actionList
    #print "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAextractActSeq"
    #print objectName, funcName, "****", actionList
    #print "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    for actionItem in actionList:
        # typeSpecKind: var | sPtr | uPtr | rPtr
        if actionItem.typeSpecKind:  
            fieldTypeSpecKind = actionItem.typeSpecKind
            fieldType = actionItem.varType
            fieldName = actionItem.varName
            #progSpec.addLocalVar(objectName, funcName,  fieldTypeSpecKind, fieldType, fieldName)
        # Conditional if
        elif actionItem.conditionalID:
            thisExpr = actionItem.expr
            thisActionSeq = actionItem.actionSeq
            thisElse = actionItem.optionalElse
            #progSpec.addConditional(objectName, funcName, thisExpr, thisActionSeq, thisElse)
        # Repeated Action withEach
        elif actionItem.repeatedActionID:
            thisLValue = actionItem.lValue
            thisActionSeq = actionItem.actionSeq
            thisWhereExpr = actionItem.whereExpr
            thisUntilExpr = actionItem.untilExpr
            #progSpec.addRepetition(objectName, funcName, thisLValue, thisActionSeq, thisWhereExpr, thisUntilExpr)
        ####################################################### Action Sequence
        elif actionItem.actionSeqIndicator:
            thisActionList = actionItem.actionList
            #print '*************Action sequence: ', thisActionList
            childActSeq = extractActSeqToActSeq(objectName, funcName, thisActionList)
            return childActSeq
        # Assign
        elif (actionItem[1]== '<-'):
            rightValue = actionItem.rValue
            leftValue = actionItem.lValue
            progSpec.addAssign(objectName, funcName, rightValue, leftValue)
        # Swap
        elif (actionItem[1]== '<->'):
            rightLValue = actionItem.RightLValue
            leftLValue = actionItem.lValue
            progSpec.addSwap(objectName, funcName, leftLValue, rightLValue)
        # Function Call
        elif actionItem.funcCallIndicator:
            thisFuncCall = actionItem.rValueList
            progSpec.addFuncCall(objectName, funcName, thisFuncCall)
        else:
            print "error in extractActSeq"
            exit(1)
    return "actionSeq"

def extractActSeqToFunc(objectName, funcName, funcResults):
    #print "UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUextractActSeqToFunc"
    #print objectName
    #print funcName
    #print funcResults
    #print "UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUextractActSeqToFunc"
    childActSeq = extractActSeq( objectName, funcName, funcResults)
    return childActSeq
    
    

def extractFuncBody(localObjectName, funcResults, funcName):
    #print "EEEEEEEEEEEEEEEEEEEEEextractFuncBody"
    #print funcResults
    #print localObjectName
    #print funcResults
    #print "EEEEEEEEEEEEEEEEEEEEEextractFuncBody"
    if funcResults[0] == "<%":
        funcActSeq = ""
        funcText = funcResults[1][0]
    else:
        funcActSeq = extractActSeqToFunc( localObjectName, funcName, funcResults)
        funcText = ""
    

def extractFuncDef(localObjectName, localFieldResults):
    funcSpecs = []
    #print "FFFFFFFFFFFFFFFFFFFFFFFFFextractFuncDef:"
    #print localObjectName, "****", localFieldResults
    returnType = localFieldResults.returnType
    funcName = localFieldResults.funcName
    argList = localFieldResults.argList
    funcBodyIn = localFieldResults.funcBody
    #print "FFFFFFFFFFFFFFFFFFFFFFFFFextractFuncDef:"
    #print "returnType", returnType
    #print "funcName", funcName
    #print "argList", argList
    #print "funcBody", funcBody
    #print "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
    if(returnType[0]=='<%'): print "RETURN TYPE:", returnType
    if localFieldResults.optionalTag:
        tagList = localFieldResults[tagDefList]
    else:
        tagList = []
    funcBodyOut = extractFuncBody(localObjectName,funcBodyIn, funcName)
    return [returnType, funcName, argList, tagList, funcBodyOut]

def extractFieldDefs(localProgSpec, localObjectName, fieldResults):
    for fieldResult in fieldResults:
        #print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXxextractFieldDefs"
        #print localProgSpec, "****", localObjectName, "****", fieldResult
        #print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXxextractFieldDefs"
        fieldTag = fieldResult[0]
        varType =fieldResult.varType
        if(not isinstance(fieldTag, basestring)):
            varType=fieldTag[1]
            fieldTag=fieldTag[0]
        if (fieldResult.flagIndicator):
            thisFlagName = fieldResult.flagName
            print "thisFlagName", thisFlagName
            progSpec.addFlag(localProgSpec, localObjectName, fieldResult[2])
        elif fieldResult.modeIndicator:
            thisModeName = fieldResult.modeName
            thisModeList = fieldResult.modeList
            print "Mode: ", thisModeName, thisModeList
            progSpec.addMode(localProgSpec, localObjectName, thisModeName, thisModeList)
        elif fieldResult.constIndicator:
            constValue = fieldResult.constValue
            progSpec.addConst(localProgSpec, localObjectName, fieldResult.cppType, fieldResult.constName, constValue)
            #exit(1)
        elif fieldResult.funcIndicator:
            localFuncSpecs = extractFuncDef( localObjectName, fieldResult)
            #print "FUNCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"
            #print localFuncSpecs
            #print "FUNCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"
            thisFuncReturns = localFuncSpecs[0]
            thisFuncName = localFuncSpecs[1]
            thisFuncArgList = localFuncSpecs[2]
            thisFuncTags = localFuncSpecs[3]
            thisFuncBody = localFuncSpecs[4]
           
            print thisFuncReturns
            print thisFuncName
            print thisFuncArgList
            print thisFuncTags
            print thisFuncBody
            progSpec.addFunc(localProgSpec, localObjectName, thisFuncReturns, thisFuncName, thisFuncArgList, thisFuncTags, thisFuncBody)
        elif (fieldResult.fieldVar): 
            progSpec.addField(localProgSpec, localObjectName, fieldTag, [fieldTag, varType], fieldResult.varName)
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
    #print "SSSSSSSSSSSSSSSSSSSSSSSSSspec = ", spec
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


