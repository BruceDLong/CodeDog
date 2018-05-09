
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
currentCheckObjectVars = ""

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

patternNonce = 0
def addPattern(objSpecs, objectNameList, name, patternList):
    global patternNonce
    patternName='!'+name+'.'+str(patternNonce)
    objectNameList.append(patternName)
    objSpecs[patternName[1:]]={'name':name, 'parameters':patternList}
    patternNonce += 1

def processParentClass(name, parentClass):
    global classHeirarchyInfo
    if name in classHeirarchyInfo: return
    if not parentClass in classHeirarchyInfo: classHeirarchyInfo[parentClass]={}
    if not 'childClasses' in classHeirarchyInfo[parentClass]: classHeirarchyInfo[parentClass]['childClasses']=[]
    classHeirarchyInfo[parentClass]['childClasses'].append(name)
    classHeirarchyInfo[name]={'parentClass': parentClass, 'childClasses': []}

# returns an identifier for functions that accounts for class and argument types
def fieldIdentifierString(className, packedField):
    fieldName = packedField['fieldName']
    if fieldName == None: fieldName =""
    fieldID=className+'::'+fieldName
    if 'typeSpec' in packedField: typeSpec=packedField['typeSpec']
    if 'argList' in typeSpec and typeSpec['argList'] :
        argList = typeSpec['argList']
        fieldID+='('
        count=0
        for arg in argList:
            if count>0: fieldID+=','
            fieldID += fieldTypeKeyword(arg['typeSpec']['fieldType'])
            count+=1
        fieldID+=')'
    return fieldID

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
    if MarkItems: MarkedObjects[name]=1
    return name

def appendToAncestorList(objRef, className, subClassMode, parentClassList):
    #subClassMode ="inherits" or "implements"
    #objRef = objSpecs[className]
    if not subClassMode in objRef:
        objRef[subClassMode] = []
    parentClassList = parentClassList.replace(" ", "")
    tmpList = parentClassList.split(",")
    for parentClass in tmpList:
        if subClassMode=='inherits': processParentClass(className, parentClass)
        if (not parentClass in objRef[subClassMode]):
            objRef[subClassMode].append(parentClass)

def addObjTags(objSpecs, className, stateType, objTags):
    startTags = {}
    if stateType=='model': className='%'+className
    elif stateType=='string': className='$'+className
    objRef = objSpecs[className]
    if ('tags' in objRef):
        objRef['tags'].update(objTags)
        #print "    APPENDED Tags to "+className+".\t", str(objTags)
    else:
        objRef['tags']=objTags
        #print "    ADDED Tags to "+className+".\t", str(objTags)
    if ('inherits' in objRef['tags']):
        parentClassList = objRef['tags']['inherits']
        appendToAncestorList(objRef, className, 'inherits', parentClassList)
        addDependancyToStruct(className, parentClassList)
    if ('implements' in objRef['tags']):
        appendToAncestorList(objRef, className, 'implements', objRef['tags']['implements'])

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


def packField(className, thisIsNext, thisOwner, thisType, thisArraySpec, thisName, thisArgList, paramList, thisValue, isAllocated):
    codeConverter=None
    packedField = {'isNext': thisIsNext, 'typeSpec':{'owner':thisOwner, 'fieldType':thisType, 'arraySpec':thisArraySpec,'argList':thisArgList}, 'fieldName':thisName, 'paramList':paramList, 'value':thisValue, 'isAllocated':isAllocated}
    if( thisValue!=None and (not isinstance(thisValue, basestring)) and len(thisValue)>1 and thisValue[1]!='' and thisValue[1][0]=='!'):
        # This is where the definitions of code conversions are loaded. E.g., 'setRGBA' might get 'setColor(new Color(%1, %2, %3, %4))'
        codeConverter = thisValue[1][1:]
        packedField['typeSpec']['codeConverter']=codeConverter
    fieldID = fieldIdentifierString(className, packedField)
    #print "FIELD-ID", fieldID
    packedField['fieldID']=fieldID
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
    fieldID = packedField['fieldID']
    typeSpec = packedField['typeSpec']
    fieldType = typeSpec['fieldType']
    if stateType=='model': taggedClassName='%'+className
    elif stateType=='string': taggedClassName='$'+className
    else: taggedClassName = className
    if stateType!='string':
        fieldIfExists = doesClassDirectlyImlementThisField(objSpecs, className, fieldID)
        field=fieldIfExists
        if fieldIfExists:
            cdlog(2, "Note: The field '" + fieldID + "' already exists. Not re-adding")
            if not isinstance(fieldIfExists, dict): return
            if not ('value' in field) or field['value']==None: return
            if not ('value' in packedField)   or packedField['value']  ==None: return
            if field['value']==packedField['value']: return
            cdErr(fieldID+" is being contradictorily redefined.")

        # Don't override flags and modes in derived classes
        if fieldType=='flag' or fieldType=='mode':
            if fieldIDAlreadyDeclaredInStruct(objSpecs, className, fieldID):
                cdlog(2, "Note: The field '" + fieldID + "' already exists. Not overriding")
                return

    objSpecs[taggedClassName]["fields"].append(packedField)
    objSpecs[taggedClassName]["vFields"]=None


    # if me or we and type is struct add unique dependancy
    fieldOwner = typeSpec['owner']
    if (fieldOwner=='me' or fieldOwner=='we' or fieldOwner=='const') and fieldsTypeCategory(typeSpec)=='struct':
        addDependancyToStruct(className, fieldType[0])


    if MarkItems:
        if not (taggedClassName in MarkedObjects):
            MarkedFields.append([taggedClassName, fieldID])

    if 'optionalTags' in packedField:
        for tag in packedField['optionalTags']:
            if tag[:7]=='COMMAND':
                newCommand = packedField['optionalTags'][tag]
                commandArg = tag[8:]
                addModifierCommand(objSpecs, taggedClassName, fieldID, commandArg, newCommand)

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
        if field['fieldID']==F['fieldID']:
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

def populateCallableStructFields(fieldList, classes, structName):  # e.g. 'type::subType::subType2'
    #print "POPULATING-STRUCT:", structName
    structSpec=findSpecOf(classes[0], structName, 'struct')
    if structSpec==None: return
    if structSpec['vFields']!=None:
        fieldList.extend(structSpec['vFields'])
        return
    classInherits = searchATagStore(structSpec['tags'], 'inherits')
    if classInherits!=None:
        for classParent in classInherits:
            populateCallableStructFields(fieldList, classes, classParent)
    classInherits = searchATagStore(structSpec['tags'], 'implements')
    if classInherits!=None:
        for classParent in classInherits:
            populateCallableStructFields(fieldList, classes, classParent)

    modelSpec=findSpecOf(classes[0], structName, 'model')
    if(modelSpec!=None): updateCvt(classes, fieldList, modelSpec["fields"])
    modelSpec=findSpecOf(classes[0], structName, 'struct')
    updateCpy(fieldList, modelSpec["fields"])

    structSpec['vFields'] = fieldList

def generateListOfFieldsToImplement(classes, structName):
    fieldList=[]
    modelSpec=findSpecOf(classes[0], structName, 'model')
    if(modelSpec!=None): updateCvt(classes, fieldList, modelSpec["fields"])
    modelSpec=findSpecOf(classes[0], structName, 'struct')
    if(modelSpec!=None): updateCpy(fieldList, modelSpec["fields"])
    return fieldList

def fieldOnlyID(fieldID):
    breakPos = fieldID.find('::')
    if breakPos<0: return fieldID
    return fieldID[breakPos+2:]

def fieldDefIsInList(fieldList, fieldID):
    for field in fieldList:
        if 'fieldID' in field and fieldOnlyID(field['fieldID']) == fieldOnlyID(fieldID):
            if 'typeSpec' in field and field['typeSpec']!=None: typeSpec=field['typeSpec']
            else: typeSpec=None

            fieldIsAFunction = fieldIsFunction(typeSpec)
            if not fieldIsAFunction: return True
            if fieldIsAFunction and 'value' in field and field['value']!=None:       # AND, the function is defined
                return field
    return False

def fieldIDAlreadyDeclaredInStruct(classes, structName, fieldID):
    structSpec=findSpecOf(classes, structName, 'struct')
    if structSpec==None:
        return False;
    if structSpec['vFields']!=None:
        for field in structSpec['vFields']:
            if fieldID == field['fieldID']:
                return True

    classInherits = searchATagStore(structSpec['tags'], 'inherits')
    if classInherits!=None:
        for classParent in classInherits:
            if fieldIDAlreadyDeclaredInStruct(classes, classParent, fieldID):
                return True

    classImplements = searchATagStore(structSpec['tags'], 'implements')
    if classImplements!=None:
        for classParent in classImplements:
            if fieldIDAlreadyDeclaredInStruct(classes, classParent, fieldID):
                return True

    modelSpec=findSpecOf(classes, structName, 'model')
    if(modelSpec!=None):
        if fieldDefIsInList(modelSpec["fields"], fieldID):
            return True

    if(structSpec!=None):
        if fieldDefIsInList(structSpec["fields"], fieldID):
            return True
    return False

#### These functions help evaluate parent-class / child-class relations

def doesClassDirectlyImlementThisField(objSpecs, structName, fieldID):
    #print '        ['+structName+']: ', fieldID
    modelSpec=findSpecOf(objSpecs, structName, 'model')
    if(modelSpec!=None):
        fieldExists = fieldDefIsInList(modelSpec["fields"], fieldID)
        if fieldExists:
            return fieldExists
    structSpec=findSpecOf(objSpecs, structName, 'struct')
    if(structSpec!=None):
        fieldExists = fieldDefIsInList(structSpec["fields"], fieldID)
        if fieldExists:
            return fieldExists
    return False

def doesClassFromListDirectlyImplementThisField(classes, structNameList, fieldID):
    if structNameList==None or len(structNameList)==0: return False
    for structName in structNameList:
        if doesClassDirectlyImlementThisField(classes[0], structName, fieldID):
            return True
    return False

def getParentClassList(classes, thisStructName):  # Checks 'inherits' but does not check 'implements'
    structSpec=findSpecOf(classes[0], thisStructName, 'struct')
    classInherits = searchATagStore(structSpec['tags'], 'inherits')
    if classInherits==None: classInherits=[]
    #print  thisStructName+':', classInherits
    return classInherits

def getChildClassList(classes, thisStructName):  # Checks 'inherits' but does not check 'implements'
    if thisStructName in classHeirarchyInfo:
        classRelationData = classHeirarchyInfo[thisStructName]
        if 'childClasses' in classRelationData and len(classRelationData['childClasses'])>0:
            return classRelationData['childClasses']
    return []

def doesParentClassImplementFunc(classes, structName, fieldID):
    #print '     Parents:\n',
    parentClasses=getParentClassList(classes, structName)
    result = doesClassFromListDirectlyImplementThisField(classes, parentClasses, fieldID)
    #if len(parentClasses)>0: print '       P-Results:', result
    return result

def doesChildClassImplementFunc(classes, structName, fieldID):
    #print '\n     Childs:\n',
    childClasses=getChildClassList(classes, structName)
    result = doesClassFromListDirectlyImplementThisField(classes, childClasses, fieldID)
    #if len(childClasses)>0: print '     Childs Result:', result
    return result

###############  Various type-handling functions
def setCurrentCheckObjectVars(message):
    global currentCheckObjectVars
    currentCheckObjectVars = message

def getTypeSpecOwner(typeSpec):
    global currentCheckObjectVars
    if (typeSpec == 0):
        cdErr(currentCheckObjectVars)
    if typeSpec==None or isinstance(typeSpec, basestring): return 'me'
    if "arraySpec" in typeSpec and typeSpec['arraySpec']!=None:
        if "owner" in typeSpec['arraySpec']:
            owner = typeSpec['arraySpec']['owner']
            return owner
        else: return 'me'
    return typeSpec['owner']

def ownerIsPointer(owner):
    if owner == 'their' or owner == 'our' or owner == 'my' or owner == 'itr' or owner == 'id_their' or owner == 'id_our': isPointer=True
    else: isPointer=False
    return isPointer

def typeIsPointer(typeSpec):
    owner=getTypeSpecOwner(typeSpec)
    return ownerIsPointer(owner)

def fieldIsFunction(typeSpec):
    if typeSpec==None: return False
    if 'argList' in typeSpec and typeSpec['argList']!=None: return True
    return False

def isWrappedType(objMap, structname):
    # If type is not wrapped, return None, else return the wrapped typeSpec
    if not structname in objMap[0]:
        #print "Struct "+structname+" not found"
        return None; # TODO: "Print Struct "+structname+" not found" But not if type is base type.
    structToSearch=findSpecOf(objMap[0], structname, 'struct')
    fieldListToSearch = structToSearch["fields"]
    if not fieldListToSearch: return None
    if len(fieldListToSearch)>0:
        for field in fieldListToSearch:
            if field['fieldName']==structname and field['typeSpec']['argList']==None:
                #print "isWrappedType: ", field['typeSpec']['argList'], structname
                return field['typeSpec']
    return None

def wrappedTypeIsPointer(classes, typeSpec, structName):
    # like typeIsPointer() but also checks wrapped type
    result = typeIsPointer(typeSpec)
    if result==True: return True

    baseType = isWrappedType(classes, structName)
    if(baseType==None): return result
# TODO: FIX
    exit(2)
    return typeIsPointer(baseType)

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

def unwrapClass(classes, structName):
    baseType = isWrappedType(classes, structName)
    if(baseType!=None):
        baseType = baseType['fieldType']
        if isinstance(baseType, basestring): return baseType
        return baseType[0]
    else: return structName

def baseStructName(structName):
    colonIndex=structName.find('::')
    if(colonIndex==-1): return structName
    return structName[0:colonIndex]

def fieldTypeKeyword(fieldType):
    if fieldType==None: return 'NONE'
    if 'fieldType' in fieldType: fieldType = fieldType['fieldType'];
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

def varsTypeCategory(typeSpec):
    if isinstance(typeSpec, basestring): fieldType=typeSpec
    else:
        fieldType=typeSpec['fieldType']
    return innerTypeCategory(fieldType)

def fieldsTypeCategory(typeSpec):
    if 'argList' in typeSpec and typeSpec['argList']!=None: return 'func'
    return varsTypeCategory(typeSpec)

def varTypeKeyWord(typeSpec):
    if isinstance(typeSpec, basestring): varType=typeSpec
    elif typeSpec==None or typeSpec==0: varType='ERROR'
    elif typeSpec['owner']=='PTR': varType='PTR'
    else:
        #print"varTypeKeyWord: ", typeSpec
        varType = varsTypeCategory(typeSpec)
        if varType =='int':
            varType = fieldTypeKeyword(typeSpec)
    return varType

def typeSpecsAreCompatible(typeSpec1, typeSpec2):
    if getTypeSpecOwner(typeSpec1) != getTypeSpecOwner(typeSpec2): return False
    if fieldTypeKeyword(typeSpec1['fieldType']) != fieldTypeKeyword(typeSpec2['fieldType']): return False
    leftContainerNull  = not('arraySpec' in typeSpec1) or (('arraySpec' in typeSpec1) and typeSpec1['arraySpec']==None)
    rightContainerNull = not('arraySpec' in typeSpec2) or (('arraySpec' in typeSpec2) and typeSpec2['arraySpec']==None)
    if not leftContainerNull and rightContainerNull: return False
    if leftContainerNull and not rightContainerNull: return False
    if not leftContainerNull and not rightContainerNull and typeSpec1['arraySpec'] != typeSpec2['arraySpec']: return False
    return True

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
    S=S.replace("'",'')
    S=S.replace(' ','')
    parenPos = S.find('(')
    if(parenPos>=0):
        itemName = S[:parenPos]
        itemName = itemName.replace(',','.')
        paramList = S[parenPos+1:]
        paramList = paramList.replace(',,,,,,', '!')
        paramList = paramList.replace(',', '')
        paramList = paramList[:-1].replace('!', ', ')
        S = itemName[:-1] + '('+paramList+')'
    else:
        S=S.replace(',','.')
        S=S.replace('(','')
        S=S.replace(')','')
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
