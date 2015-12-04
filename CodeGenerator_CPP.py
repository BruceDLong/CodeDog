# CodeGenerator_CPP.py
import progSpec
import re
import datetime

buildStr_libs='g++ -g -std=gnu++11 Prot.cpp '
def bitsNeeded(n):
    if n <= 1:
        return 0
    else:
        return 1 + bitsNeeded((n + 1) / 2)


def processFlagAndModeFields(objects, objectName, tags):
    print "                    Coding flags and modes for:", objectName
    flagsVarNeeded = False
    bitCursor=0
    structEnums="\n\n// *** Code for manipulating "+objectName+' flags and modes ***\n'
    ObjectDef = objects[0][objectName]
    for field in ObjectDef['fields']:
        fieldType=field['fieldType'];
        fieldName=field['fieldName'];
        #print "                    ", field

        if fieldType=='flag':
            print "                        flag: ", fieldName
            flagsVarNeeded=True
            structEnums += "const int "+fieldName +" = " + hex(1<<bitCursor) +"; \t// Flag: "+fieldName+"\n"
            bitCursor += 1;
        elif fieldType=='mode':
            print "                        mode: ", fieldName, '[]'
            structEnums += "\n// For Mode "+fieldName
            flagsVarNeeded=True
            # calculate field and bit position
            enumSize= len(field['enumList'])
            numEnumBits=bitsNeeded(enumSize)
            #field[3]=enumSize;
            #field[4]=numEnumBits;
            enumMask=((1 << numEnumBits) - 1) << bitCursor

            structEnums += "const int "+fieldName +"Offset = " + hex(bitCursor) +";\n"
            structEnums += "const int "+fieldName +"Mask = " + hex(enumMask) +";"

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

def convertType(owner, fieldType):
    #print "fieldType: ", fieldType
    cppType="TYPE ERROR"
    if(isinstance(fieldType, basestring)):
        if(fieldType=='uint32' or fieldType=='uint64' or fieldType=='int32' or fieldType=='int64'):
            cppType=fieldType+'_t'
        else:
            cppType=fieldType
    if(fieldType=='<%'): return fieldType[1][0]

    kindOfField=owner
    if kindOfField=='const':
        cppType = "const "+cppType
    elif kindOfField=='me':
        cppType = cppType
    elif kindOfField=='my':
        cppType += '*'
    elif kindOfField=='our':
        cppType="shared_ptr<"+cppType + '> '
    elif kindOfField=='their':
        cppType="unique_ptr<"+cppType + '> '
    else:
        print "ERROR: Owner of type not valid '" + owner + "'"
        exit(1)
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
    #print thisString
    #thisString = ''.join(thisExpression)
    return thisString

################################  C o d e   E x p r e s s i o n s

def codeNameSeg(item, connector):
    S=''
    if (isinstance(item, basestring)):
        S+=connector+item
    else:
        if item[0]=='[':
            S+= '[' + codeExpr(item[1]) +']'
    return S

def codeItemName(item):
    print "NAME:", item
    S=''
    S += codeNameSeg(item[0],'')
    if len(item)>1:
        for i in item[1]:
            S+=codeNameSeg(i,'.')
    return S

def codeFactor(item):
    ####  ( value | ('(' + expr + ')') | ('!' + expr) | ('-' + expr) | varFuncRef)
    #print '                  factor: ', item
    S=''
    item0 = item[0]
    print "ITEM0=", item0
    if (isinstance(item0, basestring)):
        if item0=='(':
            S+='(' + codeExpr(item[1]) +')'
        elif item0=='!':
            S+='!' + codeExpr(item[1])
        elif item0=='-':
            S+='-' + codeExpr(item[1])
        else: S=item0
    else:
        print "VARFUNCREF:", item0
        if len(item0)==1:
            S+=codeItemName(item0[0])                 # Code variable reference
        else:
            if len(item0)==2:
                S+=codeFuncCall(item0[0], [])         # Code function call within an expr, no parameters
            else:
                S+=codeFuncCall(item0[0], item0[2])   # Code function call within an expr
    return S

def codeTerm(item):
    #print '               term item:', item
    S=codeFactor(item[0])
    if (not(isinstance(item, basestring))) and (len(item) > 1):
        for i in item[1]:
            #print '               term:', i
            if   (i[0] == '*'): S+=' * '
            elif (i[0] == '/'): S+=' / '
            elif (i[0] == '%'): S+=' % '
            else: print "ERROR: One of '*', '/' or '%' expected in c++ code generator."; exit(2)
            S+=codeFactor(i[1])
    return S

def codePlus(item):
    #print '            plus item:', item
    S=codeTerm(item[0])
    if len(item) > 1:
        for  i in item[1]:
            #print '            plus ', i
            if   (i[0] == '+'): S+=' + '
            elif (i[0] == '-'): S+=' - '
            else: print "ERROR: '+' or '-' expected in c++ code generator."; exit(2)
            S+=codeTerm(i[1])
    return S

def codeComparison(item):
    #print '         Comp item', item
    S=codePlus(item[0])
    if len(item) > 1:
        for  i in item[1]:
            #print '         comp ', i
            if   (i[0] == '<'): S+=' < '
            elif (i[0] == '>'): S+=' > '
            elif (i[0] == '<='): S+=' <= '
            elif (i[0] == '>='): S+=' >= '
            else: print "ERROR: One of <, >, <= or >= expected in c++ code generator."; exit(2)
            S+=codePlus(i[1])
    return S

def codeIsEQ(item):
    #print '      IsEq item:', item
    S=codeComparison(item[0])
    if len(item) > 1:
        for i in item[1]:
            #print '      IsEq ', i
            if   (i[0] == '=='): S+=' == '
            elif (i[0] == '!='): S+=' != '
            else: print "ERROR: 'and' expected in c++ code generator."; exit(2)
            S+=codeComparison(i[1])
    return S

def codeLogAnd(item):
    #print '   And item:', item
    S= codeIsEQ(item[0])
    if len(item) > 1:
        for i in item[1]:
            #print '   AND ', i
            if (i[0] == 'and'):
                S+=' && ' + codeIsEQ(i[1])
            else: print "ERROR: 'and' expected in c++ code generator."; exit(2)
    return S

def codeExpr(item):
    #print 'Or item:', item
    S=codeLogAnd(item[0])
    if len(item) > 1:
        for i in item[1]:
            #print 'OR ', i
            if (i[0] == 'or'):
                S+=' || ' + codeLogAnd(i[1])
            else: print "ERROR: 'or' expected in c++ code generator."; exit(2)
    #print "S:",S
    return S

def codeParameterList(paramList):
    S=''
    count = 0
    for P in paramList:
        if(count>0): S+=', '
        count+=1
        #print "PARAM",P
        S+=codeExpr(P[0])
    return S

def codeFuncCall(funcName, paramList):
    S=''
    S+=codeItemName(funcName)
    S+='(' + codeParameterList(paramList) + ')'
    return S

def processAction(action, indent):
    #make a string and return it
    actionText = ""
    typeOfAction = action['typeOfAction']

    if (typeOfAction =='newVar'):
        varName = action['varName']
        typeSpec = convertType('me', action['typeSpec'])
        #print "VAR: ", varName, typeSpec, typeOfAction
        actionText = indent + typeSpec + " " + varName + ";\n"
    elif (typeOfAction =='assign'):
        LHS = codeItemName(action['LHS'])
        RHS = codeExpr(action['RHS'][0])
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
        ifCondition = codeExpr(action['ifCondition'][0])
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
            whereExpr = codeExpr(action['whereExpr'])
            actionText += indent + "    " + 'if (!' + whereExpr + ') continue;\n'
        if action['untilExpr']:
            untilExpr = codeExpr(action['untilExpr'])
            actionText += indent + '    ' + 'if (' + untilExpr + ') break;\n'
        repBodyText = ''
        for repAction in repBody:
            actionOut = processAction(repAction, indent + "    ")
            repBodyText += actionOut
        actionText += repBodyText + indent + '}\n'
    elif (typeOfAction =='funcCall'):
        #print "########################################## FUNCTION CALL AS ACTION\n",
        calledFunc = action['calledFunc']
        parameters = action['parameters']
        #print "funcCall: ", calledFunc, parameters
        actionText = indent + codeFuncCall(calledFunc, parameters) + ';\n'
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
 #   print "actionText", actionText
    return actionText


def processActionSeq(actSeq, indent):
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
    print "                    Generating Constructor for:", objectName
    constructorInit=":"
    constructorArgs="    "+objectName+"("
    count=0
    ObjectDef = objects[0][objectName]
    for field in ObjectDef['fields']:
        #print "^^^^^^^^^^^^^^^^^^^^"
        #print "field: ", field
        fieldType=field['fieldType']
        if(fieldType=='flag' or fieldType=='mode' or fieldType=='func'): continue
        fieldOwner=field['owner']
        fieldType=field['fieldType']
        fieldHeadType=headType(fieldType)
        convertedType = convertType(fieldOwner, fieldType)
        fieldName=field['fieldName']
        #print "$$$$$$$$$$$$$$$$$$$$$$$$$ Constructing:", objectName, fieldName, fieldType, fieldHeadType, convertedType
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

def processOtherStructFields(objects, objectName, tags, indent):
    print "                    Coding fields for", objectName
    globalFuncs=''
    funcDefCode=''
    structCode=""
    ObjectDef = objects[0][objectName]
    for field in ObjectDef['fields']:
        fieldType=field['fieldType']
        if(fieldType=='flag' or fieldType=='mode'): continue
        fieldOwner=field['owner']
        fieldName =field['fieldName']
        fieldValue=field['value']
        fieldArglist = field['argList']
        if fieldName=='opAssign': fieldName='operator='
        convertedType = convertType(fieldOwner, fieldType)
        typeDefName = progSpec.createTypedefName(fieldType)
        if(fieldValue == None):fieldValueText=""
        else: fieldValueText = " = "+ str(fieldValue)
        registerType(objectName, fieldName, convertedType, "")
        print "                       ", fieldOwner, fieldType, fieldName
        if(fieldOwner=='const'):
            structCode += indent + convertedType + ' ' + fieldName + fieldValueText +';\n';
        elif(fieldArglist==None):
            structCode += indent + convertedType +' ' + fieldName + fieldValueText +';\n';
        #################################################################
        else: # Arglist exists so this is a function.
            if(fieldType=='none'): convertedType=''
            else:
                #print convertedType
                convertedType+=''
            if (field['value'][1]!=''): # This function body is 'verbatim'.
                funcText=field['value'][1]
            # No verbatim found so generate function text from action sequence
            elif field['value'][0]!='':
                funcText=processActionSeq(field['value'][0], indent)
            else:
                print "ERROR: In processOtherFields: no funcText or funcTextVerbatim found"
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
                            argListText+= convertType(fieldOwner, arg[0][0]) +' '+ arg[0][1]
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
                        argListText+= convertType(arg[0][0], arg[0][1]) + ' ' + arg[0][2][1]
                #print "FUNCTION:",convertedType, fieldName, '(', argListText, ') ', funcText
                if(fieldType[0] != '<%'):
                    registerType(objectName, fieldName, convertedType, typeDefName)
                else: typeDefName=convertedType
                structCode += indent + typeDefName +' ' + fieldName +"("+argListText+");\n";
                objPrefix=objectName +'::'
                funcDefCode += typeDefName +' ' + objPrefix + fieldName +"("+argListText+")" +funcText+"\n\n"

    if(objectName=='MAIN'):
        return [structCode, funcDefCode, globalFuncs]
    else:
        constructCode=generate_constructor(objects, objectName, tags)
        structCode+=constructCode
        return [structCode, funcDefCode]


def generateAllObjectsButMain(objects, tags):
    print "\n            Generating Objects..."
    constsEnums="\n//////////////////////////////////////////////////////////\n////   F l a g   a n d   M o d e   D e f i n i t i o n s\n\n"
    forwardDecls="\n";
    structCodeAcc='\n////////////////////////////////////////////\n//   O b j e c t   D e c l a r a t i o n s\n\n';
    funcCodeAcc="\n//////////////////////////////////////\n//   M e m b e r   F u n c t i o n s\n\n"
    needsFlagsVar=False;
    for objectName in objects[1]:
        if(objectName[0] != '!'):
            print "                [" + objectName+"]"
            [needsFlagsVar, strOut]=processFlagAndModeFields(objects, objectName, tags)
            constsEnums+=strOut
            if(needsFlagsVar):
                progSpec.addField(objects[0], objectName, False, 'me', "uint64", 'flags', None, None)
            if(objectName != 'MAIN' and objects[0][objectName]['stateType'] == 'struct'):
                forwardDecls+="struct " + objectName + ";  \t// Forward declaration\n"
                [structCode, funcCode]=processOtherStructFields(objects, objectName, tags, '    ')
                structCodeAcc += "\nstruct "+objectName+"{\n" + structCode + '};\n'
                funcCodeAcc+=funcCode
    return [constsEnums, forwardDecls, structCodeAcc, funcCodeAcc]



def processMain(objects, tags):
    print "\n            Generating MAIN..."
    if("MAIN" in objects[1]):
        if(objects[0]["MAIN"]['stateType'] != 'struct'):
            print "ERROR: MAIN must be a 'struct'."
            exit(2)
        [structCode, funcCode, globalFuncs]=processOtherStructFields(objects, "MAIN", tags, '')
        if(funcCode==''): funcCode="// No main() function.\n"
        if(structCode==''): structCode="// No Main Globals.\n"
        return ["\n\n// Globals\n" + structCode + globalFuncs, funcCode]
    return ["// No Main Globals.\n", "// No main() function defined.\n"]

def produceTypeDefs(typeDefMap):
    typeDefCode="\n// Typedefs:\n"
    for key in typeDefMap:
        val=typeDefMap[key]
        #sprint '['+key+']='+val+']'
        if(val != '' and val != key):
            typeDefCode += 'typedef '+key+' '+val+';\n'
    return typeDefCode

def makeTagText(tags, tagName):
    tagVal=progSpec.fetchTagValue(tags, tagName)
    if tagVal==None: return "Tag '"+tagName+"' is not set in the dog file."
    return tagVal

def makeFileHeader(tags):
    global buildStr_libs
    header  = "// " + makeTagText(tags, 'Title') + " "+ makeTagText(tags, 'Version') + '\n'
    header += "// " + makeTagText(tags, 'CopyrightMesg') +'\n'
    header += "// This file: " + makeTagText(tags, 'FileName') +'\n'
    header += "// Dog File: " + makeTagText(tags, 'dogFilename') +'\n'
    header += "// Authors of CodeDog file: " + makeTagText(tags, 'Authors') +'\n'
    header += "// Build time: " + datetime.datetime.today().strftime('%c') + '\n'
    header += "\n// " + makeTagText(tags, 'Description') +'\n'
    header += "\n/*  " + makeTagText(tags, 'LicenseText') +'\n*/\n'
    header += "\n// Build Options Used: " +'Not Implemented'+'\n'
    header += "\n// Build Command: " +buildStr_libs+'\n'
    includes = re.split("[,\s]+", progSpec.fetchTagValue(tags, 'Include'))
    for hdr in includes:
        header+="\n#include "+hdr
    header += "\n\nusing namespace std; \n\n"

    header += r'static void reportFault(int Signal){cout<<"\nSegmentation Fault.\n"; fflush(stdout); abort();}'+'\n\n'

    header += "string enumText(string* array, int enumVal, int enumOffset){return array[enumVal >> enumOffset];}\n";
    header += "#define SetBits(item, mask, val) {(item) &= ~(mask); (item)|=(val);}\n"
    return header

def integrateLibrary(tags, libID):
    print '                Integrating', libID
    libFiles=progSpec.fetchTagValue(tags, 'libraries.'+libID+'.libFiles')
    #print "LIB_FILES", libFiles
    global buildStr_libs
    for libFile in libFiles:
        buildStr_libs+=' -l'+libFile
    libHeaders=progSpec.fetchTagValue(tags, 'libraries.'+libID+'.headers')
    for libHdr in libHeaders:
        tags[0]['Include'] +=', <'+libHdr+'>'
        #print "Added header", libHdr
    #print 'BUILD STR', buildStr_libs

def connectLibraries(objects, tags):
    print "\n            Choosing Libaries to link..."
    libList = progSpec.fetchTagValue(tags, 'libraries')
    for lib in libList:
        if (progSpec.fetchTagValue(tags, 'libraries."+lib+".useStatus')!='notLinked'):
            integrateLibrary(tags, lib)

def generate(objects, tags):
    #print "\nGenerating CPP code...\n"
    libInterfacesText=connectLibraries(objects, tags)
    header = makeFileHeader(tags)
    [constsEnums, forwardDecls, structCodeAcc, funcCodeAcc]=generateAllObjectsButMain(objects, tags)
    topBottomStrings = processMain(objects, tags)
    typeDefCode = produceTypeDefs(typeDefMap)
    if('cpp' in progSpec.codeHeader): codeHeader=progSpec.codeHeader['cpp']
    else: codeHeader=''
    outputStr = header + constsEnums + forwardDecls + codeHeader + typeDefCode + structCodeAcc + topBottomStrings[0] + funcCodeAcc + topBottomStrings[1]
    return outputStr
