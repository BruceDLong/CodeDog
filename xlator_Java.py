
"""
This file, along with Lib_Java.py specify to the CodeGenerater how to compile CodeDog source code into Java source code.



"""

import progSpec
import codeDogParser
from progSpec import cdlog, cdErr, logLvl
from CodeGenerator import codeItemRef, codeUserMesg, codeAllocater, codeParameterList, makeTagText, codeAction, getModeStateNames

###### Routines to track types of identifiers and to look up type based on identifier.
def getContainerType(typeSpec):
    containerSpec=typeSpec['arraySpec']
    if 'owner' in containerSpec: owner=containerSpec['owner']
    else: owner='me'
    idxType=''
    if 'indexType' in containerSpec:
        if 'IDXowner' in containerSpec:
            idxOwner=containerSpec['IDXowner']
            idxType=containerSpec['idxBaseType']
            idxType=applyOwner(idxOwner, idxType, 'IDX ERROR', containerSpec['indexType'], '')
        else: idxType=containerSpec['idxBaseType']
        #idxType=containerSpec['indexType']
    if idxType[0:4]=='uint': idxType = 'int'
    elif idxType=='string': idxType = 'String'

    datastructID = containerSpec['datastructID']
    if(datastructID=='list'): datastructID = "ArrayList"
    elif(datastructID=='map'): datastructID = "TreeMap"
    elif(datastructID=='multimap'): datastructID = "TreeMap"  # TODO: Implement true multmaps in java
    if (idxType == 'timeValue'):
        if(typeSpec['arraySpec']!= None):
            idxType = 'Long'
        else:
            idxType = 'long'
    return [datastructID, idxType, owner]

def convertToJavaType(fieldType):
    if(fieldType=='int32'):
        javaType='int'
    elif(fieldType=='uint32' or fieldType=='uint64' or fieldType=='uint'):
        javaType='int'  # these should be long but Java won't allow
    elif(fieldType=='int64'):
        javaType='int'
    elif(fieldType=='char' ):
        javaType='char'
    elif(fieldType=='bool' ):
        javaType='boolean'
    elif(fieldType=='string' ):
        javaType='String'
    else:
        javaType=progSpec.flattenObjectName(fieldType)
    #print "javaType: ", javaType
    return javaType

def convertType(classes, TypeSpec, varMode, xlator):
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
    return xlateLangType(TypeSpec,owner, fieldType, varMode, xlator)

def codeIteratorOperation(itrCommand):
    result = ''
    if itrCommand=='goNext':  result='%0.next()'
    elif itrCommand=='goPrev':result='%0.JAVA ERROR!'
    elif itrCommand=='key':   result='%0.getKey()'
    elif itrCommand=='val':   result='%0'
    return result

def applyOwner(owner, langType, innerType, idxType, varMode):
    if owner=='const':
        langType = "final "+langType
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

def xlateLangType(TypeSpec,owner, fieldType, varMode, xlator):
    # varMode is 'var' or 'arg'.
    if(isinstance(fieldType, basestring)):
        if(fieldType=='uint8' or fieldType=='uint16'): fieldType='uint32'
        elif(fieldType=='int8' or fieldType=='int16'): fieldType='int32'
        langType= convertToJavaType(fieldType)
    else: langType=progSpec.flattenObjectName(fieldType[0])
    langType = applyOwner(owner, langType, 'Itr-Error', 'ITR-ERROR', varMode)
    if langType=='TYPE ERROR': print langType, owner, fieldType;
    InnerLangType = langType

    if 'arraySpec' in TypeSpec:
        arraySpec=TypeSpec['arraySpec']
        if(arraySpec): # Make list, map, etc
            [containerType, idxType, owner]=getContainerType(TypeSpec)
            if 'owner' in TypeSpec['arraySpec']:
                containerOwner=TypeSpec['arraySpec']['owner']
            else: containerOwner='me'
            if idxType=='int': idxType = "Integer"
            if langType=='int': langType = "Integer"; InnerLangType = "Integer"
            if idxType=='long': idxType = "Long"
            if langType=='long': langType = "Long"
            if idxType=='timeValue': idxType = "Long" # this is hack and should be removed ASAP
            if containerType=='ArrayList':
                langType="ArrayList<"+langType+">"
            elif containerType=='TreeMap':
                langType="TreeMap<"+idxType+', '+langType+">"
            elif containerType=='multimap':
                langType="multimap<"+idxType+', '+langType+">"

            if varMode != 'alloc':
                langType=applyOwner(containerOwner, langType, InnerLangType, idxType, varMode)
    return [langType, InnerLangType]


def recodeStringFunctions(name, typeSpec):
    if name == "size": name = "length"
    elif name == "subStr":
        typeSpec['codeConverter']='%0.substring(%1, %2)'
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
    if LHS_KeyType == 'bool' and RHS_KeyType=='int': return '(' + codeStr + ' != 0)'
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
def getContainerTypeInfo(classes, containerType, name, idxType, typeSpecOut, paramList, xlator):
    convertedIdxType = ""
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
        elif name=='last'     : name='rbegin()->second'; paramList=None;
        elif name=='popFirst' : name='pop_front'
        elif name=='popLast'  : name='pop_back'
        elif name=='pushFirst': name='push_front'
        elif name=='pushLast' : name='add'
        else: print "Unknown ArrayList command:", name; exit(2);
    elif containerType=='TreeMap':
        convertedIdxType=idxType
        [convertedItmType, innerType]=xlator['convertType'](classes, typeSpecOut, 'var', xlator)
        if name=='at' or name=='erase': pass
        elif name=='containsKey'   : name="containsKey"; typeSpecOut={'owner':'me', 'fieldType': 'bool'}
        elif name=='size'     : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
        elif name=='insert'   : name='put';
        elif name=='clear'    : typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif name=='find'     : typeSpecOut['owner']='itr'; typeSpecOut['fieldType']=convertedItmType;  typeSpecOut['codeConverter']='tailMap(%1).entrySet().iterator()';
        elif name=='get'      : name='get';      typeSpecOut['owner']='me';  typeSpecOut['fieldType']=convertedItmType;
        elif name=='front'    : name='begin()';  typeSpecOut['owner']='itr'; paramList=None;
        elif name=='back'     : name='rbegin()'; typeSpecOut['owner']='itr'; paramList=None;
        elif name=='end'      : typeSpecOut['codeConverter']='%Gnull';    typeSpecOut['owner']='itr'; paramList=None;
        elif name=='rend'     : typeSpecOut['codeConverter']='%Gnull';    typeSpecOut['owner']='itr'; paramList=None;
        elif name=='first'    : name='get(0)';   paramList=None;
        elif name=='last'     : name='rbegin()->second'; paramList=None;
        elif name=='popFirst' : name='pop_front'
        elif name=='popLast'  : name='pop_back'
        else: print "Unknown map command:", name; exit(2);
    elif containerType=='multimap':
        convertedIdxType=idxType
        [convertedItmType, innerType]=xlator['convertType'](classes, typeSpecOut, 'var', xlator)
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

def codeFactor(item, objsRefed, xlator):
    ####  ( value | ('(' + expr + ')') | ('!' + expr) | ('-' + expr) | varFuncRef)
    #print '                  factor: ', item
    S=''
    retType='noType'
    item0 = item[0]
    #print "ITEM0=", item0, ">>>>>", item
    if (isinstance(item0, basestring)):
        if item0=='(':
            [S2, retType] = codeExpr(item[1], objsRefed, xlator)
            S+='(' + S2 +')'
        elif item0=='!':
            [S2, retType] = codeExpr(item[1], objsRefed, xlator)
            if(progSpec.typeIsPointer(retType)):
                S= '('+S2+' == null)'
                retType='bool'
            else: S+='!' + S2
        elif item0=='-':
            [S2, retType] = codeExpr(item[1], objsRefed, xlator)
            S+='-' + S2
        elif item0=='[':
            count=0
            tmp="(Arrays.asList("
            for expr in item[1:-1]:
                count+=1
                [S2, retType] = codeExpr(expr, objsRefed, xlator)
                if count>1: tmp+=", "
                tmp+=S2
            tmp+="))"
            S+="new "+"ArrayList<>"+tmp   # ToDo: make this handle things other than long.

        else:
            retType='string'
            if(item0[0]=="'"): S+=codeUserMesg(item0[1:-1], xlator)
            elif (item0[0]=='"'): S+='"'+item0[1:-1] +'"'
            else: S+=item0;
    else:
        if isinstance(item0[0], basestring):
            S+=item0[0]
        else:
            [codeStr, retType, prntType, AltIDXFormat]=codeItemRef(item0, 'RVAL', objsRefed, xlator)
            if(codeStr=="NULL"): codeStr="null"
            S+=codeStr                                # Code variable reference or function call
    return [S, retType]

def codeTerm(item, objsRefed, xlator):
    #print '               term item:', item
    [S, retType]=codeFactor(item[0], objsRefed, xlator)
    if (not(isinstance(item, basestring))) and (len(item) > 1) and len(item[1])>0:
        for i in item[1]:
            #print '               term:', i
            if   (i[0] == '*'): S+=' * '
            elif (i[0] == '/'): S+=' / '
            elif (i[0] == '%'): S+=' % '
            else: print "ERROR: One of '*', '/' or '%' expected in code generator."; exit(2)
            [S2, retType2] = codeFactor(i[1], objsRefed, xlator)
            S+=S2
    return [S, retType]

def codePlus(item, objsRefed, xlator):
    #print '            plus item:', item
    [S, retType]=codeTerm(item[0], objsRefed, xlator)
    if len(item) > 1 and len(item[1])>0:
        for  i in item[1]:
            #print '            plus ', i
            if   (i[0] == '+'): S+=' + '
            elif (i[0] == '-'): S+=' - '
            else: print "ERROR: '+' or '-' expected in code generator."; exit(2)
            [S2, retType2] = codeTerm(i[1], objsRefed, xlator)
            S+=S2
    return [S, retType]

def codeComparison(item, objsRefed, xlator):
    #print '         Comp item', item
    [S, retType]=codePlus(item[0], objsRefed, xlator)
    if len(item) > 1 and len(item[1])>0:
        for  i in item[1]:
            #print '         comp ', i
            if   (i[0] == '<'): S+=' < '
            elif (i[0] == '>'): S+=' > '
            elif (i[0] == '<='): S+=' <= '
            elif (i[0] == '>='): S+=' >= '
            else: print "ERROR: One of <, >, <= or >= expected in code generator."; exit(2)
            [S2, retType] = codePlus(i[1], objsRefed, xlator)
            S+=S2
            retType='bool'
    return [S, retType]

def codeIsEQ(item, objsRefed, xlator):
    #print '      IsEq item:', item
    [S, retType]=codeComparison(item[0], objsRefed, xlator)
    if len(item) > 1 and len(item[1])>0:
        if len(item[1])>1: print "Error: Chained == or !=.\n"; exit(1);
        if (isinstance(retType, int)): cdlog(logLvl(), "Invalid item in ==: {}".format(item[0]))
        leftOwner=owner=progSpec.getTypeSpecOwner(retType)
        for i in item[1]:
            #print '      IsEq ', i
            if   (i[0] == '=='): op=' == '
            elif (i[0] == '!='): op=' != '
            elif (i[0] == '==='): op=' == '
            else: print "ERROR: '==' or '!=' or '===' expected."; exit(2)
            [S2, retType] = codeComparison(i[1], objsRefed, xlator)
            S+= op+S2
            retType='bool'
    return [S, retType]

def codeLogAnd(item, objsRefed, xlator):
    #print '   And item:', item
    [S, retType] = codeIsEQ(item[0], objsRefed, xlator)
    if len(item) > 1 and len(item[1])>0:
        for i in item[1]:
            #print '   AND ', i
            if (i[0] == 'and'):
                [S2, retType] = codeIsEQ(i[1], objsRefed, xlator)
                S = checkForTypeCastNeed('bool', retType, S)
                S2= checkForTypeCastNeed('bool', retType, S2)
                S+=' && ' + S2
            else: print "ERROR: 'and' expected in code generator."; exit(2)
            retType='bool'
    return [S, retType]

def codeExpr(item, objsRefed, xlator):
    #print 'Or item:', item
    [S, retType]=codeLogAnd(item[0], objsRefed, xlator)
    if not isinstance(item, basestring) and len(item) > 1 and len(item[1])>0:
        for i in item[1]:
            #print 'OR ', i
            if (i[0] == 'or'):
                [S2, retType] = codeLogAnd(i[1], objsRefed, xlator)
                S = checkForTypeCastNeed('bool', retType, S)
                S2= checkForTypeCastNeed('bool', retType, S2)
                S+=' || ' + S2
            else: print "ERROR: 'or' expected in code generator."; exit(2)
            retType='bool'
    #print "S:",S
    return [S, retType]

def adjustConditional(S2, conditionType):
    #print "CONDITIONTYPE:", conditionType, '[', S2, ']'
    if not isinstance(conditionType, basestring):
        if conditionType['owner']=='our' or conditionType['owner']=='their' or conditionType['owner']=='my' or progSpec.isStruct(conditionType['fieldType']):
            S2+=" != null"
        elif conditionType['owner']=='me' and (conditionType['fieldType']=='flag' or progSpec.typeIsInteger(conditionType['fieldType'])):
            S2+=" != 0"
        conditionType='bool'
    return [S2, conditionType]

def codeSpecialReference(segSpec, objsRefed, xlator):
    S=''
    retType='void'   # default to void
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
                [S2, argType]=xlator['codeExpr'](P[0], objsRefed, xlator)
                if ("<MODENAME>" in S2):
                    S2=S2.replace("<MODENAME>", ".get(")
                    S2=S2.replace("<MODENAMEend>", ")")
                S+=S2
            S+=")"
        elif(funcName=='AllocateOrClear'):
            [varName,  varTypeSpec]=xlator['codeExpr'](paramList[0][0], objsRefed, xlator)
            S+='if('+varName+' != null){'+varName+'.clear();} else {'+varName+" = "+codeAllocater(varTypeSpec, xlator)+"();}"
        elif(funcName=='Allocate'):
            [varName,  varTypeSpec]=xlator['codeExpr'](paramList[0][0], objsRefed, xlator)
            S+=varName+" = "+codeAllocater(varTypeSpec, xlator)+'('
            count=0   # TODO: As needed, make this call CodeParameterList() with modelParams of the constructor.
            for P in paramList[1:]:
                if(count>0): S+=', '
                [S2, argType]=xlator['codeExpr'](P[0], objsRefed, xlator)
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
                [S2, argType]=xlator['codeExpr'](P[0][0], objsRefed, xlator)
                S2=derefPtr(S2, argType)
                S+='String.valueOf('+S2+')'
                retType='string'
    else: # Not parameters, i.e., not a function
        if(funcName=='self'):
            S+='this'

    return [S, retOwner, retType]

def codeArrayIndex(idx, containerType, LorR_Val, previousSegName):
    if LorR_Val=='RVAL':
        #Next line may be cause of bug with printing modes.  remove 'not'?
        if (previousSegName in getModeStateNames()):
            S= '<MODENAME>' + idx + '<MODENAMEend>'
        elif (containerType== 'ArrayList' or containerType== 'TreeMap' or containerType== 'Map' or containerType== 'multimap'):
            S= '.get(' + idx + ')'
        elif (containerType== 'string'):
            S= '.charAt(' + idx + ')'    # '.substring(' + idx + ', '+ idx + '+1' +')'
        else:
            S= '[' + idx +']'
    else: S= '[' + idx +']'
    return S


def checkIfSpecialAssignmentFormIsNeeded(AltIDXFormat, RHS, rhsType):
    # Check for string A[x] = B;  If so, render A.put(B,x)
    [containerType, idxType, owner]=getContainerType(AltIDXFormat[1])
    if containerType == "ArrayList":
        S=AltIDXFormat[0] + '.add(' + AltIDXFormat[2] + ', ' + RHS + ');\n'
    elif containerType == "TreeMap":
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
    specialCode ='const string: filename <- "' + filename + '"\n'

    GLOBAL_CODE="""
struct GLOBAL{
    %s
}
    """ % (specialCode)

    codeDogParser.AddToObjectFromText(classes[0], classes[1], GLOBAL_CODE, 'Java special code' )

def codeNewVarStr (classes, typeSpec, varName, fieldDef, indent, objsRefed, xlator):
    [fieldType, fieldAttrs] = xlator['convertType'](classes, typeSpec, 'var', xlator)
    if isinstance(typeSpec['fieldType'], basestring) and typeSpec['arraySpec'] == None:
        if(fieldDef['value']):
            [S2, rhsType]=codeExpr(fieldDef['value'][0], objsRefed, xlator)
            RHS = S2
            assignValue=' = '+ RHS
            #TODO: make test case
        else: assignValue=''
    elif(fieldDef['value']):
        [S2, rhsType]=codeExpr(fieldDef['value'][0], objsRefed, xlator)
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
            assignValue=''
        else:assignValue= " = new " + fieldType + "()"
    varDeclareStr= fieldType + " " + varName + assignValue
    return(varDeclareStr)

def codeRangeSpec(traversalMode, ctrType, repName, S_low, S_hi, indent, xlator):
    if(traversalMode=='Forward' or traversalMode==None):
        S = indent + "for("+ctrType+" " + repName+'='+ S_low + "; " + repName + "!=" + S_hi +"; "+ xlator['codeIncrement'](repName) + "){\n"
    elif(traversalMode=='Backward'):
        S = indent + "for("+ctrType+" " + repName+'='+ S_hi + "-1; " + repName + ">=" + S_low +"; --"+ repName + "){\n"
    return (S)

def iterateRangeContainerStr(classes,localVarsAllocated, StartKey, EndKey, containerType,repName,repContainer,datastructID,keyFieldType,indent,xlator):
    willBeModifiedDuringTraversal=True   # TODO: Set this programatically leter.
    actionText = ""
    loopCounterName = ""
    containedType=containerType['fieldType']
    ctrlVarsTypeSpec = {'owner':containerType['owner'], 'fieldType':containedType}

    if datastructID=='TreeMap':
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType}
        localVarsAllocated.append([repName+'_key', keyVarSpec])  # Tracking local vars for scope

        localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
        actionText += (indent + 'for(Map.Entry<'+keyFieldType+',Integer> '+repName+'Entry : '+repContainer+'.subMap('+StartKey+', '+EndKey+').entrySet()){\n' +
                       indent + indent +'int '+ repName + ' = ' + repName+'Entry.getValue();\n' +
                       indent + indent +keyFieldType +' '+ repName + '_key = ' + repName+'Entry.getKey();\n\n'  )

    elif datastructID=='list' or (datastructID=='deque' and not willBeModifiedDuringTraversal):
        pass;
    elif datastructID=='deque' and willBeModifiedDuringTraversal:
        pass;
    else:
        print "DSID range:",datastructID,containerType
        exit(2)

    return [actionText, loopCounterName]

def iterateContainerStr(classes,localVarsAllocated,containerType,repName,repContainer,datastructID,keyFieldType,ContainerOwner, isBackward, indent,xlator):
    actionText = ""
    loopCounterName=""
    containedType=containerType['fieldType']
    ctrlVarsTypeSpec = {'owner':containerType['owner'], 'fieldType':containedType}
    if datastructID=='TreeMap':
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':keyFieldType, 'codeConverter':(repName+'.getKey()')}
        localVarsAllocated.append([repName+'_key', keyVarSpec])  # Tracking local vars for scope
        ctrlVarsTypeSpec['codeConverter'] = (repName+'.getValue()')
        [containedTypeStr, innerType]=xlator['convertType'](classes, ctrlVarsTypeSpec, 'var', xlator)
        [indexTypeStr, innerType]=xlator['convertType'](classes, keyVarSpec, 'var', xlator)
        if indexTypeStr=='int': indexTypeStr = "Integer"
        elif indexTypeStr=='long': indexTypeStr = "Long"
        iteratorTypeStr="Map.Entry<"+indexTypeStr+", "+containedTypeStr+">"
        repContainer+='.entrySet()'

        localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
        actionText += (indent + "for("+iteratorTypeStr+" " + repName+' :'+ repContainer+"){\n")
        return [actionText, loopCounterName]
    elif datastructID=='list':
        loopCounterName=repName+'_key'
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType}
        localVarsAllocated.append([loopCounterName, keyVarSpec])  # Tracking local vars for scope
        [iteratorTypeStr, innerType]=xlator['convertType'](classes, ctrlVarsTypeSpec, 'var', xlator)
    else:
        loopCounterName=repName+'_key'
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType}
        localVarsAllocated.append([loopCounterName, keyVarSpec])  # Tracking local vars for scope
        [iteratorTypeStr, innerType]=xlator['convertType'](classes, ctrlVarsTypeSpec, 'var', xlator)

    localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
    loopVarName=repName+"Idx";
    if(isBackward==False):
        actionText += (indent + "for(int "+loopVarName+"=0; " + loopVarName +' != ' + repContainer+'.size(); ' + loopVarName+' += 1){\n'+indent +indent + iteratorTypeStr+' '+repName+" = "+repContainer+".get("+loopVarName+");\n")
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

def codeVarFieldRHS_Str(name, convertedType, fieldOwner, paramList, objsRefed, xlator):
    fieldValueText=""
    if fieldOwner=='we':
        convertedType = convertedType.replace('static ', '', 1)
    if (not varTypeIsValueType(convertedType) and (fieldOwner=='me' or fieldOwner=='we')):
        if paramList!=None:
            #TODO: make test case
            [CPL, paramTypeList] = codeParameterList(name, paramList, None, objsRefed, xlator)
            fieldValueText=" = new " + convertedType + CPL
        else:
            fieldValueText=" = new " + convertedType + "()"
    return fieldValueText

def codeConstField_Str(convertedType, fieldName, fieldValueText, indent, xlator ):
    return indent + convertedType + ' ' + fieldName + fieldValueText +';\n';

def codeVarField_Str(convertedType, innerType, typeSpec, fieldName, fieldValueText, className, tags, indent):
    # TODO: make test case
    S=""
    fieldOwner=progSpec.getTypeSpecOwner(typeSpec)
    Platform = progSpec.fetchTagValue(tags, 'Platform')
    # TODO: make next line so it is not hard coded
    if(Platform == 'Android' and (convertedType == "CanvasView" or convertedType == "FragmentTransaction" or convertedType == "FragmentManager" or convertedType == "Menu" or convertedType == "static GLOBAL" or convertedType == "Toolbar" or convertedType == "NestedScrollView" or convertedType == "SubMenu" or convertedType == "APP" or convertedType == "AssetManager" or convertedType == "ScrollView" or convertedType == "LinearLayout" or convertedType == "GUI" or convertedType == "HorizontalScrollView"or convertedType == "widget"or convertedType == "GLOBAL")):
        #print "                                        ConvertedType: ", convertedType, "     FieldName: ", fieldName
        S += indent + "public " + convertedType + ' ' + fieldName +';\n';
    else:
        S += indent + "public " + convertedType + ' ' + fieldName + fieldValueText +';\n';
    return [S, '']

def codeConstructorHeader(ClassName, constructorArgs, constructorInit, copyConstructorArgs, xlator):
    withArgConstructor = "    public " + ClassName + "(" + constructorArgs+"){\n"+constructorInit+"    };\n"
    copyConstructor = "    public " + ClassName + "(" + ClassName + " fromVar" +"){\n        "+ ClassName + " toVar = new "+ ClassName + "();\n" +copyConstructorArgs+"    };\n"
    noArgConstructor = "    public "  + ClassName + "(){"+"};\n"
    if (ClassName =="ourSubMenu" or ClassName =="GUI"or ClassName =="CanvasView"or ClassName =="APP"):
        return ""
    return withArgConstructor + copyConstructor + noArgConstructor

def codeConstructorInit(fieldName, count, defaultVal, xlator):
    return "        " + fieldName+"= arg_"+fieldName+";\n"

def codeConstructorArgText(argFieldName, count, argType, defaultVal, xlator):
    return argType + " arg_"+ argFieldName

def codeCopyConstructor(fieldName, convertedType, xlator):
    return "        toVar."+fieldName+" = fromVar."+fieldName+";\n"


def codeFuncHeaderStr(className, fieldName, typeDefName, argListText, localArgsAllocated, inheritMode, indent):
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
        if (RHS != 'true' and RHS !='false'):
            RHS += '!=0'
        val = '('+ RHS +')?'+mask+':0'
    elif (LHS_FieldType =='mode' ):
        item = LHS_Left+"flags"
        mask = prefix+bitMask+"Mask"
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
    xlators['codeConstructorHeader']        = codeConstructorHeader
    xlators['codeConstructorInit']          = codeConstructorInit
    xlators['codeIncrement']                = codeIncrement
    xlators['codeDecrement']                = codeDecrement
    xlators['codeConstructorArgText']       = codeConstructorArgText
    xlators['codeSwitchBreak']              = codeSwitchBreak
    xlators['codeCopyConstructor']          = codeCopyConstructor
    xlators['codeRangeSpec']                = codeRangeSpec
    xlators['codeConstField_Str']           = codeConstField_Str
    xlators['checkForTypeCastNeed']         = checkForTypeCastNeed

    return(xlators)
