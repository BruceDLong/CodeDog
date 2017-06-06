#xlator_Swing.py
import progSpec
import codeDogParser
from progSpec import cdlog, cdErr, isStruct
from CodeGenerator import codeItemRef, codeUserMesg, codeStructFields, codeAllocater, appendGlobalFuncAcc, codeParameterList, makeTagText, codeAction

###### Routines to track types of identifiers and to look up type based on identifier.
def getContainerType(typeSpec):
    containerSpec=typeSpec['arraySpec']
    if 'owner' in containerSpec: owner=containerSpec['owner']
    else: owner='me'
    idxType=''
    if 'indexType' in containerSpec:
        idxType=containerSpec['indexType']
    datastructID = containerSpec['datastructID']
    if(datastructID=='list'): datastructID = "deque"
    return [datastructID, idxType, owner]

def adjustBaseTypes(fieldType):
    if(isinstance(fieldType, basestring)):
        #print"adjustBaseTypes:basestring",fieldType
        if(fieldType=='uint8' or fieldType=='uint16'or fieldType=='uint32'): fieldType='UInt32'
        elif(fieldType=='int8' or fieldType=='int16' or fieldType=='int32'): fieldType='Int32'
        elif(fieldType=='uint64'):fieldType='UInt64'
        elif(fieldType=='int64'):fieldType='Int64'
        elif(fieldType=='int'):fieldType='Int'
        elif(fieldType=='bool'):fieldType='Bool'
        elif(fieldType=='void'):fieldType='Void'
        elif(fieldType=='float'):fieldType='Float'
        elif(fieldType=='double'):fieldType='Double'
        elif(fieldType=='string'):fieldType='String'
        elif(fieldType=='char'):fieldType='Character'

        langType=progSpec.flattenObjectName(fieldType)
    else: langType=progSpec.flattenObjectName(fieldType[0])
    return langType

def applyOwner(owner, langType, varMode):
    if owner=='const':
        langType = "let "+langType
    elif owner=='me':
        langType = langType
    elif owner=='my':
        langType="unique_ptr<"+langType + ' >'
    elif owner=='our':
        langType="shared_ptr<"+langType + ' >'
    elif owner=='their':
        langType += '*'
    elif owner=='itr':
        langType += '::iterator'
    else:
        print "ERROR: Owner of type not valid '" + owner + "'"
        exit(1)
    return langType

def xlateLangType(TypeSpec,owner, fieldType, varMode, xlator):
    # varMode is 'var' or 'arg' or 'alloc'. Large items are passed as pointers
    langType = adjustBaseTypes(fieldType)
    if varMode != 'alloc':
        langType = applyOwner(owner, langType, varMode)
    if 'arraySpec' in TypeSpec:
        arraySpec=TypeSpec['arraySpec']
        if(arraySpec): # Make list, map, etc
            [containerType, idxType, owner]=getContainerType(TypeSpec)
            if 'owner' in TypeSpec['arraySpec']:
                containerOwner=TypeSpec['arraySpec']['owner']
            else: containerOwner='me'
            idxType=adjustBaseTypes(idxType)
            if idxType=='timeValue': idxType = 'Int64'

            if containerType=='deque':
                langType="["+langType+"]"
            elif containerType=='map':
                langType="["+idxType+': '+langType+"]"
            elif containerType=='multimap': # TODO: Implement true multmaps in swift
                langType="["+idxType+': ['+langType+"]]"

            if varMode != 'alloc':
                #if varMode=='arg' and containerOwner=='their': langType+='&' # Pass these as references
                #else:
                    langType=applyOwner(containerOwner, langType, varMode)

    return [langType, langType]

def convertType(objects, TypeSpec, varMode, xlator):
    # varMode is 'var' or 'arg'. Large items are passed as pointers
    owner=TypeSpec['owner']
    fieldType=TypeSpec['fieldType']
    if not isinstance(fieldType, basestring):
        #if len(fieldType)>1: exit(2)
        fieldType=fieldType[0]
    baseType = progSpec.isWrappedType(objects, fieldType)
    if(baseType!=None):
        owner=baseType['owner']
        fieldType=baseType['fieldType']
    langType="TYPE ERROR"
    if(fieldType=='<%'): return fieldType[1][0]
    return xlateLangType(TypeSpec, owner, fieldType, varMode, xlator)

def recodeStringFunctions(name, typeSpec):
    if name == "size": name = "length"
    elif name == "subStr": name = "substr"

    return [name, typeSpec]

def langStringFormatterCommand(fmtStr, argStr):
    S='String(format:'+'"'+ fmtStr +'"'+ argStr +')'
    return S

def getTheDerefPtrMods(itemTypeSpec):
    if itemTypeSpec!=None and isinstance(itemTypeSpec, dict) and 'owner' in itemTypeSpec:
        if progSpec.typeIsPointer(itemTypeSpec):
            owner=progSpec.getTypeSpecOwner(itemTypeSpec)
            if owner=='itr':
                containerType = itemTypeSpec['arraySpec'][2]
                if containerType =='map' or containerType == 'multimap':
                    return ['', '->second']
            return ['(*', ')']
    return ['', '']

def derefPtr(varRef, itemTypeSpec):
    [leftMod, rightMod] = getTheDerefPtrMods(itemTypeSpec)
    return leftMod + varRef + rightMod

def chooseVirtualRValOwner(LVAL, RVAL):
    # Returns left and right text decorations for RHS of function arguments, return values, etc.
    if RVAL==0 or RVAL==None or isinstance(RVAL, basestring): return ['',''] # This happens e.g., string.size() # TODO: fix this.
    if LVAL==0 or LVAL==None or isinstance(LVAL, basestring): return ['', '']
    LeftOwner =progSpec.getTypeSpecOwner(LVAL)
    RightOwner=progSpec.getTypeSpecOwner(RVAL)
    if LeftOwner == RightOwner: return ["", ""]
    if LeftOwner!='itr' and RightOwner=='itr': return ["", "->second"]
    if LeftOwner=='me' and progSpec.typeIsPointer(RVAL): return ["(*", "   )"]
    if progSpec.typeIsPointer(LVAL) and RightOwner=='me': return ["&", '']
    if LeftOwner=='their' and (RightOwner=='our' or RightOwner=='my'): return ['','.get()']
    return ['','']

def determinePtrConfigForAssignments(LVAL, RVAL, assignTag):
    # Returns left and right text decorations for both LHS and RHS of assignment
    if RVAL==0 or RVAL==None or isinstance(RVAL, basestring): return ['','',  '',''] # This happens e.g., string.size() # TODO: fix this.
    if LVAL==0 or LVAL==None or isinstance(LVAL, basestring): return ['','',  '','']
    LeftOwner =progSpec.getTypeSpecOwner(LVAL)
    RightOwner=progSpec.getTypeSpecOwner(RVAL)
    if LeftOwner == RightOwner: return ['','',  '','']
    if LeftOwner=='me' and progSpec.typeIsPointer(RVAL):
        [leftMod, rightMod] = getTheDerefPtrMods(RVAL)
        return ['','',  leftMod, rightMod]  # ['', '', "(*", ")"]
    if progSpec.typeIsPointer(LVAL) and RightOwner=='me':
        if assignTag=='deep' :return ['(*',')',  '', '']
        else: return ['','',  "&", '']

    if LeftOwner=='their' and (RightOwner=='our' or RightOwner=='my'): return ['','', '','.get()']

    return ['','',  '','']


def getCodeAllocStr(varTypeStr, owner):
    if(owner=='our'): S="make_shared<"+varTypeStr+">"
    elif(owner=='my'): S="make_unique<"+varTypeStr+">"
    elif(owner=='their'): S="new "+varTypeStr
    elif(owner=='me'): print "ERROR: Cannot allocate a 'me' variable."; exit(1);
    elif(owner=='const'): print "ERROR: Cannot allocate a 'const' variable."; exit(1);
    else: print "ERROR: Cannot allocate variable because owner is", owner+"."; exit(1);
    return S

def getCodeAllocSetStr(varTypeStr, owner, value):
    S=getCodeAllocStr(varTypeStr, owner)
    S+='('+value+')'
    return S

def getConstIntFieldStr(fieldName, fieldValue):
    S= "static let Int "+fieldName+ " = " + fieldValue+ ";"
    return(S)

def getEnumStr(fieldName, enumList):
    S = "\n    enum " + fieldName +" {"
    enumSize = len (enumList)
    count=0
    for enumName in enumList:
        S += enumName+"="+hex(count)
        count=count+1
        if(count<enumSize): S += ", "
    S += "};\n";
    S += 'string ' + fieldName+'Strings['+str(len(enumList))+'] = {"'+('", "'.join(enumList))+'"};\n'
    return(S)

######################################################   E X P R E S S I O N   C O D I N G

def getContainerTypeInfo(containerType, name, idxType, typeSpecOut, paramList, objectsRef, xlator):
    convertedIdxType = ""
    if containerType=='deque':
        if name=='at' or name=='insert' or name=='erase': pass
        elif name=='size' : typeSpecOut={'owner':'me', 'fieldType': 'Uint32'}
        elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'Void'}
        elif name=='front'    : name='begin()';  typeSpecOut['owner']='itr'; paramList=None;
        elif name=='back'     : name='rbegin()'; typeSpecOut['owner']='itr'; paramList=None;
        elif name=='end'      : name='end()';    typeSpecOut['owner']='itr'; paramList=None;
        elif name=='rend'     : name='rend()';   typeSpecOut['owner']='itr'; paramList=None;
        elif name=='first'    : name='begin()->second';  paramList=None;
        elif name=='last'     : name='rbegin()->second'; paramList=None;
        elif name=='popFirst' : name='pop_front'
        elif name=='popLast'  : name='pop_back'
        elif name=='pushFirst': name='push_front'
        elif name=='pushLast' : name='push_back'
        else: print "Unknown deque command:", name; exit(2);
    elif containerType=='map':
        if idxType=='timeValue': convertedIdxType = 'Int64'
        else: convertedIdxType=idxType
        convertedItmType=xlator['convertType'](objectsRef, typeSpecOut, 'var', xlator)
        if name=='at' or name=='erase': pass
        elif name=='size'     : typeSpecOut={'owner':'me', 'fieldType': 'Uint32'}
        elif name=='insert'   : typeSpecOut['codeConverter']='insert(pair<'+convertedIdxType+', '+convertedItmType+'>(%1, %2))';
        elif name=='clear'    : typeSpecOut={'owner':'me', 'fieldType': 'Void'}
        elif name=='find'     : name='find';     typeSpecOut['owner']='itr';
        elif name=='front'    : name='begin()';  typeSpecOut['owner']='itr'; paramList=None;
        elif name=='back'     : name='rbegin()'; typeSpecOut['owner']='itr'; paramList=None;
        elif name=='end'      : name='end()';    typeSpecOut['owner']='itr'; paramList=None;
        elif name=='rend'     : name='rend()';   typeSpecOut['owner']='itr'; paramList=None;
        elif name=='first'    : name='begin()->second';  paramList=None;
        elif name=='last'     : name='rbegin()->second'; paramList=None;
        elif name=='popFirst' : name='pop_front'
        elif name=='popLast'  : name='pop_back'
        else: print "Unknown map command:", name; exit(2);
    elif containerType=='multimap':
        if idxType=='timeValue': convertedIdxType = 'Int64'
        else: convertedIdxType=idxType
        convertedItmType=xlator['convertType'](objectsRef, typeSpecOut, 'var', xlator)
        if name=='at' or name=='erase': pass
        elif name=='size'     : typeSpecOut={'owner':'me', 'fieldType': 'Uint32'}
        elif name=='insert'   : typeSpecOut['codeConverter']='insert(pair<'+convertedIdxType+', '+convertedItmType+'>(%1, %2))';
        elif name=='clear'    : typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif name=='front'    : name='begin()';  typeSpecOut['owner']='itr'; paramList=None;
        elif name=='back'     : name='rbegin()'; typeSpecOut['owner']='itr'; paramList=None;
        elif name=='end'      : name='end()';    typeSpecOut['owner']='itr'; paramList=None;
        elif name=='rend'     : name='rend()';   typeSpecOut['owner']='itr'; paramList=None;
        elif name=='first'    : name='begin()->second';  paramList=None;
        elif name=='last'     : name='rbegin()->second'; paramList=None;
        elif name=='popFirst' : name='pop_front'
        elif name=='popLast'  : name='pop_back'
        else: print "Unknown multimap command:", name; exit(2);
    elif containerType=='tree': # TODO: Make trees work
        if name=='insert' or name=='erase': pass
        elif name=='size' : typeSpecOut={'owner':'me', 'fieldType': 'Uint32'}
        elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'Void'}
        else: print "Unknown tree command:", name; exit(2)
    elif containerType=='graph': # TODO: Make graphs work
        if name=='insert' or name=='erase': pass
        elif name=='size' : typeSpecOut={'owner':'me', 'fieldType': 'Uint32'}
        elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'Void'}
        else: print "Unknown graph command:", name; exit(2);
    elif containerType=='stream': # TODO: Make stream work
        pass
    elif containerType=='filesystem': # TODO: Make filesystem work
        pass
    else: print "Unknown container type:", containerType; exit(2);
    return(name, typeSpecOut, paramList, convertedIdxType)

def codeFactor(item, xlator):
    ####  ( value | ('(' + expr + ')') | ('!' + expr) | ('-' + expr) | varFuncRef)
    #print '                  factor: ', item
    S=''
    retType='noType'
    item0 = item[0]
    #print "ITEM0=", item0, ">>>>>", item
    if (isinstance(item0, basestring)):
        if item0=='(':
            [S2, retType] = codeExpr(item[1], xlator)
            S+='(' + S2 +')'
        elif item0=='!':
            [S2, retType] = codeExpr(item[1], xlator)
            S+='!' + S2
        elif item0=='-':
            [S2, retType] = codeExpr(item[1], xlator)
            S+='-' + S2
        elif item0=='[':
            tmp="["
            for expr in item[1:-1]:
                [S2, retType] = codeExpr(expr, xlator)
                if len(tmp)>1: tmp+=", "
                tmp+=S2
            tmp+="]"
            S+=tmp
        else:
            #print "item", item
            retType='string'
            if(item0[0]=="'"): S+=codeUserMesg(item0[1:-1], xlator)
            elif (item0[0]=='"'): S+='"'+item0[1:-1] +'"'
            else: S+=item0;
    else:
        if isinstance(item0[0], basestring):
            S+=item0[0]
        else:
            [codeStr, retType, prntType, AltIDXFormat, varSRC]=codeItemRef(item0, 'RVAL', xlator)
            if(codeStr=="NULL"):
                retType={'owner':"PTR"}
            S+=codeStr                                # Code variable reference or function call
    return [S, retType]

def codeTerm(item, xlator):
    #print '               term item:', item
    [S, retType]=codeFactor(item[0], xlator)
    if (not(isinstance(item, basestring))) and (len(item) > 1) and len(item[1])>0:
        S=derefPtr(S, retType)
        for i in item[1]:
            #print '               term:', i
            if   (i[0] == '*'): S+=' * '
            elif (i[0] == '/'): S+=' / '
            elif (i[0] == '%'): S+=' % '
            else: print "ERROR: One of '*', '/' or '%' expected in code generator."; exit(2)
            [S2, retType2] = codeFactor(i[1], xlator)
            S2=derefPtr(S2, retType2)
            S+=S2
    return [S, retType]

def codePlus(item, xlator):
    #print '            plus item:', item
    [S, retType]=codeTerm(item[0], xlator)
    if len(item) > 1 and len(item[1])>0:
        S=derefPtr(S, retType)
        for  i in item[1]:
            #print '            plus ', i
            if   (i[0] == '+'): S+=' + '
            elif (i[0] == '-'): S+=' - '
            else: print "ERROR: '+' or '-' expected in code generator."; exit(2)
            [S2, retType2] = codeTerm(i[1], xlator)
            S2=derefPtr(S2, retType2)
            S+=S2
    return [S, retType]

def codeComparison(item, xlator):
    #print '         Comp item', item
    [S, retType]=codePlus(item[0], xlator)
    if len(item) > 1 and len(item[1])>0:
        if len(item[1])>1: print "Error: Chained comparisons.\n"; exit(1);
        S=derefPtr(S, retType)
        for  i in item[1]:
            #print '         comp ', i
            if   (i[0] == '<'): S+=' < '
            elif (i[0] == '>'): S+=' > '
            elif (i[0] == '<='): S+=' <= '
            elif (i[0] == '>='): S+=' >= '
            else: print "ERROR: One of <, >, <= or >= expected in code generator."; exit(2)
            [S2, retType] = codePlus(i[1], xlator)
            S2=derefPtr(S2, retType)
            S+=S2
            retType='bool'
    return [S, retType]

def codeIsEQ(item, xlator):
    #print '      IsEq item:', item
    [S, retType]=codeComparison(item[0], xlator)
    if len(item) > 1 and len(item[1])>0:
        if len(item[1])>1: print "Error: Chained == or !=.\n"; exit(1);
        leftOwner=owner=progSpec.getTypeSpecOwner(retType)
        S_derefd = derefPtr(S, retType)
        for i in item[1]:
            #print '      IsEq ', i
            if   (i[0] == '=='): op=' == '
            elif (i[0] == '!='): op=' != '
            else: print "ERROR: '==' or '!=' expected in code generator."; exit(2)
            [S2, retType] = codeComparison(i[1], xlator)
            rightOwner=progSpec.getTypeSpecOwner(retType)
            if not( leftOwner=='itr' and rightOwner=='itr'):
                if S2!='NULL': S=S_derefd
                S2=derefPtr(S2, retType)
            S+= op+S2
            retType='bool'
    return [S, retType]

def codeLogAnd(item, xlator):
    #print '   And item:', item
    [S, retType] = codeIsEQ(item[0], xlator)
    if len(item) > 1 and len(item[1])>0:
        S=derefPtr(S, retType)
        for i in item[1]:
            #print '   AND ', i
            if (i[0] == 'and'):
                [S2, retType] = codeIsEQ(i[1], xlator)
                S2=derefPtr(S2, retType)
                S+=' && ' + S2
            else: print "ERROR: 'and' expected in code generator."; exit(2)
            retType='bool'
    return [S, retType]

def codeExpr(item, xlator):
    #print 'Or item:', item
    [S, retType]=codeLogAnd(item[0], xlator)
    if not isinstance(item, basestring) and len(item) > 1 and len(item[1])>0:
        S=derefPtr(S, retType)
        for i in item[1]:
            #print 'OR ', i
            if (i[0] == 'or'):
                [S2, retType] = codeLogAnd(i[1], xlator)
                S2=derefPtr(S2, retType)
                S+=' || ' + S2
            else: print "ERROR: 'or' expected in code generator."; exit(2)
            retType='bool'
    #print "S:",S
    return [S, retType]

def adjustIfConditional(S2, conditionType):
    return [S2, conditionType]

def codeSpecialFunc(segSpec, xlator):
    S=''
    funcName=segSpec[0]
    if(funcName=='print'):
        # TODO: have a tag to choose cout vs printf()
        S+='print ('
        if(len(segSpec)>2):
            paramList=segSpec[2]
            i =0
            for P in paramList:
                [S2, argType]=xlator['codeExpr'](P[0], xlator)
                S2=derefPtr(S2, argType)
                if (i>0):
                    S+=' + '
                S+=S2
                i = i+1
            S+=")"
    elif(funcName=='AllocateOrClear'):
        if(len(segSpec)>2):
            #print "ALLOCATE-OR-CLEAR():", segSpec[2][0]
            paramList=segSpec[2]
            [varName,  varTypeSpec]=xlator['codeExpr'](paramList[0][0], xlator)
            S+='if('+varName+'){'+varName+'->clear();} else {'+varName+" = "+codeAllocater(varTypeSpec, xlator)+"();}"
    elif(funcName=='Allocate'):
        if(len(segSpec)>2):
            paramList=segSpec[2]
            [varName,  varTypeSpec]=xlator['codeExpr'](paramList[0][0], xlator)
            S+=varName+" = "+codeAllocater(varTypeSpec, xlator)+'('
            count=0   # TODO: As needed, make this call CodeParameterList() with modelParams of the constructor.
            for P in paramList[1:]:
                if(count>0): S+=', '
                [S2, argType]=xlator['codeExpr'](P[0], xlator)
                S+=S2
            S+=")"
    elif(funcName=='callPeriodically'):
        if(len(segSpec)>2):
            # Call g_timeout_add()
            paramList=segSpec[2]
            [objName,  retType]=xlator['codeExpr'](paramList[1][0], xlator)
            [interval,  intSpec]   =xlator['codeExpr'](paramList[2][0], xlator)
            varTypeSpec= retType['fieldType'][0]
            wrapperName="cb_wraps_"+varTypeSpec
            S+='g_timeout_add('+interval+', '+wrapperName+', '+objName+')'

            # Create a global function wrapping the class
            decl='\nInt '+wrapperName+'(Void* data)'
            defn='{'+varTypeSpec+'* self = ('+varTypeSpec+'*)data; self->run(); return true;}\n\n'
            appendGlobalFuncAcc(decl, defn)
    #elif(funcName=='break'):
    #elif(funcName=='return'):
    #elif(funcName==''):

    return S

def checkIfSpecialAssignmentFormIsNeeded(AltIDXFormat, RHS, rhsType):
    return ""

############################################
def codeMain(objects, tags, xlator):
    print "\n            Generating GLOBAL..."
    if("GLOBAL" in objects[1]):
        if(objects[0]["GLOBAL"]['stateType'] != 'struct'):
            print "ERROR: GLOBAL must be a 'struct'."
            exit(2)
        [structCode, funcCode, globalFuncs]=codeStructFields(objects, "GLOBAL", tags, '', xlator)
        if(funcCode==''): funcCode="// No main() function.\n"
        if(structCode==''): structCode="// No Main Globals.\n"
        funcCode = "\n\n"+funcCode
        return ["\n\n// Globals\n" + structCode + globalFuncs, funcCode]
    return ["// No Main Globals.\n", "// No main() function defined.\n"]

def codeActTextMain(actSeq, indent, xlator):
    indent = ""
    actSeqText = ""
    for action in actSeq:
        [actionText, varSRC] = codeAction(action, indent, xlator)
        actSeqText += actionText
    return [actSeqText, varSRC]

def codeArgText(argFieldName, argType, xlator):
    return "_ " + argFieldName + ": " + argType

def codeStructText(classAttrs, parentClass, structName, structCode):
    if parentClass != "":
        parentClass=':'+parentClass+' '
    S= "\nstruct "+structName+parentClass+"{\n" + structCode + '};\n'
    forwardDecls=""
    return([S,forwardDecls])

def produceTypeDefs(typeDefMap, xlator):
    typeDefCode="\n// Typedefs:\n"
    for key in typeDefMap:
        val=typeDefMap[key]
        #sprint '['+key+']='+val+']'
        if(val != '' and val != key):
            typeDefCode += 'typedef '+key+' '+val+';\n'
    return typeDefCode

def addSpecialCode(filename):
    S='\n\n//////////// Swing specific code:\n'
    #S += "\n\nusing namespace std;\n\n"
    #S += 'const string filename = "' + filename + '";\n'
    #S += r'static void reportFault(int Signal){cout<<"\nSegmentation Fault.\n"; fflush(stdout); abort();}'+'\n\n'

    #S += "string enumText(string* array, int enumVal, int enumOffset){return array[enumVal >> enumOffset];}\n";
    #S += "#define SetBits(item, mask, val) {(item) &= ~(mask); (item)|=(val);}\n"

    #string getFilesDirAsString(){}
    #bool doesFileExist(string filePath){}
    #void copyAssetToWritableFolder(string fromPath, string toPath){}


    decl ="string readFileAsString(string filename)"
    defn="""{
        string S="";
        std::ifstream file(filename);
        if(file.eof() || file.fail()) {return "";}
        file.seekg(0, std::ios::end);
        S.resize(file.tellg());
        file.seekg(0, std::ios::beg);
        file.read((char*)S.c_str(), S.length());
        return S;  //No errors
    }"""
    #appendGlobalFuncAcc(decl, defn)

    return S

def addGLOBALSpecialCode(objects, tags, xlator):
    specialCode =''

    GLOBAL_CODE="""
struct GLOBAL{
    %s
}
    """ % (specialCode)

    #codeDogParser.AddToObjectFromText(objects[0], objects[1], GLOBAL_CODE )

def codeNewVarStr (typeSpec, varName, fieldDef, fieldType, innerType, xlator):
    varDeclareStr=''
    assignValue=''
    if(fieldDef['value']):
        [S2, rhsType]=xlator['codeExpr'](fieldDef['value'][0], xlator)
        [leftMod, rightMod]=chooseVirtualRValOwner(typeSpec, rhsType)
        assignValue = " = " + leftMod+S2+rightMod

    else: # If no value was given:
        if fieldDef['paramList'] != None:
            # Code the constructor's arguments
            [CPL, paramTypeList] = codeParameterList(fieldDef['paramList'], None, xlator)
            if len(paramTypeList)==1:
                if not isinstance(paramTypeList[0], dict):
                    print "\nPROBLEM: The return type of the parameter '", CPL, "' cannot be found and is needed. Try to define it.\n"
                    exit(1)

                theParam=paramTypeList[0]['fieldType']

                # TODO: Remove the 'True' and make this check object heirarchies or similar solution
                if True or not isinstance(theParam, basestring) and fieldType==theParam[0]:
                    assignValue = " = " + CPL   # Act like a copy constructor

    if(isStruct(typeSpec['fieldType'])):
        varDeclareStr= "var " + varName + "="+ fieldType + "()"
    else:
        varDeclareStr= "var " + varName + ":"+ fieldType + assignValue
 
    return(varDeclareStr)

def codeForStmt(ctrType, repName, startVal, endVal):
    return "for " + repName+' in '+ startVal + "..." + endVal 

def iterateRangeContainerStr(objectsRef,localVarsAllocated, StartKey, EndKey,containerType,repName,repContainer,datastructID,keyFieldType,indent,xlator):
    willBeModifiedDuringTraversal=True   # TODO: Set this programatically leter.
    actionText = ""
    loopCounterName = ""
    containedType=containerType['fieldType']
    ctrlVarsTypeSpec = {'owner':containerType['owner'], 'fieldType':containedType}

    if datastructID=='multimap' or datastructID=='map':
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType, 'codeConverter':(repName+'.first')}
        localVarsAllocated.append([repName+'_key', keyVarSpec])  # Tracking local vars for scope
        ctrlVarsTypeSpec['codeConverter'] = (repName+'.second')

        localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
        actionText += (indent + "for (" + repName +"_key, "+ repName+") in "+ repContainer+"->lower_bound("+StartKey+")" + "; " + repName + "Itr !=" + repContainer+"->upper_bound("+EndKey+")" +"; ++"+ repName + "Itr {\n"
                    + indent+"    "+"auto "+repName+" = *"+repName+"Itr;\n")

    elif datastructID=='list' or (datastructID=='deque' and not willBeModifiedDuringTraversal):
        pass;
    elif datastructID=='deque' and willBeModifiedDuringTraversal:
        pass;
    else:
        print "DSID:",datastructID,containerType
        exit(2)

    return [actionText, loopCounterName]

def iterateContainerStr(objectsRef,localVarsAllocated,containerType,repName,repContainer,datastructID,keyFieldType,ContainerOwner,indent,xlator):
    willBeModifiedDuringTraversal=True   # TODO: Set this programatically leter.
    actionText = ""
    loopCounterName = ""
    containedType=containerType['fieldType']
    ctrlVarsTypeSpec = {'owner':containerType['owner'], 'fieldType':containedType}
    if datastructID=='multimap' or datastructID=='map':
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType, 'codeConverter':(repName+'_key')}
        localVarsAllocated.append([repName+'_key', keyVarSpec])  # Tracking local vars for scope
        if datastructID=='multimap':
            ctrlVarsTypeSpec['codeConverter'] = (repName+'[0]')
        else:
            ctrlVarsTypeSpec['codeConverter'] = (repName)

        localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
        actionText += indent + "for (" + repName +"_key, " + repName + ") in " + repContainer +"{\n"

    elif datastructID=='list' or (datastructID=='deque' and not willBeModifiedDuringTraversal):
        loopCounterName=repName+'_key'
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType}
        localVarsAllocated.append([loopCounterName, keyVarSpec])  # Tracking local vars for scope

        localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
        actionText += (indent + "for( auto " + repName+'Itr ='+ repContainer+'.begin()' + "; " + repName + "Itr !=" + repContainer+'.end()' +"; ++"+ repName + "Itr ){\n"
                    + indent+"    "+"auto "+repName+" = *"+repName+"Itr;\n")
    elif datastructID=='deque' and willBeModifiedDuringTraversal:
        loopCounterName=repName+'_key'
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType}
        localVarsAllocated.append([loopCounterName, keyVarSpec])  # Tracking local vars for scope

        localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
        lvName=repName+"Itr"
        actionText += (indent + "for " + lvName+" in 0..." +  repContainer + ".count-1{\n"
                    + indent+"    var "+repName+" = "+repContainer+"["+lvName+"];\n")
    else:
        print "DSID:",datastructID,containerType
        exit(2)

    return [actionText, loopCounterName]
    
def codeIncrement(varName):
    return varName + "+=1"
    
def codeDecrement(varName):
    return varName + "-=1"

def isNumericType(convertedType):
    if(convertedType == "UInt32" or convertedType == "UInt64" or convertedType == "Float" or convertedType == "Int" or convertedType == "Int32" or convertedType == "Int64" or convertedType == "Double"):
        return True
    else:
        return False

def codeVarFieldRHS_Str(fieldValue, convertedType, fieldOwner, paramList, xlator):
    fieldValueText=""
    if(fieldValue == None):
        if (fieldOwner=='me'):
            if paramList!=None:
                [CPL, paramTypeList] = codeParameterList(paramList, None, xlator)
                fieldValueText=" = new " + convertedType + CPL

    return fieldValueText

def codeVarField_Str(convertedType, typeSpec, fieldName, fieldValueText, objectName, tags, indent):
    convertedType = adjustBaseTypes(convertedType)
    
    if (fieldValueText == ""):
        if (convertedType == "String"):
            fieldValueText=' = ""'
        elif (convertedType.startswith("[")):
            fieldValueText=" = " + convertedType + "()"
        elif (convertedType == "Bool"):
            fieldValueText=' = false'
        elif (isNumericType(convertedType)):
            fieldValueText=' = 0'
        elif (convertedType == "Character"):
            fieldValueText=' = ""'
        elif(convertedType.startswith('map')):
            fieldValueText=' = []'
        else:
            print convertedType, " not initialized."
            exit (2)
    
    if 'arraySpec' in typeSpec:
        if (fieldValueText == ""):
            S=indent + "var "+ fieldName + ":" +  convertedType + '\n'
        else:
            S=indent + "var "+ fieldName + ":" +  convertedType +  fieldValueText + '\n'
    else:
        if (convertedType.startswith('map')):
            S=indent + "var "+ fieldName + fieldValueText + '\n'
        else:
            S=indent + "var "+ fieldName + ":" +  convertedType + fieldValueText + '\n'
    return S

def codeConstructionHeader(ClassName, constructorArgs, constructorInit, xlator):
    return "init (" + constructorArgs+"){"+constructorInit+"\n    }\n"

def codeConstructorInit(fieldName, count, xlator):
    if (count > 0):
        return "\n        self." + fieldName +" = _"+fieldName
    elif(count == 0):
        return "\n        self." + fieldName +" = _"+fieldName
    else:
        print "Error in codeConstructorInit."
        exit(2)


def codeFuncHeaderStr(objectName, fieldName, typeDefName, argListText, localArgsAllocated, isMutating, indent):
    #TODO: add \n before func
    structCode=''; funcDefCode=''; globalFuncs='';
    if (isMutating):
        mutatingStr = "mutating "
    else:
        mutatingStr = ""
    if(objectName=='GLOBAL'):
        if fieldName=='main':
            structCode += '// M A I N ' + '\n'
            localArgsAllocated.append(['argc', {'owner':'me', 'fieldType':'int', 'arraySpec':None,'argList':None}])
            localArgsAllocated.append(['argv', {'owner':'their', 'fieldType':'char', 'arraySpec':None,'argList':None}])  # TODO: Wrong. argv should be an array.
        else:
            structCode += mutatingStr + "func " + fieldName +"("+argListText+") -> " + typeDefName
    else:
        structCode += indent + mutatingStr + "func " + fieldName +"("+argListText+") -> " + typeDefName
    return [structCode, funcDefCode, globalFuncs]

def codeArrayIndex(idx, containerType, LorR_Val):
    S= '[' + idx +']'
    return S

def codeSetBits(LHS_Left, LHS_FieldType, prefix, bitMask, RHS):
    if (LHS_FieldType =='flag' ):
        return "SetBits("+LHS_Left+"flags, "+prefix+bitMask+", "+ RHS + ");\n"
    elif (LHS_FieldType =='mode' ):
        return "SetBits("+LHS_Left+"flags, "+prefix+bitMask+"Mask, "+ RHS+"<<" +prefix+bitMask+"Offset"+");\n"

#######################################################

def includeDirective(libHdr):
    S = 'import '+libHdr+'\n'
    return S

def generateMainFunctionality(objects, tags):
    # TODO: Make initCode, runCode and deInitCode work better and more automated by patterns.
    # TODO: Some deInitialize items should automatically run during abort().
    # TODO: Deinitialize items should happen in reverse order.

    runCode = progSpec.fetchTagValue(tags, 'runCode')
    mainFuncCode="""
    me void: main() <- {
        /-initialize()
        """ + runCode + """
        /-deinitialize()
        /-endFunc()
    }

"""
    progSpec.addObject(objects[0], objects[1], 'GLOBAL', 'struct', 'SEQ')
    codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef('GLOBAL',  mainFuncCode ))


def fetchXlators():
    xlators = {}

    xlators['LanguageName']         = "Swift"
    xlators['BuildStrPrefix']       = ""
    xlators['fileExtension']        = ".swift"
    xlators['typeForCounterInt']    = "var"
    xlators['GlobalVarPrefix']      = ""
    xlators['PtrConnector']         = "->"                      # Name segment connector for pointers.
    xlators['ObjConnector']         = "::"                      # Name segment connector for classes.
    xlators['NameSegConnector']     = "."
    xlators['NameSegFuncConnector'] = "()."
    xlators['doesLangHaveGlobals']  = "True"
    xlators['funcBodyIndent']       = "    "
    xlators['funcsDefInClass']      = "True"
    xlators['MakeConstructors']     = "False"
    xlators['codeExpr']                     = codeExpr
    xlators['adjustIfConditional']          = adjustIfConditional
    xlators['includeDirective']             = includeDirective
    xlators['codeMain']                     = codeMain
    xlators['produceTypeDefs']              = produceTypeDefs
    xlators['addSpecialCode']               = addSpecialCode
    xlators['convertType']                  = convertType
    xlators['xlateLangType']                = xlateLangType
    xlators['getContainerType']             = getContainerType
    xlators['langStringFormatterCommand']   = langStringFormatterCommand
    xlators['getCodeAllocStr']              = getCodeAllocStr
    xlators['getCodeAllocSetStr']           = getCodeAllocSetStr
    xlators['codeSpecialFunc']              = codeSpecialFunc
    xlators['checkIfSpecialAssignmentFormIsNeeded'] = checkIfSpecialAssignmentFormIsNeeded
    xlators['getConstIntFieldStr']          = getConstIntFieldStr
    xlators['codeStructText']               = codeStructText
    xlators['getContainerTypeInfo']         = getContainerTypeInfo
    xlators['codeNewVarStr']                = codeNewVarStr
    xlators['chooseVirtualRValOwner']       = chooseVirtualRValOwner
    xlators['determinePtrConfigForAssignments'] = determinePtrConfigForAssignments
    xlators['iterateRangeContainerStr']     = iterateRangeContainerStr
    xlators['iterateContainerStr']          = iterateContainerStr
    xlators['getEnumStr']                   = getEnumStr
    xlators['codeVarFieldRHS_Str']          = codeVarFieldRHS_Str
    xlators['codeVarField_Str']             = codeVarField_Str
    xlators['codeFuncHeaderStr']            = codeFuncHeaderStr
    xlators['codeArrayIndex']               = codeArrayIndex
    xlators['codeSetBits']                  = codeSetBits
    xlators['generateMainFunctionality']    = generateMainFunctionality
    xlators['addGLOBALSpecialCode']         = addGLOBALSpecialCode
    xlators['codeArgText']                  = codeArgText
    xlators['codeActTextMain']              = codeActTextMain
    xlators['recodeStringFunctions']        = recodeStringFunctions
    xlators['codeConstructionHeader']       = codeConstructionHeader
    xlators['codeConstructorInit']          = codeConstructorInit
    xlators['codeIncrement']                = codeIncrement
    xlators['codeDecrement']                = codeDecrement
    xlators['codeForStmt']                  = codeForStmt
    return(xlators)
