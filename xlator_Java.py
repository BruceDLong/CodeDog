#This file, along with Lib_Java.py specify to the CodeGenerater how to compile CodeDog source code into Java source code.
import progSpec
import codeDogParser
from progSpec import cdlog, cdErr, logLvl
from codeGenerator import codeItemRef, codeUserMesg, codeAllocater, codeParameterList, makeTagText, codeAction, getModeStateNames, codeExpr, convertType, generateGenericStructName, getGenericTypeSpec, getInheritedEnums, CheckObjectVars

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
                idxType  = applyOwner(typeSpec, idxOwner, idxType, '')
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
        else:
            if(fieldType=='int32'):      javaType= 'int'
            elif(fieldType=='uint32'or fieldType=='uint'):  javaType='int'  # these should be long but Java won't allow
            elif(fieldType=='int64' or fieldType=='uint64'):javaType= 'long'
            elif(fieldType=='uint8' or fieldType=='uint16'):javaType='uint32'
            elif(fieldType=='int8'  or fieldType=='int16'): javaType='int32'
            elif(fieldType=='char' ):    javaType= 'char'
            elif(fieldType=='bool' ):    javaType= 'boolean'
            elif(fieldType=='string'):   javaType= 'String'
            else: javaType=progSpec.flattenObjectName(fieldType)
    return javaType

def isJavaPrimativeType(fieldType):
    if fieldType=="int" or fieldType=="boolean" or fieldType=="float" or fieldType=="double" or fieldType=="long" or fieldType=="char": return True
    return False

def applyOwner(typeSpec, owner, langType, actionOrField, varMode):
    if owner=='const':
        if actionOrField=="field": langType = "final static "+langType
        else: langType = "final "+langType
    elif owner=='me':    langType = langType
    elif owner=='my':    langType = langType
    elif owner=='our':   langType = langType
    elif owner=='their': langType = langType
    elif owner=='itr':
        langType  = progSpec.fieldTypeKeyword(progSpec.getItrTypeOfDataStruct(typeSpec))
        if langType=='nodeType': cdErr("TODO: design iterators in Java!!!!!!!!!!!!!!!!!!!!!!!!!! "+langType)
    elif owner=='we': langType = 'static '+langType
    else: cdErr("ERROR: Owner of type not valid '" + owner + "'")
    return langType

def getUnwrappedClassOwner(classes, typeSpec, fieldType, varMode, ownerIn):
    ownerOut = ownerIn
    baseType = progSpec.isWrappedType(classes, fieldType)
    if baseType!=None:  # TODO: When this is all tested and stable, un-hardcode and optimize this!!!!!
        if 'ownerMe' in baseType:
            ownerOut = 'their'
        else:
            ownerOut=ownerIn
    return ownerOut

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
    langType = applyOwner(typeSpec, owner, langType, actionOrField, varMode)
    if langType=='TYPE ERROR': print(langType, owner, fTypeKW);
    innerType = langType
    if progSpec.isNewContainerTempFunc(typeSpec): return [langType, innerType]
    if owner =="const": innerType = fTypeKW
    return [langType, innerType]

def makePtrOpt(typeSpec):
    return('')

def isComparableType(typeSpec):
    fTypeKW = progSpec.fieldTypeKeyword(typeSpec)
    if fTypeKW == 'keyType': return True
    if 'generic' in typeSpec and typeSpec['generic'] == 'keyType' and fTypeKW == 'string':
        return True
    return False

def codeIteratorOperation(itrCommand, fieldType):
    result = ''
    if itrCommand=='goNext':  result='%0.goNext()'
    elif itrCommand=='goPrev':result='%0.JAVA ERROR!'
    elif itrCommand=='key':   result='%0.node.key'
    elif itrCommand=='val':   result='%0.node.value'
    return result

def recodeStringFunctions(name, typeSpec):
    if name == "size":
        name = "length"
    elif name == "subStr":
        typeSpec['codeConverter']='%0.substring(%1, %1+%2)'
        typeSpec['fieldType']='String'
    elif name == "append":
        typeSpec['codeConverter']='%0 += %1'

    return [name, typeSpec]

def langStringFormatterCommand(fmtStr, argStr):
    fmtStr=fmtStr.replace(r'%i', r'%d')
    fmtStr=fmtStr.replace(r'%l', r'%d')
    S='String.format('+'"'+ fmtStr +'"'+ argStr +')'
    return S

def LanguageSpecificDecorations(classes, S, typeSpec, owner, LorRorP_Val, xlator):
    return S

def convertToInt(S, typeSpec):
    fTypeKW = progSpec.fieldTypeKeyword(typeSpec)
    if fTypeKW=='numeric': return S
    if fTypeKW == 'char': S = 'Character.getNumericValue('+S+')'
    return S

def checkForTypeCastNeed(lhsTypeSpec, rhsTypeSpec, RHScodeStr):
    LTypeKW = progSpec.fieldTypeKeyword(lhsTypeSpec)
    RTypeKW = progSpec.fieldTypeKeyword(rhsTypeSpec)
    if LTypeKW == 'bool'or LTypeKW == 'boolean':
        if progSpec.typeIsPointer(rhsTypeSpec):
            return '(' + RHScodeStr + ' == null)'
        if (RTypeKW=='int' or RTypeKW=='flag'):
            if RHScodeStr[0]=='!': return '(' + RHScodeStr[1:] + ' == 0)'
            else: return '(' + RHScodeStr + ' != 0)'
        if RHScodeStr == "0": return "false"
        if RHScodeStr == "1": return "true"
    if LTypeKW != RTypeKW:
        if LTypeKW == 'char' and RTypeKW == 'numeric':
            RHScodeStr = '(char)('+ RHScodeStr +')'
    return RHScodeStr

def getTheDerefPtrMods(itemTypeSpec):
    return ['', '', False]

def derefPtr(varRef, itemTypeSpec):
    [leftMod, rightMod, isDerefd] = getTheDerefPtrMods(itemTypeSpec)
    S = leftMod + varRef + rightMod
    return [S, isDerefd]

def ChoosePtrDecorationForSimpleCase(owner):
    #print("TODO: finish ChoosePtrDecorationForSimpleCase")
    return ['','',  '','']

def chooseVirtualRValOwner(LVAL, RVAL):
    return ['','']

def determinePtrConfigForAssignments(LVAL, RVAL, assignTag, codeStr):
    return ['','',  '','']

def getCodeAllocStr(varTypeStr, owner):
    if(owner!='const'): S="new "+varTypeStr
    else: cdErr("ERROR: Cannot allocate a 'const' variable.")
    return S

def getCodeAllocSetStr(varTypeStr, owner, value):
    S=getCodeAllocStr(varTypeStr, owner)
    S+='('+value+')'
    return S

def getConstIntFieldStr(fieldName, fieldValue, intSize):
    if intSize==32: S= "public static final int "+fieldName+ " = " + fieldValue+ ";\n"
    else: S= "public static final long "+fieldName+ " = " + fieldValue+ "L;\n"
    return(S)

def getEnumStr(fieldName, enumList):
    S = ''
    count=0
    for enumName in enumList:
        S += "    " + getConstIntFieldStr(enumName, str(count), 32)
        count=count+1
    S += "\n"
    return(S)

def getEnumStructStr(fieldName, enumList):
    S = 'enum '+fieldName+'{'+ ', '.join(enumList) +'}\n'
    return S

def getEnumStringifyFunc(className, enumList):
    S = 'String[] ' + className + 'Strings = {"' + '", "'.join(enumList) + '"};\n'
    return S

def codeIdentityCheck(S, S2, retType1, retType2, opIn):
    S2 = adjustQuotesForChar(retType1, retType2, S2)
    if opIn == '===':
        #print("TODO: finish codeIdentityCk")
        return S + " == "+ S2
    else:
        lFType = progSpec.fieldTypeKeyword(retType1)
        rFType = progSpec.fieldTypeKeyword(retType2)
        if (lFType=='String' or lFType == "string") and opIn=="==" and (rFType == "String" or rFType == "string"):
            return S+'.equals('+S2+')'
        else:
            if   (opIn == '=='): opOut=' == '
            elif (opIn == '!='): opOut=' != '
            elif (opIn == '!=='): opOut=' != '
            else: cdErr("ERROR: '==' or '!=' or '===' or '!==' expected.")
            return S+opOut+S2
    return S

def codeComparisonStr(S, S2, retType1, retType2, op):
    S3 = ""
    if (op == '<'):
        if isComparableType(retType1):
            S+='.compareTo('
            S3= ") < 0"
        else: S+=' < '
    elif (op == '>'):
        if isComparableType(retType1):
            S+='.compareTo('
            S3= ") > 0"
        else: S+=' > '
    elif (op == '<='): S+=' <= '
    elif (op == '>='): S+=' >= '
    else: cdErr("ERROR: One of <, >, <= or >= expected in code generator.")
    S2 = adjustQuotesForChar(retType1, retType2, S2)
    [S2, isDerefd]=derefPtr(S2, retType2)
    S+=S2+S3
    return S

###################################################### CONTAINERS
def getContaineCategory(containerSpec):
    fTypeKW = progSpec.fieldTypeKeyword(containerSpec)
    if fTypeKW=='PovList':
        return 'PovList'
    elif fTypeKW=='TreeMap' or fTypeKW=='Java_Map' or 'RBTreeMap' in fTypeKW or "__Map_" in fTypeKW:
        return 'MAP'
    elif fTypeKW=='list' or fTypeKW=='Java_ArrayList' or "__List_" in fTypeKW or "__CDList" in fTypeKW:
        return 'LIST'
    elif 'Multimap' in fTypeKW:
        return 'MULTIMAP'
    return None

def getContainerTypeInfo(classes, containerType, name, idxType, typeSpecIn, paramList, genericArgs, xlator):
    convertedIdxType = ""
    typeSpecOut = typeSpecIn
    if progSpec.isNewContainerTempFunc(typeSpecIn): return(name, typeSpecOut, paramList, convertedIdxType)
    return(name, typeSpecOut, paramList, convertedIdxType)

def codeArrayIndex(idx, containerType, LorR_Val, previousSegName, idxTypeSpec):
    if LorR_Val=='RVAL':
        #Next line may be cause of bug with printing modes.  remove 'not'?
        modeStateNames = getModeStateNames()
        if previousSegName in modeStateNames:
            modeStruct = modeStateNames[previousSegName]
            if modeStruct=='modeStrings': S = '[(int)' + idx + '.ordinal()]'
            else: S= '.get((int)' + idx + ')'
        elif (containerType== 'string'):
            fTypeKW = progSpec.fieldTypeKeyword(idxTypeSpec)
            mod = ''
            if fTypeKW!='numeric' and fTypeKW!='int':
                jType = adjustBaseTypes(fTypeKW, False)
                mod = '(int)'
            S= '.charAt(' + mod + idx + ')'    # '.substring(' + idx + ', '+ idx + '+1' +')'
        else:
            fieldDefAt = CheckObjectVars(containerType, "at", "")
            if fieldDefAt:
                if 'typeSpec' in fieldDefAt and 'codeConverter' in fieldDefAt['typeSpec']:
                    S = fieldDefAt['typeSpec']['codeConverter']
                    S = S.replace('%1', idx)
                else: S= '.at(' + idx +')'
            else: S= '[' + idx +']'
    else:
        if containerType== 'ArrayList' or containerType== 'Java_Map' or containerType== 'Java_ArrayList': S = '.get('+idx+')'
        else: S= '[' + idx +']'
    return S
###################################################### CONTAINER REPETITIONS
def codeRangeSpec(traversalMode, ctrType, repName, S_low, S_hi, indent, xlator):
    if(traversalMode=='Forward' or traversalMode==None):
        S = indent + "for("+ctrType+" " + repName+'='+ S_low + "; " + repName + "!=" + S_hi +"; "+ xlator['codeIncrement'](repName) + "){\n"
    elif(traversalMode=='Backward'):
        S = indent + "for("+ctrType+" " + repName+'='+ S_hi + "-1; " + repName + ">=" + S_low +"; --"+ repName + "){\n"
    return (S)

def iterateRangeFromTo(classes,localVarsAlloc,StartKey,EndKey,ctnrTSpec,repName,ctnrName,indent,xlator):
    willBeModifiedDuringTraversal=True   # TODO: Set this programatically later.
    [datastructID, idxTypeKW, ctnrOwner]=getContainerType(ctnrTSpec, 'action')
    actionText   = ""
    loopCntrName = ""
    firstOwner   = progSpec.getOwnerFromTypeSpec(ctnrTSpec)
    firstType    = progSpec.getNewContainerFirstElementTypeTempFunc(ctnrTSpec)
    firstTSpec   = {'owner':firstOwner, 'fieldType':firstType}
    reqTagList   = progSpec.getReqTagList(ctnrTSpec)
    containerCat = getContaineCategory(ctnrTSpec)
    if containerCat=="MAP" or containerCat=="MULTIMAP":
        valueFieldType = progSpec.fieldTypeKeyword(ctnrTSpec)
        if(reqTagList != None):
            firstTSpec['owner']     = progSpec.getOwnerFromTemplateArg(reqTagList[1])
            firstTSpec['fieldType'] = progSpec.getTypeFromTemplateArg(reqTagList[1])
            idxTypeKW      = progSpec.getTypeFromTemplateArg(reqTagList[0])
            valueFieldType = progSpec.getTypeFromTemplateArg(reqTagList[1])
        keyVarSpec = {'owner':ctnrTSpec['owner'], 'fieldType':firstType}
        loopCntrName = repName+'_key'
        itrTypeKW = progSpec.fieldTypeKeyword(progSpec.getItrTypeOfDataStruct(ctnrTSpec))
        idxTypeKW = adjustBaseTypes(idxTypeKW, True)
        valueFieldType = adjustBaseTypes(valueFieldType, True)
        localVarsAlloc.append([loopCntrName, keyVarSpec])  # Tracking local vars for scope
        localVarsAlloc.append([repName, firstTSpec]) # Tracking local vars for scope
        if '__RB' in datastructID:
            actionText += (indent + 'for('+itrTypeKW+' '+repName+'Entry = '+ctnrName+'.find('+StartKey+'); '+repName+'Entry !='+ctnrName+'.find('+EndKey+'); '+repName+'Entry.__inc()){\n' +
                       indent + '    '+valueFieldType+' '+ repName + ' = ' + repName+'Entry.node.value;\n' +
                       indent + '    ' +idxTypeKW +' '+ repName+'_rep = ' + repName+'Entry.node.key;\n'  )
        else:
            actionText += (indent + 'for(Map.Entry<'+idxTypeKW+','+valueFieldType+'> '+repName+'Entry : '+ctnrName+'.subMap('+StartKey+', '+EndKey+').entrySet()){\n' +
                       indent + '    '+valueFieldType+' '+ repName + ' = ' + repName+'Entry.getValue();\n' +
                       indent + '    ' +idxTypeKW +' '+ repName+'_rep = ' + repName+'Entry.getKey();\n'  )
    elif datastructID=='list' or (datastructID=='deque' and not willBeModifiedDuringTraversal): pass;
    elif datastructID=='deque' and willBeModifiedDuringTraversal: pass;
    else: cdErr("DSID iterateRangeFromTo:"+datastructID+" "+containerCat)
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
    itrOwner     = progSpec.getOwnerFromTypeSpec(itrTSpec)
    itrName      = repName
    containerCat = getContaineCategory(ctnrTSpec)
    [LDeclP, RDeclP, LDeclA, RDeclA] = ChoosePtrDecorationForSimpleCase(firstOwner)
    [LNodeP, RNodeP, LNodeA, RNodeA] = ChoosePtrDecorationForSimpleCase(itrOwner)
    if containerCat=='PovList': cdErr("PovList: "+repName+"   "+ctnrName) # this should be called PovList
    if containerCat=='MAP' or containerCat=="MULTIMAP":
        reqTagStr    = getReqTagString(classes, ctnrTSpec)
        if(reqTagList != None):
            firstTSpec['owner']     = progSpec.getOwnerFromTemplateArg(reqTagList[1])
            firstTSpec['fieldType'] = progSpec.getTypeFromTemplateArg(reqTagList[1])
        if datastructID=='TreeMap' or datastructID=='Java_Map':
            keyVarSpec  = {'owner':firstOwner, 'fieldType':idxTypeKW, 'codeConverter':(repName+'.getKey()')}
            firstTSpec['codeConverter'] = (repName+'.getValue()')
            iteratorTypeStr="Map.Entry"+reqTagStr
            actionText += indent + "for("+iteratorTypeStr+" " + repName+' :'+ ctnrName+".entrySet()){\n"
        else:
            keyVarSpec = {'owner':firstOwner, 'fieldType':idxTypeKW, 'codeConverter':(repName+'.node.key')}
            firstTSpec['codeConverter'] = (repName+'.node.value')
            itrType    = progSpec.fieldTypeKeyword(progSpec.getItrTypeOfDataStruct(ctnrTSpec)) + ' '
            frontItr   = ctnrName+'.front()'
            if not 'generic' in ctnrTSpec: itrType += reqTagStr
            actionText += (indent + 'for('+itrType + itrName+' ='+frontItr + '; ' + itrName + '.node!='+ctnrName+'.end().node'+'; '+repName+'.goNext()){\n')
           #actionText += (indent + "for("+itrType + itrName+' ='+frontItr + "; " + itrName + " !=" + ctnrName+RDeclP+'end()' +"; ++"+itrName  + " ){\n"
                # + indent+"    "+itrType+repName+" = *"+itrName+";\n")
    elif containerCat=="LIST":
        containedOwner = progSpec.getOwnerFromTypeSpec(ctnrTSpec)
        keyVarSpec     = {'owner':containedOwner, 'fieldType':firstType}
        [iteratorTypeStr, innerType] = convertType(firstTSpec, 'var', 'action', genericArgs, xlator)
        loopVarName=repName+"Idx";
        if(isBackward):
            actionText += (indent + "for(int "+loopVarName+'='+ctnrName+'.size()-1; ' + loopVarName +' >=0; --' + loopVarName+'){\n'
                        + indent + indent + iteratorTypeStr+' '+repName+" = "+ctnrName+".get("+loopVarName+");\n")
        else:
            actionText += (indent + "for(int "+loopVarName+"=0; " + loopVarName +' != ' + ctnrName+'.size(); ' + loopVarName+' += 1){\n'
                        + indent + indent + iteratorTypeStr+' '+repName+" = "+ctnrName+".get("+loopVarName+");\n")
    else: cdErr("iterateContainerStr() datastructID = " + datastructID)
    localVarsAlloc.append([loopCntrName, keyVarSpec])  # Tracking local vars for scope
    localVarsAlloc.append([repName, firstTSpec]) # Tracking local vars for scope
    return [actionText, loopCntrName, itrIncStr]

def codeSwitchExpr(switchKeyExpr, switchKeyTypeSpec):
    return switchKeyExpr

def codeSwitchCase(caseKeyValue, caseKeyTypeSpec):
    return caseKeyValue

###################################################### EXPRESSION CODING
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
            if(progSpec.typeIsPointer(retTypeSpec)):
                S= '('+S2+' == null)'
                retTypeSpec='bool'
            else: S+='!' + S2
        elif item0=='-':
            [S2, retTypeSpec] = codeExpr(item[1], objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs, xlator)
            S+='-' + S2
        elif item0=='[':
            count=0
            tmp="(Arrays.asList("
            for expr in item[1:-1]:
                count+=1
                [S2, exprTypeSpec] = codeExpr(expr, objsRefed, returnType, expectedTypeSpec, LorRorP_Val, genericArgs, xlator)
                if not exprTypeSpec=='noType':
                    retTypeSpec = adjustBaseTypes(exprTypeSpec, True)
                if count>1: tmp+=', '
                tmp+=S2
                if exprTypeSpec=='Long' or exprTypeSpec=='noType':
                    if '*' in S2:
                        numVal = S2
                        #print 'numVal', numVal
                    elif int(S2) > 2147483647:
                        tmp+="L"
                        retTypeSpec = 'Long'
            tmp+="))"
            retTypeKW = progSpec.fieldTypeKeyword(retTypeSpec)
            if isinstance(exprTypeSpec,str):typeKeyword = exprTypeSpec
            elif progSpec.isAContainer(returnType):
                reqType = progSpec.getContainerFirstElementType(returnType)
                typeKeyword = progSpec.fieldTypeKeyword(reqType)
                typeKeyword = adjustBaseTypes(typeKeyword, True)
            else: typeKeyword = retTypeKW
            S+='new ArrayList<'+typeKeyword+'>'+tmp   # ToDo: make this handle things other than long.
        elif item0=='{':cdErr("TODO: finish Java initialize new map")
        else:
            fTypeKW = progSpec.varTypeKeyWord(expectedTypeSpec)
            owner   = progSpec.getOwnerFromTypeSpec(expectedTypeSpec)
            if(item0[0]=="'"):    S+=codeUserMesg(item0[1:-1], xlator);   retTypeSpec='String'
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
                if retTypeSpec == 'noType' and (fTypeKW=='bool' or item0=='true' or item0=='false'):
                    retTypeSpec={'owner': owner, 'fieldType': 'bool'}
                if retTypeSpec == 'noType' and progSpec.typeIsInteger(fTypeKW):
                    retTypeSpec={'owner': owner, 'fieldType': fTypeKW}
                if retTypeSpec == 'noType' and progSpec.isStringNumeric(item0):
                    retTypeSpec={'owner': 'literal', 'fieldType': 'numeric'}

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
                codeStr="null"
                retTypeSpec={'owner':"PTR"}
            typeKeyword = progSpec.fieldTypeKeyword(retTypeSpec)
            if (len(item0[0]) > 1  and item0[0][0]==typeKeyword and item0[0][1] and item0[0][1]=='('):
                codeStr = 'new ' + codeStr
            S+=codeStr                                # Code variable reference or function call
    if retTypeSpec == 'noType': print("Warning: type Spec not found.", S)
    return [S, retTypeSpec]

######################################################
def adjustQuotesForChar(typeSpec1, typeSpec2, S):
    fieldType1 = progSpec.fieldTypeKeyword(typeSpec1)
    fieldType2 = progSpec.fieldTypeKeyword(typeSpec2)
    if fieldType1 == "char" and (fieldType2 == 'string' or fieldType2 == 'String') and S[0] == '"':
        return("'" + S[1:-1] + "'")
    return(S)

def adjustConditional(S, conditionType):
    if not isinstance(conditionType, str):
        if conditionType['owner']=='our' or conditionType['owner']=='their' or conditionType['owner']=='my' or progSpec.isStruct(conditionType['fieldType']):
            if S[0]=='!': S = S[1:]+ " == true"
            else: S+=" != null"
        elif conditionType['owner']=='me' and (conditionType['fieldType']=='flag' or progSpec.typeIsInteger(conditionType['fieldType'])):
            if S[0]=='!': S = '('+S[1:]+' == 0)'
            else: S = '('+S+') != 0'
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
            S+='System.out.print('
            count = 0
            for P in paramList:
                if(count!=0): S+=" + "
                count+=1
                [S2, argTypeSpec]=codeExpr(P[0], objsRefed, None, None, 'PARAM', genericArgs, xlator)
                if 'fieldType' in argTypeSpec:
                    fieldType = progSpec.fieldTypeKeyword(argTypeSpec)
                    fieldType = adjustBaseTypes(fieldType, False)
                else: fieldType = argTypeSpec
                if fieldType == "timeValue" or fieldType == "int" or fieldType == "double": S2 = '('+S2+')'
                elif fieldType in getInheritedEnums(): S2 = S2 + '.ordinal()'
                S+=S2
            S+=")"
            retOwner='me'
            fieldType='string'
        elif(funcName=='AllocateOrClear'):
            [varName,  varTypeSpec]=codeExpr(paramList[0][0], objsRefed, None, None, 'PARAM', genericArgs, xlator)
            S+='if('+varName+' != null){'+varName+'.clear();} else {'+varName+" = "+codeAllocater(varTypeSpec, genericArgs, xlator)+"();}"
        elif(funcName=='Allocate'):
            [varName,  varTypeSpec]=codeExpr(paramList[0][0], objsRefed, None, None, 'PARAM', genericArgs, xlator)
            fieldType = progSpec.fieldTypeKeyword(varTypeSpec)
            S+=varName+" = "+codeAllocater(varTypeSpec, genericArgs, xlator)+'('
            count=0   # TODO: As needed, make this call CodeParameterList() with modelParams of the constructor.
            if fieldType=='workerMsgThread':
                S += '"workerMsgThread"'
            else:
                for P in paramList[1:]:
                    if(count>0): S+=', '
                    [S2, argTypeSpec]=codeExpr(P[0], objsRefed, None, None, 'PARAM', genericArgs, xlator)
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
                [S2, argTypeSpec]=codeExpr(P[0][0], objsRefed, None, None, 'PARAM', genericArgs, xlator)
                [S2, isDerefd]=derefPtr(S2, argTypeSpec)
                S+='String.valueOf('+S2+')'
                fieldType='String'
    else: # Not parameters, i.e., not a function
        if(funcName=='self'):
            S+='this'

    return [S, retOwner, fieldType]

def checkIfSpecialAssignmentFormIsNeeded(AltIDXFormat, RHS, rhsType, LHS, LHSParentType, LHS_FieldType):
    # Check for string A[x] = B;  If so, render A.put(B,x)
    [containerType, idxType, owner]=getContainerType(AltIDXFormat[1], "")
    if LHSParentType == 'string' and LHS_FieldType == 'char':
        S=AltIDXFormat[0] + '= replaceCharAt(' +AltIDXFormat[0]+', '+ AltIDXFormat[2] + ', ' + RHS + ');\n'
    elif containerType == 'ArrayList':
        S=AltIDXFormat[0] + '.add(' + AltIDXFormat[2] + ', ' + RHS + ');\n'
    elif containerType == 'TreeMap' or containerType == 'Java_Map':
        S=AltIDXFormat[0] + '.put(' + AltIDXFormat[2] + ', ' + RHS + ');\n'
    elif containerType == 'RBTreeMap' or containerType[:2]=="__" and 'Map' in containerType:
        S=AltIDXFormat[0] + '.insert(' + AltIDXFormat[2] + ', ' + RHS + ');\n'
    else: cdErr("ERROR in checkIfSpecialAssignmentFormIsNeeded: containerType not found for "+ containerType)
    return S

############################################
def codeProtectBlock(mutex, criticalText, indent, xlator):
    S = indent+'MutexMngr mtxMgr = new MutexMngr('+mutex+');\n'
    S += indent+'try{\n'+indent+'    '+mutex+'.lock();\n'+criticalText+indent+'}finally{'+mutex+'.unlock();}\n'
    return(S)

def codeMain(classes, tags, objsRefed, xlator):
    return ["", ""]

def codeArgText(argFieldName, argType, argOwner, typeSpec, makeConst, typeArgList, xlator):
    return argType + " " +argFieldName

def codeStructText(classes, attrList, parentClass, classInherits, classImplements, structName, structCode, tags):
    classAttrs=''
    Platform = progSpec.fetchTagValue(tags, 'Platform')
    if len(attrList)>0:
        for attr in attrList:
            if attr=='abstract': classAttrs += 'abstract '
    if parentClass != "":
        parentClass = parentClass.replace('::', '_')
        parentClass = progSpec.getUnwrappedClassFieldTypeKeyWord(classes, structName)
        parentClass=' extends ' +parentClass
    elif classInherits!=None:
        parentClass=' extends ' + progSpec.getUnwrappedClassFieldTypeKeyWord(classes, classInherits[0][0])
    if classImplements!=None:
        # TODO: verify if classImplements is used
        #print(structName, "Implements: " , classImplements)
        parentClass+=' implements '
        count =0
        for item in classImplements[0]:
            if count>0:
                parentClass+= ', '
            parentClass+= item
            count += 1
    if structName =="GLOBAL" and Platform == 'Android':
        classAttrs = "public " + classAttrs
    S= "\n"+classAttrs +"class "+structName+''+parentClass+" {\n" + structCode + '};\n'
    typeArgList = progSpec.getTypeArgList(structName)
    if(typeArgList != None):
        templateHeader = codeTemplateHeader(structName, typeArgList)
        S=templateHeader+" {\n" + structCode + '};\n'
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

    codeDogParser.AddToObjectFromText(classes[0], classes[1], GLOBAL_CODE, 'Java special code')

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
    fTypeKW = progSpec.fieldTypeKeyword(lhsTypeSpec)
    if owner=='itr':
        itrType = progSpec.fieldTypeKeyword(progSpec.getItrTypeOfDataStruct(lhsTypeSpec))
        cvrtType = generateGenericStructName(itrType, reqTagList, genericArgs, xlator)
    localVarsAllocated.append([varName, lhsTypeSpec])  # Tracking local vars for scope
    ctnrTSpec = progSpec.getContainerSpec(lhsTypeSpec)
    isAContainer=progSpec.isNewContainerTempFunc(lhsTypeSpec)
    fTypeKW = adjustBaseTypes(cvrtType, isAContainer)
    if isinstance(ctnrTSpec, str) and ctnrTSpec == None:
        if(fieldDef['value']):
            [S2, rhsTypeSpec]=codeExpr(fieldDef['value'][0], objsRefed, None, None, 'RVAL', genericArgs, xlator)
            RHS = S2
            assignValue=' = '+ RHS
            #TODO: make test case
        else: assignValue=''
    elif(fieldDef['value']):
        [S2, rhsTypeSpec]=codeExpr(fieldDef['value'][0], objsRefed, lhsTypeSpec, None, 'RVAL', genericArgs, xlator)
        S2=checkForTypeCastNeed(cvrtType, rhsTypeSpec, S2)
        RHS = S2
        if varTypeIsValueType(fTypeKW):
            assignValue=' = '+ RHS
        else:
        #TODO: make test case
            constructorExists=False  # TODO: Use some logic to know if there is a constructor, or create one.
            if (constructorExists):
                assignValue=' = new ' + fTypeKW +'('+ RHS + ')'
            else:
                assignValue= ' = '+ RHS   #' = new ' + fTypeKW +'();\n'+ indent + varName+' = '+RHS
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
                if not isinstance(rhsType, str) and fTypeKW==rhsType[0]:
                    assignValue = " = " + CPL   # Act like a copy constructor
                elif 'codeConverter' in paramTypeList[0]: #ktl 12.14.17
                    assignValue = " = " + CPL
                else:
                    if isJavaPrimativeType(fTypeKW): assignValue  = " =  " + CPL
                    else: assignValue  = " = new " + fTypeKW + CPL
            if(assignValue==''): assignValue = ' = '+getCodeAllocStr(fTypeKW, owner)+CPL
        elif varTypeIsValueType(fTypeKW):
            if fTypeKW == 'long' or fTypeKW == 'int' or fTypeKW == 'float'or fTypeKW == 'double': assignValue=' = 0'
            elif fTypeKW == 'string':  assignValue=' = ""'
            elif fTypeKW == 'boolean': assignValue=' = false'
            elif fTypeKW == 'char':    assignValue=" = ' '"
            else: assignValue=''
        else:assignValue= " = new " + fTypeKW + "()"
    varDeclareStr= fTypeKW + " " + varName + assignValue
    return(varDeclareStr)

def codeIncrement(varName):
    return "++" + varName

def codeDecrement(varName):
    return "--" + varName

def varTypeIsValueType(convertedType):
    if (convertedType=='int' or convertedType=='long' or convertedType=='byte' or convertedType=='boolean' or convertedType=='char'
       or convertedType=='float' or convertedType=='double' or convertedType=='short'):
        return True
    return False

def codeVarFieldRHS_Str(fieldName, cvrtType, innerType, typeSpec, paramList, objsRefed, isAllocated, typeArgList, genericArgs, xlator):
    fieldValueText=""
    fieldOwner=progSpec.getTypeSpecOwner(typeSpec)
    if fieldOwner=='we':
        cvrtType = cvrtType.replace('static ', '', 1)
    if (not varTypeIsValueType(cvrtType) and (fieldOwner=='me' or fieldOwner=='we' or fieldOwner=='const')):
        if fieldOwner =="const": cvrtType = innerType
        if paramList!=None:
            #TODO: make test case
            if paramList[-1] == "^&useCtor//8":
                del paramList[-1]
            [CPL, paramTypeList] = codeParameterList(fieldName, paramList, None, objsRefed, genericArgs, xlator)
            fieldValueText=" = new " + cvrtType + CPL
        elif typeArgList == None:
            fieldValueText=" = new " + cvrtType + "()"
    return fieldValueText

def codeConstField_Str(convertedType, fieldName, fieldValueText, className, indent, xlator ):
    defn = indent + convertedType + ' ' + fieldName + fieldValueText +';\n';
    decl = ''
    return [defn, decl]

def codeVarField_Str(convertedType, typeSpec, fieldName, fieldValueText, className, tags, typeArgList, indent):
    # TODO: make test case
    S=""
    fieldOwner=progSpec.getTypeSpecOwner(typeSpec)
    Platform = progSpec.fetchTagValue(tags, 'Platform')
    # TODO: make next line so it is not hard coded
    if(Platform == 'Android' and (convertedType == "TextView" or convertedType == "ViewGroup" or convertedType == "CanvasView" or convertedType == "FragmentTransaction" or convertedType == "FragmentManager" or convertedType == "Menu" or convertedType == "static GLOBAL" or convertedType == "Toolbar" or convertedType == "NestedScrollView" or convertedType == "SubMenu" or convertedType == "APP" or convertedType == "AssetManager" or convertedType == "ScrollView" or convertedType == "LinearLayout" or convertedType == "GUI"or convertedType == "CheckBox" or convertedType == "HorizontalScrollView"or convertedType == "GUI_ZStack"or convertedType == "widget"or convertedType == "GLOBAL")):
        S += indent + "public " + convertedType + ' ' + fieldName +';\n';
    else:
        S += indent + "public " + convertedType + ' ' + fieldName + fieldValueText +';\n';
    return [S, '']

###################################################### CONSTRUCTORS
def codeConstructors(className, ctorArgs, ctorOvrRide, ctorInit, copyCtorArgs, funcBody, callSuper, xlator):
    if callSuper:
        funcBody = '        super();\n' + funcBody
    withArgConstructor = ''
    if ctorArgs != '':
        withArgConstructor = "    public " + className + "(" + ctorArgs+"){\n"+funcBody+ ctorInit+"    };\n"
    copyConstructor = "    public " + className + "(final " + className + " fromVar" +"){\n        "+ className + " toVar = new "+ className + "();\n" +copyCtorArgs+"    };\n"
    noArgConstructor = "    public "  + className + "(){\n"+funcBody+'\n    };\n'
    # TODO: remove hardCoding
    if (className =="ourSubMenu" or className =="GUI"or className =="CanvasView"or className =="APP"or className =="GUI_ZStack"):
        return ""
    return withArgConstructor + copyConstructor + noArgConstructor

def codeConstructorInit(fieldName, count, defaultVal, xlator):
    return "        " + fieldName+"= arg_"+fieldName+";\n"

def codeConstructorArgText(argFieldName, count, argType, defaultVal, xlator):
    return argType + " arg_"+ argFieldName

def codeCopyConstructor(fieldName, convertedType, isTemplateVar, xlator):
    if isTemplateVar: return ""
    return "        toVar."+fieldName+" = fromVar."+fieldName+";\n"

def codeConstructorCall(className):
    return '        INIT();\n'

def codeSuperConstructorCall(parentClassName):
    return '        '+parentClassName+'();\n'

def codeFuncHeaderStr(className, fieldName, typeDefName, argListText, localArgsAllocated, inheritMode, overRideOper, isConstructor, typeArgList, typeSpec, indent):
#    if fieldName == 'init':
#        fieldName = fieldName+'_'+className
    if inheritMode=='pure-virtual':
        typeDefName = 'abstract '+typeDefName
    structCode='\n'; funcDefCode=''; globalFuncs='';
    if(className=='GLOBAL'):
        if fieldName=='main':
            structCode += indent + "public static void " + fieldName +" (String[] args)";
            #localArgsAllocated.append(['args', {'owner':'me', 'fieldType':'String', 'argList':None}])
        else:
            structCode += indent + "public " + typeDefName + ' ' + fieldName +"("+argListText+")"
    else:
        structCode += indent + "public " + typeDefName +' ' + fieldName +"("+argListText+")"
    if inheritMode=='pure-virtual':
        structCode += ";\n"
    elif inheritMode=='override': pass
    return [structCode, funcDefCode, globalFuncs]

def getVirtualFuncText(field):
    return ""

def codeTypeArgs(typeArgList):
    print("TODO: finish codeTypeArgs")

def codeTemplateHeader(structName, typeArgList):
    templateHeader = "\nclass "+structName+"<"
    count = 0
    for typeArg in typeArgList:
        if(count>0):templateHeader+=", "
        templateHeader+=typeArg
        if isComparableType(typeArg):templateHeader+=" extends Comparable"
        count+=1
    templateHeader+=">"
    return(templateHeader)

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
    return '((int)'+itemToAlterType+')'

#######################################################

def includeDirective(libHdr):
    S = 'import '+libHdr+';\n'
    return S

def generateMainFunctionality(classes, tags):
    # TODO: Some deInitialize items should automatically run during abort().
    # TODO: System initCode should happen first in initialize, last in deinitialize.

    runCode = progSpec.fetchTagValue(tags, 'runCode')
    if runCode==None: runCode=""
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
    xlators['iteratorsUseOperators'] = "False"
    xlators['renderGenerics']        = "True"
    xlators['renameInitFuncs']       = "False"
    xlators['codeFactor']                   = codeFactor
    xlators['codeComparisonStr']            = codeComparisonStr
    xlators['codeIdentityCheck']            = codeIdentityCheck
    xlators['derefPtr']                     = derefPtr
    xlators['checkForTypeCastNeed']         = checkForTypeCastNeed
    xlators['adjustConditional']            = adjustConditional
    xlators['includeDirective']             = includeDirective
    xlators['codeMain']                     = codeMain
    xlators['produceTypeDefs']              = produceTypeDefs
    xlators['addSpecialCode']               = addSpecialCode
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
    xlators['iterateRangeFromTo']           = iterateRangeFromTo
    xlators['iterateContainerStr']          = iterateContainerStr
    xlators['getEnumStr']                   = getEnumStr
    xlators['getEnumStructStr']             = getEnumStructStr
    xlators['getEnumStringifyFunc']         = getEnumStringifyFunc
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
    xlators['codeSwitchExpr']               = codeSwitchExpr
    xlators['codeSwitchCase']               = codeSwitchCase
    xlators['codeSwitchBreak']              = codeSwitchBreak
    xlators['codeCopyConstructor']          = codeCopyConstructor
    xlators['codeRangeSpec']                = codeRangeSpec
    xlators['codeConstField_Str']           = codeConstField_Str
    xlators['codeConstructorCall']          = codeConstructorCall
    xlators['codeSuperConstructorCall']     = codeSuperConstructorCall
    xlators['getVirtualFuncText']           = getVirtualFuncText
    xlators['getUnwrappedClassOwner']       = getUnwrappedClassOwner
    xlators['makePtrOpt']                   = makePtrOpt
    xlators['adjustBaseTypes']              = adjustBaseTypes
    xlators['codeProtectBlock']             = codeProtectBlock
    xlators['convertToInt']                 = convertToInt
    xlators['getReqTagString']              = getReqTagString
    return(xlators)
