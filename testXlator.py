#!/usr/bin/env python
# CodeDog Xlator tester

import os
from progSpec import cdlog
import errno
import subprocess
import sys;  sys.dont_write_bytecode = True
buildSpec = "LinuxBuild: Platform='Linux' CPU='amd64' Lang='CPP' optimize='speed';"

testDefinitions = {
     'class/simple':       ['struct emptyClass{ }', 'PGB'],
     'class/intDecl':      ['struct testClass{me int: myInt}', 'PGB'],
     'class/strDecl':      ['struct testClass{me string: myString}', 'PGB'],
     'class/int32Decl':    ['struct testClass{me int32: myInt32}', 'PGB'],
     'class/int64Decl':    ['struct testClass{me int64: myInt64}', 'PGB'],
     'class/doubleDecl':   ['struct testClass{me double: myDouble}', 'PGB'],
     'class/uint32Decl':   ['struct testClass{me uint32: myUint32}', 'PGB'],
     'class/uint64Decl':   ['struct testClass{me uint64: myUint64}', 'PGB'],
     'class/boolDecl':     ['struct testClass{me bool: myBool}', 'PGB'],
     'class/constDecl':    ['struct testClass{const int: pi <- 3.14}', 'PGB'],
     'class/charDecl':     ['struct testClass{me char: myChar}', 'PGB'],
     'class/baseDecls':    ['''
struct testClass{
    me int: myInt 
    me string: myString
    me int32: myInt32
    me int64: myInt64
    me double: myDouble
    me uint32: myUint32
    me uint64: myUint64
    me bool: myBool
    const int: pi <- 3.14
    me char: myChar
}''', 'PGB',['class/simple', 'class/intDecl', 'class/strDecl', 'class/int32Decl', 'class/int64Decl', 'class/doubleDecl', 'class/uint32Decl', 'class/uint64Decl', 'class/boolDecl', 'class/constDecl', 'class/charDecl']],
     #'class/strListDecl':  ['struct testClass{me string[list]: myStringList}', 'PGB'],
     #'class/mapDecl':      ['struct testClass{me int[map string]: testMap}', 'PGB'],
     #'class/multimapDecl':[],
     #'class/treeDecl':    [],
     #'class/graphDecl':   [],
     
     
     #'class/funcDecl':     ['struct testClass{me void: testFunc()<-{print("testFunc:")}}', 'PGB'],
#     'class/pureVirtualFunc':   ['''
#struct testClass{
#    me void: testFunc()<-{
#        print ("testFunc")
#    }
#}
#struct pureVirtualClass{
#    me void: pureVirtualFunc()
#}
#''', 'PGBR'],
     #'actions/funcCallArgs':['struct testClass{me void: testFunc()<-{testFunc2("FuncCallArg")}\nme void: testFunc2(me string: strArg)<-{print(strArg)}}', 'PGBR'],
     #'actions/withEach':    ['struct testClass{me void: testFunc()<-{me string[list]: myStringList\nwithEach str in myStringList:{print(str)}}}', 'PGBR'],
     #'actions/conditional': ['struct testClass{me void: testFunc()<-{testFunc2(true)}\nme void: testFunc2(me bool: isTrue)<-{if (isTrue){print("true")}\nelse{print("false")}}}', 'PGBR'],
     
     
     
     
}

tags = """BuildCmd = "g++ -g -std=gnu++14 `pkg-config --cflags gtk+-3.0` testXlator.cpp `pkg-config --libs gtk+-3.0` -o testXlator"
Title = "Infomage - DataDog"
FileName = "testXlator"
Version = "0.1"
CopyrightMesg = "Copyright (c) 2015-2016 Bruce Long"
Authors = "Bruce Long"
Description = "DataDog gives you the numbers of your life."
ProgramOrLibrary = "program"
LicenseText = `This file is part of the "Proteus suite" All Rights Reserved.`
runCode=<runCodeGoesHere>"""

def makeDir(dirToGen):
    #print "dirToGen:", dirToGen
    try:
        os.makedirs(dirToGen)
    except OSError as exception:
        if exception.errno != errno.EEXIST: raise

def writeFile(path, fileName, testString):
    #print path
    makeDir(path)
    makeDir(path+"/Resources")
    pathName = path + os.sep + fileName
    fo=open(pathName, 'w')
    fo.write(testString)
    fo.close()

def RunCodeDogPrg(testString):
    path = "xlatorTests"
    fileName = "testXlator.dog"
    writeFile(path, fileName, testString)
    #programmatically run "codeDog " + name of saved file then run file capture output search for 3 strings
    runString ="codeDog " + fileName 
    currentDirectory = currentWD = os.getcwd()
    workingDirectory = currentDirectory + "/" + path
    out, err = printResults(workingDirectory, runString)
    return out, err

def ExecCodeDogTest(testSpec, buildSpec):
    #print"testSpec: ", testSpec
    global tags
    testString = buildSpec+"\n"
    if(testSpec[1]=='PGBR'):
        testString += tags.replace('<runCodeGoesHere>', '`\nme testClass: TC\nTC.testFunc()\n`') + "\n"
    else:
        testString += tags.replace('<runCodeGoesHere>', '``') + "\n"

    testString += testSpec[0] + "\n"
    #print"testString: ", testString
    out, err = RunCodeDogPrg(testString)
    if out: 
        if(out.find('Marker: Parse Successful')==-1):
            print"***Parse Fail***: ", out
            #exit(1)
            return "***Parse Fail***"
        if (out.find('Marker: Code Gen Successful')==-1):
            print"***Code Gen Fail***: ", out
            #exit(1)
            return "***Code Gen Fail***"
        if (out.find('Marker: Build Successful')==-1): 
            print"***Build Fail***: ", out
            #exit(1)
            return "***Build Fail***"
        return "Success"
    else: return "***Error: no out***"
    # Check for parse success or error mesg

    # Check for build success or error mesg

    # Cut and verify resulting text Acc a short report

def runDeps(testKey):
    global buildSpec
    global testDefinitions
    depsList = testDefinitions[testKey][2]
    depsReportText = ""
    for dep in depsList:
        testResult = ExecCodeDogTest(testDefinitions[dep], buildSpec)
        depsReportText +=  "    " + dep + ": "+testResult+  "\n"
    return depsReportText

    
def runListedTests(testsToRun):
    global buildSpec
    global testDefinitions
    reportText = ""
    for testKey in testsToRun:
        print "Running test: ", testKey
        testResult = ExecCodeDogTest(testDefinitions[testKey], buildSpec)
        #print "testResult: ", testKey, "  ", testResult
        reportText+= testKey + ": "+testResult+  "\n"
        if(testResult!="Success"):
            depsReportText = runDeps(testKey)
            reportText+= depsReportText
    return reportText
    
def gatherListOfTestsToRun(keywordList):
    global testDefinitions
    testList = []
    if len(keywordList)>0:
        testList = keywordList
    else:
        for key in testDefinitions:
            if (len(testDefinitions[key])>2 and  len(testDefinitions[key][2])>0):
                testList.append(key)
    return testList

def printResults(workingDirectory, runString):
    pipe = subprocess.Popen(runString, cwd=workingDirectory, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    return out, err

###################################
# Get command line: tests and xlator name
if len(sys.argv)==1:
    print "\nUsage:", sys.argv[0], "<xlatorName> [test-names...]\n"
    exit(0)

xlatorName = sys.argv[1]
testListSpec = sys.argv[2:]

testsToRun = gatherListOfTestsToRun(testListSpec)
#print "testsToRun: ",testsToRun
reportText = runListedTests(testsToRun)
print "********** T E S T    R E S U L T S **********"
print reportText
print "**********************************************"
