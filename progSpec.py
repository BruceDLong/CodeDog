
# ProgSpec manipulation routines

import sys
import re
import copy
from timeit import default_timer as timer
from pyparsing import ParseResults

MaxLogLevelToShow = 1

storeOfBaseTypesUsed={} # Registry of all types used

startTime = timer()
#########################
# Variables to store what Classes and fields were added after a marked point (When MarkItems=True).
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
templatesDefined={}
classImplementationOptions = {}
libLevels = {}

def setLibLevels(childLibList):
    global libLevels
    libLevels = childLibList

def getLibLevel(libName):
    global libLevels
    for lib in range(0,len(libLevels)):
        if (libLevels[lib] == libName):
            return 2
    return 1

def rollBack(classes, tags):
    global MarkedObjects
    global MarkedFields
    global ModifierCommands
    global structsNeedingModification
    global DependanciesMarked
    global funcsCalled

    if 'initCode' in tags and tags['initCode']:
        del tags['initCode']

    for ObjToDel in list(MarkedObjects.keys()):
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

    # Delete platform-specific functions called in two stages
        # First, delete calls of keys marked for deletion
    for FC_ListKey in funcsCalled:
        idx=0
        FC_List=funcsCalled[FC_ListKey]
        while(idx<len(FC_List)):
            if FC_List[idx][1]==True:
                del FC_List[idx]
            else: idx+=1
        # Second, remove empty keys entirely.
        ## This doesn't appear to be necessary
    '''deleteFunc = [key for key in funcsCalled if len(funcsCalled[key]) == 0]
    for key in deleteFunc:
        #print("DELETING KEY: ", key, "      WITH CONTENTS: ", funcsCalled[key])
        del funcsCalled[key]'''

    # Delete platform-specific items in codeGenerator.structsNeedingModification {}
    itemsToDelete=[]
    for itm in structsNeedingModification:
        if structsNeedingModification[itm][3] == True:
            itemsToDelete.append(itm)
    for itm in itemsToDelete: del(structsNeedingModification[itm])

    # Clear other variables
    MarkedObjects={}
    MarkedFields=[]
    DependanciesMarked={}
    # featuresHandled is cleared in libraryMngr.py

#########################

def getTypesBase(tSpec):
    if isinstance(tSpec, str):
       return tSpec
    else: return getTypesBase(tSpec[1])

def registerBaseType(usedType, className):
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
    if not parentClass in classHeirarchyInfo: classHeirarchyInfo[parentClass]={'parentClass': None, 'childClasses': set([name])}
    else: classHeirarchyInfo[parentClass]['childClasses'].add(name)

    if not name in classHeirarchyInfo: classHeirarchyInfo[name]={'parentClass': parentClass, 'childClasses': set([])}
    else:
        prevParentClassName = classHeirarchyInfo[name]['parentClass']
        if prevParentClassName == None:
            classHeirarchyInfo[name]['parentClass'] = parentClass
        elif parentClass != prevParentClassName:
            cdErr("The class "+name+" cannot descend from both "+parentClass+" and "+prevParentClassName)

# returns an identifier for functions that accounts for class and argument types
def fieldIdentifierString(className, packedField):
    fieldName = packedField['fieldName']
    if fieldName == None: fieldName =""
    fieldID=className+'::'+fieldName
    if 'typeSpec' in packedField: tSpec = getTypeSpec(packedField)
    if 'argList' in tSpec and tSpec['argList'] :
        argList = tSpec['argList']
        fieldID+='('
        count=0
        for arg in argList:
            if count>0: fieldID+=','
            fieldID += fieldTypeKeyword(arg)
            count+=1
        fieldID+=')'
    return fieldID

def addObject(objSpecs, objectNameList, name, stateType, configType, libName = None):
    global MarkItems
    global MarkedObjects
    global libLevels
    # Config type is [unknown | SEQ | ALT]

    if libName != None:
        level = getLibLevel(libName)
    else: level = 0

    if stateType=='model': name='%'+name
    elif stateType=='string': name='$'+name
    if(name in objSpecs):
        cdlog(4, "Note: The struct '{}' is being added but already exists.".format(name))
        return None
    objSpecs[name]={'name':name, "attrList":[], "attr":{}, "fields":[], "vFields":None, 'stateType':stateType, 'configType':configType,'libLevel':level, 'libName':libName}
    objectNameList.append(name)
    if MarkItems: MarkedObjects[name]=1
    return name

def filterClassesToList(parentClassList):
    '''Takes string, list or ParseResults and returns it as a list

    This is used in a specific situation where different parse branches
    cause types to vary between string, list and ParseResults.
    '''
    if isinstance(parentClassList, list):
        return parentClassList
    elif isinstance(parentClassList, str):
        parentClassList = parentClassList.replace(" ", "")
        tmpList = parentClassList.split(",")
    elif isinstance(parentClassList, ParseResults):
        if parentClassList.get('fieldType', 0) and parentClassList['fieldType'].get('altModeList', 0):
            tmpList = parentClassList['fieldType']['altModeList'].asList()
            print("tmpList: ", tmpList)
        else:
            cdErr("Expected a ParseResults to be for the case where a mode is inherited")
    else:
        cdErr("Trying to convert unexpected type to list")
    return tmpList

def filterClassesToString(classes):
    '''Takes string, list or ParseResults and returns it as a string

    This is used in a specific situation where different parse branches
    cause types to vary between string, list and ParseResults.
    See specificity of filterClassesToList
    '''
    if isinstance(classes, ParseResults):
        classes = filterClassesToList(classes)
    if isinstance(classes, list):
        classes = str(classes)
    elif isinstance(classes, str):
        pass
    else:
        cdErr("Trying to convert unexpected type to string")
    return classes

def appendToAncestorList(objRef, className, subClassMode, parentClassList):
    global classImplementationOptions
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

        if subClassMode=='implements':
            if not (parentClass in classImplementationOptions):
                classImplementationOptions[parentClass] = [className]
            else: classImplementationOptions[parentClass].append(className)

def addObjTags(objSpecs, className, stateType, objTags):
    startTags = {}
    if stateType=='model': className='%'+className
    elif stateType=='string': className='$'+className
    objRef = objSpecs[className]
    if ('tags' in objRef):
        objRef['tags'].update(objTags)
    else:
        objRef['tags']=objTags
    if ('inherits' in objRef['tags']):
        parentClassList = objRef['tags']['inherits']
        inheritsMode = False
        try:
            if parentClassList['fieldType']['altModeIndicator']:
                inheritsMode = True
        except (KeyError, TypeError) as e:
            cdlog(6, "{}\n failed dict lookup in codeFlagAndModeFields".format(e))
        if not inheritsMode:
            appendToAncestorList(objRef, className, 'inherits', parentClassList)
            addDependencyToStruct(className, parentClassList)
    if ('implements' in objRef['tags']):
        appendToAncestorList(objRef, className, 'implements', objRef['tags']['implements'])
    for tag in objRef['tags']:
        if tag[:7]=='COMMAND':
            newCommand = objRef['tags'][tag]
            commandArg = tag[8:]
            addModifierCommand(objSpecs, className, commandArg, commandArg, newCommand)

def addTypeArgList(className, typeArgList):
    templatesDefined[className]=typeArgList

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

def packField(className, thisIsNext, thisOwner, thisType, thisArraySpec, thisReqTagList, thisName, thisArgList, paramList, thisValue, isAllocated, hasFuncBody):
    codeConverter=None
    packedField = {'isNext': thisIsNext, 'typeSpec':{'owner':thisOwner, 'fieldType':thisType, 'arraySpec':thisArraySpec, 'reqTagList':thisReqTagList, 'argList':thisArgList}, 'fieldName':thisName, 'paramList':paramList, 'value':thisValue, 'isAllocated':isAllocated}
    if(thisValue!=None and (not isinstance(thisValue, str)) and len(thisValue)>1 and thisValue[1]!=''):
        if thisValue[1][0]=='!':
            # This is where the definitions of code conversions are loaded. E.g., 'setRGBA' might get 'setColor(new Color(%1, %2, %3, %4))'
            codeConverter = thisValue[1][1:]
            packedField['typeSpec']['codeConverter']=codeConverter
        elif thisValue[1]!='':
            verbatimText=thisValue[1][1:]
            #packedField['typeSpec']['verbatimText']=verbatimText
    if hasFuncBody:
        packedField['hasFuncBody']=True
    else:
        packedField['hasFuncBody']=False
    fieldID = fieldIdentifierString(className, packedField)
    packedField['fieldID']=fieldID
    return packedField

def addDependencyToStruct(className, dependency):
    #print("############ addDependencyToStruct:", className, " --> ", dependency)
    global DependanciesMarked
    global DependanciesUnmarked
    fTypeKW = fieldTypeKeyword(dependency)
    reqTagList = getReqTagList(dependency)
    if reqTagList:
        owner = getOwner(dependency)
        addDependencyToStruct(className, fTypeKW)
        for reqTag in reqTagList:
            argTypeKW = reqTag['tArgType']
            argOwner  = reqTag['tArgOwner']
            if argOwner=='me' and not isBaseType(argTypeKW):
                addDependencyToStruct(className, argTypeKW)
    else:
        dependency = fieldTypeKeyword(dependency)
        if className == dependency: return
        if MarkItems: listToUpdate = DependanciesMarked
        else: listToUpdate = DependanciesUnmarked
        if dependency in listToUpdate and className in listToUpdate[dependency]:
            cdlog(1, "   NOTE: Possible circular dependency between "+className+" and "+dependency)
        if not(className in listToUpdate): listToUpdate[className]=[dependency]
        else:
            if not (dependency in listToUpdate[className]):
                listToUpdate[className].append(dependency)

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
    thisName  = packedField['fieldName']
    fieldID   = packedField['fieldID']
    tSpec     = getTypeSpec(packedField)
    fTypeKW   = fieldTypeKeyword(tSpec)

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

        # Don't override flags and modes in derived Classes
        if fTypeKW=='flag' or fTypeKW=='mode':
            if fieldIDAlreadyDeclaredInStruct(objSpecs, className, fieldID):
                cdlog(2, "Note: The field '" + fieldID + "' already exists. Not overriding")
                return

    objSpecs[taggedClassName]["fields"].append(packedField)
    objSpecs[taggedClassName]["vFields"]=None

    # if me or we and type is struct add unique dependency
    fieldOwner = getOwner(tSpec)
    if (fieldOwner=='me' or fieldOwner=='we' or fieldOwner=='const') and fieldsTypeCategory(tSpec)=='struct':
        addDependencyToStruct(className, tSpec)

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
def getTagSpec(classStore, className, tagName):
    if  className in classStore[1]:
        objRef = classStore[0][className]
        if 'tags' in objRef and tagName in objRef['tags']:
            return objRef['tags'][tagName]
    return None

def extractMapFromTagMap(tagmap):
    tagRetMap={}
    #tagmap = tagmap.asList()
    if ((not isinstance(tagmap, str)) and len(tagmap)>=2):
        tagmap = tagmap[1]
        for each in tagmap:
            #print("EACH:", each)
            tagRetMap[each[0]] = each[1][0]
    return tagRetMap

def extractListFromTagList(tagVal):
    tagValues=[]
    if ((not isinstance(tagVal, str)) and len(tagVal)>=2):
        if(tagVal[0]=='['):
            for each in tagVal.tagListContents:
                tagValues.append(each.tagValue[0])
    return tagValues

def searchATagStore(tagStore, tagToFind):
    #print("SEARCHING for tag", tagToFind, "     in tagStore: ", tagStore)
    if tagStore == None: return None
    tagSegs=tagToFind.split(r'.')
    crntStore=tagStore
    item=''
    for seg in tagSegs:
        #print("seg: ", seg, "      crntStore: ", crntStore)
        if seg in crntStore:
            item=crntStore[seg]
            crntStore=item
        else: return None
        #print seg, item
    #print item
    return [item]

def doesClassHaveProperty(classes, fType, propToFind):
    if isinstance(fType, str) or fType == None: return False
    className=fType[0]
    modelSpec = findSpecOf(classes[0], className, 'struct')
    if modelSpec == None: return False
    classProperties=searchATagStore(modelSpec["tags"], 'properties')
    if classProperties != None and classProperties[0] != None :
        if propToFind in classProperties[0]:
            return True
    return False

def fetchTagValue(tagStoreArray, tagToFind):
    """Searches tagStoreArray, a list of dictionaries, for tagToFind

    Pass in a list of tag stores to search, sorted with the lower priority lists first.

    For example, if you want to search for the tag "platform", first in the buildSpecs tags
    and if not found there, in the main tag store, call it like this:

       fetchTagValue([mainTags, buildSpecTags], "platform")

    If "platform" is defined in the buildSpecTags, that value will override any value for "platform" in the mainTags.

    The return value will be of the type and value of the given tag or None if there was no such tag.

    Because a tag's value can be a string, number, dict or list, the return value can be any of these.

    To search a specific tag store (instead of a prioritized list) use searchAtTagStore().
    """

    for tagStore in reversed(tagStoreArray):
        tagRet=searchATagStore(tagStore, tagToFind)
        if tagRet:
            #print("tagRet[0]. type: {}      value: {}".format(type(tagRet[0]), tagRet[0]))
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

dataStructureRequirements = []
def addDataStructureRequirements(requirementSpec):
    global dataStructureRequirements
    dataStructureRequirements.append(requirementSpec)

def addCodeToInit(tagStore, newInitCode):
    appendToStringTagValue(tagStore, "initCode", newInitCode);

def removeFieldFromObject (classes, className, fieldtoRemove):
    if not className in classes[0]:
        return
    fieldList=classes[0][className]['fields']
    idx=0
    for field in fieldList:
        if field["fieldID"] == fieldtoRemove:
            #print("Removed: ", field["fieldID"])
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
        tSpec    = getTypeSpec(F)
        baseType = TypeSpecsMinimumBaseType(classes, tSpec)
        G        = F.copy()
        if baseType!=None:
            G['typeSpec']=tSpec
            G['typeSpec']['fieldType'] = baseType
        insertOrReplaceField(fieldListToUpdate, G)

def updateCpy(fieldListToUpdate, fieldsToCopy):
    for field in fieldsToCopy:
        insertOrReplaceField(fieldListToUpdate, field)

def populateCallableStructFields(fieldList, classes, className):  # e.g. 'type::subType::subType2'
    #print("POPULATING-STRUCT:", className)
    # TODO: fix sometimes will populateCallableStructFields with sibling class fields
    structSpec=findSpecOf(classes[0], className, 'struct')
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

    modelSpec=findSpecOf(classes[0], className, 'model')
    if(modelSpec!=None): updateCvt(classes, fieldList, modelSpec["fields"])
    modelSpec=findSpecOf(classes[0], className, 'struct')
    updateCpy(fieldList, modelSpec["fields"])
    fieldListOut = copy.copy(fieldList)
    structSpec['vFields'] = fieldListOut

def generateListOfFieldsToImplement(classes, className):
    fieldList=[]
    modelSpec=findSpecOf(classes[0], className, 'model')
    if(modelSpec!=None):
        updateCvt(classes, fieldList, modelSpec["fields"])
    modelSpec=findSpecOf(classes[0], className, 'struct')
    if(modelSpec!=None):
        updateCpy(fieldList, modelSpec["fields"])
    return fieldList

def fieldOnlyID(fieldID):
    breakPos = fieldID.find('::')
    if breakPos<0: return fieldID
    return fieldID[breakPos+2:]

def fieldNameID(fieldID):
    colonIndex = fieldID.find('::')
    fieldID = fieldID[colonIndex+2:]
    parenIndex=fieldID.find('(')
    return fieldID[0:parenIndex]

def fieldDefIsInList(fieldList, fieldID):
    for field in fieldList:
        if 'fieldID' in field and fieldOnlyID(field['fieldID']) == fieldOnlyID(fieldID):
            if 'typeSpec' in field and field['typeSpec']!=None: tSpec=field['typeSpec']
            else: tSpec=None

            fieldIsAFunction = fieldIsFunction(tSpec)
            if not fieldIsAFunction: return True
            if fieldIsAFunction and 'value' in field and field['value']!=None:       # AND, the function is defined
                return field
    return False

def fieldIDAlreadyDeclaredInStruct(classes, className, fieldID):
    structSpec=findSpecOf(classes, className, 'struct')
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

    modelSpec=findSpecOf(classes, className, 'model')
    if(modelSpec!=None):
        if fieldDefIsInList(modelSpec["fields"], fieldID):
            return True

    if(structSpec!=None):
        if fieldDefIsInList(structSpec["fields"], fieldID):
            return True
    return False

def fieldNameInStructHierachy(classes, className, fName):
    #print('Searching for ', fName, ' in', className)
    structSpec=findSpecOf(classes, className, 'struct')
    if structSpec==None:
        return False;

    if structSpec['vFields']!=None:
        for field in structSpec['vFields']:
            if 'fieldID' in field:
                fieldID = field['fieldID']
                if fName in field['fieldID']:
                    return True

    classInherits = searchATagStore(structSpec['tags'], 'inherits')
    if classInherits!=None:
        for classParent in classInherits:
            if fieldNameInStructHierachy(classes, classParent, fName):
                return True

    classImplements = searchATagStore(structSpec['tags'], 'implements')
    if classImplements!=None:
        for classParent in classImplements:
            if fieldNameInStructHierachy(classes, classParent, fName):
                return True
    modelSpec=findSpecOf(classes, className, 'model')
    if(modelSpec!=None):
        if fieldDefIsInList(modelSpec["fields"], fName):
            return True

    if(structSpec!=None):
        if fieldDefIsInList(structSpec["fields"], fName):
            return True
    return False

#### These functions help evaluate parent-class / child-class relations

def doesChildImplementParentClass(classes, parentClassName, childClassName):
    parentClassDef = findSpecOf(classes, parentClassName, 'model')
    if(parentClassDef == None):parentClassDef = findSpecOf(classes, parentClassName, 'struct')
    if(parentClassDef == None):cdErr("Struct to implement not found:"+parentClassName)
    for field in parentClassDef['fields']:
        argList = getArgList(field)
        if(argList != None): # ArgList exists so this is a FUNCTION
            parentFieldID = field['fieldID']
            childFieldID = parentFieldID.replace(parentClassName+"::", childClassName+"::")
            fieldExists = doesClassDirectlyImlementThisField(classes, childClassName, childFieldID)
            if not fieldExists:
                return [False, parentFieldID]
    return [True, ""]

def doesClassDirectlyImlementThisField(objSpecs, className, fieldID):
    #print '        ['+className+']: ', fieldID
    modelSpec=findSpecOf(objSpecs, className, 'model')
    if(modelSpec!=None):
        fieldExists = fieldDefIsInList(modelSpec["fields"], fieldID)
        if fieldExists:
            return fieldExists
    structSpec=findSpecOf(objSpecs, className, 'struct')
    if(structSpec!=None):
        fieldExists = fieldDefIsInList(structSpec["fields"], fieldID)
        if fieldExists:
            return fieldExists
    return False

def doesClassFromListDirectlyImplementThisField(classes, structNameList, fieldID):
    if structNameList==None or len(structNameList)==0: return False
    for className in structNameList:
        if doesClassDirectlyImlementThisField(classes[0], className, fieldID):
            return True
    return False

def getParentClassList(classes, thisStructName):  # Checks 'inherits' but does not check 'implements'
    structSpec=findSpecOf(classes[0], thisStructName, 'struct')
    classInherits = searchATagStore(structSpec['tags'], 'inherits')
    if classInherits==None: classInherits=[]
    #print(thisStructName+':', classInherits)
    return classInherits

def getChildClassList(classes, thisStructName):  # Checks 'inherits' but does not check 'implements'
    global classHeirarchyInfo
    if thisStructName in classHeirarchyInfo:
        classRelationData = classHeirarchyInfo[thisStructName]
        if 'childClasses' in classRelationData and len(classRelationData['childClasses'])>0:
            listOfChildClasses = classRelationData['childClasses']
            grandChildren = set([])
            for className in listOfChildClasses:
                GchildList = getChildClassList(classes, className)
                grandChildren.update(GchildList)
            listOfChildClasses |= grandChildren
            return listOfChildClasses
    return []

def doesParentClassImplementFunc(classes, className, fieldID):
    #print '     Parents:\n',
    parentClasses=getParentClassList(classes, className)
    result = doesClassFromListDirectlyImplementThisField(classes, parentClasses, fieldID)
    #if len(parentClasses)>0: print '       P-Results:', result
    return result

def doesChildClassImplementFunc(classes, className, fieldID):
    childClasses=getChildClassList(classes, className)
    result = doesClassFromListDirectlyImplementThisField(classes, childClasses, fieldID)
    #if len(childClasses)>0: print '     Childs Result:', result
    return result

def doesClassContainFunc(classes, className, funcName):
    #TODO: make this take field ID instead of funcName
    callableStructFields=[]
    populateCallableStructFields(callableStructFields, classes, className)
    for field in callableStructFields:
        fieldName=field['fieldName']
        if fieldName == funcName: return field
    return False

templateSpecKeyWords = {'verySlow':0, 'slow':10, 'normal':20, 'fast':30, 'veryFast':40, 'polynomial':0, 'exponential':0, 'nLog_n':10, 'linear':20, 'logarithmic':30, 'constant':40, 'dontUse':0}
def scoreImplementation(optionSpecs, reqTags):
    returnScore = 0
    errorStr = ""
    if(reqTags != None):
        for reqTag in reqTags:
            reqID = reqTag[0]
            reqVal = templateSpecKeyWords[reqTag[1][0]]
            if(reqID in optionSpecs):
                specVal = templateSpecKeyWords[optionSpecs[reqID]]
                if(specVal < reqVal):return([-1, errorStr])
                if(specVal > reqVal):returnScore = specVal - reqVal
            else:
                errorStr = "Requirement '"+reqID+"' not found in Spec:"+str(optionSpecs)
                return([-1, errorStr])
        return [returnScore, errorStr]
    else:
        for specKey,specValue in optionSpecs.items():
            specScore = templateSpecKeyWords[specValue]
            returnScore += specScore
        return([returnScore, errorStr])

def getImplementationOptionsFor(fType):
    global classImplementationOptions
    if fType in classImplementationOptions:
        return classImplementationOptions[fType]
    return None
###############  Various Dynamic Type-handling functions
def convertItrType(classStore, owner, fTypeKW):
    # TODO: have this look for iterator sub class
    if owner=='itr':
        classDef  =  findSpecOf(classStore[0], fTypeKW, "struct")
        for field in classDef['fields']:
            KW = fieldTypeKeyword(field)
            if KW=='struct' or KW=='model':
                fieldName = field['fieldName']
                if fieldName[:8]=='iterator':
                    return fieldName
    return None

def getGenericArgs(ObjectDef):
    if('genericArgs' in ObjectDef): return(ObjectDef['genericArgs'])
    else: return(None)

def getGenericArgsFromTypeSpec(tSpec):
    genericArgs = {}
    reqTagList = getReqTagList(tSpec)
    if reqTagList:
        implTArgs = getImplementationTypeArgs(tSpec)
        if implTArgs:
            count = 0
            for reqTag in reqTagList:
                genericArgs[implTArgs[count]]=reqTag
                count += 1
        return genericArgs
    return None

def getTypeArgList(className):
    if not isinstance(className, str): print("ERROR: in progSpec.getTypeArgList(): expected a string not: "+ str(className))
    if(className in templatesDefined): return(templatesDefined[className])
    else: return(None)

def getReqTagList(tSpec):
    if('fieldType' in tSpec and 'reqTagList' in tSpec['fieldType']):
        tSpec = tSpec['fieldType']
    if('reqTagList' in tSpec):
        return(tSpec['reqTagList'])
    return(None)

def getReqTags(fType):
    if('optionalTag' in fType[1]): return(fType[1][3])
    else: return None

def isOldContainerTempFuncErr(tSpec, msg):
    if'arraySpec' in tSpec and tSpec['arraySpec']!=None:
        cdErr("Deprecated container type in " + msg)

def isNewContainerTempFunc(tSpec):
    # use only while transitioning to dynamic lists<> then delete
    # TODO: delete this function when dynamic types working

    if not 'fieldType' in tSpec: return(False)
    fType = tSpec['fieldType']
    if isinstance(fType, str): return(False)
    fieldTypeKW = fType[0]
    if fieldTypeKW=='PovList': return(True)
    reqTagList = getReqTagList(tSpec)
    if reqTagList: return(True)
    elif reqTagList == None: return(False)
    return(False)

def isAContainer(tSpec):
    if tSpec==None:return(False)
    if isNewContainerTempFunc(tSpec): return True  # TODO: Remove this after Dynamix Types work.
    # TODO: remove check for Old Container
    # needed for stringStructs
    return('arraySpec' in tSpec and tSpec['arraySpec']!=None)

def getContainerSpec(tSpec):
    if isNewContainerTempFunc(tSpec):
        if 'fieldType' in tSpec: fType = tSpec['fieldType']
        else: fType = None
        containerType=fType[0]
        return {'owner': tSpec['owner'], 'datastructID':containerType}
    # TODO: remove check for Old Container. Needed for stringStructs
    return(tSpec['arraySpec'])

def getDatastructID(tSpec):
    if isNewContainerTempFunc(tSpec):
        # if fType is parseResult w/ fType whose value is 'PovList'
        return 'list'
    # TODO: remove check for Old Container. Needed for stringStructs
    if(isinstance(tSpec['arraySpec']['datastructID'], str)):
        return(tSpec['arraySpec']['datastructID'])
    else:   #is a parseResult
        return(tSpec['arraySpec']['datastructID'][0])

def getContaineCategory(ctnrTSpec):
    fromImpl = getFromImpl(ctnrTSpec)
    if fromImpl: return fromImpl
    fTypeKW = fieldTypeKeyword(ctnrTSpec)
    if fTypeKW=='string':     return 'string'
    cdErr("Unknown type in progSpec.getContaineCategory() "+fTypeKW)

def getContainerType_Owner(tSpec):
    isOldContainerTempFuncErr(tSpec,"progSpec.getContainerType_Owner()")
    owner = getOwner(tSpec)
    if isNewContainerTempFunc(tSpec): datastructID = fieldTypeKeyword(tSpec)
    else: datastructID = 'None'
    return [datastructID, owner]

def isContainerTemplateTempFunc(tSpec):
    fTypeKW  = fieldTypeKeyword(tSpec)
    if fTypeKW=='CPP_Deque' or fTypeKW=='Java_ArrayList' or fTypeKW=='Swift_Array':
        return True
    if fTypeKW=='CPP_Map' or fTypeKW=='Java_Map' or fTypeKW=='Swift_Map':
        return True
    if fTypeKW=='Java_MultiMap':
        return True
    if not "RBNode" in fTypeKW and not "RBTree" in fTypeKW and not "List" in fTypeKW and fTypeKW!="Map" and not "Multimap" in fTypeKW:
        print("Template class '"+fTypeKW+"' not found")
    return False

def getNewContainerFirstElementTypeTempFunc2(tSpec):
    # use only while transitioning to dynamic lists<> then delete
    # TODO: delete this function when dynamic types working
    if tSpec == None: return(None)
    if not 'fieldType' in tSpec: return(None)
    fType = tSpec['fieldType']
    if isinstance(fType, str): return(None)
    fTypeKW = fType[0]
    if fTypeKW=='PovList': return(['infon'])
    reqTagList = getReqTagList(tSpec)
    if reqTagList:
        if isContainerTemplateTempFunc(tSpec) or fTypeKW=='List': return(reqTagList[0]['tArgType'])
    elif reqTagList == None: return(None)
    return(None)

def getNewContainerFirstElementTypeTempFunc(tSpec):
    # use only while transitioning to dynamic lists<> then delete
    # TODO: delete this function when dynamic types working
    if tSpec == None: return(None)
    if not 'fieldType' in tSpec: return(None)
    fType = tSpec['fieldType']
    if isinstance(fType, str): return(None)
    fTypeKW = fType[0]
    if fTypeKW=='PovList': return(['infon'])
    reqTagList = getReqTagList(tSpec)
    if reqTagList:
        if isContainerTemplateTempFunc(tSpec): return(reqTagList[0]['tArgType'])
    elif reqTagList == None: return(None)
    return(None)

def getNewContainerFirstElementOwnerTempFunc(tSpec):
    # TODO: delete this function when dynamic types working. Needed for stringStructs
    if tSpec == None: return(None)
    if not 'fieldType' in tSpec: return(None)
    fType = tSpec['fieldType']
    if isinstance(fType, str): return(None)
    fTypeKW = fType[0]
    if fTypeKW=='PovList': return('our')
    reqTagList = getReqTagList(tSpec)
    if reqTagList:
        if isContainerTemplateTempFunc(tSpec) or fTypeKW=='List': return(reqTagList[0]['tArgOwner'])
    elif reqTagList == None: return(None)
    return(None)

def getFromImpl(tSpec):
    if 'fromImplemented' in tSpec: return tSpec['fromImplemented']
    return None

def getImplementationTypeArgs(tSpec):
    if 'implTypeArgs' in tSpec: return tSpec['implTypeArgs']
    return None

def fieldTypeKeyword(fType):
    # fType can be fType or typeSpec
    if fType==None:                         return None
    if 'dummyType' in fType:                return None
    if 'typeSpec' in fType:                 fType = fType['typeSpec']   # if var fType is fieldDef
    if 'fieldType' in fType:                fType = fType['fieldType']  # if var fType is typeSpec
    if 'owner' in fType and fType['owner']=='PTR': return None
    if isinstance(fType, str):              return fType
    if len(fType)>1 and fType[1]=='..': return 'int'
    if('varType' in fType[0]):              fType = fType[0]['varType']
    if isinstance(fType[0], str):           return fType[0]
    if isinstance(fType[0][0], str):        return fType[0][0]
    cdErr("?Invalid fieldTypeKeyword?")

def getFieldType(tSpec):
    retVal = getNewContainerFirstElementTypeTempFunc(tSpec)
    if retVal != None: return retVal
    if 'fieldType' in tSpec: return(tSpec['fieldType'])
    return None

def getContainerFirstElementType(tSpec):
    reqTagList=getReqTagList(tSpec)
    if reqTagList:
        return(reqTagList[0]['tArgType'])
    return None

def getContainerFirstElementOwner(tSpec):
    global currentCheckObjectVars
    if (tSpec == 0):
        cdErr(currentCheckObjectVars)
    if isAContainer(tSpec):
        if isNewContainerTempFunc(tSpec):
            if(tSpec['fieldType'][0] == 'PovList'): return('our')
            else: return (getOwnerFromTemplateArg(tSpec['reqTagList'][0]))
        else: return(getOwner(tSpec))
    else:
        # TODO: This should throw error, no lists should reach this point.
        return(getOwner(tSpec))

def getOwner(tSpec):
    global currentCheckObjectVars
    if (tSpec == 0): cdErr(currentCheckObjectVars)
    if tSpec==None or isinstance(tSpec, str): return 'me'
    if 'typeSpec' in tSpec: tSpec = tSpec['typeSpec']
    return tSpec['owner']

def getArgList(tSpec):
    if tSpec==None: return None
    if 'typeSpec' in tSpec: tSpec = tSpec['typeSpec']
    if 'argList' in tSpec: return tSpec['argList']
    return None

def getCodeConverterByFieldID(classes, className, fieldName, prevNameSeg, connector):
    structSpec=findSpecOf(classes[0], className, 'struct')
    fieldID = className+ "::" +fieldName
    if structSpec==None: return None
    for field in structSpec["fields"]:
        if field['fieldID']==fieldID:
            if 'typeSpec' in field and field['typeSpec']!=None and 'codeConverter' in field['typeSpec']:
                codeConverter = field['typeSpec']['codeConverter']
                codeConverter = codeConverter.replace("%G", '')
                codeConverter = codeConverter.replace("%0", prevNameSeg)
                return codeConverter
            return prevNameSeg+connector+fieldName+"()"
    return prevNameSeg+connector+fieldName+"()"

def getTypeSpec(fieldDef):
    if 'typeSpec' in fieldDef: return fieldDef['typeSpec']
    cdErr("TypeSpec not found in progSpec.getTypeSpec()")

#### Packed Template Arg Handling Functions ####
def getOwnerFromTemplateArg(tArg):
    global currentCheckObjectVars
    if (tArg == 0): cdErr(currentCheckObjectVars)
    return tArg['tArgOwner']

def getTypeFromTemplateArg(tArg):
    global currentCheckObjectVars
    if (tArg == 0): cdErr(currentCheckObjectVars)
    return tArg['tArgType']

################################################

def setCurrentCheckObjectVars(message):
    global currentCheckObjectVars
    currentCheckObjectVars = message

def ownerIsPointer(owner):
    if owner == 'their' or owner == 'our' or owner == 'my' or owner == 'itr' or owner == 'id_their' or owner == 'id_our': isPointer=True
    else: isPointer=False
    return isPointer

def typeIsPointer(tSpec):
    if isinstance(tSpec,str): owner = tSpec   # tSpec is really Owner field
    else: owner=getOwner(tSpec)   # tSpec is full typeSpec
    return ownerIsPointer(owner)

def fieldIsFunction(tSpec):
    if tSpec==None: return False
    if getArgList(tSpec)!=None: return True
    return False

def doesFieldDefHaveValue(fieldDef):
    if len(fieldDef['value'][0]) == 0 and len(fieldDef['value'][1]) == 0:
        return 0
    else:
        return 1

def isWrappedType(objMap, structname):
    # If type is not wrapped, return None, else return the wrapped typeSpec
    if not structname in objMap[0]:
        return None; # TODO: "Print Struct "+structname+" not found" But not if type is base type.
    structToSearch=findSpecOf(objMap[0], structname, 'struct')
    ownerMe = False
    if('tags' in structToSearch and 'wraps' in structToSearch['tags']):
        if('tags' in structToSearch and 'ownerMe' in structToSearch['tags']):
            ownerMe = True
            retOwner = structToSearch['tags']['ownerMe']
        else: retOwner = 'me'
        wrappedStructName = structToSearch['tags']['wraps']
        typeSpecRetVal = {'owner':retOwner, 'fieldType':[wrappedStructName], 'arraySpec':None, 'argList':None}
        if ownerMe: typeSpecRetVal['ownerMe'] = retOwner
        #print(typeSpecRetVal)
        return(typeSpecRetVal)

    # Try old method of wrapping.
    # TODO: Deprecate this soon.
    fieldListToSearch = structToSearch["fields"]
    if not fieldListToSearch:
        return None
    if len(fieldListToSearch)>0:
        for field in fieldListToSearch:
            if field['fieldName']==structname and getArgList(field)==None:
                return getTypeSpec(field)
    return None

def wrappedTypeIsPointer(classes, tSpec, className):
    # like typeIsPointer() but also checks wrapped type
    result = typeIsPointer(tSpec)
    if result==True: return True

    baseType = isWrappedType(classes, className)
    if(baseType==None): return result
# TODO: FIX
    exit(2)
    return typeIsPointer(baseType)

def createTypedefName(ItmType):
    if(isinstance(ItmType, str)): return ItmType
    else:
        return 'BAD-TYPE-NAME'
        baseType=createTypedefName(ItmType[1])
        suffix=''
        typeHead=ItmType[0]
        if(typeHead=='their'): suffix='RPtr'
        elif(typeHead=='our'): suffix='SPtr'
        elif(typeHead=='my'): suffix='UPtr'
        return baseType+suffix

def findSpecOf(objMap, className, stateTypeWanted):
    if stateTypeWanted=='model': className='%'+className
    elif stateTypeWanted=='string': className='$'+className
    if not className in objMap: return None
    return objMap[className]

def getUnwrappedClassFieldTypeKeyWord(classes, className):
    baseType = isWrappedType(classes, className)
    if(baseType!=None): return fieldTypeKeyword(baseType)
    else: return className

def baseStructName(className):
    colonIndex=className.find('::')
    if(colonIndex==-1): return className
    return className[0:colonIndex]

def queryTagFunction(classes, className, funcName, matchName, tSpecIn):
    funcField = doesClassContainFunc(classes, className, funcName)
    if(funcField):
        funcFieldKW = fieldTypeKeyword(funcField)
        if(funcFieldKW == matchName):
            typeArgList = getTypeArgList(className)
            reqTagList  = getReqTagList(tSpecIn)
            count = 0
            for item in typeArgList:
                if(item == matchName):
                    innerTypeOwner   = getOwnerFromTemplateArg(reqTagList[count])
                    innerTypeKeyWord = getTypeFromTemplateArg(reqTagList[count])
                    return([innerTypeOwner, innerTypeKeyWord])
                count += 1
    return([None, None])

def isStruct(fType):
    if isinstance(fType, str): return False
    return True

def isBaseType(fType):
    KW = fieldTypeKeyword(fType)
    if KW=='string' or KW[0:4]=='uint' or KW[0:3]=='int' or KW[0:6]=='double' or KW[0:4]=='char' or KW[0:4]=='bool' or KW[0:4]=='flag':
        return True
    return False

def isAltStruct(classes, fType):
    if not isStruct(fType) or not(fType[0] in classes[0]): return [False, [] ]
    fieldObj=classes[0][fType[0]]
    fieldObjConfig=fieldObj['configType']
    Objfields=fieldObj['fields']
    if (fieldObjConfig=='ALT'): return [True, Objfields]
    else: return [False, [] ]

def isAbstractStruct(classes, className):
    modelDef = findSpecOf(classes, className, 'model')
    if modelDef:
        classDef = findSpecOf(classes, className, 'struct')
        if classDef == None: return True
    return False

def typeIsNumRange(fType):
    if isinstance(fType, str): return False
    if len(fType)==3:
        if fType[1]=='..':
            return True
    return False

def typeIsInteger(fType):
    # NOTE: If you need this to work for wrapped types as well use the version in CodeGenerator.py
    if fType == None: return False
    if typeIsNumRange(fType): return True
    if not isinstance(fType, str):
        fType= fType[0]
    if fType=="int" or fType=="BigInt" or fType=="uint" or fType=="uint64" or fType=="uint32"or fType=="int64" or fType=="int32" or fType=="FlexNum":
        return True
    return False

def isStringHexNum(S):
    if len(S) < 3: return False
    if not (S[:2]=='0x' or S[:2]=='0X'): return False
    hexNums = set("0123456789abcdefABCDEF")
    for char in S[2:]:
        if not (char in hexNums):return False
    return True

def isStringBinNum(S):
    if len(S) < 3: return False
    if not (S[:2]=='0b' or S[:2]=='0B'): return False
    for char in S[2:]:
        if not char.isdigit():return False
    return True

def isStringNumeric(S):
    if isStringHexNum(S): return True
    if isStringBinNum(S): return True
    countDots = 0
    for char in S:
        if char == '.':
            countDots += 1
            if countDots >1: return False
        elif not char.isdigit():return False
    return True

def fetchFieldByName(fields, fieldName):
    for field in fields:
        fname=field['fieldName']
        if fname==fieldName: return field
    return None

def TypeSpecsMinimumBaseType(classes, tSpec):
    owner     = getOwner(tSpec)
    fType = tSpec['fieldType']
    if typeIsNumRange(fType):
        minVal = int(fType[0])
        maxVal = int(fType[2])
        if minVal>=0:
            if (maxVal<=256):    return "uint8"
            if maxVal<=65536:    return "uint16"
            if maxVal<=(2**32):  return "uint32"
            if maxVal<=(2**64):  return "uint64"
            if maxVal<=(2**128): return "uint128"
            else:  return "flexInt"
        else: # Handle signed values (int)
            return "int64"
    elif isStruct(fType) and (fType[0] in classes[0]):
        fieldObj=classes[0][fType[0]]
        fieldObjConfig=fieldObj['configType']
        if(fieldObjConfig=='ALT'):
            innerTypeSpec = getTypeSpec(fieldObj['fields'][0])
            retType       = TypeSpecsMinimumBaseType(classes, innerTypeSpec)
            return retType
    return fType

def innerTypeCategory(fType):
    fTypeKW = fieldTypeKeyword(fType)
    if fTypeKW=='flag' or fTypeKW=='mode' or fTypeKW=='timeValue' or fTypeKW=='void' or fTypeKW=='char' or fTypeKW=='double' or fTypeKW=='float' or fTypeKW=='string' or fTypeKW=='bool':
        return fTypeKW
    if isStruct(fType): return 'struct'
    if typeIsInteger(fType): return 'int'
    return 'ERROR'

def varsTypeCategory(tSpec):
    fType = ''
    if isinstance(tSpec, str): fType=tSpec
    else: fType = getFieldType(tSpec)
    return innerTypeCategory(fType)

def fieldsTypeCategory(tSpec):
    if getArgList(tSpec)!=None: return 'func'
    return varsTypeCategory(tSpec)

def varTypeKeyWord(tSpec):
    if tSpec == None: varType=None
    elif isinstance(tSpec, str): varType=tSpec
    elif tSpec==None or tSpec==0: varType='ERROR'
    elif tSpec['owner']=='PTR': varType='PTR'
    else:
        varType = varsTypeCategory(tSpec)
        if varType =='int':
            varType = fieldTypeKeyword(tSpec)
    return varType

def typeSpecsAreCompatible(tSpec1, tSpec2):
    if getOwner(tSpec1) != getOwner(tSpec2): return False
    if fieldTypeKeyword(tSpec1) != fieldTypeKeyword(tSpec2): return False
    leftContainerNull  = not(isNewContainerTempFunc(tSpec1))
    rightContainerNull = not(isNewContainerTempFunc(tSpec2))
    if not leftContainerNull and rightContainerNull: return False
    if leftContainerNull and not rightContainerNull: return False
    if not leftContainerNull and not rightContainerNull and getContainerSpec(tSpec1) != getContainerSpec(tSpec2): return False
    return True

def flattenObjectName(objName):
    return objName.replace('::', '_')

def stringFromFile(filename):
#    try:
        f=open(filename)
        Str = f.read()
        f.close()
#    except IOError as e:
#        cdErr("I/O error({0}): {1}: {2}".format(e.errno, e.strerror, filename))
        return Str

#############################################################  Logging functions
lastLogMesgs=['','','','','','','','','','']
highestLvl=0;
noError=False

def logLvl():
    return highestLvl+1

def dePythonStr(pyItem):
    S=""
    count=0
    for segSpec in pyItem:
        if count>0: S+="."
        S+=str(segSpec)
        count += 1
    print(str(pyItem))
    S=S.replace('[','')
    S=S.replace(']','')
    S=S.replace("'",'')
    S=S.replace(' ','')
    parenPos = S.find('(')
    if(parenPos>=0):
        itemName = S[:parenPos]
        itemName = itemName.replace(',','.')
        paramList = S[parenPos+1:]
        if len(paramList)>1 and paramList[0]==",": paramList = paramList[1:]
       # paramList = paramList.replace(', ', '!')
       # paramList = paramList.replace(',', '')
        paramList = paramList.replace(',', ', ')
        S = itemName[:-1] + '('+paramList+')'
    else:
        S=S.replace(',','.')
        S=S.replace('(','')
        S=S.replace(')','')
    return S

def printAtLvl(lvl, mesg, indent):
    for i in range(0, lvl): sys.stdout.write(indent)
    print(mesg)

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
    lastLogMesgs[highestLvl]="\n\nError: "+mesg
    exit(1)

def whenExit():
    endTime = timer()
    print("\nTIME: {0:.2f} seconds".format(endTime-startTime))
    global lastLogMesgs
    global highestLvl
    global noError
    if(noError): return;
    print("\n\nAn error occured while:", end=' ')
    for i in range(0, highestLvl+1):
        printAtLvl(i, lastLogMesgs[i], '    ')
    print("\n")

def saveTextToErrFile(textToSave):
    text_file = open("ErrFile.dog", "w")
    text_file.write(textToSave)
    text_file.close()
