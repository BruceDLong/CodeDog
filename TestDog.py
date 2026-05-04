#! /usr/bin/env python3
# Code dog module for generating unit tests

# TODO: Capture and analyze the stdout
# TODO: Add command line options: -L: List only, -f: Run failed tests, -t: <list of tests>, also, report options and crash-testing / multi-threaded testing
# TODO: Add timing, timeouts and time requirements

import progSpec
import codeDogParser

def setResultCode():

    testMacros = r'''
#define BAIL() <% return()%>
#define FAIL(text) <%{T_TEST_BUFF <- T_TEST_BUFF + text+"\n" Tstat<-"F" BAIL()}%>     // Print the text, mark the test failed, end its execution.
#define CAPTURE(expr) <%{INFO("expr = " + expr)}%>                                 // Show the expression with INFO
#define REQUIRE(expr) <%{if(!(expr)) {FAIL("The requirement 'expr' failed: " + BlowPOP(expr) )}}%>                     // If the expression fails, show its value with FAIL().
#define CHECK(expr)   <%{if(!(expr)) {CHK_FAIL("expr = " + expr)}}%>                 // If the expression fails, show its value with CHK_FAIL().
    '''

    testResultUtilities = r'''

    struct GLOBAL {
        me int: T_NUM_FAILS <- 0
        me int: T_total <- 0
        me string: T_MESG_BUFF <- ""
        me string: T_TEST_BUFF <- ""
        me string: Tstat <- ""

        void: INFO(me string: text) <- {T_TEST_BUFF <- T_TEST_BUFF + text+"\n"}                               // Buffer text and print it if the test fails.
        void: WARN(me string: text) <- {T_TEST_BUFF <- T_TEST_BUFF + text+"\n" if(Tstat=="."){Tstat<-"W"}}    // Print text even if the test does not fail.
        void: CHK_FAIL(me string: text) <- {Tstat<-"F"  T_TEST_BUFF <- T_TEST_BUFF + text+"\n" }              // Print the text, mark the test failed, do not end its execution.

    }
    '''
    return [testMacros, testResultUtilities]

def setUtilityCode(TestArrayText, SwitchCaseText):

    testBedUtilities = r'''

    struct GLOBAL {

        me List<string>: testToRun

        void: WriteTestingReport() <- {
            print(T_MESG_BUFF)
            print("\nTotal Failures/Tests: ", T_NUM_FAILS, "/", T_total, "\n")
        }

        me bool: isDigitString(me string: text) <- {
            if(text==""){return(false)}
            withEach pos in range 0 .. text.size(){
                if(!isdigit(text[pos])){return(false)}
            }
            return(true)
        }
        me int: parseReturnCode(me string: output) <- {
            me int: pos <- findString(output, "__RC:")
            if(pos==-1){return(-1)}
            me int: idx <- pos+5
            me string: codeTxt <- ""
            while(idx<output.size() and isdigit(output[idx])){
                codeTxt <+- output[idx]
                idx <+- 1
            }
            if(codeTxt==""){return(-1)}
            return(stoi(codeTxt))
        }
        me int: parseFailureCount(me string: output) <- {
            me string: marker <- "Total Failures/Tests:"
            me int: pos <- findString(output, marker)
            if(pos==-1){return(-1)}
            me int: idx <- pos + marker.size()
            while(idx<output.size() and output[idx]==" "){idx <+- 1}
            me string: failTxt <- ""
            while(idx<output.size() and isdigit(output[idx])){
                failTxt <+- output[idx]
                idx <+- 1
            }
            if(failTxt==""){return(-1)}
            return(stoi(failTxt))
        }
        me bool: startsWith(me string: txt, me string: prefix) <- {
            me int: pSize <- prefix.size()
            if(txt.size()<pSize){return(false)}
            return(txt.subStr(0, pSize)==prefix)
        }
        me bool: isStatusChar(me char: ch) <- {
            return(ch=="." or ch=="F" or ch=="T" or ch=="?" or ch=="W")
        }
        me string: reportableTestName(me string: testName) <- {
            if(hasDynamicTest(testName)){return(dynamicTestsFile+":"+testName)}
            return(testName)
        }
        me void: appendSanitizedChildLine(me string: lineIn, their string: outTxt) <- {
            me string: line <- lineIn
            if(line.size()>0 and line[line.size()-1]=="\r"){line <- line.subStr(0, line.size()-1)}
            me string: trimmed <- trimWS(line)
            if(trimmed==""){return()}
            if(startsWith(trimmed, "############################################ FAILED:")){return()}
            if(startsWith(trimmed, "############################################ TIMEOUT:")){return()}
            if(startsWith(trimmed, "Total Failures/Tests:")){return()}
            if(trimmed=="DONE" or trimmed=="PASSED"){return()}
            if(trimmed.size()==1 and isStatusChar(trimmed[0])){return()}
            if(trimmed.size()>=3 and isStatusChar(trimmed[0]) and trimmed[1]==" "){
                me string: tail <- trimmed.subStr(2, trimmed.size()-2)
                tail <- trimWS(tail)
                if(tail=="DONE" or tail=="PASSED"){return()}
            }
            line <+- "\n"
            outTxt <+- line
        }
        me string: sanitizeChildFailureOutput(me string: output) <- {
            me string: cleaned <- ""
            me string: line <- ""
            withEach charPos in range 0 .. output.size(){
                if(output[charPos]=="\n"){
                    appendSanitizedChildLine(line, cleaned)
                    line <- ""
                } else {line <+- output[charPos]}
            }
            if(line!=""){appendSanitizedChildLine(line, cleaned)}
            return(cleaned)
        }
        void: finalizeTestOutput(me int: testNum, me string: testName, me string: verboseMode, me int: lineLength) <- {
            if(verboseMode=="1"){
                me string: spaces <- ""
                withEach spc in range 0 .. 40-lineLength {spaces <+- " "}
                print(spaces)
                if(Tstat=="."){print("OK\n")}
                else if(Tstat=="?"){print("TEST NAME NOT RECOGNIZED\n")}
                else if(Tstat=="T"){print("TIMEOUT\n")}
                else if(Tstat=="F"){print("FAILED\n")}
                else {print("UNKNOWN OUTCOME\n")}
            } else {print(Tstat)}
            if(Tstat=="?"){T_TEST_BUFF <- T_TEST_BUFF + "\nTEST NAME NOT RECOGNIZED\n"}
            if(Tstat!=".") {
                if(Tstat=="F" or Tstat=="?" or Tstat=="T"){T_NUM_FAILS<-T_NUM_FAILS+1}
                T_MESG_BUFF <- T_MESG_BUFF + T_TEST_BUFF
            }
        }

        void: RUN_TEST(me int: testNum, me string: testName, me string: verboseMode) <- {
            Tstat <- "."
            T_total <- T_total+1
            me string: shownName <- reportableTestName(testName)
            T_TEST_BUFF <- "\n############################################ FAILED:"+shownName+"\n"
            me int: lineLength
            if(verboseMode=="1"){
                lineLength <- testName.size() + 13
                print(testNum, "\tTESTING ",testName," ... ")
            }
            log("TESTING "+testName+" _________________")
            // clear failFlag and mesg_buff; setTimer
            if(hasDynamicTest(testName)){executeDynamicTest(testName)}
            else{
                <TEST-CASES-HERE>
            }
            finalizeTestOutput(testNum, testName, verboseMode, lineLength)
        }

        void: RUN_TEST_WITH_TIMEOUT(me int: testNum, me string: testName, me string: verboseMode, me string: timeoutSecs) <- {
            Tstat <- "."
            T_total <- T_total+1
            me string: shownName <- reportableTestName(testName)
            T_TEST_BUFF <- "\n############################################ FAILED:"+shownName+"\n"
            me int: lineLength
            if(verboseMode=="1"){
                lineLength <- testName.size() + 13
                print(testNum, "\tTESTING ",testName," ... ")
            }

            me string: useTimeout <- timeoutSecs
            if(!isDigitString(useTimeout)){useTimeout <- "0"}

            me string: childSpec <- testName
            if(hasDynamicTest(testName)){childSpec <- dynamicTestsFile + ":" + testName}
            me string: cmd <- "timeout "+useTimeout+"s ./"+filename+" -t "+childSpec+" -v 0 -T 0 ; echo __RC:$?"
            me string: childOut <- execCmd(cmd)
            me int: rc <- parseReturnCode(childOut)
            me int: rcPos <- findString(childOut, "__RC:")
            if(rcPos!=-1){childOut <- childOut.subStr(0, rcPos)}

            if(rc==124){
                Tstat <- "T"
                T_TEST_BUFF <- "\n############################################ TIMEOUT:"+shownName+"\n"
                T_TEST_BUFF <- T_TEST_BUFF + "Timed out after "+useTimeout+"s.\n"
            } else {
                me int: failCount <- parseFailureCount(childOut)
                if(failCount==0){Tstat <- "."}
                else if(failCount>0){
                    Tstat <- "F"
                    me string: cleanedOut <- sanitizeChildFailureOutput(childOut)
                    if(cleanedOut==""){cleanedOut <- "Child test failed with no detail output.\n"}
                    T_TEST_BUFF <- T_TEST_BUFF + cleanedOut
                } else {
                    Tstat <- "F"
                    T_TEST_BUFF <- T_TEST_BUFF + "Could not parse child test result.\n"
                    T_TEST_BUFF <- T_TEST_BUFF + sanitizeChildFailureOutput(childOut)
                }
            }
            finalizeTestOutput(testNum, testName, verboseMode, lineLength)
        }

        void: EXEC_TESTS(me string: verboseMode, me string: timeoutSecs) <- {
            me bool: listOnly <- false
            me bool: CrashProof <- false
            me int: testNum <- 1
            withEach testname in testToRun{
                if(! listOnly){
                    if (!CrashProof){
                        if(timeoutSecs=="0"){RUN_TEST(testNum, testname, verboseMode)}
                        else{RUN_TEST_WITH_TIMEOUT(testNum, testname, verboseMode, timeoutSecs)}
                    } else {
     //                   ExecSelf with timer and fetch result
                    }
     //               StoreResults()
                }
                testNum <+- 1
            }
            if(T_NUM_FAILS==0){print(" PASSED")}
            else{print(" DONE")}
            WriteTestingReport() // to screen and file for knowing failures. if --HTML, do html. Options allow field selection

        }

        void: RUN_SELECTED_TESTS() <- {
            // Construct list of tests to run. // All Tests | -t <testSPec List> | -f = run failed tests
            CommandLineManager.defineOption("TestDog", "ListOfTests", "-t", "--tests", "Specification of which tests to run.", "")
            CommandLineManager.defineOption("TestDog", "verbose", "-v", "--verbose", "V0: Verbose output off. V1: Verbose on.", "0")
            CommandLineManager.defineOption("TestDog", "timeout", "-T", "--timeout", "Per-test timeout seconds. 0 disables timeout.", "0")
            me string: testListSpec <- CommandLineManager.getOption("TestDog", "ListOfTests")
            me string: verboseMode  <- CommandLineManager.getOption("TestDog", "verbose")
            me string: timeoutSecs  <- CommandLineManager.getOption("TestDog", "timeout")
            //print("TEST LIST SPECIFICATION:'", testListSpec, "'\n")
            me List<string>: testList <- [<TEST-LIST-HERE>]
            if(testListSpec==""){
                testToRun <- testList
                appendDynamicTestsMatching("", testToRun)
            }
            else {
                me int: splitPos <- findString(testListSpec, ":")
                if(splitPos != -1){
                    me string: fileStem <- testListSpec.subStr(0, splitPos)
                    me string: selector <- ""
                    me int: selectorSize <- testListSpec.size()-(splitPos+1)
                    if(selectorSize>0){selector <- testListSpec.subStr(splitPos+1, selectorSize)}
                    loadTestSpec(fileStem)
                    me int: numMatches <- appendDynamicTestsMatching(selector, testToRun)
                    if(numMatches==0 and selector!=""){testToRun.append(selector)}
                }
                else{
                    // TODO: make test selection work with multiple tests.
                    me int: strSize <- testListSpec.size()
                    if(testListSpec[strSize-1] == "/"){
                        withEach testname in testList{
                            if(testname.subStr(0,strSize) == testListSpec){testToRun.append(testname)}
                        }
                        appendDynamicTestsMatching(testListSpec, testToRun)
                    }
                    else{testToRun.append(testListSpec)}
                }
            }
            // Sort list as needed
            EXEC_TESTS(verboseMode, timeoutSecs)
        }
    }
'''
    testBedUtilities = testBedUtilities.replace("<TEST-LIST-HERE>", TestArrayText)
    testBedUtilities = testBedUtilities.replace("<TEST-CASES-HERE>", SwitchCaseText)
    return testBedUtilities

def generateTestCode(classes, buildTags, tags, macroDefs):
    [testMacros, testResultUtilities]=setResultCode()
    codeDogParser.AddToObjectFromText(classes[0], classes[1], testResultUtilities , 'Test utility functions')

    TestSpecFile= progSpec.fetchTagValue([tags, buildTags], 'TestSpec')
    TestSpecStr = progSpec.stringFromFile(TestSpecFile) + testMacros
    #print "#################################\n", TestSpecStr
    [testTagStore, testBuildSpecs, testClasses, newTestClasses] = codeDogParser.parseCodeDogString(TestSpecStr, classes[0], classes[1], macroDefs, "TestDog Specification")

    # Replace runcode if it isn't there
    # Here: generate EXEC_TESTS() and RUN_TEST()
    TestsToRun = progSpec.fetchTagValue([testTagStore], 'TestsToRun')
    TestList = TestsToRun.split()
    TestArrayText=""
    count=0
    # SwitchCaseText=""
    # for T in TestList:
    #     if count>0:
    #         TestArrayText+=", "
    #         SwitchCaseText+="else "
    #     count+=1
    #     TestArrayText += '"'+T+'"'
    #     SwitchCaseText += 'if(testName=="'+T+'"){' + T.replace('/', '_') +'(testName)}\n'

    SwitchCaseText = 'switch(testName){\n'
    for T in TestList:
        if count>0:
            TestArrayText+=', '
        count+=1
        TestArrayText += '"'+T+'"'
        SwitchCaseText += '    case "'+T+'":{\n'+ T.replace('/', '_') +'(testName);\n    }\n'
    SwitchCaseText += '    default:{Tstat <- "?"}\n'
    SwitchCaseText += '}\n'
    testBedUtilities = setUtilityCode(TestArrayText, SwitchCaseText)

   # print "TEST TEXT:", testBedUtilities
    codeDogParser.AddToObjectFromText(classes[0], classes[1], testBedUtilities, 'Test code' )

    return testTagStore
