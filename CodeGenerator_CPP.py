# CodeGenerator_CPP.py
import progSpec
import re

def bitsNeeded(n):
    if n <= 1:
        return 0
    else:
        return 1 + bitsNeeded((n + 1) / 2)


def processFlagAndModeFields(objects, objectName, tags):
    print "\n        Coding flags and modes for:", objectName
    flagsVarNeeded = False
    bitCursor=0
    structEnums="\n\n// *** Code for manipulating "+objectName+' flags and modes ***\n'
    ObjectDef = objects[0][objectName]
    for field in ObjectDef['fields']:
        #print field
        kindOfField=field['kindOfField'];
        fieldName=field['fieldName'];

        if kindOfField=='flag':
            print "        ->:", fieldName
            flagsVarNeeded=True
            structEnums += "\nconst int "+fieldName +" = " + hex(1<<bitCursor) +"; \t// Flag: "+fieldName+"\n"
            bitCursor += 1;
        elif kindOfField=='mode':
            print "        ->:", fieldName, '[]'
            structEnums += "\n// For Mode "+fieldName
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
            structEnums += "#define "+fieldName+"is(VAL) ((inf)->flags & )\n"
            # str array and printer

            bitCursor=bitCursor+numEnumBits;
    return [flagsVarNeeded, structEnums]

typeDefMap={}
ObjectsFieldTypeMap={}
def registerType(objName, fieldName, typeOfField, typeDefTag):
    ObjectsFieldTypeMap[objName+'::'+fieldName]={'rawType':typeOfField, 'typeDef':typeDefTag}
    typeDefMap[typeOfField]=typeDefTag

def convertType(fieldType):
    if(isinstance(fieldType, basestring)):
        if(fieldType=='uint32' or fieldType=='uint64' or fieldType=='int32' or fieldType=='int64'):
            cppType=fieldType+'_t'
        else:
            cppType=fieldType
    else:
        kindOfField=fieldType[0]
        if(kindOfField=='<%'): return fieldType[1][0]
        baseType=convertType(fieldType[1])
        if kindOfField=='var':
            cppType = baseType
        elif kindOfField=='rPtr':
            cppType=baseType + '*'
        elif kindOfField=='sPtr':
            cppType="shared_ptr<"+baseType + '> '
        elif kindOfField=='uPtr':
            cppType="unique_ptr<"+baseType + '> '
        else: cppType=kindOfField; print "RETURNTYPE:", fieldType
    return cppType

def prepareTypeName(typeSpec):
    typeDefName=createTypedefName(typeSpec)
    typeDefSpec=convertType(typeSpec)
    if(typeSpec[0]=='var'):
        typeDefName=typeDefSpec
    return typeDefName
    
def processActionSeq(actSeq):
    print "processActionSeq ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^"
    print actSeq
    return " "


def processOtherFields(objects, objectName, tags, indent):
    print "        Coding fields for", objectName
    globalFuncs=''
    funcDefCode=''
    structCode=""
    ObjectDef = objects[0][objectName]
    print "processOtherFields%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%"
    for field in ObjectDef['fields']:
        #print field
        kindOfField=field['kindOfField']
        if(kindOfField=='flag' or kindOfField=='mode'): continue
        fieldType=field['fieldType']
        fieldName=field['fieldName']
        convertedType = convertType(fieldType)
        typeDefName = progSpec.createTypedefName(fieldType)
        if kindOfField != 'flags':
            print "        ->", kindOfField, fieldName

        if kindOfField=='var':
            registerType(objectName, fieldName, convertedType, "")
            structCode += indent + convertedType + ' ' + fieldName +";\n";
        elif kindOfField=='rPtr':
            typeStr=convertedType # + '*'
            registerType(objectName, fieldName, typeStr, "")
            structCode += indent + typeStr + fieldName +";\n";
        elif kindOfField=='sPtr':
            typeStr=convertedType
            registerType(objectName, fieldName, typeStr, typeDefName)
            structCode += indent + typeDefName +' '+ fieldName +";\n";
        elif kindOfField=='uPtr':
            typeStr=convertedType
            registerType(objectName, fieldName, typeStr, typeDefName)
            structCode += indent + typeDefName +' '+ fieldName +";\n";
        #################################################################
        elif kindOfField=='func':
            
            print field['funcText']
            if(fieldType=='none'): convertedType=''
            else:
                #print convertedType
                convertedType+=''
            
            funcText=field['funcText'][1]
            print funcText
            if funcText=='':
                funcText=processActionSeq(field['funcText'][0])
            #print "FUNCTEXT:",funcText
            if(objectName=='MAIN'):
                if fieldName=='main':
                    funcDefCode += 'int main(int argc, char **argv)' +funcText+"\n\n"
                else:
                    argList=field['argList']
                    if argList[0]=='<%':
                        argListText=argList[1][0]
                    else:
                        argListText="Argument List Needs Generated"
                    globalFuncs += "\n" + convertedType  +' '+ fieldName +"("+argListText+")" +funcText+"\n\n"
            else:
                argList=field['argList']
                if len(argList)==0:
                    argListText='void'
                elif argList[0]=='<%':
                    argListText=argList[1][0]
                else:
                    argListText=""
                    count=0
                    for arg in argList:
                        if(count>0): argListText+=", "
                        count+=1
                        argListText+= convertType(arg[0]) +' '+ arg[2]
                print "FUNCTION:",convertedType, fieldName, '(', argListText, ') ', funcText
                if(fieldType[0] != '<%'):
                    registerType(objectName, fieldName, convertedType, typeDefName)
                else: typeDefName=convertedType
                structCode += indent + typeDefName +' ' + fieldName +"("+argListText+");\n";
                objPrefix=objectName +'::'
                funcDefCode += typeDefName +' ' + objPrefix + fieldName +"("+argListText+")" +funcText+"\n\n"
        elif kindOfField=='const':
            fieldValue=field['fieldValue']
            structCode += indent + 'const ' + fieldType +' ' + fieldName +" = "+fieldValue +';\n';
    if(objectName=='MAIN'):
        return [structCode, funcDefCode, globalFuncs]
    else:
        return [structCode, funcDefCode]

def generate_constructor(objects, objectName, tags, indent):
    print 'Generate Constructor'
    #constructorInit=":"
    #constructorArgs="    "+structName+"("
    #...
    # for each field:
            #if(fieldType[0:3]=="int" or fieldType[0:4]=="uint" or fieldType[-3:]=="Ptr"):
                #constructorArgs += fieldType+" _"+fieldName+"=0,"
                #constructorInit += fieldName+"("+" _"+fieldName+"),"
                #count=count+1
            #elif(fieldType=="string"):
                #constructorArgs += fieldType+" _"+fieldName+'="",'
                #constructorInit += fieldName+"("+" _"+fieldName+"),"
                #count=count+1
    #if(count>0):
        #constructorInit=constructorInit[0:-1]
        #constructorArgs=constructorArgs[0:-1]
    #structCode += constructorArgs+")"+constructorInit+"{};\n" +"};\n"


def generateAllObjectsButMain(objects, tags):
    print "    Generating Objects..."
    constsEnums="\n//////////////////////////////////////////////////////////\n////   F l a g   a n d   M o d e   D e f i n i t i o n s\n\n"
    forwardDecls="\n";
    structCodeAcc='\n////////////////////////////////////////////\n//   O b j e c t   D e c l a r a t i o n s\n\n';
    funcCodeAcc="\n//////////////////////////////////////\n//   M e m b e r   F u n c t i o n s\n\n"
    needsFlagsVar=False;
    for objectName in objects[1]:
        if(objectName[0] != '!'):
            [needsFlagsVar, strOut]=processFlagAndModeFields(objects, objectName, tags)
            constsEnums+=strOut
            if(needsFlagsVar):
                progSpec.addField(objects[0], objectName, 'var', 'uint64', 'flags')

            if(objectName != 'MAIN'):
                forwardDecls+="struct " + objectName + ";  \t// Forward declaration\n"
                [structCode, funcCode]=processOtherFields(objects, objectName, tags, '    ')
                structCodeAcc += "\nstruct "+objectName+"{\n" + structCode + '};\n'
                funcCodeAcc+=funcCode
    return [constsEnums, forwardDecls, structCodeAcc, funcCodeAcc]



def processMain(objects, tags):
    print "\n    Generating MAIN..."
    if("MAIN" in objects[1]):
        [structCode, funcCode, globalFuncs]=processOtherFields(objects, "MAIN", tags, '')
        if(funcCode==''): funcCode="// No main() function.\n"
        if(structCode==''): structCode="// No Main Globals.\n"
        return ["\n\n// Globals\n" + structCode + globalFuncs, funcCode]
    return ["// No Main Globals.\n", "// No main() function defined.\n"]

def produceTypeDefs(typeDefMap):
    typeDefCode="\n// Typedefs:\n"
    for key in typeDefMap:
        val=typeDefMap[key]
        print '['+key+']='+val+']'
        if(val != '' and val != key):
            typeDefCode += 'typedef '+key+' '+val+';\n'
    return typeDefCode

def makeFileHeader(tags):
    header = "// " + progSpec.fetchTagValue(tags, 'Title') +'\n'
    includes = re.split("[,\s]+", progSpec.fetchTagValue(tags, 'Include'))
    for hdr in includes:
        header+="\n#include "+hdr
    header += "\n\nusing namespace std; \n\n"

    header += r'static void reportFault(int Signal){cout<<"\nSegmentation Fault.\n"; fflush(stdout); abort();}'+'\n\n'

    header += "string enumText(string* array, int enumVal, int enumOffset){return array[enumVal >> enumOffset];}\n";
    header += "#define SetBits(item, mask, val) {(item) &= ~(mask); (item)|=(val);}\n"
    return header

def generate(objects, tags):
    print "\nGenerating CPP code...\n"
    header = makeFileHeader(tags)
    [constsEnums, forwardDecls, structCodeAcc, funcCodeAcc]=generateAllObjectsButMain(objects, tags)
    topBottomStrings = processMain(objects, tags)
    typeDefCode = produceTypeDefs(typeDefMap)
    outputStr = header + topBottomStrings[0] + constsEnums + forwardDecls + typeDefCode + structCodeAcc + funcCodeAcc + topBottomStrings[1]
    return outputStr
