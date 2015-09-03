# CodeGenerator_CPP.py
import progSpec

def bitsNeeded(n):
    if n <= 1:
        return 0
    else:
        return 1 + bitsNeeded((n + 1) / 2)

def fetchTagValue(tagStoreArray, tagToFind):
    for tagStore in reversed(tagStoreArray):
        if(tagToFind in tagStore):
            return tagStore[tagToFind]
    return None


def processFlagAndModeFields(objects, objectName, tags):
	print "Procesing flag/modes for:", objectName
	flagsVarNeeded = False
	bitCursor=0
	structEnums="\n///////////////////////////////////////////////////\n////   Flag and Mode Definitions \n\n"
	ObjectDef = objects[0][objectName]
	for field in ObjectDef['fields']:
		print field
		kindOfField=field['kindOfField'];
		fieldName=field['fieldName'];
		accessDefines = ""
		print "FIELDNAME:", fieldName
		if kindOfField=='flag':
			flagsVarNeeded=True
			structEnums += "const int "+fieldName +" = " + hex(1<<bitCursor) +";\n"
			bitCursor += 1;
		elif kindOfField=='mode':
			flagsVarNeeded=True
			# calculate field and bit position
			enumSize= len(field['enumList'])
			numEnumBits=bitsNeeded(enumSize)
			#field[3]=enumSize;
			#field[4]=numEnumBits;
			enumMask=((1 << numEnumBits) - 1) << bitCursor

			structEnums += "\nconst int "+fieldName +"Offset = " + hex(bitCursor) +";"
			structEnums += "\nconst int "+fieldName +"Mask = " + hex(enumMask) +";"

			# enum
			count=0
			structEnums += "\nenum " + fieldName +" {"
			for enumName in field['enumList']:
				structEnums += enumName+"="+hex(count<<bitCursor)
				count=count+1
				if(count<enumSize): structEnums += ", "
			structEnums += "};\n";

			structEnums += 'string ' + fieldName+'Strings[] = {"'+('", "'.join(field['enumList']))+'"};\n'
			# read/write macros
			accessDefines = accessDefines + "#define "+fieldName+"is(VAL) ((inf)->flags & )"
			# str array and printer

			bitCursor=bitCursor+numEnumBits;
	return flagsVarNeeded

def convertType(fieldType):
	Print "convert type: ", fieldType
	cppType = ""
	
	retrun cppType
	
def processOtherFields(objects, objectName, tags):
	print "$$$$$$$$$$$$$$$processOtherFields:"
	print objectName
	ObjectDef = objects[0][objectName]
	for field in ObjectDef['fields']:
		print field
		kindOfField=field['kindOfField']
		fieldType=field['fieldType']
		fieldName=field['fieldName']
		print "FIELDNAME:", fieldName
		structCode = structCode +"\nstruct "+structName+"{\n"
		if kindOfField=='var':
			print "var"
			convType = convertType(fieldType)
			structCode += "\n   "
		elif kindOfField=='rPtr':
			print "rPtr"
		elif kindOfField=='sPtr':
			print "sPtr"
		elif kindOfField=='uPtr':
			print "uPtr"			

def generateAllObjectsButMain(objects, tags):
	print "generateAllObjectsButMain"
	for objectName in objects[1]:
		if(objectName[0] != '!' and objectName != 'MAIN'):
			ObjectDef = objects[0][objectName]
			if(processFlagAndModeFields(objects, objectName, tags)):
				progSpec.addField(objects[0], objectName, 'var', 'uint64', 'flags')
			processOtherFields(objects, objectName, tags)
				
				
	
def processMain(objects, tags):
	print "Processing MAIN"
	if("MAIN" in objects):
		if(processFlagAndModeFields(objects, "MAIN", tags)):
			progSpec.addField(objects[0], "MAIN", 'var', 'uint64', 'flags')
				
	
def generate(objects, tags):
	print "generate$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$4"
	generateAllObjectsButMain(objects, tags)
	processMain(objects, tags)
	outputStr=""
	return outputStr
