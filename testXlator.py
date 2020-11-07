# !/usr/bin/env python3

# CodeDog Xlator tester

import os
from progSpec import cdlog
import errno
import subprocess
import sys;  sys.dont_write_bytecode = True
buildSpec = ""
runSpec = ""
workingDirectory = ""
runDirectory = ""

testDefinitions = {
     'class/simple':        ['struct emptyClass{ }', 'PGB:'],
     'class/intDecl':       ['struct testClass{me int: myInt}', 'PGB:'],
     'class/strDecl':       ['struct testClass{me string: myString}', 'PGB:'],
     'class/int32Decl':     ['struct testClass{me int32: myInt32}', 'PGB:'],
     'class/int64Decl':     ['struct testClass{me int64: myInt64}', 'PGB:'],
     'class/doubleDecl':    ['struct testClass{me double: myDouble}', 'PGB:'],
     'class/uint32Decl':    ['struct testClass{me uint32: myUint32}', 'PGB:'],
     'class/uint64Decl':    ['struct testClass{me uint64: myUint64}', 'PGB:'],
     'class/boolDecl':      ['struct testClass{me bool: myBool}', 'PGB:'],
     'class/constDecl':     ['struct testClass{const int: myConst <- 2}', 'PGB:'],
     'class/charDecl':      ['struct testClass{me char: myChar}', 'PGB:'],
     'class/baseDecls':     ['''
struct testClass{
    me int: myInt
    me string: myString
    me int32: myInt32
    me int64: myInt64
    me double: myDouble
    me uint32: myUint32
    me uint64: myUint64
    me bool: myBool <- false 
    const int: myConst <- 2
    me char: myChar
}''', 'PGB:',['class/simple', 'class/intDecl', 'class/strDecl', 'class/int32Decl', 'class/int64Decl', 'class/doubleDecl', 'class/uint32Decl', 'class/uint64Decl', 'class/boolDecl', 'class/constDecl', 'class/charDecl']],
#####################################################################################################
     #'class/strListDecl':  ['struct testClass{me string[list]: myStringList}', 'PGB:'],
     #'class/mapDecl':      ['struct testClass{me int[map string]: testMap}', 'PGB:'],
     #'class/multimapDecl':[],
     #'class/treeDecl':    [],
     #'class/graphDecl':   [],
     #const string: constStr <- "Hello"
     #const double: pi <- 3.14
     'class/funcDefn':          ['struct testClass{me int: myInt <- 7-3}', 'PGB:'],
     'class/funcDecl':          ['struct testClass{me void: runTest()<-{print("Function was called.")}}', 'PGBR:Function was called.'],
     'class/funcCallArgs':      ['struct testClass{me void: runTest()<-{testFunc2("Pass func arg.")}\nme void: testFunc2(me string: strArg)<-{print(strArg)}}', 'PGBR:Pass func arg.'],
     #'class/pureVirtualFunc':   ['struct testClass{me void: runTest()<-{me pureVirtualClass::derivedClass: DC\nDC.pureVirtualFunc ()}}\nstruct pureVirtualClass{me void: pureVirtualFunc()}\nstruct pureVirtualClass::derivedClass{me void: pureVirtualFunc()<-{print("Function was called.")}}', 'PGBR:Function was called.'],
     'class/funcDefaultParams': ['struct testClass{me void: runTest()<-{DefaultParams()}\nme void: DefaultParams(me string: defaultParam<-"Default func param1.  ",me string: defaultParam2<-"Default func param2. ")<-{print(defaultParam,defaultParam2)}}', 'PGBR:Default func param1.  Default func param2. '],
     'class/funcPassAndDefault':['struct testClass{me void: runTest()<-{PassAndDefault("Pass func arg.  ")}\nme void: PassAndDefault(me string: defaultParam<-"Default func param1.  ",me string: defaultParam2<-"Default func param2. ")<-{print(defaultParam,defaultParam2)}}', 'PGBR:Pass func arg.  Default func param2. '],
     'class/funcs':             ['''
struct testClass{
    me void: runTest()<-{
        testFunc2("Pass func arg.  ")
        me derivedClass: DC
        DC.pureVirtualFunc ()
        DefaultParams()
        PassAndDefault("Pass func arg.  ")
    }
    me void: testFunc2(me string: strArg)<-{print(strArg)}
    me void: DefaultParams(me string: defaultParam<-"Default func param1.  ",me string: defaultParam2<-"Default func param2. ")<-{
        print(defaultParam,defaultParam2)
    }
    me void: PassAndDefault(me string: defaultParam<-"Default func param1.  ",me string: defaultParam2<-"Default func param2. ")<-{
        print(defaultParam,defaultParam2)
    }
}
struct pureVirtualClass{
    me void: pureVirtualFunc()
}
struct derivedClass: inherits=pureVirtualClass{
    me void: pureVirtualFunc()<-{
        print("Function was called.")
    }
}
''', 'PGBR:Pass func arg.  Function was called.Default func param1.  Default func param2. Pass func arg.  Default func param2. ',['class/funcDefn','class/funcDecl','class/funcCallArgs', 'class/funcDefaultParams', 'class/funcPassAndDefault']],
#####################################################################################################
     'actions/varDecl':      ['struct testClass{me void: runTest()<-{me int: actionVarDecl}}', 'PGB:'],
     'actions/mapDecl':      ['struct testClass{me void: runTest()<-{me string[map string]:testMap}}', 'PGB:'],
     'actions/decls':        ['struct testClass{me void: runTest()<-{me int: actionVarDecl\nme string[map string]:testMap}}', 'PGB:',['actions/varDecl','actions/mapDecl']],
#####################################################################################################
     'actions/varAsgn':      ['struct testClass{me void: runTest()<-{me int: actionVarAsgn\nactionVarAsgn<-4567\nprint(actionVarAsgn)}}', 'PGBR:4567'],
     'actions/flagAsgn':     ['struct testClass{flag: isStart\nme void: runTest()<-{print(isStart)\nisStart<-true\nprint("-")\nprint(isStart)}}', 'PGBR:0-1'],
     'actions/modeAsgn':     ['struct testClass{me mode[small, medium, large]: myMode\nme void: runTest()<-{print(myModeStrings[myMode]+ "-")\nmyMode<- large\nprint(myModeStrings[myMode])}}', 'PGBR:small-large'],
     'actions/stringAsgn':   ['struct testClass{me void: runTest()<-{me string: actionStrAsgn\nactionStrAsgn<-"Hello"\nprint(actionStrAsgn)}}', 'PGBR:Hello'],
     'actions/mapAsgn':      ['struct testClass{me void: runTest()<-{me string[map string]:testMap\ntestMap["key0"]<-"value0"\nprint(testMap["key0"])}}', 'PGBR:value0'],
     #'actions/dictAsgn':
     #'actions/mapPush':     ['struct testClass{me void: runTest()<-{me string[map string]:testMap<-{"key":"value"}}}', 'PGB:'],
     'actions/assigns':        ['''
struct testClass{
    flag: isStart
    me mode[small, medium, large]: myMode
    me void: runTest()<-{
        me int: actionVarAsgn
        actionVarAsgn<-4567
        print(actionVarAsgn)
        print(isStart)
        print("-")
        isStart<-true
        print(isStart+ "-")
        print(myModeStrings[myMode]+ "-")
        myMode<- large
        print(myModeStrings[myMode]+ "-")
        me string: actionStrAsgn
        actionStrAsgn<-"Hello"
        print(actionStrAsgn+"-")
        me string[map string]:testMap
        testMap["key0"]<-"value0"
        print(testMap["key0"])
    }
}''', 'PGBR:45670-small-large-Hello-value0',['actions/varAsgn','actions/flagAsgn','actions/modeAsgn','actions/stringAsgn','actions/mapAsgn']],
#####################################################################################################
     'actions/conditional':  ['struct testClass{me void: runTest()<-{testFunc(true)}\nme void: testFunc(me bool: isTrue)<-{if (isTrue){print("true")}\nelse{print("false")}}}', 'PGB:'],
     'actions/switch':       ['struct testClass{me void: runTest()<-{me int:myInt<-3\nswitch(myInt){case 3:{print("3")}case 2:{print("2")}default:{print("default")}}}}', 'PGBR:3'],
     'actions/misc':         ['''
struct testClass{
    me void: runTest()<-{
        me int:myInt<-3
        testFunc(true)
        switch(myInt){
            case 3:{print("3")}
            case 2:{print("2")}
            default:{print("default")}
        }
    }
    me void: testFunc(me bool: isTrue)<-{
        if (isTrue){print("true ")}
        else{print("false ")}
    }
}''', 'PGBR:true 3',['actions/conditional','actions/switch']],
#####################################################################################################
# TODO: make tests for 'actions/repetitions':  'actions/rangeRep','actions/backRangeRep','actions/listRep','actions/backListRep','actions/listKeyRep','actions/mapRep','actions/mapKeyRep','actions/deleteMapRep','actions/deleteListRep'
#####################################################################################################

}

tags = """BuildCmd = ""
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
    try:
        os.makedirs(dirToGen)
    except OSError as exception:
        if exception.errno != errno.EEXIST: raise

def writeFile(path, fileName, testString):
    makeDir(path)
    makeDir(path+"/Resources")
    pathName = path + os.sep + fileName
    fo=open(pathName, 'w')
    fo.write(testString)
    fo.close()

def runCmd(workingDirectory, runString):
    pipe = subprocess.Popen(runString, cwd=workingDirectory, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    return out, err

def RunCodeDogPrg(testString):
    path = "xlatorTests"
    fileName = "testXlator.dog"
    writeFile(path, fileName, testString)
    runString ="codeDog " + fileName
    workingDirectory = os.getcwd() + "/" + path
    #print"    workingDirectory: ", workingDirectory
    #print"    runString: " ,runString
    out, err = runCmd(workingDirectory, runString)
    return out, err

def ExecCodeDogTest(testSpec, buildSpec):
    global tags
    global runSpec
    global workingDirectory
    testString = buildSpec+"\n"
    reqSpec =""
    if(len(testSpec)>1):
        colonPos = testSpec[1].find(':')
    else:
        print("Missing Test Spec")
        exit(0)
    willRun = False
    if(colonPos):
        reqSpec = testSpec[1][(colonPos+1):]
        testSpec[1] = testSpec[1][:(colonPos)]
    if(testSpec[1]=='PGB'):
        testString += tags.replace('<runCodeGoesHere>', '``') + "\n"
    elif(testSpec[1]=='PGBR'):
        willRun = True
        testString += tags.replace('<runCodeGoesHere>', '`\nme testClass: TC\nTC.runTest()\n`') + "\n"
    else:
        print(("Unknown test spec: ",testSpec[1]))
        exit(0)

    testString += testSpec[0] + "\n"
    out, err = RunCodeDogPrg(testString)
    #print(("out: ", out))
    if out:
        decodedOut = bytes.decode(out)
        if(decodedOut.find('Marker: Parse Successful')==-1):
            print(decodedOut)
            return "***Parse Fail***"
        if (decodedOut.find('Marker: Code Gen Successful')==-1):
            return "***Code Gen Fail***"
        buildMarker = decodedOut.find('Marker: Build Successful')
        if (buildMarker==-1):
            return "***Build Fail***"
        if(not willRun):
            return "Success"
        else:
            out, err = runCmd(runDirectory, runSpec)
            decodedOut = bytes.decode(out)
            #print("out: ", out)
            if (reqSpec != ""):
                if (reqSpec == decodedOut):
                    return "Success"
                else:
                    return "***Run Fail*** expected '"+str(reqSpec)+"' not '"+decodedOut+"'"
    else: return "***Error: no out***"

def runDeps(testKey):
    global buildSpec
    global testDefinitions
    depsList=[]
    depsReportText = ""
    if (len(testDefinitions[testKey])>2):
        depsList = testDefinitions[testKey][2]
    for dep in depsList:
        testResult = ExecCodeDogTest(testDefinitions[dep], buildSpec)
        depsReportText +=  "        " + dep + " : "+testResult+  "\n"
    return depsReportText


def runListedTests(testsToRun):
    global buildSpec
    global testDefinitions
    reportText = ""
    for testKey in testsToRun:
        print(("Running test: ", testKey))
        testResult = ExecCodeDogTest(testDefinitions[testKey], buildSpec)
        #print "testResult: ", testKey, ":  ", testResult
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

###################################
# Get command line: tests and xlator name
if len(sys.argv)==1:
    print(("\nUsage:", sys.argv[0], "<xlatorName> [test-names...]\n"))
    exit(0)

xlatorName = sys.argv[1]
testListSpec = sys.argv[2:]

workingDirectory = os.getcwd() + "/xlatorTests"
if (xlatorName == "cpp"):
    buildSpec = "LinuxBuild: Platform='Linux' CPU='amd64' Lang='CPP' optimize='speed';"
    runSpec = "./testXlator"
    runDirectory = workingDirectory + "/LinuxBuild"
elif(xlatorName == "swing" or xlatorName == "java"):
    buildSpec = "SwingBuild: Platform='Java' CPU='JavaVM' Lang='Java' optimize='speed';"
    runSpec = "java GLOBAL"
    runDirectory = workingDirectory + "/SwingBuild"
elif(xlatorName == "swift"):
    buildSpec = "iPhoneBuild: Platform='IOS' CPU='amd64' Lang='Swift' optimize='speed';"
    runSpec = ".build/debug/testXlator"
    runDirectory = workingDirectory + "/SwiftBuild/testXlator"
else:
    print(("UNKNOWN XLATOR: ", xlatorName))
    exit(0)

testsToRun = gatherListOfTestsToRun(testListSpec)
#print "testsToRun: ",testsToRun
reportText = runListedTests(testsToRun)
print("********** T E S T    R E S U L T S **********")
print(reportText)
print("**********************************************")
