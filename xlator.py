# xlator.py

from progSpec import cdErr

class Xlator(object):
    def adjustBaseTypes(self, fType, isContainer):
        cdErr("In base class Xlator::adjustBaseTypes.")

    def applyOwner(self, owner, langType):
        cdErr("In base class Xlator::applyOwner.")

    def getUnwrappedClassOwner(self, classes, tSpec, fType, varMode, ownerIn):
        cdErr("In base class Xlator::getUnwrappedClassOwner.")

    def getReqTagString(self, classes, tSpec):
        cdErr("In base class Xlator::getReqTagString.")

    def makePtrOpt(self, tSpec):
        cdErr("In base class Xlator::makePtrOpt.")

    def recodeStringFunctions(self, name, tSpec, lenParams):
        cdErr("In base class Xlator::recodeStringFunctions.")

    def langStringFormatterCommand(self, fmtStr, argStr):
        cdErr("In base class Xlator::langStringFormatterCommand.")

    def LanguageSpecificDecorations(self, S, tSpec, owner, LorRorP_Val):
        cdErr("In base class Xlator::LanguageSpecificDecorations.")

    def convertToInt(self, S, tSpec):
        cdErr("In base class Xlator::convertToInt.")

    def checkForTypeCastNeed(self, lhsTSpec, rhsTSpec, RHS):
        cdErr("In base class Xlator::checkForTypeCastNeed.")

    def getTheDerefPtrMods(self, itemTypeSpec):
        cdErr("In base class Xlator::getTheDerefPtrMods.")

    def derefPtr(self, varRef, itemTypeSpec):
        cdErr("In base class Xlator::derefPtr.")

    def ChoosePtrDecorationForSimpleCase(self, owner):
        cdErr("In base class Xlator::ChoosePtrDecorationForSimpleCase.")

    def chooseVirtualRValOwner(self, LVAL, RVAL):
        cdErr("In base class Xlator::chooseVirtualRValOwner.")

    def determinePtrConfigForNewVars(self, LSpec, RSpec, useCtor):
        cdErr("In base class Xlator::determinePtrConfigForNewVars.")

    def determinePtrConfigForAssignments(self, LVAL, RVAL, assignTag, codeStr):
        cdErr("In base class Xlator::determinePtrConfigForAssignments.")

    def codeSpecialParamList(self, tSpec, CPL):
        cdErr("In base class Xlator::codeSpecialParamList.")

    def codeXlatorAllocater(self, tSpec, genericArgs):
        cdErr("In base class Xlator::codeXlatorAllocater.")

    def getConstIntFieldStr(self, fieldName, fieldValue, intSize):
        cdErr("In base class Xlator::getConstIntFieldStr.")

    def getEnumStr(self, fieldName, enumList):
        cdErr("In base class Xlator::getEnumStr.")

    def codeIdentityCheck(self, S, S2, retType1, retType2, opIn):
        cdErr("In base class Xlator::codeIdentityCheck.")

    def codeComparisonStr(self, S, S2, retType1, retType2, op):
        cdErr("In base class Xlator::codeComparisonStr.")

    def getContaineCategory(self, containerSpec):
        cdErr("In base class Xlator::getContaineCategory.")

    def codeArrayIndex(self, idx, containerType, LorR_Val, previousSegName, idxTypeSpec):
        cdErr("In base class Xlator::codeArrayIndex.")

    def codeRangeSpec(self, traversalMode, ctrType, repName, S_low, S_hi, indent):
        cdErr("In base class Xlator::codeRangeSpec.")

    def iterateRangeFromTo(self, classes,localVarsAlloc,StartKey,EndKey,ctnrTSpec,repName,ctnrName,indent):
        cdErr("In base class Xlator::iterateRangeFromTo.")

    def iterateContainerStr(self, classes,localVarsAlloc,ctnrTSpec,repName,ctnrName,isBackward,indent,genericArgs):
        cdErr("In base class Xlator::iterateContainerStr.")

    def codeSwitchExpr(self, switchKeyExpr, switchKeyTypeSpec):
        cdErr("In base class Xlator::codeSwitchExpr.")

    def codeSwitchCase(self, caseKeyValue, caseKeyTypeSpec):
        cdErr("In base class Xlator::codeSwitchCase.")

    def codeNotOperator(self, S, S2,retTypeSpec):
        cdErr("In base class Xlator::codeNotOperator.")

    def codeFactor(self, item, returnType, expectedTypeSpec, LorRorP_Val, genericArgs):
        cdErr("In base class Xlator::codeFactor.")

    def adjustQuotesForChar(self, typeSpec1, typeSpec2, S):
        cdErr("In base class Xlator::adjustQuotesForChar.")

    def adjustConditional(self, S, conditionType):
        cdErr("In base class Xlator::adjustConditional.")

    def codeSpecialReference(sself, egSpec, genericArgs):
        cdErr("In base class Xlator::codeSpecialReference.")

    def checkIfSpecialAssignmentFormIsNeeded(self, action, indent, AltIDXFormat, RHS, rhsType, LHS, LHSParentType, LHS_FieldType):
        cdErr("In base class Xlator::checkIfSpecialAssignmentFormIsNeeded.")

    def codeMain(self, classes, tags):
        cdErr("In base class Xlator::codeMain.")

    def codeArgText(self, argFieldName, argType, argOwner, tSpec, makeConst, typeArgList):
        cdErr("In base class Xlator::codeArgText.")

    def codeStructText(self, classes, attrList, parentClass, classInherits, classImplements, className, structCode, tags):
        cdErr("In base class Xlator::codeStructText.")

    def produceTypeDefs(self, typeDefMap):
        cdErr("In base class Xlator::produceTypeDefs.")

    def addSpecialCode(self, filename):
        cdErr("In base class Xlator::addSpecialCode.")

    def addGLOBALSpecialCode(self, classes, tags):
        cdErr("In base class Xlator::addGLOBALSpecialCode.")

    def variableDefaultValueString(self, fType, isTypeArg, owner):
        cdErr("In base class Xlator::variableDefaultValueString.")

    def codeNewVarStr(self, LTSpec, varName, fieldDef, indent, genericArgs, localVarsAlloc):
        cdErr("In base class Xlator::codeNewVarStr.")

    def codeIncrement(self, varName):
        cdErr("In base class Xlator::codeIncrement.")

    def codeDecrement(self, varName):
        cdErr("In base class Xlator::codeDecrement.")

    def isNumericType(self, convertedType):
        cdErr("In base class Xlator::isNumericType.")

    def codeVarFieldRHS_Str(self, fieldName, cvrtType, tSpec, paramList, isAllocated, typeArgList, genericArgs):
        cdErr("In base class Xlator::codeVarFieldRHS_Str.")

    def codeConstField_Str(self, convertedType, fieldName, fieldValueText, className, indent):
        cdErr("In base class Xlator::codeConstField_Str.")

    def codeVarField_Str(self, convertedType, tSpec, fieldName, fieldValueText, className, tags, typeArgList, indent):
        cdErr("In base class Xlator::codeVarField_Str.")

    def codeConstructor(self, className, ctorArgs, callSuper, ctorInit, funcBody):
        cdErr("In base class Xlator::codeConstructor.")

    def codeConstructors(self, className, ctorArgs, ctorOvrRide, ctorInit, copyCtorArgs, funcBody, callSuper):
        cdErr("In base class Xlator::codeConstructors.")

    def codeConstructorInit(self, fieldName, count, defaultVal):
        cdErr("In base class Xlator::codeConstructorInit.")

    def codeConstructorArgText(self, argFieldName, count, argType, defaultVal):
        cdErr("In base class Xlator::codeConstructorArgText.")

    def codeCopyConstructor(self, fieldName, isTemplateVar):
        cdErr("In base class Xlator::codeCopyConstructor.")

    def codeConstructorCall(self, className):
        cdErr("In base class Xlator::codeConstructorCall.")

    def codeSuperConstructorCall(self, parentClassName):
        cdErr("In base class Xlator::codeSuperConstructorCall.")

    def codeFuncHeaderStr(self, className, fieldName, returnType, argListText, localArgsAllocated, inheritMode, overRideOper, isConstructor, typeArgList, tSpec, indent):
        cdErr("In base class Xlator::codeFuncHeaderStr.")

    def getVirtualFuncText(self, field):
        cdErr("In base class Xlator::getVirtualFuncText.")

    def codeTemplateHeader(self, className, typeArgList):
        cdErr("In base class Xlator::codeTemplateHeader.")

    def extraCodeForTopOfFuntion(self, argList):
        cdErr("In base class Xlator::extraCodeForTopOfFuntion.")

    def codeSetBits(self, LHS_Left, LHS_FieldType, prefix, bitMask, RHS, rhsType):
        cdErr("In base class Xlator::codeSetBits.")

    def codeSwitchBreak(self, caseAction, indent):
        cdErr("In base class Xlator::codeSwitchBreak.")

    def applyTypecast(self, typeInCodeDog, itemToAlterType):
        cdErr("In base class Xlator::applyTypecast.")

    def includeDirective(self, libHdr):
        cdErr("In base class Xlator::includeDirective.")

    def generateMainFunctionality(self, classes, tags):
        cdErr("In base class Xlator::generateMainFunctionality.")

    def __init__(self):
        cdErr("In base class Xlator::__init__.")
