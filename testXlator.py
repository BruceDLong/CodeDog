#!/usr/bin/env python
# CodeDog Xlator tester

import sys;  sys.dont_write_bytecode = True

testDefinitions = [
     ["class/simple",  "struct emptyClass{ }", "PB"],
     ['class/intDecl', 'struct tclass{me int: A}', 'PB'],
     ['class/strDecl', 'struct tclass{me string: A}', 'PB'],
     ['class/funcs',   'struct tclass{me void: f(me int: in){print("In:", in)}}', 'PB:In'],

]

RunCodeDogPrg(testString):
    pass

def ExecCodeDogTest(TestSpec, buildSpec):
    testString = buildSpec+"\n"
    testString += tagSet[testSpec.tagSetID] + "\n"
    testString += testSpec.testCode + "\n"

    testResultData = RunCodeDogPrg(testString)
    # Check for parse success or error mesg

    # Check for build success or error mesg

    # Cut and verify resulting text Acc a short report

    return "pass"


def runListedTests(testsToRun):
    for test in testsToRun:
        ExecCodeDogTest(TestSpec, buildSpec)

def gatherListOfTestsToRun(keywordList):
    pass


###################################
# Get command line: tests and xlator name
if len(sys.argv)==1:
    print "\nUsage:", sys.argv[0], "<xlatorName> [test-names...]\n"
    exit(0)

xlatorName = sys.argv[1]
testListSpec = sys.argv[2:]

testsToRun = gatherListOfTestsToRun(testListSpec)
reportText = runListedTests(testsToRun)
print reportText
