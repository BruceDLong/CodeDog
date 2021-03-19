#xlator_Swift.py
import progSpec
import codeDogParser
from progSpec import cdlog, cdErr, isStruct
from codeGenerator import codeItemRef, codeUserMesg, codeStructFields, codeAllocater, appendGlobalFuncAcc, codeParameterList, makeTagText, codeAction, codeExpr

###### Routines to track types of identifiers and to look up type based on identifier.
def getContainerType(typeSpec, actionOrField):
    idxType=''
    if progSpec.isNewContainerTempFunc(typeSpec):
        containerTypeSpec = progSpec.getContainerSpec(typeSpec)
        if 'owner' in containerTypeSpec: owner=progSpec.getOwnerFromTypeSpec(containerTypeSpec)
        else: owner='me'
        if 'indexType' in containerTypeSpec:
            if 'IDXowner' in containerTypeSpec['indexType']:
                idxOwner=containerTypeSpec['indexType']['IDXowner'][0]
                idxType=containerTypeSpec['indexType']['idxBaseType'][0][0]
                idxType=applyOwner(idxOwner, idxType, '')
            else:
                idxType=containerTypeSpec['indexType']['idxBaseType'][0][0]
        else:
            idxType = progSpec.getFieldType(typeSpec)
        adjustBaseTypes(idxType, True)
        if(isinstance(containerTypeSpec['datastructID'], str)):
            datastructID = containerTypeSpec['datastructID']
        else:   # it's a parseResult
            datastructID = containerTypeSpec['datastructID'][0]
    elif progSpec.isOldContainerTempFunc(typeSpec): print("Deprecated container type:", typeSpec); exit(2);
    else:
        owner = progSpec.getOwnerFromTypeSpec(typeSpec)
        datastructID = 'None'
    return [datastructID, idxType, owner]

def adjustBaseTypes(fieldType, isContainer):
    if(isinstance(fieldType, str)):
        if(fieldType=='uint8' or fieldType=='uint16'or fieldType=='uint32'): return 'UInt32'
        elif(fieldType=='int8' or fieldType=='int16' or fieldType=='int32'): return 'Int32'
        elif(fieldType=='uint64'): return 'UInt64'
        elif(fieldType=='int64'):  return 'Int64'
        elif(fieldType=='int'):    return 'Int'
        elif(fieldType=='bool'):   return 'Bool'
        elif(fieldType=='void'):   return 'Void'
        elif(fieldType=='float'):  return 'Float'
        elif(fieldType=='double'): return 'Double'
        elif(fieldType=='string'): return 'String'
        elif(fieldType=='char'):   return 'Character'
        langType=progSpec.flattenObjectName(fieldType)
    else: langType=progSpec.flattenObjectName(fieldType[0])
    return langType

def applyOwner(owner, langType, varMode):
    if owner=='me':
        langType = langType
    elif owner=='my':
        langType = langType
    elif owner=='our':
        langType = langType
    elif owner=='their':
        langType = langType
    elif owner=='itr':
        langType += '::iterator'
    elif owner=='const':
        langType = langType
    elif owner=='we':
        langType += 'public static'
    else:
        langType = ''
    return langType

def getUnwrappedClassOwner(classes, typeSpec, fieldType, varMode, ownerIn):
    ownerOut = ownerIn
    owner=typeSpec['owner']
    baseType = progSpec.isWrappedType(classes, fieldType)
    if baseType!=None:  # TODO: When this is all tested and stable, un-hardcode and optimize this!!!!!
        if 'ownerMe' in baseType:
            if owner=='their':
                if varMode=='arg': owner='their'
                else: owner = 'their'
            elif owner=='me':
                owner = 'their'
        else:
            if varMode=='var':owner=baseType['owner']   # TODO: remove this condition: accomodates old list type generated in stringStructs
            else: owner=ownerIn
    return owner

def xlateLangType(classes, typeSpec, owner, fieldType, varMode, xlator):
    # varMode is 'var' or 'arg' or 'alloc'. Large items are passed as pointers
    if progSpec.isOldContainerTempFunc(typeSpec): print("Deprecated container type:", typeSpec); exit(2);
    fieldAttrs=''
    if(isinstance(fieldType, str)):
        langType = adjustBaseTypes(fieldType, progSpec.isNewContainerTempFunc(typeSpec))
    else: langType = progSpec.flattenObjectName(fieldType[0])
    langType = applyOwner(owner, langType, varMode)
    if langType=='TYPE ERROR': print(langType, owner, fieldType);
    InnerLangType = langType
    reqTagList = progSpec.getReqTagList(typeSpec)
    if(reqTagList != None):
        reqTagString = "<"
        count = 0
        for reqTag in reqTagList:
            reqOwner = progSpec.getOwnerFromTemplateArg(reqTag)
            varTypeKeyword = progSpec.getTypeFromTemplateArg(reqTag)
            unwrappedOwner=getUnwrappedClassOwner(classes, typeSpec, varTypeKeyword, 'alloc', reqOwner)
            unwrappedTypeKeyword = progSpec.getUnwrappedClassFieldTypeKeyWord(classes, varTypeKeyword)
            reqType = adjustBaseTypes(unwrappedTypeKeyword, True)
            if(count>0):reqTagString += ", "
            reqTagString += reqType
            count += 1
        reqTagString += ">"
        langType += reqTagString
    if progSpec.isNewContainerTempFunc(typeSpec): return [langType, InnerLangType]
    if varMode != 'alloc': fieldAttrs = applyOwner(owner, langType, varMode)
    return [langType, fieldAttrs]   # E.g.: langType='uint', file

def convertType(classes, typeSpec, varMode, actionOrField, xlator):
    # varMode is 'var' or 'arg' or 'alloc'. Large items are passed as pointers
    ownerIn   = progSpec.getOwnerFromTypeSpec(typeSpec)
    fieldType = progSpec.getFieldTypeNew(typeSpec)
    if not isinstance(fieldType, str):
        fieldType=fieldType[0]
    unwrappedFieldTypeKeyWord = progSpec.getUnwrappedClassFieldTypeKeyWord(classes, fieldType)
    ownerOut=getUnwrappedClassOwner(classes, typeSpec, fieldType, varMode, ownerIn)
    retVal = xlateLangType(classes, typeSpec, ownerOut, unwrappedFieldTypeKeyWord, varMode, xlator)
    return retVal

def makePtrOpt(typeSpec):
    # Make pointer field variables optionals
    if progSpec.typeIsPointer(typeSpec): return('!')
    return('')

def codeIteratorOperation(itrCommand, fieldType):
    result = ''
    if itrCommand=='goNext':  result='%0.next()'
    elif itrCommand=='goPrev':result='%0.Swift ERROR!'
    elif itrCommand=='key':   result='%0.getKey()'
    elif itrCommand=='val':   result='%0.getValue()'
    return result

def recodeStringFunctions(name, typeSpec):
    if name == "size":
        typeSpec['codeConverter']='%0.count'
        typeSpec['fieldType']='int'
    elif name == "subStr":
        typeSpec['codeConverter']='substring(from:%1, to:%2)'
    #elif name == "append": name='append'

    return [name, typeSpec]

def langStringFormatterCommand(fmtStr, argStr):
    S='String(format:'+'"'+ fmtStr +'"'+ argStr +')'
    return S

def LanguageSpecificDecorations(classes, S, typeSpec, owner, LorRorP_Val, isLastSeg, xlator):
    if typeSpec!= 0 and progSpec.typeIsPointer(typeSpec) and typeSpec['owner']!='itr' and not 'codeConverter' in typeSpec:
        if LorRorP_Val == "PARAM":
            if  S=="nil":
                [paramType, innerType] = convertType(classes, typeSpec, 'arg', '', xlator)        #"RBNode<keyType, valueType>"
                S = 'Optional<'+paramType+'>.none'
        elif S!='NULL' and S[-1]!=']' and S[-1]!=')' and S!='self' and not(LorRorP_Val =="LVAL" and isLastSeg):
            S+='!'  # optionals
    return S

def checkForTypeCastNeed(lhsTypeSpec, rhsTypeSpec, RHScodeStr):
    LHS_KeyType = progSpec.fieldTypeKeyword(lhsTypeSpec)
    RHS_KeyType = progSpec.fieldTypeKeyword(rhsTypeSpec)
    if LHS_KeyType == 'bool'or LHS_KeyType == 'boolean':
        if progSpec.typeIsPointer(rhsTypeSpec):
            return '(' + RHScodeStr + ' == nil)'
        if (RHS_KeyType=='int' or RHS_KeyType=='flag'):
            if RHScodeStr[0]=='!': return '(' + codeStr[1:] + ' == 0)'
            else: return '(' + RHScodeStr + ' != 0)'
        if RHScodeStr == "0": return "false"
        if RHScodeStr == "1": return "true"
    elif LHS_KeyType == 'uint64' and RHS_KeyType=='int':
        RHScodeStr = 'UInt64('+RHScodeStr+')'
    elif LHS_KeyType == 'double' and RHS_KeyType=='int':
        RHScodeStr = 'Double('+RHScodeStr+')'
    elif LHS_KeyType == 'int' and RHS_KeyType=='char':
        RHScodeStr = RHScodeStr+'.asciiValue'
    elif LHS_KeyType == 'string' and RHS_KeyType=='char':
        RHScodeStr = "String(" + RHScodeStr+ ")"
    #elif LHS_KeyType != RHS_KeyType and LHS_KeyType != "mode" and LHS_KeyType != "flag" and RHS_KeyType != "ERROR" and LHS_KeyType != "struct" and LHS_KeyType != "bool":
    return RHScodeStr

def getTheDerefPtrMods(itemTypeSpec):
    if itemTypeSpec!=None and isinstance(itemTypeSpec, dict) and 'owner' in itemTypeSpec:
        if progSpec.typeIsPointer(itemTypeSpec):
            owner=progSpec.getTypeSpecOwner(itemTypeSpec)
            if owner=='itr':
                containerType = itemTypeSpec['arraySpec'][2]
                if containerType =='map' or containerType == 'multimap':
                    return ['', '->value', False]
            return ['', '', False]
    return ['', '', False]

def derefPtr(varRef, itemTypeSpec):
    if varRef=='NULL': return varRef
    [leftMod, rightMod, isDerefd] = getTheDerefPtrMods(itemTypeSpec)
    S = leftMod + varRef + rightMod
    return [S, isDerefd]

def chooseVirtualRValOwner(LVAL, RVAL):
    # Returns left and right text decorations for RHS of function arguments, return values, etc.
    if RVAL==0 or RVAL==None or isinstance(RVAL, str): return ['',''] # This happens e.g., string.size() # TODO: fix this.
    if LVAL==0 or LVAL==None or isinstance(LVAL, str): return ['', '']
    LeftOwner =progSpec.getTypeSpecOwner(LVAL)
    RightOwner=progSpec.getTypeSpecOwner(RVAL)
    if LeftOwner == RightOwner: return ["", ""]
    if LeftOwner!='itr' and RightOwner=='itr': return ["", ".value"]
    if LeftOwner=='me' and progSpec.typeIsPointer(RVAL): return ['', '']
    if progSpec.typeIsPointer(LVAL) and RightOwner=='me': return ['', '']
    #if LeftOwner=='their' and (RightOwner=='our' or RightOwner=='my'): return ['','.get()']
    return ['','']

def determinePtrConfigForNewVars(lhsTypeSpec, rhsTypeSpec, useCtor):
    return["", ""]

def determinePtrConfigForAssignments(LVAL, RVAL, assignTag, codeStr):
    #TODO: make test case
    # Returns left and right text decorations for both LHS and RHS of assignment
    if RVAL==0 or RVAL==None or isinstance(RVAL, str): return ['','',  '',''] # This happens e.g., string.size() # TODO: fix this.
    if LVAL==0 or LVAL==None or isinstance(LVAL, str): return ['','',  '','']
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

def getCodeAllocStr(varTypeStr, owner):
    if(owner=='our'): S=varTypeStr
    elif(owner=='my'): S=varTypeStr
    elif(owner=='their'): S=varTypeStr
    elif(owner=='me'): print("ERROR: Cannot allocate a 'me' variable."); exit(1);
    elif(owner=='const'): print("ERROR: Cannot allocate a 'const' variable."); exit(1);
    else: print("ERROR: Cannot allocate variable because owner is", owner+"."); exit(1);
    return S

def getCodeAllocSetStr(varTypeStr, owner, value):
    S=getCodeAllocStr(varTypeStr, owner)
    S+='('+value+')'
    return S

def getConstIntFieldStr(fieldName, fieldValue):
    S= "static let "+fieldName+ ": Int = " + fieldValue+ ";\n"
    return(S)

def getEnumStr(fieldName, enumList):
    S = ''
    count=0
    for enumName in enumList:
        S += "    " + getConstIntFieldStr(enumName, str(count))
        count=count+1
    S += "\n"
    return(S)

###################################################### CONTAINERS
def getContainerTypeInfo(classes, containerType, name, idxType, typeSpecIn, paramList, xlator):
    convertedIdxType = ""
    typeSpecOut = typeSpecIn
    if progSpec.isNewContainerTempFunc(typeSpecIn): return(name, typeSpecOut, paramList, convertedIdxType)
    if progSpec.isOldContainerTempFunc(typeSpecIn): print("Deprecated container type:", typeSpecIn); exit(2);
    return(name, typeSpecOut, paramList, convertedIdxType)

def codeArrayIndex(idx, containerType, LorR_Val, previousSegName, idxTypeSpec):
    if (containerType == 'string'):
        S= '[index: '+idx+']'
    else:
        S= '[' + idx +']'
    return S
###################################################### CONTAINER REPETITIONS
def codeRangeSpec(traversalMode, ctrType, repName, S_low, S_hi, indent, xlator):
    if(traversalMode=='Forward' or traversalMode==None):
        S = indent + "for "+ repName+' in '+ S_low + "..<Int(" + S_hi + ") {\n"
    elif(traversalMode=='Backward'):
        S = indent + "for("+ctrType+" " + repName+'='+ S_hi + "-1; " + repName + ">=" + S_low +"; "+ repName + "-=1){\n"
    return (S)

def iterateRangeContainerStr(classes,localVarsAlloc, StartKey, EndKey, containerType, containerOwner,repName,repContainer,datastructID,keyFieldType,indent,xlator):
    willBeModifiedDuringTraversal=True   # TODO: Set this programatically leter.
    actionText       = ""
    loopCounterName  = ""
    containedType    = progSpec.getFieldTypeNew(containerType)
    containerOwner   = progSpec.getOwnerFromTypeSpec(containerType)
    ctrlVarsTypeSpec = {'owner':containerOwner, 'fieldType':containedType}

    if datastructID=='multimap' or datastructID=='map':
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType, 'codeConverter':(repName+'.first')}
        localVarsAlloc.append([repName+'_key', keyVarSpec])  # Tracking local vars for scope
        ctrlVarsTypeSpec['codeConverter'] = (repName+'.second')
        localVarsAlloc.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
        actionText += (indent + "for( auto " + repName+'Itr ='+ repContainer+'->lower_bound('+StartKey+')' + "; " + repName + "Itr !=" + repContainer+'->upper_bound('+EndKey+')' +"; ++"+ repName + "Itr ){\n"
                    + indent+"    "+"auto "+repName+" = *"+repName+"Itr;\n")

    elif datastructID=='list' or (datastructID=='list' and not willBeModifiedDuringTraversal):
        pass;
    elif datastructID=='list' and willBeModifiedDuringTraversal:
        pass;
    else:
        print("DSID iterateRangeContainerStr:",datastructID,containerType)
        exit(2)
    return [actionText, loopCounterName]

def iterateContainerStr(classes,localVarsAlloc,containerType,repName,containerName,datastructID,indexTypeKeyWord,containerOwner,isBackward,actionOrField, indent,xlator):
    willBeModifiedDuringTraversal=True   # TODO: Set this programatically leter.
    actionText       = ""
    loopCounterName  = repName+'_key'
    containedType    = progSpec.getContainerFirstElementType(containerType)
    ctrlVarsTypeSpec = {'owner':containerType['owner'], 'fieldType':containedType}
    indexTypeKeyWord = adjustBaseTypes(indexTypeKeyWord, False)
    if datastructID=='multimap' or datastructID=='map' or datastructID=='Swift_Map':
        keyVarSpec = {'owner':containerType['owner'], 'fieldType':containedType, 'codeConverter':(repName+'.key')}
        ctrlVarsTypeSpec['codeConverter'] = (repName+'.value')
        actionText += (indent + "for " + repName+' in '+ containerName + " {\n")
    elif datastructID=='list' or datastructID=='Swift_Array':
        if willBeModifiedDuringTraversal:
            containedOwner = progSpec.getOwnerFromTypeSpec(containerType)
            keyVarSpec     = {'owner':containedOwner, 'fieldType':containedType}
            [iteratorTypeStr, innerType]=convertType(classes, ctrlVarsTypeSpec, 'var', actionOrField, xlator)
            loopVarName=repName+"Idx";
            actionText += (indent + "for " + loopVarName + " in 0..<" +  containerName+".count {\n"
                        + indent+"var "+repName + ':' + indexTypeKeyWord + " = "+containerName+"["+loopVarName+"];\n")
        else:
            keyVarSpec = {'owner':'me', 'fieldType':'Int'}
            actionText += (indent + "for " + repName+' in '+ containerName + " {\n")
    else:
        print("DSID iterateContainerStr:",datastructID,containerType)
        exit(2)
    localVarsAlloc.append([loopCounterName, keyVarSpec])  # Tracking local vars for scope
    localVarsAlloc.append([repName, ctrlVarsTypeSpec]) # Tracking local vars for scope
    return [actionText, loopCounterName]
###################################################### EXPRESSION CODING
def codeFactor(item, objsRefed, returnType, expectedTypeSpec, xlator):
    ####  ( value | ('(' + expr + ')') | ('!' + expr) | ('-' + expr) | varRef("varFunRef"))
    #print('                  factor: ', item)
    S=''
    retTypeSpec='noType'
    item0 = item[0]
    #print("ITEM0=", item0, ">>>>>", item)
    if (isinstance(item0, str)):
        if item0=='(':
            [S2, retTypeSpec] = codeExpr(item[1], objsRefed, returnType, expectedTypeSpec, 'XVAL', xlator)
            S+='(' + S2 +')'
        elif item0=='!':
            [S2, retTypeSpec] = codeExpr(item[1], objsRefed, returnType, expectedTypeSpec, 'XVAL', xlator)
            if progSpec.varsTypeCategory(retTypeSpec) != 'bool':
                if S2[-1]=='!': S2=S2[:-1]   # Todo: Better detect this
                S2='('+S2+' != nil)'
                retTypeSpec='bool'
            else: S+='!' + S2
        elif item0=='-':
            [S2, retTypeSpec] = codeExpr(item[1], objsRefed, returnType, expectedTypeSpec, 'XVAL', xlator)
            S+='-' + S2
        elif item0=='[':
            tmp="["
            for expr in item[1:-1]:
                [S2, retTypeSpec] = codeExpr(expr, objsRefed, returnType, expectedTypeSpec, 'XVAL', xlator)
                if len(tmp)>1: tmp+=", "
                tmp+=S2
            tmp+="]"
            S+=tmp
        else:
            expected_KeyType = progSpec.varTypeKeyWord(expectedTypeSpec)
            if expected_KeyType == "BigInt":
                S += item0
                retTypeSpec='BigInt'
            elif expected_KeyType == "BigFloat":
                S += item0 + "_mpf"
                retTypeSpec='BigFloat'
            elif expected_KeyType == "BigFrac":
                S += item0 + "_mpq"
                retTypeSpec='BigFrac'
            elif(item0[0]=="'"):
                retTypeSpec='string'
                S+=codeUserMesg(item0[1:-1], xlator)
            elif (item0[0]=='"'):
                if returnType != None and returnType["fieldType"]=="char":
                    retTypeSpec='char'
                    innerS=item0[1:-1]
                    if len(innerS)==1:
                        S+="'"+item0[1:-1] +"'"
                    else:
                        cdErr("Characters must have exactly 1 character.")
                else:
                    S+='"'+item0[1:-1] +'"'
                    retTypeSpec='String'
            else:
                S+=item0;
                if item0=='false' or item0=='true':
                    retTypeSpec={'owner': 'literal', 'fieldType': 'bool'}
                if retTypeSpec == 'noType' and progSpec.isStringNumeric(item0):
                    retTypeSpec={'owner': 'literal', 'fieldType': 'numeric'}
                if retTypeSpec == 'noType' and progSpec.typeIsInteger(expected_KeyType):retTypeSpec=expected_KeyType
    else: # CODEDOG LITERALS
        if isinstance(item0[0], str):
            S+=item0[0]
            if '"' in S or "'" in S: retTypeSpec = 'string'
            if '.' in S: retTypeSpec = 'double'
            if isinstance(S, int): retTypeSpec = 'int64'
            else:  retTypeSpec = 'int32'
        else:
            [codeStr, retTypeSpec, prntType, AltIDXFormat]=codeItemRef(item0, 'RVAL', objsRefed, returnType, xlator)
            if(codeStr=="NULL"):
                codeStr="nil"
                retTypeSpec={'owner':"PTR"}
            S+=codeStr                                # Code variable reference or function call
    return [S, retTypeSpec]

def codeTerm(item, objsRefed, returnType, expectedTypeSpec, xlator):
    #print('               term item:', item)
    [S, retTypeSpec]=codeFactor(item[0], objsRefed, returnType, expectedTypeSpec, xlator)
    if (not(isinstance(item, str))) and (len(item) > 1) and len(item[1])>0:
        [S, isDerefd]=derefPtr(S, retTypeSpec)
        for i in item[1]:
            #print '               term:', i
            if   (i[0] == '*'): S+=' * '
            elif (i[0] == '/'): S+=' / '
            elif (i[0] == '%'): S+=' % '
            else: print("ERROR: One of '*', '/' or '%' expected in code generator."); exit(2)
            [S2, retType2] = codeFactor(i[1], objsRefed, returnType, expectedTypeSpec, xlator)
            [S2, isDerefd]=derefPtr(S2, retType2)
            S+=S2
    return [S, retTypeSpec]

def codePlus(item, objsRefed, returnType, expectedTypeSpec, xlator):
    #print('            plus item:', item)
    [S, retTypeSpec]=codeTerm(item[0], objsRefed, returnType, expectedTypeSpec, xlator)
    if len(item) > 1 and len(item[1])>0:
        [S, isDerefd]=derefPtr(S, retTypeSpec)
        if isDerefd:
            keyType = progSpec.varTypeKeyWord(retTypeSpec)
            retTypeSpec={'owner': 'me', 'fieldType': keyType}
        for  i in item[1]:
            if   (i[0] == '+'): S+=' + '
            elif (i[0] == '-'): S+=' - '
            else: print("ERROR: '+' or '-' expected in code generator."); exit(2)
            [S2, retType2] = codeTerm(i[1], objsRefed, returnType, expectedTypeSpec, xlator)
            [S2, isDerefd]=derefPtr(S2, retType2)
            if i[0]=='+' and 'fieldType' in retType2 and retType2['fieldType']=='char':
                S2='String('+S2+')'
            S+=S2
    return [S, retTypeSpec]

def codeComparison(item, objsRefed, returnType, expectedTypeSpec, xlator):
    #print('         Comp item', item)
    [S, retTypeSpec]=codePlus(item[0], objsRefed, returnType, expectedTypeSpec, xlator)
    if len(item) > 1 and len(item[1])>0:
        if len(item[1])>1: print("Error: Chained comparisons.\n"); exit(1);
        [S, isDerefd]=derefPtr(S, retTypeSpec)
        for  i in item[1]:
            if   (i[0] == '<'): S+=' < '
            elif (i[0] == '>'): S+=' > '
            elif (i[0] == '<='): S+=' <= '
            elif (i[0] == '>='): S+=' >= '
            else: print("ERROR: One of <, >, <= or >= expected in code generator."); exit(2)
            [S2, retTypeSpec] = codePlus(i[1], objsRefed, returnType, expectedTypeSpec, xlator)
            [S2, isDerefd]=derefPtr(S2, retTypeSpec)
            S+=S2
            retTypeSpec='bool'
    return [S, retTypeSpec]

def codeIsEQ(item, objsRefed, returnType, expectedTypeSpec, xlator):
    #print('      IsEq item:', item)
    [S, retTypeSpec]=codeComparison(item[0], objsRefed, returnType, expectedTypeSpec, xlator)
    if len(item) > 1 and len(item[1])>0:
        if len(item[1])>1: print("Error: Chained == or !=.\n"); exit(1);
        if (isinstance(retTypeSpec, int)): cdlog(logLvl(), "Invalid item in ==: {}".format(item[0]))
        leftOwner=owner=progSpec.getTypeSpecOwner(retTypeSpec)
        [S_derefd, isDerefd] = derefPtr(S, retTypeSpec)
        for i in item[1]:
            if   (i[0] == '=='): op=' == '
            elif (i[0] == '!='): op=' != '
            elif (i[0] == '!=='): op=' !== '
            elif (i[0] == '==='): op=' === '
            else: print("ERROR: '==' or '!=' or '===' or '!==' expected."); exit(2)
            [S2, retTypeSpec] = codeComparison(i[1], objsRefed, returnType, expectedTypeSpec, xlator)
            rightOwner=progSpec.getTypeSpecOwner(retTypeSpec)
            if not( leftOwner=='itr' and rightOwner=='itr') and i[0] != '===':
                if (S2!='nil' ): S=S_derefd
                elif S[-1]=='!': S=S[:-1]   # Todo: Better detect this
                [S2, isDerefd]=derefPtr(S2, retTypeSpec)
            S+= op+S2
            retTypeSpec='bool'
    return [S, retTypeSpec]

######################################################
def adjustConditional(S2, conditionType):
    if conditionType!=None and not isinstance(conditionType, str):
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
    fieldType='void'   # default to void
    retOwner='me'    # default to 'me'
    funcName=segSpec[0]
    if(len(segSpec)>2):  # If there are arguments...
        paramList=segSpec[2]
        if(funcName=='print'):
            S+='print('
            count = 0
            for P in paramList:
                [S2, argType]=codeExpr(P[0], objsRefed, None, None, 'PARAM', xlator)
                if(count>0): S+=', '
                S+=S2
                count= count + 1
            S+=',separator:"", terminator:"")'
        elif(funcName=='AllocateOrClear'):
            [varName,  varTypeSpec]=codeExpr(paramList[0][0], objsRefed, None, None, 'PARAM', xlator)
            if(varTypeSpec==0): cdErr("Name is undefined: " + varName)
            if(varName[-1]=='!'): varNameUnRefed=varName[:-1]  # Remove a reference. It would be better to do this in codeExpr but may take some work.
            else: varNameUnRefed=varName
            S+='if('+varNameUnRefed+' != nil){'+varName+'.clear();} else {'+varName+" = "+codeAllocater(varTypeSpec, xlator)+"();}"
        elif(funcName=='Allocate'):
            [varName,  varTypeSpec]=codeExpr(paramList[0][0], objsRefed, None, None, 'PARAM', xlator)
            if(varTypeSpec==0): cdErr("Name is Undefined: " + varName)
            S+=varName+" = "+codeAllocater(varTypeSpec, xlator)+'('
            count=0   # TODO: As needed, make this call CodeParameterList() with modelParams of the constructor.
            for P in paramList[1:]:
                if(count>0): S+=', '
                [S2, argType]=codeExpr(P[0], objsRefed, None, None, 'PARAM', xlator)
                S+=S2
                count=count+1
            S+=")"
        elif(funcName=='callPeriodically'):
            [objName,  fieldType]=codeExpr(paramList[1][0], objsRefed, None, None, 'PARAM', xlator)
            [interval,  intSpec] = codeExpr(paramList[2][0], objsRefed, None, None, 'PARAM', xlator)
            varTypeSpec= fieldType['fieldType'][0]
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
                [S2, argType]=codeExpr(P[0][0], objsRefed, None, None, 'PARAM', xlator)
                S2=derefPtr(S2, argType)
                S+='to_string('+S2+')'
                returnType='string'
    else: # Not parameters, i.e., not a function
        if(funcName=='self'):
            S+='self'

    return [S, retOwner, fieldType]

def checkIfSpecialAssignmentFormIsNeeded(AltIDXFormat, RHS, rhsType, LHS, LHSParentType, LHS_FieldType):
    return ""

######################################################
def codeMain(classes, tags, objsRefed, xlator):
    cdlog(3, "\n            Generating GLOBAL...")
    if("GLOBAL" in classes[1]):
        if(classes[0]["GLOBAL"]['stateType'] != 'struct'):
            print("ERROR: GLOBAL must be a 'struct'.")
            exit(2)
        [structCode, funcCode, globalFuncs]=codeStructFields(classes, "GLOBAL", tags, '', objsRefed, xlator)
        if(funcCode==''): funcCode="// No main() function.\n"
        if(structCode==''): structCode="// No Main Globals.\n"
        funcCode = "\n\n"+funcCode+"\nmain();"
        return ["\n\n// Globals\n" + structCode + globalFuncs, funcCode]
    return ["// No Main Globals.\n", "// No main() function defined.\n"]

def codeArgText(argFieldName, argType, argOwner, typeSpec, makeConst, typeArgList, xlator):
    isTypeArg = False
    if typeArgList:
        for typeArg in typeArgList:
            if argType == typeArg: argType = "[" + argType + "]"
    fieldTypeMod = makePtrOpt(typeSpec)
    return "_ " + argFieldName + ": " + argType + fieldTypeMod

def codeStructText(classes, attrList, parentClass, classInherits, classImplements, structName, structCode, tags):
    classAttrs=''
    if len(attrList)>0:
        for attr in attrList:
            if attr[0]=='@': classAttrs += attr+' '
    if parentClass != "":
        parentClass = ': '+parentClass+' '
        parentClass = progSpec.getUnwrappedClassFieldTypeKeyWord(structName)
    if classInherits!=None:
        parentClass=': ' + classInherits[0][0]
    typeArgList = progSpec.getTypeArgList(structName)
    if(typeArgList != None):
        templateHeader = codeTemplateHeader(structName, typeArgList)+" "
        structName= structName+templateHeader
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

    func substring(from: Int, to:Int) -> String {
        return String(self[index(from: from)..<index(from: to)])
    }

    subscript(index value: Int) -> Element {
        get {
            let i = index(startIndex, offsetBy: value)
            return self[i]
        } set {
            var array = Array(self)
            array[value] = newValue
            self = String(array)
        }
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
        file.read((char*)S.c_str(), S.count);
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

    #codeDogParser.AddToObjectFromText(classes[0], classes[1], GLOBAL_CODE)
def variableDefaultValueString(fieldType, isTypeArg):
    if (fieldType == "String"):
        fieldValueText=' = ""'
    elif (fieldType.startswith("[")):
        fieldValueText=' = '+fieldType + '()'
    elif (fieldType == "Bool"):
        fieldValueText=' = false'
    elif (isNumericType(fieldType)):
        fieldValueText=' = 0'
    elif (fieldType == "Character"):
        fieldValueText=' = "\\0"'
    elif(isTypeArg):
        fieldValueText = ' = ['+fieldType +']()'
    else:
        fieldValueText = ' = ' + fieldType +'()'
    return fieldValueText

def codeNewVarStr(classes, lhsTypeSpec, varName, fieldDef, indent, objsRefed, actionOrField, xlator):
    varDeclareStr=''
    assignValue=''
    isAllocated = fieldDef['isAllocated']
    owner = progSpec.getTypeSpecOwner(lhsTypeSpec)
    useCtor = False
    if fieldDef['paramList'] and fieldDef['paramList'][-1] == "^&useCtor//8":
        del fieldDef['paramList'][-1]
        useCtor = True
    [fieldType, innerType]            = convertType(classes, lhsTypeSpec, 'var', actionOrField, xlator)
    [allocFieldType, allocFieldAttrs] = convertType(classes, lhsTypeSpec, 'alloc', '', xlator)
    if(fieldDef['value']):
        [RHS, rhsTypeSpec]=codeExpr(fieldDef['value'][0], objsRefed, None, None, 'RVAL', xlator)
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
                    print("\nPROBLEM: The return type of the parameter '", CPL, "' of "+varName+"(...) cannot be found and is needed. Try to define it.\n",   paramTypeList)
                    exit(1)
                rhsTypeSpec = paramTypeList[0]
                rhsType     = progSpec.getFieldType(rhsTypeSpec)
                # TODO: Remove the 'True' and make this check object heirarchies or similar solution
                if True or not isinstance(rhsType, str) and fieldType==rhsType[0]:
                    assignValue = " = " + CPL   # Act like a copy constructor
        else:
            assignValue = variableDefaultValueString(allocFieldType, False)
    fieldTypeMod = makePtrOpt(lhsTypeSpec)
    if (assignValue == ""):
        varDeclareStr= "var " + varName + ": "+ fieldType + fieldTypeMod + " = " + allocFieldType + '()'
    else:
        varDeclareStr= "var " + varName + ": "+ fieldType + fieldTypeMod + assignValue
    return(varDeclareStr)

def codeIncrement(varName):
    return varName + " += 1"

def codeDecrement(varName):
    return varName + " -= 1"

def isNumericType(convertedType):
    if(convertedType == "UInt32" or convertedType == "UInt64" or convertedType == "Float" or convertedType == "Int" or convertedType == "Int32" or convertedType == "Int64" or convertedType == "Double"):
        return True
    else:
        return False

def codeVarFieldRHS_Str(fieldName, convertedType, fieldType, fieldOwner, paramList, objsRefed, isAllocated, typeArgList, xlator):
    fieldValueText=""
    isTypeArg = False
    if typeArgList:
        for typeArg in typeArgList:
            if convertedType == typeArg: isTypeArg = True
    if paramList!=None:
        if paramList[-1] == "^&useCtor//8":
            del paramList[-1]
        [CPL, paramTypeList] = codeParameterList(fieldName, paramList, None, objsRefed, xlator)
        fieldValueText=" = " + convertedType + CPL
    else:
        fieldValueText = variableDefaultValueString(convertedType, isTypeArg)
    return fieldValueText

def codeConstField_Str(convertedType, fieldName, fieldValueText, className, indent, xlator ):
    defn = ''
    decl =  indent  + "let " + fieldName + ':'+ convertedType  + fieldValueText +';\n';
    return [defn, decl]

def codeVarField_Str(convertedType, typeSpec, fieldName, fieldValueText, className, tags, typeArgList, indent):
    # TODO: make test case
    fieldOwner=progSpec.getTypeSpecOwner(typeSpec)
    if fieldOwner=='we':
        defn = indent + "public static var "+ indent + fieldName + ": " +  convertedType  +  fieldValueText + '\n'
        decl = ''
    else:
        isTypeArg = False
        if typeArgList:
            for typeArg in typeArgList:
                if convertedType == typeArg: isTypeArg = True
        if isTypeArg: defn = indent + "var "+ fieldName + fieldValueText + '\n'
        else: defn = indent + "var "+ fieldName + ": " +  convertedType + fieldValueText + '\n'
        decl = ''
    return [defn, decl]

###################################################### CONSTRUCTORS
def codeConstructor(className, ctorArgs, callSuper, ctorInit, funcBody):
    if callSuper != '':
        callSuper = ':' + callSuper
        if ctorInit != '':
            callSuper = callSuper + ', '
    elif ctorInit != '':
        ctorInit = ': ' + ctorInit
    S = '    init(' + ctorArgs + ') {\n' + funcBody + '    };\n'
    return (S)

def codeConstructors(className, ctorArgs, ctorInit, copyCtorArgs, funcBody, callSuper, xlator):
    #TODO: Swift should only have constructors if they are called somewhere.
    if ctorArgs != "":
        S = "    init(" + ctorArgs+"){\n"+callSuper+ctorInit+funcBody+"    }\n"
    if callSuper != "":
        S += "    override init(){\n"+callSuper+funcBody+"    }\n"
    else:
        S += "    init(){\n"+callSuper+funcBody+"    }\n"
    return S

def codeConstructorInit(fieldName, count, defaultVal, xlator):
    return "        self." + fieldName +" = arg_"+fieldName+";\n"

def codeConstructorArgText(argFieldName, count, argType, defaultVal, xlator):
    if defaultVal == "NULL": defaultVal = ""
    if defaultVal: argType = argType + '=' + defaultVal
    return "_ arg_" + argFieldName  + ': ' +argType

def codeCopyConstructor(fieldName, convertedType, isTemplateVar, xlator):
    return ""

def codeConstructorCall(className):
    return '        __INIT_'+className+'();\n'

def codeSuperConstructorCall(parentClassName):
    return '        super.init();\n'

######################################################
def codeFuncHeaderStr(className, fieldName, returnType, argListText, localArgsAllocated, inheritMode, overRideOper, isConstructor, typeArgList, typeSpec, indent):
    #TODO: add \n before func
    structCode=''; funcDefCode=''; globalFuncs='';
    if typeArgList:
        for typeArg in typeArgList:
            if returnType == typeArg: returnType = '['+returnType+']'
    if returnType!='': returnType = '-> '+returnType
    if(className=='AppDelegate'):
        if fieldName=='application':
            structCode += '    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplicationLaunchOptionsKey: Any]?) -> Bool '
            localArgsAllocated.append(['application', {'owner':'me', 'fieldType':'UIApplication', 'arraySpec':None,'argList':None}])
            localArgsAllocated.append(['launchOptions', {'owner':'their', 'fieldType':'int', 'arraySpec':None,'argList':None}])  # TODO: Wrong. launchOptions should be an array.
        else:
            structCode +="func " + fieldName +"("+argListText+") " + returnType
    else:
        if fieldName=="init":
            fieldName = "__INIT_"+className
            structCode += indent + "func "  + fieldName +"("+argListText+")"
        else:
            if isConstructor:
                structCode += indent + "init "  +"("+argListText+") " + returnType
            else:
                fieldTypeMod = makePtrOpt(typeSpec)
                funcAttrs=''
                if inheritMode=='override': funcAttrs='override '
                structCode += indent + funcAttrs + "func " + fieldName +"("+argListText+") " + returnType + fieldTypeMod
    return [structCode, funcDefCode, globalFuncs]

def getVirtualFuncText(field):
    field['value'] = '{fatalError("Must Override")}'
    return field['value']+'\n'

def codeTemplateHeader(structName, typeArgList):
    templateHeader = "<"
    count = 0
    for typeArg in typeArgList:
        if(count>0):templateHeader+=", "
        templateHeader+=typeArg
        count+=1
    templateHeader+=">"
    return(templateHeader)

def extraCodeForTopOfFuntion(argList):
    if len(argList)==0:
        topCode=''
    else:
        topCode=""
        for arg in argList:
            argTypeSpec =arg['typeSpec']
            argFieldName=arg['fieldName']
            topCode+=  '        var '+argFieldName+' = '+argFieldName+'\n'
    return topCode

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
    platformType = adjustBaseTypes(typeInCodeDog, False)
    return platformType+'('+itemToAlterType+')';

######################################################

def includeDirective(libHdr):
    S = 'import '+libHdr+'\n'
    return S

def generateMainFunctionality(classes, tags):
    # TODO: Make initCode, runCode and deInitCode work better and more automated by patterns.
    # TODO: Some deInitialize items should automatically run during abort().
    # TODO: Deinitialize items should happen in reverse order.

    runCode = progSpec.fetchTagValue(tags, 'runCode')
    mainFuncCode="""
    me void: main() <- {
        //initialize()
        """ + runCode + """
        deinitialize()
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
    xlators['PtrConnector']          = "."                      # Name segment connector for pointers.
    xlators['ObjConnector']          = "."                      # Name segment connector for classes.
    xlators['NameSegConnector']      = "."
    xlators['NameSegFuncConnector']  = "()."
    xlators['doesLangHaveGlobals']   = "True"
    xlators['funcBodyIndent']        = "    "
    xlators['funcsDefInClass']       = "True"
    xlators['MakeConstructors']      = "True"
    xlators['funcsDefInClass']       = "True"
    xlators['blockPrefix']           = "do"
    xlators['usePrefixOnStatics']    = "True"
    xlators['iteratorsUseOperators'] = "False"
    xlators['renderGenerics']        = "True"
    xlators['renameInitFuncs']       = "True"
    xlators['codeIsEQ']                     = codeIsEQ
    xlators['derefPtr']                     = derefPtr
    xlators['applyOwner']                   = applyOwner
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
    xlators['codeConstructor']              = codeConstructor
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
    xlators['getVirtualFuncText']           = getVirtualFuncText
    return(xlators)
