
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
        print "The struct '", name, "' is being added but already exists."
        exit(1)
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
