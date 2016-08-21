import progSpec
from CodeGenerator_Java import codeItemRef, codeUserMesg

###### Routines to track types of identifiers and to look up type based on identifier.
def getContainerType(typeSpec):
    containerSpec=typeSpec['arraySpec']
    idxType=''
    if 'indexType' in containerSpec:
        idxType=containerSpec['indexType']
    if idxType[0:4]=='uint': idxType = 'Long'
    elif idxType=='string': idxType = 'String'

    datastructID = containerSpec['datastructID']
    if(datastructID=='list'): datastructID = "ArrayDeque"
    elif(datastructID=='map'): datastructID = "TreeMap"
    elif(datastructID=='multimap'): datastructID = "TreeMap"  # TODO: Implement true multmaps in java
    return [datastructID, idxType]

def convertToJavaType(fieldType):
    if(fieldType=='int32'):
        javaType='int'
    elif(fieldType=='uint32' or fieldType=='uint64'):
        javaType='long'
    elif(fieldType=='int64'):
        javaType='long'
    elif(fieldType=='char' ):
        javaType='byte'
    elif(fieldType=='bool' ):
        javaType='boolean'
    elif(fieldType=='string' ):
        javaType='String'
    else:
        javaType=progSpec.flattenObjectName(fieldType)
    #print "javaType: ", javaType
    return javaType



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
        langType= convertToJavaType(fieldType)
    else: langType=progSpec.flattenObjectName(fieldType[0])

    if owner=='const':
        langType = "final static "+langType
    elif owner=='me':
        langType = langType
    elif owner=='my':
        langType = langType
    elif owner=='our':
        langType = langType
    elif owner=='their':
        langType = langType
    else:
        print "ERROR: Owner of type not valid '" + owner + "'"
        exit(1)
    if langType=='TYPE ERROR': print langType, owner, fieldType;

    if 'arraySpec' in TypeSpec:
        arraySpec=TypeSpec['arraySpec']
        if(arraySpec): # Make list, map, etc
            [containerType, idxType]=getContainerType(TypeSpec)
            print "IDX-TYPe:", idxType
            if containerType=='ArrayDeque':
                langType="ArrayDeque< "+langType+" >"
            elif containerType=='TreeMap':
                langType="TreeMap< "+idxType+', '+langType+" >"
            elif containerType=='multimap':
                langType="multimap< "+idxType+', '+langType+" >"
    return langType

def langStringFormatterCommand(fmtStr, argStr):
    fmtStr=fmtStr.replace(r'%i', r'%d')
    fmtStr=fmtStr.replace(r'%l', r'%d')
    S='String.format('+'"'+ fmtStr +'"'+ argStr +')'
    return S

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
            [codeStr, retType]= codeItemRef(item0, 'RVAL', xlator)
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
################################################
def processMain(objects, tags, xlator):
    return ["", ""]

def produceTypeDefs(typeDefMap, xlator):
    return ''

def addSpecialCode():
    S='\n\n//////////// Java specific code:\n'
    S+="""

    """
    return S

#######################################################

def includeDirective(libHdr):
    S = 'import '+libHdr+';\n'
    return S

def fetchXlators():
    xlators = {}

    xlators['LanguageName']     = "Java"
    xlators['BuildStrPrefix']   = "Javac "
    xlators['typeForCounterInt']= "long"
    xlators['GlobalVarPrefix']  = "GLOBAL.static_Global."
    xlators['PtrConnector']     = "."                      # Name segment connector for pointers.
    xlators["codeExpr"]         = codeExpr
    xlators['includeDirective'] = includeDirective
    xlators['processMain']      = processMain
    xlators['produceTypeDefs']  = produceTypeDefs
    xlators['addSpecialCode']   = addSpecialCode
    xlators['convertType']      = convertType
    xlators['xlateLangType']    = xlateLangType
    xlators['getContainerType'] = getContainerType
    xlators['langStringFormatterCommand'] = langStringFormatterCommand

    return(xlators)
