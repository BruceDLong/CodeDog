
# ProgSpec manipulation routines

import re

storeOfBaseTypesUsed={} # Registry of all types used
codeHeader={} # e.g., codeHeader['cpp']="C++ header code"
libsToUse={}

def setCodeHeader(languageID, codeText):
    global codeHeader
    if not languageID in codeHeader: codeHeader[languageID]='';
    codeHeader[languageID]+='\n'+codeText

def getTypesBase(typeSpec):
    if isinstance(typeSpec, basestring):
       return typeSpec
    else: return getTypesBase(typeSpec[1])

def registerBaseType(usedType, objectName):
    #print "registerBaseType: ", usedType, objectName
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
    print "ADDED PATTERN", name, patternName

def addObject(objSpecs, objectNameList, name, stateType, configType):
    # Config type is [unknown | SEQ | ALT]
    if(name in objSpecs):
        print "Note: The struct '", name, "' is being added but already exists."
        return
    objSpecs[name]={'name':name, "attrList":[], "attr":{}, "fields":[], 'stateType':stateType, 'configType':configType}
    objectNameList.append(name)
    print "ADDED STRUCT: ", name

def addObjTags(objSpecs, objectName, objTags):
    objSpecs[objectName]["tags"]=objTags
    print "    ADDED Tags to "+objectName+".\t"


def packField(thisIsNext, thisOwner, thisType, thisArraySpec, thisName, thisArgList, thisValue):
    codeConverter=None
    packedField = {'isNext': thisIsNext, 'typeSpec':{'owner':thisOwner, 'fieldType':thisType, 'arraySpec':thisArraySpec,'argList':thisArgList}, 'fieldName':thisName,  'value':thisValue}
    if( thisValue!=None and (not isinstance(thisValue, basestring)) and len(thisValue)>1 and thisValue[1]!='' and thisValue[1][0]=='!'):
        # This is where the definitions of code conversions are loaded. E.g., 'setRGBA' might get 'setColor(new Color(%1, %2, %3, %4))'
        codeConverter = thisValue[1][1:]
        packedField['typeSpec']['codeConverter']=codeConverter
    return packedField

def addField(objSpecs, objectName, packedField):
    if(packedField['fieldName'] in objSpecs[objectName]["fields"]):
        print "Note: The field '", objectName, '::', thisName, "' already exists. Not re-adding"
        return
    objSpecs[objectName]["fields"].append(packedField)
    #if(thisOwner!='flag' and thisOwner!='mode'):
        #print "FIX THIS COMMENTED OUT PART", thisType, objectName #registerBaseType(thisType, objectName)


def markStructAuto(objSpecs, objectName):
    objSpecs[objectName]["autoGen"]='yes'

###############

def searchATagStore(tagStore, tagToFind):
    #print "SEARCHING for tag", tagToFind
    tagSegs=tagToFind.split(r'.')
    crntStore=tagStore
    item=''
    for seg in tagSegs:
        #print seg
        if(seg in crntStore):
            item=crntStore[seg]
            crntStore=item
        else: return None
        #print seg, item
    #print item
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

def appendToStringTagValue(tagStore, tagToSet, toAppend):
    tagRet=searchATagStore(tagStore, tagToSet)
    if(tagRet==None):
        tagStore[tagToSet]=toAppend
    else:
        tagRet[0]+= "\n" +toAppend
        tagStore[tagToSet]=tagRet[0]

def wrapFieldListInObjectDef(objName, fieldDefStr):
    retStr='struct '+objName +' {\n' + fieldDefStr + '\n}\n'
    return retStr

def setFeatureNeeded(tags, featureID, objMap):
    tags['featuresNeeded'][featureID]=objMap

def setFeaturesNeeded(tags, featureIDs, neededBy):
    for feature in featureIDs:
        setFeatureNeeded(tags, feature, neededBy)

def addCodeToInit(tagStore, newInitCode):
    appendToStringTagValue(tagStore, "initCode", newInitCode + "\n");

def removeFieldFromObject (objects, objectName, fieldtoRemove):
    if not objectName in objects[0]:
        return
    fieldList=objects[0][objectName]["fields"]
    idx=0
    for field in fieldList:
        if field["fieldName"] == fieldtoRemove:
            print "Removed: ", field["fieldName"]
            del fieldList[idx]
        idx+=1

###############

def isWrappedType(objMap, structname):
    if not structname in objMap[0]:
        #print "Struct "+structname+" not found"
        return None; # TODO: "Print Struct "+structname+" not found" But not if type is base type.
    structToSearch=objMap[0][structname]
    fieldListToSearch = structToSearch['fields']
    if not fieldListToSearch: return None
    if len(fieldListToSearch)>0:
        theField=fieldListToSearch[0]
        if theField['fieldName']==structname:
            return theField['typeSpec']
    return None


def createTypedefName(ItmType):
    if(isinstance(ItmType, basestring)):
        return ItmType
    else:
        return 'BAD-TYPE-NAME'
        baseType=createTypedefName(ItmType[1])
        suffix=''
        typeHead=ItmType[0]
        if(typeHead=='their'): suffix='RPtr'
        elif(typeHead=='our'): suffix='SPtr'
        elif(typeHead=='my'): suffix='UPtr'
        return baseType+suffix


def findModelOf(objMap, structName):
    # returns None or ref to the model. E.g. for date:HR, the model would be 'date'
    colonIndex=structName.find('::')
    if(colonIndex==-1): return None
    modelName=structName[0:colonIndex]
    return objMap[0][modelName]

def baseStructName(structName):
    colonIndex=structName.find('::')
    if(colonIndex==-1): return structName
    return structName[0:colonIndex]

def isStruct(fieldType):
    if isinstance(fieldType, basestring): return False
    return True

def isAltStruct(objects, fieldType):
    if not isStruct(fieldType): return [False, [] ]
    fieldObj=objects[0][fieldType[0]]
    fieldObjConfig=fieldObj['configType']
    Objfields=fieldObj['fields']
    if (fieldObjConfig=='ALT'): return [True, Objfields]
    else: return [False, [] ]

def typeIsNumRange(fieldType):
    if isinstance(fieldType, basestring): return False
    if len(fieldType)==3:
        if fieldType[1]=='..':
            return True
    return False

def fetchFieldByName(fields, fieldName):
    for field in fields:
        fname=field['fieldName']
        if fname==fieldName: return field
    return None

def TypeSpecsMinimumBaseType(objects, typeSpec):
    owner=typeSpec['owner']
    fieldType=typeSpec['fieldType']
    #print "TYPESPEC:", typeSpec, "<", fieldType, ">\n"
    if typeIsNumRange(fieldType):
        minVal = int(fieldType[0])
        maxVal = int(fieldType[2])
        if minVal>=0:
            if (maxVal<=256):    return "uint8"
            if maxVal<=65536:    return "uint16"
            if maxVal<=(2**32):  return "uint32"
            if maxVal<=(2**64):  return "uint64"
            if maxVal<=(2**128): return "uint128"
            else:  return "flexInt"
        else: # Handle signed values (int)
            return "int64"
    elif isStruct(fieldType):
        fieldObj=objects[0][fieldType[0]]
        fieldObjConfig=fieldObj['configType']
        if(fieldObjConfig=='ALT'):
            innerTypeSpec=fieldObj['fields'][0]['typeSpec']
            retType = TypeSpecsMinimumBaseType(objects, innerTypeSpec)
            return retType
    return fieldType

def flattenObjectName(objName):
    if objName[-5:]=='::mem': return objName[:-5]
    return objName.replace('::', '_')

"""
def getNameSegInfo(objMap, structName, fieldName):
    structToSearch = objMap[structName]
    #print fieldName
    if not structToSearch: print "struct ", structName, " not found."; exit(2);
    fieldListToSearch = structToSearch['fields']
    if not fieldListToSearch: print "struct's fields ", structName, " not found."; exit(2);
    for fieldRec in fieldListToSearch:
        #print "fieldRec['fieldName']", fieldRec['fieldName']
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
        #print "REF: ", REF
        if(REF):
            #print "    REF:", REF
            if 'kindOfField' in REF:
                structKind=REF['kindOfField']
                #print "structKind", structKind
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
    #print "LHS:", LHS
    RHS=getValueString(objMap, structName, action[2])
    leftKind=LHS[0]
    actionStr=""; testStr="";
    if leftKind =='flag':
        #print "ACTION[0]=", action[2][0]
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
"""
