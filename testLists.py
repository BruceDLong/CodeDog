#!/usr/bin/env python3
# CodeDog Xlator tester
import os
from progSpec import cdlog
import errno
import subprocess
import sys;  sys.dont_write_bytecode = True
from datetime import date
buildSpec = ""
runSpec = ""
workingDirectory = ""
runDirectory = ""

testDefinitions = {
#####################################################################################################
     'actions/emptyList':    ['struct testClass{\nme void: runTest()<-{\nme List<me int>:wrappedList\nprint("isEmpty:"+wrappedList.isEmpty())\n}\n}', 'PGBR:isEmpty:true'],
     'lists/lists':  ['''
struct testClass{
    me List<me int>: classList
    we List<me string>: weList

    me void: runTest()<-{
        me List<me int>:wrappedList
        print(" isEmpty:"+toString(wrappedList.isEmpty()))
        wrappedList.pushLast(1)
        wrappedList.pushLast(3)
        wrappedList.pushFirst(5)
        wrappedList.pushFirst(6)
        wrappedList.pushFirst(8)
        wrappedList.pushFirst(4)
        wrappedList.pushFirst(7)
        withEach item in wrappedList{
            print(toString(item))
        }
        me int: valAt <- wrappedList.at(2)
        print("valAt:"+ toString(valAt))
        me int: firstItm <- wrappedList.first()
        print("firstItm:"+ toString(firstItm))
        me int: lastItm <- wrappedList.last()
        print("lastItm:"+ toString(lastItm))
        me int: firstPop <-wrappedList.popFirst()
        me int: lastPop  <-wrappedList.popLast()
        print("firstPop:"+ toString(firstPop))
        print("lastPop:"+ toString(lastPop))
        print("Size:"+ toString(wrappedList.size()))
        withEach item2 in wrappedList{
            print("   item:"+ toString(item2))
        }
        wrappedList.clear()
        print("Size after clear:"+ toString(wrappedList.size()))
        me List<our string>: ourStringList
        me List<me string>: meStringList
        me List<me timeValue>: meTimeValList
    }
    void: testPassList(me List<me string>: listToPass)<-{}
}''', 'PGBR: isEmpty:true7486513valAt:8firstItm:7lastItm:3firstPop:7lastPop:3Size:5   item:4   item:8   item:6   item:5   item:1Size after clear:0',
        ['','']],
###################################################################################################
     'class/charDecl':      ['struct testClass{me char: myChar}', 'PGB:'],
     'maps/maps':     ['''
struct gloop<key, value>{
    me int: i
    me key: k
    our value: val
}
struct testClass{
    me gloop<me int, me string>: gloopList
    me void: runTest()<-{
        me Map<me int, me string>: mapIntString
        print(" isEmpty:"+toString(mapIntString.isEmpty()))
        mapIntString.insert(0,"aa")
        mapIntString.insert(1,"bb")
        mapIntString.insert(2,"cc")
        print(" ",mapIntString.at(1))
        print(" ",mapIntString.first())
        print(" ",mapIntString.size())
        print(" ",mapIntString.last())
        withEach item in mapIntString{print(item)}
        mapIntString.clear()
        print(" ",mapIntString.size())

    }
}''', 'PGBR: isEmpty:true bb aa 3 ccaabbcc 0',
        ['', '']],

###################################################################################################
###################################################################################################
     'class/charDecl':      ['struct testClass{me char: myChar}', 'PGB:'],
     'maps/maps2':     ['''
struct testClass{
    me int: runTest()<-{
        me Map<me string, me int>: mapStringInt
        print(" isEmpty:"+toString(mapStringInt.isEmpty()))
        mapStringInt.insert("aa",0)
        mapStringInt.insert("bb",1)
        mapStringInt.insert("cc",2)
        withEach item in mapStringInt{print(item)}
        print(" at(cc)=",mapStringInt.at("cc"))
        return(mapStringInt.at("cc"))
    }
}''', 'PGBR: isEmpty:true012 at(cc)=2',
        ['', '']],

###################################################################################################
# TODO: make tests for 'actions/repetitions':  'actions/rangeRep','actions/backRangeRep','actions/listRep','actions/backListRep','actions/listKeyRep','actions/mapRep','actions/mapKeyRep','actions/deleteMapRep','actions/deleteListRep'
     'actions/rangeRep':     ['struct testClass{me void: runTest()<-{withEach spec in RANGE(2..6){print(spec," ")}}}', 'PGBR:2 3 4 5 '],
     'actions/repetitions':  ['''
struct testClass{
    me void: runTest()<-{
        withEach spec in RANGE(2..6) {print(spec," ")}
        withEach RB in Backward RANGE(2..6) {print(RB," ")}
        me List<me int>:testList<-[2,13,-22,188]
        withEach T in testList {print(T," ")}
        me List<me int>:testListBackward<-[2,13,-22,188]
        withEach TB in Backward testListBackward {print(TB," ")}
        me List<me int>:testKeyList<-[2,3,5,8,13,21]
        withEach TK in testKeyList {print(TK_key,"-", TK, " ")}
        me Map<me string, me string>:testMap
        testMap["E"]<-"every"\ntestMap["G"]<-"good"\ntestMap["B"]<-"boy"\ntestMap["D"]<-"does"\ntestMap["F"]<-"fine"
        withEach M in testMap {print(M," ")}
        me Map<me string, me string>:testMapKey
        testMapKey["E"]<-"every"\ntestMapKey["G"]<-"good"\ntestMapKey["B"]<-"boy"\ntestMapKey["D"]<-"does"\ntestMapKey["F"]<-"fine"
        withEach MK in testMapKey {print(MK_key,"-",MK," ")}
        me List<me int>:testDelList<-[2,3,5,8,13,21]
        withEach TD in testDelList {
            if(TD_key==3){
                testDelList.erase(TD_key)
                TDIdx<-TDIdx-1
            }else{print(TD, " ")}
        }
    }
}''', 'PGBR:2 3 4 5 5 4 3 2 2 13 -22 188 188 -22 13 2 0-2 1-3 2-5 3-8 4-13 5-21 boy does every fine good B-boy D-does E-every F-fine G-good 2 3 5 13 21 ',
    ['','']],
###################################################################################################
}

tags = """BuildCmd = ""
Title = "Infomage - DataDog"
FileName = "testXlator"
Version = "0.1"
CopyrightMesg = "Copyright (c) 2015-2016 Bruce Long"
Authors = "Bruce Long"
Description = "DataDog gives you the numbers of your life."
ProgramOrLibrary = "program"
featuresNeeded = [List]
LicenseText = `This file is part of the "Proteus suite" All Rights Reserved.`
runCode=<runCodeGoesHere>"""

def makeDir(dirToGen):
    try:
        os.makedirs(dirToGen)
    except OSError as exception:
        if exception.errno != errno.EEXIST: raise

def clearErrorFile():
    makeDir("xlatorTests")
    erfClear = open("xlatorTests/failedTests.txt","w")
    erfClear.close()

def writePrepend(fileName, testName):
    with open(fileName, 'r+') as f:
        content = f.read()
        f.seek(0,0) # add global counter to stop the reverse order of the tests?
        f.write(testName.rstrip('\r\n') + "\n" + content)

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

def ExecCodeDogTest(testSpec, buildSpec, testName,toPrint):
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
    if(testSpec[1]=='PGBR'):
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
            if(toPrint):
                errorFile = open("xlatorTests/failedTests.txt","a")
                errorFile.write("***\nParse Fail***\n")
                errorFile.write(testName + "\n")
                errorFile.write(testSpec[0]+"\n\n")
                errorFile.close()
            #print(decodedOut)
            return "***Parse Fail***"
        if (decodedOut.find('Marker: Code Gen Successful')==-1):
            if(toPrint):
                errorFile = open("xlatorTests/failedTests.txt","a")
                errorFile.write("***\nCode Gen Fail***\n")
                errorFile.write(testName + "\n")
                errorFile.write(testSpec[0]+"\n\n")
                errorFile.close()
            return "***Code Gen Fail***"
        buildMarker = decodedOut.find('Marker: Build Successful')
        if (buildMarker==-1):
            if(toPrint):
                errorFile = open("xlatorTests/failedTests.txt","a")
                errorFile.write("\n***Build Fail***\n")
                errorFile.write(testName + "\n")
                errorFile.write(testSpec[0]+"\n\n")
                errorFile.close()
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
        testResult = ExecCodeDogTest(testDefinitions[dep], buildSpec,dep,True)
        depsReportText +=  "        " + dep + " : "+testResult+  "\n"
        if(testResult != "Success"):
            writePrepend("xlatorTests/failedTests.txt",dep)
    return depsReportText

def runListedTests(testsToRun):
    global buildSpec
    global testDefinitions
    clearErrorFile()
    reportText = ""
    for testKey in testsToRun:
        #print(("Running test: ", testKey))
        testResult = ExecCodeDogTest(testDefinitions[testKey], buildSpec, testKey,False)
        print("testResult: ", testKey, ":  ", testResult)
        reportText+= testKey + ": "+testResult+  "\n"
        #if(testResult!="Success"):
            #depsReportText = runDeps(testKey)
            #reportText+= depsReportText
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
    buildSpec += "//SwingBuild: Platform='Java' CPU='JavaVM' Lang='Java' optimize='speed';"
    runSpec = "./testXlator"
    runDirectory = workingDirectory + "/LinuxBuild"
elif(xlatorName == "swing" or xlatorName == "java" or xlatorName == "Java"):
    buildSpec  = "SwingBuild: Platform='Java' CPU='JavaVM' Lang='Java' optimize='speed';"
    buildSpec += "//LinuxBuild: Platform='Linux' CPU='amd64' Lang='CPP' optimize='speed';"
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
reportText = runListedTests(testsToRun)
print("********** T E S T    R E S U L T S **********")
print(reportText)
print("**********************************************")
writePrepend("xlatorTests/failedTests.txt", "Failed tests: \n")
writePrepend("xlatorTests/failedTests.txt","Run on: "+ str(date.today())+"\n\n")

 # TODO: make contained List types default to owner me when no owner given
 # TODO: test iterateRangeContainerStr
