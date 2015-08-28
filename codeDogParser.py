from pyparsing import Word, alphas, nums, Literal, Keyword, Optional, OneOrMore, ZeroOrMore, delimitedList, Group, ParseException, quotedString, Forward, StringStart, StringEnd, SkipTo


identifier = Word(alphas + nums + "_-")
CID = identifier
CIDList = delimitedList(CID, ',')
objectName = CID
cppType = (Keyword("int32") | Keyword("int64") | Keyword("double") | Keyword("char"))
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
funcType = varType
actionSeq = Literal("actionSeq")
argList =  Literal("argList") #+ (actionSeq | SkipTo("funcEnd"))
modeSpec = "mode" + ":" + CID + "[" + CIDList + "]"
varSpec = (Keyword("var") | Keyword("sPtr") | Keyword("uPtr") | Keyword("rPtr") ) + varType + ":" + CID
constSpec = "const" + ":" + CID + "=" + value 
funcSpec = "func" + funcType + ":" + CID + "(" + argList + ")" + Optional(":" + tagDefList)
fieldDef = "flag" + ":" + CID + ( modeSpec | varSpec | constSpec | funcSpec )
objectDef = Keyword("object") + CID + Optional(":" + tagDefList) + "{" + ZeroOrMore(fieldDef) + "}"
objectList = Group(ZeroOrMore(objectDef))
progSpec = tagDefList + buildSpecList #+ objectList
##########################################################
def parseInput(inputStr):
	try: 
		localResults = progSpec.parseString(inputStr, parseAll = True)
	
	except ParseException , pe:
		print "error parsing: " , pe
		exit(1)
	return localResults
	
def extractTagDefs(tagResults):
	localTagStore = {}
	for tagSpec in tagResults:
		#print tagSpec[0], "is", tagSpec[1]
		localTagStore[tagSpec[0]] = tagSpec[1]
	return localTagStore
	
def extractBuildSpecs(buildSpecResults):
	localBuildSpecs = []
	for localBuildSpecs in buildSpecResults:
		spec = [localBuildSpecs[0], extractTagDefs(localBuildSpecs[1])]
		#print spec
	#for buildSpecTag in localBuildSpecs[0]:
		#print buildSpecTag
		#spec[1][buildSpecTag[1] = buildSpecTag[3]
	return localBuildSpecs
	
def extractObjectSpecs(objectSpecResults):
	localObjectSpecs = objectSpecResults
	return localObjectSpecs
	
def parseCodeDogString(inputString):
	results = parseInput(inputString)
	tagStore = extractTagDefs(results[0])
	#print tagStore["BuildCmd"]
	buildSpecs = extractBuildSpecs(results[1])
	print buildSpecs
	objectSpecs = extractObjectSpecs("objectSpecsPlaceHolder")
	#print
	return[tagstore, buildSpecs, objectSpecs]
