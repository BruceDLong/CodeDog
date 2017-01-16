
"""
This file, along with Lib_Java.py specify to the CodeGenerater how to compile CodeDog source code into Java source code.



"""

import progSpec
import codeDogParser
import Lib_Android
from CodeGenerator import codeItemRef, codeUserMesg, codeAllocater, codeParameterList

###### Routines to track types of identifiers and to look up type based on identifier.
def getContainerType(typeSpec):
    containerSpec=typeSpec['arraySpec']
    idxType=''
    if 'indexType' in containerSpec:
        idxType=containerSpec['indexType']
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
    return [datastructID, idxType]

def convertToJavaType(fieldType):
    if(fieldType=='int32'):
        javaType='int'
    elif(fieldType=='uint32' or fieldType=='uint64'):
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

def convertType(objects, TypeSpec, varMode, xlator):
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
    return xlateLangType(TypeSpec,owner, fieldType, varMode, xlator)

def xlateLangType(TypeSpec,owner, fieldType, varMode, xlator):
    # varMode is 'var' or 'arg'.
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
            if idxType=='int': idxType = "Integer"
            if langType=='int': langType = "Integer"
            if idxType=='long': idxType = "Long"
            if langType=='long': langType = "Long"
            if idxType=='timeValue': idxType = "Long" # this is hack and should be removed ASAP
            if containerType=='ArrayList':
                langType="ArrayList<"+langType+">"
            elif containerType=='TreeMap':
                langType="TreeMap<"+idxType+', '+langType+">"
            elif containerType=='multimap':
                langType="multimap<"+idxType+', '+langType+">"
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
    S= "public static final int "+fieldName + " = " + fieldValue+ ";\n"
    return(S)

def getEnumStr(fieldName, enumList):
    S=''
    count=0
    for enumName in enumList:
        S += getConstIntFieldStr(enumName, str(count))
        count=count+1
    S += "\n"
    return(S)

######################################################   E X P R E S S I O N   C O D I N G
def getContainerTypeInfo(containerType, name, idxType, typeSpecOut, paramList, objectsRef, xlator):
    convertedIdxType = ""
    if containerType=='ArrayList':
        if name=='at' or name=='insert' or name=='erase': pass
        elif name=='size' : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
        elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif name=='front'    : name='begin()';  typeSpecOut['owner']='itr'; paramList=None;
        elif name=='back'     : name='rbegin()'; typeSpecOut['owner']='itr'; paramList=None;
        elif name=='end'      : name='end()';    typeSpecOut['owner']='itr'; paramList=None;
        elif name=='rend'     : name='rend()';   typeSpecOut['owner']='itr'; paramList=None;
        elif name=='first'    : name='get(0)';   paramList=None;
        elif name=='last'     : name='rbegin()->second'; paramList=None;
        elif name=='popFirst' : name='pop_front'
        elif name=='popLast'  : name='pop_back'
        elif name=='pushFirst': name='push_front'
        elif name=='pushLast' : name='add'
        else: print "Unknown ArrayList command:", name; exit(2);
    elif containerType=='TreeMap':
        convertedIdxType=idxType
        convertedItmType=xlator['convertType'](objectsRef, typeSpecOut, 'var', xlator)
        if name=='at' or name=='erase': pass
        elif name=='size'     : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
        elif name=='insert'   : name='put';
        elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif name=='find'     : name='find';     typeSpecOut['owner']='itr';
        elif name=='front'    : name='begin()';  typeSpecOut['owner']='itr'; paramList=None;
        elif name=='back'     : name='rbegin()'; typeSpecOut['owner']='itr'; paramList=None;
        elif name=='end'      : name='end()';    typeSpecOut['owner']='itr'; paramList=None;
        elif name=='rend'     : name='rend()';   typeSpecOut['owner']='itr'; paramList=None;
        elif name=='first'    : name='get(0)';   paramList=None;
        elif name=='last'     : name='rbegin()->second'; paramList=None;
        elif name=='popFirst' : name='pop_front'
        elif name=='popLast'  : name='pop_back'
        else: print "Unknown map command:", name; exit(2);
    elif containerType=='multimap':
        convertedIdxType=idxType
        convertedItmType=xlator['convertType'](objectsRef, typeSpecOut, 'var', xlator)
        if name=='at' or name=='erase': pass
        elif name=='size'     : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
        elif name=='insert'   : name='put'; #typeSpecOut['codeConverter']='put(pair<'+convertedIdxType+', '+convertedItmType+'>(%1, %2))'
        elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif name=='front'    : name='begin()';  typeSpecOut['owner']='itr'; paramList=None;
        elif name=='back'     : name='rbegin()'; typeSpecOut['owner']='itr'; paramList=None;
        elif name=='end'      : name='end()';    typeSpecOut['owner']='itr'; paramList=None;
        elif name=='rend'     : name='rend()';   typeSpecOut['owner']='itr'; paramList=None;
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
            count=0
            tmp="(Arrays.asList("
            for expr in item[1:-1]:
                count+=1
                [S2, retType] = codeExpr(expr, xlator)
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
            [codeStr, retType, prntType, AltIDXFormat]=codeItemRef(item0, 'RVAL', xlator)
            if(codeStr=="NULL"): codeStr="null"
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

def adjustIfConditional(S2, conditionType):
    #print "CONDITIONTYPE:", conditionType, '[', S2, ']'
    if not isinstance(conditionType, basestring):
        if conditionType['owner']=='our' or conditionType['owner']=='their' or conditionType['owner']=='my':
            S2+=" != null"
        elif conditionType['owner']=='me' and conditionType['fieldType']=='flag':
            S2+=" != 0"
        conditionType='bool'
    return [S2, conditionType]

def codeSpecialFunc(segSpec, xlator):
    S=''
    funcName=segSpec[0]
    if(funcName=='print'):
        S+='System.out.print('
        if(len(segSpec)>2):
            paramList=segSpec[2]
            count=0
            for P in paramList:
                if(count!=0): S+=" + "
                count+=1
                [S2, argType]=xlator['codeExpr'](P[0], xlator)
                S+=S2
        S+=")"
    elif(funcName=='AllocateOrClear'):
        if(len(segSpec)>2):
            #print "ALLOCATE-OR-CLEAR():", segSpec[2][0]
            paramList=segSpec[2]
            [varName,  varTypeSpec]=xlator['codeExpr'](paramList[0][0], xlator)
            S+='if('+varName+' != null){'+varName+'.clear();} else {'+varName+" = "+codeAllocater(varTypeSpec, xlator)+"();}"
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

def codeArrayIndex(idx, containerType, LorR_Val):
    if LorR_Val=='RVAL':
        if (containerType== 'ArrayList' or containerType== 'TreeMap' or containerType== 'Map' or containerType== 'multimap'):
            S= '.get(' + idx + ')'
        elif (containerType== 'string'):
            S= '.charAt(' + idx + ')'    # '.substring(' + idx + ', '+ idx + '+1' +')'
        else:
            S= '[' + idx +']'
    else: S= '[' + idx +']'
    return S


def checkIfSpecialAssignmentFormIsNeeded(AltIDXFormat, RHS, rhsType):
    # Check for string A[x] = B;  If so, render A.put(B,x)
    S=AltIDXFormat[0] + '.put(' + AltIDXFormat[1] + ', ' + RHS + ');'
    return S

################################################
def codeMain(objects, tags, xlator):
    return ["", ""]

def codeStructText(classAttrs, parentClass, structName, structCode):
    if parentClass != "":
        if parentClass[0]=="!": parentClass=' implements '+parentClass[1:]+' '
        else: parentClass=' extends '+parentClass+' '
    S= "\n"+classAttrs +"class "+structName+parentClass+"{\n" + structCode + '};\n'
    return([S,""])


def produceTypeDefs(typeDefMap, xlator):
    return ''

def addSpecialCode():
    S='\n\n//////////// Java specific code:\n'
    S+="""
    class funcs{
        public static String readFileAsString(String filePath){
            try {
                DataInputStream dis = new DataInputStream(new FileInputStream(filePath));
                try {
                    long len = new File(filePath).length();
                    if (len > Integer.MAX_VALUE) return "";
                    byte[] bytes = new byte[(int) len];
                    dis.readFully(bytes);
                    return new String(bytes, "UTF-8");
                } finally {
                    dis.close();
                }
            } catch (IOException ioe) {
                System.out.println("Cannot read file " + ioe.getMessage());
                return "";
            }
        }
    }
    """
    return S

def codeNewVarStr (typeSpec, varName, fieldDef, fieldType, xlator):
    if isinstance(typeSpec['fieldType'], basestring):
        if(fieldDef['value']):
            [S2, rhsType]=codeExpr(fieldDef['value'][0], xlator)
            RHS = S2
            assignValue=' = '+ RHS
        else: assignValue=''
    elif(fieldDef['value']):
        [S2, rhsType]=codeExpr(fieldDef['value'][0], xlator)
        RHS = S2
        if varTypeIsJavaValueType(fieldType):
            assignValue=' = '+ RHS
        else:
            constructorExists=False  # TODO: Use some logic to know if there is a constructor, or create one.
            if (constructorExists):
                assignValue=' = new ' + fieldType +'('+ RHS + ')'
            else:
                assignValue=' = new ' + fieldType +'();  ' + varName+' = '+RHS
    else: # If no value was given:
        #print "TYPE:", fieldType
        if fieldDef['paramList'] != None:
            # Code the constructor's arguments
            [CPL, paramTypeList] = codeParameterList(fieldDef['paramList'], None, xlator)
            if len(paramTypeList)==1:
                if not isinstance(paramTypeList[0], dict):
                    print "\nPROBLEM: The return type of the parameter '", CPL, "' cannot be found and is needed. Try to define it.\n"
                    exit(1)

                theParam=paramTypeList[0]['fieldType']
                if not isinstance(theParam, basestring) and fieldType==theParam[0]:
                    assignValue = " = " + CPL   # Act like a copy constructor
                else: assignValue = " = new " + fieldType + CPL
            else: assignValue = " = new " + fieldType + CPL
        elif varTypeIsJavaValueType(fieldType):
            assignValue=''
        else:assignValue= " = new " + fieldType + "()"
    varDeclareStr= fieldType + " " + varName + assignValue
    return(varDeclareStr)

def iterateRangeContainerStr(objectsRef,localVarsAllocated, StartKey, EndKey, containerType,repName,repContainer,datastructID,keyFieldType,indent,xlator):
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

def iterateContainerStr(objectsRef,localVarsAllocated,containerType,repName,repContainer,datastructID,keyFieldType,indent,xlator):
    actionText = ""
    loopCounterName=""
    containedType=containerType['fieldType']
    ctrlVarsTypeSpec = {'owner':containerType['owner'], 'fieldType':containedType}
    if datastructID=='TreeMap':
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':keyFieldType, 'codeConverter':(repName+'.getKey()')}
        localVarsAllocated.append([repName+'_key', keyVarSpec])  # Tracking local vars for scope
        ctrlVarsTypeSpec['codeConverter'] = (repName+'.getValue()')
        containedTypeStr=xlator['convertType'](objectsRef, ctrlVarsTypeSpec, 'var', xlator)
        indexTypeStr=xlator['convertType'](objectsRef, keyVarSpec, 'var', xlator)
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
        iteratorTypeStr=xlator['convertType'](objectsRef, ctrlVarsTypeSpec, 'var', xlator)
    else:
        loopCounterName=repName+'_key'
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType}
        localVarsAllocated.append([loopCounterName, keyVarSpec])  # Tracking local vars for scope
        iteratorTypeStr=xlator['convertType'](objectsRef, ctrlVarsTypeSpec, 'var', xlator)

    localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
    loopVarName=repName+"Idx";
    actionText += (indent + "for(int "+loopVarName+"=0; " + loopVarName +' != ' + repContainer+'.size(); ' + loopVarName+' += 1){\n'+indent +indent + iteratorTypeStr+' '+repName+" = "+repContainer+".get("+loopVarName+");\n")
    return [actionText, loopCounterName]

def varTypeIsJavaValueType(convertedType):
    if (convertedType=='int' or convertedType=='long' or convertedType=='byte' or convertedType=='boolean' or convertedType=='char'
       or convertedType=='float' or convertedType=='double' or convertedType=='short'):
        return True
    return False

def codeVarFieldRHS_Str(fieldValue, convertedType, fieldOwner, paramList, xlator):
    fieldValueText=""
    if(fieldValue == None):
        if (not varTypeIsJavaValueType(convertedType) and fieldOwner=='me'):
            if paramList!=None:
                [CPL, paramTypeList] = codeParameterList(paramList, None, xlator)
                fieldValueText=" = new " + convertedType + CPL
            else:
                fieldValueText=" = new " + convertedType + "()"
    return fieldValueText

def codeVarField_Str(convertedType, fieldName, fieldValueText, objectName, tags, indent):
    S=""
    Platform = progSpec.fetchTagValue(tags, 'Platform')
    if (fieldName == "static_Global" or fieldName == "static_gui_tk"):  # TODO: make static_Global so it is not hard coded
        S += indent + "public static " + convertedType + ' ' + fieldName + fieldValueText +';\n';
    elif(objectName == 'GLOBAL' and Platform == 'Android'):
        print "objectName: fieldValueText: ", objectName, fieldValueText
        S += indent + "public " + convertedType + ' ' + fieldName +';\n';
    else:
        S += indent + "public " + convertedType + ' ' + fieldName + fieldValueText +';\n';
    return S

def codeFuncHeaderStr(objectName, fieldName, typeDefName, argListText, localArgsAllocated, indent):
    structCode=''; funcDefCode=''; globalFuncs='';
    if(objectName=='GLOBAL'):
        if fieldName=='main':
            structCode += indent + "public static void " + fieldName +" (String[] args)";
            #localArgsAllocated.append(['args', {'owner':'me', 'fieldType':'String', 'arraySpec':None,'argList':None}])
        else:
            structCode += indent + "public " + typeDefName + ' ' + fieldName +"("+argListText+")"

    else:
        structCode += indent + "public " + typeDefName +' ' + fieldName +"("+argListText+")";
    return [structCode, funcDefCode, globalFuncs]

def codeSetBits(LHS_Left, LHS_FieldType, prefix, bitMask, RHS):
    if (RHS == 'true'):RHS= '1'
    elif (RHS == 'false'):RHS= '0'
    if (LHS_FieldType =='flag' ):
        item = LHS_Left+"flags"
        mask = prefix+bitMask
        val = RHS
    elif (LHS_FieldType =='mode' ):
        item = LHS_Left+"flags"
        mask = prefix+bitMask+"Mask"
        val = RHS+"<<"+prefix+bitMask+"Offset"
    return "{"+item+" &= ~"+mask+"; "+item+" |= ("+val+");}\n"


#######################################################

def includeDirective(libHdr):
    S = 'import '+libHdr+';\n'
    return S



def generateMainFunctionality(objects, tags):
    # TODO: Make initCode, runCode and deInitCode work better and more automated by patterns.
    # TODO: Some deInitialize items should automatically run during abort().
    # TODO: Deinitialize items should happen in reverse order.

    runCode = progSpec.fetchTagValue(tags, 'runCode')
    Platform = progSpec.fetchTagValue(tags, 'Platform')
    if Platform == 'Android':
        Lib_Android.GenerateMainActivity(objects, tags, runCode)
    else:
        mainFuncCode="""
        me void: main( ) <- {
            initialize()
            """ + runCode + """
            deinitialize()
            endFunc()
        }

    """
        progSpec.addObject(objects[0], objects[1], 'GLOBAL', 'struct', 'SEQ')
        codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef('GLOBAL',  mainFuncCode ))


def fetchXlators():
    xlators = {}

    xlators['LanguageName']     = "Java"
    xlators['BuildStrPrefix']   = "Javac "
    xlators['fileExtension']     = ".java"
    xlators['typeForCounterInt']= "int"
    xlators['GlobalVarPrefix']  = "GLOBAL.static_Global."
    xlators['PtrConnector']     = "."                      # Name segment connector for pointers.
    xlators['ObjConnector']     = "."                      # Name segment connector for classes.
    xlators['doesLangHaveGlobals'] = "False"
    xlators['funcBodyIndent']   = "    "
    xlators['funcsDefInClass']  = "True"
    xlators['MakeConstructors'] = "False"
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

    return(xlators)
