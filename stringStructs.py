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
            S+='flag: ' + fieldName + ' <- true\n'
        else: S+='flag: ' + fieldName +'\n'
    elif fieldType=='mode':
        if fieldValue!=None:
            S+='mode ['+field['enumList']+']: ' + fieldName + ' <- '+fieldValue+'\n'
        else: S+='mode ['+field['enumList']+']: ' + fieldName +'\n'
    elif fieldOwner=='const':
        print 'const ', fieldType, ': ', fieldName, ' <- ',fieldValue
        #S+='const '+fieldType+': ' + fieldName + ' <- '+fieldValue+'\n'
    elif fieldOwner=='const':
        print "Finish This"

    return S

def writePositionalFetch(objects, tags, field):
    fname=field['fieldName']
    fieldType=str(field['fieldType'])
    S="""
    me fetchResult: fetch_%s() <- {
        if(%s_hasVal) {return (fetchOK)}
        }
"""% (fname, fname)
    return S




    print 'FIELD::', fname, field['owner'], '"'+fieldType+'"'
    if(field['owner']=='const' and fieldType=='string'):
        S+='    %s_hasLen <- true \n    %s_span.len <- '% (fname, fname) + str(len(field['value']))
    S+="        if(! %s_hasPos){pos <- pred.pos+pred.len}\n" % (fname)
    S+="        if( %s_hasPos){\n" % (fname)
    # Scoop Data
    S+=' FieldTYpe("' + fieldType +'")\n'
    if fieldType=='struct':
        print " Call stuct's fetch()"
    #elif fieldType=='':
    # Set and propogate length
    S+="        }\n"
    S+='    }'

    return S

def writePositionalSet(field):
    return "    // Positional Set() TBD\n";

def writeContextualGet(field):
    return "    // Contextual Get() TBD\n";

def writeContextualSet(field):
    return "    // Contextual Set() TBD\n";

def CreateStructsForStringModels(objects, tags):
    print "Creating structs from string models..."

    # Define fieldResult struct
    structsName = 'fetchResult'
    StructFieldStr = "mode [fetchOK, fetchNotReady, fetchSyntaxError, FetchIO_Error] : FetchResult"
    progSpec.addObject(objects[0], objects[1], structsName, 'struct', 'SEQ')
    codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef(structsName, StructFieldStr))

    # Define streamSpan struct
    structsName = 'streamSpan'
    StructFieldStr = "    me uint32: offset \n    me uint32: len"
    progSpec.addObject(objects[0], objects[1], structsName, 'struct', 'SEQ')
    codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef(structsName, StructFieldStr))


    for objectName in objects[1]:
        if objectName[0] == '!': continue
        ObjectDef = objects[0][objectName]
        if(objectName[0] != '!' and ObjectDef['stateType'] == 'string'):
            primaryFetchFuncText='\n\nme fetchResult: fetch()<- {\n    me fetchResult: result\n'
            configType=ObjectDef['configType']
            print "    WRITING STRING-STRUCT:", objectName, configType
            objFieldStr=""
            objFieldStr='   me  string: data\n'
            for field in ObjectDef['fields']:
                fname=field['fieldName']
                print "        ", field

                #### First, write fetch function for this field...
                objFieldStr+="    "+codeDogTypeToString(objects, tags, field)
                objFieldStr+="    flag: "+fname+'_hasVal\n'
                if(field['isNext']==True):
                    objFieldStr+="    flag: "+fname+'_hasPos\n'
                    objFieldStr+="    flag: "+fname+'_hasLen\n'
                    objFieldStr+="    me streamSpan: "+fname+'_span\n'
                    objFieldStr+= writePositionalFetch(objects, tags, field)
                    objFieldStr+= writePositionalSet(field)
                else:
                    objFieldStr+= writeContextualGet(field) #'    func int: '+fname+'_get(){}\n'
                    objFieldStr+= writeContextualSet(field)

                ### Next, call that function from the 'master' fetch()...
    #            primaryFetchFuncText+='    result <- fetch_'+fname+'()\n'
    #            if(configType=='SEQ'):
     #               primaryFetchFuncText+='    if(result!=fetchOK){return(result)}\n\n'
     #           elif(configTypee=='ALT'):
     #               primaryFetchFuncText+='     if(result!=fetchSyntaxError){return(result)}\n\n'
            if(configType=='SEQ'):  primaryFetchFuncText+='    return(fetchOK)\n'
            elif(configType=='ALT'):primaryFetchFuncText+='    return(fetchSyntaxError)\n'
            primaryFetchFuncText+='\n}\n'
            objFieldStr += primaryFetchFuncText
            print "#################################### objFieldStr:\n", objFieldStr, '\n####################################'
            structsName = objectName+"_struct"
            progSpec.addObject(objects[0], objects[1], structsName, 'struct', 'SEQ')
            codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef(structsName, objFieldStr))
