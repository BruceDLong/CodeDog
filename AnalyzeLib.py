#!/usr/bin/env python3
# AnalyzeLib.py
import sys;  sys.dont_write_bytecode = True
import re
import codeDogParser
import libraryMngr
import progSpec
from progSpec import cdlog, cdErr, logLvl, dePythonStr
from progSpec import structsNeedingModification
from pyparsing import ParseResults
from pprint import pprint

import os
from os.path import abspath
import errno

classDefs   = {}
classNames  = []
fileClasses = [classDefs, classNames]
libPaths    = []
libsFields  = []

if sys.version_info[0] < 3:
    print("\n\nERROR: CodeDog must be used with Python 3\n")
    exit(1)

codeDogVersion = '2.0'


if(len(sys.argv) < 2):
    print("\n    usage: codeDog [-v] filename\n")
    exit(1)
arg1 = sys.argv[1]
if arg1=="-v" or arg1=='--version':
    print("\n    CodeDog application compiler version "+ codeDogVersion+"\n")
    exit(1)
if arg1[0]=='-':
    print("Unsupported argument:", arg1)
    exit(1)

##################################################
def makeDir(dirToGen):
    try:
        os.makedirs(dirToGen)
    except OSError as exception:
        if exception.errno != errno.EEXIST: raise

def writeFile(libPath):
    global libsFields
    dirName = "LIB_ANALYSIS"
    makeDir(dirName)
    libsDir, libName = os.path.split(abspath(libPath))
    base=os.path.basename(libPath)
    fileName = dirName+"/"+libName+".info"
    cdlog(1, "WRITING FILE: "+fileName)
    with open(fileName, 'wt') as out: pprint(libsFields, stream=out)

def addToLibFieldsList(filename, fileClasses, newClasses):
    global libsFields
    libraryClasses = []
    for className in newClasses:
        fieldsList = []
        classDef = fileClasses[0][className]
        if 'fields' in classDef:
            for fieldDef in classDef['fields']:
                if progSpec.fieldIsFunction(fieldDef['typeSpec']):
                    #print("VALUE: ", fieldDef['value'])
                    if fieldDef['hasFuncBody'] and fieldDef['value'][0]:
                        status = 'Impl'
                    elif not fieldDef['hasFuncBody']:
                        status = 'Abstract'
                    elif fieldDef['hasFuncBody'] and (fieldDef['value'][0] == [] or fieldDef['value'] == ''):
                        status = 'Empty'
                    elif 'verbatimText' in fieldDef['typeSpec']:
                        status = 'Impl'
                    elif 'codeConverter' in fieldDef['typeSpec']:
                        status = 'Convtr'
                    else:
                        print("Unknown: ", fieldDef)
                        status = 'Unknown'
                    fieldIDandStatus = {'fieldID':fieldDef['fieldID'], 'status':status}
                else: fieldIDandStatus = {'fieldID':fieldDef['fieldID']}
                fieldsList.append(fieldIDandStatus)
        libraryClass = {'className':className, 'fields': fieldsList}
        libraryClasses.append(libraryClass)
    library = [filename, libraryClasses]
    libsFields.append(library)

def loadLibrary(filename):
    global classDefs
    global classNames
    global fileClasses
    codeDogStr = progSpec.stringFromFile(filename)
    codeDogStr = libraryMngr.processIncludedFiles(codeDogStr, filename)
    [tagStore, buildSpecs, fileClasses, newClasses] = codeDogParser.parseCodeDogString(codeDogStr, fileClasses[0], fileClasses[1], {}, filename)
    return [fileClasses, newClasses]

def analyzeLibByName(filename):
    [fileClasses, newClasses] = loadLibrary(filename)
    addToLibFieldsList(arg1, fileClasses, newClasses)
    writeFile(filename)

#filename = "LIBS/"+arg1+".Lib.dog"
filename = arg1
analyzeLibByName(filename)

