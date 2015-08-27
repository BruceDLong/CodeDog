
# ProgSpec manipulation routines

import re

#  spec: [structsSpec, structNames ]
structsSpec=0

def addStruct(spec, name):
    if(name in spec[structsSpec]):
        print "The struct '", name, "' is being added but already exists."
        exit(1)
    spec[structsSpec][name]={'name':name, "attrList":[], "attr":{}, "fields":[]}
    print "ADDED STRUCT: ", name

def addField(spec, structName, kindOfField, fieldType, fieldName):
    if (kindOfField=="var" or kindOfField=="ptr" or kindOfField=="dblList"):
        spec[structsSpec][structName]["fields"].append({'kindOfField':kindOfField, 'fieldType':fieldType, 'fieldName':fieldName})
    else:
        print "When adding a Field to ", structName, ", invalid field type: ", kindOfField,"."
        exit(1)
    print "    ADDED FIELD:\t", kindOfField, fieldName

def addFlag(spec, structName, flagName):
    spec[structsSpec][structName]["fields"].append({'kindOfField':'flag', 'fieldName':flagName})
    print "    ADDED FLAG: \t", flagName


def addMode(spec, structName, modeName, enumList):
    spec[structsSpec][structName]["fields"].append({'kindOfField':'mode', 'fieldName':modeName, 'enumList':enumList})
    print "    ADDED MODE:\t", modeName


def addFunc(spec, structName, funcName, returnType, funcText):
    spec[structsSpec][structName]["fields"].append({'kindOfField':'func', 'funcText':funcText, 'returnType':returnType, 'fieldName':funcName})
    print "    ADDED FUNCTION:\t", funcName


def addMartialType():
    print "ADDED MARTIAL: "


def CreatePointerItems(spec, structName):
    spec[structsSpec][structName]=structName;
    print "ADDED AUTO-POINTER: "+structName


def CreateConstructorsDestructors():
    # Includes martialing constructors and copy operators + DeepCopy or ShallowCopy
    print "ADDED CONSTRUCTS: "


def FillStructFromText(spec, structName, structDefString):
    print "POPULATING STRUCT ", structName, " FROM TEXT..."

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
            addFlag(spec, structName, items.group(2))
        elif fieldType=="mode":
            items=re.match("\s*(\w+)\s*:\s*(\w+)\s*\[([\w\s,]*)\]", structBodyText)
            #print "<<<<<<<"+items.group(3)+">>>>>>>>>"
            fieldsName=items.group(2)
            enumList=re.findall("\w+", items.group(3))
            addMode(spec, structName, fieldsName, enumList)
        elif (fieldType=="var"):
            items=re.match("\s*(\w+)\s*:\s*(\w+)\s*([\w\s<> \*,\[\]]*);", structBodyText)
            fieldsType=items.group(2)
            fieldsName=items.group(3)
            addField(spec, structName, "var", fieldsType, fieldsName)
        elif fieldType=="ptr":
            items=re.match("\s*(\w+)\s*:\s*(\w+)\s*(\w*)", structBodyText)
            fieldsType=items.group(2)
            fieldsName=items.group(3)
            addField(spec, structName, "ptr", fieldsType, fieldsName)
        elif fieldType=="dblList":
            items=re.match("\s*(\w+)\s*:\s*(\w+)\s*(\w*)", structBodyText)
            fieldsType=items.group(2)
            fieldsName=items.group(3)
            addField(spec, structName, "dblList", fieldsType, fieldsName)
        elif fieldType=="func":
            items=re.match("\s*(\w+)\s*:\s*(.+?)\s*:\s*(.+?)\s*END", structBodyText, re.DOTALL)
            returnType=items.group(2)
            funcsText=items.group(3)
            fieldsName="FUNC"
            addFunc(spec, structName, fieldsName, returnType, funcsText)

        structBodyText=structBodyText[items.end():]
