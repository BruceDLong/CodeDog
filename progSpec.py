
# ProgSpec manipulation routines

import re

def addObject(objSpecs, objectNameList, name, objTags):
    objectNameList.append(name)
    if(name in objSpecs):
        print "The struct '", name, "' is being added but already exists."
        exit(1)
    objSpecs[name]={'name':name, "attrList":[], "attr":{}, "fields":[]}
    print "ADDED STRUCT: ", name

def addField(objSpecs, objectName, kindOfField, fieldType, fieldName):
    if (kindOfField=="var" or kindOfField=="rPtr" kindOfField=="sPtr" or kindOfField=="uPtr"):
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

def addConst(objSpecs, objectName, constName, constValue):
    objSpecs[objectName]["fields"].append({'kindOfField':'const', 'fieldName':constName, 'fieldValue':constValue})
    print "    ADDED CONST\n"


def addFunc(objSpecs, objectName, funcName, returnType, argList, funcBody):
    objSpecs[objectName]["fields"].append({'kindOfField':'func', 'funcText':funcText, 'returnType':returnType, 'fieldName':funcName})
    print "    ADDED FUNCTION:\t", funcName

def FillStructFromText(objSpecs, objectNameList, objectName, structDefString):
    print "POPULATING STRUCT ", objectName, " FROM TEXT..."

    #Split struct body
    structBodyText=structDefString
    items=None
    while(1):
        fieldTypeM=re.match("\s*(\w+)\s*:\s*", structBodyText)
        if fieldTypeM is None:
            break
        fieldType=fieldTypeM.group(1);
        #print fieldType
        if(fieldType=="flag"):
            items=re.match("\s*(\w+)\s*:\s*(\w+)", structBodyText)
            addFlag(objSpecs, objectNames, items.group(2))
        elif fieldType=="mode":
            items=re.match("\s*(\w+)\s*:\s*(\w+)\s*\[([\w\s,]*)\]", structBodyText)
            #print "<<<<<<<"+items.group(3)+">>>>>>>>>"
            fieldsName=items.group(2)
            enumList=re.findall("\w+", items.group(3))
            addMode(objSpecs, objectNames, fieldsName, enumList)
        elif (fieldType=="var"):
            items=re.match("\s*(\w+)\s*:\s*(\w+)\s*([\w\s<> \*,\[\]]*);", structBodyText)
            fieldsType=items.group(2)
            fieldsName=items.group(3)
            addField(objSpecs, objectNames, "var", fieldsType, fieldsName)
        elif fieldType=="ptr":
            items=re.match("\s*(\w+)\s*:\s*(\w+)\s*(\w*)", structBodyText)
            fieldsType=items.group(2)
            fieldsName=items.group(3)
            addField(objSpecs, objectNames, "ptr", fieldsType, fieldsName)
        elif fieldType=="dblList":
            items=re.match("\s*(\w+)\s*:\s*(\w+)\s*(\w*)", structBodyText)
            fieldsType=items.group(2)
            fieldsName=items.group(3)
            addField(objSpecs, objectNames, "dblList", fieldsType, fieldsName)
        elif fieldType=="func":
            items=re.match("\s*(\w+)\s*:\s*(.+?)\s*:\s*(.+?)\s*END", structBodyText, re.DOTALL)
            returnType=items.group(2)
            funcsText=items.group(3)
            fieldsName="FUNC"
            addFunc(objSpecs, objectNames, fieldsName, returnType, funcsText)

        structBodyText=structBodyText[items.end():]
