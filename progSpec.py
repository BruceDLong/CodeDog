
# ProgSpec manipulation routines

import re

def addPattern(objSpecs, objectNameList, name, patternList):
    patternName='!'+name
    objectNameList.append(patternName)
    objSpecs[name]={'name':patternName, 'parameters':patternList}
    print "ADDED PATTERN", name

def addObject(objSpecs, objectNameList, name):
    objectNameList.append(name)
    if(name in objSpecs):
        print "Note: The struct '", name, "' is being added but already exists."
        return
    objSpecs[name]={'name':name, "attrList":[], "attr":{}, "fields":[]}
    print "ADDED STRUCT: ", name

def addObjTags(objSpecs, objectName, objTags):
    objSpecs[objectName]["tags"]=objTags
    print "    ADDED Tags to object.\t"


def addField(objSpecs, objectName, kindOfField, fieldType, fieldName):
    if (kindOfField=="var" or kindOfField=="rPtr" or kindOfField=="sPtr" or kindOfField=="uPtr"):
        objSpecs[objectName]["fields"].append({'kindOfField':kindOfField, 'fieldType':fieldType, 'fieldName':fieldName})
    else:
        print "When adding a Field to ", objectName, ", invalid field type: ", kindOfField,"."
        exit(1)
    print "    ADDED FIELD:\t", kindOfField, fieldName

def addFlag(objSpecs, objectName, flagName):
    objSpecs[objectName]["fields"].append({'kindOfField':'flag', 'fieldName':flagName})
    print "    ADDED FLAG: \t", flagName


def addMode(objSpecs, objectName, modeName, enumList):
    objSpecs[objectName]["fields"].append({'kindOfField':'mode', 'fieldName':modeName, 'enumList':enumList})
    print "    ADDED MODE:\t", modeName
    print enumList

def addConst(objSpecs, objectName, cppType, constName, constValue):
    objSpecs[objectName]["fields"].append({'kindOfField':'const', 'fieldType':cppType, 'fieldName':constName, 'fieldValue':constValue})
    print "    ADDED CONST\n"

def addFunc(objSpecs, objectName, returnType, funcName, argList, tagList, funcBody):
    objSpecs[objectName]["fields"].append({'kindOfField':'func', 'funcText':funcBody, 'fieldType':returnType, 'fieldName':funcName})
    print "    ADDED FUNCTION:\t", funcName

def addActionToSeq(objSpecs, objectName, funcName, ):

    print "        ADDED Action to ", objName, ".", funcName, ".\n"

def addSequenceToFunc(objSpecs, objectName, funcName, ):

    print "        ADDED Sequence to ", objName, ".", funcName, ".\n"

def addRepetitionToFunc(objSpecs, objectName, funcName, ):

    print "        ADDED Repetition to ", objName, ".", funcName, ".\n"

def addLocalVarToFunc(objSpecs, objectName, funcName, ):

    print "        ADDED LocalVar to ", objName, ".", funcName, ".\n"

def addCommentToFunc(objSpecs, objectName, funcName, ):

    print "        ADDED Comment to ", objName, ".", funcName, ".\n"


###############

def fetchTagValue(tagStoreArray, tagToFind):
    for tagStore in reversed(tagStoreArray):
        if(tagToFind in tagStore):
            return tagStore[tagToFind]
    return None

###############

def getNameSegInfo(objMap, structName, fieldName):
    structToSearch = objMap[structName]
    if not structToSearch: print "struct ", structName, " not found."; exit(2);
    fieldListToSearch = structToSearch['fields']
    if not fieldListToSearch: print "struct's fields ", structName, " not found."; exit(2);
    for fieldRec in fieldListToSearch:
        if fieldRec['fieldName']==fieldName:
            print "FOR ", structName, ',', fieldName, ", returning", fieldRec
            return fieldRec
    return None

def getFieldInfo(objMap, structName, fieldNameSegments):
    # return [kind-of-last-element,  reference-string, type-of-last-element]
    structKind=""
    prevKind="ptr"
    structType=""
    referenceStr=""
    print "    Getting Field Info for:", structName, fieldNameSegments
    for fieldName in fieldNameSegments:
        REF=getNameSegInfo(objMap, structName, fieldName)
        if(REF):
            print "    REF:", REF
            if 'kindOfField' in REF:
                structKind=REF['kindOfField']
                if(prevKind=="ptr"): joiner='.' #'->'
                else: joiner='.'
                if (structKind=='flag'):
                    referenceStr+=joiner+"flags"
                elif structKind=='mode':
                    referenceStr+=joiner+'flags'
                elif structKind=='var':
                    referenceStr+= joiner+fieldName
                    structType=REF['fieldType']
                elif structKind=='ptr':
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
        actionStr="SetBits(ITEM.flags, "+action[0][-1]+", "+ action[2][0]+");"
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

