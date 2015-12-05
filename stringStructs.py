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
    fname=field['fieldName']
# TODO: Move these constants out-side. They should only be done once. Best if they an an enum.
    S="""
    const int32: fetchOK=0
    const int32: fetchNotReady=1
    const int32: fetchParseError=2
    const int32: fetchIOError=3

    me uint32: fetch_%s()={
        if(%s_hasVal) {return (fetchOK)}
        }
"""% (fname, fname)
    temp="""
        if(this is const string) set length and set have-length flag
        if(! %s_hasPos)
            query for it
            // use predecessor's pos+len
        if(%s_hasPos)
             Scoop the data with A<-B
             set and propagate length
    }
    """ # % (fname, fname, fname)
    return S

def writePositionalSet(field):
    return "    // Positional Set() TBD\n";

def writeContextualGet(field):
    return "    // Contextual Get() TBD\n";

def writeContextualSet(field):
    return "    // Contextual Set() TBD\n";

def CreateStructsForStringModels(objects, tags):
    print "Creating structs from string models..."
    for objectName in objects[1]:
        if objectName[0] == '!': continue
        ObjectDef = objects[0][objectName]
        if(objectName[0] != '!' and ObjectDef['stateType'] == 'string'):
            print "    WRITING STRUCT:", objectName
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
                    objFieldStr+= writePositionalFetch(objects, tags, field)
                    objFieldStr+= writePositionalSet(field)
                else:
                    objFieldStr+= writeContextualGet(field) #'    func int: '+fname+'_get(){}\n'
                    objFieldStr+= writeContextualSet(field)
            print "#################################### objFieldStr:\n", objFieldStr, '\n####################################'
            structsName = objectName+"_struct"
            progSpec.addObject(objects[0], objects[1], structsName, 'struct')
            codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef(structsName, objFieldStr))
