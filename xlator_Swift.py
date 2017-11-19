#xlator_Swift.py
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
        langType = langType
    elif owner=='me':
        langType = langType
    elif owner=='my':
        langType = langType
    elif owner=='our':
        langType = langType
    elif owner=='their':
        langType  = langType
    elif owner=='itr':
        langType += '::iterator'
    elif owner=='we':
        langType += 'public static'
    else:
        langType = ''
    return langType

def xlateLangType(TypeSpec, owner, fieldType, varMode, xlator):
    fieldAttrs=''
    langType = adjustBaseTypes(fieldType)
    if varMode != 'alloc':
        fieldAttrs = applyOwner(owner, langType, varMode)
    if 'arraySpec' in TypeSpec:
        arraySpec=TypeSpec['arraySpec']
        if(arraySpec): # Make list, map, etc
            [containerType, idxType, owner]=getContainerType(TypeSpec)
            if 'owner' in TypeSpec['arraySpec']:
                containerOwner=TypeSpec['arraySpec']['owner']
            else: containerOwner='me'
            idxType=adjustBaseTypes(idxType)
            if idxType=='timeValue': idxType = 'Int64'

            if containerType=='list':
                langType="["+langType+"]"
            elif containerType=='map':
                langType="NSMutableOrderedSet< "+idxType+', '+langType+" >"
            elif containerType=='multimap':
                langType="multimap< "+idxType+', '+langType+" >"

            if varMode != 'alloc':
                fieldAttrs=applyOwner(containerOwner, langType, varMode)

    if varMode != 'alloc' and progSpec.typeIsPointer(TypeSpec):
        langType+='?'    # Make pointer func args optionals

    return [langType, fieldAttrs]   # E.g.: langType='uint', file

def convertType(classes, TypeSpec, varMode, xlator):
    # varMode is 'var' or 'arg'. Large items are passed as pointers
    owner=TypeSpec['owner']
    fieldType=TypeSpec['fieldType']
    if not isinstance(fieldType, basestring):
        #if len(fieldType)>1: exit(2)
        fieldType=fieldType[0]
    baseType = progSpec.isWrappedType(classes, fieldType)
    if(baseType!=None):
        owner=baseType['owner']
        fieldType=baseType['fieldType']
    if(fieldType=='<%'): return fieldType[1][0]
    return xlateLangType(TypeSpec, owner, fieldType, varMode, xlator)

def codeIteratorOperation(itrCommand):
    result = ''
    if itrCommand=='goNext':  result='%0.next()'
    elif itrCommand=='goPrev':result='%0.Swift ERROR!'
    elif itrCommand=='key':   result='%0.getKey()'
    elif itrCommand=='val':   result='%0.getValue()'
    return result


def recodeStringFunctions(name, typeSpec):
    if name == "size":
        name = "characters.count"
        typeSpec['fieldType']='int'
    elif name == "subStr":
        typeSpec['codeConverter']='substring(from:%1, to:%2)'
    #elif name == "append": name='append'

    return [name, typeSpec]

def langStringFormatterCommand(fmtStr, argStr):
    S='String(format:'+'"'+ fmtStr +'"'+ argStr +')'
    return S

def LanguageSpecificDecorations(S, segType, owner):
    if segType!= 0 and progSpec.typeIsPointer(segType) and owner!='itr' and S!='NULL' and S[-1]!=']':
        S+='!'  # optionals
    return S

def checkForTypeCastNeed(lhsTypeSpec, rhsTypeSpec, RHScodeStr):
    LHS_KeyType = progSpec.varTypeKeyWord(lhsTypeSpec)
    RHS_KeyType = progSpec.varTypeKeyWord(rhsTypeSpec)
    if LHS_KeyType == 'uint64' and RHS_KeyType=='int':
        RHScodeStr = 'UInt64('+RHScodeStr+')'
    elif LHS_KeyType == 'double' and RHS_KeyType=='int':
        RHScodeStr = 'Double('+RHScodeStr+')'
    elif LHS_KeyType == 'int' and RHS_KeyType=='char':
        RHScodeStr = RHScodeStr+'.asciiValue'
    #elif LHS_KeyType != RHS_KeyType and LHS_KeyType != "mode" and LHS_KeyType != "flag" and RHS_KeyType != "ERROR" and LHS_KeyType != "struct" and LHS_KeyType != "bool":
    #    print"checkForTypeCastNeed: ", LHS_KeyType, RHS_KeyType, '        ',  RHScodeStr

    return RHScodeStr

def chooseVirtualRValOwner(LVAL, RVAL):
    # Returns left and right text decorations for RHS of function arguments, return values, etc.
    if RVAL==0 or RVAL==None or isinstance(RVAL, basestring): return ['',''] # This happens e.g., string.size() # TODO: fix this.
    if LVAL==0 or LVAL==None or isinstance(LVAL, basestring): return ['', '']
    LeftOwner =progSpec.getTypeSpecOwner(LVAL)
    RightOwner=progSpec.getTypeSpecOwner(RVAL)
    if LeftOwner == RightOwner: return ["", ""]
    if LeftOwner!='itr' and RightOwner=='itr': return ["", ".value"]
    if LeftOwner=='me' and progSpec.typeIsPointer(RVAL): return ['', '']
    if progSpec.typeIsPointer(LVAL) and RightOwner=='me': return ['', '']
    #if LeftOwner=='their' and (RightOwner=='our' or RightOwner=='my'): return ['','.get()']
    return ['','']

def determinePtrConfigForAssignments(LVAL, RVAL, assignTag):
    #TODO: make test case
    # Returns left and right text decorations for both LHS and RHS of assignment
    if RVAL==0 or RVAL==None or isinstance(RVAL, basestring): return ['','',  '',''] # This happens e.g., string.size() # TODO: fix this.
    if LVAL==0 or LVAL==None or isinstance(LVAL, basestring): return ['','',  '','']
    LeftOwner =progSpec.getTypeSpecOwner(LVAL)
    RightOwner=progSpec.getTypeSpecOwner(RVAL)
    if progSpec.typeIsPointer(LVAL) and progSpec.typeIsPointer(RVAL):
        if assignTag=='deep' :return ['','',  '','']
        else: return ['','',  '', '']
    if LeftOwner == RightOwner: return ['','',  '','']
    if LeftOwner=='me' and progSpec.typeIsPointer(RVAL):
        [leftMod, rightMod] = getTheDerefPtrMods(RVAL)
        return ['','',  leftMod, rightMod]  # ['', '', "(*", ")"]
    if progSpec.typeIsPointer(LVAL) and RightOwner=='me':
        if assignTag=='deep' :return ['','',  '', '']
        else: return ['','',  "", '']

    #if LeftOwner=='their' and (RightOwner=='our' or RightOwner=='my'): return ['','', '','.get()']

    return ['','',  '','']


def getTheDerefPtrMods(itemTypeSpec):
    if itemTypeSpec!=None and isinstance(itemTypeSpec, dict) and 'owner' in itemTypeSpec:
        if progSpec.typeIsPointer(itemTypeSpec):
            owner=progSpec.getTypeSpecOwner(itemTypeSpec)
            if owner=='itr':
                containerType = itemTypeSpec['arraySpec'][2]
                if containerType =='map' or containerType == 'multimap':
                    return ['', '->value']
            return ['', '']
    return ['', '']

def derefPtr(varRef, itemTypeSpec):
    if varRef=='NULL': return varRef
    [leftMod, rightMod] = getTheDerefPtrMods(itemTypeSpec)
    return leftMod + varRef + rightMod

def getCodeAllocStr(varTypeStr, owner):
    if(owner=='our'): S=varTypeStr
    elif(owner=='my'): S=varTypeStr
    elif(owner=='their'): S=varTypeStr
    elif(owner=='me'): print "ERROR: Cannot allocate a 'me' variable."; exit(1);
    elif(owner=='const'): print "ERROR: Cannot allocate a 'const' variable."; exit(1);
    else: print "ERROR: Cannot allocate variable because owner is", owner+"."; exit(1);
    return S

def getCodeAllocSetStr(varTypeStr, owner, value):
    S=getCodeAllocStr(varTypeStr, owner)
    S+='('+value+')'
    return S

def getConstIntFieldStr(fieldName, fieldValue):
    S= "static let "+fieldName+ ": Int = " + fieldValue+ ";\n"
    return(S)

def getEnumStr(fieldName, enumList):
    S=''
    count=0
    for enumName in enumList:
        S += "    " + getConstIntFieldStr(enumName, str(count))
        count=count+1
    S += "\n"
    return(S)

######################################################   E X P R E S S I O N   C O D I N G

def getContainerTypeInfo(classes, containerType, name, idxType, typeSpecOut, paramList, xlator):
    convertedIdxType = ""
    typeSpecOut={'owner':'me', 'fieldType': 'void'}
    if containerType=='list':
        if name=='size'       : name='count'; typeSpecOut={'owner':'me', 'fieldType': 'Int'}; paramList=None;
        elif name=='clear'    : name='removeAll'
        elif name=='front'    : name='begin()';  typeSpecOut['owner']='itr'; paramList=None;
        elif name=='back'     : name='rbegin()'; typeSpecOut['owner']='itr'; paramList=None;
        elif name=='end'      : name='end()';    typeSpecOut['owner']='itr'; paramList=None;
        elif name=='rend'     : name='rend()';   typeSpecOut['owner']='itr'; paramList=None;
        elif name=='first'    : name='begin()->second';  paramList=None;
        elif name=='last'     : name='rbegin()->second'; paramList=None;
        elif name=='popFirst' : name='pop_front'
        elif name=='popLast'  : name='pop_back'
        elif name=='pushFirst': name=typeSpecOut['codeConverter']='insert(%1, at:0)';
        elif name=='pushLast' : name='append'
        elif name=='erase'    : name='xlator_Swift.getContainerTypeInfo'
        elif name=='deleteNth': name='xlator_Swift.getContainerTypeInfo'
        elif name=='nthItr'   : name='xlator_Swift.getContainerTypeInfo'
        else: print "xlator_Swift.getContainerTypeInfo Unknown list command:", name; exit(2);
    elif containerType=='map':
        # https://developer.apple.com/documentation/foundation/nsmutableorderedset
        if idxType=='timeValue': convertedIdxType = 'Int64'
        else: convertedIdxType=idxType
        [convertedItmType, fieldAttrs]=xlator['convertType'](classes, typeSpecOut, 'var', xlator)
        if name=='containsKey': name="containsKey"; typeSpecOut={'owner':'me', 'fieldType': 'bool'}
        elif name=='size'     : name='count'; typeSpecOut={'owner':'me', 'fieldType': 'Int'}; paramList=None;
        elif name=='insert'   : typeSpecOut['codeConverter']='insert(pair<'+convertedIdxType+', '+convertedItmType+'>(%1, %2))';
        elif name=='clear'    : name='removeAll'
        elif name=='find'     : name='find';     typeSpecOut['owner']='itr';
        elif name=='front'    : name='begin()';  typeSpecOut['owner']='itr'; paramList=None;
        elif name=='back'     : name='rbegin()'; typeSpecOut['owner']='itr'; paramList=None;
        elif name=='end'      : name='endIndex';    typeSpecOut['owner']='itr'; paramList=None;
        elif name=='rend'     : name='rend()';   typeSpecOut['owner']='itr'; paramList=None;
        elif name=='first'    : name='begin()->second';  paramList=None;
        elif name=='last'     : name='rbegin()->second'; paramList=None;
        elif name=='popFirst' : name='pop_front'
        elif name=='popLast'  : name='pop_back'
        elif name=='get'      : name='xlator_Swift.getContainerTypeInfo'
        else: print "xlator_Swift.getContainerTypeInfo Unknown map command:", name; exit(2);
    elif containerType=='multimap':
        if idxType=='timeValue': convertedIdxType = 'Int64'
        else: convertedIdxType=idxType
        [convertedItmType, fieldAttrs]=xlator['convertType'](classes, typeSpecOut, 'var', xlator)
        if name=='size'       : name='count'; typeSpecOut={'owner':'me', 'fieldType': 'Int'}; paramList=None;
        elif name=='insert'   : typeSpecOut['codeConverter']='insert(pair<'+convertedIdxType+', '+convertedItmType+'>(%1, %2))';
        elif name=='clear'    : name='removeAll'
        elif name=='front'    : name='begin()';  typeSpecOut['owner']='itr'; paramList=None;
        elif name=='back'     : name='rbegin()'; typeSpecOut['owner']='itr'; paramList=None;
        elif name=='end'      : name='end()';    typeSpecOut['owner']='itr'; paramList=None;
        elif name=='rend'     : name='rend()';   typeSpecOut['owner']='itr'; paramList=None;
        elif name=='first'    : name='begin()->second';  paramList=None;
        elif name=='last'     : name='rbegin()->second'; paramList=None;
        elif name=='popFirst' : name='pop_front'
        elif name=='popLast'  : name='pop_back'
        else: print "xlator_Swift.getContainerTypeInfo Unknown multimap command:", name; exit(2);
    elif containerType=='tree': # TODO: Make trees work
        if name=='size' : name='count'; typeSpecOut={'owner':'me', 'fieldType': 'Int'}; paramList=None;
        elif name=='clear': name='removeAll'
        else: print "xlator_Swift.getContainerTypeInfo Unknown tree command:", name; exit(2)
    elif containerType=='graph': # TODO: Make graphs work
        if name=='size' : name='count'; typeSpecOut={'owner':'me', 'fieldType': 'Int'}; paramList=None;
        elif name=='clear': name='removeAll'
        else: print "xlator_Swift.getContainerTypeInfo Unknown graph command:", name; exit(2);
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
        elif item0=='!':  # 'not' operator?
            [S2, retType] = codeExpr(item[1], objsRefed, xlator)
            if progSpec.varsTypeCategory(retType) != 'bool':
                if S2[-1]=='!': S2=S2[:-1]   # Todo: Better detect this
                S2='('+S2+' != nil)'
                retType='bool'
            S+='!' + S2  # add 'not' operator
        elif item0=='-':
            [S2, retType] = codeExpr(item[1], objsRefed, xlator)
            S+='-' + S2
        elif item0=='[':
            tmp="["
            for expr in item[1:-1]:
                [S2, retType] = codeExpr(expr, objsRefed, xlator)
                if len(tmp)>1: tmp+=", "
                tmp+=S2
            tmp+="]"
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
            [codeStr, retType, prntType, AltIDXFormat]=codeItemRef(item0, 'RVAL', objsRefed, xlator)
            if(codeStr=="NULL"):
                codeStr="nil"
                retType={'owner':"PTR"}
            S+=codeStr                                # Code variable reference or function call
    return [S, retType]

def codeTerm(item, objsRefed, xlator):
    #print '               term item:', item
    [S, retType]=codeFactor(item[0], objsRefed, xlator)
    if (not(isinstance(item, basestring))) and (len(item) > 1) and len(item[1])>0:
        S=derefPtr(S, retType)
        for i in item[1]:
            #print '               term:', i
            if   (i[0] == '*'): S+=' * '
            elif (i[0] == '/'): S+=' / '
            elif (i[0] == '%'): S+=' % '
            else: print "ERROR: One of '*', '/' or '%' expected in code generator."; exit(2)
            [S2, retType2] = codeFactor(i[1], objsRefed, xlator)
            S2=derefPtr(S2, retType2)
            S+=S2
    return [S, retType]

def codePlus(item, objsRefed, xlator):
    #print '            plus item:', item
    [S, retType]=codeTerm(item[0], objsRefed, xlator)
    if len(item) > 1 and len(item[1])>0:
        S=derefPtr(S, retType)
        for  i in item[1]:
            #print '            plus ', i
            if   (i[0] == '+'): S+=' + '
            elif (i[0] == '-'): S+=' - '
            else: print "ERROR: '+' or '-' expected in code generator."; exit(2)
            [S2, retType2] = codeTerm(i[1], objsRefed, xlator)
            S2=derefPtr(S2, retType2)
            if i[0]=='+' and 'fieldType' in retType2 and retType2['fieldType']=='char': S2='String('+S2+')'
            #print "SUMMANDS:", S, S2, "\n     ", retType, "\n\n     ", retType2, "\n"
            S+=S2
    return [S, retType]

def codeComparison(item, objsRefed, xlator):
    #print '         Comp item', item
    [S, retType]=codePlus(item[0], objsRefed, xlator)
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
            [S2, retType] = codePlus(i[1], objsRefed, xlator)
            S2=derefPtr(S2, retType)
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
        S_derefd = derefPtr(S, retType)
        for i in item[1]:
            #print '      IsEq ', i
            if   (i[0] == '=='): op=' == '
            elif (i[0] == '!='): op=' != '
            elif (i[0] == '==='): op=' == '
            else: print "ERROR: '==' or '!=' or '===' expected."; exit(2)
            [S2, retType] = codeComparison(i[1], objsRefed, xlator)
            rightOwner=progSpec.getTypeSpecOwner(retType)
            if not( leftOwner=='itr' and rightOwner=='itr') and i[0] != '===':
                if (S2!='nil' ): S=S_derefd
                elif S[-1]=='!': S=S[:-1]   # Todo: Better detect this
                S2=derefPtr(S2, retType)
            S+= op+S2
            retType='bool'
    return [S, retType]

def codeLogAnd(item, objsRefed, xlator):
    #print '   And item:', item
    [S, retType] = codeIsEQ(item[0], objsRefed, xlator)
    if len(item) > 1 and len(item[1])>0:
        S=derefPtr(S, retType)
        for i in item[1]:
            #print '   AND ', i
            if (i[0] == 'and'):
                [S2, retType] = codeIsEQ(i[1], objsRefed, xlator)
                S2=derefPtr(S2, retType)
                S+=' && ' + S2
            else: print "ERROR: 'and' expected in code generator."; exit(2)
            retType='bool'
    return [S, retType]

def codeExpr(item, objsRefed, xlator):
    #print 'Or item:', item
    [S, retType]=codeLogAnd(item[0], objsRefed, xlator)
    if not isinstance(item, basestring) and len(item) > 1 and len(item[1])>0:
        S=derefPtr(S, retType)
        for i in item[1]:
            #print 'OR ', i
            if (i[0] == 'or'):
                [S2, retType] = codeLogAnd(i[1], objsRefed, xlator)
                S2=derefPtr(S2, retType)
                S+=' || ' + S2
            else: print "ERROR: 'or' expected in code generator."; exit(2)
            retType='bool'
    #print "S:",S
    return [S, retType]

def adjustConditional(S2, conditionType):
    if conditionType!=None and not isinstance(conditionType, basestring):
        #print "ADJUST IF:", S2, conditionType
        if conditionType['owner']=='our' or conditionType['owner']=='their' or conditionType['owner']=='my' or progSpec.isStruct(conditionType['fieldType']):
            if S2[-1]=='!': S2=S2[:-1]   # Todo: Better detect this
            S2+=" != nil"
        elif conditionType['owner']=='me' and (conditionType['fieldType']=='flag' or progSpec.typeIsInteger(conditionType['fieldType'])):
            if S2[-1]=='!': S2=S2[:-1]   # Todo: Better detect this
            S2+=" != 0"
        conditionType='bool'
    return [S2, conditionType]

def codeSpecialReference(segSpec, objsRefed, xlator):
    S=''
    retType='void'   # default to void
    retOwner='me'    # default to 'me'
    funcName=segSpec[0]
    if(len(segSpec)>2):  # If there are arguments...
        paramList=segSpec[2]
        if(funcName=='print'):
            S+='print('
            count = 0
            for P in paramList:
                [S2, argType]=xlator['codeExpr'](P[0], objsRefed, xlator)
                if(count>0): S+=', '
                S+=S2
                count= count + 1
            S+=',separator:"", terminator:"")'
        elif(funcName=='AllocateOrClear'):
            [varName,  varTypeSpec]=xlator['codeExpr'](paramList[0][0], objsRefed, xlator)
            if(varTypeSpec==0): cdErr("Name is undefined: " + varName)
            if(varName[-1]=='!'): varNameUnRefed=varName[:-1]  # Remove a reference. It would be better to do this in codeExpr but may take some work.
            else: varNameUnRefed=varName
            S+='if('+varNameUnRefed+' != nil){'+varName+'.clear();} else {'+varName+" = "+codeAllocater(varTypeSpec, xlator)+"();}"
        elif(funcName=='Allocate'):
            [varName,  varTypeSpec]=xlator['codeExpr'](paramList[0][0], objsRefed, xlator)

            if(varTypeSpec==0): cdErr("Name is Undefined: " + varName)
            S+=varName+" = "+codeAllocater(varTypeSpec, xlator)+'('
            count=0   # TODO: As needed, make this call CodeParameterList() with modelParams of the constructor.
            for P in paramList[1:]:
                if(count>0): S+=', '
                [S2, argType]=xlator['codeExpr'](P[0], objsRefed, xlator)
                S+=S2
                count=count+1
            S+=")"
        elif(funcName=='callPeriodically'):
            [objName,  retType]=xlator['codeExpr'](paramList[1][0], objsRefed, xlator)
            [interval,  intSpec]   =xlator['codeExpr'](paramList[2][0], objsRefed, xlator)
            varTypeSpec= retType['fieldType'][0]
            wrapperName="cb_wraps_"+varTypeSpec
            S+='g_timeout_add('+interval+', '+wrapperName+', '+objName+')'

            # Create a global function wrapping the class
            decl='\nint '+wrapperName+'(void* data)'
            defn='{'+varTypeSpec+'* self = ('+varTypeSpec+'*)data; self.run(); return true;}\n\n'
            appendGlobalFuncAcc(decl, defn)
        elif(funcName=='break'):
            if len(paramList)==0: S='break'
        elif(funcName=='return'):
            if len(paramList)==0: S+='return'
        elif(funcName=='toStr'):
            if len(paramList)==1:
                [S2, argType]=xlator['codeExpr'](P[0][0], objsRefed, xlator)
                S2=derefPtr(S2, argType)
                S+='to_string('+S2+')'
                returnType='string'
    else: # Not parameters, i.e., not a function
        if(funcName=='self'):
            S+='self'


    return [S, retOwner, retType]

def checkIfSpecialAssignmentFormIsNeeded(AltIDXFormat, RHS, rhsType):
    return ""

############################################
def codeMain(classes, tags, objsRefed, xlator):
    print "\n            Generating GLOBAL..."
    if("GLOBAL" in classes[1]):
        if(classes[0]["GLOBAL"]['stateType'] != 'struct'):
            print "ERROR: GLOBAL must be a 'struct'."
            exit(2)
        [structCode, funcCode, globalFuncs]=codeStructFields(classes, "GLOBAL", tags, '', objsRefed, xlator)
        if(funcCode==''): funcCode="// No main() function.\n"
        if(structCode==''): structCode="// No Main Globals.\n"
        funcCode = "\n\n"+funcCode
        return ["\n\n// Globals\n" + structCode + globalFuncs, funcCode]
    return ["// No Main Globals.\n", "// No main() function defined.\n"]

def codeArgText(argFieldName, argType, xlator):
    return "_ " + argFieldName + ": " + argType

def codeStructText(classes, attrList, parentClass, classInherits, classImplements, structName, structCode, tags):
    classAttrs=''
    if len(attrList)>0:
        for attr in attrList:
            if attr[0]=='@': classAttrs += attr+' '

    if parentClass != "":
        parentClass=': '+parentClass+' '
        parentClass = progSpec.unwrapClass(structName)
    if classImplements!=None:
        parentClass=': '
        count =0
        for item in classImplements[0]:
            if count>0:
                parentClass+= ', '
            parentClass+= item
            count += 1
    if classInherits!=None:
        parentClass=': ' + classInherits[0][0]
    S= "\n"+classAttrs+"class "+structName+parentClass+"{\n" + structCode + '};\n'
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
    S='\n\n//////////// SWIFT specific code:\n'
    S+="""
extension String {
    func index(from: Int) -> Index {
        return self.index(startIndex, offsetBy: from)
    }

    func substring(from: Int) -> String {
        return String(self[index(from: from)...])
    }

    func substring(to: Int) -> String {
        return String(self[..<index(from: to)])
    }

    func substring(from: Int, to:Int) -> String {
        return String(self[index(from: from)..<index(from: to)])
    }

    func substring(from: Int, length:Int) -> String {
        return String(self[index(from: from)..<index(from: length+from)])
    }

    func getChar(at: Int) -> Character {
        return Character(self.substring(from: at, length:1))
    }
}

extension Character {
    var asciiValue: Int {
        get {
            let s = String(self).unicodeScalars
            return Int(s[s.startIndex].value)
        }
    }
}
    """

    decl ="string readFileAsString(string filename)"
    defn="""{
        string S="";
        std::ifstream file(filename);
        if(file.eof() || file.fail()) {return "";}
        file.seekg(0, std::ios::end);
        S.resize(file.tellg());
        file.seekg(0, std::ios::beg);
        file.read((char*)S.c_str(), S.characters.count);
        return S;  //No errors
    }"""
    #appendGlobalFuncAcc(decl, defn)

    return S

def addGLOBALSpecialCode(classes, tags, xlator):
    specialCode =''

    GLOBAL_CODE="""
struct GLOBAL{
    %s
}
    """ % (specialCode)

    #codeDogParser.AddToObjectFromText(classes[0], classes[1], GLOBAL_CODE )
def variableDefaultValueString(fieldType):
    if (fieldType == "String"):
        fieldValueText='""'
    elif (fieldType.startswith("[")):
        fieldValueText=fieldType + "()"
    elif (fieldType == "Bool"):
        fieldValueText='false'
    elif (isNumericType(fieldType)):
        fieldValueText='0'
    elif (fieldType == "Character"):
        fieldValueText='"\\0"'
    else:
        fieldValueText = fieldType +'()'
    return fieldValueText

def codeNewVarStr (classes, lhsTypeSpec, varName, fieldDef, indent, objsRefed, xlator):
    assignValue=''
    [fieldType, fieldAttrs]           = xlator['convertType'](classes, lhsTypeSpec, 'var', xlator)
    [allocFieldType, allocFieldAttrs] = xlator['convertType'](classes, lhsTypeSpec, 'alloc', xlator)
    if(fieldDef['value']):
        [RHS, rhsTypeSpec]=xlator['codeExpr'](fieldDef['value'][0], objsRefed, xlator)
        [leftMod, rightMod]=chooseVirtualRValOwner(lhsTypeSpec, rhsTypeSpec)
        RHS = leftMod+RHS+rightMod
        RHS = xlator['checkForTypeCastNeed'](lhsTypeSpec, rhsTypeSpec, RHS)
        assignValue = " = " + RHS

    else: # If no value was given:
        if fieldDef['paramList'] != None:
            # Code the constructor's arguments
            [CPL, paramTypeList] = codeParameterList(varName, fieldDef['paramList'], None, objsRefed, xlator)
            if len(paramTypeList)==1:
                if not isinstance(paramTypeList[0], dict):
                    print "\nPROBLEM: The return type of the parameter '", CPL, "' cannot be found and is needed. Try to define it.\n"
                    exit(1)

                theParam=paramTypeList[0]['fieldType']

                # TODO: Remove the 'True' and make this check object heirarchies or similar solution
                if True or not isinstance(theParam, basestring) and fieldType==theParam[0]:
                    assignValue = " = " + CPL   # Act like a copy constructor
        else:
            assignValue = ' = '+variableDefaultValueString(allocFieldType)
    if (assignValue == ""):
        varDeclareStr= "var " + varName + ": "+ fieldType + " = " + allocFieldType + '()'
    else:

        varDeclareStr= "var " + varName + ": "+ fieldType + assignValue

    return(varDeclareStr)

def codeRangeSpec(traversalMode, ctrType, repName, S_low, S_hi, indent, xlator):
    if(traversalMode=='Forward' or traversalMode==None):
        S = indent + "for "+ repName+' in '+ S_low + "...Int(" + S_hi + ") {\n"
    elif(traversalMode=='Backward'):
        S = indent + "for("+ctrType+" " + repName+'='+ S_hi + "-1; " + repName + ">=" + S_low +"; "+ repName + "-=1){\n"
    return (S)

def iterateRangeContainerStr(classes,localVarsAllocated, StartKey, EndKey,containerType,repName,repContainer,datastructID,keyFieldType,indent,xlator):
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
        actionText += (indent + "for( auto " + repName+'Itr ='+ repContainer+'->lower_bound('+StartKey+')' + "; " + repName + "Itr !=" + repContainer+'->upper_bound('+EndKey+')' +"; ++"+ repName + "Itr ){\n"
                    + indent+"    "+"auto "+repName+" = *"+repName+"Itr;\n")

    elif datastructID=='list' or (datastructID=='list' and not willBeModifiedDuringTraversal):
        pass;
    elif datastructID=='list' and willBeModifiedDuringTraversal:
        pass;
    else:
        print "DSID:",datastructID,containerType
        exit(2)

    return [actionText, loopCounterName]

def iterateContainerStr(classes,localVarsAllocated,containerType,repName,repContainer,datastructID,keyFieldType,ContainerOwner, isBackward,indent,xlator):
    willBeModifiedDuringTraversal=True   # TODO: Set this programatically leter.
    actionText = ""
    loopCounterName = ""
    containedType=containerType['fieldType']

    if datastructID=='multimap' or datastructID=='map':
        ctrlVarsTypeSpec = {'owner':'me', 'fieldType':containedType}
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType, 'codeConverter':(repName+'.key')}
        localVarsAllocated.append([repName+'_key', keyVarSpec])  # Tracking local vars for scope
        ctrlVarsTypeSpec['codeConverter'] = (repName+'.value')

        localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
        actionText += (indent + "for " + repName+' in '+ repContainer + " {\n")
        #print "MAKING MAP LOOP:", repContainer, repName, containerType

    elif datastructID=='list' or (datastructID=='list' and not willBeModifiedDuringTraversal):
        ctrlVarsTypeSpec = {'owner':'me', 'fieldType':containedType}
        loopCounterName=repName+'_key'
        keyVarSpec = {'owner':'me', 'fieldType':'Int'}
        localVarsAllocated.append([loopCounterName, keyVarSpec])  # Tracking local vars for scope

        localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
        actionText += (indent + "for " + repName+' in '+ repContainer + " {\n")
        #print "MAKING LIST LOOP:", repContainer, repName, containerType
    elif datastructID=='list' and willBeModifiedDuringTraversal:
        ctrlVarsTypeSpec = {'owner':containerType['owner'], 'fieldType':containedType}
        loopCounterName=repName+'_key'
        keyVarSpec = {'owner':'me', 'fieldType':'Int'}
        localVarsAllocated.append([loopCounterName, keyVarSpec])  # Tracking local vars for scope

        localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
        lvName=repName+"Itr"
       # [containerType, containedType] = convertType(classes, ctrlVarsTypeSpec, 'var', xlator)
        #print "MAKING LOOP:", lvName, repContainer, repName, containerType, repContainer
        actionText += ( indent + "for " + lvName + " in 0..<" +  repContainer+".count {\n"
                    + indent+"    var "+repName + ':' + containerType + " = "+repContainer+"["+lvName+"];\n")
    else:
        print "DSID:",datastructID,containerType
        exit(2)

    return [actionText, loopCounterName]

def codeIncrement(varName):
    return varName + " += 1"

def codeDecrement(varName):
    return varName + " -= 1"

def isNumericType(convertedType):
    if(convertedType == "UInt32" or convertedType == "UInt64" or convertedType == "Float" or convertedType == "Int" or convertedType == "Int32" or convertedType == "Int64" or convertedType == "Double"):
        return True
    else:
        return False

def codeVarFieldRHS_Str(fieldName,  convertedType, fieldOwner, paramList, objsRefed, xlator):
    fieldValueText=""
    if paramList!=None:
        [CPL, paramTypeList] = codeParameterList(fieldName, paramList, None, objsRefed, xlator)
        fieldValueText=" = " + convertedType + CPL
    else:
        if fieldOwner=='me' or fieldOwner=='we':
            fieldValueText = ' = '+variableDefaultValueString(convertedType)
    return fieldValueText

def codeConstField_Str(convertedType, fieldName, fieldValueText, indent, xlator ):
    return indent  + "let " + fieldName + ':'+ convertedType  + fieldValueText +';\n';

def codeVarField_Str(intermediateType, fieldAttrs, typeSpec, fieldName, fieldValueText, className, tags, indent):
    #TODO: make test case
    fieldOwner=progSpec.getTypeSpecOwner(typeSpec)
    if fieldOwner=='we':
        defn = indent + "public static var "+ fieldName + ": " +  intermediateType  +  fieldValueText + '\n'
        decl = ''
    else:
        fieldTypeMod=''
    #    if progSpec.typeIsPointer(typeSpec):
    #        fieldTypeMod += '?CUSTARD'    # Make pointer field variables optionals
        defn = indent + "var "+ fieldName + ": " +  intermediateType + fieldTypeMod + fieldValueText + '\n'
        decl = ''
    return [defn, decl]

def codeConstructorHeader(ClassName, constructorArgs, constructorInit, copyConstructorArgs, xlator):
    #TODO: Swift should only have constructors if they are called somewhere.
    return "" #    init (" + constructorArgs+"){"+constructorInit+"\n    }\n"

def codeConstructorInit(fieldName, count, defaultVal, xlator):
    if (count > 0):
        return "\n        self." + fieldName +" = arg_"+fieldName
    elif(count == 0):
        return "\n        self." + fieldName +" = arg_"+fieldName
    else:
        print "Error in codeConstructorInit."
        exit(2)

def codeConstructorArgText(argFieldName, count, argType, defaultVal, xlator):
    if defaultVal == "NULL":
        defaultVal = "0"
    return "arg_" + argFieldName  + ': ' +argType

def codeCopyConstructor(fieldName, convertedType, xlator):
    return ""

def codeFuncHeaderStr(className, fieldName, returnType, argListText, localArgsAllocated, inheritMode, indent):
    #TODO: add \n before func
    structCode=''; funcDefCode=''; globalFuncs='';
    if returnType!='': returnType = '-> '+returnType
    if(className=='AppDelegate'):
        if fieldName=='application':
            structCode += '    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplicationLaunchOptionsKey: Any]?) -> Bool '
            localArgsAllocated.append(['application', {'owner':'me', 'fieldType':'UIApplication', 'arraySpec':None,'argList':None}])
            localArgsAllocated.append(['launchOptions', {'owner':'their', 'fieldType':'int', 'arraySpec':None,'argList':None}])  # TODO: Wrong. launchOptions should be an array.
        else:
            structCode +="func " + fieldName +"("+argListText+") " + returnType
    else:
        funcAttrs=''
        if inheritMode=='override': funcAttrs='override '
        if fieldName=="init":
            structCode += indent + funcAttrs + fieldName +"("+argListText+")"
        else:
            structCode += indent + funcAttrs + "func " + fieldName +"("+argListText+") " + returnType
    return [structCode, funcDefCode, globalFuncs]

def extraCodeForTopOfFuntion(argList):
    if len(argList)==0:
        topCode=''
    else:
        topCode=""
        for arg in argList:
            argTypeSpec =arg['typeSpec']
            argFieldName=arg['fieldName']
            topCode+= 'var '+argFieldName+' = '+argFieldName+'\n'
    return topCode

def codeArrayIndex(idx, containerType, LorR_Val, previousSegName):
    if (containerType == "string"):
        S= '.getChar(at:'+idx+')'
    else:
        S= '[' + idx +']'
    return S

def codeSetBits(LHS_Left, LHS_FieldType, prefix, bitMask, RHS, rhsType):
    if (LHS_FieldType =='flag' ):
        item = LHS_Left+"flags"
        mask = prefix+bitMask
        if (RHS != 'true' and RHS !='false'):
            RHS += ' != 0'
        val = '('+ RHS +') ? '+mask+':0'
    elif (LHS_FieldType =='mode' ):
        item = LHS_Left+"flags"
        mask = prefix+bitMask+"Mask"
        val = RHS+"<<"+prefix+bitMask+"Offset"
    return 'do{'+item+" &= ~UInt64("+mask+"); "+item+" |= UInt64("+val+");}\n"

def codeSwitchBreak(caseAction, indent, xlator):
    return indent+"    break;\n"

def applyTypecast(typeInCodeDog, itemToAlterType):
    platformType = adjustBaseTypes(typeInCodeDog)
    return platformType+'('+itemToAlterType+')';

#######################################################

def includeDirective(libHdr):
    S = 'import '+libHdr+'\n'
    return S

def generateMainFunctionality(classes, tags):
    # TODO: Make initCode, runCode and deInitCode work better and more automated by patterns.
    # TODO: Some deInitialize items should automatically run during abort().
    # TODO: Deinitialize items should happen in reverse order.

    runCode = progSpec.fetchTagValue(tags, 'runCode')
    mainFuncCode="""
    me void: runCode() <- {
        /-initialize()
        """ + runCode + """
        /-deinitialize()
    }

"""
    progSpec.addObject(classes[0], classes[1], 'GLOBAL', 'struct', 'SEQ')
    codeDogParser.AddToObjectFromText(classes[0], classes[1], progSpec.wrapFieldListInObjectDef('GLOBAL',  mainFuncCode ), 'Swift start-up code')


def fetchXlators():
    xlators = {}

    xlators['LanguageName']          = "Swift"
    xlators['BuildStrPrefix']        = ""
    xlators['fileExtension']         = ".swift"
    xlators['typeForCounterInt']     = "var"
    xlators['GlobalVarPrefix']       = ""
    xlators['PtrConnector']          = "."                       # Name segment connector for pointers.
    xlators['ObjConnector']          = "."                       # Name segment connector for classes.
    xlators['NameSegConnector']      = "."
    xlators['NameSegFuncConnector']  = "()."
    xlators['doesLangHaveGlobals']   = "True"
    xlators['funcBodyIndent']        = "    "
    xlators['funcsDefInClass']       = "True"
    xlators['MakeConstructors']      = "True"
    xlators['funcsDefInClass']       = "True"
    xlators['blockPrefix']           = "do"
    xlators['usePrefixOnStatics']    = "True"
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
