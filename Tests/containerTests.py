#!/usr/bin/env python3
# CodeDog tests for Containers
import os
import errno
import subprocess
import sys;  sys.dont_write_bytecode = True
import copy
from datetime import date
buildSpec = ""
runSpec = ""
workingDirectory = ""
runDirectory = ""

testDefinitions = {
#####################################################################################################
'lists': ['''
struct testClass{
    me List<me int>: classList
    we List<me string>: weList

    me void: runTest()<-{
        me List<me int>:wrappedList
        print(" isEmpty:"+toString(wrappedList.isEmpty()))
        wrappedList.append(1)
        wrappedList.append(3)
        wrappedList.prepend(5)
        wrappedList.prepend(6)
        wrappedList.prepend(8)
        wrappedList.prepend(4)
        wrappedList.prepend(7)
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
}''', 'PGBR: isEmpty:true7486513valAt:8firstItm:7lastItm:3firstPop:7lastPop:3Size:5   item:4   item:8   item:6   item:5   item:1Size after clear:0'],
###################################################################################################
'maps1': ['''
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
}''', 'PGBR: isEmpty:true bb aa 3 ccaabbcc 0'],
###################################################################################################
'maps2': ['''
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
}''', 'PGBR: isEmpty:true012 at(cc)=2'],
###################################################################################################
'listReps': ['''
struct testClass{
    me void: runTest()<-{
        print("RANGE:")
        withEach spec in RANGE(2..6) {print(spec," ")}
        print(" RANGEBKWD:")
        withEach RB in Backward RANGE(2..6) {print(RB," ")}
        me List<me int>:testList<-[2,13,-22,188]
        print(" LIST:")
        withEach T in testList {print(T," ")}
        me List<me int>:testListBackward<-[2,13,-22,188]
        print(" LISTBKWD:")
        withEach TB in Backward testListBackward {print(TB," ")}
        me List<me int>:testKeyList<-[2,3,5,8,13,21]
        print(" LISTKEY:")
        withEach TK in testKeyList {print(TK_key,"-", TK, " ")}
     }
}''', 'PGBR:RANGE:2 3 4 5  RANGEBKWD:5 4 3 2  LIST:2 13 -22 188  LISTBKWD:188 -22 13 2  LISTKEY:0-2 1-3 2-5 3-8 4-13 5-21 '],
###################################################################################################
'mapReps': ['''
struct testClass{
    me void: runTest()<-{
        me Map<me string, me string>:testMap
        testMap["E"]<-"every"\ntestMap["G"]<-"good"\ntestMap["B"]<-"boy"\ntestMap["D"]<-"does"\ntestMap["F"]<-"fine"
        withEach M in testMap {print(M," ")}
        me Map<me string, me string>:testMapKey
        testMapKey["E"]<-"every"\ntestMapKey["G"]<-"good"\ntestMapKey["B"]<-"boy"\ntestMapKey["D"]<-"does"\ntestMapKey["F"]<-"fine"
        withEach MK in testMapKey {print(MK_key,"-",MK," ")}
    }
}''', 'PGBR:boy does every fine good B-boy D-does E-every F-fine G-good '],
###################################################################################################
'twoMaps': ['''
struct testClass{
    me void: runTest()<-{
        me Map<me string, me string>:testMapStrStr
        me Map<me string, me int>:testMapStrInt
        testMapStrStr.insert("aa","zero")
        testMapStrStr.insert("bb","one")
        testMapStrStr.insert("cc","two")
        testMapStrInt.insert("aa",0)
        testMapStrInt.insert("bb",1)
        testMapStrInt.insert("cc",2)
        withEach strItm in testMapStrStr{print(strItm)}
        withEach intItm in testMapStrInt{print(intItm)}
    }
}''', 'PGBR:zeroonetwo012'],
###################################################################################################
'mapWraps': ['''
struct wrappedStr: wraps = string{}
struct testClass{
    me void: runTest()<-{
        me Map<me string, me wrappedStr>: testMapStringMyString
        testMapStringMyString.insert("aa","zero")
        testMapStringMyString.insert("bb","one")
        testMapStringMyString.insert("cc","two")
        withEach strItm in testMapStringMyString{print(strItm)}
    }
}''', 'PGBR:zeroonetwo'],
###################################################################################################
'mapReps2': ['''
struct txtOut{
    me bool: isHidden
    me int: val

    void: output() <- {
        print(" at:", val)
    }
    none: txtOut(me bool: _isHidden, me int: _val) <- {
        isHidden <- _isHidden
        val      <- _val
    }
}
struct testClass{
    me Map<me int, their txtOut>: txtsOut
    me void: runTest()<-{
        their txtOut: Tzero{false, 0}
        their txtOut: Tone{false, 1}
        their txtOut: Ttwo{false, 2}
        txtsOut.insert(0,Tzero)
        txtsOut.insert(1,Tone)
        txtsOut.insert(2,Ttwo)
        withEach itm in txtsOut{
            if(!itm.isHidden){
                itm.output()
            }
        }
    }
}''', 'PGBR: at:0 at:1 at:2'],
###################################################################################################
'multimap': ['''
struct testClass{
    me void: runTest()<-{
        me Multimap<me int, me string>: mapIntString
        print(" isEmpty:"+toString(mapIntString.isEmpty()))
        mapIntString.insert(0,"aa")
        mapIntString.insert(1,"bb")
        mapIntString.insert(1,"qq")
        mapIntString.insert(2,"cc")
        print(" ",mapIntString.first())
        print(" ",mapIntString.size())
        print(" ",mapIntString.last())
        withEach item in mapIntString from 1 to 1{print(" [1..1]"+item)}
        mapIntString.popFirst()
        mapIntString.clear()
        print(" ",mapIntString.size())
    }
}''', 'PGBR: isEmpty:true aa 4 cc [1..1]bb [1..1]qq 0'],
###################################################################################################
'iterator': ['''
struct testClass{
    me void: runTest()<-{
        me Map<me int, me string>: testMap
        testMap.insert(1, "A")
        itr Map<me int, me string>: testItr <- testMap.find(1)
        if(testItr == testMap.end()){print("End")}
        else{print("Found")}
    }
}''', 'PGBR:Found'],
###################################################################################################
'mapAdd': ['''
struct testClass{
    me void: runTest()<-{
        me Map<me int, me string>: mapIntString
        mapIntString.insert(5,"ff")
        mapIntString.insert(3,"dd")
        mapIntString.insert(4,"ee")
        mapIntString.insert(1,"bb")
        mapIntString.insert(2,"cc")
        mapIntString.insert(0,"aa")
        withEach item in mapIntString{print(item)}
    }
}''', 'PGBR:aabbccddeeff',
        ['', '']],
###################################################################################################
}

tags = """BuildCmd = ""
Title = "Infomage - DataDog"
FileName = "containerTests"
Version = "0.1"
CopyrightMesg = "Copyright (c) 2015-2016 Bruce Long"
Authors = "Bruce Long"
Description = "DataDog gives you the numbers of your life."
ProgramOrLibrary = "program"
featuresNeeded = [List, Multimap]
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
    fileName = "containerTests.dog"
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

def runListedTests(testsToRun):
    global buildSpec
    global testDefinitions
    clearErrorFile()
    print('________________________________\n'+xlatorLabel)
    reportText = ""
    for testKey in testsToRun:
        #print(("Running test: ", testKey))
        testResult = ExecCodeDogTest(copy.copy(testDefinitions[testKey]), buildSpec, testKey,False)
        print("testResult: ", testKey, ":\t", testResult)
        reportText+= testKey + ": "+testResult+  "\n"
    return reportText

def gatherListOfTestsToRun(keywordList):
    global testDefinitions
    testList = []
    if len(keywordList)>0:
        testList = keywordList
    else:
        for key in testDefinitions:
            testList.append(key)
    return testList

def getCPPTest():
    global xlatorLabel
    global buildSpec
    global runSpec
    global runDirectory
    global workingDirectory
    xlatorLabel = 'TESTING: CPP'
    buildSpec = "LinuxBuild: Platform='Linux' Lang='CPP';\n"
    buildSpec += "//SwingBuild: Platform='Swing' Lang='Java';\n"
    buildSpec += "//SwiftBuild: Platform='Swift' Lang='Swift';"
    runSpec = "./containerTests"
    runDirectory = workingDirectory + "/LinuxBuild"
    runListedTests(testsToRun)

def getJavaTest():
    global xlatorLabel
    global buildSpec
    global runSpec
    global runDirectory
    global workingDirectory
    xlatorLabel = 'TESTING: JAVA'
    buildSpec = "SwingBuild: Platform='Swing' Lang='Java';\n"
    buildSpec += "//LinuxBuild: Platform='Linux' Lang='CPP';\n"
    buildSpec += "//SwiftBuild: Platform='Swift' Lang='Swift';"
    runSpec = "java GLOBAL"
    runDirectory = workingDirectory + "/SwingBuild"
    runListedTests(testsToRun)

def getSwiftTest():
    global xlatorLabel
    global buildSpec
    global runSpec
    global runDirectory
    global workingDirectory
    xlatorLabel = 'TESTING: SWIFT'
    buildSpec = "SwiftBuild: Platform='Swift' Lang='Swift';\n"
    buildSpec += "//SwingBuild: Platform='Swing' Lang='Java';\n"
    buildSpec += "//LinuxBuild: Platform='Linux' Lang='CPP';"
    runSpec = "./containerTests"
    runDirectory = workingDirectory + "/SwiftBuild"
    runListedTests(testsToRun)

###################################
# Get command line: tests and xlator name
if len(sys.argv)==1:
    print(("\nUsage:", sys.argv[0], "<xlatorName> [test-names...]\n"))
    exit(0)

xlatorName   = sys.argv[1]
testListSpec = sys.argv[2:]
xlatorLabel  = ''
testsToRun = gatherListOfTestsToRun(testListSpec)
workingDirectory = os.getcwd() + "/xlatorTests"

if (xlatorName == "all"):
    getCPPTest()
    getJavaTest()
    getSwiftTest()
elif (xlatorName == "cpp"):
    getCPPTest()
elif(xlatorName == "swing" or xlatorName == "java" or xlatorName == "Java"):
    getJavaTest()
elif(xlatorName == "swift" or xlatorName == "Swift"):
    getSwiftTest()
else:
    print(("UNKNOWN XLATOR: ", xlatorName))
    exit(0)

writePrepend("xlatorTests/failedTests.txt", "Failed tests: \n")
writePrepend("xlatorTests/failedTests.txt","Run on: "+ str(date.today())+"\n\n")

 # TODO: make contained List types default to owner me when no owner given
 # TODO: test iterateRangeContainerStr
