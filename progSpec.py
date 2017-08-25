
# ProgSpec manipulation routines

import sys
import re

MaxLogLevelToShow = 1

storeOfBaseTypesUsed={} # Registry of all types used


#########################
# Variables to store what classes and fields were added after a marked point (When MarkItems=True).
# So that they can be "rolled back" later. (For rolling back libaries, etc.)

MarkItems=False
MarkedObjects={}
MarkedFields=[]
ModifierCommands=[]
funcsCalled={}
structsNeedingModification={}
DependanciesUnmarked={}
DependanciesMarked={}
classHeirarchyInfo = {}

def rollBack(classes):
    global MarkedObjects
    global MarkedFields
    global ModifierCommands
    global structsNeedingModification
    global DependanciesMarked

    for ObjToDel in MarkedObjects.keys():
        del classes[0][ObjToDel]
        classes[1].remove(ObjToDel)

    for fieldToDel in MarkedFields:
        removeFieldFromObject(classes, fieldToDel[0],  fieldToDel[1])

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
    DependanciesMarked={}

#########################

def getTypesBase(typeSpec):
    if isinstance(typeSpec, basestring):
       return typeSpec
    else: return getTypesBase(typeSpec[1])

def registerBaseType(usedType, className):
    #print "registerBaseType: ", usedType, className
    baseType=getTypesBase(usedType)
    if not (baseType in storeOfBaseTypesUsed):
        storeOfBaseTypesUsed[baseType]={}
    if not (className in storeOfBaseTypesUsed[baseType]):
        storeOfBaseTypesUsed[baseType][className]=0
    else: storeOfBaseTypesUsed[baseType][className] += 1

def addPattern(objSpecs, objectNameList, name, patternList):
    patternName='!'+name
    objectNameList.append(patternName)
    objSpecs[name]={'name':patternName, 'parameters':patternList}

def processParentClass(name):
    global classHeirarchyInfo
    if name in classHeirarchyInfo: return
    parentClass=None
    colonPos = name.rfind('::')
    if colonPos>=0:
        parentClass=name[0:colonPos]
        processParentClass(parentClass)
        classHeirarchyInfo[parentClass]['childClasses'].append(name)

    classHeirarchyInfo[name]={'parentClass': parentClass, 'childClasses': []}

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
        return None
    objSpecs[name]={'name':name, "attrList":[], "attr":{}, "fields":[], "vFields":None, 'stateType':stateType, 'configType':configType}
    objectNameList.append(name)
    processParentClass(name)
    if MarkItems: MarkedObjects[name]=1
    return name

def addObjTags(objSpecs, className, stateType, objTags):
    startTags = {}
    if stateType=='model': className='%'+className
    elif stateType=='string': className='$'+className
    if ('tags' in objSpecs[className]):
        objSpecs[className]['tags'].update(objTags)
        #print "    APPENDED Tags to "+className+".\t", str(objTags)
    else:
        objSpecs[className]['tags']=objTags
        #print "    ADDED Tags to "+className+".\t", str(objTags)

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

def addDependancyToStruct(structName, nameOfDependancy):
    global DependanciesMarked
    global DependanciesUnmarked
    if structName == nameOfDependancy: return
    #print "DEPINFO:",  structName, nameOfDependancy
    if MarkItems: listToUpdate = DependanciesMarked
    else: listToUpdate = DependanciesUnmarked
    if not(structName in listToUpdate): listToUpdate[structName]=[nameOfDependancy]
    else:
        if not (nameOfDependancy in listToUpdate[structName]):
            listToUpdate[structName].append(nameOfDependancy)

def getClassesDependancies(className):
    global DependanciesMarked
    global DependanciesUnmarked
    retList=[]
    if className in DependanciesUnmarked: retList.extend(DependanciesUnmarked[className])
    if className in DependanciesMarked:   retList.extend(DependanciesMarked[className])
    return retList

def addField(objSpecs, className, stateType, packedField):
    global MarkItems
    global MarkedObjects
    global MarkedFields
    global ModifierCommands
    thisName=packedField['fieldName']
    if stateType=='model': taggedObjectName='%'+className
    elif stateType=='string': taggedObjectName='$'+className
    else: taggedObjectName = className
    #print "ADDING FIELD:", taggedObjectName, stateType, thisName
    if thisName in objSpecs[taggedObjectName]["fields"]:
        cdlog(2, "Note: The field '" + taggedObjectName + '::' + thisName + "' already exists. Not re-adding")
        return

    # Don't override flags and modes in derived classes
    typeSpec = packedField['typeSpec']
    fieldType = typeSpec['fieldType']
    if fieldType=='flag' or fieldType=='mode':
        if fieldAlreadyDeclaredInStruct(objSpecs, className, thisName):
            return

    objSpecs[taggedObjectName]["fields"].append(packedField)
    objSpecs[taggedObjectName]["vFields"]=None


    # if me or we and type is struct add unique dependancy
    fieldOwner = typeSpec['owner']
    if (fieldOwner=='me' or fieldOwner=='we') and fieldsTypeCategory(typeSpec)=='struct':
        addDependancyToStruct(className, fieldType[0])


    if MarkItems:
        if not (taggedObjectName in MarkedObjects):
            MarkedFields.append([taggedObjectName, thisName])

    if 'optionalTags' in packedField:
        for tag in packedField['optionalTags']:
            if tag[:7]=='COMMAND':
                newCommand = packedField['optionalTags'][tag]
                commandArg = tag[8:]
                addModifierCommand(objSpecs, taggedObjectName, thisName, commandArg, newCommand)

def markStructAuto(objSpecs, className):
    objSpecs[className]["autoGen"]='yes'

###############

def extractListFromTagList(tagVal):
    tagValues=[]
    if ((not isinstance(tagVal, basestring)) and len(tagVal)>=2):
        if(tagVal[0]=='['):
            for multiVal in tagVal[1]:
                tagValues.append(multiVal[0])
    return tagValues

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

def setFeatureNeeded(tags, featureID):
    tags['featuresNeeded'].append(featureID)

def setFeaturesNeeded(tags, featureIDs):
    for feature in featureIDs:
        setFeatureNeeded(tags, feature)

def addCodeToInit(tagStore, newInitCode):
    appendToStringTagValue(tagStore, "initCode", newInitCode + "\n");

def removeFieldFromObject (classes, className, fieldtoRemove):
    if not className in classes[0]:
        return
    fieldList=classes[0][className]['fields']
    idx=0
    for field in fieldList:
        if field["fieldName"] == fieldtoRemove:
           # print "Removed: ", field["fieldName"]
            del fieldList[idx]
        idx+=1

############## Field manupulation regarding inheritance

def insertOrReplaceField(fieldListToUpdate, field):
    idx=0
    for F in fieldListToUpdate:
        if field['fieldName']==F['fieldName']:
            fieldListToUpdate[idx]=field
            return
        idx+=1
    fieldListToUpdate.append(field)

def updateCvt(classes, fieldListToUpdate, fieldsToConvert):
    for F in fieldsToConvert:
        typeSpec=F['typeSpec']
        baseType=TypeSpecsMinimumBaseType(classes, typeSpec)
        G = F.copy()
        if baseType!=None:
            G['typeSpec']=typeSpec.copy()
            G['typeSpec']['fieldType']=baseType
        insertOrReplaceField(fieldListToUpdate, G)

def updateCpy(fieldListToUpdate, fieldsToCopy):
    for field in fieldsToCopy:
        insertOrReplaceField(fieldListToUpdate, field)

def populateCallableStructFields(classes, structName):  # e.g. 'type::subType::subType2'
    #print "POPULATING-STRUCT:", structName
    structSpec=findSpecOf(classes[0], structName, 'struct')
    if structSpec==None: return []
    if structSpec['vFields']!=None: return structSpec['vFields']
    fList=[]
    segIdx=0
    while(segIdx>=0):
        segIdx=structName.find('::', segIdx);
        if segIdx == -1: segStr=structName
        else: segStr=structName[0:segIdx]
        #print "     SEGSTR:", segStr
        modelSpec=findSpecOf(classes[0], segStr, 'model')
        if(modelSpec!=None): updateCvt(classes, fList, modelSpec["fields"])
        modelSpec=findSpecOf(classes[0], segStr, 'struct')
        updateCpy(fList, modelSpec["fields"])
        if(segIdx>=0): segIdx+=1
    structSpec['vFields'] = fList
    return fList

def generateListOfFieldsToImplement(classes, structName):
    fList=[]
    modelSpec=findSpecOf(classes[0], structName, 'model')
    if(modelSpec!=None): updateCvt(classes, fList, modelSpec["fields"])
    modelSpec=findSpecOf(classes[0], structName, 'struct')
    if(modelSpec!=None): updateCpy(fList, modelSpec["fields"])
    return fList

def fieldDefIsInList(fList, fieldName):
    for field in fList:
        if 'fieldName' in field and field['fieldName']==fieldName:
            return True
    return False

def fieldAlreadyDeclaredInStruct(classes, structName, fieldName):  # e.g. 'type::subType::subType2'
    segIdx=0
    while(segIdx>=0):
        segIdx=structName.find('::', segIdx);
        if segIdx == -1: segStr=structName
        else: segStr=structName[0:segIdx]
        #print "     SEGSTR:", segStr, fieldName
        modelSpec=findSpecOf(classes, segStr, 'model')
        if(modelSpec!=None):
            if fieldDefIsInList(modelSpec["fields"], fieldName): return True
        modelSpec=findSpecOf(classes, segStr, 'struct')
        if(modelSpec!=None):
            if fieldDefIsInList(modelSpec["fields"], fieldName): return True
        if(segIdx>=0): segIdx+=1
    return False

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
    structToSearch=findSpecOf(objMap[0], structname, 'struct')
    fieldListToSearch = structToSearch["fields"]
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
    if not structName in objMap: return None
    return objMap[structName]

def baseStructName(structName):
    colonIndex=structName.find('::')
    if(colonIndex==-1): return structName
    return structName[0:colonIndex]

def fieldTypeKeyword(fieldType):
    if isinstance(fieldType, basestring): return fieldType
    return fieldType[0]

def isStruct(fieldType):
    if isinstance(fieldType, basestring): return False
    return True

def isAltStruct(classes, fieldType):
    if not isStruct(fieldType) or not(fieldType[0] in classes[0]): return [False, [] ]
    fieldObj=classes[0][fieldType[0]]
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

def TypeSpecsMinimumBaseType(classes, typeSpec):
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
    elif isStruct(fieldType) and (fieldType[0] in classes[0]):
        fieldObj=classes[0][fieldType[0]]
        fieldObjConfig=fieldObj['configType']
        if(fieldObjConfig=='ALT'):
            innerTypeSpec=fieldObj['fields'][0]['typeSpec']
            retType = TypeSpecsMinimumBaseType(classes, innerTypeSpec)
            return retType
    return fieldType

def innerTypeCategory(fieldType):
    typeKey = fieldTypeKeyword(fieldType)
    if typeKey=='flag' or typeKey=='mode' or typeKey=='void' or typeKey=='char' or typeKey=='double' or typeKey=='float' or typeKey=='string' or typeKey=='bool': return typeKey
    if typeIsInteger(fieldType): return 'int'
    if isStruct(fieldType): return 'struct'
    return 'ERROR'

def fieldsTypeCategory(typeSpec):
    if 'argList' in typeSpec and typeSpec['argList']!=None: return 'func'
    fieldType=typeSpec['fieldType']
    return innerTypeCategory(fieldType)

def flattenObjectName(objName):
    return objName.replace('::', '_')


def stringFromFile(filename):
#    try:
        f=open(filename)
        Str = f.read()
        f.close()
#    except IOError as e:
#        print "FILENAME:", filename
#        cdErr("I/O error({0}): {1}: {2}".format(e.errno, e.strerror, filename))
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
