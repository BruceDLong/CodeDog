#xlator_CPP.py
import progSpec
from CodeGenerator_CPP import codeItemRef, codeUserMesg, processOtherStructFields, codeAllocater

###### Routines to track types of identifiers and to look up type based on identifier.
def getContainerType(typeSpec):
    containerSpec=typeSpec['arraySpec']
    idxType=''
    if 'indexType' in containerSpec:
        idxType=containerSpec['indexType']
    datastructID = containerSpec['datastructID']
    if idxType[0:4]=='uint': idxType+='_t'
    if(datastructID=='list'): datastructID = "deque"
    return [datastructID, idxType]

def convertType(objects, TypeSpec, xlator):
    owner=TypeSpec['owner']
    fieldType=TypeSpec['fieldType']
    #print "fieldType: ", fieldType
    if not isinstance(fieldType, basestring):
        #if len(fieldType)>1: exit(2)
        fieldType=fieldType[0]
    baseType = progSpec.isWrappedType(objects, fieldType)
    if(baseType!=None):
        owner=baseType['owner']
        fieldType=baseType['fieldType']

    langType="TYPE ERROR"
    if(fieldType=='<%'): return fieldType[1][0]
    return xlateLangType(TypeSpec,owner, fieldType, xlator)

def xlateLangType(TypeSpec,owner, fieldType, xlator):
    if(isinstance(fieldType, basestring)):
        if(fieldType=='uint8' or fieldType=='uint16'): fieldType='uint32'
        elif(fieldType=='int8' or fieldType=='int16'): fieldType='int32'
        if(fieldType=='uint32' or fieldType=='uint64' or fieldType=='int32' or fieldType=='int64'):
            langType=fieldType+'_t'
        else:
            langType=progSpec.flattenObjectName(fieldType)
    else: langType=progSpec.flattenObjectName(fieldType[0])

    if owner=='const':
        langType = "const "+langType
    elif owner=='me':
        langType = langType
    elif owner=='my':
        langType="unique_ptr<"+langType + '> '
    elif owner=='our':
        langType="shared_ptr<"+langType + '> '
    elif owner=='their':
        langType += '*'
    else:
        print "ERROR: Owner of type not valid '" + owner + "'"
        exit(1)
    if langType=='TYPE ERROR': print langType, owner, fieldType;

    if 'arraySpec' in TypeSpec:
        arraySpec=TypeSpec['arraySpec']
        if(arraySpec): # Make list, map, etc
            [containerType, idxType]=getContainerType(TypeSpec)
            if containerType=='deque':
                langType="deque< "+langType+" >"
            elif containerType=='map':
                langType="map< "+idxType+', '+langType+" >"
            elif containerType=='multimap':
                langType="multimap< "+idxType+', '+langType+" >"
    return langType

def langStringFormatterCommand(fmtStr, argStr):
    S='strFmt('+'"'+ fmtStr +'"'+ argStr +')'
    return S

def chooseVirtualRValOwner(LVAL, RVAL):
    if RVAL==0 or RVAL==None or isinstance(RVAL, basestring): return ['',''] # This happens e.g., string.size() # TODO: fix this.
    if LVAL==0 or LVAL==None or isinstance(LVAL, basestring): return ['', '']
    LeftOwner=LVAL['owner']
    RightOwner=RVAL['owner']
    if LeftOwner == RightOwner: return ["", ""]
    if LeftOwner=='me' and (RightOwner=='my' or RightOwner=='our' or RightOwner=='their'): return ["(*", ")"]
    if (LeftOwner=='my' or LeftOwner=='our' or LeftOwner=='their') and RightOwner=='me': return ["&", '']
    # TODO: Verify these and other combinations. e.g., do we need something like ['', '.get()'] ?
    return ['','']

def getCodeAllocStr(varTypeStr, owner):
    if(owner=='our'): S="make_shared<"+varTypeStr+">"
    elif(owner=='my'): S="make_unique<"+varTypeStr+">"
    elif(owner=='their'): S="new "+varTypeStr
    elif(owner=='me'): print "ERROR: Cannot allocate a 'me' variable."; exit(1);
    elif(owner=='const'): print "ERROR: Cannot allocate a 'const' variable."; exit(1);
    else: print "ERROR: Cannot allocate variable because owner is", owner+"."; exit(1);
    return S

def getConstIntFieldStr(fieldName, fieldValue):
    S= "const int "+fieldName+ " = " + fieldValue+ ";"
    return(S)

def getEnumStr(fieldName, enumList):
    S = "\nenum " + fieldName +" {"
    enumSize = len (enumList)
    count=0
    for enumName in enumList:
        S += enumName+"="+hex(count)
        count=count+1
        if(count<enumSize): S += ", "
    S += "};\n";
    return(S)

######################################################   E X P R E S S I O N   C O D I N G

def getContainerTypeInfo(containerType, name, idxType, typeSpecOut, paramList, objectsRef, xlator):
    convertedIdxType = ""
    if containerType=='deque':
        if name=='at' or name=='insert' or name=='erase' or name=='end' or  name=='rend': pass
        elif name=='size' : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
        elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif name=='front'    : name='begin()'; paramList=None;
        elif name=='back'     : name='rbegin()'; paramList=None;
        elif name=='popFirst' : name='pop_front'
        elif name=='popLast'  : name='pop_back'
        elif name=='pushFirst': name='push_front'
        elif name=='pushLast' : name='push_back'
        else: print "Unknown deque command:", name; exit(2);
    elif containerType=='map':
        convertedIdxType=idxType
        convertedItmType=xlator['convertType'](objectsRef, typeSpecOut, xlator)
        if name=='at' or name=='erase': pass
        elif name=='size' : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
        elif name=='insert'   : typeSpecOut['codeConverter']='insert(pair<'+convertedIdxType+', '+convertedItmType+'>(%1, %2))';
        elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif name=='front': name='begin()->second'; paramList=None;
        elif name=='back': name='rbegin()->second'; paramList=None;
        elif name=='popFirst' : name='pop_front'
        elif name=='popLast'  : name='pop_back'
        else: print "Unknown map command:", name; exit(2);
    elif containerType=='multimap':
        convertedIdxType=idxType
        convertedItmType=xlator['convertType'](objectsRef, typeSpecOut, xlator)
        if name=='at' or name=='erase': pass
        elif name=='size' : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
        elif name=='insert'   : typeSpecOut['codeConverter']='insert(pair<'+convertedIdxType+', '+convertedItmType+'>(%1, %2))';
        elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif name=='front': name='begin()->second'; paramList=None;
        elif name=='back': name='rbegin()->second'; paramList=None;
        elif name=='popFirst' : name='pop_front'
        elif name=='popLast'  : name='pop_back'
        else: print "Unknown multimap command:", name; exit(2);
    elif containerType=='tree': # TODO: Make trees work
        if name=='insert' or name=='erase': pass
        elif name=='size' : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
        elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
        else: print "Unknown tree command:", name; exit(2)
    elif containerType=='graph': # TODO: Make graphs work
        if name=='insert' or name=='erase': pass
        elif name=='size' : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
        elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
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
            tmp="{"
            for expr in item[1:-1]:
                [S2, retType] = codeExpr(expr, xlator)
                if len(tmp)>1: tmp+=", "
                tmp+=S2
            tmp+="}"
            S+=tmp
        else:
            retType='string'
            if(item0[0]=="'"): S+=codeUserMesg(item0[1:-1], xlator)
            elif (item0[0]=='"'): S+='"'+item0[1:-1] +'"'
            else: S+=item0;
    else:
        if isinstance(item0[0], basestring):
            S+=item0[0]
        else:
            [codeStr, retType]=codeItemRef(item0, 'RVAL', xlator)
            S+=codeStr                                # Code variable reference or function call
    return [S, retType]

def codeTerm(item, xlator):
    #print '               term item:', item
    [S, retType]=codeFactor(item[0], xlator)
    if (not(isinstance(item, basestring))) and (len(item) > 1):
        for i in item[1]:
            #print '               term:', i
            if   (i[0] == '*'): S+=' * '
            elif (i[0] == '/'): S+=' / '
            elif (i[0] == '%'): S+=' % '
            else: print "ERROR: One of '*', '/' or '%' expected in code generator."; exit(2)
            [S2, retType2] = codeFactor(i[1], xlator)
            S+=S2
    return [S, retType]

def codePlus(item, xlator):
    #print '            plus item:', item
    [S, retType]=codeTerm(item[0], xlator)
    if len(item) > 1:
        for  i in item[1]:
            #print '            plus ', i
            if   (i[0] == '+'): S+=' + '
            elif (i[0] == '-'): S+=' - '
            else: print "ERROR: '+' or '-' expected in code generator."; exit(2)
            [S2, retType2] = codeTerm(i[1], xlator)
            S+=S2
    return [S, retType]

def codeComparison(item, xlator):
    #print '         Comp item', item
    [S, retType]=codePlus(item[0], xlator)
    if len(item) > 1:
        for  i in item[1]:
            #print '         comp ', i
            if   (i[0] == '<'): S+=' < '
            elif (i[0] == '>'): S+=' > '
            elif (i[0] == '<='): S+=' <= '
            elif (i[0] == '>='): S+=' >= '
            else: print "ERROR: One of <, >, <= or >= expected in code generator."; exit(2)
            [S2, retType] = codePlus(i[1], xlator)
            S+=S2
            retType='bool'
    return [S, retType]

def codeIsEQ(item, xlator):
    #print '      IsEq item:', item
    [S, retType]=codeComparison(item[0], xlator)
    if len(item) > 1:
        for i in item[1]:
            #print '      IsEq ', i
            if   (i[0] == '=='): S+=' == '
            elif (i[0] == '!='): S+=' != '
            else: print "ERROR: 'and' expected in code generator."; exit(2)
            [S2, retType] = codeComparison(i[1], xlator)
            S+=S2
            retType='bool'
    return [S, retType]

def codeLogAnd(item, xlator):
    #print '   And item:', item
    [S, retType] = codeIsEQ(item[0], xlator)
    if len(item) > 1:
        for i in item[1]:
            #print '   AND ', i
            if (i[0] == 'and'):
                [S2, retType] = codeIsEQ(i[1], xlator)
                S+=' && ' + S2
            else: print "ERROR: 'and' expected in code generator."; exit(2)
            retType='bool'
    return [S, retType]

def codeExpr(item, xlator):
    #print 'Or item:', item
    [S, retType]=codeLogAnd(item[0], xlator)
    if not isinstance(item, basestring) and len(item) > 1:
        for i in item[1]:
            #print 'OR ', i
            if (i[0] == 'or'):
                S+=' || ' + codeLogAnd(i[1], xlator)[0]
            else: print "ERROR: 'or' expected in code generator."; exit(2)
            retType='bool'
    #print "S:",S
    return [S, retType]

def codeSpecialFunc(segSpec, xlator):
    S=''
    funcName=segSpec[0]
    if(funcName=='print'):
        # TODO: have a tag to choose cout vs printf()
        S+='cout'
        if(len(segSpec)>2):
            paramList=segSpec[2]
            for P in paramList:
                [S2, argType]=xlator['codeExpr'](P[0], xlator)
                S+=' << '+S2
            S+=" << flush"
    elif(funcName=='AllocateOrClear'):
        if(len(segSpec)>2):
            print "ALLOCATE-OR-CLEAR():", segSpec[2][0]
            paramList=segSpec[2]
            [varName,  varTypeSpec]=xlator['codeExpr'](paramList[0][0], xlator)
            S+='if('+varName+'){'+varName+'->clear();} else {'+varName+" = "+codeAllocater(varTypeSpec, xlator)+";}"
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
    #elif(funcName=='break'):
    #elif(funcName=='return'):
    #elif(funcName==''):

    return S

def codeNewVarStr (typeSpec, fieldDef, fieldType, xlator):
    assignValue=''
    if(fieldDef['value']):
        [S2, rhsType]=xlator['codeExpr'](fieldDef['value'][0], xlator)
        [leftMod, rightMod]=chooseVirtualRValOwner(typeSpec, rhsType)
        RHS = leftMod+S2+rightMod
        assignValue=' = '+ RHS

    return(assignValue)

def iterateContainerStr(xlator):
    localVarsAllocData = ''
    actionText = ''

    return (actionText, localVarsAllocData)

############################################
def processMain(objects, tags, xlator):
    print "\n            Generating GLOBAL..."
    if("GLOBAL" in objects[1]):
        if(objects[0]["GLOBAL"]['stateType'] != 'struct'):
            print "ERROR: GLOBAL must be a 'struct'."
            exit(2)
        [structCode, funcCode, globalFuncs]=processOtherStructFields(objects, "GLOBAL", tags, '', xlator)
        if(funcCode==''): funcCode="// No main() function.\n"
        if(structCode==''): structCode="// No Main Globals.\n"
        return ["\n\n// Globals\n" + structCode + globalFuncs, funcCode]
    return ["// No Main Globals.\n", "// No main() function defined.\n"]

def codeStructText(parentClass, structName, structCode):
    if parentClass != "":
        parentClass=':'+parentClass+' '
    S= "\nstruct "+structName+parentClass+"{\n" + structCode + '};\n'
    forwardDecls="struct " + structName + ";  \t// Forward declaration\n"
    return([S,forwardDecls])


def produceTypeDefs(typeDefMap, xlator):
    typeDefCode="\n// Typedefs:\n"
    for key in typeDefMap:
        val=typeDefMap[key]
        #sprint '['+key+']='+val+']'
        if(val != '' and val != key):
            typeDefCode += 'typedef '+key+' '+val+';\n'
    return typeDefCode

def addSpecialCode():
    S='\n\n//////////// C++ specific code:\n'
    S += "\n\nusing namespace std;\n\n"
    S += r'static void reportFault(int Signal){cout<<"\nSegmentation Fault.\n"; fflush(stdout); abort();}'+'\n\n'

    S += "string enumText(string* array, int enumVal, int enumOffset){return array[enumVal >> enumOffset];}\n";
    S += "#define SetBits(item, mask, val) {(item) &= ~(mask); (item)|=(val);}\n"

    S+="""
    // Thanks to Erik Aronesty via stackoverflow.com
    // Like printf but returns a string.
    // #include <memory>, #include <cstdarg>
    inline std::string strFmt(const std::string fmt_str, ...) {
        int final_n, n = fmt_str.size() * 2; /* reserve 2 times as much as the length of the fmt_str */
        std::string str;
        std::unique_ptr<char[]> formatted;
        va_list ap;
        while(1) {
            formatted.reset(new char[n]); /* wrap the plain char array into the unique_ptr */
            strcpy(&formatted[0], fmt_str.c_str());
            va_start(ap, fmt_str);
            final_n = vsnprintf(&formatted[0], n, fmt_str.c_str(), ap);
            va_end(ap);
            if (final_n < 0 || final_n >= n)
                n += abs(final_n - n + 1);
            else
                break;
        }
        return std::string(formatted.get());
    }
    """
    return S

#######################################################

def includeDirective(libHdr):
    S = '#include <'+libHdr+'>\n'
    return S

def fetchXlators():
    xlators = {}

    xlators['LanguageName']     = "C++"
    xlators['BuildStrPrefix']   = "g++ -g -std=gnu++14  "
    xlators['typeForCounterInt']= "int64_t"
    xlators['GlobalVarPrefix']  = ""
    xlators['PtrConnector']     = "->"                      # Name segment connector for pointers.
    xlators['codeExpr']         = codeExpr
    xlators['includeDirective'] = includeDirective
    xlators['processMain']      = processMain
    xlators['produceTypeDefs']  = produceTypeDefs
    xlators['addSpecialCode']   = addSpecialCode
    xlators['convertType']      = convertType
    xlators['xlateLangType']    = xlateLangType
    xlators['getContainerType'] = getContainerType
    xlators['langStringFormatterCommand']   = langStringFormatterCommand
    xlators['getCodeAllocStr']              = getCodeAllocStr
    xlators['codeSpecialFunc']              = codeSpecialFunc
    xlators['getConstIntFieldStr']          = getConstIntFieldStr
    xlators['doesLangHaveGlobals']          = "True"
    xlators['codeStructText']               = codeStructText
    xlators['getContainerTypeInfo']         = getContainerTypeInfo
    xlators['codeNewVarStr']                = codeNewVarStr
    xlators['chooseVirtualRValOwner']       = chooseVirtualRValOwner
    xlators['iterateContainerStr']          = iterateContainerStr
    xlators['getEnumStr']                   = getEnumStr

    return(xlators)
