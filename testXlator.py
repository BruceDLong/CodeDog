#!/usr/bin/env python
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
    me bool: myBool
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
     'class/pureVirtualFunc':   ['struct testClass{me void: runTest()<-{me pureVirtualClass::derivedClass: DC\nDC.pureVirtualFunc ()}}\nstruct pureVirtualClass{me void: pureVirtualFunc()}\nstruct pureVirtualClass::derivedClass{me void: pureVirtualFunc()<-{print("Function was called.")}}', 'PGBR:Function was called.'],
     'class/funcDefaultParams': ['struct testClass{me void: runTest()<-{DefaultParams()}\nme void: DefaultParams(me string: defaultParam<-"Default func param1.  ",me string: defaultParam2<-"Default func param2. ")<-{print(defaultParam,defaultParam2)}}', 'PGBR:Default func param1.  Default func param2. '],
     'class/funcPassAndDefault':['struct testClass{me void: runTest()<-{PassAndDefault("Pass func arg.  ")}\nme void: PassAndDefault(me string: defaultParam<-"Default func param1.  ",me string: defaultParam2<-"Default func param2. ")<-{print(defaultParam,defaultParam2)}}', 'PGBR:Pass func arg.  Default func param2. '],
     'class/funcs':             ['''
struct testClass{
    me void: runTest()<-{
        testFunc2("Pass func arg.  ")
        me pureVirtualClass::derivedClass: DC\nDC.pureVirtualFunc ()
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
struct pureVirtualClass::derivedClass{
    me void: pureVirtualFunc()<-{
        print("Function was called.")
    }
}
''', 'PGBR:Pass func arg.  Function was called.Default func param1.  Default func param2. Pass func arg.  Default func param2. ',['class/funcDefn','class/funcDecl','class/funcCallArgs','class/pureVirtualFunc', 'class/funcDefaultParams', 'class/funcPassAndDefault']],
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
     'actions/rangeRep':     ['struct testClass{me void: runTest()<-{withEach R in RANGE(2..6):{print(R," ")}}}', 'PGBR:2 3 4 5 '],
     'actions/backRangeRep': ['struct testClass{me void: runTest()<-{withEach RB in Backward RANGE(2..6):{print(RB," ")}}}', 'PGBR:5 4 3 2 '],
     'actions/listRep':      ['struct testClass{me void: runTest()<-{me int[list]:testList<-[2,13,-22,188]\nwithEach T in testList:{print(T," ")}}}', 'PGBR:2 13 -22 188 '],
     'actions/backListRep':  ['struct testClass{me void: runTest()<-{me int[list]:testListBackward<-[2,13,-22,188]\nwithEach TB in Backward testListBackward:{print(TB," ")}}}', 'PGBR:188 -22 13 2 '],
     'actions/listKeyRep':   ['struct testClass{me void: runTest()<-{me int[list]:testKeyList<-[2,3,5,8,13,21]\nwithEach TK in testKeyList:{print(TK_key,"-", TK, " ")}}}', 'PGBR:0-2 1-3 2-5 3-8 4-13 5-21 '],
     'actions/mapRep':       ['struct testClass{me void: runTest()<-{me string[map string]:testMap\ntestMap["E"]<-"every"\ntestMap["G"]<-"good"\ntestMap["B"]<-"boy"\ntestMap["D"]<-"does"\ntestMap["F"]<-"fine"\nwithEach M in testMap:{print(M," ")}}}', 'PGBR:boy does every fine good '],
     'actions/mapKeyRep':    ['struct testClass{me void: runTest()<-{me string[map string]:testMapKey\ntestMapKey["E"]<-"every"\ntestMapKey["G"]<-"good"\ntestMapKey["B"]<-"boy"\ntestMapKey["D"]<-"does"\ntestMapKey["F"]<-"fine"\nwithEach MK in testMapKey:{print(MK_key,"-",MK," ")}}}', 'PGBR:B-boy D-does E-every F-fine G-good '],
     'actions/deleteMapRep': ['struct testClass{me void: runTest()<-{me string[map string]:testMapDel\ntestMapDel["E"]<-"every"\ntestMapDel["G"]<-"good"\ntestMapDel["B"]<-"boy"\ntestMapDel["D"]<-"does"\ntestMapDel["F"]<-"fine"\nwithEach MD in testMapDel:{if(MD=="boy"){testMapDel.erase(MD_key)}else{print(MD_key,"-",MD," ")}}}}', 'PGBR:D-does E-every F-fine G-good '],
     'actions/deleteListRep':['struct testClass{me void: runTest()<-{me int[list]:testDelList<-[2,3,5,8,13,21]\nwithEach TD in testDelList:{if(TD_key==3){testDelList.erase(TD_key)\nTDIdx<-TDIdx-1}\nelse{print(TD, " ")}}}}', 'PGBR:2 3 5 13 21 '],
     'actions/repetitions':  ['''
struct testClass{
    me void: runTest()<-{
        withEach R in RANGE(2..6):{print(R," ")}
        withEach RB in Backward RANGE(2..6):{print(RB," ")}
        me int[list]:testList<-[2,13,-22,188]
        withEach T in testList:{print(T," ")}
        me int[list]:testListBackward<-[2,13,-22,188]
        withEach TB in Backward testListBackward:{print(TB," ")}
        me int[list]:testKeyList<-[2,3,5,8,13,21]
        withEach TK in testKeyList:{print(TK_key,"-", TK, " ")}
        me string[map string]:testMap\ntestMap["E"]<-"every"\ntestMap["G"]<-"good"\ntestMap["B"]<-"boy"\ntestMap["D"]<-"does"\ntestMap["F"]<-"fine"
        withEach M in testMap:{print(M," ")}
        me string[map string]:testMapKey\ntestMapKey["E"]<-"every"\ntestMapKey["G"]<-"good"\ntestMapKey["B"]<-"boy"\ntestMapKey["D"]<-"does"\ntestMapKey["F"]<-"fine"
        withEach MK in testMapKey:{print(MK_key,"-",MK," ")}
        me string[map string]:testMapDel\ntestMapDel["E"]<-"every"\ntestMapDel["G"]<-"good"\ntestMapDel["B"]<-"boy"\ntestMapDel["D"]<-"does"\ntestMapDel["F"]<-"fine"
        withEach MD in testMapDel:{if(MD=="boy"){testMapDel.erase(MD_key)}else{print(MD_key,"-",MD," ")}}
        me int[list]:testDelList<-[2,3,5,8,13,21]\nwithEach TD in testDelList:{if(TD_key==3){testDelList.erase(TD_key)\nTDIdx<-TDIdx-1}\nelse{print(TD, " ")}}
    }
}''', 'PGBR:BB',['actions/rangeRep','actions/backRangeRep','actions/listRep','actions/backListRep','actions/listKeyRep','actions/mapRep','actions/mapKeyRep','actions/deleteMapRep','actions/deleteListRep']],
#####################################################################################################
     
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
    #programmatically run "codeDog " + name of saved file then run file capture output search for 3 strings
    runString ="codeDog " + fileName 
    workingDirectory = os.getcwd() + "/" + path
    #print"workingDirectory *** runString: ", workingDirectory, " *** " ,runString
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
        print"Missing Test Spec"
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
        print "Unknown test spec: ",testSpec[1]
        exit(0)

    testString += testSpec[0] + "\n"
    out, err = RunCodeDogPrg(testString)
    print "out: ", out
    if out: 
        if(out.find('Marker: Parse Successful')==-1):
            return "***Parse Fail***"
        if (out.find('Marker: Code Gen Successful')==-1):
            return "***Code Gen Fail***"
        buildMarker = out.find('Marker: Build Successful')
        if (buildMarker==-1):
            return "***Build Fail***"
        if(not willRun):
            return "Success"
        else: 
            out, err = runCmd(runDirectory, runSpec)
            #print "out: ", out
            if (reqSpec != ""):
                if (reqSpec == out):
                    return "Success"
                else:
                    return "***Run Fail*** expected '"+reqSpec+"' not '"+out+"'"
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
        depsReportText +=  "        " + dep + ": "+testResult+  "\n"
    return depsReportText

    
def runListedTests(testsToRun):
    global buildSpec
    global testDefinitions
    reportText = ""
    for testKey in testsToRun:
        print "Running test: ", testKey
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
    print "\nUsage:", sys.argv[0], "<xlatorName> [test-names...]\n"
    exit(0)

xlatorName = sys.argv[1]
testListSpec = sys.argv[2:]

workingDirectory = os.getcwd() + "/xlatorTests"
if (xlatorName == "cpp"):
    buildSpec = "LinuxBuild: Platform='Linux' CPU='amd64' Lang='CPP' optimize='speed';"
    runSpec = "./testXlator"
    runDirectory = workingDirectory + "/LinuxBuild"
elif(xlatorName == "swing"):
    buildSpec = "SwingBuild: Platform='Java' CPU='JavaVM' Lang='Java' optimize='speed';"
    runSpec = "java GLOBAL"
    runDirectory = workingDirectory + "/SwingBuild"
else:
    print "UNKNOWN XLATOR: ", xlatorName
    exit(0)

testsToRun = gatherListOfTestsToRun(testListSpec)
#print "testsToRun: ",testsToRun
reportText = runListedTests(testsToRun)
print "********** T E S T    R E S U L T S **********"
print reportText
print "**********************************************"
