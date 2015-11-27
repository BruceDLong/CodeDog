# CodeDog Program Maker

import progSpec
import codeDogParser

import pattern_Write_Main
import pattern_Gen_ParsePrint
import pattern_Gen_Eventhandler
import pattern_BigNums
#import pattern_Gen_GUI

#import stringStructs

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

def stringFromFile(filename):
    f=open(filename)
    Str = f.read()
    f.close()
    return Str

def processIncludedFiles(fileString):
    pattern = re.compile(r'#include +([\w -\.\/\\]+)')
    return pattern.sub(replaceFileName, fileString)

def replaceFileName(fileMatch):
    includedStr = stringFromFile(fileMatch.group(1))
    includedStr = processIncludedFiles(includedStr)
    return includedStr


def ScanAndApplyPatterns(objects, tags):
    print "Applying Patterns..."
    print len(objects[1])
    for item in objects[1]:
        print "    ITEM:", item
        if item[0]=='!':
            pattName=item[1:]
            patternArgs=objects[0][pattName]['parameters']
            print pattName, ':', patternArgs

            if pattName=='Write_Main': pattern_Write_Main.apply(objects, tags, patternArgs[0])
            elif pattName=='Gen_Eventhandler': pattern_Gen_Eventhandler.apply(objects, tags)
            elif pattName=='writeParser': pattern_Gen_ParsePrint.apply(objects, tags, patternArgs[0], patternArgs[1])
            elif pattName=='useBigNums': pattern_BigNums.apply(tags)


def setFeatureNeeded(tags, featureID, objMap):
    tags[featureID]=objMap

def ScanFuncsAndTypesThenSetTags(tags):
    for typeName in progSpec.storeOfBaseTypesUsed:
        if(typeName=='BigNum' or typeName=='BigFrac'):
            print 'Need Large Numbers'
            setFeatureNeeded(tags, 'largeNumbers', progSpec.storeOfBaseTypesUsed[typeName])


def GenerateProgram(objects, buildSpec, tags):
    result='No Language Generator Found for '+tags['langToGen']
    langGenTag = tags['langToGen']
    if(langGenTag == 'CPP'):
        print 'Generating C++ Program...'
        result=CodeGenerator_CPP.generate(objects, [tags, buildSpec[1]])
    else:
        print "No language generator found for ", langGenTag
    return result

def GenerateSystem(objects, buildSpecs, tags):
    print "Generating System"
    ScanAndApplyPatterns(objects, tags)
    #stringStructs.CreateStructsForStringModels(objects, tags)
    ScanFuncsAndTypesThenSetTags(tags)
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
codeDogStr = stringFromFile(file_name)
codeDogStr = processIncludedFiles(codeDogStr)


# objectSpecs is like: [ProgSpec, objNames]
print "Parsing", file_name, "..."
[tagStore, buildSpecs, objectSpecs] = codeDogParser.parseCodeDogString(codeDogStr)
tagStore['dogFilename']=file_name

outputScript = GenerateSystem(objectSpecs, buildSpecs, tagStore)
