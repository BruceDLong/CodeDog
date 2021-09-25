#xlator_Swift.py
import progSpec
import codeDogParser
from progSpec import cdlog, cdErr, isStruct
from codeGenerator import codeItemRef, codeUserMesg, codeStructFields, codeAllocater, appendGlobalFuncAcc, codeParameterList, codeAction, codeExpr, convertType, generateGenericStructName, getGenericTypeSpec, CheckObjectVars

###### Routines to track types of identifiers and to look up type based on identifier.
def getContainerType(typeSpec, actionOrField):
    idxType=''
    if progSpec.isNewContainerTempFunc(typeSpec):
        ctnrTSpec = progSpec.getContainerSpec(typeSpec)
        if 'owner' in ctnrTSpec: owner=progSpec.getOwnerFromTypeSpec(ctnrTSpec)
        else: owner = 'me'
        if 'indexType' in ctnrTSpec:
            if 'IDXowner' in ctnrTSpec['indexType']:
                idxOwner = ctnrTSpec['indexType']['IDXowner'][0]
                idxType  = ctnrTSpec['indexType']['idxBaseType'][0][0]
                idxType  = applyOwner(idxOwner, idxType, '')
            else:
                idxType=ctnrTSpec['indexType']['idxBaseType'][0][0]
        else:
            idxType = progSpec.getFieldType(typeSpec)
        if(isinstance(ctnrTSpec['datastructID'], str)):
            datastructID = ctnrTSpec['datastructID']
        else:   # it's a parseResult
            datastructID = ctnrTSpec['datastructID'][0]
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

def getReqTagString(classes, typeSpec):
    reqTagStr  = ""
    reqTagList = progSpec.getReqTagList(typeSpec)
    if(reqTagList != None):
        reqTagStr = "<"
        count = 0
        for reqTag in reqTagList:
            reqOwnr     = progSpec.getOwnerFromTemplateArg(reqTag)
            varTypeKW   = progSpec.getTypeFromTemplateArg(reqTag)
            unwrappedOwner=getUnwrappedClassOwner(classes, typeSpec, varTypeKW, 'alloc', reqOwnr)
            unwrappedKW = progSpec.getUnwrappedClassFieldTypeKeyWord(classes, varTypeKW)
            reqType     = adjustBaseTypes(unwrappedKW, True)
            if(count>0): reqTagStr += ", "
            reqTagStr += reqType
            count += 1
        reqTagStr += ">"
    return reqTagStr

def xlateLangType(classes, typeSpec, owner, fTypeKW, varMode, actionOrField):
    # varMode is 'var' or 'arg' or 'alloc'. Large items are passed as pointers
    innerType=''
    langType = adjustBaseTypes(fTypeKW, progSpec.isNewContainerTempFunc(typeSpec))
    langType = applyOwner(owner, langType, varMode)
    if langType=='TYPE ERROR': print(langType, owner, fTypeKW);
    innerType = langType
    if progSpec.isNewContainerTempFunc(typeSpec): return [langType, innerType]
    if varMode != 'alloc': innerType = applyOwner(owner, langType, varMode)
    return [langType, innerType]

def makePtrOpt(typeSpec):
    # Make pointer field variables optionals
    fTypeKW = progSpec.fieldTypeKeyword(typeSpec)
    if progSpec.typeIsPointer(typeSpec) and (fTypeKW != 'string' or fTypeKW != 'String'): return('!')
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

def LanguageSpecificDecorations(S, typeSpec, owner, LorRorP_Val, xlator):
    if typeSpec!= 0 and progSpec.typeIsPointer(typeSpec) and typeSpec['owner']!='itr' and not 'codeConverter' in typeSpec:
        if LorRorP_Val == "PARAM" and S=="nil":
            [cvrtType, innerType] = convertType(typeSpec, 'arg', '', genericArgs, xlator)
            S = 'Optional<'+cvrtType+'>.none'
    return S

def convertToInt(S, typeSpec):
    return S

def checkForTypeCastNeed(lhsTypeSpec, rhsTypeSpec, RHScodeStr):
    LTypeKW = progSpec.fieldTypeKeyword(lhsTypeSpec)
    RTypeKW = progSpec.fieldTypeKeyword(rhsTypeSpec)
    if LTypeKW == 'bool'or LTypeKW == 'boolean':
        if progSpec.typeIsPointer(rhsTypeSpec):
            return '(' + RHScodeStr + ' == nil)'
        if (RTypeKW=='int' or RTypeKW=='flag'):
            if RHScodeStr[0]=='!': return '(' + codeStr[1:] + ' == 0)'
            else: return '(' + RHScodeStr + ' != 0)'
        if RHScodeStr == "0": return "false"
        if RHScodeStr == "1": return "true"
    elif LTypeKW == 'uint64' and RTypeKW=='int':
        RHScodeStr = 'UInt64('+RHScodeStr+')'
    elif LTypeKW == 'double' and RTypeKW=='int':
        RHScodeStr = 'Double('+RHScodeStr+')'
    elif LTypeKW == 'int' and RTypeKW=='char':
        RHScodeStr = RHScodeStr+'.asciiValue'
    elif LTypeKW == 'string' and RTypeKW=='char':
        RHScodeStr = "String(" + RHScodeStr+ ")"
    #elif LTypeKW != RTypeKW and LTypeKW != "mode" and LTypeKW != "flag" and RTypeKW != "ERROR" and LTypeKW != "struct" and LTypeKW != "bool":
    return RHScodeStr

def getTheDerefPtrMods(itemTypeSpec):
    if itemTypeSpec!=None and isinstance(itemTypeSpec, dict) and 'owner' in itemTypeSpec:
        if progSpec.isNewContainerTempFunc(itemTypeSpec): return ['', '', False]
        if progSpec.typeIsPointer(itemTypeSpec):
            owner=progSpec.getTypeSpecOwner(itemTypeSpec)
            if progSpec.isAContainer(itemTypeSpec):
                if owner=='itr':
                    containerType = progSpec.getDatastructID(itemTypeSpec)
                    if containerType =='map' or containerType == 'multimap':
                        return ['', '', False]
                # OPTIONALS
                return ['', '!', False]
            else:
                if owner!='itr':
                    # OPTIONALS
                    return ['', '!', True]
    return ['', '', False]

def derefPtr(varRef, itemTypeSpec):
    if varRef=='NULL': return varRef
    [leftMod, rightMod, isDerefd] = getTheDerefPtrMods(itemTypeSpec)
    S = leftMod + varRef + rightMod
    return [S, isDerefd]

def ChoosePtrDecorationForSimpleCase(owner):
    if(owner=='our' or owner=='my' or owner=='their'):
        # OPTIONALS
        return ['','',  '', '!']
    else: return ['','',  '','']

def chooseVirtualRValOwner(LVAL, RVAL):
    # Returns left and right text decorations for RHS of function arguments, return values, etc.
    if RVAL==0 or RVAL==None or isinstance(RVAL, str): return ['',''] # This happens e.g., string.size() # TODO: fix this.
    if LVAL==0 or LVAL==None or isinstance(LVAL, str): return ['', '']
    LeftOwner =progSpec.getTypeSpecOwner(LVAL)
    RightOwner=progSpec.getTypeSpecOwner(RVAL)
    if LeftOwner == RightOwner: return ["", ""]
    if LeftOwner!='itr' and RightOwner=='itr':
        return ["", ""]
    if LeftOwner=='me' and progSpec.typeIsPointer(RVAL):
        return ['', '!']             # OPTIONALS
    if progSpec.typeIsPointer(LVAL) and RightOwner=='me':
        return ['', '']
    #if LeftOwner=='their' and (RightOwner=='our' or RightOwner=='my'): return ['','.get()']
    return ['','']

def determinePtrConfigForNewVars(LSpec, RSpec, useCtor):
    return ['','']

def determinePtrConfigForAssignments(LVAL, RVAL, assignTag, codeStr):
    #TODO: make test case
    # Returns left and right text decorations for both LHS and RHS of assignment
    if RVAL==0 or RVAL==None or isinstance(RVAL, str): return ['','',  '',''] # This happens e.g., string.size() # TODO: fix this.
    if LVAL==0 or LVAL==None or isinstance(LVAL, str): return ['','',  '','']
    LeftOwner =progSpec.getTypeSpecOwner(LVAL)
    RightOwner=progSpec.getTypeSpecOwner(RVAL)
    if not isinstance(assignTag, str):
        assignTag = assignTag[0]
    if progSpec.typeIsPointer(LVAL) and progSpec.typeIsPointer(RVAL):
        # OPTIONALS
        if assignTag=='deep' :return ['','!',  '','!']
        elif LeftOwner=='their' and (RightOwner=='our' or RightOwner=='my'): return ['','', '','']
        else: return ['','',  '', '']
    if LeftOwner == RightOwner: return ['','',  '','']
    if LeftOwner=='me' and progSpec.typeIsPointer(RVAL):
        [leftMod, rightMod, isDerefd] = getTheDerefPtrMods(RVAL)
        # OPTIONALS
        return ['','',  leftMod, rightMod]
    if progSpec.typeIsPointer(LVAL) and RightOwner=='me':
        # OPTIONALS
        if assignTag!="" or assignTag=='deep':return ['','!',  '', '']
        else: return ['','',  "", '']
    # OPTIONALS
    if progSpec.typeIsPointer(LVAL) and RightOwner=='literal':return ['','!',  '', '']
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

def getConstIntFieldStr(fieldName, fieldValue, intSize):
    S= "static let "+fieldName+ ": Int = " + fieldValue+ ";\n"
    return(S)

def getEnumStr(fieldName, enumList):
    S = ''
    count=0
    for enumName in enumList:
        S += "    " + getConstIntFieldStr(enumName, str(count), 32)
        count=count+1
    S += "\n"
    return(S)

def codeIdentityCheck(S, S2, retType1, retType2, opIn):
    if opIn == '===':
        return S+' === '+S2
    else:
        if   (opIn == '=='): opOut=' == '
        elif (opIn == '!='): opOut=' != '
        elif (opIn == '!=='): opOut=' !== '
        else: print("ERROR: '==' or '!=' or '===' or '!==' expected."); exit(2)
        [S_derefd, isDerefd] = derefPtr(S, retType1)
        if S2!='nil':
            S=S_derefd
            [S2, isDerefd]=derefPtr(S2, retType1)
        elif S[-1]=='!':
            S=S[:-1]   # Todo: Better detect this
        S+= opOut+S2
        return S

def codeComparisonStr(S, S2, retType1, retType2, op):
    if (op == '<'): S+=' < '
    elif (op == '>'): S+=' > '
    elif (op == '<='): S+=' <= '
    elif (op == '>='): S+=' >= '
    else: print("ERROR: One of <, >, <= or >= expected in code generator."); exit(2)
    S2 = adjustQuotesForChar(retType1, retType2, S2)
    [S2, isDerefd]=derefPtr(S2, retType2)
    S+=S2
    return S

###################################################### CONTAINERS
def getContaineCategory(containerSpec):
    fTypeKW = progSpec.fieldTypeKeyword(containerSpec)
    if fTypeKW=='multimap' or fTypeKW=='map' or fTypeKW=='Swift_Map' or 'RBTreeMap' in fTypeKW or "__Map_" in fTypeKW:
        return 'MAP'
    elif fTypeKW=='list' or fTypeKW=='Swift_Array' or "__List_" in fTypeKW:
        return 'LIST'
    return None

def getContainerTypeInfo(containerType, name, idxType, typeSpecIn, paramList, genericArgs, xlator):
    convertedIdxType = ""
    typeSpecOut = typeSpecIn
    if progSpec.isNewContainerTempFunc(typeSpecIn): return(name, typeSpecOut, paramList, convertedIdxType)
    return(name, typeSpecOut, paramList, convertedIdxType)

def codeArrayIndex(idx, containerType, LorR_Val, previousSegName, idxTypeSpec):
    if (containerType == 'string'):
        S= '[index: '+idx+']'
    else:
        fieldDefAt = CheckObjectVars(containerType, "at", "")
        if fieldDefAt: S= '.at(' + idx +')'
        else: S= '[' + idx +']'
    return S
###################################################### CONTAINER REPETITIONS
def codeRangeSpec(traversalMode, ctrType, repName, S_low, S_hi, indent, xlator):
    if(traversalMode=='Forward' or traversalMode==None):
        S = indent + "for "+ repName+' in '+ S_low + "..<Int(" + S_hi + "){\n"
    elif(traversalMode=='Backward'):
        S = indent + "for " + repName + " in stride(from:"+ S_hi+"-1" + ", through: " + S_low + ", by: -1){\n"
    return (S)

def iterateRangeFromTo(classes,localVarsAlloc,StartKey,EndKey,ctnrTSpec,repName,ctnrName,indent,xlator):
    willBeModifiedDuringTraversal=True   # TODO: Set this programatically later.
    [datastructID, idxTypeKW, ctnrOwner]=getContainerType(ctnrTSpec, 'action')
    actionText   = ""
    loopCntrName = ""
    firstOwner   = progSpec.getOwnerFromTypeSpec(ctnrTSpec)
    firstType    = progSpec.getNewContainerFirstElementTypeTempFunc(ctnrTSpec)
    firstTSpec   = {'owner':firstOwner, 'fieldType':firstType}
    containerCat = getContaineCategory(ctnrTSpec)
    if containerCat == "MAP":
        keyVarSpec = {'owner':ctnrTSpec['owner'], 'fieldType':firstType, 'codeConverter':(repName+'.first')}
        localVarsAlloc.append([repName+'_key', keyVarSpec])  # Tracking local vars for scope
        firstTSpec['codeConverter'] = (repName+'.second')
        localVarsAlloc.append([repName, firstTSpec]) # Tracking local vars for scope
        actionText += (indent + "for( auto " + repName+'Itr ='+ ctnrName+'->lower_bound('+StartKey+')' + "; " + repName + "Itr !=" + ctnrName+'->upper_bound('+EndKey+')' +"; ++"+ repName + "Itr ){\n"
                    + indent+"    "+"auto "+repName+" = *"+repName+"Itr;\n")
    elif datastructID=='list' or (datastructID=='list' and not willBeModifiedDuringTraversal):
        pass;
    elif datastructID=='list' and willBeModifiedDuringTraversal:
        pass;
    else:
        print("DSID iterateRangeFromTo:",datastructID,ctnrTSpec)
        exit(2)
    return [actionText, loopCntrName]

def iterateContainerStr(classes,localVarsAlloc,ctnrTSpec,repName,ctnrName,isBackward,indent,genericArgs,xlator):
    #TODO: handle isBackward
    willBeModifiedDuringTraversal=True   # TODO: Set this programatically later.
    [datastructID, idxTypeKW, ctnrOwner]=getContainerType(ctnrTSpec, 'action')
    actionText   = ""
    loopCntrName = repName+'_key'
    itrIncStr    = ""
    firstOwner   = progSpec.getContainerFirstElementOwner(ctnrTSpec)
    firstType    = progSpec.getContainerFirstElementType(ctnrTSpec)
    firstTSpec   = {'owner':firstOwner, 'fieldType':firstType}
    reqTagList   = progSpec.getReqTagList(ctnrTSpec)
    itrTSpec     = progSpec.getItrTypeOfDataStruct(ctnrTSpec)
    itrTypeKW    = progSpec.fieldTypeKeyword(itrTSpec)
    itrOwner     = progSpec.getOwnerFromTypeSpec(itrTSpec)
    itrName      = repName + "Itr"
    containerCat = getContaineCategory(ctnrTSpec)
    [LDeclP, RDeclP, LDeclA, RDeclA] = ChoosePtrDecorationForSimpleCase(firstOwner)
    [LNodeP, RNodeP, LNodeA, RNodeA] = ChoosePtrDecorationForSimpleCase(itrOwner)
    if containerCat=='PovList': cdErr("TODO: handle PovList")
    if containerCat=='MAP':
        if(reqTagList != None):
            firstTSpec['fieldType'] = progSpec.getTypeFromTemplateArg(reqTagList[1])
        keyVarSpec  = {'owner':firstOwner, 'fieldType':firstType, 'codeConverter':(repName+'!.key')}
        firstTSpec['codeConverter'] = (repName+'!.value')
        itrType     = progSpec.getItrTypeOfDataStruct(ctnrTSpec)
        itrTypeKW   = progSpec.fieldTypeKeyword(itrType)
        itrTypeKW   = generateGenericStructName(itrTypeKW, reqTagList, genericArgs, xlator)
        itrDeclStr  = indent + 'var '+itrName+":"+itrTypeKW+' = '+ctnrName+'.front()\n'
        localVarsAlloc.append([itrName, itrType])
        endItrName       = repName + "EndItr"
        endItrStr   = indent + 'var ' + endItrName + ':'+itrTypeKW+' = '+ctnrName+'.end()\n'
        itrIncStr   = indent + "    " + itrName + " = " + itrName + ".__inc()\n"
        actionText += itrDeclStr + endItrStr
        actionText += (indent + 'while ' + itrName + '.node !== '+endItrName+'.node {\n')
        actionText += (indent + "    var  " + repName + " = " + itrName + ".node\n")
        # TODO: increment ITR
    elif containerCat=="LIST":
        if willBeModifiedDuringTraversal:
            idxTypeKW        = adjustBaseTypes(idxTypeKW, False)
            containedOwner = progSpec.getOwnerFromTypeSpec(ctnrTSpec)
            keyVarSpec     = {'owner':containedOwner, 'fieldType':firstType}
            loopVarName=repName+"Idx";
            if(isBackward):
                actionText += (indent + "for " + repName+' in '+ ctnrName +".reversed() {\n")
            else:
                actionText += (indent + "for " + loopVarName + " in 0..<" +  ctnrName+".count {\n"
                            + indent+"    var "+repName + ':' + idxTypeKW + " = "+ctnrName+"["+loopVarName+"];\n")
        else:
            keyVarSpec = {'owner':'me', 'fieldType':'Int'}
            if(isBackward):
                actionText += (indent + "for " + repName+' in ('+ ctnrName +".count - 1).stride(through: 0, by: -1) {\n")
            else:
                actionText += (indent + "for " + repName+' in '+ ctnrName + " {\n")
    else: cdErr("iterateContainerStr() datastructID = " + datastructID)
    localVarsAlloc.append([loopCntrName, keyVarSpec])  # Tracking local vars for scope
    localVarsAlloc.append([repName, firstTSpec]) # Tracking local vars for scope
    return [actionText, loopCntrName, itrIncStr]

def codeSwitchExpr(switchKeyExpr, switchKeyTypeSpec):
    return switchKeyExpr

def codeSwitchCase(caseKeyValue, caseKeyTypeSpec):
    return caseKeyValue

###################################################### EXPRESSION CODING
def codeNotOperator(S, S2,retTypeSpec):
    if progSpec.varsTypeCategory(retTypeSpec) != 'bool':
        if S2[-1]=='!': S2=S2[:-1]   # Todo: Better detect this
        S2='('+S2+' != nil)'
        retTypeSpec='bool'
    else: S+='!' + S2
    return [S, retTypeSpec]

def codeFactor(item, objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs, xlator):
    ####  ( value | ('(' + expr + ')') | ('!' + expr) | ('-' + expr) | varRef("varFunRef"))
    #print('                  factor: ', item)
    S=''
    retTypeSpec='noType'
    item0 = item[0]
    #print("ITEM0=", item0, ">>>>>", item)
    if (isinstance(item0, str)):
        if item0=='(':
            [S2, retTypeSpec] = codeExpr(item[1], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs, xlator)
            S+='(' + S2 +')'
        elif item0=='!':
            [S2, retTypeSpec] = codeExpr(item[1], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs, xlator)
            [S, retTypeSpec]  = codeNotOperator(S, S2,retTypeSpec)
        elif item0=='-':
            [S2, retTypeSpec] = codeExpr(item[1], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs, xlator)
            S+='-' + S2
        elif item0=='[':
            tmp="["
            for expr in item[1:-1]:
                [S2, retTypeSpec] = codeExpr(expr, objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs, xlator)
                if len(tmp)>1: tmp+=", "
                tmp+=S2
            tmp+="]"
            S+=tmp
        elif item0=='{':
            cdErr("TODO: finish Swift initialize new map")
        else:
            fTypeKW = progSpec.varTypeKeyWord(expectedTypeSpec)
            if fTypeKW == "BigInt":
                S += item0
                retTypeSpec='BigInt'
            elif fTypeKW == "BigFloat":
                S += item0 + "_mpf"
                retTypeSpec='BigFloat'
            elif fTypeKW == "BigFrac":
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
                if item0=='false' or item0=='true': retTypeSpec={'owner': 'literal', 'fieldType': 'bool'}
                if retTypeSpec == 'noType' and progSpec.isStringNumeric(item0): retTypeSpec={'owner': 'literal', 'fieldType': 'numeric'}
                if retTypeSpec == 'noType' and progSpec.typeIsInteger(fTypeKW): retTypeSpec=fTypeKW

    else: # CODEDOG LITERALS
        if isinstance(item0[0], str):
            S+=item0[0]
            if '"' in S or "'" in S: retTypeSpec = 'string'
            if '.' in S: retTypeSpec = 'double'
            if isinstance(S, int): retTypeSpec = 'int64'
            else:  retTypeSpec = 'int32'
        else:
            [codeStr, retTypeSpec, prntType, AltIDXFormat]=codeItemRef(item0, 'RVAL', objsRefed, returnType, LorRorP_Val, genericArgs, xlator)
            if(codeStr=="NULL"):
                codeStr="nil"
                retTypeSpec={'owner':"PTR"}
            S+=codeStr                                # Code variable reference or function call
    return [S, retTypeSpec]

######################################################
def adjustQuotesForChar(typeSpec1, typeSpec2, S):
    return(S)

def adjustConditional(S, conditionType):
    if conditionType!=None and not isinstance(conditionType, str):
        if conditionType['owner']=='our' or conditionType['owner']=='their' or conditionType['owner']=='my' or progSpec.isStruct(conditionType['fieldType']):
            if S[-1]=='!': S=S[:-1]   # Todo: Better detect this
            S+=" != nil"
        elif conditionType['owner']=='me' and (conditionType['fieldType']=='flag' or progSpec.typeIsInteger(conditionType['fieldType'])):
            if S[-1]=='!': S=S[:-1]   # Todo: Better detect this
            S+=" != 0"
        conditionType='bool'
    return [S, conditionType]

def codeSpecialReference(segSpec, objsRefed, genericArgs, xlator):
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
                [S2, argTypeSpec]=codeExpr(P[0], objsRefed, None, None, 'PARAM', genericArgs, xlator)
                [S2, isDerefd]=derefPtr(S2, argTypeSpec)
                if(count>0): S+=', '
                S+=S2
                count= count + 1
            S+=',separator:"", terminator:"")'
        elif(funcName=='AllocateOrClear'):
            [varName,  varTypeSpec]=codeExpr(paramList[0][0], objsRefed, None, None, 'PARAM', genericArgs, xlator)
            if(varTypeSpec==0): cdErr("Name is undefined: " + varName)
            if(varName[-1]=='!'): varNameUnRefed=varName[:-1]  # Remove a reference. It would be better to do this in codeExpr but may take some work.
            else: varNameUnRefed=varName
            S+='if('+varNameUnRefed+' != nil){'+varName+'.clear();} else {'+varName+" = "+codeAllocater(varTypeSpec, genericArgs, xlator)+"();}"
        elif(funcName=='Allocate'):
            [varName,  varTypeSpec]=codeExpr(paramList[0][0], objsRefed, None, None, 'LVAL', genericArgs, xlator)
            if(varTypeSpec==0): cdErr("Name is Undefined: " + varName)
            S+=varName+" = "+codeAllocater(varTypeSpec, genericArgs, xlator)+'('
            count=0   # TODO: As needed, make this call CodeParameterList() with modelParams of the constructor.
            for P in paramList[1:]:
                if(count>0): S+=', '
                [S2, argType]=codeExpr(P[0], objsRefed, None, None, 'PARAM', genericArgs, xlator)
                S+=S2
                count=count+1
            S+=")"
        elif(funcName=='callPeriodically'):
            [objName,  fieldType]=codeExpr(paramList[1][0], objsRefed, None, None, 'PARAM', genericArgs, xlator)
            [interval,  intSpec] = codeExpr(paramList[2][0], objsRefed, None, None, 'PARAM', genericArgs, xlator)
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
                [S2, argType]=codeExpr(P[0][0], objsRefed, None, None, 'PARAM', genericArgs, xlator)
                S2=derefPtr(S2, argType)
                S+='to_string('+S2+')'
                returnType='string'
    else: # Not parameters, i.e., not a function
        if(funcName=='self'):
            S+='self'

    return [S, retOwner, fieldType]

def checkIfSpecialAssignmentFormIsNeeded(AltIDXFormat, RHS, rhsType, LHS, LHSParentType, LHS_FieldType):
    # Check for string A[x] = B;  If so, render A.insert(B,x)
    S = ''
    RHS += makePtrOpt(rhsType)
    [containerType, idxTypeKW, owner]=getContainerType(AltIDXFormat[1], "")
    if containerType == 'RBTreeMap' or containerType[:2]=="__" and 'Map' in containerType:
        S=AltIDXFormat[0] + '.insert(' + AltIDXFormat[2] + ', ' + RHS + ');\n'
    return S

######################################################
def codeMain(classes, tags, objsRefed, xlator):
    cdlog(3, "\n            Generating GLOBAL...")
    if("GLOBAL" in classes[1]):
        if(classes[0]["GLOBAL"]['stateType'] != 'struct'):
            print("ERROR: GLOBAL must be a 'struct'.")
            exit(2)
        [structCode, funcCode, globalFuncs]=codeStructFields("GLOBAL", tags, '', objsRefed, xlator)
        if(funcCode==''): funcCode="// No main() function.\n"
        if(structCode==''): structCode="// No Main Globals.\n"
        funcCode = "\n\n"+funcCode+"\nmain();" # TODO: figure out why call to main isn't generated and un-hardcode this
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
        parentClass=': '
        count =0
        for item in classInherits[0]:
            if count>0:
                parentClass+= ', '
            parentClass+= progSpec.getUnwrappedClassFieldTypeKeyWord(classes, item)
            count += 1
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

func joinCmdStrings(count: Int, argv: [Character]) -> String{
    var acc: String=""
    for i in 1...count{
        if(i>1){acc+=" "}
        acc += String(argv[i])
    }
    return(acc)
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
def variableDefaultValueString(fieldType, isTypeArg, owner):
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
        if progSpec.ownerIsPointer(owner):fieldValueText = ''
        else:fieldValueText = ' = ' + fieldType +'()'
    return fieldValueText

def codeNewVarStr(classes, tags, lhsTypeSpec, varName, fieldDef, indent, objsRefed, actionOrField, genericArgs, localVarsAllocated, xlator):
    varDeclareStr = ''
    assignValue   = ''
    isAllocated   = fieldDef['isAllocated']
    owner         = progSpec.getTypeSpecOwner(lhsTypeSpec)
    useCtor       = False
    if fieldDef['paramList'] and fieldDef['paramList'][-1] == "^&useCtor//8":
        del fieldDef['paramList'][-1]
        useCtor = True
    [cvrtType, innerType] = convertType(lhsTypeSpec, 'var', actionOrField, genericArgs, xlator)
    reqTagList = progSpec.getReqTagList(lhsTypeSpec)
    fieldType = progSpec.fieldTypeKeyword(lhsTypeSpec)
    [allocFieldType, innerType] = convertType(lhsTypeSpec, 'alloc', '', genericArgs, xlator)
    if reqTagList and not progSpec.isWrappedType(classes, fieldType) and not progSpec.isAbstractStruct(classes[0], fieldType):
        cvrtType = generateGenericStructName(fieldType, reqTagList, genericArgs, xlator)
        allocFieldType = cvrtType
        lhsTypeSpec = getGenericTypeSpec(genericArgs, lhsTypeSpec, xlator)
        fromImpl = progSpec.getFromImpl(lhsTypeSpec)
        if fromImpl: lhsTypeSpec.pop('fromImplemented')
        localVarsAllocated.append([varName, lhsTypeSpec])  # Tracking local vars for scope
    else:
        localVarsAllocated.append([varName, lhsTypeSpec])  # Tracking local vars for scope
    if(fieldDef['value']):
        [RHS, rhsTypeSpec]=codeExpr(fieldDef['value'][0], objsRefed, None, None, 'RVAL', genericArgs, xlator)
        [leftMod, rightMod]=chooseVirtualRValOwner(lhsTypeSpec, rhsTypeSpec)
        RHS = leftMod+RHS+rightMod
        RHS = xlator['checkForTypeCastNeed'](lhsTypeSpec, rhsTypeSpec, RHS)
        assignValue = " = " + RHS
    else: # If no value was given:
        CPL=''
        if fieldDef['paramList'] != None:       # call constructor  # curly bracket param list
            # Code the constructor's arguments
            [CPL, paramTypeList] = codeParameterList(varName, fieldDef['paramList'], None, objsRefed, genericArgs, xlator)
            if len(paramTypeList)==1:
                if not isinstance(paramTypeList[0], dict):
                    print("\nPROBLEM: The return type of the parameter '", CPL, "' of "+varName+"(...) cannot be found and is needed. Try to define it.\n",   paramTypeList)
                    exit(1)
                rhsTypeSpec = paramTypeList[0]
                rhsType     = progSpec.getFieldType(rhsTypeSpec)
                # TODO: Remove the 'True' and make this check object heirarchies or similar solution
                if True or not isinstance(rhsType, str) and cvrtType==rhsType[0]:
                    assignValue = " = " + CPL   # Act like a copy constructor
            if(assignValue==''): assignValue = ' = ' + allocFieldType + CPL
        else:
            assignValue = variableDefaultValueString(allocFieldType, False, owner)
    fieldTypeMod = makePtrOpt(lhsTypeSpec)
    if (assignValue == ""):
        varDeclareStr= "var " + varName + ": "+ cvrtType + fieldTypeMod + " = " + allocFieldType + '()'
    else:
        varDeclareStr= "var " + varName + ": "+ cvrtType + fieldTypeMod + assignValue
    return(varDeclareStr)

def codeIncrement(varName):
    return varName + " += 1"

def codeDecrement(varName):
    return varName + " -= 1"

def isNumericType(convertedType):
    if(convertedType == "UInt32" or convertedType == "UInt64" or convertedType == "Float" or convertedType == "Int" or convertedType == "Int32" or convertedType == "Int64" or convertedType == "Double"):
        return True
    return False

def codeVarFieldRHS_Str(fieldName, cvrtType, innerType, typeSpec, paramList, objsRefed, isAllocated, typeArgList, genericArgs, xlator):
    fieldValueText=""
    fieldOwner=progSpec.getTypeSpecOwner(typeSpec)
    isTypeArg = False
    if typeArgList:
        for typeArg in typeArgList:
            if cvrtType == typeArg: isTypeArg = True
    if paramList!=None:
        if paramList[-1] == "^&useCtor//8":
            del paramList[-1]
        [CPL, paramTypeList] = codeParameterList(fieldName, paramList, None, objsRefed, genericArgs, xlator)
        fieldValueText=" = " + cvrtType + CPL
    else:
        fieldValueText = variableDefaultValueString(cvrtType, isTypeArg, fieldOwner)
        if fieldValueText and cvrtType != 'String':
            fieldValueText += makePtrOpt(typeSpec) # Default String value can't be optional
    return fieldValueText

def codeConstField_Str(convertedType, fieldName, fieldValueText, className, indent, xlator ):
    decl = ''
    if className=='GLOBAL': defn =  indent  + "let " + fieldName + ':'+ convertedType  + fieldValueText +';\n';
    else: defn =  indent  + "let " + fieldName + ':'+ convertedType  + fieldValueText +';\n';
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
        else:
            convertedType += makePtrOpt(typeSpec)
            defn = indent + "var "+ fieldName + ": " +  convertedType + fieldValueText + '\n'
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

def codeConstructors(className, ctorArgs, ctorOvrRide, ctorInit, copyCtorArgs, funcBody, callSuper, xlator):
    #TODO: Swift should only have constructors if they are called somewhere.
    prefix = ''
    if callSuper != "": prefix = 'override '
    if ctorArgs != "":
        S = '    '+ctorOvrRide+'init(' + ctorArgs+'){\n'+callSuper+ctorInit+funcBody+'    }\n'
    S += '    '+prefix+'init(){\n'+callSuper+funcBody+'    }\n'
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
    return '        INIT();\n'

def codeSuperConstructorCall(parentClassName):
    return '        super.init();\n'

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
            structCode += indent + "func "  + fieldName +"("+argListText+")" + returnType
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

#######################################################

def includeDirective(libHdr):
    S = 'import '+libHdr+'\n'
    return S

def generateMainFunctionality(classes, tags):
    # TODO: Make initCode, runCode and deInitCode work better and more automated by patterns.
    # TODO: Some deInitialize items should automatically run during abort().
    # TODO: Deinitialize items should happen in reverse order.

    runCode = progSpec.fetchTagValue(tags, 'runCode')
    if runCode==None: runCode=""
    mainFuncCode="""
    me void: main() <- {
        initialize("")        // TODO: get command line args and pass to initialize(joinCmdStrings(argc, argv))
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
    xlators['PtrConnector']          = "!."                     # Name segment connector for pointers.
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
    xlators['addGLOBALSpecialCode']         = addGLOBALSpecialCode
    xlators['addSpecialCode']               = addSpecialCode
    xlators['adjustConditional']            = adjustConditional
    xlators['applyOwner']                   = applyOwner
    xlators['applyTypecast']                = applyTypecast
    xlators['checkForTypeCastNeed']         = checkForTypeCastNeed
    xlators['checkIfSpecialAssignmentFormIsNeeded'] = checkIfSpecialAssignmentFormIsNeeded
    xlators['chooseVirtualRValOwner']       = chooseVirtualRValOwner
    xlators['codeArgText']                  = codeArgText
    xlators['codeArrayIndex']               = codeArrayIndex
    xlators['codeComparisonStr']            = codeComparisonStr
    xlators['codeConstField_Str']           = codeConstField_Str
    xlators['codeConstructor']              = codeConstructor
    xlators['codeConstructorArgText']       = codeConstructorArgText
    xlators['codeConstructorCall']          = codeConstructorCall
    xlators['codeConstructorInit']          = codeConstructorInit
    xlators['codeConstructors']             = codeConstructors
    xlators['codeCopyConstructor']          = codeCopyConstructor
    xlators['codeDecrement']                = codeDecrement
    xlators['codeFactor']                   = codeFactor
    xlators['codeFuncHeaderStr']            = codeFuncHeaderStr
    xlators['codeIdentityCheck']            = codeIdentityCheck
    xlators['codeIncrement']                = codeIncrement
    xlators['codeIteratorOperation']        = codeIteratorOperation
    xlators['codeMain']                     = codeMain
    xlators['codeNewVarStr']                = codeNewVarStr
    xlators['codeRangeSpec']                = codeRangeSpec
    xlators['codeSetBits']                  = codeSetBits
    xlators['codeSpecialReference']         = codeSpecialReference
    xlators['codeStructText']               = codeStructText
    xlators['codeSuperConstructorCall']     = codeSuperConstructorCall
    xlators['codeSwitchBreak']              = codeSwitchBreak
    xlators['codeSwitchCase']               = codeSwitchCase
    xlators['codeSwitchExpr']               = codeSwitchExpr
    xlators['codeVarField_Str']             = codeVarField_Str
    xlators['codeVarFieldRHS_Str']          = codeVarFieldRHS_Str
    xlators['convertToInt']                 = convertToInt
    xlators['derefPtr']                     = derefPtr
    xlators['determinePtrConfigForAssignments'] = determinePtrConfigForAssignments
    xlators['extraCodeForTopOfFuntion']     = extraCodeForTopOfFuntion
    xlators['generateMainFunctionality']    = generateMainFunctionality
    xlators['getCodeAllocSetStr']           = getCodeAllocSetStr
    xlators['getCodeAllocStr']              = getCodeAllocStr
    xlators['getConstIntFieldStr']          = getConstIntFieldStr
    xlators['getContainerType']             = getContainerType
    xlators['getContainerTypeInfo']         = getContainerTypeInfo
    xlators['getEnumStr']                   = getEnumStr
    xlators['getReqTagString']              = getReqTagString
    xlators['getUnwrappedClassOwner']       = getUnwrappedClassOwner
    xlators['getVirtualFuncText']           = getVirtualFuncText
    xlators['includeDirective']             = includeDirective
    xlators['iterateContainerStr']          = iterateContainerStr
    xlators['iterateRangeFromTo']           = iterateRangeFromTo
    xlators['langStringFormatterCommand']   = langStringFormatterCommand
    xlators['LanguageSpecificDecorations']  = LanguageSpecificDecorations
    xlators['makePtrOpt']                   = makePtrOpt
    xlators['produceTypeDefs']              = produceTypeDefs
    xlators['recodeStringFunctions']        = recodeStringFunctions
    xlators['xlateLangType']                = xlateLangType
    return(xlators)
