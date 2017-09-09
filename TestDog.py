# Code dog module for generating unit tests

# TODO: Capture and analyze the stdout
# TODO: Add command line options: -L: List only, -f: Run failed tests, -t: <list of tests>, also, report options and crash-testing / multi-threaded testing
# TODO: Add timing, timeouts and time requirements

import progSpec
import codeDogParser

def setResultCode():

    testMacros = r'''
#define BAIL() <% return()%>
#define FAIL(text) <%{T_TEST_BUFF <- T_TEST_BUFF + text+"\n" Tstat<-"F" BAIL()}%>     /- Print the text, mark the test failed, end its execution.
#define CAPTURE(expr) <%{INFO("expr = " + expr)}%>                                 /- Show the expression with INFO
#define REQUIRE(expr) <%{if(!(expr)) {FAIL("The requirement 'expr' failed: " + BlowPOP(expr) )}}%>                     /- If the expression fails, show its value with FAIL().
#define CHECK(expr)   <%{if(!(expr)) {CHK_FAIL("expr = " + expr)}}%>                 /- If the expression fails, show its value with CHK_FAIL().
    '''

    testResultUtilities = r'''

    struct GLOBAL {
        me int: T_NUM_FAILS <- 0
        me int: T_total <- 0
        me string: T_MESG_BUFF <- ""
        me string: T_TEST_BUFF <- ""
        me string: Tstat <- ""

        void: INFO(me string: text) <- {T_TEST_BUFF <- T_TEST_BUFF + text+"\n"}                               /- Buffer text and print it if the test fails.
        void: WARN(me string: text) <- {T_TEST_BUFF <- T_TEST_BUFF + text+"\n" if(Tstat=="."){Tstat<-"W"}}    /- Print text even if the test does not fail.
        void: CHK_FAIL(me string: text) <- {Tstat<-"F"  T_TEST_BUFF <- T_TEST_BUFF + text+"\n" }              /- Print the text, mark the test failed, do not end its execution.

    }
    '''
    return [testMacros, testResultUtilities]

def setUtilityCode(TestArrayText, SwitchCaseText):

    testBedUtilities = r'''

    struct GLOBAL {

        me string[list]: testToRun

        void: WriteTestingReport() <- {
            print(T_MESG_BUFF)
            print("\nTotal Failures/Tests: ", T_NUM_FAILS, "/", T_total, "\n")
        }

        void: RUN_TEST(me string: testName, me string: verboseMode) <- {
            Tstat <- "."
            T_total <- T_total+1
            T_TEST_BUFF <- "\n############################################ FAILED:"+testName+"\n"
            if(verboseMode=="1"){
                print("TESTING ",testName,"...   \t\t")
            }
            /- clear failFlag and mesg_buff; setTimer
            <TEST-CASES-HERE>
            else {Tstat <- "?"}
            /- readTimer()
            /- fetch and return results
            if(verboseMode=="1"){
                if(Tstat=="."){print("OK\n")}
                else if(Tstat=="?"){print("TEST NAME NOT RECOGNIZED\n")}
                else if(Tstat=="F"){print("FAILED\n")}
                else {print("UNKNOWN OUTCOME\n")}
            } else {print(Tstat)}
            if(Tstat=="?"){T_TEST_BUFF <- T_TEST_BUFF + "\nTEST NAME NOT RECOGNIZED\n"}
            if(Tstat!=".") {
                if(Tstat=="F" or Tstat=="?"){T_NUM_FAILS<-T_NUM_FAILS+1}
                T_MESG_BUFF <- T_MESG_BUFF + T_TEST_BUFF
            }
        }

        void: EXEC_TESTS(me string: verboseMode) <- {
            me bool: listOnly <- false
            me bool: CrashProof <- false
            withEach test in testToRun:{
                if(! listOnly){
                    if (!CrashProof){
                        RUN_TEST(test, verboseMode)
                    } else {
     /-                   ExecSelf with timer and fetch result
                    }
     /-               StoreResults()
                }
            }
            if(T_NUM_FAILS==0){print(" PASSED")}
            else{print(" DONE")}
            WriteTestingReport() /- to screen and file for knowing failures. if --HTML, do html. Options allow field selection

        }

        void: RUN_SELECTED_TESTS() <- {
            /- Construct list of tests to run. /- All Tests | -t <testSPec List> | -f = run failed tests
            CommandLineManager.defineOption("TestDog", "ListOfTests", "-t", "--tests", "Specification of which tests to run.")
            CommandLineManager.defineOption("TestDog", "verbose", "-v", "--verbose", "Provide more detail about running tests")
            me string: testListSpec <- CommandLineManager.getOption("TestDog", "ListOfTests")
            me string: verboseMode  <- CommandLineManager.getOption("TestDog", "verbose")
            /-print("TEST LIST SPECIFICATION:'", testListSpec, "'\n")
            me string[list]: testList <- [<TEST-LIST-HERE>]
            if(testListSpec==""){testToRun <- testList}
            else {
                /- TODO: make test selection work with multiple tests and wildcards.
                testToRun.pushLast(testListSpec)
            }
            /- Sort list as needed
            EXEC_TESTS(verboseMode)
        }
    }
'''
    testBedUtilities = testBedUtilities.replace("<TEST-LIST-HERE>", TestArrayText)
    testBedUtilities = testBedUtilities.replace("<TEST-CASES-HERE>", SwitchCaseText)
    return testBedUtilities

def generateTestCode(classes, buildTags, tags, macroDefs):
    [testMacros, testResultUtilities]=setResultCode()
    codeDogParser.AddToObjectFromText(classes[0], classes[1], testResultUtilities )

    TestSpecFile= progSpec.fetchTagValue([tags, buildTags], 'TestSpec')
    TestSpecStr = progSpec.stringFromFile(TestSpecFile) + testMacros
    #print "#################################\n", TestSpecStr
    [testTagStore, testBuildSpecs, testClasses, newTestClasses] = codeDogParser.parseCodeDogString(TestSpecStr, classes[0], classes[1], macroDefs)

    # Replace runcode if it isn't there
    # Here: generate EXEC_TESTS() and RUN_TEST()
    TestsToRun = progSpec.fetchTagValue([testTagStore], 'TestsToRun')
    TestList = TestsToRun.split()
    TestArrayText=""
    SwitchCaseText=""
    count=0
    for T in TestList:
        if count>0:
            TestArrayText+=", "
            SwitchCaseText+="else "

        count+=1
        TestArrayText += '"'+T+'"'

        SwitchCaseText += 'if(testName=="'+T+'"){' + T.replace('/', '_') +'()}\n'

    testBedUtilities = setUtilityCode(TestArrayText, SwitchCaseText)

   # print "TEST TEXT:", testBedUtilities
    codeDogParser.AddToObjectFromText(classes[0], classes[1], testBedUtilities )

    return testTagStore
