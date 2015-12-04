# CodeDog Program Maker
#   This file is code to convert "string" style structures into 'struct' style structures.

import progSpec
import codeDogParser

def codeDogTypeToString(objects, tags, field):
    S=''
    fieldName=field['fieldName']
    fieldType=field['fieldType']
    fieldValue =field['value']
    fieldOwner =field['owner']
    if(fieldType == 'flag'):
        if fieldValue!=None and fieldValue!=0 and fieldValue!='false':
            S+='flag: ' + fieldName + '=true\n'
        else: S+='flag: ' + fieldName +'\n'
    elif fieldType=='mode':
        if fieldValue!=None:
            S+='mode ['+field['enumList']+']: ' + fieldName + '='+fieldValue+'\n'
        else: S+='mode ['+field['enumList']+']: ' + fieldName +'\n'
    elif fieldOwner=='const':
        S+='const '+fieldType+': ' + fieldName + '='+fieldValue+'\n'
    elif fieldOwner=='const':
        print "Finish This"

    return S

def writePositionalFetch(objects, tags, field):
    S="""
    const fetchOK=0
    const fetchNotReady=1
    const fetchParseError=2
    const fetchIOError=3

    getStatus fetch(){
        if(%s_hasVal) return fetchOK
        if(length is constant) set it and set flag
        if(! %s_hasPos)
            query for it
            // use predecessor's pos+len
        if(%s_hasPos)
             Scoop the data with A<-B
             set and propagate length
    }
    """ % [fname, fname, fname]
    return S

def CreateStructsForStringModels(objects, tags):
    print "Creating structs from string models..."
    for objectName in objects[1]:
        ObjectDef = objects[0][objectName]
        if(objectName[0] != '!' and ObjectDef['stateType'] == 'string'):
            print "    ", objectName
            objFieldStr=""
            for field in ObjectDef['fields']:
                fname=field['fieldName']
                print "        ", field
                objFieldStr+="    "+codeDogTypeToString(objects, tags, field)
                objFieldStr+="    flag: "+fname+'_hasVal\n'
                if(field['isNext']==True):
                    objFieldStr+="    flag: "+fname+'_hasPos\n'
                    objFieldStr+="    flag: "+fname+'_hasLen\n'
                    objFieldStr+="    streamSpan: "+fname+'_span\n'
                    objFieldStr+= writePositionalFetch(field)
                    objFieldStr+= writePositionalSet(field)
                else:
                    objFieldStr+= writeContextualGet(field) #'    func int: '+fname+'_get(){}\n'
                    objFieldStr+= writeContextualSet(field)
            print "objFieldStr:", objFieldStr
            structsName = objectName+"_struct"
            #progSpec.addObject(objects[0], objects[1], structsName, 'struct')
            #codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef(structsName, objFieldStr))
