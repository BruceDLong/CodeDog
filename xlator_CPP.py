#xlator_CPP.py
import progSpec
import codeDogParser
from xlator import Xlator
from progSpec import cdlog, cdErr, logLvl
from codeGenerator import CodeGenerator

class Xlator_CPP(Xlator):
    codeGen               = CodeGenerator()
    LanguageName          = "C++"
    BuildStrPrefix        = "g++ -g -std=gnu++17  "
    fileExtension         = ".cpp"
    typeForCounterInt     = "int64_t"
    GlobalVarPrefix       = ""
    PtrConnector          = "->"                      # Name segment connector for pointers.
    ObjConnector          = "::"                      # Name segment connector for Classes.
    NameSegConnector      = "."
    NameSegFuncConnector  = "."
    doesLangHaveGlobals   = True
    funcBodyIndent        = ""
    funcsDefInClass       = False
    MakeConstructors      = True
    blockPrefix           = ""
    usePrefixOnStatics    = False
    iteratorsUseOperators = True
    renderGenerics        = "False"
    renameInitFuncs       = False
    useAllCtorArgs        = False
    nullValue             = "nullptr"
    hasMacros             = True

    ###### Routines to track types of identifiers and to look up type based on identifier.
    def implOperatorsAsFuncs(self, fTypeKW):
        return False
    def getContainerType(self, typeSpec, actionOrField):
        idxType=''
        if progSpec.isAContainer(typeSpec):
            ctnrTSpec = progSpec.getContainerSpec(typeSpec)
            if 'owner' in ctnrTSpec: owner=progSpec.getOwnerFromTypeSpec(ctnrTSpec)
            else: owner = 'me'
            if 'indexType' in ctnrTSpec:
                if 'IDXowner' in ctnrTSpec['indexType']:
                    idxOwner = ctnrTSpec['indexType']['IDXowner'][0]
                    idxType  = ctnrTSpec['indexType']['idxBaseType'][0][0]
                    idxType  = self.applyOwner(ctnrTSpec, idxOwner, idxType)
                else:
                    idxType=ctnrTSpec['indexType']['idxBaseType'][0][0]
            if(isinstance(ctnrTSpec['datastructID'], str)):
                datastructID = ctnrTSpec['datastructID']
            else:   # it's a parseResult
                datastructID = ctnrTSpec['datastructID'][0]
            if idxType[0:4]=='uint': idxType+='_t'
            if(datastructID=='list'): datastructID = "deque"
            if(datastructID=='iterableList'): datastructID = "list"
        else:
            owner = progSpec.getOwnerFromTypeSpec(typeSpec)
            datastructID = 'None'
        return [datastructID, idxType, owner]

    def adjustBaseTypes(self, fieldType):
        if(isinstance(fieldType, str)):
            if(fieldType=='uint8' or fieldType=='uint16'): fieldType='uint32'
            elif(fieldType=='int8' or fieldType=='int16'): fieldType='int32'
            if(fieldType=='uint32' or fieldType=='uint64' or fieldType=='int32' or fieldType=='int64'):
                langType=fieldType+'_t'
            else:
                langType=progSpec.flattenObjectName(fieldType)
        else: langType=progSpec.flattenObjectName(fieldType[0])
        return langType

    def applyOwner(self, typeSpec, owner, langType):
        if owner=='me':
            langType = langType
        elif owner=='my':
            langType = "unique_ptr<"+langType + ' >'
        elif owner=='our':
            langType = "shared_ptr<"+langType + ' >'
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
        elif owner=='dblTheir':
            langType += '**'
        else: cdErr("ERROR: Owner of type not valid '" + owner + "'")
        return langType

    def getUnwrappedClassOwner(self, classes, typeSpec, fieldType, varMode, ownerIn):
        ownerOut = ownerIn
        baseType = progSpec.isWrappedType(classes, fieldType)
        if baseType!=None:  # TODO: When this is all tested and stable, un-hardcode and optimize this!!!!!
            if 'ownerMe' in baseType:
                ownerOut = 'their'
            else:
                if varMode=='var' and progSpec.isOldContainerTempFunc(typeSpec):
                    ownerOut=progSpec.getOwnerFromTypeSpec(baseType)   # TODO: remove this condition: accomodates old list type generated in stringStructs
                else:
                    ownerOut=ownerIn
        return ownerOut

    def getReqTagString(self, classes, typeSpec):
        reqTagStr  = ""
        reqTagList = progSpec.getReqTagList(typeSpec)
        if(reqTagList != None):
            reqTagStr = "<"
            count = 0
            for reqTag in reqTagList:
                reqOwnr     = progSpec.getOwnerFromTemplateArg(reqTag)
                varTypeKW   = progSpec.getTypeFromTemplateArg(reqTag)
                unwrappedOwner=self.getUnwrappedClassOwner(classes, typeSpec, varTypeKW, 'alloc', reqOwnr)
                unwrappedKW = progSpec.getUnwrappedClassFieldTypeKeyWord(classes, varTypeKW)
                unwrappedKW = self.adjustBaseTypes(unwrappedKW)
                reqType     = self.applyOwner(typeSpec, unwrappedOwner, unwrappedKW)
                if(count>0):reqTagStr += ", "
                reqTagStr += reqType
                count += 1
            reqTagStr += ">"
        return reqTagStr

    def xlateLangType(self, classes, typeSpec, owner, fTypeKW, varMode, actionOrField):
        # varMode is 'var' or 'arg' or 'alloc'. Large items are passed as pointers
        langType  = self.adjustBaseTypes(fTypeKW)
        innerType = langType
        reqTagStr = self.getReqTagString(classes, typeSpec)
        langType += reqTagStr
        if reqTagStr != '':innerType = langType
        if varMode != 'alloc': langType = self.applyOwner(typeSpec, owner, langType)

        if progSpec.isNewContainerTempFunc(typeSpec):
            return [langType, innerType]

        if progSpec.isOldContainerTempFunc(typeSpec):
            ctnrTSpec = progSpec.getContainerSpec(typeSpec)
            if(ctnrTSpec): # Make list, map, etc
                [containerType, idxType, idxOwner]=self.getContainerType(typeSpec, '')
                if 'owner' in ctnrTSpec:
                    ctnrOwner = progSpec.getOwnerFromTypeSpec(ctnrTSpec)
                else: ctnrOwner='me'
                idxType  = self.adjustBaseTypes(idxType)
                if idxType=='timeValue': idxType = 'int64_t'
                if containerType=='deque':
                    if varMode == 'alloc': langType = self.applyOwner(typeSpec, owner, langType)
                    langType="deque< "+langType+" >"
                elif containerType=='list':
                    if varMode == 'alloc': langType = self.applyOwner(typeSpec, owner, langType)
                    langType="list< "+langType+" >"
                elif containerType=='map':
                    if varMode == 'alloc': langType = self.applyOwner(typeSpec, owner, langType)
                    langType="map< "+idxType+', '+langType+" >"
                elif containerType=='multimap':
                    if varMode == 'alloc': langType = self.applyOwner(typeSpec, owner, langType)
                    langType="multimap< "+idxType+', '+langType+" >"
                innerType = langType
                if varMode != 'alloc':
                    langType=self.applyOwner(typeSpec, ctnrOwner, langType)
        return [langType, innerType]

    def makePtrOpt(self, typeSpec):
        return('')

    def codeIteratorOperation(self, itrCommand, fieldType):
        result = ''
        if(fieldType[0]=='deque'): # TODO: this should be like "If this iterator doesn't return BOTH key and value  ...". 'deque' is just one case.
            if itrCommand=='val':   result='*(%0)'
        else:
            if itrCommand=='goNext':  result='%0++'
            elif itrCommand=='goPrev':result='--%0'
            elif itrCommand=='key':   result='%0->first'
            elif itrCommand=='val':   result='%0->second'
        return result

    def recodeStringFunctions(self, name, typeSpec, lenParams):
        if name == "size": name = "length"
        elif name == "subStr": name = "substr"

        return [name, typeSpec]

    def langStringFormatterCommand(self, fmtStr, argStr):
        S='strFmt('+'"'+ fmtStr +'"'+ argStr +')'
        return S

    def LanguageSpecificDecorations(self, S, typeSpec, owner, LorRorP_Val):
        return S

    def convertToInt(self, S, typeSpec):
        return S

    def checkForTypeCastNeed(self, lhsTSpec, rhsTSpec, RHS):
        return RHS

    def getTheDerefPtrMods(self, itemTypeSpec):
        if itemTypeSpec!=None and isinstance(itemTypeSpec, dict) and 'owner' in itemTypeSpec:
            if progSpec.isNewContainerTempFunc(itemTypeSpec): return ['', '', False]
            if progSpec.typeIsPointer(itemTypeSpec):
                owner=progSpec.getTypeSpecOwner(itemTypeSpec)
                if progSpec.isAContainer(itemTypeSpec):
                    if owner=='itr':
                        containerType = progSpec.getDatastructID(itemTypeSpec)
                        if containerType =='map' or containerType == 'multimap':
                            return ['', '->second', False]
                    return ['(*', ')', False]
                else:
                    if owner!='itr':
                        return ['(*', ')', True]
        return ['', '', False]

    def derefPtr(self, varRef, itemTypeSpec):
        [leftMod, rightMod, isDerefd] = self.getTheDerefPtrMods(itemTypeSpec)
        S = leftMod + varRef + rightMod
        return [S, isDerefd]

    def ChoosePtrDecorationForSimpleCase(self, owner):
        if(owner=='our' or owner=='my' or owner=='their'):
            return ['','->',  '(*', ')']
        else: return ['','.',  '','']

    def chooseVirtualRValOwner(self, LVAL, RVAL):
        # Returns left and right text decorations for RHS of function arguments, return values, etc.
        if RVAL==0 or RVAL==None or isinstance(RVAL, str): return ['',''] # This happens e.g., string.size() # TODO: fix this.
        if LVAL==0 or LVAL==None or isinstance(LVAL, str): return ['', '']
        LeftOwner =progSpec.getTypeSpecOwner(LVAL)
        RightOwner=progSpec.getTypeSpecOwner(RVAL)
        if(LeftOwner=="id_their" and RightOwner=="id_their"): return ["&", ""]
        if LeftOwner == RightOwner: return ["", ""]
        if LeftOwner!='itr' and RightOwner=='itr':
            # TODO: test this change.  This looks like code that handled codeDog 1.0 container iterators, which is now handled in codeIteratorOperation()
            #return ["", "->second"]
            return ["", ""]
        if LeftOwner=='me' and progSpec.typeIsPointer(RVAL):
            return ["(*", "   )"]
        if progSpec.typeIsPointer(LVAL) and RightOwner=='me':
            return ["&", '']
        if LeftOwner=='their' and (RightOwner=='our' or RightOwner=='my'): return ['','.get()']
        return ['','']

    def determinePtrConfigForNewVars(self, lhsTypeSpec, rhsTypeSpec, useCtor):
        leftOwner =progSpec.getTypeSpecOwner(lhsTypeSpec)
        rightOwner=progSpec.getTypeSpecOwner(rhsTypeSpec)
        if ((leftOwner=="me" or leftOwner=="literal") and rightOwner=="our"):
            return["*", ""]
        elif leftOwner=='their' and rightOwner == 'our' and not useCtor:
            return["*", ""]
        elif leftOwner=='their' and rightOwner == 'our' :
            return["", ".get()"]
        return["", ""]

    def determinePtrConfigForAssignments(self, LVAL, RVAL, assignTag, codeStr):
        #TODO: make test case
        # Returns left and right text decorations for both LHS and RHS of assignment
        if RVAL==0 or RVAL==None or isinstance(RVAL, str): return ['','',  '',''] # This happens e.g., string.size() # TODO: fix this.
        if LVAL==0 or LVAL==None or isinstance(LVAL, str): return ['','',  '','']
        LeftOwner =progSpec.getTypeSpecOwner(LVAL)
        RightOwner=progSpec.getTypeSpecOwner(RVAL)
        if not isinstance(assignTag, str):
            assignTag = assignTag[0]
        if progSpec.typeIsPointer(LVAL) and progSpec.typeIsPointer(RVAL):
            if assignTag=='deep' :return ['(*',')',  '(*',')']
            elif LeftOwner=='their' and (RightOwner=='our' or RightOwner=='my'): return ['','', '','.get()']
            else: return ['','',  '', '']
        if LeftOwner == RightOwner: return ['','',  '','']
        if LeftOwner=='me' and progSpec.typeIsPointer(RVAL):
            [leftMod, rightMod, isDerefd] = self.getTheDerefPtrMods(RVAL)
            return ['','',  leftMod, rightMod]  # ['', '', "(*", ")"]
        if progSpec.typeIsPointer(LVAL) and RightOwner=='me':
            if assignTag!="" or assignTag=='deep':return ['(*',')',  '', '']
            else: return ['','',  "&", '']
        if progSpec.typeIsPointer(LVAL) and RightOwner=='literal':return ['(*',')',  '', '']
        if progSpec.typeIsPointer(LVAL) and RightOwner=='const':return ['(*',')', '','']
        return ['','',  '','']

    def codeSpecialParamList(self, tSpec, CPL):
        return CPL

    def codeXlatorAllocater(self, tSpec, genericArgs):
        S     = ''
        owner = progSpec.getTypeSpecOwner(tSpec)
        [cvrtType, innerType]  = self.codeGen.convertType(tSpec, 'alloc', '', genericArgs)
        if(owner=='our'): S="make_shared<"+cvrtType+">"
        elif(owner=='my'): S="make_unique<"+cvrtType+">"
        elif(owner=='their'): S="new "+cvrtType
        elif(owner=='me'): cdErr("Cannot allocate a 'me' variable. (" + cvrtType + ')')
        elif(owner=='we'): cdErr("Cannot allocate a 'we' variable. (" + varTypeStr + ')')
        elif(owner=='const'): cdErr("Cannot allocate a 'const' variable.")
        else: cdErr("Cannot allocate variable because owner is " + owner+".")
        return S

    def getConstIntFieldStr(self, fieldName, fieldValue, intSize):
        S= "static const uint64_t "+fieldName+ " = " + fieldValue+ ";"
        return(S)

    def getEnumStr(self, fieldName, enumList):
        S = "\n    enum " + fieldName +" {"
        enumSize = len (enumList)
        count=0
        for enumName in enumList:
            S += enumName+"="+hex(count)
            count=count+1
            if(count<enumSize): S += ", "
        S += "};\n";
        return(S)

    def getEnumStringifyFunc(self, className, enumList):
        S = "deque<string> {}Strings = {{".format(className)
        S += '"{}"'.format('", "'.join(enumList))
        S += '};\n\n'
        return S

    def codeIdentityCheck(self, S, S2, retType1, retType2, opIn):
        S2 = self.adjustQuotesForChar(retType1, retType2, S2)
        leftOwner  = progSpec.getTypeSpecOwner(retType1)
        rightOwner = progSpec.getTypeSpecOwner(retType2)
        if opIn == '===' or opIn == '!==':
            if progSpec.typeSpecsAreCompatible(retType1, retType2):
                return S+ opIn[:2] +S2
            elif progSpec.typeIsPointer(retType1) and progSpec.typeIsPointer(retType2):
                if leftOwner =='our' or leftOwner =='my': S+='.get()'
                if rightOwner=='our' or rightOwner=='my': S2+='.get()'
                return "(void*)("+ S +") "+opIn[:2]+" (void*)("+S2+")"
            else:
                return S+ opIn[:2] +S2
        else:
            if (opIn == '=='): opOut=' == '
            elif (opIn == '!='): opOut=' != '
            if not(leftOwner=='itr' and rightOwner=='itr'):
                [S_derefd, isDerefd] = self.derefPtr(S, retType1)
                if S2!='NULL' and S2!='nullptr': S=S_derefd
                [S2, isDerefd]=self.derefPtr(S2, retType2)
            return S+ opOut+S2
        return S

    def codeComparisonStr(self, S, S2, retType1, retType2, op):
        if (op == '<'): S+=' < '
        elif (op == '>'): S+=' > '
        elif (op == '<='): S+=' <= '
        elif (op == '>='): S+=' >= '
        else: print("ERROR: One of <, >, <= or >= expected in code generator."); exit(2)
        S2 = self.adjustQuotesForChar(retType1, retType2, S2)
        [S2, isDerefd]=self.derefPtr(S2, retType2)
        S+=S2
        return S

    ###################################################### CONTAINERS
    def getContaineCategory(self, containerSpec):
        fromImpl=progSpec.getFromImpl(containerSpec)
        if fromImpl and 'implements' in fromImpl: return fromImpl['implements']
        fTypeKW = progSpec.fieldTypeKeyword(containerSpec)
        if fTypeKW=='string':     return 'string'
        if fTypeKW=='PovList':    return 'PovList'
        if fTypeKW=='CPP_Map':    return 'Map'
        if fTypeKW=='list':       return 'List'
        if fTypeKW=='CPP_Deque':  return 'List'
        if 'Multimap' in fTypeKW: return 'Multimap'
        return None

    def getContainerTypeInfo(self, containerType, name, idxType, typeSpecIn, paramList, genericArgs):
        convertedIdxType = ""
        typeSpecOut = typeSpecIn
        if progSpec.isNewContainerTempFunc(typeSpecIn): return(name, typeSpecOut, paramList, convertedIdxType)
        if containerType=='deque' or  containerType=='list':
            if name=='at' or name=='resize': pass
            elif name=='size' : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
            elif name=='insert'   : typeSpecOut={'owner':'me', 'fieldType': 'void', 'argList':[{'typeSpec':{'owner':'itr'}}, {'typeSpec':typeSpecIn}]}
            elif name=='insertIdx': typeSpecOut={'owner':'me', 'fieldType': 'void', 'argList':[{'typeSpec':{'owner':'itr'}}, {'typeSpec':typeSpecIn}]}; typeSpecOut['codeConverter']='%0.insert((%0.begin()+%1), %2)'
            elif name=='InsertIdx': typeSpecOut={'owner':'me', 'fieldType': 'void', 'argList':[{'typeSpec':{'owner':'itr'}}, {'typeSpec':typeSpecIn}]}; typeSpecOut['codeConverter']='%0->insert((%0->begin()+%1), %2)'
            elif name=='clear'    : typeSpecOut={'owner':'me', 'fieldType': 'void'}
            elif name=='erase'    : name='erase';  typeSpecOut['owner']='itr';
            elif name=='deleteNth': typeSpecOut['codeConverter']='%0->erase(%0->begin()+%1)'; typeSpecOut['owner']='itr';
            elif name=='DeleteNth': typeSpecOut['codeConverter']='%0.erase(%0.begin()+%1)'; typeSpecOut['owner']='itr';
            elif name=='front'    : name='begin()';  typeSpecOut['owner']='itr'; paramList=None;
            elif name=='back'     : name='rbegin()'; typeSpecOut['owner']='itr'; paramList=None;
            elif name=='end'      : name='end()';    typeSpecOut['owner']='itr'; paramList=None;
            elif name=='rend'     : name='rend()';   typeSpecOut['owner']='itr'; paramList=None;
            elif name=='nthItr'   : typeSpecOut['codeConverter']='(%0->begin()+%1)'; typeSpecOut['owner']='itr';
            elif name=='first'    : name='front()';  paramList=None;
            elif name=='last'     : name='back()';   paramList=None;
            elif name=='popFirst' : name='pop_front'
            elif name=='popLast'  : name='pop_back'
            elif name=='pushFirst': name='push_front';# typeSpecOut={'owner':'me', 'fieldType': 'void', 'argList':[{'typeSpec':typeSpecIn}]}
            elif name=='pushLast' : name='push_back'; # typeSpecOut={'owner':'me', 'fieldType': 'void', 'argList':[{'typeSpec':typeSpecIn}]}
            elif name=='isEmpty'  : name='empty';     typeSpecOut={'owner':'me', 'fieldType': 'bool'}
            elif name=='itmMode'  or name=='tag' or name=='value'  or name=='format' or name=='itmItr' or True: pass # temp fix
            else: print("Unknown deque or list command:", containerType + '::' +name); exit(2);
        elif containerType=='map':
            if idxType=='timeValue': convertedIdxType = 'int64_t'
            else: convertedIdxType=self.adjustBaseTypes(idxType)
            [convertedItmType, innerType] = self.codeGen.convertType(typeSpecOut, 'var', '', genericArgs)
            if name=='at': pass
            elif name=='containsKey'   :  typeSpecOut={'owner':'me', 'fieldType': 'bool'}; typeSpecOut['codeConverter']='(%0.count(%1)>0)';
            elif name=='containsKey2'   :  typeSpecOut={'owner':'me', 'fieldType': 'bool'}; typeSpecOut['codeConverter']='(%0->count(%1)>0)';
            elif name=='size'     : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
            elif name=='insert'   : typeSpecOut['codeConverter']='insert(pair<'+convertedIdxType+', '+convertedItmType+'>(%1, %2))';
            elif name=='clear'    : typeSpecOut={'owner':'me', 'fieldType': 'void'}
            elif name=='find'     : name='find';     typeSpecOut['owner']='itr'; typeSpecOut['fieldType']=convertedItmType;
            elif name=='lower_bound'     : name='lower_bound';     typeSpecOut['owner']='itr'; typeSpecOut['fieldType']=convertedItmType;
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
            elif name=='isEmpty'  : name='empty';     typeSpecOut={'owner':'me', 'fieldType': 'bool'}
            else: print("Unknown map command:", name); exit(2);
        elif containerType=='multimap':
            if idxType=='timeValue': convertedIdxType = 'int64_t'
            else: convertedIdxType=self.adjustBaseTypes(idxType)
            [convertedItmType, innerType] = self.codeGen.convertType(typeSpecOut, 'var', '', genericArgs)
            if name=='at': pass
            elif name=='containsKey'   :  typeSpecOut={'owner':'me', 'fieldType': 'bool'}; typeSpecOut['codeConverter']='count(%1)>=1';
            elif name=='size'     : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
            elif name=='insert'   : typeSpecOut['codeConverter']='insert(pair<'+convertedIdxType+', '+convertedItmType+'>(%1, %2))';
            elif name=='clear'    : typeSpecOut={'owner':'me', 'fieldType': 'void'}
            elif name=='find'     : name='find';     typeSpecOut['owner']='itr'; typeSpecOut['fieldType']=convertedItmType;
            elif name=='erase'    : name='erase';  typeSpecOut['owner']='itr';
            elif name=='front'    : name='begin()';  typeSpecOut['owner']='itr'; paramList=None;
            elif name=='back'     : name='rbegin()'; typeSpecOut['owner']='itr'; paramList=None;
            elif name=='end'      : name='end()';    typeSpecOut['owner']='itr'; paramList=None;
            elif name=='rend'     : name='rend()';   typeSpecOut['owner']='itr'; paramList=None;
            elif name=='first'    : name='begin()->second';  paramList=None;
            elif name=='last'     : name='rbegin()->second'; paramList=None;
            elif name=='popFirst' : name='%0.erase(%0.begin())'; paramList=None;
            elif name=='popLast'  : name='pop_back'
            elif name=='isEmpty'  : name='empty';     typeSpecOut={'owner':'me', 'fieldType': 'bool'}
            else: print("Unknown multimap command:", name); exit(2);
        elif containerType=='tree': # TODO: Make trees work
            if name=='insert' or name=='erase': pass
            elif name=='size' : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
            elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
            else: print("Unknown tree command:", name); exit(2)
        elif containerType=='graph': # TODO: Make graphs work
            if name=='insert' or name=='erase': pass
            elif name=='size' : typeSpecOut={'owner':'me', 'fieldType': 'uint32'}
            elif name=='clear': typeSpecOut={'owner':'me', 'fieldType': 'void'}
            else: print("Unknown graph command:", name); exit(2);
        elif containerType=='stream': # TODO: Make stream work
            pass
        elif containerType=='filesystem': # TODO: Make filesystem work
            pass
        else: print("Unknown container type:", containerType); exit(2);
        return(name, typeSpecOut, paramList, convertedIdxType)

    def codeArrayIndex(self, idx, containerType, LorR_Val, previousSegName, idxTypeSpec):
        if 'owner' in idxTypeSpec and (idxTypeSpec['owner']=='their' or idxTypeSpec['owner']=='our' or idxTypeSpec['owner']=='itr'):
            idx = "*"+idx
        S= '[' + idx +']'
        return S
    ###################################################### CONTAINER REPETITIONS
    def codeRangeSpec(self, traversalMode, ctrType, repName, S_low, S_hi, indent):
        if(traversalMode=='Forward' or traversalMode==None):
            S = indent + "for("+ctrType+" " + repName+'='+ S_low + "; " + repName + "!=" + S_hi +"; "+ self.codeIncrement(repName) + "){\n"
        elif(traversalMode=='Backward'):
            S = indent + "for("+ctrType+" " + repName+'='+ S_hi + "-1; " + repName + ">=" + S_low +"; --"+ repName + "){\n"
        return (S)

    def iterateRangeFromTo(self, classes,localVarsAlloc,StartKey,EndKey,ctnrTSpec,repName,ctnrName,indent):
        willBeModifiedDuringTraversal=True   # TODO: Set this programatically later.
        [datastructID, idxTypeKW, ctnrOwner]=self.getContainerType(ctnrTSpec, 'action')
        actionText   = ""
        loopCntrName = ""
        firstOwner   = progSpec.getContainerFirstElementOwner(ctnrTSpec)
        firstType    = progSpec.fieldTypeKeyword(ctnrTSpec)
        firstTSpec   = {'owner':firstOwner, 'fieldType':firstType}
        itrName      = repName + "Itr"
        reqTagList   = progSpec.getReqTagList(ctnrTSpec)
        containerCat = self.getContaineCategory(ctnrTSpec)
        if progSpec.ownerIsPointer(ctnrOwner): connector="->"
        else: connector = "."
        if containerCat=="Map" or containerCat=="Multimap":
            if(reqTagList != None):
                firstTSpec['owner']     = progSpec.getOwnerFromTemplateArg(reqTagList[1])
                firstTSpec['fieldType'] = progSpec.getTypeFromTemplateArg(reqTagList[1])
            keyVarSpec = {'owner':'itr', 'fieldType':firstType, 'codeConverter':(repName+'.first')}
            loopCntrName  = repName+'_key'
            firstTSpec['codeConverter'] = (repName+'.second')
            localVarsAlloc.append([loopCntrName, keyVarSpec])  # Tracking local vars for scope
            localVarsAlloc.append([repName, firstTSpec]) # Tracking local vars for scope
            actionText += (indent + "for( auto " + itrName+' ='+ ctnrName+connector+'lower_bound('+StartKey+')' + "; " + itrName + " !=" + ctnrName+connector+'upper_bound('+EndKey+')' +"; ++"+ repName + "Itr ){\n"
                        + indent+"    "+"auto "+repName+" = *"+itrName+";\n")
        elif datastructID=='List' and not willBeModifiedDuringTraversal: pass;
        elif datastructID=='List' and willBeModifiedDuringTraversal: pass;
        else:
            print("DSID iterateRangeFromTo:",datastructID,containerCat)
            exit(2)
        return [actionText, loopCntrName]

    def iterateContainerStr(self, classes,localVarsAlloc,ctnrTSpec,repName,ctnrName,isBackward,indent,genericArgs):
        #TODO: handle isBackward
        willBeModifiedDuringTraversal=True   # TODO: Set this programatically later.
        [datastructID, idxTypeKW, ctnrOwner]=self.getContainerType(ctnrTSpec, 'action')
        actionText   = ""
        loopCntrName = repName+'_key'
        itrIncStr    = ""
        firstOwner   = progSpec.getContainerFirstElementOwner(ctnrTSpec)
        firstType    = progSpec.getFieldTypeKeyWordOld(ctnrTSpec)
        firstTSpec   = {'owner':firstOwner, 'fieldType':firstType}
        reqTagList   = progSpec.getReqTagList(ctnrTSpec)
        itrTSpec     = progSpec.getItrTypeOfDataStruct(ctnrTSpec)
        itrTypeKW    = progSpec.fieldTypeKeyword(itrTSpec)
        itrOwner     = progSpec.getOwnerFromTypeSpec(itrTSpec)
        itrName      = repName + "Itr"
        containerCat = self.getContaineCategory(ctnrTSpec)
        [LDeclP, RDeclP, LDeclA, RDeclA] = self.ChoosePtrDecorationForSimpleCase(ctnrOwner)
        [LNodeP, RNodeP, LNodeA, RNodeA] = self.ChoosePtrDecorationForSimpleCase(itrOwner)
        if containerCat=='PovList':
            firstTSpec = {'owner':'our', 'fieldType':['infon']}
            keyVarSpec = {'owner':'me', 'fieldType':'uint64_t'}
            localVarsAlloc.append([loopCntrName, keyVarSpec])  # Tracking local vars for scope
            localVarsAlloc.append([repName, firstTSpec]) # Tracking local vars for scope
            actionText += (indent + "for( auto " + itrName+' ='+ ctnrName+RDeclP+'begin()' + "; " + itrName + " !=" + ctnrName+RDeclP+'end()' +"; "+ itrName + " = " + itrName+"->next ){\n"
                        + indent+"    "+"shared_ptr<infon> "+repName+" = "+itrName+"->pItem;\n")
            cdErr("iterateContainerStr() found PovList: "+repName+"   "+ctnrName)
            return [actionText, loopCntrName, itrIncStr]
        if containerCat=='Map'     or containerCat=="Multimap":
            if(reqTagList != None):
                firstTSpec['owner']     = progSpec.getOwnerFromTemplateArg(reqTagList[1])
                firstTSpec['fieldType'] = progSpec.getTypeFromTemplateArg(reqTagList[1])
            keyVarSpec  = {'owner':'me', 'fieldType':firstType, 'codeConverter':(repName+'.first')}
            localVarsAlloc.append([loopCntrName, keyVarSpec])  # Tracking local vars for scope
            getNodeVal  = progSpec.getCodeConverterByFieldID(classes, itrTypeKW, 'val', repName,RNodeP)
            firstTSpec['codeConverter'] = (getNodeVal)
            localVarsAlloc.append([repName, firstTSpec]) # Tracking local vars for scope
            localVarsAlloc.append([itrName, itrTSpec]) # Tracking local vars for scope
            frontItr    = progSpec.getCodeConverterByFieldID(classes, datastructID, "front" , ctnrName , RDeclP)
            actionText += (indent + "for( auto " + itrName+' ='+frontItr + "; " + itrName + " !=" + ctnrName+RDeclP+'end()' +"; ++"+itrName  + " ){\n"
                        + indent+"    "+"auto "+repName+" = *"+itrName+";\n")
        elif containerCat=='List' or datastructID=='deque':
            if willBeModifiedDuringTraversal:
                keyVarSpec = {'owner':'me', 'fieldType':'uint64_t'}
                lvName=repName+"Idx"
                idxVarSpec = {'owner':'itr', 'fieldType':firstType}
                localVarsAlloc.append([loopCntrName, keyVarSpec])  # Tracking local vars for scope
                localVarsAlloc.append([repName, firstTSpec]) # Tracking local vars for scope
                localVarsAlloc.append([lvName, idxVarSpec]) # Tracking local vars for scope
                if isBackward: actionText += (indent + "for( int64_t " + lvName+' = '+ctnrName+RDeclP+'size()-1; ' + lvName+" >= 0; "+" --"+lvName+" ){\n")
                else: actionText += (indent + "for( uint64_t " + lvName+' = 0; ' + lvName+" < " +  ctnrName+RDeclP+'size();' +" ++"+lvName+" ){\n")
                actionText += indent+"    "+"auto &"+repName+" = "+LDeclA+ctnrName+RDeclA+"["+lvName+"];\n"
            else:
                keyVarSpec = {'owner':firstOwner, 'fieldType':firstType}
                localVarsAlloc.append([loopCntrName, keyVarSpec])  # Tracking local vars for scope
                localVarsAlloc.append([repName, firstTSpec]) # Tracking local vars for scope
                if isBackward: actionText += (indent + "for( auto " + itrName+' ='+ ctnrName+RDeclP+'rbegin()' + "; " + itrName + " !=" + ctnrName+RDeclP+'rend()' +"; ++"+ itrName + " ){\n")
                else: actionText += (indent + "for( auto " + itrName+' ='+ ctnrName+RDeclP+'begin()' + "; " + itrName + " !=" + ctnrName+RDeclP+'end()' +"; ++"+ itrName + " ){\n")
                actionText += indent+"    "+"auto "+repName+" = *"+itrName+";\n"
        elif containerCat=='string':
            loopCntrName = ''
            actionText += indent + "for(char const &" + repName +": " + ctnrName + " ){\n"
        else: cdErr("iterateContainerStr() datastructID = " + datastructID)
        return [actionText, loopCntrName, itrIncStr]

    def codeSwitchExpr(self, switchKeyExpr, switchKeyTypeSpec):
        if switchKeyTypeSpec['fieldType'] == 'string':
            switchKeyExpr = '_strHash(' + switchKeyExpr + '.data())'
        return switchKeyExpr

    def codeSwitchCase(self, caseKeyValue, caseKeyTypeSpec):
        if caseKeyTypeSpec == 'string':
            caseKeyValue = '_strHash(' + caseKeyValue + ')'
        return caseKeyValue

    ###################################################### EXPRESSION CODING
    def codeNotOperator(self, S, S2,retTypeSpec):
        S+='!' + S2
        return [S, retTypeSpec]

    def codeFactor(self, item, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        ####  ( value | ('(' + expr + ')') | ('!' + expr) | ('-' + expr) | varRef("varFunRef"))
        #print('                  factor: ', item)
        S=''
        retTypeSpec='noType'
        item0 = item[0]
        #print("ITEM0=", item0, ">>>>>", item)
        if (isinstance(item0, str)):
            if item0=='(':
                [S2, retTypeSpec] = self.codeGen.codeExpr(item[1], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                S+='(' + S2 +')'
            elif item0=='!':
                [S2, retTypeSpec] = self.codeGen.codeExpr(item[1], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                [S, retTypeSpec]  = self.codeNotOperator(S, S2,retTypeSpec)
            elif item0=='-':
                [S2, retTypeSpec] = self.codeGen.codeExpr(item[1], returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                S+='-' + S2
            elif item0=='[':
                tmp="{"
                for expr in item[1:-1]:
                    [S2, retTypeSpec] = self.codeGen.codeExpr(expr, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                    if len(tmp)>1: tmp+=", "
                    tmp+=S2
                tmp+="}"
                S+=tmp
            elif item0=='{':
                tmp="{"
                idx=1
                while idx <  len(item)-1:
                    valExpr = item[idx+2]
                    [S2, retTypeSpec] = self.codeGen.codeExpr(valExpr, returnType, expectedTypeSpec, LorRorP_Val, genericArgs)
                    if len(tmp)>1: tmp+=", "
                    tmp+="{" + item[idx] + ", " + S2 + "}"
                    idx += 3
                tmp+="}"
                S+=tmp
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
                    S+=self.codeGen.codeUserMesg(item0[1:-1])
                elif (item0[0]=='"'):
                    retTypeSpec='string'
                    if returnType != None and returnType["fieldType"]=="char":
                        retTypeSpec='char'
                        innerS=item0[1:-1]
                        if len(innerS)==1:
                            S+="'"+item0[1:-1] +"'"
                        else:
                            cdErr("Characters must have exactly 1 character.")
                    else:
                        S+='"'+item0[1:-1] +'"'
                        retTypeSpec='string'
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
                [codeStr, retTypeSpec, prntType, AltIDXFormat]=self.codeGen.codeItemRef(item0, 'RVAL', returnType, LorRorP_Val, genericArgs)
                if(codeStr=="NULL"):
                    codeStr="nullptr"
                    retTypeSpec={'owner':"PTR"}
                S+=codeStr                                # Code variable reference or function call
        if retTypeSpec == 'noType': print("Warning: type Spec not found.", S)
        return [S, retTypeSpec]

    ######################################################
    def adjustQuotesForChar(self, typeSpec1, typeSpec2, S):
        fieldType1 = progSpec.fieldTypeKeyword(typeSpec1)
        fieldType2 = progSpec.fieldTypeKeyword(typeSpec2)
        if fieldType1 == "char" and (fieldType2 == 'string' or fieldType2 == 'String') and S[0] == '"':
            return("'" + S[1:-1] + "'")
        return(S)

    def adjustConditional(self, S2, conditionType):
        return [S2, conditionType]

    def codeSpecialReference(self, segSpec, genericArgs):
        S=''
        fieldType='void'   # default to void
        retOwner='me'    # default to 'me'
        funcName=segSpec[0]
        if(len(segSpec)>2):  # If there are arguments...
            paramList=segSpec[2]
            if(funcName=='print'):
                # TODO: have a tag to choose cout vs printf()
                S+='cout'
                for P in paramList:
                    [S2, argTypeSpec]=self.codeGen.codeExpr(P[0], None, None, 'PARAM', genericArgs)
                    [S2, isDerefd]=self.derefPtr(S2, argTypeSpec)
                    S+=' << '+S2
                S+=" << flush"
            elif(funcName=='input'):
                P=paramList[0]
                [S2, argTypeSpec]=self.codeGen.codeExpr(P[0], None, None, 'PARAM', genericArgs)
                [S2, isDerefd]=self.derefPtr(S2, argTypeSpec)
                S+='getline(cin, '+S2+')'
            elif(funcName=='AllocateOrClear'):
                [varName,  varTypeSpec]=self.codeGen.codeExpr(paramList[0][0], None, None, 'PARAM', genericArgs)
                if(varTypeSpec==0): cdErr("Name is undefined: " + varName)
                S+='if('+varName+'){'+varName+'->clear();} else {'+varName+" = "+self.codeXlatorAllocater(varTypeSpec, genericArgs)+"();}"
            elif(funcName=='Allocate'):
                [varName,  varTypeSpec]=self.codeGen.codeExpr(paramList[0][0], None, None, 'LVAL', genericArgs)
                if(varTypeSpec==0): cdErr("Name is Undefined: " + varName)
                S+=varName+" = "+self.codeXlatorAllocater(varTypeSpec, genericArgs)+'('
                count=0   # TODO: As needed, make this call CodeParameterList() with modelParams of the constructor.
                for P in paramList[1:]:
                    if(count>0): S+=', '
                    [S2, argTypeSpec]=self.codeGen.codeExpr(P[0], None, None, 'PARAM', genericArgs)
                    S+=S2
                    count=count+1
                S+=")"
            elif(funcName=='callPeriodically'):
                [objName,  typeSpec]=self.codeGen.codeExpr(paramList[1][0], None, None, 'PARAM', genericArgs)
                [interval,  intTypeSpec]   =self.codeGen.codeExpr(paramList[2][0], None, None, 'PARAM', genericArgs)
                fieldType = progSpec.fieldTypeKeyword(typeSpec)
                varTypeSpec= fieldType
                wrapperName="cb_wraps_"+varTypeSpec
                S+='g_timeout_add('+interval+', '+wrapperName+', '+objName+')'

                # Create a global function wrapping the class
                decl='\nint '+wrapperName+'(void* data)'
                defn='{'+varTypeSpec+'* self = ('+varTypeSpec+'*)data; self->run(); return true;}\n\n'
                self.codeGen.appendGlobalFuncAcc(decl, defn)
            elif(funcName=='break'):
                if len(paramList)==0: S='break'
            elif(funcName=='return'):
                if len(paramList)==0: S+='return'
            elif(funcName=='toStr'):
                if len(paramList)==1:
                    [S2, argTypeSpec]=self.codeGen.codeExpr(P[0][0], None, None, 'PARAM', genericArgs)
                    [S2, isDerefd]=self.derefPtr(S2, argTypeSpec)
                    S+='to_string('+S2+')'
                    fieldType='string'
            elif(funcName=='asClass'):
                if len(paramList)==2:
                    [newTypeStr, argTypeSpec]=self.codeGen.codeExpr(paramList[0][0], None, None, 'PARAM', genericArgs)
                    [newTypeStr, isDerefd]=self.derefPtr(newTypeStr, argTypeSpec)
                    [toCvtStr, toCvtTypeSpec]=self.codeGen.codeExpr(paramList[1][0], None, None, 'PARAM', genericArgs)
                   # [toCvtStr, isDerefd]=self.derefPtr(toCvtStr, toCvtTypeSpec)
                    varOwner=progSpec.getTypeSpecOwner(toCvtTypeSpec)
                    if(varOwner=='their'): S="static_cast<"+newTypeStr+"*>("+toCvtStr+")"
                    elif(varOwner=='our'): S="static_pointer_cast<"+newTypeStr+">("+toCvtStr+")"
                    elif(varOwner=='my'):  S="static_pointer_cast<"+newTypeStr+">("+toCvtStr+")"
                    elif(varOwner=='me'):  S="static_cast<"+newTypeStr+">("+toCvtStr+")"
                    else: cdErr("Casting that to "+str(newTypeStr)+" is not yet supported.")
                    fieldType = newTypeStr
                    retOwner= varOwner

        else: # Not parameters, i.e., not a function
            if(funcName=='self'):
                S+='this'

        return [S, retOwner, fieldType]

    def checkIfSpecialAssignmentFormIsNeeded(self, action, indent, AltIDXFormat, RHS, rhsType, LHS, LHSParentType, LHS_FieldType):
        # Check for string A[x] = B;  If so, render A.insert(B,x)
        S = ''
        assignTag = action['assignTag']
        [containerType, idxType, owner]=self.getContainerType(AltIDXFormat[1], "")
        if assignTag == '':
            [containerType, idxType, owner]=self.getContainerType(AltIDXFormat[1], "")
            if containerType == 'RBTreeMap':
                S = indent+AltIDXFormat[0]+'.insert('+AltIDXFormat[2]+', '+RHS+');\n'
        #else: assignTag = assignTag[0]
        return S

    ############################################
    def codeProtectBlock(self, mutex, criticalText, indent):
        S = indent+'{\n'
        S += indent+'    Unique_Lock_Mutex mtxMgr('+mutex+');\n'
        S += criticalText
        S += indent+'}\n'
        return(S)

    def codeMain(self, classes, tags):
        cdlog(3, "\n            Generating GLOBAL...")
        if("GLOBAL" in classes[1]):
            if(classes[0]["GLOBAL"]['stateType'] != 'struct'):
                print("ERROR: GLOBAL must be a 'struct'.")
                exit(2)
            [structCode, funcCode, globalFuncs]=self.codeGen.codeStructFields("GLOBAL", tags, '')
            if(funcCode==''): funcCode="// No main() function.\n"
            if(structCode==''): structCode="// No Main Globals.\n"
            funcCode = "\n\n"+funcCode
            return ["\n\n// Globals\n" + structCode + "\n// Global Functions\n" + globalFuncs, funcCode]
        return ["// No Main Globals.\n", "// No main() function defined.\n"]

    def codeArgText(self, argFieldName, argType, argOwner, typeSpec, makeConst, typeArgList):
        argTypeStr = argType
        if makeConst:
            if argOwner == "me": argMod = "&"
            else: argMod = ""
            argTypeStr = "const "+argTypeStr+argMod
        return argTypeStr + " " +argFieldName

    def codeStructText(self, classes, attrList, parentClass, classInherits, classImplements, structName, structCode, tags):
        if parentClass != "":
            parentClass = parentClass.replace('::', '_')
            parentClass = progSpec.getUnwrappedClassFieldTypeKeyWord(classes, structName)
            parentClass=': public '+parentClass+' '
            print("Warning: old style inheritance used: " , parentClass)
        if classInherits!=None:
            parentClass=': public '
            count =0
            for item in classInherits[0]:
                if count>0:
                    parentClass+= ', '
                parentClass+= progSpec.getUnwrappedClassFieldTypeKeyWord(classes, item)
                count += 1
        S= "\nstruct "+structName+parentClass+"{\n" + structCode + '};\n'
        typeArgList = progSpec.getTypeArgList(structName)
        templateHeader = ""
        if(typeArgList != None):
            forwardDecls = ""
            templateHeader = self.codeTemplateHeader(structName, typeArgList)+" "
            S=templateHeader+S
        forwardDecls=templateHeader+"struct " + structName + ";  \t// Forward declaration\n"
        return([S,forwardDecls])

    def produceTypeDefs(self, typeDefMap):
        typeDefCode="\n// Typedefs:\n"
        for key in typeDefMap:
            val=typeDefMap[key]
            #sprint '['+key+']='+val+']'
            if(val != '' and val != key):
                typeDefCode += 'typedef '+key+' '+val+';\n'
        return typeDefCode

    def addSpecialCode(self, filename):
        S='\n\n//////////// C++ specific code:\n'
        S += "\n\nusing namespace std;\n\n"
        S += "typedef unsigned int uint;\n\n"
        S += 'const string filename = "' + filename + '";\n'
        S += r'static void reportFault(int Signal){cout<<"\nSegmentation Fault.\n"; fflush(stdout); abort();}'+'\n\n'

        S += "string enumText(string* array, int enumVal, int enumOffset){return array[enumVal >> enumOffset];}\n";
        S += "#define SetBitsMACRO(item, mask, val) {(item) &= ~((uint64_t)mask); (item)|=((uint64_t)val);}\n"
        S += "#define SetFlagBit(item, mask, val) SetBits(item, mask, ((val)?mask:0))\n"
        S += "#define SetModeBits(item, mask, val) SetBits(item, mask##Mask, ((uint64_t)val << mask##Offset))\n"
        S += "#define getFlagBit(item, mask) (bool)(item & (uint64_t)mask)\n"
        S += "#define getModeBits(item, mask) (uint64_t)((item & (uint64_t)mask##Mask)>>(uint64_t)mask##Offset)\n"

        S += '''
template<class T> class CopyableAtomic : public std::atomic<T>{
public:
    //defaultinitializes value
    CopyableAtomic() = default;

    constexpr CopyableAtomic(T desired) :
        std::atomic<T>(desired)
    {}

    constexpr CopyableAtomic(const CopyableAtomic<T>& other) :
        CopyableAtomic(other.load(std::memory_order_relaxed))
    {}

    CopyableAtomic& operator=(const CopyableAtomic<T>& other) {
        this->store(other.load(std::memory_order_relaxed), std::memory_order_relaxed);
        return *this;
    }
};

void SetBits(CopyableAtomic<uint64_t>& target, uint64_t mask, uint64_t value) {
    uint64_t original_value = target.load();
    uint64_t new_value = original_value;
    SetBitsMACRO(new_value, mask, value);
    while(!target.compare_exchange_weak(original_value, new_value)){
        new_value = original_value;
        SetBitsMACRO(new_value, mask, value);
    }
}

'''
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
        self.codeGen.appendGlobalFuncAcc(decl, defn)

        return S

    def addGLOBALSpecialCode(self, classes, tags):
        specialCode =''

        GLOBAL_CODE="""
    struct GLOBAL{
        %s
    }
        """ % (specialCode)

        #codeDogParser.AddToObjectFromText(classes[0], classes[1], GLOBAL_CODE )

    def codeNewVarStr(self, classes, tags, lhsTypeSpec, varName, fieldDef, indent, actionOrField, genericArgs, localVarsAllocated):
        varDeclareStr = ''
        assignValue   = ''
        isAllocated   = fieldDef['isAllocated']
        owner         = progSpec.getTypeSpecOwner(lhsTypeSpec)
        useCtor       = False
        paramList     = None
        if fieldDef['paramList']: paramList = fieldDef['paramList']
        if paramList and fieldDef['paramList'][-1] == "^&useCtor//8":
            del fieldDef['paramList'][-1]
            useCtor = True
        [cvrtType, innerType] = self.codeGen.convertType(lhsTypeSpec, 'var', actionOrField, genericArgs)
        localVarsAllocated.append([varName, lhsTypeSpec])  # Tracking local vars for scope
        if(fieldDef['value']):
            [RHS, rhsTypeSpec]=self.codeGen.codeExpr(fieldDef['value'][0], lhsTypeSpec, None, 'RVAL', genericArgs)
            [LHS_leftMod, LHS_rightMod,  RHS_leftMod, RHS_rightMod] = self.determinePtrConfigForAssignments(lhsTypeSpec, rhsTypeSpec, "" , RHS)
            if(isAllocated and not progSpec.typeIsPointer(rhsTypeSpec)):
                RHS = self.codeGen.codeAllocater(lhsTypeSpec, RHS, genericArgs)
            else: RHS = RHS_leftMod+RHS+RHS_rightMod
            if(isAllocated or useCtor==False): assignValue = " = " + RHS
            else: assignValue = RHS
        else: # If no value was given:
            CPL=''
            if paramList!= None:       # call constructor  # curly bracket param list
                # Code the constructor's arguments
                ### TODO: CHoose the best constructor and get modelParams to pass in instead of None.
                modelParams  = self.codeGen.chooseCtorModelParams(lhsTypeSpec, paramList, genericArgs)
                [CPL, paramTypeList] = self.codeGen.codeParameterList(varName, paramList, modelParams, genericArgs)
                if len(paramTypeList)==1:
                    if not isinstance(paramTypeList[0], dict):
                        print("\nPROBLEM: The return type of the parameter '", CPL, "' of "+varName+"(...) cannot be found and is needed. Try to define it.\n",   paramTypeList)
                        exit(1)
                    rhsTypeSpec = paramTypeList[0]
                    rhsType     = progSpec.fieldTypeKeyword(rhsTypeSpec)
                    # TODO: Remove the 'True' and make this check object heirarchies or similar solution
                    if True or not isinstance(rhsType, str) and cvrtType==rhsType[0]:
                        [leftMod, rightMod] = self.determinePtrConfigForNewVars(lhsTypeSpec, rhsTypeSpec, useCtor)
                        if(not useCtor): assignValue += " = "    # Use a copy constructor
                        if(isAllocated):
                            assignValue += self.codeXlatorAllocater(lhsTypeSpec, genericArgs)
                        assignValue += "(" + leftMod + CPL[1:-1] + rightMod + ")"
                if(assignValue==''):
                    if(owner == 'their' or owner == 'our' or owner == 'my'): assignValue = ' = '+self.codeXlatorAllocater(lhsTypeSpec, genericArgs)+CPL
                    else: assignValue = CPL # add "(x, y, z...) to make this into a constructor call.
            elif(progSpec.typeIsPointer(lhsTypeSpec)):
                if(isAllocated):
                    assignValue = " = " + self.codeGen.codeAllocater(lhsTypeSpec, paramList, genericArgs)
                else:
                    assignValue = '= NULL'
            elif(progSpec.isAContainer(lhsTypeSpec)):
                pass
            else:
                fieldTypeCat= progSpec.fieldsTypeCategory(lhsTypeSpec)
                if(fieldTypeCat=='int' or fieldTypeCat=='char' or fieldTypeCat=='double' or fieldTypeCat=='float'):
                    assignValue = ' = 0'
                elif(fieldTypeCat=='bool'):
                    assignValue = '= false'

        varDeclareStr= cvrtType + " " + varName + assignValue
        return(varDeclareStr)

    def codeIncrement(self, varName):
        return "++" + varName

    def codeDecrement(self, varName):
        return "--" + varName

    def codeVarFieldRHS_Str(self, fieldName, cvrtType, innerType, typeSpec, paramList, isAllocated, typeArgList, genericArgs):
        fieldValueText=""
        fieldOwner=progSpec.getTypeSpecOwner(typeSpec)
        #TODO: make test case
        if paramList!=None:
            if paramList[-1] == "^&useCtor//8":
                del paramList[-1]
            [CPL, paramTypeList] = self.codeGen.codeParameterList(fieldName, paramList, None, genericArgs)
            fieldValueText += CPL
        if isAllocated == True:
            fieldValueText = " = " + self.codeGen.codeAllocater(typeSpec, paramList, genericArgs)
        return fieldValueText

    def codeConstField_Str(self, convertedType, fieldName, fieldValueText, className, indent):
        if className=='GLOBAL':
            defn = indent + convertedType + ' ' + fieldName + fieldValueText +';\n';
            decl = ''
        else:
            defn = indent + convertedType + ' ' + fieldName +';\n'
            decl = convertedType[7:] + ' ' + progSpec.flattenObjectName(className) + "::"+ fieldName + fieldValueText +';\n\n'
        return [defn, decl]

    def codeVarField_Str(self, convertedType, typeSpec, fieldName, fieldValueText, className, tags, typeArgList, indent):
        #TODO: make test case
        fieldOwner=progSpec.getTypeSpecOwner(typeSpec)
        if fieldOwner=='we':
            defn = indent + convertedType + ' ' + fieldName +';\n'
            decl = convertedType[7:] + ' ' + progSpec.flattenObjectName(className) + "::"+ fieldName + fieldValueText +';\n\n'
        else:
            defn = indent + convertedType + ' ' + fieldName + fieldValueText +';\n'
            decl = ''
        return [defn, decl]

    def codeConstructor(self, className, ctorArgs, callSuper, ctorInit, funcBody):
        if callSuper != '':
            callSuper = ':' + callSuper
            if ctorInit != '':
                callSuper = callSuper + ', '
        elif ctorInit != '':
            ctorInit = ':' + ctorInit
        S = "    " + className + "(" + ctorArgs + ")" + callSuper + ctorInit +"{\n" + funcBody + "    };\n"
        return (S)

    def codeConstructors(self, className, ctorArgs, ctorOvrRide, ctorInit, copyCtorArgs, funcBody, callSuper):
        S = ''
        if ctorArgs != '' or funcBody!='':
            S += self.codeConstructor(className, ctorArgs, callSuper, ctorInit, funcBody)
      #  S += self.codeConstructor(className, '', callSuper, '', funcBody)
        return S

    def codeConstructorInit(self, fieldName, count, defaultVal):
        if (count > 0):
            return "," + fieldName+"("+" _"+fieldName+")"
        elif(count == 0):
            return fieldName+"("+" _"+fieldName+")"
        else:
            cdErr("Error in codeConstructorInit.")

    def codeConstructorArgText(self, argFieldName, count, argType, defaultVal):
        if defaultVal == "NULL":
            defaultVal = "0"
        if defaultVal != '':
            defaultVal = "=" + defaultVal
        return argType + "  _" +argFieldName + defaultVal

    def codeCopyConstructor(self, fieldName, convertedType, isTemplateVar):
        return ""

    def codeConstructorCall(self, className):
        return '        INIT();\n'

    def codeSuperConstructorCall(self, parentClassName):
        return parentClassName+'()'

    def specialFunction(self, fieldName):
        if fieldName == "__plus": newFieldName = "operator+"
        elif fieldName == "__minus": newFieldName = "operator-"
        elif fieldName == "__times": newFieldName = "operator*"
        elif fieldName == "__divide": newFieldName = "operator/"
        elif fieldName == "__negate": newFieldName = "operator-"
        elif fieldName == "__plusEqual": newFieldName = "operator+="
        elif fieldName == "__lessThan": newFieldName = "operator<"
        elif fieldName == "__lessOrEq": newFieldName = "operator<="
        elif fieldName == "__greaterThan": newFieldName = "operator>"
        elif fieldName == "__greaterOrEq": newFieldName = "operator>="
        elif fieldName == "__isEqual": newFieldName = "operator=="
        elif fieldName == "__notEqual": newFieldName = "operator!="
        elif fieldName == "__inc": newFieldName = "operator++"
        elif fieldName == "__opAssign": newFieldName = "operator="
        elif fieldName == "__derefPtr": newFieldName = "operator*"
        elif fieldName == "__index": newFieldName = "operator[]"
        else:  newFieldName = fieldName
        return newFieldName

    def codeFuncHeaderStr(self, className, fieldName, typeDefName, argListText, localArgsAllocated, inheritMode, overRideOper, isConstructor, typeArgList, typeSpec, indent):
        structCode=''; funcDefCode=''; globalFuncs='';
        if(className=='GLOBAL'):
            if fieldName=='main':
                funcDefCode += 'int main(int argc, char *argv[])'
                localArgsAllocated.append(['argc', {'owner':'me', 'fieldType':'int', 'arraySpec':None, 'argList':None}])
                localArgsAllocated.append(['argv', {'owner':'their', 'fieldType':'char', 'arraySpec':None,'argList':None}])  # TODO: Wrong. argv should be an array.
            else:
                globalFuncs += typeDefName +' ' + fieldName +"("+argListText+")"
        else:
            typeArgList = progSpec.getTypeArgList(className)
            if(typeArgList != None):
                templateHeader = self.codeTemplateHeader(className, typeArgList) +"\n"
                className = className + self.codeTypeArgs(typeArgList)
            else:
                templateHeader = ""
            if overRideOper:
                if fieldName == "operator[]":
                    typeDefName += "&"
            if inheritMode=='normal' or inheritMode=='override':
                structCode += indent + typeDefName +' ' + fieldName +"("+argListText+");\n";
                objPrefix = progSpec.flattenObjectName(className) +'::'
                funcDefCode += templateHeader + typeDefName +' ' + objPrefix + fieldName +"("+argListText+")"
            elif inheritMode=='virtual':
                structCode += indent + 'virtual '+typeDefName +' ' + fieldName +"("+argListText +");\n";
                objPrefix = progSpec.flattenObjectName(className) +'::'
                funcDefCode += templateHeader + typeDefName +' ' + objPrefix + fieldName +"("+argListText+")"
            elif inheritMode=='pure-virtual':
                structCode +=  indent + 'virtual ' + typeDefName +' ' + fieldName +"("+argListText +") = 0;\n";
            else: cdErr("Invalid inherit mode found: "+inheritMode)
            if funcDefCode[:7]=="static ": funcDefCode=funcDefCode[7:]
        return [structCode, funcDefCode, globalFuncs]

    def getVirtualFuncText(self, field):
        return ""

    def codeTypeArgs(self, typeArgList):
        typeArgsCode = "<"
        count = 0
        for typeArg in typeArgList:
            if(count>0):typeArgsCode+=", "
            typeArgsCode+=typeArg
            count+=1
        typeArgsCode+=">"
        return(typeArgsCode)

    def codeTemplateHeader(self, structName, typeArgList):
        templateHeader = "\ntemplate<"
        count = 0
        for typeArg in typeArgList:
            if(count>0):templateHeader+=","
            templateHeader+="typename "+typeArg
            count+=1
        templateHeader+=">"
        return(templateHeader)

    def extraCodeForTopOfFuntion(self, argList):
        return ''

    def codeSetBits(self, LHS_Left, LHS_FieldType, prefix, bitMask, RHS, rhsType):
        if (LHS_FieldType =='flag' ):
            return "SetFlagBit("+LHS_Left+"flags, "+prefix+bitMask+", "+ RHS + ");\n"
        elif (LHS_FieldType =='mode' ):
            return "SetModeBits("+LHS_Left+"flags, "+prefix+bitMask+", "+ RHS +");\n"

    def codeSwitchBreak(self, caseAction, indent):
        return indent+"    break;\n"

    def applyTypecast(self, typeInCodeDog, itemToAlterType):
        platformType = self.adjustBaseTypes(typeInCodeDog)
        return '('+platformType+')'+itemToAlterType;

    #######################################################

    def includeDirective(self, libHdr):
        if libHdr[0] == '"' or libHdr[0] == "'":
            S = '#include "'+libHdr[1:-1]+'"\n'
        else:
            S = '#include <'+libHdr+'>\n'
        return S

    def generateMainFunctionality(self, classes, tags):
        # TODO: Some deInitialize items should automatically run during abort().
        # TODO: System initCode should happen first in initialize, last in deinitialize.

        runCode = progSpec.fetchTagValue(tags, 'runCode')
        if runCode==None: runCode=""
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

    def __init__(self):
        print("INIT")
