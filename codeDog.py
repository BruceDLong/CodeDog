# CodeDog Program Maker

import progSpec
import codeDogParser

import pattern_Write_Main
import pattern_Gen_ParsePrint
import pattern_Gen_Eventhandler
#import pattern_Gen_GUI

import CodeGenerator_CPP
#import CodeGenerator_JavaScript
#import CodeGenerator_ObjectiveC
#import CodeGenerator_Java

import re
import os
import sys
import errno

def writeFile(path, fileName, outStr):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST: raise

    fo=open(path + os.sep + fileName, 'w')
    fo.write(outStr)
    fo.close()

def ScanAndApplyPatterns(objects, tags):
    print "Applying Patterns..."
    for item in objects[1]:
        if item[0]=='!':
            print item

def GenerateProgram(objects, buildSpec, tags):
    print tags
    result='No Language Generator Found for '+tags['langToGen']
    langGenTag = tags['langToGen']
    if(langGenTag == 'CPP'):
        print 'Generating C++ Program...'
        result=CodeGenerator_CPP.generate(objects, [tags, buildSpec[1]])
    else:
        print "No language generator found for ", langGenTag
    return result

def GenerateSystem(objects, buildSpecs, tags):
    ScanAndApplyPatterns(objects, tags)
    for buildSpec in buildSpecs:
        buildName=buildSpec[0]
        print "Generating code for build ", buildName
        outStr = GenerateProgram(objects, buildSpec, tags)
        writeFile(buildName, tagStore['FileName'], outStr)
        #GenerateBuildSystem()
    # GenerateTests()
    # GenerateDocuments()
    return outStr


#############################################    L o a d / P a r s e   P r o g r a m   S p e c

if(len(sys.argv) < 2):
    print "No Filename given.\n"
    exit(1)

file_name = sys.argv[1]
f=open(file_name)
codeDogStr = f.read()
f.close()

# objectSpecs is like: [ProgSpec, objNames]
[tagStore, buildSpecs, objectSpecs] = codeDogParser.parseCodeDogString(codeDogStr)

outputScript = GenerateSystem(objectSpecs, buildSpecs, tagStore)
