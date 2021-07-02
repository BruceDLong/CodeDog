
# ProgSpec manipulation routines

import sys
import re
import copy
from pyparsing import ParseResults

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

def getTypesBase(typeSpec):
    if isinstance(typeSpec, str):
       return typeSpec
    else: return getTypesBase(typeSpec[1])

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
    if 'typeSpec' in packedField: typeSpec=packedField['typeSpec']
    if 'argList' in typeSpec and typeSpec['argList'] :
        argList = typeSpec['argList']
        fieldID+='('
        count=0
        for arg in argList:
            if count>0: fieldID+=','
            argKeyWord = fieldTypeKeyword(arg['typeSpec'])
            fieldID += argKeyWord
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
            addDependancyToStruct(className, parentClassList)
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

def addDependancyToStruct(structName, nameOfDependancy):
    #print("############ addDependancyToStruct:", structName, " --> ", nameOfDependancy)
    global DependanciesMarked
    global DependanciesUnmarked
    if structName == nameOfDependancy: return
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

def doesClassHaveProperty(classes, fieldType, propToFind):
    if isinstance(fieldType, str) or fieldType == None: return False
    structName=fieldType[0]
    modelSpec = findSpecOf(classes[0], structName, 'struct')
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
        typeSpec=F['typeSpec']
        baseType=TypeSpecsMinimumBaseType(classes, typeSpec)
        G = F.copy()
        if baseType!=None:
            G['typeSpec']=typeSpec.copy()
            G['typeSpec']['fieldType'] = baseType
        insertOrReplaceField(fieldListToUpdate, G)

def updateCpy(fieldListToUpdate, fieldsToCopy):
    for field in fieldsToCopy:
        insertOrReplaceField(fieldListToUpdate, field)

def populateCallableStructFields(fieldList, classes, structName):  # e.g. 'type::subType::subType2'
    #print("POPULATING-STRUCT:", structName)
    # TODO: fix sometimes will populateCallableStructFields with sibling class fields
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
    fieldListOut = copy.copy(fieldList)
    structSpec['vFields'] = fieldListOut

def generateListOfFieldsToImplement(classes, structName):
    fieldList=[]
    modelSpec=findSpecOf(classes[0], structName, 'model')
    if(modelSpec!=None):
        updateCvt(classes, fieldList, modelSpec["fields"])
    modelSpec=findSpecOf(classes[0], structName, 'struct')
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

def fieldNameInStructHierachy(classes, structName, fName):
    #print('Searching for ', fName, ' in', structName)
    structSpec=findSpecOf(classes, structName, 'struct')
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
    modelSpec=findSpecOf(classes, structName, 'model')
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
        if(field['typeSpec'] and field['typeSpec']['argList'] and field['typeSpec']['argList'] != None): # ArgList exists so this is a FUNCTION
            parentFieldID = field['fieldID']
            childFieldID = parentFieldID.replace(parentClassName+"::", childClassName+"::")
            fieldExists = doesClassDirectlyImlementThisField(classes, childClassName, childFieldID)
            if not fieldExists:
                return [False, parentFieldID]
    return [True, ""]

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

def doesParentClassImplementFunc(classes, structName, fieldID):
    #print '     Parents:\n',
    parentClasses=getParentClassList(classes, structName)
    result = doesClassFromListDirectlyImplementThisField(classes, parentClasses, fieldID)
    #if len(parentClasses)>0: print '       P-Results:', result
    return result

def doesChildClassImplementFunc(classes, structName, fieldID):
    childClasses=getChildClassList(classes, structName)
    result = doesClassFromListDirectlyImplementThisField(classes, childClasses, fieldID)
    #if len(childClasses)>0: print '     Childs Result:', result
    return result

def doesClassContainFunc(classes, structName, funcName):
    #TODO: make this take field ID instead of funcName
    callableStructFields=[]
    populateCallableStructFields(callableStructFields, classes, structName)
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

def getImplementationOptionsFor(fieldType):
    global classImplementationOptions
    if fieldType in classImplementationOptions:
        return classImplementationOptions[fieldType]
    return None
###############  Various Dynamic Type-handling functions
def getGenericArgs(ObjectDef):
    if('genericArgs' in ObjectDef): return(ObjectDef['genericArgs'])
    else: return(None)

def getTypeArgList(className):
    if not isinstance(className, str):
        print("ERROR: in progSpec.getTypeArgList(): expected a string not: "+ str(className))
    if(className in templatesDefined):
        return(templatesDefined[className])
    else:
        return(None)

def getReqTagList(typeSpec):
    if('reqTagList' in typeSpec):
        return(typeSpec['reqTagList'])
    if('fieldType' in typeSpec and 'reqTagList' in typeSpec['fieldType']):
        return(typeSpec['fieldType']['reqTagList'])
    return(None)

def getReqTags(fieldType):
    if('optionalTag' in fieldType[1]):
        reqTags = fieldType[1][3]
        return(reqTags)
    else:
        return None

def isNewContainerTempFunc(typeSpec):
    # use only while transitioning to dynamic lists<> then delete
    # TODO: delete this function when dynamic types working
    if not 'fieldType' in typeSpec: return(False)
    fieldType = typeSpec['fieldType']
    if isinstance(fieldType, str): return(False)
    fieldTypeKW = fieldType[0]
    if fieldTypeKW=='DblLinkedList': return(True)
    reqTagList = getReqTagList(typeSpec)
    if reqTagList: return(True)
    elif reqTagList == None: return(False)
    return(False)

def isOldContainerTempFunc(typeSpec):
    return('arraySpec' in typeSpec and typeSpec['arraySpec']!=None)

def isAContainer(typeSpec):
    if typeSpec==None:return(False)
    if isNewContainerTempFunc(typeSpec): return True  # TODO: Remove this after Dynamix Types work.
    return(isOldContainerTempFunc(typeSpec))

def getContainerSpec(typeSpec):
    if isNewContainerTempFunc(typeSpec):
        fieldType=getFieldTypeNew(typeSpec)
        containerType=fieldType[0]
        return {'owner': typeSpec['owner'], 'datastructID':containerType}
    return(typeSpec['arraySpec'])

def getTemplateArg(typeSpec, argIdx):
    return(typeSpec)

def getDatastructID(typeSpec):
    if isNewContainerTempFunc(typeSpec):
        # if fieldType is parseResult w/ fieldType whose value is 'DblLinkedList'
        return 'list'
    if(isinstance(typeSpec['arraySpec']['datastructID'], str)):
        return(typeSpec['arraySpec']['datastructID'])
    else:   #is a parseResult
        return(typeSpec['arraySpec']['datastructID'][0])

def isContainerTemplateTempFunc(typeSpec):
    fTypeKW = fieldTypeKeyword(typeSpec)
    if fTypeKW=='CPP_Deque' or fTypeKW=='Java_ArrayList' or fTypeKW=='Swift_Array':
        return True
    if fTypeKW=='CPP_Map' or fTypeKW=='Java_Map' or fTypeKW=='Swift_Map':
        return True
    if fTypeKW=='Java_MultiMap':
        return True
    if not "RBNode" in fTypeKW and not "RBTree" in fTypeKW and not "CDList" in fTypeKW and fTypeKW!="Map" and not "Multimap" in fTypeKW:
        print("Template class '"+fTypeKW+"' not found")
    return False

def getNewContainerFirstElementTypeTempFunc2(typeSpec):
    # use only while transitioning to dynamic lists<> then delete
    # TODO: delete this function when dynamic types working
    if typeSpec == None: return(None)
    if not 'fieldType' in typeSpec: return(None)
    fieldType = typeSpec['fieldType']
    if isinstance(fieldType, str): return(None)
    fTypeKW = fieldType[0]
    if fTypeKW=='DblLinkedList': return(['infon'])
    reqTagList = getReqTagList(typeSpec)
    if reqTagList:
        if isContainerTemplateTempFunc(typeSpec) or fTypeKW=='List': return(reqTagList[0]['tArgType'])
    elif reqTagList == None: return(None)
    return(None)

def getNewContainerFirstElementTypeTempFunc(typeSpec):
    # use only while transitioning to dynamic lists<> then delete
    # TODO: delete this function when dynamic types working
    if typeSpec == None: return(None)
    if not 'fieldType' in typeSpec: return(None)
    fieldType = typeSpec['fieldType']
    if isinstance(fieldType, str): return(None)
    fTypeKW = fieldType[0]
    if fTypeKW=='DblLinkedList': return(['infon'])
    reqTagList = getReqTagList(typeSpec)
    if reqTagList:
        if isContainerTemplateTempFunc(typeSpec): return(reqTagList[0]['tArgType'])
    elif reqTagList == None: return(None)
    return(None)

def getNewContainerFirstElementOwnerTempFunc(typeSpec):
    # use only while transitioning to dynamic lists<> then delete
    # TODO: delete this function when dynamic types working
    if typeSpec == None: return(None)
    if not 'fieldType' in typeSpec: return(None)
    fieldType = typeSpec['fieldType']
    if isinstance(fieldType, str): return(None)
    fTypeKW = fieldType[0]
    if fTypeKW=='DblLinkedList': return('our')
    reqTagList = getReqTagList(typeSpec)
    if reqTagList:
        if isContainerTemplateTempFunc(typeSpec) or fTypeKW=='List': return(reqTagList[0]['tArgOwner'])
    elif reqTagList == None: return(None)
    return(None)

def getContainerKeyOwnerAndType(typeSpec):
    owner     = getContainerFirstElementOwner(typeSpec)
    fieldType = fieldTypeKeyword(typeSpec)
    if not isNewContainerTempFunc(typeSpec): return[owner, fieldType]
    reqTagList = getReqTagList(typeSpec)
    if "fromImplemented" in typeSpec:
        fromImplemented = typeSpec['fromImplemented']
        if 'typeArgList' in fromImplemented:
            typeArgList = fromImplemented['typeArgList']
        if 'atKeyTypeSpec' in fromImplemented:
            fieldDefAt = fromImplemented['atKeyTypeSpec']
        if typeArgList and fieldDefAt:
            atOwner  = fieldDefAt['owner']
            atTypeKW = fieldTypeKeyword(fieldDefAt)
            if atTypeKW in typeArgList:
                idxAt = typeArgList.index(atTypeKW)
                valType = reqTagList[idxAt]
                return[valType['tArgOwner'], valType['tArgType']]
            else: return[atOwner, atTypeKW]
    return[owner, fieldType]

def getContainerValueOwnerAndType(typeSpec):
    owner     = getContainerFirstElementOwner(typeSpec)
    fieldType = fieldTypeKeyword(typeSpec)
    if not isNewContainerTempFunc(typeSpec): return[owner, fieldType]
    reqTagList = getReqTagList(typeSpec)
    if "fromImplemented" in typeSpec:
        fromImplemented = typeSpec['fromImplemented']
        if 'typeArgList' in fromImplemented:
            typeArgList = fromImplemented['typeArgList']
        if 'atTypeSpec' in fromImplemented:
            fieldDefAt = fromImplemented['atTypeSpec']
        if typeArgList and fieldDefAt:
            atOwner  = fieldDefAt['owner']
            atTypeKW = fieldTypeKeyword(fieldDefAt)
            if atTypeKW in typeArgList:
                idxAt = typeArgList.index(atTypeKW)
                valType = reqTagList[idxAt]
                return[valType['tArgOwner'], valType['tArgType']]
            else: return[atOwner, atTypeKW]
    if reqTagList:
        owner     = reqTagList[0]['tArgOwner']
        fieldType = reqTagList[0]['tArgType']
    return[owner, fieldType]

def getFieldType(typeSpec):
    retVal = getNewContainerFirstElementTypeTempFunc(typeSpec)
    if retVal != None:
        return retVal
    if 'fieldType' in typeSpec: return(typeSpec['fieldType'])
    return None

def getFieldTypeKeyWordOld(typeSpec):
    # TODO: delete this function when dynamic types working
    if(typeSpec==None):return None
    fieldType = getFieldType(typeSpec)
    if isinstance(fieldType, str): return fieldType
    if isinstance(fieldType[0], str): return fieldType[0]
    print("TODO: reduce field type to key word in progSpec.getFieldTypeKeyWord():",fieldType)
    exit(2)

def getContainerFirstElementType(typeSpec):
    reqTagList=getReqTagList(typeSpec)
    if reqTagList:
        return(reqTagList[0]['tArgType'])
    return None

def getFieldTypeNew(typeSpec):
    if 'fieldType' in typeSpec: return(typeSpec['fieldType'])
    return None

def getContainerFirstElementOwner(typeSpec):
    global currentCheckObjectVars
    if (typeSpec == 0):
        cdErr(currentCheckObjectVars)
    if isAContainer(typeSpec):
        if isNewContainerTempFunc(typeSpec):
            if(typeSpec['fieldType'][0] == 'DblLinkedList'): return('our')
            else: return (getOwnerFromTemplateArg(typeSpec['reqTagList'][0]))
        else: return(typeSpec['owner'])
    else:
        # TODO: This should throw error, no lists should reach this point.
        return(typeSpec['owner'])

def getTypeSpecOwner(typeSpec):
    # this is old way to get the owner, delete when transition complete
    global currentCheckObjectVars
    if (typeSpec == 0):
        cdErr(currentCheckObjectVars)
    if typeSpec==None or isinstance(typeSpec, str): return 'me'
    if isAContainer(typeSpec):
        if isNewContainerTempFunc(typeSpec): return typeSpec['owner']
        if "owner" in typeSpec['arraySpec']:
            owner = typeSpec['arraySpec']['owner']
            return owner
        else: return 'me'
    return typeSpec['owner']

def getOwnerFromTypeSpec(typeSpec):
    global currentCheckObjectVars
    if (typeSpec == 0):
        cdErr(currentCheckObjectVars)
    if(typeSpec==None):return None
    return typeSpec['owner']

def getCodeConverterByFieldID(classes, structName, fieldName, prevNameSeg, connector):
    structSpec=findSpecOf(classes[0], structName, 'struct')
    fieldID = structName+ "::" +fieldName
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

def getItrTypeOfDataStruct(datastructID, containerType):
    if 'fromImplemented' in containerType:
        fromImplemented = containerType['fromImplemented']
        if 'itrTypeSpec' in fromImplemented:
            return fromImplemented['itrTypeSpec']
    return None

#### Packed Template Arg Handling Functions ####
def getOwnerFromTemplateArg(tArg):
    global currentCheckObjectVars
    if (tArg == 0):
        cdErr(currentCheckObjectVars)
    return tArg['tArgOwner']

def getTypeFromTemplateArg(tArg):
    global currentCheckObjectVars
    if (tArg == 0):
        cdErr(currentCheckObjectVars)
    return tArg['tArgType']

################################################

def setCurrentCheckObjectVars(message):
    global currentCheckObjectVars
    currentCheckObjectVars = message

def ownerIsPointer(owner):
    if owner == 'their' or owner == 'our' or owner == 'my' or owner == 'itr' or owner == 'id_their' or owner == 'id_our': isPointer=True
    else: isPointer=False
    return isPointer

def typeIsPointer(typeSpec):
    if isinstance(typeSpec,str): owner = typeSpec   # typeSpec is really Owner field
    else: owner=getTypeSpecOwner(typeSpec)          # typeSpec is full typeSpec
    return ownerIsPointer(owner)

def fieldIsFunction(typeSpec):
    if typeSpec==None:
        return False
    if 'argList' in typeSpec and typeSpec['argList']!=None:
        return True
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
            if field['fieldName']==structname and field['typeSpec']['argList']==None:
                #print ("isWrappedType: ", field['typeSpec']['argList'], structname)
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
    if(isinstance(ItmType, str)):
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

def getUnwrappedClassFieldTypeKeyWord(classes, structName):
    baseType = isWrappedType(classes, structName)
    if(baseType!=None): return fieldTypeKeyword(baseType)
    else: return structName

def baseStructName(structName):
    colonIndex=structName.find('::')
    if(colonIndex==-1): return structName
    return structName[0:colonIndex]

def fieldTypeKeyword(fieldType):
    # fieldType can be fieldType or typeSpec
    if fieldType==None: return 'NONE'
    if 'owner' in fieldType and fieldType['owner']=='PTR':
        return 'NONE'
    if 'fieldType' in fieldType:    # if var fieldType is typeSpec
        fieldType = fieldType['fieldType']
    if isinstance(fieldType, str):
        return fieldType
    if('varType' in fieldType[0]):
        fieldType = fieldType[0]['varType']
    if isinstance(fieldType[0], str):
        return fieldType[0]
    if isinstance(fieldType[0][0], str):
        return fieldType[0][0]
    cdErr("?Invalid fieldTypeKeyword?")

def queryTagFunction(classes, className, funcName, matchName, typeSpecIn):
    funcField = doesClassContainFunc(classes, className, funcName)
    if(funcField):
        funcFieldKW = fieldTypeKeyword(funcField['typeSpec'])
        if(funcFieldKW == matchName):
            typeArgList = getTypeArgList(className)
            reqTagList  = getReqTagList(typeSpecIn)
            count = 0
            for item in typeArgList:
                if(item == matchName):
                    innerTypeOwner   = getOwnerFromTemplateArg(reqTagList[count])
                    innerTypeKeyWord = getTypeFromTemplateArg(reqTagList[count])
                    return([innerTypeOwner, innerTypeKeyWord])
                count += 1
    return([None, None])

def isStruct(fieldType):
    if isinstance(fieldType, str): return False
    return True

def isBaseType(fType):
    KW = fieldTypeKeyword(fType)
    if KW=='string' or KW[0:4]=='uint' or KW[0:3]=='int' or KW[0:6]=='double' or KW[0:4]=='char' or KW[0:4]=='bool' or KW[0:4]=='flag':
        return True
    return False

def isAltStruct(classes, fieldType):
    if not isStruct(fieldType) or not(fieldType[0] in classes[0]): return [False, [] ]
    fieldObj=classes[0][fieldType[0]]
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

def typeIsNumRange(fieldType):
    if isinstance(fieldType, str): return False
    if len(fieldType)==3:
        if fieldType[1]=='..':
            return True
    return False

def typeIsInteger(fieldType):
    # NOTE: If you need this to work for wrapped types as well use the version in CodeGenerator.py
    if fieldType == None: return False
    if typeIsNumRange(fieldType): return True
    if not isinstance(fieldType, str):
        fieldType= fieldType[0]
    if fieldType=="int" or fieldType=="BigInt" or fieldType=="uint" or fieldType=="uint64" or fieldType=="uint32"or fieldType=="int64" or fieldType=="int32" or fieldType=="FlexNum":
        return True
    return False

def isStringNumeric(S):
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

def TypeSpecsMinimumBaseType(classes, typeSpec):
    owner=typeSpec['owner']
    fieldType = typeSpec['fieldType']
    #print("TYPESPEC:", typeSpec, "<", fieldType, ">\n")
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
    if typeKey=='flag' or typeKey=='mode' or typeKey=='timeValue' or typeKey=='void' or typeKey=='char' or typeKey=='double' or typeKey=='float' or typeKey=='string' or typeKey=='bool': return typeKey
    if isStruct(fieldType): return 'struct'
    if typeIsInteger(fieldType): return 'int'
    return 'ERROR'

def varsTypeCategory(typeSpec):
    fieldType=''
    if isinstance(typeSpec, str): fieldType=typeSpec
    else:
        fieldType=getFieldType(typeSpec)
    return innerTypeCategory(fieldType)

def fieldsTypeCategory(typeSpec):
    if 'argList' in typeSpec and typeSpec['argList']!=None: return 'func'
    return varsTypeCategory(typeSpec)

def varTypeKeyWord(typeSpec):
    if typeSpec == None: varType=None
    elif isinstance(typeSpec, str): varType=typeSpec
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
    if fieldTypeKeyword(typeSpec1) != fieldTypeKeyword(typeSpec2): return False
    leftContainerNull  = not(isAContainer(typeSpec1))
    rightContainerNull = not(isAContainer(typeSpec2))
    if not leftContainerNull and rightContainerNull: return False
    if leftContainerNull and not rightContainerNull: return False
    if not leftContainerNull and not rightContainerNull and getContainerSpec(typeSpec1) != getContainerSpec(typeSpec2): return False
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
