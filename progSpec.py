
# ProgSpec manipulation routines

import re

storeOfBaseTypesUsed={} # Registry of all types used
codeHeader={} # e.g., codeHeader['cpp']="C++ header code"

def setCodeHeader(languageID, codeText):
    global codeHeader
    if not languageID in codeHeader: codeHeader[languageID]='';
    codeHeader[languageID]+='\n'+codeText

def getTypesBase(typeSpec):
    if isinstance(typeSpec, basestring):
       return typeSpec
    else: return getTypesBase(typeSpec[1])

def registerBaseType(usedType, objectName):
    baseType=getTypesBase(usedType)
    if not (baseType in storeOfBaseTypesUsed):
        storeOfBaseTypesUsed[baseType]={}
    if not (objectName in storeOfBaseTypesUsed[baseType]):
        storeOfBaseTypesUsed[baseType][objectName]=0
    else: storeOfBaseTypesUsed[baseType][objectName] += 1

def addPattern(objSpecs, objectNameList, name, patternList):
    patternName='!'+name
    objectNameList.append(patternName)
    objSpecs[name]={'name':patternName, 'parameters':patternList}
    print "ADDED PATTERN", name

def addObject(objSpecs, objectNameList, name):
    if(name in objSpecs):
        print "Note: The struct '", name, "' is being added but already exists."
        return
    objSpecs[name]={'name':name, "attrList":[], "attr":{}, "fields":[]}
    objectNameList.append(name)
    print "ADDED STRUCT: ", name

def addObjTags(objSpecs, objectName, objTags):
    objSpecs[objectName]["tags"]=objTags
    print "    ADDED Tags to object.\t"



def addField(objSpecs, objectName, kindOfField, fieldType, fieldName):
    if(fieldName in objSpecs[objectName]["fields"]):
        print "Note: The field '", objectName, '::', fieldName, "' already exists. Not re-adding"
        return
    if (kindOfField=="var" or kindOfField=="rPtr" or kindOfField=="sPtr" or kindOfField=="uPtr"):
        objSpecs[objectName]["fields"].append({'kindOfField':kindOfField, 'fieldType':fieldType, 'fieldName':fieldName})
        registerBaseType(fieldType, objectName)
    else:
        print "When adding a Field to ", objectName, ", invalid field type: ", kindOfField,"."
        exit(1)
    print "    ADDED FIELD:\t", kindOfField, fieldName

def addFlag(objSpecs, objectName, flagName):
    if(flagName in objSpecs[objectName]["fields"]):
        print "Note: The flag '", objectName, '::', flagName, "' already exists. Not re-adding"
        return
    objSpecs[objectName]["fields"].append({'kindOfField':'flag', 'fieldName':flagName})
    print "    ADDED FLAG: \t", flagName


def addMode(objSpecs, objectName, modeName, enumList):
    objSpecs[objectName]["fields"].append({'kindOfField':'mode', 'fieldName':modeName, 'enumList':enumList})
    print "    ADDED MODE:\t", modeName
    print enumList

def addConst(objSpecs, objectName, cppType, constName, constValue):
    objSpecs[objectName]["fields"].append({'kindOfField':'const', 'fieldType':cppType, 'fieldName':constName, 'fieldValue':constValue})
    print "    ADDED CONST\n"

def addFunc(objSpecs, objectName, returnType, funcName, argList, tagList, funcBody, funcTextVerbatim):
    objSpecs[objectName]["fields"].append({'kindOfField':'func', 'funcText':funcBody, 'fieldType':returnType, 'fieldName':funcName, 'argList':argList, 'funcTextVerbatim':funcTextVerbatim})
    registerBaseType(returnType, objectName)
    print "    ADDED FUNCTION:\t", funcName, '(', argList, ')'

###############

def searchATagStore(tagStore, tagToFind):
    print "SEARCHING for", tagToFind
    tagSegs=tagToFind.split(r'.')
    crntStore=tagStore
    item=''
    for seg in tagSegs:
        print seg
        if(seg in crntStore):
            item=crntStore[seg]
            crntStore=item
        else: return None
        print seg, item
    print item
    return [item]

def fetchTagValue(tagStoreArray, tagToFind):
    for tagStore in reversed(tagStoreArray):
        tagRet=searchATagStore(tagStore, tagToFind)
        if(tagRet):
            return tagRet[0]
    return None

def setTagValue(tagStore, tagToSet, tagValue):
    tagRet=searchATagStore(tagStore, tagToSet)
    tagRet[0]=tagValue

def wrapFieldListInObjectDef(objName, fieldDefStr):
    retStr='object '+objName +' {\n' + fieldDefStr + '\n}\n'
    return retStr

###############

def createTypedefName(ItmType):
    if(isinstance(ItmType, basestring)):
        return ItmType
    else:
        baseType=createTypedefName(ItmType[1])
        suffix=''
        typeHead=ItmType[0]
        if(typeHead=='rPtr'): suffix='Ptr'
        elif(typeHead=='sPtr'): suffix='SPtr'
        elif(typeHead=='uPtr'): suffix='UPtr'
        return baseType+suffix

def getNameSegInfo(objMap, structName, fieldName):
    structToSearch = objMap[structName]
    if not structToSearch: print "struct ", structName, " not found."; exit(2);
    fieldListToSearch = structToSearch['fields']
    if not fieldListToSearch: print "struct's fields ", structName, " not found."; exit(2);
    for fieldRec in fieldListToSearch:
        if fieldRec['fieldName']==fieldName:
            print "FOR ", structName, '::', fieldName, ", returning", fieldRec
            return fieldRec
    return None

def getFieldInfo(objMap, structName, fieldNameSegments):
    # return [kind-of-last-element,  reference-string, type-of-last-element]
    structKind=""
    prevKind="xPtr"
    structType=""
    referenceStr=""
    print "    Getting Field Info for:", structName, fieldNameSegments
    for fieldName in fieldNameSegments:
        print "    Segment:",structName,'::',fieldName;
        REF=getNameSegInfo(objMap, structName, fieldName)
        if(REF):
            print "    REF:", REF
            if 'kindOfField' in REF:
                structKind=REF['kindOfField']
                if(prevKind[1:]=="Ptr"): joiner='->'
                else: joiner= '.'
                if (structKind=='flag'):
                    referenceStr+=joiner+"flags"
                elif structKind=='mode':
                    referenceStr+=joiner+'flags'
                elif structKind=='var':
                    referenceStr+= joiner+fieldName
                    structType=REF['fieldType'][1]
                elif structKind=='iPtr' or structKind=='rPtr' or structKind=='sPtr' or structKind=='uPtr':
                    referenceStr+= joiner+fieldName
                    structType=REF['fieldType']
                prevKind=structKind
            structName=structType
        else: print "Problem getting name seg info:", structName, fieldName; exit(1);
    return [structKind, referenceStr, structType]

def getValueString(objMap, structName, valItem):
    if isinstance(valItem, list):
        return getFieldInfo(objMap, structName, valItem)
    else:
        return (["", valItem])

def getActionTestStrings(objMap, structName, action):
    print "################################ Getting Action and Test string for", structName, "ACTION:", action
    LHS=getFieldInfo(objMap, structName, action[0])
    print "LHS:", LHS
    RHS=getValueString(objMap, structName, action[2])
    leftKind=LHS[0]
    actionStr=""; testStr="";
    if leftKind =='flag':
        print "ACTION[0]=", action[2][0]
        actionStr="SetBits(ITEM->flags, "+action[0][-1]+", "+ action[2][0]+");"
        testStr="(flags&"+action[0][0]+")"
    elif leftKind == "mode":
        ITEM="ITEM"
        actionStr="SetBits("+ITEM+LHS[1]+", "+action[0][-1]+"Mask, "+ action[2][0]+");"
        testStr="((flags&"+action[0][-1]+"Mask)"+">>"+action[0][-1]+"Offset) == "+action[2][0]
    elif leftKind == "var":
        actionStr="ITEM"+LHS[1]+action[1]+action[2][0]+'; '
        testStr=action[0][0]+"=="+action[2][0]
    elif leftKind == "ptr":
        print "PTR - ERROR: CODE THIS"
        exit(2)
    return ([leftKind, actionStr, testStr])

