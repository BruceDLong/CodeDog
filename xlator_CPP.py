#xlator_CPP.py
import progSpec
import codeDogParser
from progSpec import cdlog, cdErr, logLvl
from CodeGenerator import codeItemRef, codeUserMesg, codeStructFields, codeAllocater, appendGlobalFuncAcc, codeParameterList, makeTagText, codeAction

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
            idxType=applyOwner(idxOwner, idxType, '')
        else: idxType=containerSpec['idxBaseType']
    datastructID = containerSpec['datastructID']
    if idxType[0:4]=='uint': idxType+='_t'
    if(datastructID=='list'): datastructID = "deque"
    return [datastructID, idxType, owner]

def adjustBaseTypes(fieldType):
    if(isinstance(fieldType, basestring)):
        if(fieldType=='uint8' or fieldType=='uint16'): fieldType='uint32'
        elif(fieldType=='int8' or fieldType=='int16'): fieldType='int32'
        if(fieldType=='uint32' or fieldType=='uint64' or fieldType=='int32' or fieldType=='int64'):
            langType=fieldType+'_t'
        else:
            langType=progSpec.flattenObjectName(fieldType)
    else: langType=progSpec.flattenObjectName(fieldType[0])
    return langType

def applyOwner(owner, langType, varMode):
    if owner=='me':
        langType = langType
    elif owner=='my':
        langType="unique_ptr<"+langType + ' >'
    elif owner=='our':
        langType="shared_ptr<"+langType + ' >'
    elif owner=='their':
        langType += '*'
    elif owner=='itr':
        langType += '::iterator'
    elif owner=='const':
        langType = "static const "+langType
    elif owner=='we':
        langType = 'static '+langType
    elif owner=='id_our':
        langType="shared_ptr<"+langType + ' >*'
    elif owner=='id_their':
        langType += '**'
    else:
        cdErr("ERROR: Owner of type not valid '" + owner + "'")
    return langType

def xlateLangType(TypeSpec, owner, fieldType, varMode, xlator):
    # varMode is 'var' or 'arg' or 'alloc'. Large items are passed as pointers

    langType = adjustBaseTypes(fieldType)
    InnerLangType = langType
    if varMode != 'alloc': langType = applyOwner(owner, langType, varMode)

    if 'arraySpec' in TypeSpec:
        arraySpec=TypeSpec['arraySpec']
        if(arraySpec): # Make list, map, etc
            [containerType, idxType, owner]=getContainerType(TypeSpec)

            if 'owner' in TypeSpec['arraySpec']:
                containerOwner=TypeSpec['arraySpec']['owner']
            else: containerOwner='me'
            idxType=adjustBaseTypes(idxType)
            if idxType=='timeValue': idxType = 'int64_t'

            if containerType=='deque':
                if varMode == 'alloc': langType = applyOwner(owner, langType, varMode)
                langType="deque< "+langType+" >"
            elif containerType=='map':
                if varMode == 'alloc': langType = applyOwner(owner, langType, varMode)
                langType="map< "+idxType+', '+langType+" >"
            elif containerType=='multimap':
                if varMode == 'alloc': langType = applyOwner(owner, langType, varMode)
                langType="multimap< "+idxType+', '+langType+" >"

            InnerLangType = langType
            if varMode != 'alloc':
                langType=applyOwner(containerOwner, langType, varMode)
    return [langType, InnerLangType]

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
    if itrCommand=='goNext':  result='%0++'
    elif itrCommand=='goPrev':result='--%0'
    elif itrCommand=='key':   result='%0->first'
    elif itrCommand=='val':   result='%0->second'
    return result

def recodeStringFunctions(name, typeSpec):
    if name == "size": name = "length"
    elif name == "subStr": name = "substr"

    return [name, typeSpec]

def langStringFormatterCommand(fmtStr, argStr):
    S='strFmt('+'"'+ fmtStr +'"'+ argStr +')'
    return S

def LanguageSpecificDecorations(S, segType, owner):
        return S


def checkForTypeCastNeed(LHS_Type, RHS_Type, codeStr):
    #LHS_KeyType = progSpec.varTypeKeyWord(lhsTypeSpec)
    #RHS_KeyType = progSpec.varTypeKeyWord(rhsTypeSpec)
    return codeStr

def getTheDerefPtrMods(itemTypeSpec):
    if itemTypeSpec!=None and isinstance(itemTypeSpec, dict) and 'owner' in itemTypeSpec:
        if progSpec.typeIsPointer(itemTypeSpec) and ('arraySpec' in itemTypeSpec):
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

def ChoosePtrDecorationForSimpleCase(owner):
    if(owner=='our' or owner=='my' or owner=='their'):
        return ['','->',  '(*', ')']
    else: return ['','.',  '','']

def chooseVirtualRValOwner(LVAL, RVAL):
    # Returns left and right text decorations for RHS of function arguments, return values, etc.
    if RVAL==0 or RVAL==None or isinstance(RVAL, basestring): return ['',''] # This happens e.g., string.size() # TODO: fix this.
    if LVAL==0 or LVAL==None or isinstance(LVAL, basestring): return ['', '']
    LeftOwner =progSpec.getTypeSpecOwner(LVAL)
    RightOwner=progSpec.getTypeSpecOwner(RVAL)
    if(LeftOwner=="id_their" and RightOwner=="id_their"): return ["&", ""]
    if LeftOwner == RightOwner: return ["", ""]
    if LeftOwner!='itr' and RightOwner=='itr': return ["", "->second"]
    if LeftOwner=='me' and progSpec.typeIsPointer(RVAL): return ["(*", "   )"]
    if progSpec.typeIsPointer(LVAL) and RightOwner=='me': return ["&", '']
    if LeftOwner=='their' and (RightOwner=='our' or RightOwner=='my'): return ['','.get()']
    return ['','']

def determinePtrConfigForAssignments(LVAL, RVAL, assignTag):
    #TODO: make test case
    # Returns left and right text decorations for both LHS and RHS of assignment
    if RVAL==0 or RVAL==None or isinstance(RVAL, basestring): return ['','',  '',''] # This happens e.g., string.size() # TODO: fix this.
    if LVAL==0 or LVAL==None or isinstance(LVAL, basestring): return ['','',  '','']
    LeftOwner =progSpec.getTypeSpecOwner(LVAL)
    RightOwner=progSpec.getTypeSpecOwner(RVAL)
    if progSpec.typeIsPointer(LVAL) and progSpec.typeIsPointer(RVAL):
        if assignTag=='deep' :return ['(*',')',  '(*',')']
        elif LeftOwner=='their' and (RightOwner=='our' or RightOwner=='my'): return ['','', '','.get()']
        else: return ['','',  '', '']
    if LeftOwner == RightOwner: return ['','',  '','']
    if LeftOwner=='me' and progSpec.typeIsPointer(RVAL):
        [leftMod, rightMod] = getTheDerefPtrMods(RVAL)
        return ['','',  leftMod, rightMod]  # ['', '', "(*", ")"]
    if progSpec.typeIsPointer(LVAL) and RightOwner=='me':
        if assignTag=='deep' :return ['(*',')',  '', '']
        else: return ['','',  "&", '']
    return ['','',  '','']


def getCodeAllocStr(varTypeStr, owner):
    if(owner=='our'): S="make_shared<"+varTypeStr+">"
    elif(owner=='my'): S="make_unique<"+varTypeStr+">"
    elif(owner=='their'): S="new "+varTypeStr
    elif(owner=='me'): print "ERROR: Cannot allocate a 'me' variable.", '('+varTypeStr+')'; exit(1);
    elif(owner=='const'): print "ERROR: Cannot allocate a 'const' variable."; exit(1);
    else: print "ERROR: Cannot allocate variable because owner is", owner+"."; exit(1);
    return S

def getCodeAllocSetStr(varTypeStr, owner, value):
    S=getCodeAllocStr(varTypeStr, owner)
    S+='('+value+')'
    return S

def getConstIntFieldStr(fieldName, fieldValue):
    S= "static const int "+fieldName+ " = " + fieldValue+ ";"
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
    return(S)

######################################################   E X P R E S S I O N   C O D I N G

def codeIdentityCheck(S1, S2, retType1, retType2):
    if progSpec.typeSpecsAreCompatible(retType1, retType2): retStr = S1+' == '+S2
    elif progSpec.typeIsPointer(retType1) and progSpec.typeIsPointer(retType2):
        LHS = S1
        RHS = S2
        LeftOwner  = progSpec.getTypeSpecOwner(retType1)
        RightOwner = progSpec.getTypeSpecOwner(retType2)
        if LeftOwner =='our' or LeftOwner =='my': LHS+='.get()'
        if RightOwner=='our' or RightOwner=='my': RHS+='.get()'
        retStr =  "(void*)("+LHS+") == (void*)("+RHS+")"
    else: retStr =  S1+' == '+S2
    #print "IDENTITY CHECK:"+retStr+"\n    ", retType1, "\n    ", retType2
    return retStr


def getContainerTypeInfo(classes, containerType, name, idxType, typeSpecIn, paramList, xlator):
    convertedIdxType = ""
    typeSpecOut = typeSpecIn
    #print containerType, name
    if containerType=='deque':
        if name=='at' or name=='resize': pass
        elif name=='size' : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
        elif name=='insert'   : typeSpecOut={'owner':'me', 'fieldType': 'void', 'argList':[{'typeSpec':{'owner':'itr'}}, {'typeSpec':typeSpecIn}]}
        elif name=='clear'    : typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif name=='erase'    : name='erase';  typeSpecOut['owner']='itr';
        elif name=='front'    : name='begin()';  typeSpecOut['owner']='itr'; paramList=None;
        elif name=='back'     : name='rbegin()'; typeSpecOut['owner']='itr'; paramList=None;
        elif name=='end'      : name='end()';    typeSpecOut['owner']='itr'; paramList=None;
        elif name=='rend'     : name='rend()';   typeSpecOut['owner']='itr'; paramList=None;
        elif name=='nthItr'   : typeSpecOut['codeConverter']='(%0.begin()+%1)'; typeSpecOut['owner']='itr';
        elif name=='first'    : name='front()';  paramList=None;
        elif name=='last'     : name='back()';   paramList=None;
        elif name=='popFirst' : name='pop_front'
        elif name=='popLast'  : name='pop_back'
        elif name=='pushFirst': name='push_front';# typeSpecOut={'owner':'me', 'fieldType': 'void', 'argList':[{'typeSpec':typeSpecIn}]}
        elif name=='pushLast' : name='push_back'; # typeSpecOut={'owner':'me', 'fieldType': 'void', 'argList':[{'typeSpec':typeSpecIn}]}
        else: print "Unknown deque command:", name; exit(2);
    elif containerType=='map':
        if idxType=='timeValue': convertedIdxType = 'int64_t'
        else: convertedIdxType=idxType
        [convertedItmType, innerType] = xlator['convertType'](classes, typeSpecOut, 'var', xlator)
        if name=='at': pass
        elif name=='containsKey'   :  typeSpecOut={'owner':'me', 'fieldType': 'bool'}; typeSpecOut['codeConverter']='count(%1)>=1';
        elif name=='size'     : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
        elif name=='insert'   : typeSpecOut['codeConverter']='insert(pair<'+convertedIdxType+', '+convertedItmType+'>(%1, %2))';
        elif name=='clear'    : typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif name=='find'     : name='find';     typeSpecOut['owner']='itr'; typeSpecOut['fieldType']=convertedItmType;
        elif name=='get'      : name='at';    # typeSpecOut['owner']='me';  typeSpecOut['fieldType']=convertedItmType;
        elif name=='erase'    : name='erase';  typeSpecOut['owner']='itr';
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
        if idxType=='timeValue': convertedIdxType = 'int64_t'
        else: convertedIdxType=idxType
        [convertedItmType, innerType] = xlator['convertType'](classes, typeSpecOut, 'var', xlator)
        if name=='at': pass
        elif name=='containsKey'   :  typeSpecOut={'owner':'me', 'fieldType': 'bool'}; typeSpecOut['codeConverter']='count(%1)>=1';
        elif name=='size'     : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
        elif name=='insert'   : typeSpecOut['codeConverter']='insert(pair<'+convertedIdxType+', '+convertedItmType+'>(%1, %2))';
        elif name=='clear'    : typeSpecOut={'owner':'me', 'fieldType': 'void'}
        elif name=='erase'    : name='erase';  typeSpecOut['owner']='itr';
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
    retType='noType'
    item0 = item[0]
    #print "ITEM0=", item0, ">>>>>", item
    if (isinstance(item0, basestring)):
        if item0=='(':
            [S2, retType] = codeExpr(item[1], objsRefed, returnType, xlator)
            S+='(' + S2 +')'
        elif item0=='!':
            [S2, retType] = codeExpr(item[1], objsRefed, returnType, xlator)
            S+='!' + S2
        elif item0=='-':
            [S2, retType] = codeExpr(item[1], objsRefed, returnType, xlator)
            S+='-' + S2
        elif item0=='[':
            tmp="{"
            for expr in item[1:-1]:
                [S2, retType] = codeExpr(expr, objsRefed, returnType, xlator)
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
            [codeStr, retType, prntType, AltIDXFormat]=codeItemRef(item0, 'RVAL', objsRefed, returnType, xlator)
            if(codeStr=="NULL"):
                codeStr="nullptr"
                retType={'owner':"PTR"}
            S+=codeStr                                # Code variable reference or function call
    return [S, retType]

def codeTerm(item, objsRefed, returnType, xlator):
    #print '               term item:', item
    [S, retType]=codeFactor(item[0], objsRefed, returnType, xlator)
    if (not(isinstance(item, basestring))) and (len(item) > 1) and len(item[1])>0:
        S=derefPtr(S, retType)
        for i in item[1]:
            #print '               term:', i
            if   (i[0] == '*'): S+=' * '
            elif (i[0] == '/'): S+=' / '
            elif (i[0] == '%'): S+=' % '
            else: print "ERROR: One of '*', '/' or '%' expected in code generator."; exit(2)
            [S2, retType2] = codeFactor(i[1], objsRefed, returnType, xlator)
            S2=derefPtr(S2, retType2)
            S+=S2
    return [S, retType]

def codePlus(item, objsRefed, returnType, xlator):
    #print '            plus item:', item
    [S, retType]=codeTerm(item[0], objsRefed, returnType, xlator)
    if len(item) > 1 and len(item[1])>0:
        S=derefPtr(S, retType)
        for  i in item[1]:
            #print '            plus ', i
            if   (i[0] == '+'): S+=' + '
            elif (i[0] == '-'): S+=' - '
            else: print "ERROR: '+' or '-' expected in code generator."; exit(2)
            [S2, retType2] = codeTerm(i[1], objsRefed, returnType, xlator)
            S2=derefPtr(S2, retType2)
            S+=S2
    return [S, retType]

def codeComparison(item, objsRefed, returnType, xlator):
    #print '         Comp item', item
    [S, retType]=codePlus(item[0], objsRefed, returnType, xlator)
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
            [S2, retType] = codePlus(i[1], objsRefed, returnType, xlator)
            S2=derefPtr(S2, retType)
            S+=S2
            retType='bool'
    return [S, retType]

def codeIsEQ(item, objsRefed, returnType, xlator):
    #print '      IsEq item:', item
    [S, retType]=codeComparison(item[0], objsRefed, returnType, xlator)
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
            [S2, retType2] = codeComparison(i[1], objsRefed, returnType, xlator)
            rightOwner=progSpec.getTypeSpecOwner(retType2)
            if not( leftOwner=='itr' and rightOwner=='itr') and i[0] != '===':
                if (S2!='NULL' and S2!='nullptr' ): S=S_derefd
                S2=derefPtr(S2, retType2)
            if i[0] == '===':
                S=codeIdentityCheck(S, S2, retType, retType2)
            else:S+= op+S2
            retType='bool'
    return [S, retType]

def codeLogAnd(item, objsRefed, returnType, xlator):
    #print '   And item:', item
    [S, retType] = codeIsEQ(item[0], objsRefed, returnType, xlator)
    if len(item) > 1 and len(item[1])>0:
        S=derefPtr(S, retType)
        for i in item[1]:
            #print '   AND ', i
            if (i[0] == 'and'):
                [S2, retType] = codeIsEQ(i[1], objsRefed, returnType, xlator)
                S2=derefPtr(S2, retType)
                S+=' && ' + S2
            else: print "ERROR: 'and' expected in code generator."; exit(2)
            retType='bool'
    return [S, retType]

def codeExpr(item, objsRefed, returnType, xlator):
    #print 'Or item:', item
    [S, retType]=codeLogAnd(item[0], objsRefed, returnType, xlator)
    if not isinstance(item, basestring) and len(item) > 1 and len(item[1])>0:
        S=derefPtr(S, retType)
        for i in item[1]:
            #print 'OR ', i
            if (i[0] == 'or'):
                [S2, retType] = codeLogAnd(i[1], objsRefed, returnType, xlator)
                S2=derefPtr(S2, retType)
                S+=' || ' + S2
            else: print "ERROR: 'or' expected in code generator."; exit(2)
            retType='bool'
    #print "S:",S
    return [S, retType]

def adjustConditional(S2, conditionType):
    return [S2, conditionType]

def codeSpecialReference(segSpec, objsRefed, xlator):
    S=''
    retType='void'   # default to void
    retOwner='me'    # default to 'me'
    funcName=segSpec[0]
    if(len(segSpec)>2):  # If there are arguments...
        paramList=segSpec[2]
        if(funcName=='print'):
            # TODO: have a tag to choose cout vs printf()
            S+='cout'
            for P in paramList:
                [S2, argType]=xlator['codeExpr'](P[0], objsRefed, None, xlator)
                S2=derefPtr(S2, argType)
                S+=' << '+S2
            S+=" << flush"
        elif(funcName=='input'):
            P=paramList[0]
            [S2, argType]=xlator['codeExpr'](P[0], objsRefed, None, xlator)
            S2=derefPtr(S2, argType)
            S+='getline(cin, '+S2+')'
        elif(funcName=='AllocateOrClear'):
            [varName,  varTypeSpec]=xlator['codeExpr'](paramList[0][0], objsRefed, None, xlator)
            if(varTypeSpec==0): cdErr("Name is undefined: " + varName)
            S+='if('+varName+'){'+varName+'->clear();} else {'+varName+" = "+codeAllocater(varTypeSpec, xlator)+"();}"
        elif(funcName=='Allocate'):
            [varName,  varTypeSpec]=xlator['codeExpr'](paramList[0][0], objsRefed, None, xlator)
            #print "ALLOCATE:", varName, varTypeSpec
            if(varTypeSpec==0): cdErr("Name is Undefined: " + varName)
            S+=varName+" = "+codeAllocater(varTypeSpec, xlator)+'('
            count=0   # TODO: As needed, make this call CodeParameterList() with modelParams of the constructor.
            for P in paramList[1:]:
                if(count>0): S+=', '
                [S2, argType]=xlator['codeExpr'](P[0], objsRefed, None, xlator)
                S+=S2
                count=count+1
            S+=")"
        elif(funcName=='callPeriodically'):
            [objName,  retType]=xlator['codeExpr'](paramList[1][0], objsRefed, None, xlator)
            [interval,  intSpec]   =xlator['codeExpr'](paramList[2][0], objsRefed, None, xlator)
            varTypeSpec= retType['fieldType'][0]
            wrapperName="cb_wraps_"+varTypeSpec
            S+='g_timeout_add('+interval+', '+wrapperName+', '+objName+')'

            # Create a global function wrapping the class
            decl='\nint '+wrapperName+'(void* data)'
            defn='{'+varTypeSpec+'* self = ('+varTypeSpec+'*)data; self->run(); return true;}\n\n'
            appendGlobalFuncAcc(decl, defn)
        elif(funcName=='break'):
            if len(paramList)==0: S='break'
        elif(funcName=='return'):
            if len(paramList)==0: S+='return'
        elif(funcName=='toStr'):
            if len(paramList)==1:
                [S2, argType]=xlator['codeExpr'](P[0][0], objsRefed, None, xlator)
                S2=derefPtr(S2, argType)
                S+='to_string('+S2+')'
                retType='string'
        elif(funcName=='asClass'):
            if len(paramList)==2:
                [newTypeStr, argType]=xlator['codeExpr'](paramList[0][0], objsRefed, None, xlator)
                newTypeStr=derefPtr(newTypeStr, argType)
                [toCvtStr, toCvtType]=xlator['codeExpr'](paramList[1][0], objsRefed, None, xlator)
                toCvtStr=derefPtr(toCvtStr, toCvtType)
                varOwner=progSpec.getTypeSpecOwner(toCvtType)
                if(varOwner=='their'): S="static_cast<"+newTypeStr+"*>("+toCvtStr+")"
                elif(varOwner=='our'): S="static_pointer_cast<"+newTypeStr+">("+toCvtStr+")"
                elif(varOwner=='my'):  S="static_pointer_cast<"+newTypeStr+">("+toCvtStr+")"
                elif(varOwner=='me'):  S="static_cast<"+newTypeStr+">("+toCvtStr+")"
                else: cdErr("Casting that to "+str(newTypeStr)+" is not yet supported.")
                retType = newTypeStr
                retOwner= varOwner

    else: # Not parameters, i.e., not a function
        if(funcName=='self'):
            S+='this'

    return [S, retOwner, retType]

def checkIfSpecialAssignmentFormIsNeeded(AltIDXFormat, RHS, rhsType):
    return ""

############################################
def codeMain(classes, tags, objsRefed, xlator):
    cdlog(3, "\n            Generating GLOBAL...")
    if("GLOBAL" in classes[1]):
        if(classes[0]["GLOBAL"]['stateType'] != 'struct'):
            print "ERROR: GLOBAL must be a 'struct'."
            exit(2)
        [structCode, funcCode, globalFuncs]=codeStructFields(classes, "GLOBAL", tags, '', objsRefed, xlator)
        if(funcCode==''): funcCode="// No main() function.\n"
        if(structCode==''): structCode="// No Main Globals.\n"
        funcCode = "\n\n"+funcCode
        return ["\n\n// Globals\n" + structCode + "\n// Global Functions\n" + globalFuncs, funcCode]
    return ["// No Main Globals.\n", "// No main() function defined.\n"]

def codeArgText(argFieldName, argType, xlator):
    return argType + " " +argFieldName

def codeStructText(classes, attrList, parentClass, classInherits, classImplements, structName, structCode, tags):
    if parentClass != "":
        parentClass = parentClass.replace('::', '_')
        parentClass = progSpec.unwrapClass(classes, structName)
        parentClass=': public '+parentClass+' '
        print "Warning: old style inheritance used: " , parentClass
    if classImplements!=None:
        print "Error: Implements found for: " , parentClass
        exit(1)
    if classInherits!=None:
        parentClass=': public '
        count =0
        for item in classInherits[0]:
            if count>0:
                parentClass+= ', '
            parentClass+= progSpec.unwrapClass(classes, item)
            count += 1
        #print "parentClass" , parentClass
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

def addSpecialCode(filename):
    S='\n\n//////////// C++ specific code:\n'
    S += "\n\nusing namespace std;\n\n"
    S += 'const string filename = "' + filename + '";\n'
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

    string getFilesDirAsString(){
        //string fileDir = "~/."+filename ";
        string fileDir = "./assets";

        mkdir(fileDir.data(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
        return (fileDir);
    }

    bool doesFileExist(string filePath){
        ifstream ifile(filename);
        return (bool)ifile;
    }

    void copyAssetToWritableFolder(string fromPath, string toPath){
        //TODO: finish func body if package C++
    }

    string joinCmdStrings(int count , char *argv[]) {
        string acc="";
        for(int i=1; i<count; ++i){
            if(i>1) acc+=" ";
            acc += argv[i];
        }
        return(acc);
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
        file.read((char*)S.c_str(), S.length());
        return S;  //No errors
    }

    """
    appendGlobalFuncAcc(decl, defn)

    return S

def addGLOBALSpecialCode(classes, tags, xlator):
    specialCode =''

    GLOBAL_CODE="""
struct GLOBAL{
    %s
}
    """ % (specialCode)

    #codeDogParser.AddToObjectFromText(classes[0], classes[1], GLOBAL_CODE )

def codeNewVarStr (classes, typeSpec, varName, fieldDef, indent, objsRefed, xlator):
    #TODO: make test case
    [fieldType, innerType] = xlator['convertType'](classes, typeSpec, 'var', xlator)
    varDeclareStr=''
    assignValue=''
    if(fieldDef['value']):
        [S2, rhsType]=xlator['codeExpr'](fieldDef['value'][0], objsRefed, None, xlator)
        [leftMod, rightMod]=chooseVirtualRValOwner(typeSpec, rhsType)
        assignValue = " = " + leftMod+S2+rightMod

    else: # If no value was given:
        CPL=''
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
            if(assignValue==''):
                owner = progSpec.getTypeSpecOwner(typeSpec)
                assignValue = ' = '+getCodeAllocStr(innerType, owner)+CPL
    varDeclareStr= fieldType + " " + varName + assignValue
    return(varDeclareStr)

def codeRangeSpec(traversalMode, ctrType, repName, S_low, S_hi, indent, xlator):
    if(traversalMode=='Forward' or traversalMode==None):
        S = indent + "for("+ctrType+" " + repName+'='+ S_low + "; " + repName + "!=" + S_hi +"; "+ xlator['codeIncrement'](repName) + "){\n"
    elif(traversalMode=='Backward'):
        S = indent + "for("+ctrType+" " + repName+'='+ S_hi + "-1; " + repName + ">=" + S_low +"; --"+ repName + "){\n"
    return (S)

def iterateRangeContainerStr(classes,localVarsAllocated, StartKey, EndKey,containerType,ContainerOwner,repName,repContainer,datastructID,keyFieldType,indent,xlator):
    willBeModifiedDuringTraversal=True   # TODO: Set this programatically later.
    actionText = ""
    loopCounterName = ""
    containedType=containerType['fieldType']
    if progSpec.ownerIsPointer(ContainerOwner): connector="->"
    else: connector = "."
    ctrlVarsTypeSpec = {'owner':containerType['owner'], 'fieldType':containedType}

    if datastructID=='multimap' or datastructID=='map':
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType, 'codeConverter':(repName+'.first')}
        localVarsAllocated.append([repName+'_key', keyVarSpec])  # Tracking local vars for scope
        ctrlVarsTypeSpec['codeConverter'] = (repName+'.second')

        localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
        actionText += (indent + "for( auto " + repName+'Itr ='+ repContainer+connector+'lower_bound('+StartKey+')' + "; " + repName + "Itr !=" + repContainer+connector+'upper_bound('+EndKey+')' +"; ++"+ repName + "Itr ){\n"
                    + indent+"    "+"auto "+repName+" = *"+repName+"Itr;\n")

    elif datastructID=='list' or (datastructID=='deque' and not willBeModifiedDuringTraversal):
        pass;
    elif datastructID=='deque' and willBeModifiedDuringTraversal:
        pass;
    else:
        print "DSID:",datastructID,containerType
        exit(2)

    return [actionText, loopCounterName]

def iterateContainerStr(classes,localVarsAllocated,containerType,repName,repContainer,datastructID,keyFieldType,ContainerOwner,isBackward,indent,xlator):
    #TODO: handle isBackward
    willBeModifiedDuringTraversal=True   # TODO: Set this programatically leter.
    actionText = ""
    loopCounterName = ""
    owner=containerType['owner']
    containedType=containerType['fieldType']
    ctrlVarsTypeSpec = {'owner':owner, 'fieldType':containedType}
    [LDeclP, RDeclP, LDeclA, RDeclA] = ChoosePtrDecorationForSimpleCase(ContainerOwner)
    if datastructID=='multimap' or datastructID=='map':
        keyVarSpec = {'owner':'me', 'fieldType':containedType, 'codeConverter':(repName+'.first')}
        localVarsAllocated.append([repName+'_key', keyVarSpec])  # Tracking local vars for scope
        ctrlVarsTypeSpec['codeConverter'] = (repName+'.second')

        localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
        actionText += (indent + "for( auto " + repName+'Itr ='+ repContainer+RDeclP+'begin()' + "; " + repName + "Itr !=" + repContainer+RDeclP+'end()' +"; ++"+ repName + "Itr ){\n"
                    + indent+"    "+"auto "+repName+" = *"+repName+"Itr;\n")

    elif datastructID=='list' or (datastructID=='deque' and not willBeModifiedDuringTraversal):
        loopCounterName=repName+'_key'
        keyVarSpec = {'owner':owner, 'fieldType':containedType}
        localVarsAllocated.append([loopCounterName, keyVarSpec])  # Tracking local vars for scope

        localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
        actionText += (indent + "for( auto " + repName+'Itr ='+ repContainer+RDeclP+'begin()' + "; " + repName + "Itr !=" + repContainer+RDeclP+'end()' +"; ++"+ repName + "Itr ){\n"
                    + indent+"    "+"auto "+repName+" = *"+repName+"Itr;\n")
    elif datastructID=='deque' and willBeModifiedDuringTraversal:
        loopCounterName=repName+'_key'
        keyVarSpec = {'owner':'me', 'fieldType':'uint64_t'}
        localVarsAllocated.append([loopCounterName, keyVarSpec])  # Tracking local vars for scope

        localVarsAllocated.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
        lvName=repName+"Idx"
        actionText += (indent + "for( uint64_t " + lvName+' = 0; ' + lvName+" < " +  repContainer+RDeclP+'size();' +" ++"+lvName+" ){\n"
                    + indent+"    "+"auto &"+repName+" = "+LDeclA+repContainer+RDeclA+"["+lvName+"];\n")
    else:
        cdErr("DSID:" + datastructID + ', ' +containerType)

    return [actionText, loopCounterName]

def codeIncrement(varName):
    return "++" + varName

def codeDecrement(varName):
    return "--" + varName

def codeVarFieldRHS_Str(name,  convertedType, fieldOwner, paramList, objsRefed, xlator):
    fieldValueText=""
    #TODO: make test case
    if paramList!=None:
        [CPL, paramTypeList] = codeParameterList(name, paramList, None, objsRefed, xlator)
        fieldValueText += CPL
    return fieldValueText

def codeConstField_Str(convertedType, fieldName, fieldValueText, className, indent, xlator ):
    if className=='GLOBAL':
        defn = indent + convertedType + ' ' + fieldName + fieldValueText +';\n';
        decl = ''
    else:
        defn = indent + convertedType + ' ' + fieldName +';\n'
        decl = convertedType[7:] + ' ' + progSpec.flattenObjectName(className) + "::"+ fieldName + fieldValueText +';\n\n'
    return [defn, decl]

def codeVarField_Str(convertedType, innerType, typeSpec, fieldName, fieldValueText, className, tags, indent):
    #TODO: make test case
    fieldOwner=progSpec.getTypeSpecOwner(typeSpec)
    if fieldOwner=='we':
        defn = indent + convertedType + ' ' + fieldName +';\n'
        decl = convertedType[7:] + ' ' + progSpec.flattenObjectName(className) + "::"+ fieldName + fieldValueText +';\n\n'
    else:
        defn = indent + convertedType + ' ' + fieldName + fieldValueText +';\n'
        decl = ''
    return [defn, decl]

def codeConstructorHeader(ClassName, constructorArgs, constructorInit, copyConstructorArgs, xlator):
    return "    " + ClassName + "(" + constructorArgs+")"+constructorInit+"{};\n"

def codeConstructorInit(fieldName, count, defaultVal, xlator):
    if (count > 0):
        return "," + fieldName+"("+" _"+fieldName+")"
    elif(count == 0):
        return ":" + fieldName+"("+" _"+fieldName+")"
    else:
        cdErr("Error in codeConstructorInit.")

def codeConstructorArgText(argFieldName, count, argType, defaultVal, xlator):
    if defaultVal == "NULL":
        defaultVal = "0"
    return argType + "  _" +argFieldName + "=" + defaultVal

def codeCopyConstructor(fieldName, convertedType, xlator):
    return ""

def codeFuncHeaderStr(className, fieldName, typeDefName, argListText, localArgsAllocated, inheritMode, indent):
    structCode=''; funcDefCode=''; globalFuncs='';
    if(className=='GLOBAL'):
        if fieldName=='main':
            funcDefCode += 'int main(int argc, char *argv[])'
            localArgsAllocated.append(['argc', {'owner':'me', 'fieldType':'int', 'arraySpec':None,'argList':None}])
            localArgsAllocated.append(['argv', {'owner':'their', 'fieldType':'char', 'arraySpec':None,'argList':None}])  # TODO: Wrong. argv should be an array.
        else:
            globalFuncs += typeDefName +' ' + fieldName +"("+argListText+")"
    else:
        if inheritMode=='normal' or inheritMode=='override':
            structCode += indent + typeDefName +' ' + fieldName +"("+argListText+");\n";
            objPrefix = progSpec.flattenObjectName(className) +'::'
            funcDefCode += typeDefName +' ' + objPrefix + fieldName +"("+argListText+")"
        elif inheritMode=='virtual':
            structCode += indent + 'virtual '+typeDefName +' ' + fieldName +"("+argListText +");\n";
            objPrefix = progSpec.flattenObjectName(className) +'::'
            funcDefCode += typeDefName +' ' + objPrefix + fieldName +"("+argListText+")"
        elif inheritMode=='pure-virtual':
            #print "PARMS: ", "'"+str(fieldName)+"'",  "'"+str(typeDefName)+"'", "'"+str(argListText)+"'"
            structCode += indent + 'virtual '+typeDefName +' ' + fieldName +"("+argListText +") = 0;\n";
        else: cdErr("Invalid inherit mode found: "+inheritMode)
        if funcDefCode[:7]=="static ": funcDefCode=funcDefCode[7:]
    return [structCode, funcDefCode, globalFuncs]

def extraCodeForTopOfFuntion(argList):
    return ''

def codeArrayIndex(idx, containerType, LorR_Val, previousSegName):
    S= '[' + idx +']'
    return S

def codeSetBits(LHS_Left, LHS_FieldType, prefix, bitMask, RHS, rhsType):
    if (LHS_FieldType =='flag' ):
        return "SetBits("+LHS_Left+"flags, "+prefix+bitMask+", ("+ RHS +")?"+prefix+bitMask+":0" + ");\n"
    elif (LHS_FieldType =='mode' ):
        return "SetBits("+LHS_Left+"flags, "+prefix+bitMask+"Mask, "+ RHS+"<<" +prefix+bitMask+"Offset"+");\n"

def codeSwitchBreak(caseAction, indent, xlator):
    return indent+"    break;\n"

def applyTypecast(typeInCodeDog, itemToAlterType):
    platformType = adjustBaseTypes(typeInCodeDog)
    return '('+platformType+')'+itemToAlterType;

#######################################################

def includeDirective(libHdr):
    S = '#include <'+libHdr+'>\n'
    return S

def generateMainFunctionality(classes, tags):
    # TODO: Some deInitialize items should automatically run during abort().
    # TODO: System initCode should happen first in initialize, last in deinitialize.

    runCode = progSpec.fetchTagValue(tags, 'runCode')
    mainFuncCode="""
    me int32: main(me int32: argc, their char: argv ) <- {
        initialize(joinCmdStrings(argc, argv))
        """ + runCode + """
        deinitialize()
        endFunc()
    }

"""
    progSpec.addObject(classes[0], classes[1], 'GLOBAL', 'struct', 'SEQ')
    codeDogParser.AddToObjectFromText(classes[0], classes[1], progSpec.wrapFieldListInObjectDef('GLOBAL',  mainFuncCode ), "C++ main()")


def fetchXlators():
    xlators = {}

    xlators['LanguageName']          = "C++"
    xlators['BuildStrPrefix']        = "g++ -g -std=gnu++14  "
    xlators['fileExtension']         = ".cpp"
    xlators['typeForCounterInt']     = "int64_t"
    xlators['GlobalVarPrefix']       = ""
    xlators['PtrConnector']          = "->"                      # Name segment connector for pointers.
    xlators['ObjConnector']          = "::"                      # Name segment connector for classes.
    xlators['NameSegConnector']      = "."
    xlators['NameSegFuncConnector']  = "."
    xlators['doesLangHaveGlobals']   = "True"
    xlators['funcBodyIndent']        = ""
    xlators['funcsDefInClass']       = "False"
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
