
# ProgSpec manipulation routines

import sys
import re

MaxLogLevelToShow = 2

storeOfBaseTypesUsed={} # Registry of all types used

libsToUse={}

#########################
# Variables to store what objects and fields were added after a marked point (When MarkItems=True).
# So that they can be "rolled back" later. (For rolling back libaries, etc.)

MarkItems=False
MarkedObjects={}
MarkedFields=[]
ModifierCommands=[]
funcsCalled={}
structsNeedingModification={}

def rollBack(objSpecs):
    global MarkedObjects
    global MarkedFields
    global ModifierCommands
    global structsNeedingModification

    for ObjToDel in MarkedObjects.keys():
        del objSpecs[0][ObjToDel]
        objSpecs[1].remove(ObjToDel)

    for fieldToDel in MarkedFields:
        removeFieldFromObject(objSpecs, fieldToDel[0],  fieldToDel[1])

    # Delete platform-specific ModifierCommands
    idx=0
    while(idx<len(ModifierCommands)):
        if ModifierCommands[idx][3]==True:
            del ModifierCommands[idx]
        else: idx+=1

    # Delete platform-specific funcsCalled
    for FC_ListKey in funcsCalled:
        idx=0
        FC_List=funcsCalled[FC_ListKey]
        while(idx<len(FC_List)):
            if FC_List[idx][1]==True:
                del FC_List[idx]
            else: idx+=1

    # Delete platform-specific items in CodeGenerator.structsNeedingModification {}
    itemsToDelete=[]
    for itm in structsNeedingModification:
        if structsNeedingModification[itm][3] == True:
            itemsToDelete.append(itm)
    for itm in itemsToDelete: del(structsNeedingModification[itm])

    # Clear other variables
    MarkedObjects={}
    MarkedFields=[]

#########################

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

def addObject(objSpecs, objectNameList, name, stateType, configType):
    global MarkItems
    global MarkedObjects
    # Config type is [unknown | SEQ | ALT]
    #print "ADDING:", name, stateType
    if stateType=='model': name='%'+name
    elif stateType=='string': name='$'+name
    if(name in objSpecs):
        #print "NOT ADDING:"
        cdlog(4, "Note: The struct '{}' is being added but already exists.".format(name))
        return
    objSpecs[name]={'name':name, "attrList":[], "attr":{}, "fields":[], 'stateType':stateType, 'configType':configType}
    objectNameList.append(name)
    if MarkItems: MarkedObjects[name]=1
    #print "ADDED STRUCT: ", name

def addObjTags(objSpecs, objectName, stateType, objTags):
    startTags = {}
    if stateType=='model': objectName='%'+objectName
    elif stateType=='string': objectName='$'+objectName
    if ('tags' in objSpecs[objectName]):
        startTags = objSpecs[objectName]['tags']
        # append tags here
        objSpecs[objectName]['tags'].update(objTags)
       # print "    APPENDED Tags to "+objectName+".\t"
    else:
        objSpecs[objectName]['tags']=objTags
       # print "    ADDED Tags to "+objectName+".\t"

def addModifierCommand(objSpecs, objName, funcName, commandArg, commandStr):
    global MarkItems
    global ModifierCommands
    ModifierCommands.append([objName, funcName, commandStr, commandArg, MarkItems])

def appendToFuncsCalled(funcName,funcParams):
    global MarkItems
    global funcsCalled
    if not(funcName in funcsCalled):
        funcsCalled[funcName]= []
    funcsCalled[funcName].append([funcParams, MarkItems])


def packField(thisIsNext, thisOwner, thisType, thisArraySpec, thisName, thisArgList, paramList, thisValue):
    codeConverter=None
    packedField = {'isNext': thisIsNext, 'typeSpec':{'owner':thisOwner, 'fieldType':thisType, 'arraySpec':thisArraySpec,'argList':thisArgList}, 'fieldName':thisName, 'paramList':paramList,  'value':thisValue}
    if( thisValue!=None and (not isinstance(thisValue, basestring)) and len(thisValue)>1 and thisValue[1]!='' and thisValue[1][0]=='!'):
        # This is where the definitions of code conversions are loaded. E.g., 'setRGBA' might get 'setColor(new Color(%1, %2, %3, %4))'
        codeConverter = thisValue[1][1:]
        packedField['typeSpec']['codeConverter']=codeConverter
    return packedField

def addField(objSpecs, objectName, stateType, packedField):
    global MarkItems
    global MarkedObjects
    global MarkedFields
    global ModifierCommands
    thisName=packedField['fieldName']
    if stateType=='model': objectName='%'+objectName
    elif stateType=='string': objectName='$'+objectName
    #print "ADDING FIELD:", objectName, stateType, thisName
    if thisName in objSpecs[objectName]["fields"]:
        cdlog(2, "Note: The field '" + objectName + '::' + thisName + "' already exists. Not re-adding")
        return
    objSpecs[objectName]["fields"].append(packedField)

    if MarkItems:
        if not (objectName in MarkedObjects):
            MarkedFields.append([objectName, thisName])

    #if(thisOwner!='flag' and thisOwner!='mode'):
        #print "FIX THIS COMMENTED OUT PART", thisType, objectName #registerBaseType(thisType, objectName)

    if 'optionalTags' in packedField:
        for tag in packedField['optionalTags']:
            if tag[:7]=='COMMAND':
                newCommand = packedField['optionalTags'][tag]
                commandArg = tag[8:]
                addModifierCommand(objSpecs, objectName, thisName, commandArg, newCommand)

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
           # print "Removed: ", field["fieldName"]
            del fieldList[idx]
        idx+=1

###############  Various type-handling functions

def getTypeSpecOwner(typeSpec):
    if typeSpec==None or isinstance(typeSpec, basestring): return 'me'
    if "arraySpec" in typeSpec and typeSpec['arraySpec']!=None:
        if "owner" in typeSpec['arraySpec']:
            return typeSpec['arraySpec']['owner']
        else: return 'me'
    return typeSpec['owner']

def typeIsPointer(typeSpec):
    owner=getTypeSpecOwner(typeSpec)
    if owner == 'their' or owner == 'our' or owner == 'my' or owner == 'itr': isPointer=True
    else: isPointer=False
    return isPointer

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


def findSpecOf(objMap, structName, stateTypeWanted):
    if stateTypeWanted=='model': structName='%'+structName
    elif stateTypeWanted=='string': structName='$'+structName
    if not structName in objMap[0]: return None
    return objMap[0][structName]

def baseStructName(structName):
    colonIndex=structName.find('::')
    if(colonIndex==-1): return structName
    return structName[0:colonIndex]

def isStruct(fieldType):
    if isinstance(fieldType, basestring): return False
    return True

def isAltStruct(objects, fieldType):
    if not isStruct(fieldType) or not(fieldType[0] in objects[0]): return [False, [] ]
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

def typeIsInteger(fieldType):
    if typeIsNumRange(fieldType): return true
    if isinstance(fieldType, basestring):
        if fieldType[:3]=='int' or fieldType[:4]=='uint': return True
    elif fieldType[0][:3]=='int' or fieldType[0][:4]=='uint': return True
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
    elif isStruct(fieldType) and (fieldType[0] in objects[0]):
        fieldObj=objects[0][fieldType[0]]
        fieldObjConfig=fieldObj['configType']
        if(fieldObjConfig=='ALT'):
            innerTypeSpec=fieldObj['fields'][0]['typeSpec']
            retType = TypeSpecsMinimumBaseType(objects, innerTypeSpec)
            return retType
    return fieldType

def innerTypeCategory(fieldType):
    if fieldType=='flag' or fieldType=='mode' or fieldType=='void' or fieldType=='char' or fieldType=='double' or fieldType=='string' or fieldType=='bool': return fieldType
    if typeIsInteger(fieldType): return 'int'
    if isStruct(fieldType): return 'struct'
    return 'ERROR'

def fieldsTypeCategory(typeSpec):
    if 'argList' in typeSpec and typeSpec['argList']!=None: return 'func'
    fieldType=typeSpec['fieldType']
    return innerTypeCategory(fieldType)



def flattenObjectName(objName):
    if objName[-5:]=='::mem': return objName[:-5]
    return objName.replace('::', '_')


def stringFromFile(filename):
    f=open(filename)
    Str = f.read()
    f.close()
    return Str

#############################################################  Logging functions
lastLogMesgs=['','','','','','','','','','']
highestLvl=0;
noError=False

def logLvl():
    return highestLvl+1

def dePythonStr(pyItem):
    S=str(pyItem).replace('[','')
    S=S.replace(']','')
    S=S.replace('(','')
    S=S.replace(')','')
    S=S.replace("'",'')
    S=S.replace(' ','')
    S=S.replace(',','.')
    return S

def printAtLvl(lvl, mesg, indent):
    for i in range(0, lvl): sys.stdout.write(indent)
    print mesg


def resizeLogArray(lvl):
    global lastLogMesgs
    while(lvl+1>len(lastLogMesgs)):
        lastLogMesgs.append('')

def cdlog(lvl, mesg):
    global MaxLogLevelToShow
    global lastLogMesgs
    global highestLvl
    highestLvl=lvl
    resizeLogArray(lvl)
    lastLogMesgs[lvl]=mesg
    for i in range(highestLvl+1, len(lastLogMesgs)):
        lastLogMesgs[i]=''
    if(lvl<=MaxLogLevelToShow):
        if(lvl==0): print('')
        printAtLvl(lvl, mesg, '|    ')

def cdErr(mesg):
    global lastLogMesgs
    global highestLvl
    highestLvl+=1
    lastLogMesgs[highestLvl]="Error: "+mesg
    exit(1)

def whenExit():
    global lastLogMesgs
    global highestLvl
    global noError
    if(noError): return;
    print "\n\nAn error occured while:",
    for i in range(0, highestLvl+1):
        printAtLvl(i, lastLogMesgs[i], '    ')
    print("\n")

def saveTextToErrFile(textToSave):
    text_file = open("ErrFile.txt", "w")
    text_file.write(textToSave)
    text_file.close()
