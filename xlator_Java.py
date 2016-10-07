import progSpec
from CodeGenerator import codeItemRef, codeUserMesg, codeAllocater

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

def chooseVirtualRValOwner(LVAL, RVAL):
    return ['','']

def determinePtrConfigForAssignments(LVAL, RVAL, assignTag):
    return ['','',  '','']


def getCodeAllocStr(varTypeStr, owner):
    if(owner!='const'):  S="new "+varTypeStr
    else: print "ERROR: Cannot allocate a 'const' variable."; exit(1);
    return S

def getCodeAllocSetStr(varTypeStr, owner, value):
    S=getCodeAllocStr(varTypeStr, owner)
    S+='('+value+')'
    return S

def getConstIntFieldStr(fieldName, fieldValue):
    S= "final int "+fieldName + " = " + fieldValue+ ";"
    return(S)

def getEnumStr(fieldName, enumList):
    S = ""
    count=0
    for enumName in enumList:
        S += getConstIntFieldStr(enumName,hex(count))+"\n"
        count=count+1
    return(S)

######################################################   E X P R E S S I O N   C O D I N G
def getContainerTypeInfo(containerType, name, idxType, typeSpecOut, paramList, objectsRef, xlator):
    convertedIdxType = ""
    if containerType=='ArrayDeque':
        if name=='at' or name=='insert' or name=='erase' or  name=='size' or name=='end' or  name=='rend': pass
        elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif name=='front'    : name='begin()'; paramList=None;
        elif name=='back'     : name='rbegin()'; paramList=None;
        elif name=='popFirst' : name='pop_front'
        elif name=='popLast'  : name='pop_back'
        elif name=='pushFirst': name='push_front'
        elif name=='pushLast' : name='push_back'
        else: print "Unknown ArrayDeque command:", name; exit(2);
    elif containerType=='TreeMap':
        convertedIdxType=idxType
        convertedItmType=xlator['convertType'](objectsRef, typeSpecOut, xlator)
        if name=='at' or name=='erase' or  name=='size': pass
        elif name=='insert'   : name='put';
        elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif name=='front': name='firstEntry().getValue()'; paramList=None;
        elif name=='back': name='lastEntry().getValue()'; paramList=None;
        elif name=='popFirst' : name='pop_front'
        elif name=='popLast'  : name='pop_back'
        else: print "Unknown map command:", name; exit(2);
    elif containerType=='multimap':
        convertedIdxType=idxType
        convertedItmType=xlator['convertType'](objectsRef, typeSpecOut, xlator)
        if name=='at' or name=='erase' or  name=='size': pass
        elif name=='insert'   : name='put'; #typeSpecOut['codeConverter']='put(pair<'+convertedIdxType+', '+convertedItmType+'>(%1, %2))'
        elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif name=='front': name='firstEntry().getValue()'; paramList=None;
        elif name=='back': name='lastEntry().getValue()'; paramList=None;
        elif name=='popFirst' : name='pop_front'
        elif name=='popLast'  : name='pop_back'
        else: print "Unknown multimap command:", name; exit(2);
    elif containerType=='tree': # TODO: Make trees work
        if name=='insert' or name=='erase' or  name=='size': pass
        elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
        else: print "Unknown tree command:", name; exit(2)
    elif containerType=='graph': # TODO: Make graphs work
        if name=='insert' or name=='erase' or  name=='size': pass
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
        S+='System.out.print('
        if(len(segSpec)>2):
            paramList=segSpec[2]
            count=0
            for P in paramList:
                if(count!=0): S+=", "
                count+=1
                [S2, argType]=xlator['codeExpr'](P[0], xlator)
                S+=S2
        S+=")"
    elif(funcName=='AllocateOrClear'):
        if(len(segSpec)>2):
            print "ALLOCATE-OR-CLEAR():", segSpec[2][0]
            paramList=segSpec[2]
            [varName,  varTypeSpec]=xlator['codeExpr'](paramList[0][0], xlator)
            S+='if('+varName+'){'+varName+'.clear();} else {'+varName+" = "+codeAllocater(varTypeSpec, xlator)+";}"
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


################################################
def codeMain(objects, tags, xlator):
    return ["", ""]

def codeStructText(parentClass, structName, structCode):
    if parentClass != "":
        parentClass=' extends '+parentClass+' '
    S= "\nclass "+structName+parentClass+"{\n" + structCode + '};\n'
    return([S,""])


def produceTypeDefs(typeDefMap, xlator):
    return ''

def addSpecialCode():
    S='\n\n//////////// Java specific code:\n'
    S+="""

    """
    return S

def codeNewVarStr (typeSpec, fieldDef, fieldType, xlator):
    if isinstance(typeSpec['fieldType'], basestring):
        if(fieldDef['value']):
            print "                                         fieldDef['value']: "
            [S2, rhsType]=codeExpr(fieldDef['value'][0], xlator)
            RHS = S2
            print "                                             RHS: ", RHS
            assignValue=' = '+ RHS + ';\n'
        else: assignValue=';\n'
    elif(fieldDef['value']):
        [S2, rhsType]=codeExpr(fieldDef['value'][0], xlator)
        RHS = S2
        if not varTypeIsJavaValueType(fieldType):
            assignValue=' = '+ RHS + ';\n'
        else:assignValue=' = new ' + fieldType +'('+ RHS + ');\n'
    else:
        #print "TYPE:", fieldType
        assignValue= " = new " + fieldType +"();\n"
    return(assignValue)

def iterateContainerStr(objectsRef,localVarsAllocated,containerType,repName,repContainer,datastructID,keyFieldType,indent,xlator):
    actionText = ""
    loopCounterName=""
    containedType=containerType['fieldType']
    ctrlVarsTypeSpec = {'owner':containerType['owner'], 'fieldType':containedType}
    if datastructID=='TreeMap':
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':keyFieldType, 'codeConverter':(repName+'.getKey()')}
        localVarsAllocated.append([repName+'_key', keyVarSpec])  # Tracking local vars for scope
        ctrlVarsTypeSpec['codeConverter'] = (repName+'.getValue()')
        containedTypeStr=xlator['convertType'](objectsRef, ctrlVarsTypeSpec, xlator)
        indexTypeStr=xlator['convertType'](objectsRef, keyVarSpec, xlator)
        iteratorTypeStr="Map.Entry<"+indexTypeStr+", "+containedTypeStr+">"
        repContainer+='.entrySet()'
    elif datastructID=='list':
        loopCounterName=repName+'_key'
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType}
        localVarsAllocated.append([loopCounterName, keyVarSpec])  # Tracking local vars for scope
        iteratorTypeStr=xlator['convertType'](objectsRef, ctrlVarsTypeSpec, xlator)
    else: iteratorTypeStr=xlator['convertType'](objectsRef, ctrlVarsTypeSpec, xlator)

    localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
    actionText += (indent + "for("+iteratorTypeStr+" " + repName+' :'+ repContainer+"){\n")
    return [actionText, loopCounterName]

def varTypeIsJavaValueType(convertedType):
    if (convertedType=='int' or convertedType=='long' or convertedType=='byte' or convertedType=='boolean' or convertedType=='char'
       or convertedType=='float' or convertedType=='double' or convertedType=='short'):
        return True
    return False

def codeVarFieldRHS_Str(fieldValue, convertedType, fieldOwner):
    fieldValueText=""
    if(fieldValue == None):
        if (not varTypeIsJavaValueType(convertedType) and fieldOwner!='their'):
            fieldValueText=" = new " + convertedType + "()"
    return fieldValueText

def codeVarField_Str(convertedType, fieldName, fieldValueText, indent):
    S=""
    if (fieldName == "static_Global" or fieldName == "static_gui_tk"):  # TODO: make static_Global so it is not hard coded
        S += indent + "public static " + convertedType + ' ' + fieldName + fieldValueText +';\n';
    else:
        S += indent + "public " + convertedType + ' ' + fieldName + fieldValueText +';\n';
    return S

def codeFuncHeaderStr(objectName, fieldName, typeDefName, argListText, localArgsAllocated, indent):
    structCode=''; funcDefCode=''; globalFuncs='';
    if(objectName=='GLOBAL'):
        if fieldName=='main':
            structCode += indent + "public static void " + fieldName +" (String[] args)\n";
            #localArgsAllocated.append(['args', {'owner':'me', 'fieldType':'String', 'arraySpec':None,'argList':None}])
        else:
            structCode += indent + "public " + typeDefName + ' ' + fieldName +"("+argListText+")\n"

    else:
        structCode += indent + "public " + typeDefName +' ' + fieldName +"("+argListText+")\n";
    return [structCode, funcDefCode, globalFuncs]

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
    xlators['doesLangHaveGlobals'] = "False"
    xlators['funcBodyIndent']   = "    "
    xlators['funcsDefInClass']  = "True"
    xlators['MakeConstructors'] = "False"
    xlators['codeExpr']         = codeExpr
    xlators['includeDirective'] = includeDirective
    xlators['codeMain']         = codeMain
    xlators['produceTypeDefs']  = produceTypeDefs
    xlators['addSpecialCode']   = addSpecialCode
    xlators['convertType']      = convertType
    xlators['xlateLangType']    = xlateLangType
    xlators['getContainerType'] = getContainerType
    xlators['langStringFormatterCommand']   = langStringFormatterCommand
    xlators['getCodeAllocStr']              = getCodeAllocStr
    xlators['getCodeAllocSetStr']           = getCodeAllocSetStr
    xlators['codeSpecialFunc']              = codeSpecialFunc
    xlators['getConstIntFieldStr']          = getConstIntFieldStr
    xlators['codeStructText']               = codeStructText
    xlators['getContainerTypeInfo']         = getContainerTypeInfo
    xlators['codeNewVarStr']                = codeNewVarStr
    xlators['chooseVirtualRValOwner']       = chooseVirtualRValOwner
    xlators['determinePtrConfigForAssignments'] = determinePtrConfigForAssignments
    xlators['iterateContainerStr']          = iterateContainerStr
    xlators['getEnumStr']                   = getEnumStr
    xlators['codeVarFieldRHS_Str']          = codeVarFieldRHS_Str
    xlators['codeVarField_Str']             = codeVarField_Str
    xlators['codeFuncHeaderStr']            = codeFuncHeaderStr

    return(xlators)
