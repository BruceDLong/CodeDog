#This file, along with Lib_Java.py specify to the CodeGenerater how to compile CodeDog source code into Java source code.
import progSpec
import codeDogParser
from progSpec import cdlog, cdErr, logLvl
from CodeGenerator import codeItemRef, codeUserMesg, codeAllocater, codeParameterList, makeTagText, codeAction, getModeStateNames

###### Routines to track types of identifiers and to look up type based on identifier.
def getContainerType(typeSpec, actionOrField):
    containerSpec = progSpec.getContainerSpec(typeSpec)
    if 'owner' in containerSpec: owner=containerSpec['owner']
    else: owner='me'
    idxType=''
    if progSpec.isAContainer(typeSpec):
        if 'indexType' in containerSpec:
            if 'IDXowner' in containerSpec:
                idxOwner=containerSpec['IDXowner']
                idxType=containerSpec['idxBaseType'][0]
                idxType=applyOwner(idxOwner, idxType, 'IDX ERROR', containerSpec['indexType'], actionOrField, '')
            else: idxType=containerSpec['idxBaseType'][0]
        else:
            idxType = progSpec.getFieldType(typeSpec)
        convertToJavaType(idxType, True)

    datastructID = containerSpec['datastructID']
    if(datastructID=='list'):       datastructID = 'ArrayList'
    elif(datastructID=='map'):      datastructID = 'TreeMap'
    elif(datastructID=='multimap'): datastructID = 'TreeMap'  # TODO: Implement true multmaps in java
    return [datastructID, idxType, owner]

def convertToJavaType(fieldType, isContainer):
    javaType = ''
    if fieldType !="":
        if isContainer:
            if fieldType=='int':         javaType = 'Integer'
            elif fieldType=='long':      javaType = 'Long'
            elif fieldType=='double':    javaType = 'Double'
            elif fieldType=='timeValue': javaType = 'Long' # this is hack and should be removed ASAP
            elif fieldType=='int64':     javaType = 'Long'
            elif fieldType=='string':    javaType = 'String'
            elif fieldType=='uint':      javaType = 'Integer'
            else:
                javaType = fieldType
                #print "javaType: ", javaType
        else:
            if(fieldType=='int32'):      javaType= 'int'
            elif(fieldType=='uint32' or fieldType=='uint64' or fieldType=='uint'):javaType='int'  # these should be long but Java won't allow
            elif(fieldType=='int64'):    javaType= 'long'
            elif(fieldType=='char' ):    javaType= 'char'
            elif(fieldType=='bool' ):    javaType= 'boolean'
            elif(fieldType=='string'):   javaType= 'String'
            else: javaType=progSpec.flattenObjectName(fieldType)
    return javaType

def convertType(classes, TypeSpec, varMode, actionOrField, xlator):
    owner=TypeSpec['owner']
    fieldType=TypeSpec['fieldType']
    #print "fieldType: ", fieldType
    if not isinstance(fieldType, basestring):
        #if len(fieldType)>1: exit(2)
        fieldType=fieldType[0]
    baseType = progSpec.isWrappedType(classes, fieldType)
    if(baseType!=None):
        owner=baseType['owner']
        fieldType=baseType['fieldType']

    langType="TYPE ERROR"
    if(fieldType=='<%'): return fieldType[1][0]
    return xlateLangType(TypeSpec,owner, fieldType, varMode, actionOrField, xlator)

def codeIteratorOperation(itrCommand):
    result = ''
    if itrCommand=='goNext':  result='%0.next()'
    elif itrCommand=='goPrev':result='%0.JAVA ERROR!'
    elif itrCommand=='key':   result='%0.getKey()'
    elif itrCommand=='val':   result='%0.next().getValue()'
    return result

def applyOwner(owner, langType, innerType, idxType, actionOrField, varMode):
    if owner=='const':
        if actionOrField=="field": langType = "final static "+langType
        else: langType = "final "+langType
    elif owner=='me':
        langType = langType
    elif owner=='my':
        langType = langType
    elif owner=='our':
        langType = langType
    elif owner=='their':
        langType = langType
    elif owner=='itr':
        langType = langType="Iterator<Map.Entry<"+idxType+', '+innerType+"> >"
    elif owner=='we':
        langType = 'static '+langType
    else:
        cdErr("ERROR: Owner of type not valid '" + owner + "'")
    return langType

def xlateLangType(TypeSpec,owner, fieldType, varMode, actionOrField, xlator):
    # varMode is 'var' or 'arg'.
    if(isinstance(fieldType, basestring)):
        if(fieldType=='uint8' or fieldType=='uint16'): fieldType='uint32'
        elif(fieldType=='int8' or fieldType=='int16'): fieldType='int32'
        langType= convertToJavaType(fieldType, progSpec.isAContainer(TypeSpec))
    else: langType=progSpec.flattenObjectName(fieldType[0])
    langType = applyOwner(owner, langType, 'Itr-Error', 'ITR-ERROR', actionOrField, varMode)
    if langType=='TYPE ERROR': print langType, owner, fieldType;
    InnerLangType = langType

    if 'fieldType' in TypeSpec and not(isinstance(TypeSpec['fieldType'], basestring)) and TypeSpec['fieldType'][0]=='DblLinkedList':
        print"xlateLangType DblLinkedList"
        return [langType, InnerLangType]

    if progSpec.isAContainer(TypeSpec):
        containerSpec= progSpec.getContainerSpec(TypeSpec)
        if(containerSpec): # Make list, map, etc
            [containerType, idxType, owner]=getContainerType(TypeSpec, actionOrField)
            if 'owner' in containerSpec:    containerOwner=containerSpec['owner']
            else:                           containerOwner='me'
            idxType = convertToJavaType(idxType, True)
            langType = convertToJavaType(langType, True)
            InnerLangType = langType
            if containerType=='ArrayList':  langType ="ArrayList<"+langType+'>'
            elif containerType=='TreeMap':  langType ='TreeMap<'+idxType+', '+langType+'>'
            elif containerType=='multimap': langType ='multimap<'+idxType+', '+langType+'>'
            if varMode != 'alloc':          langType=applyOwner(containerOwner, langType, InnerLangType, idxType, actionOrField, varMode)
    if owner =="const":                     InnerLangType = fieldType
    return [langType, InnerLangType]

def recodeStringFunctions(name, typeSpec):
    if name == "size": name = "length"
    elif name == "subStr":
        typeSpec['codeConverter']='%0.substring(%1, %1+%2)'
    elif name == "append":
        typeSpec['codeConverter']='%0 += %1'

    return [name, typeSpec]

def langStringFormatterCommand(fmtStr, argStr):
    fmtStr=fmtStr.replace(r'%i', r'%d')
    fmtStr=fmtStr.replace(r'%l', r'%d')
    S='String.format('+'"'+ fmtStr +'"'+ argStr +')'
    return S

def LanguageSpecificDecorations(S, segType, owner):
        return S

def checkForTypeCastNeed(LHS_Type, RHS_Type, codeStr):
    LHS_KeyType = progSpec.fieldTypeKeyword(LHS_Type)
    RHS_KeyType = progSpec.fieldTypeKeyword(RHS_Type)
    if LHS_KeyType == 'bool' and progSpec.typeIsPointer(RHS_KeyType): return '(' + codeStr + ' != null)'
    if (LHS_KeyType == 'bool' or LHS_KeyType == 'boolean') and (RHS_KeyType=='int' or RHS_KeyType=='flag'):
        if codeStr[0]=='!': return '(' + codeStr[1:] + ' == 0)'
        else: return '(' + codeStr + ' != 0)'
    return codeStr

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
    S= "public static final int "+fieldName + " = " + fieldValue+ ";\n"
    return(S)

def getEnumStr(fieldName, enumList):
    S=''
    count=0
    for enumName in enumList:
        S += "    " + getConstIntFieldStr(enumName, str(count))
        count=count+1
    S += "\n"
   # S += 'public static final String ' + fieldName+'Strings[] = {"'+('", "'.join(enumList))+'"};\n'
    return(S)
######################################################   E X P R E S S I O N   C O D I N G
def getContainerTypeInfo(classes, containerType, name, idxType, typeSpecIn, paramList, xlator):
    convertedIdxType = ""
    typeSpecOut = typeSpecIn
    if 'fieldType' in typeSpecIn and not(isinstance(typeSpecIn['fieldType'], basestring)) and typeSpecIn['fieldType'][0]=='DblLinkedList':
        print"getContainerTypeInfo DblLinkedList"
        return(name, typeSpecOut, paramList, convertedIdxType)
    if containerType=='ArrayList':
        if name=='at': pass
        elif name=='erase'    : name='remove'
        elif name=='size'     : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
        elif name=='insert'   : name='add';
        elif name=='clear'    : typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif name=='front'    : name='begin()';  typeSpecOut['owner']='itr'; paramList=None;
        elif name=='back'     : name='rbegin()'; typeSpecOut['owner']='itr'; paramList=None;
        elif name=='end'      : name='end()';    typeSpecOut['owner']='itr'; paramList=None;
        elif name=='rend'     : name='rend()';   typeSpecOut['owner']='itr'; paramList=None;
        elif name=='nthItr'   : typeSpecOut['codeConverter']='%G%1';  typeSpecOut['owner']='itr';
        elif name=='first'    : name='get(0)';   paramList=None;
        elif name=='last'     : name='%0.get(%0.size()-1)'; paramList=None;
        elif name=='popFirst' : name='remove(0)';   paramList=None;
        elif name=='popLast'  : typeSpecOut['codeConverter']='%0.remove(%0.size() - 1)';  typeSpecOut['owner']='itr';
        elif name=='pushFirst': typeSpecOut['codeConverter']='%0.add(0, %1)';  typeSpecOut['owner']='itr';
        elif name=='pushLast' : name='add'
        elif name=='isEmpty'  : name='isEmpty'
        elif name=='deleteNth': name='remove'
        else: print "Unknown ArrayList command:", name; exit(2);
    elif containerType=='TreeMap':
        convertedIdxType=idxType
        [convertedItmType, innerType]=xlator['convertType'](classes, typeSpecOut, 'var', '', xlator)
        if name=='at': pass
        elif name=='containsKey'   : name="containsKey"; typeSpecOut={'owner':'me', 'fieldType': 'bool'}
        elif name=='size'     : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
        elif name=='insert'   : name='put';
        elif name=='clear'    : typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif name=='find'     : typeSpecOut['owner']='itr'; typeSpecOut['fieldType']=convertedItmType;  typeSpecOut['codeConverter']='tailMap(%1).entrySet().iterator()';
        elif name=='get'      : name='get';      typeSpecOut['owner']='me';  typeSpecOut['fieldType']=convertedItmType;
        elif name=='front'    : name='firstEntry().getValue()';  typeSpecOut['owner']='itr'; paramList=None;
        elif name=='back'     : name='rbegin()'; typeSpecOut['owner']='itr'; paramList=None;
        elif name=='end'      : typeSpecOut['codeConverter']='%Gnull';    typeSpecOut['owner']='itr'; paramList=None;
        elif name=='rend'     : typeSpecOut['codeConverter']='%Gnull';    typeSpecOut['owner']='itr'; paramList=None;
        elif name=='first'    : name='get(0)';   paramList=None;
        elif name=='last'     : name='%0.get(%0.size()-1)'; paramList=None;
        elif name=='popFirst' : name='%0.remove(%0.firstKey())'; paramList=None;
        elif name=='popLast'  : name='pollLastEntry'
        elif name=='erase'    : name='remove'
        elif name=='isEmpty'  : name='isEmpty';typeSpecOut={'owner':'me', 'fieldType': 'bool'}
        else: print "ERROR: Unknown map command:", name; exit(2);
    elif containerType=='multimap':
        convertedIdxType=idxType
        [convertedItmType, innerType]=xlator['convertType'](classes, typeSpecOut, 'var', '', xlator)
        if name=='at' or name=='erase': pass
        elif name=='size'     : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
        elif name=='insert'   : name='put'; #typeSpecOut['codeConverter']='put(pair<'+convertedIdxType+', '+convertedItmType+'>(%1, %2))'
        elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif name=='front'    : name='begin()';  typeSpecOut['owner']='itr'; paramList=None;
        elif name=='back'     : name='rbegin()'; typeSpecOut['owner']='itr'; paramList=None;
        elif name=='end'      : typeSpecOut['codeConverter']='%Gnull';    typeSpecOut['owner']='itr'; paramList=None;
        elif name=='rend'     : typeSpecOut['codeConverter']='%Gnull';    typeSpecOut['owner']='itr'; paramList=None;
        elif name=='first'    : name='get(0)';   paramList=None;
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

def codeFactor(item, objsRefed, returnType, xlator):
    ####  ( value | ('(' + expr + ')') | ('!' + expr) | ('-' + expr) | varFuncRef)
    #print '                  factor: ', item
    S=''
    retTypeSpec='noType'
    item0 = item[0]
    #print "ITEM0=", item0, ">>>>>", item
    if (isinstance(item0, basestring)):
        if item0=='(':
            [S2, retTypeSpec] = codeExpr(item[1], objsRefed, returnType, xlator)
            S+='(' + S2 +')'
        elif item0=='!':
            [S2, retTypeSpec] = codeExpr(item[1], objsRefed, returnType, xlator)
            if(progSpec.typeIsPointer(retTypeSpec)):
                S= '('+S2+' == null)'
                retTypeSpec='bool'
            else: S+='!' + S2
        elif item0=='-':
            [S2, retTypeSpec] = codeExpr(item[1], objsRefed, returnType, xlator)
            S+='-' + S2
        elif item0=='[':
            count=0
            tmp="(Arrays.asList("
            for expr in item[1:-1]:
                count+=1
                [S2, exprTypeSpec] = codeExpr(expr, objsRefed, returnType, xlator)
                if not exprTypeSpec=='noType':
                    retTypeSpec = convertToJavaType(exprTypeSpec, True)
                if count>1: tmp+=', '
                tmp+=S2
                if exprTypeSpec=='Long' or exprTypeSpec=='noType':
                    if '*' in S2:
                        numVal = S2
                        #print 'numVal', numVal
                    elif long(S2) > 2147483647:
                        tmp+="L"
                        retTypeSpec = 'Long'
            tmp+="))"
            typeKeyword = progSpec.fieldTypeKeyword(retTypeSpec)
            typeKeyword = convertToJavaType(typeKeyword, True)
            S+='new '+'ArrayList<'+typeKeyword+'>'+tmp   # ToDo: make this handle things other than long.
        else:
            if(item0[0]=="'"):    S+=codeUserMesg(item0[1:-1], xlator);   retTypeSpec='String'
            elif (item0[0]=='"'): S+='"'+item0[1:-1] +'"';                retTypeSpec='String'
            else:                 S+=item0;
    else: # CODEDOG LITERALS
        if isinstance(item0[0], basestring):
            S+=item0[0]
            if '"' in S or "'" in S: retTypeSpec = 'string'
            if '.' in S: retTypeSpec = 'double'
            if isinstance(S, long): retTypeSpec = 'int64'
            else:  retTypeSpec = 'int32'
        else:
            [codeStr, retTypeSpec, prntType, AltIDXFormat]=codeItemRef(item0, 'RVAL', objsRefed, returnType, xlator)
            if(codeStr=="NULL"): codeStr="null"
            typeKeyword = progSpec.fieldTypeKeyword(retTypeSpec)
            if (len(item0[0]) > 1  and item0[0][0]==typeKeyword and item0[0][1] and item0[0][1]=='('):
                codeStr = 'new ' + codeStr
            S+=codeStr                                # Code variable reference or function call
    return [S, retTypeSpec]

def codeTerm(item, objsRefed, returnType, xlator):
    #print '               term item:', item
    [S, retTypeSpec]=codeFactor(item[0], objsRefed, returnType, xlator)
    if (not(isinstance(item, basestring))) and (len(item) > 1) and len(item[1])>0:
        for i in item[1]:
            #print '               term:', i
            if   (i[0] == '*'): S+=' * '
            elif (i[0] == '/'): S+=' / '
            elif (i[0] == '%'): S+=' % '
            else: print "ERROR: One of '*', '/' or '%' expected in code generator."; exit(2)
            [S2, retType2] = codeFactor(i[1], objsRefed, returnType, xlator)
            S+=S2
    return [S, retTypeSpec]

def codePlus(item, objsRefed, returnType, xlator):
    #print '            plus item:', item
    [S, retTypeSpec]=codeTerm(item[0], objsRefed, returnType, xlator)
    if len(item) > 1 and len(item[1])>0:
        for  i in item[1]:
            #print '            plus ', i
            if   (i[0] == '+'): S+=' + '
            elif (i[0] == '-'): S+=' - '
            else: print "ERROR: '+' or '-' expected in code generator."; exit(2)
            [S2, retType2] = codeTerm(i[1], objsRefed, returnType, xlator)
            S+=S2
    return [S, retTypeSpec]

def codeComparison(item, objsRefed, returnType, xlator):
    #print '         Comp item', item
    [S, retTypeSpec]=codePlus(item[0], objsRefed, returnType, xlator)
    if len(item) > 1 and len(item[1])>0:
        for  i in item[1]:
            #print '         comp ', i
            if   (i[0] == '<'): S+=' < '
            elif (i[0] == '>'): S+=' > '
            elif (i[0] == '<='): S+=' <= '
            elif (i[0] == '>='): S+=' >= '
            else: print "ERROR: One of <, >, <= or >= expected in code generator."; exit(2)
            [S2, retTypeSpec] = codePlus(i[1], objsRefed, returnType, xlator)
            S+=S2
            retTypeSpec='bool'
    return [S, retTypeSpec]

def codeIsEQ(item, objsRefed, returnType, xlator):
    #print '      IsEq item:', item
    [S, retTypeSpec]=codeComparison(item[0], objsRefed, returnType, xlator)
    if len(item) > 1 and len(item[1])>0:
        if len(item[1])>1: print "Error: Chained == or !=.\n"; exit(1);
        if (isinstance(retTypeSpec, int)): cdlog(logLvl(), "Invalid item in ==: {}".format(item[0]))
        leftOwner=owner=progSpec.getTypeSpecOwner(retTypeSpec)
        for i in item[1]:
            #print '      IsEq ', i
            if   (i[0] == '=='): op=' == '
            elif (i[0] == '!='): op=' != '
            elif (i[0] == '==='): op=' == '
            else: print "ERROR: '==' or '!=' or '===' expected."; exit(2)
            [S2, retType2] = codeComparison(i[1], objsRefed, returnType, xlator)
            rightOwner=progSpec.getTypeSpecOwner(retType2)
            if not isinstance(retTypeSpec, basestring) and isinstance(retTypeSpec['fieldType'], basestring) and isinstance(retType2, basestring):
                if retTypeSpec['fieldType'] == "char" and retType2 == 'String'and S2[0] == '"':
                    S2 = "'" + S2[1:-1] + "'"
            if i[0] == '===':
                S = S + " == "+ S2
            else:S+= op+S2
            retTypeSpec='bool'
    return [S, retTypeSpec]

def codeLogAnd(item, objsRefed, returnType, xlator):
    #print '   And item:', item
    [S, retTypeSpec] = codeIsEQ(item[0], objsRefed, returnType, xlator)
    if len(item) > 1 and len(item[1])>0:
        for i in item[1]:
            #print '   AND ', i
            if (i[0] == 'and'):
                S = checkForTypeCastNeed('bool', retTypeSpec, S)
                [S2, retTypeSpec] = codeIsEQ(i[1], objsRefed, returnType, xlator)
                S2= checkForTypeCastNeed('bool', retTypeSpec, S2)
                S+=' && ' + S2
            else: print "ERROR: 'and' expected in code generator."; exit(2)
            retTypeSpec='bool'
    return [S, retTypeSpec]

def codeExpr(item, objsRefed, returnType, xlator):
    #print 'Or item:', item
    [S, retTypeSpec]=codeLogAnd(item[0], objsRefed, returnType, xlator)
    if not isinstance(item, basestring) and len(item) > 1 and len(item[1])>0:
        for i in item[1]:
            #print 'OR ', i
            if (i[0] == 'or'):
                S = checkForTypeCastNeed('bool', retTypeSpec, S)
                [S2, retTypeSpec] = codeLogAnd(i[1], objsRefed, returnType, xlator)
                S2= checkForTypeCastNeed('bool', retTypeSpec, S2)
                S+=' || ' + S2
            else: print "ERROR: 'or' expected in code generator."; exit(2)
            retTypeSpec='bool'
    #print "S:",S
    return [S, retTypeSpec]

def adjustConditional(S2, conditionType):
    #print "CONDITIONTYPE:", conditionType, '[', S2, ']'
    if not isinstance(conditionType, basestring):
        if conditionType['owner']=='our' or conditionType['owner']=='their' or conditionType['owner']=='my' or progSpec.isStruct(conditionType['fieldType']):
            if S2[0]=='!': S2 = S2[1:]+ " == true"
            else: S2+=" != null"
        elif conditionType['owner']=='me' and (conditionType['fieldType']=='flag' or progSpec.typeIsInteger(conditionType['fieldType'])):
            if S2[0]=='!':
                S2 = '('+S2[1:]+' ==0)'
            else:S2+=" !=0"
        conditionType='bool'
    return [S2, conditionType]

def codeSpecialReference(segSpec, objsRefed, xlator):
    S=''
    fieldType='void'   # default to void
    retOwner='me'    # default to 'me'
    funcName=segSpec[0]
    if(len(segSpec)>2):
        paramList=segSpec[2]
        if(funcName=='print'):
            S+='System.out.print('
            count=0
            for P in paramList:
                if(count!=0): S+=" + "
                count+=1
                [S2, argTypeSpec]=xlator['codeExpr'](P[0], objsRefed, None, xlator)
                if 'fieldType' in argTypeSpec: 
                    fieldType = argTypeSpec['fieldType']
                    if not isinstance(fieldType, basestring):
                        fieldType=fieldType[0]
                    fieldType = convertToJavaType(fieldType, False)
                else: fieldType = argTypeSpec
                if fieldType == "timeValue" or fieldType == "int" or fieldType == "double": S2 = '('+S2+')'
                S+=S2
            S+=")"
        elif(funcName=='AllocateOrClear'):
            [varName,  varTypeSpec]=xlator['codeExpr'](paramList[0][0], objsRefed, None, xlator)
            S+='if('+varName+' != null){'+varName+'.clear();} else {'+varName+" = "+codeAllocater(varTypeSpec, xlator)+"();}"
        elif(funcName=='Allocate'):
            [varName,  varTypeSpec]=xlator['codeExpr'](paramList[0][0], objsRefed, None, xlator)
            fieldType = progSpec.getFieldType(varTypeSpec)
            if not isinstance(fieldType, basestring):
                fieldType = fieldType[0]
            S+=varName+" = "+codeAllocater(varTypeSpec, xlator)+'('
            count=0   # TODO: As needed, make this call CodeParameterList() with modelParams of the constructor.
            if fieldType=='workerMsgThread':
                S += '"workerMsgThread"'
            else:
                for P in paramList[1:]:
                    if(count>0): S+=', '
                    [S2, argTypeSpec]=xlator['codeExpr'](P[0], objsRefed, None, xlator)
                    S+=S2
                    count=count+1
            S+=")"
        elif(funcName=='break'):
            if len(paramList)==0: S='break'
        elif(funcName=='return'):
            if len(paramList)==0: S+='return'
        elif(funcName=='self'):
            if len(paramList)==0: S+='this'
        elif(funcName=='toStr'):
            if len(paramList)==1:
                [S2, argTypeSpec]=xlator['codeExpr'](P[0][0], objsRefed, None, xlator)
                S2=derefPtr(S2, argTypeSpec)
                S+='String.valueOf('+S2+')'
                fieldType='String'
    else: # Not parameters, i.e., not a function
        if(funcName=='self'):
            S+='this'

    return [S, retOwner, fieldType]

def codeArrayIndex(idx, containerType, LorR_Val, previousSegName):
    if LorR_Val=='RVAL':
        #Next line may be cause of bug with printing modes.  remove 'not'?
        if (previousSegName in getModeStateNames()): S= '.get(' + idx + ')'
        elif (containerType== 'ArrayList' or containerType== 'TreeMap' or containerType== 'Map' or containerType== 'multimap'):
            S= '.get(' + idx + ')'
        elif (containerType== 'string'): S= '.charAt(' + idx + ')'    # '.substring(' + idx + ', '+ idx + '+1' +')'
        else: S= '[' + idx +']'
    else:
        if containerType== 'ArrayList': S = '.get('+idx+')'
        else: S= '[' + idx +']'
    return S

def checkIfSpecialAssignmentFormIsNeeded(AltIDXFormat, RHS, rhsType):
    # Check for string A[x] = B;  If so, render A.put(B,x)
    [containerType, idxType, owner]=getContainerType(AltIDXFormat[1], "")
    if containerType == 'ArrayList':
        S=AltIDXFormat[0] + '.add(' + AltIDXFormat[2] + ', ' + RHS + ');\n'
    elif containerType == 'TreeMap':
        S=AltIDXFormat[0] + '.put(' + AltIDXFormat[2] + ', ' + RHS + ');\n'
    else:
        print "ERROR in checkIfSpecialAssignmentFormIsNeeded: containerType not found for ", containerType
        exit(1)
    return S
################################################
def codeMain(classes, tags, objsRefed, xlator):
    return ["", ""]

def codeArgText(argFieldName, argType, xlator):
    return argType + " " +argFieldName

def codeStructText(classes, attrList, parentClass, classInherits, classImplements, structName, structCode, tags):
    classAttrs=''
    Platform = progSpec.fetchTagValue(tags, 'Platform')
    if len(attrList)>0:
        for attr in attrList:
            if attr=='abstract': classAttrs += 'abstract '

    if (parentClass != ""):
        parentClass = parentClass.replace('::', '_')
        parentClass = progSpec.unwrapClass(classes, structName)
        parentClass=' extends ' +parentClass
    elif classInherits!=None:
        parentClass=' extends ' + classInherits[0][0]
        #print "parentClass::: " , parentClass
    if classImplements!=None:
        parentClass+=' implements '
        count =0
        for item in classImplements[0]:
            if count>0:
                parentClass+= ', '
            parentClass+= item
            count += 1
        #print "parentClass:: " , parentClass
    if structName =="GLOBAL" and Platform == 'Android':
        classAttrs = "public " + classAttrs
    S= "\n"+classAttrs +"class "+structName+''+parentClass+" {\n" + structCode + '};\n'
    #if classAttrs!='': print "ATTRIBUTE:", classAttrs +"class "+structName+''+parentClass
    return([S,""])

def produceTypeDefs(typeDefMap, xlator):
    return ''

def addSpecialCode(filename):
    S='\n\n//////////// Java specific code:\n'
    return S

def addGLOBALSpecialCode(classes, tags, xlator):
    filename = makeTagText(tags, 'FileName')
    specialCode ='const String: filename <- "' + filename + '"\n'

    GLOBAL_CODE="""
struct GLOBAL{
    %s
}
    """ % (specialCode)

    codeDogParser.AddToObjectFromText(classes[0], classes[1], GLOBAL_CODE, 'Java special code' )

def codeNewVarStr (classes, typeSpec, varName, fieldDef, indent, objsRefed, actionOrField, xlator):
    [fieldTypeSpec, fieldAttrs] = xlator['convertType'](classes, typeSpec, 'var', actionOrField, xlator)
    containerSpec = progSpec.getContainerSpec(typeSpec)
    fieldType = convertToJavaType(fieldTypeSpec, progSpec.isAContainer(typeSpec))
    if isinstance(containerSpec, basestring) and containerSpec == None:
        if(fieldDef['value']):
            [S2, rhsTypeSpec]=codeExpr(fieldDef['value'][0], objsRefed, None, xlator)
            RHS = S2
            assignValue=' = '+ RHS
            #TODO: make test case
        else: assignValue=''
    elif(fieldDef['value']):
        [S2, rhsTypeSpec]=codeExpr(fieldDef['value'][0], objsRefed, None, xlator)
        S2=checkForTypeCastNeed(fieldTypeSpec, rhsTypeSpec, S2)
        RHS = S2
        if varTypeIsValueType(fieldType):
            assignValue=' = '+ RHS
        else:
        #TODO: make test case
            constructorExists=False  # TODO: Use some logic to know if there is a constructor, or create one.
            if (constructorExists):
                assignValue=' = new ' + fieldType +'('+ RHS + ')'
            else:
                assignValue= ' = '+ RHS   #' = new ' + fieldType +'();\n'+ indent + varName+' = '+RHS
    else: # If no value was given:
        #print "TYPE:", fieldType
        if fieldDef['paramList'] != None:       # call constructor
            # Code the constructor's arguments
        #TODO: make test case
            [CPL, paramTypeList] = codeParameterList(varName, fieldDef['paramList'], None, objsRefed, xlator)
            if len(paramTypeList)==1:
                if not isinstance(paramTypeList[0], dict):
                    print "\nPROBLEM: The return type of the parameter '", CPL, "' cannot be found and is needed. Try to define it.\n"
                    exit(1)

                theParam=paramTypeList[0]['fieldType']
                if not isinstance(theParam, basestring) and fieldType==theParam[0]:
                    assignValue = " = " + CPL   # Act like a copy constructor
                elif 'codeConverter' in paramTypeList[0]: #ktl 12.14.17
                    assignValue = " = " + CPL
                else: assignValue = " = new " + fieldType + CPL
            else: assignValue = " = new " + fieldType + CPL
        elif varTypeIsValueType(fieldType):
            if fieldType == 'long' or fieldType == 'int' or fieldType == 'float'or fieldType == 'double': assignValue=' = 0'
            elif fieldType == 'string':  assignValue=' = ""'
            elif fieldType == 'boolean': assignValue=' = false'
            elif fieldType == 'char':    assignValue=" = ' '"
            else: assignValue=''
        else:assignValue= " = new " + fieldType + "()"
    varDeclareStr= fieldType + " " + varName + assignValue
    #print"codeNewVarStr: ",varDeclareStr
    return(varDeclareStr)

def codeRangeSpec(traversalMode, ctrType, repName, S_low, S_hi, indent, xlator):
    if(traversalMode=='Forward' or traversalMode==None):
        S = indent + "for("+ctrType+" " + repName+'='+ S_low + "; " + repName + "!=" + S_hi +"; "+ xlator['codeIncrement'](repName) + "){\n"
    elif(traversalMode=='Backward'):
        S = indent + "for("+ctrType+" " + repName+'='+ S_hi + "-1; " + repName + ">=" + S_low +"; --"+ repName + "){\n"
    return (S)

def iterateRangeContainerStr(classes,localVarsAllocated, StartKey, EndKey, containerType, ContainerOwner,repName,repContainer,datastructID,keyFieldType,indent,xlator):
    willBeModifiedDuringTraversal=True   # TODO: Set this programatically leter.
    actionText = ""
    loopCounterName = ""
    containedType=containerType['fieldType']
    ctrlVarsTypeSpec = {'owner':containerType['owner'], 'fieldType':containedType}

    if datastructID=='TreeMap':
        valueFieldType = convertToJavaType(progSpec.fieldTypeKeyword(progSpec.getFieldType(containerType)), True)
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType}
        localVarsAllocated.append([repName+'_key', keyVarSpec])  # Tracking local vars for scope
        localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
        keyFieldType = convertToJavaType(keyFieldType, True)
        repContainerTypeSpec = (repContainer)
        actionText += (indent + 'for(Map.Entry<'+keyFieldType+','+valueFieldType+'> '+repName+'Entry : '+repContainer+'.subMap('+StartKey+', '+EndKey+').entrySet()){\n' +
                       indent + '    '+valueFieldType+' '+ repName + ' = ' + repName+'Entry.getValue();\n' +
                       indent + '    ' +keyFieldType +' '+ repName + '_key = ' + repName+'Entry.getKey();\n\n'  )
    elif datastructID=='list' or (datastructID=='deque' and not willBeModifiedDuringTraversal):
        pass;
    elif datastructID=='deque' and willBeModifiedDuringTraversal:
        pass;
    else:
        print "DSID range:",datastructID,containerType
        exit(2)
    return [actionText, loopCounterName]

def iterateContainerStr(classes,localVarsAllocated,containerType,repName,repContainer,datastructID,keyFieldType,ContainerOwner, isBackward, actionOrField, indent,xlator):
    actionText = ""
    loopCounterName=""
    owner=containerType['owner']
    containedType=containerType['fieldType']
    ctrlVarsTypeSpec = {'owner':containerType['owner'], 'fieldType':containedType}
    if containerType['fieldType'][0]=='DblLinkedList':
        ctrlVarsTypeSpec = {'owner':'our', 'fieldType':['infon']}
        loopCounterName=repName+'_key'
        keyVarSpec = {'owner':owner, 'fieldType':containedType}
        localVarsAllocated.append([loopCounterName, keyVarSpec])  # Tracking local vars for scope
        localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
        repItrName = repName+'Itr'
        actionText += (indent + "for( int " + repItrName+" = 0; " + repItrName + " !=" + repContainer+'.size()' +"; "+ repItrName + " +=1){\n"
                    + indent+"    "+"infon "+repName+" = "+repContainer+".at("+repItrName+").item;\n")
        return [actionText, loopCounterName]
    if datastructID=='TreeMap':
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':keyFieldType, 'codeConverter':(repName+'.getKey()')}
        localVarsAllocated.append([repName+'_key', keyVarSpec])  # Tracking local vars for scope
        ctrlVarsTypeSpec['codeConverter'] = (repName+'.getValue()')
        [containedTypeStr, innerType]=xlator['convertType'](classes, ctrlVarsTypeSpec, 'var', actionOrField, xlator)
        containedTypeStr = convertToJavaType(containedTypeStr, True)
        [indexTypeStr, innerType]=xlator['convertType'](classes, keyVarSpec, 'var', actionOrField, xlator)
        indexTypeStr = convertToJavaType(indexTypeStr, True)
        containedTypeStr = convertToJavaType(containedTypeStr, True)
        iteratorTypeStr="Map.Entry<"+indexTypeStr+', '+containedTypeStr+'>'
        repContainer+='.entrySet()'
        localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
        actionText += (indent + "for("+iteratorTypeStr+" " + repName+' :'+ repContainer+"){\n")
        return [actionText, loopCounterName]
    elif datastructID=='list':
        loopCounterName=repName+'_key'
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType}
        localVarsAllocated.append([loopCounterName, keyVarSpec])  # Tracking local vars for scope
        [iteratorTypeStr, innerType]=xlator['convertType'](classes, ctrlVarsTypeSpec, 'var', actionOrField, xlator)
    else:
        loopCounterName=repName+'_key'
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType}
        localVarsAllocated.append([loopCounterName, keyVarSpec])  # Tracking local vars for scope
        [iteratorTypeStr, innerType]=xlator['convertType'](classes, ctrlVarsTypeSpec, 'var', actionOrField, xlator)

    localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
    loopVarName=repName+"Idx";
    if(isBackward==False):
        actionText += (indent + "for(int "+loopVarName+"=0; " + loopVarName +' != ' + repContainer+'.size(); ' + loopVarName+' += 1){\n'
                    + indent +"    " + iteratorTypeStr+' '+repName+" = "+repContainer+".get("+loopVarName+");\n")
    else:
        actionText += (indent + "for(int "+loopVarName+'='+repContainer+'.size()-1; ' + loopVarName +' >=0; --' + loopVarName+' ){\n'+indent +indent + iteratorTypeStr+' '+repName+" = "+repContainer+".get("+loopVarName+");\n")
    return [actionText, loopCounterName]

def codeIncrement(varName):
    return "++" + varName

def codeDecrement(varName):
    return "--" + varName

def varTypeIsValueType(convertedType):
    if (convertedType=='int' or convertedType=='long' or convertedType=='byte' or convertedType=='boolean' or convertedType=='char'
       or convertedType=='float' or convertedType=='double' or convertedType=='short'):
        return True
    return False

def codeVarFieldRHS_Str(name, convertedType, fieldType, fieldOwner, paramList, objsRefed, isAllocated, xlator):
    fieldValueText=""
    if fieldOwner=='we':
        convertedType = convertedType.replace('static ', '', 1)
    if (not varTypeIsValueType(convertedType) and (fieldOwner=='me' or fieldOwner=='we' or fieldOwner=='const')):
        if fieldOwner =="const": convertedType = fieldType
        if paramList!=None:
            #TODO: make test case
            [CPL, paramTypeList] = codeParameterList(name, paramList, None, objsRefed, xlator)
            fieldValueText=" = new " + convertedType + CPL
        else:
            fieldValueText=" = new " + convertedType + "()"
    return fieldValueText

def codeConstField_Str(convertedType, fieldName, fieldValueText, className, indent, xlator ):
    defn = indent + convertedType + ' ' + fieldName + fieldValueText +';\n';
    decl = ''
    return [defn, decl]

def codeVarField_Str(convertedType, innerType, typeSpec, fieldName, fieldValueText, className, tags, indent):
    # TODO: make test case
    S=""
    fieldOwner=progSpec.getTypeSpecOwner(typeSpec)
    Platform = progSpec.fetchTagValue(tags, 'Platform')
    # TODO: make next line so it is not hard coded
    if(Platform == 'Android' and (convertedType == "TextView" or convertedType == "CanvasView" or convertedType == "FragmentTransaction" or convertedType == "FragmentManager" or convertedType == "Menu" or convertedType == "static GLOBAL" or convertedType == "Toolbar" or convertedType == "NestedScrollView" or convertedType == "SubMenu" or convertedType == "APP" or convertedType == "AssetManager" or convertedType == "ScrollView" or convertedType == "LinearLayout" or convertedType == "GUI"or convertedType == "CheckBox" or convertedType == "HorizontalScrollView"or convertedType == "GUI_ZStack"or convertedType == "widget"or convertedType == "GLOBAL")):
        #print "                                        ConvertedType: ", convertedType, "     FieldName: ", fieldName
        S += indent + "public " + convertedType + ' ' + fieldName +';\n';
    else:
        S += indent + "public " + convertedType + ' ' + fieldName + fieldValueText +';\n';
    return [S, '']

def codeConstructors(ClassName, constructorArgs, constructorInit, copyConstructorArgs, funcBody, callSuperConstructor, xlator):
    if callSuperConstructor:
        funcBody = '        super();\n' + funcBody
    withArgConstructor = ''
    if constructorArgs != '':
        withArgConstructor = "    public " + ClassName + "(" + constructorArgs+"){\n"+funcBody+ constructorInit+"    };\n"
    copyConstructor = "    public " + ClassName + "(final " + ClassName + " fromVar" +"){\n        "+ ClassName + " toVar = new "+ ClassName + "();\n" +copyConstructorArgs+"    };\n"
    noArgConstructor = "    public "  + ClassName + "(){\n"+funcBody+'\n    };\n'
    if (ClassName =="ourSubMenu" or ClassName =="GUI"or ClassName =="CanvasView"or ClassName =="APP"or ClassName =="GUI_ZStack"):
        return ""
    return withArgConstructor + copyConstructor + noArgConstructor

def codeConstructorInit(fieldName, count, defaultVal, xlator):
    return "        " + fieldName+"= arg_"+fieldName+";\n"

def codeConstructorArgText(argFieldName, count, argType, defaultVal, xlator):
    return argType + " arg_"+ argFieldName

def codeCopyConstructor(fieldName, convertedType, xlator):
    return "        toVar."+fieldName+" = fromVar."+fieldName+";\n"

def codeConstructorCall(className):
    return '        INIT();\n'

def codeSuperConstructorCall(parentClassName):
    return '        '+parentClassName+'();\n'

def codeFuncHeaderStr(className, fieldName, typeDefName, argListText, localArgsAllocated, inheritMode, indent):
#    if fieldName == 'init':
#        fieldName = fieldName+'_'+className
    if inheritMode=='pure-virtual':
        #print "Inherit Mode: ", className, fieldName
        typeDefName = 'abstract '+typeDefName
    structCode='\n'; funcDefCode=''; globalFuncs='';
    if(className=='GLOBAL'):
        if fieldName=='main':
            structCode += indent + "public static void " + fieldName +" (String[] args)";
            #localArgsAllocated.append(['args', {'owner':'me', 'fieldType':'String', 'arraySpec':None,'argList':None}])
        else:
            structCode += indent + "public " + typeDefName + ' ' + fieldName +"("+argListText+")"
    else:
        structCode += indent + "public " + typeDefName +' ' + fieldName +"("+argListText+")"
    if inheritMode=='pure-virtual':
        structCode += ";\n"
    elif inheritMode=='override': pass
    return [structCode, funcDefCode, globalFuncs]

def extraCodeForTopOfFuntion(argList):
    return ''

def codeSetBits(LHS_Left, LHS_FieldType, prefix, bitMask, RHS, rhsType):
    if (LHS_FieldType =='flag' ):
        item = LHS_Left+"flags"
        mask = prefix+bitMask
        if (RHS != 'true' and RHS !='false' and progSpec.fieldTypeKeyword(rhsType)!='bool' ):
            RHS += '!=0'
        val = '('+ RHS +')?'+mask+':0'
    elif (LHS_FieldType =='mode' ):
        item = LHS_Left+"flags"
        mask = prefix+bitMask+"Mask"
        if RHS == 'false': RHS = '0'
        if RHS == 'true': RHS = '1'
        val = RHS+"<<"+prefix+bitMask+"Offset"
    return "{"+item+" &= ~"+mask+"; "+item+" |= ("+val+");}\n"

def codeSwitchBreak(caseAction, indent, xlator):
    if not(len(caseAction) > 0 and caseAction[-1]['typeOfAction']=='funcCall' and caseAction[-1]['calledFunc'][0][0] == 'return'):
        return indent+"    break;\n"
    else:
        return ''

def applyTypecast(typeInCodeDog, itemToAlterType):
    return '('+itemToAlterType+')'
#######################################################
def includeDirective(libHdr):
    S = 'import '+libHdr+';\n'
    return S

def generateMainFunctionality(classes, tags):
    # TODO: Some deInitialize items should automatically run during abort().
    # TODO: System initCode should happen first in initialize, last in deinitialize.

    runCode = progSpec.fetchTagValue(tags, 'runCode')
    Platform = progSpec.fetchTagValue(tags, 'Platform')
    if Platform != 'Android':
        mainFuncCode="""
        me void: main( ) <- {
            initialize(String.join(" ", args))
            """ + runCode + """
            deinitialize()
            endFunc()
        }

    """
    if Platform == 'Android':
        mainFuncCode="""
        me void: runDogCode() <- {
            """ + runCode + """
        }
    """
    progSpec.addObject(classes[0], classes[1], 'GLOBAL', 'struct', 'SEQ')
    codeDogParser.AddToObjectFromText(classes[0], classes[1], progSpec.wrapFieldListInObjectDef('GLOBAL',  mainFuncCode ), 'Java start-up code')

def fetchXlators():
    xlators = {}

    xlators['LanguageName']          = "Java"
    xlators['BuildStrPrefix']        = "Javac "
    xlators['fileExtension']         = ".java"
    xlators['typeForCounterInt']     = "int"
    xlators['GlobalVarPrefix']       = "GLOBAL.static_Global."
    xlators['PtrConnector']          = "."                      # Name segment connector for pointers.
    xlators['ObjConnector']          = "."                      # Name segment connector for classes.
    xlators['NameSegConnector']      = "."
    xlators['NameSegFuncConnector']  = "."
    xlators['doesLangHaveGlobals']   = "False"
    xlators['funcBodyIndent']        = "    "
    xlators['funcsDefInClass']       = "True"
    xlators['MakeConstructors']      = "True"
    xlators['blockPrefix']           = ""
    xlators['usePrefixOnStatics']    = "False"
    xlators['codeExpr']                     = codeExpr
    xlators['adjustConditional']            = adjustConditional
    xlators['includeDirective']             = includeDirective
    xlators['codeMain']                     = codeMain
    xlators['produceTypeDefs']              = produceTypeDefs
    xlators['addSpecialCode']               = addSpecialCode
    xlators['convertType']                  = convertType
    xlators['applyTypecast']                = applyTypecast
    xlators['codeIteratorOperation']        = codeIteratorOperation
    xlators['xlateLangType']                = xlateLangType
    xlators['getContainerType']             = getContainerType
    xlators['recodeStringFunctions']        = recodeStringFunctions
    xlators['langStringFormatterCommand']   = langStringFormatterCommand
    xlators['LanguageSpecificDecorations']  = LanguageSpecificDecorations
    xlators['getCodeAllocStr']              = getCodeAllocStr
    xlators['getCodeAllocSetStr']           = getCodeAllocSetStr
    xlators['codeSpecialReference']         = codeSpecialReference
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
    xlators['extraCodeForTopOfFuntion']     = extraCodeForTopOfFuntion
    xlators['codeArrayIndex']               = codeArrayIndex
    xlators['codeSetBits']                  = codeSetBits
    xlators['generateMainFunctionality']    = generateMainFunctionality
    xlators['addGLOBALSpecialCode']         = addGLOBALSpecialCode
    xlators['codeArgText']                  = codeArgText
    xlators['codeConstructors']             = codeConstructors
    xlators['codeConstructorInit']          = codeConstructorInit
    xlators['codeIncrement']                = codeIncrement
    xlators['codeDecrement']                = codeDecrement
    xlators['codeConstructorArgText']       = codeConstructorArgText
    xlators['codeSwitchBreak']              = codeSwitchBreak
    xlators['codeCopyConstructor']          = codeCopyConstructor
    xlators['codeRangeSpec']                = codeRangeSpec
    xlators['codeConstField_Str']           = codeConstField_Str
    xlators['checkForTypeCastNeed']         = checkForTypeCastNeed
    xlators['codeConstructorCall']          = codeConstructorCall
    xlators['codeSuperConstructorCall']     = codeSuperConstructorCall

    return(xlators)
