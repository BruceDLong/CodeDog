# This module parses CodeDog syntax

import re
import progSpec
from pyparsing import Word, alphas, nums, Literal, Keyword, Optional, OneOrMore, oneOf, ZeroOrMore, delimitedList, Group, ParseException, quotedString, Forward, StringStart, StringEnd, SkipTo, Combine

def reportParserPlace(s, loc, toks):
    print "    PARSING AT char",loc, toks

# # # # # # # # # # # # #   BNF Parser Productions for CodeDog syntax   # # # # # # # # # # # # #

#######################################   T A G S   A N D   B U I L D - S P E C S
identifier = Word(alphas + nums + "_-")("identifier")
tagID = identifier("tagID")
tagDefList = Forward()
tagValue = Forward()
tagMap  = Group('{' + tagDefList + '}')
tagList = Group('[' + Group(Optional(delimitedList(Group(tagValue), ','))) + ']')
backTickString = Literal("`").suppress() + SkipTo("`") + Literal("`").suppress()("backTickString")
tagValue <<= (quotedString() | backTickString | Word(alphas+nums+'-_.') | tagList | tagMap)("tagValue")
tagDef = Group(tagID + Literal("=").suppress() + tagValue)("tagDef")
tagDefList <<= Group(ZeroOrMore(tagDef))("tagDefList")
#tagDefList.setParseAction(reportParserPlace)

buildID = identifier("buildID")
buildDefList = tagDefList("buildDefList")
buildSpec = Group(buildID + Literal(":").suppress() + buildDefList + ";")("buildSpec")
buildSpecList = Group(OneOrMore(buildSpec))("buildSpecList")
#buildSpec.setParseAction(reportParserPlace)

#######################################   B A S I C   T Y P E S
CID = identifier("CID")
CIDList = Group(delimitedList(CID, ','))("CIDList")
objectName = CID("objectName")
cppType = (Keyword("void") | Keyword("bool") | Keyword("int32") | Keyword("int64") | Keyword("double") | Keyword("char") | Keyword("uint32") | Keyword("uint64") | Keyword("string"))("cppType")
intNum = Word(nums)("intNum")
numRange = intNum + ".." + intNum("numRange")
varType = (objectName | cppType | numRange | Keyword("mesg"))("varType")
boolValue = (Keyword("true") | Keyword("false"))("boolValue")
floatNum = intNum + Optional("." + intNum)("floatNum")
value = Forward()
listVal = "[" + delimitedList(value, ",") + "]"
strMapVal = "{" + delimitedList( quotedString() + ":" + value, ",")  + "}"
value <<= (boolValue | intNum | floatNum | quotedString() | listVal | strMapVal)("value")

#######################################   E X P R E S S I O N S
expr = Forward()
funcCall = Forward()
arrayRef = Group('[' + expr('startOffset') + Optional(( ':' + expr('endOffset')) | ('..' + expr('itemLength'))) + ']')
secondRefSegment = (Literal('.').suppress() + CID | arrayRef)
firstRefSegment = (CID | arrayRef)
varRef = Group(firstRefSegment + ZeroOrMore(secondRefSegment))("varRef")
parameters = Forward()
varFuncRef = Group(varRef("varName") + Optional(parameters))("varFuncRef")
lValue = varRef("lValue")
factor = Group( value | ('(' + expr + ')') | ('!' + expr) | ('-' + expr) | varFuncRef)("factor")
term = Group( factor + Group(Optional(OneOrMore(Group(oneOf('* / %') + factor )))))("term")
plus = Group( term  + Group(Optional(OneOrMore(Group(oneOf('+ -') + term )))))("plus")
comparison = Group( plus + Group(Optional(OneOrMore(Group(oneOf('< > <= >=') + plus )))))("comparison")
isEQ = Group( comparison  + Group(Optional(OneOrMore(Group(oneOf('= !=') + comparison )))))("isEQ")
logAnd = Group( isEQ  + Group(Optional(OneOrMore(Group('and' + isEQ )))))
expr <<= Group( logAnd + Group(Optional(OneOrMore(Group('or' + logAnd )))))("expr")
swap = Group(lValue + Literal("<->")("swapID") + lValue ("RightLValue"))("swap")
rValue = Group(expr)("rValue")
assign = (lValue + Combine(Literal("<") + Optional(Word(alphas + nums + '_')("assignTag")) + Literal("-"))("assignID") + rValue)("assign")
parameters <<= (Literal("(").suppress() + Optional(delimitedList(rValue, ',')) + Literal(")").suppress())("parameters")
funcCall <<= Group(varRef+ parameters("parameters"))("funcCall")

########################################   F U N C T I O N S
verbatim = Group(Literal(r"<%") + SkipTo(r"%>", include=True))
fieldDef = Forward()
argList =  (verbatim | Group(Optional(delimitedList(Group( fieldDef)))))("argList")
actionSeq = Forward()
conditionalAction = Forward()
conditionalAction <<= Group(Group(Keyword("if") + "(" + expr("ifCondition") + ")" + actionSeq("ifBody"))("ifStatement")+ Optional(Keyword("else") + (actionSeq | conditionalAction)("elseBody"))("optionalElse"))("conditionalAction")
repeatedAction = Group(
            Keyword("withEach")("repeatedActionID")  + CID("repName") + "in"+ lValue("repList") + ":"
            + Optional(Keyword("where") + "(" + expr("whereExpr") + ")")
            + Optional(Keyword("until") + "(" + expr("untilExpr") + ")")
            + actionSeq
        )("repeatedAction")

action = Group(funcCall | assign | fieldDef('fieldDef'))
actionSeq <<=  Group(Literal("{")("actSeqID") + ( ZeroOrMore (conditionalAction | repeatedAction | actionSeq | action))("actionList") + Literal("}")) ("actionSeq")
funcBodyVerbatim = Group( "<%" + SkipTo("%>", include=True))("funcBodyVerbatim")
funcBody = (actionSeq | funcBodyVerbatim)("funcBody")

#########################################   F I E L D   D E S C R I P T I O N S
nameAndVal = Group(
          (Literal(":") + CID("fieldName") + "(" + argList + Literal(")")('argListTag') + "=" + funcBody )         # Function Definition
        | (Literal(":") + CID("fieldName")  + "=" + value("givenValue"))
        | (Literal(":") + "=" + (value("givenValue") | funcBody))
        | (Literal(":") + CID("fieldName")  + Optional("(" + argList + Literal(")")('argListTag')))
    )("nameAndVal")

arraySpec = Group ('[' + Optional(intNum | numRange) + ']')("arraySpec")
meOrMy = (Keyword("me") | Keyword("my"))
modeSpec = (Optional(meOrMy)('owner') + Keyword("mode")("modeIndicator") + Literal("[") + CIDList("modeList") + Literal("]") + nameAndVal("modeName"))("modeSpec")
flagDef  = (Optional(meOrMy)('owner') + Keyword("flag")("flagIndicator") + nameAndVal )("flagDef")
baseType = (cppType)("baseType")

#########################################   O B J E C T   D E S C R I P T I O N S
objectName = Combine(CID + Optional('::' + CID))("objectName")
fieldDefs = (Literal("{").suppress() + ZeroOrMore(fieldDef)+ Literal("}").suppress())("fieldDefs")
SetFieldStmt = Group(lValue + '=' + rValue)
coFactualEL  = (Literal("(") + Group(fieldDefs + "<=>" + Group(OneOrMore(SetFieldStmt + Literal(';').suppress())))  + ")") ("coFactualEL")
alternateEl  = (Literal("[") + Group(OneOrMore(fieldDefs + Optional("|").suppress())) + Literal("]"))("alternateEl")
anonModel = (fieldDefs | alternateEl | coFactualEL ) ("anonModel")
owners = (Keyword("const") | Keyword("me") | Keyword("my") | Keyword("our") | Keyword("their"))
fullFieldDef = (Optional('>')('isNext') + Optional(owners)('owner') + (baseType | objectName | anonModel)('fieldType') +Optional(arraySpec) + Optional(nameAndVal))("fullFieldDef")
fieldDef <<= Group(flagDef('flagDef') | modeSpec('modeDef') | quotedString()('constStr') | intNum('constNum') | nameAndVal('nameVal') | fullFieldDef('fullFieldDef'))("fieldDef")
modelTypes = (Keyword("model") | Keyword("struct") | Keyword("string") | Keyword("stream"))
objectDef = Group(modelTypes + objectName + Optional(Literal(":")("optionalTag") + tagDefList) + (Keyword('auto') | anonModel))("objectDef")
doPattern = Group(Keyword("do") + objectName + Literal("(").suppress() + CIDList + Literal(")").suppress())("doPattern")
objectList = Group(ZeroOrMore(objectDef | doPattern))("objectList")

#########################################   P A R S E R   S T A R T   S Y M B O L
progSpecParser = (tagDefList + buildSpecList + objectList)("progSpecParser")

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

def extractActSeqToActSeq(funcName, childActSeq):
    #print "QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQUextractActSeqToActSeq"
    #print childActSeq
    #print "QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQextractActSeqToActSeq"
    actSeqData = extractActSeq(funcName, childActSeq)
    return actSeqData

def parseResultToArray(parseSegment):
    myList = []
    for seg in parseSegment:
        myList.append(seg)
    return myList


def extractActItem(funcName, actionItem):
    thisActionItem='error'
    # Create Variable: var | sPtr | uPtr | rPtr | list
    #print "ACTIONITEM:", actionItem
    if actionItem.fieldDef:
        thisTypeSpec = actionItem.typeSpec
        thisVarName = actionItem.varName
        #print 'TypeSpec and VarName: ', thisTypeSpec, thisVarName
        thisActionItem = {'typeOfAction':"newVar", 'typeSpec':thisTypeSpec, 'varName':thisVarName}
    elif actionItem.ifStatement:    # Conditional if
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
        #print "\n IF........IF........IF........IF........IF: ", ifCondition, ifBodyOut, elseBodyOut

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
    elif (actionItem.assign):
        RHS = parseResultToArray(actionItem.rValue)
        LHS = parseResultToArray(actionItem.lValue)
        assignTag = ''
        if (actionItem.assignTag):
            assignTag = actionItem.assignTag
        #print RHS, LHS
        thisActionItem = {'typeOfAction':"assign", 'LHS':LHS, 'RHS':RHS, 'assignTag':assignTag}
    # Swap
    elif (actionItem.swapID):
        RHS = actionItem.RightLValue
        LHS = actionItem.lValue
        #print "SWAP...SWAP...SWAP...SWAP...SWAP...SWAP...SWAP...SWAP: ", swapRightLValue, swapLeftLValue
        thisActionItem = {'typeOfAction':"swap", 'LHS':LHS, 'RHS':RHS}
    # Function Call
    elif actionItem.funcCall:
        calledFunc = (actionItem.funcCall.varRef[0])
        parameters = actionItem.funcCall.parameters
        print "FUNC_CALL...FUNC_CALL...FUNC_CALL...FUNC_CALL...FUNC_CALL: [", calledFunc, '], <', parameters, '>\n\n'
        thisActionItem = {'typeOfAction':"funcCall", 'calledFunc':calledFunc, 'parameters':parameters}
    else:
        print "error in extractActItem"
        print "actionItem", actionItem
        exit(1)
    #print "thisActionItem...thisActionItem...thisActionItem...thisActionItem: ", thisActionItem
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
    #print "EEEEEEEEEEEEEEEEEEEEEextractFuncBody"
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
    #print funcBodyOut
    return funcBodyOut, funcTextVerbatim

def extractFieldDefs(ProgSpec, ObjectName, fieldResults):
    print "    EXTRACTING Field Defs for", ObjectName
    #print fieldResults
    for fieldResult in fieldResults:
        #print fieldResult
        isNext=False;
        if(fieldResult.isNext): isNext=fieldResult.isNext
        if(fieldResult.owner): owner=fieldResult.owner;
        else: owner='me';
        if(fieldResult.fieldType): fieldType=fieldResult.fieldType;
        else: fieldType=None;
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
                argList=nameAndVal.argList
                #print 'argList: ', argList
            else: argList=None;
        else:
            givenValue=None;
            fieldName=None;
        if(fieldResult.flagDef):
            print "        FLAG: ", fieldResult
            progSpec.addField(ProgSpec, ObjectName, False, owner, 'flag', fieldName, None, givenValue)
        elif(fieldResult.modeDef):
            print "        MODE: ", fieldResult
            progSpec.addMode(ProgSpec, ObjectName, False, owner, 'mode', fieldName, givenValue, enumList)
        elif(fieldResult.constStr):
            print "        CONST String: ", fieldResult
            progSpec.addField(ProgSpec, ObjectName, isNext, 'const', 'string', None, None, givenValue)
        elif(fieldResult.constNum):
            print "        CONST Num: ", fieldResult
            progSpec.addField(ProgSpec, ObjectName, isNext, 'const', 'int', None, None, givenValue)
        elif(fieldResult.nameVal):
            print "        NameAndVal: ", fieldResult
            progSpec.addField(ProgSpec, ObjectName, None, None, None, fieldName, argList, givenValue)
        elif(fieldResult.fullFieldDef):
            print "        FULL FIELD: ", fieldResult
            progSpec.addField(ProgSpec, ObjectName, isNext, owner, fieldType, fieldName, argList, givenValue)
        else:
            print "Error in extractFieldDefs:", fieldResult
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
