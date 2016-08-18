#xlator_CPP.py
import progSpec
from CodeGenerator_CPP import codeItemRef, codeUserMesg, processOtherStructFields

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



######################################################   E X P R E S S I O N   C O D I N G

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
    xlators['PtrConnector']     = "->"                      # Name segment connector for pointers.
    xlators['codeExpr']         = codeExpr
    xlators['includeDirective'] = includeDirective
    xlators['processMain']      = processMain
    xlators['produceTypeDefs']  = produceTypeDefs
    xlators['addSpecialCode']   = addSpecialCode
    xlators['convertType']      = convertType
    xlators['xlateLangType']    = xlateLangType
    xlators['getContainerType'] = getContainerType

    return(xlators)
