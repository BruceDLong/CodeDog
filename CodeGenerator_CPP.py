# CodeGenerator_CPP.py
import progSpec
import re

buildStr_libs='g++ -g -std=gnu++11 Prot.cpp '
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
        elif kindOfField=='list':
            cppType="vector<"+baseType + '> '
        else: cppType=kindOfField; print "RETURNTYPE:", fieldType
    return cppType

def prepareTypeName(typeSpec):
    typeDefName=createTypedefName(typeSpec)
    typeDefSpec=convertType(typeSpec)
    if(typeSpec[0]=='var'):
        typeDefName=typeDefSpec
    return typeDefName

def genIfBody(ifBody, indent):
    ifBodyText = ""
    for ifAction in ifBody:
        actionOut = processAction(ifAction, indent + "    ")
        #print "If action: ", actionOut
        ifBodyText += actionOut
    return ifBodyText

def stringifyArray(thisExpression):
    thisString = ''
    for each in thisExpression:
        if isinstance(each, basestring):
            thisString += each
        else:
            thisString += stringifyArray(each)
    print thisString
    #thisString = ''.join(thisExpression)
    return thisString


def processAction(action, indent):
    #make a string and return it
    actionText = ""
    #print "........action........action........action: ", action
    typeOfAction = action['typeOfAction']
    #print typeOfAction
    if (typeOfAction =='newVar'):
        varName = action['varName']
        typeSpec = convertType(action['typeSpec'])
        #print "VAR: ", varName, typeSpec, typeOfAction
        actionText = indent + typeSpec + " " + varName + ";\n"
    elif (typeOfAction =='assign'):
        LHS = ".".join(action['LHS'])
        RHS = stringifyArray(action['RHS'])
        assignTag = action['assignTag']
        #print "Assign: ", LHS, RHS
        if assignTag == '':
            actionText = indent + LHS + " = " + RHS + ";\n"
        else:
            actionText = indent + "opAssign" + assignTag + '(' + LHS + ", " + RHS + ");\n"
    elif (typeOfAction =='swap'):
        LHS =  ".".join(action['LHS'])
        RHS =  ".".join(action['LHS'])
        #print "swap: ", LHS, RHS
        actionText = indent + "swap (" + LHS + ", " + RHS + ");\n"
    elif (typeOfAction =='conditional'):
        ifCondition = stringifyArray(action['ifCondition'])
        ifBodyText = genIfBody(action['ifBody'], indent)
        actionText =  "if (" + ifCondition + ") " + "{\n" + ifBodyText + indent + "}\n"
        elseBodyText = ""
        elseBody = action['elseBody']
        if (elseBody):
            #print 'ELSE BODY.......ELSE BODY.......ELSE BODY:', elseBody
            if (action['ifBody'] ):
                elseIf = elseBody
                elseIfText = processAction(elseIf, indent)
                #print "ELSE IF:  ELSE IF:  ELSE IF:  ELSE IF:  ", elseIfText
                actionText += indent + "else " + elseIfText

            elif (elseBody['actionList'] ):
                elseActSeq = elseBody['actionList']
                elseText = processActionSeq(elseActSeq, indent)
                #print "ELSE: ELSE: ELSE: ELSE: ELSE: ", elseText
                actionText += indent + "else" + elseText
    elif (typeOfAction =='repetition'):
        #print "repetition: ", action
        #whereExpr = action['whereExpr']
        repBody = action['repBody']
        repName = action['repName']
        repList = ".".join(action['repList'])
        actionText += indent + "for ( auto " + repName + ":" + repList + "){\n"
        if action['whereExpr']:
            whereExpr = stringifyArray(action['whereExpr'])
            actionText += indent + "    " + 'if (!' + whereExpr + ') continue;\n'
        if action['untilExpr']:
            untilExpr = stringifyArray(action['untilExpr'])
            actionText += indent + '    ' + 'if (' + untilExpr + ') break;\n'
        repBodyText = ''
        for repAction in repBody:
            actionOut = processAction(repAction, indent + "    ")
            repBodyText += actionOut
        actionText += repBodyText + indent + '}\n'
    elif (typeOfAction =='funcCall'):
        calledFunc = action['calledFunc']
        parameters = ",".join(action['parameters'])
        #print "funcCall: ", calledFunc, parameters
        actionText = indent + calledFunc + " (" + parameters  + ");\n"
    elif (typeOfAction =='actionSeq'):
        actionListIn = action['actionList']
        actionListText = ''
        for action in actionListIn:
            actionListOut = processAction(action, indent + "    ")
            actionListText += actionListOut
        #print "actionSeq: ", actionListText
        actionText += indent + "{\n" + actionListText + indent + '}\n'
    else:
        print "error in processAction: ", action
    print "actionText", actionText
    return actionText


def processActionSeq(actSeq, indent):
    #print "........processActionSeq........processActionSeq........processActionSeq"
    #print actSeq
    #print "........processActionSeq........processActionSeq........processActionSeq"
    actSeqText = "{\n"
    for action in actSeq:
        actionText = processAction(action, indent+'    ')
        #print actionText
        actSeqText += actionText
    actSeqText += "\n" + indent + "}"

    return actSeqText
def headType(typeSpec): # e.g., xPtr or if var, int, uint, etc,
    if typeSpec[0]=='var': return typeSpec[1]
    return typeSpec[0]



def generate_constructor(objects, objectName, tags):
    print 'Generate Constructor'
    constructorInit=":"
    constructorArgs="    "+objectName+"("
    count=0
    ObjectDef = objects[0][objectName]
    for field in ObjectDef['fields']:
        kindOfField=field['kindOfField']
        if(kindOfField=='flag' or kindOfField=='mode' or kindOfField=='func'): continue
        fieldType=field['fieldType']
        fieldHeadType=headType(fieldType)
        convertedType = convertType(fieldType)
        fieldName=field['fieldName']
        print "$$$$$$$$$$$$$$$$$$$$$$$$$ Constructing:", objectName, fieldName, fieldType, fieldHeadType, convertedType
        if(fieldHeadType[0:3]=="int" or fieldHeadType[0:4]=="uint" or fieldHeadType[-3:]=="Ptr"):
            constructorArgs += convertedType+" _"+fieldName+"=0,"
            constructorInit += fieldName+"("+" _"+fieldName+"),"
            count += 1
        elif(fieldHeadType=="string"):
            constructorArgs += convertedType+" _"+fieldName+'="",'
            constructorInit += fieldName+"("+" _"+fieldName+"),"
            count += 1
    if(count>0):
        constructorInit=constructorInit[0:-1]
        constructorArgs=constructorArgs[0:-1]
        constructCode = constructorArgs+")"+constructorInit+"{};\n"
    else: constructCode=''
    return constructCode

def processOtherFields(objects, objectName, tags, indent):
    print "        Coding fields for", objectName
    globalFuncs=''
    funcDefCode=''
    structCode=""
    ObjectDef = objects[0][objectName]
    for field in ObjectDef['fields']:
        #print field
        kindOfField=field['kindOfField']
        if(kindOfField=='flag' or kindOfField=='mode'): continue
        fieldType=field['fieldType']
        fieldName=field['fieldName']
        if fieldName=='opAssign': fieldName='operator='
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
        elif kindOfField=='sPtr' or kindOfField=='uPtr' or kindOfField=='list':
            typeStr=convertedType
            registerType(objectName, fieldName, typeStr, typeDefName)
            structCode += indent + typeDefName +' '+ fieldName +";\n";
        #################################################################
        elif kindOfField=='func':
            if(fieldType=='none'): convertedType=''
            else:
                #print convertedType
                convertedType+=''
            #get verbatim
            if field['funcTextVerbatim']:
                funcText=field['funcTextVerbatim']
            # if no verbatim found so generate function text from action sequence
            elif field['funcText']:
                funcText=processActionSeq(field['funcText'], indent)
            else:
                print "error in processOtherFields: no funcText or funcTextVerbatim found"
                exit(1)
            #print "FUNCTEXT:",funcText
        ###########################################################
            if(objectName=='MAIN'):
                if fieldName=='main':
                    funcDefCode += 'int main(int argc, char **argv)' +funcText+"\n\n"
                else:
                    argList=field['argList']
                    if argList[0]=='<%':
                        argListText=argList[1][0]
                    else:
                        argListText=""
                        count=0
                        for arg in argList:
                            if(count>0): argListText+=", "
                            count+=1
                            argListText+= convertType(arg[0][0]) +' '+ arg[0][1]
                    globalFuncs += "\n" + convertedType  +' '+ fieldName +"("+argListText+")" +funcText+"\n\n"
            else:
                argList=field['argList']
                if len(argList)==0:
                    argListText='void'
                    print "VOID:", argList
                elif argList[0]=='<%':
                    argListText=argList[1][0]
                else:
                    argListText=""
                    count=0
                    for arg in argList:
                        if(count>0): argListText+=", "
                        count+=1
                        argListText+= convertType(arg[0][0]) +' '+ arg[0][1]
                #print "FUNCTION:",convertedType, fieldName, '(', argListText, ') ', funcText
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
        constructCode=generate_constructor(objects, objectName, tags)
        structCode+=constructCode
        return [structCode, funcDefCode]


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
                progSpec.addField(objects[0], objectName, 'var', ['var','uint64'], 'flags')

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

def integrateLibrary(tags, libID):
    print '    Integrating', libID, tags
    libFiles=progSpec.fetchTagValue(tags, 'libraries.'+libID+'.libFiles')
    print "LIB_FILES", libFiles
    global buildStr_libs
    for libFile in libFiles:
        buildStr_libs+=' -l'+libFile
    libHeaders=progSpec.fetchTagValue(tags, 'libraries.'+libID+'.headers')
    for libHdr in libHeaders:
        tags[0]['Include'] +=', <'+libHdr+'>'
        print "Added header", libHdr
    print 'BUILD STR', buildStr_libs

def connectLibraries(objects, tags):
    print "Choosing Libaries to link..."
    libList = progSpec.fetchTagValue(tags, 'libraries')
    for lib in libList:
        if (progSpec.fetchTagValue(tags, 'libraries."+lib+".useStatus')!='notLinked'):
            integrateLibrary(tags, lib)

def generate(objects, tags):
    print "\nGenerating CPP code...\n"
    libInterfacesText=connectLibraries(objects, tags)
    header = makeFileHeader(tags)
    [constsEnums, forwardDecls, structCodeAcc, funcCodeAcc]=generateAllObjectsButMain(objects, tags)
    topBottomStrings = processMain(objects, tags)
    typeDefCode = produceTypeDefs(typeDefMap)
    if('cpp' in progSpec.codeHeader): codeHeader=progSpec.codeHeader['cpp']
    else: codeHeader=''
    outputStr = header + constsEnums + forwardDecls + codeHeader + typeDefCode + structCodeAcc + topBottomStrings[0] + funcCodeAcc + topBottomStrings[1]
    return outputStr
