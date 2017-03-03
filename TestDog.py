# Code dog module for generating unit tests

import progSpec
import codeDogParser


testBedUtilities = r'''

    struct GLOBAL {
        me int: T_NUM_FAILS <- 0
        me string: T_MESG_BUFF
        void: BAIL() <- {}
        void: INFO(me string: text) <- {T_MESG_BUFF <- T_MESG_BUFF + text+"\n"}                                        // Buffer text and print it if the test fails.
        void: WARN(me string: text) <- {print(text+'\n')}                                                              // Print text even if the test does not fail.
        void: FAIL(me string: text) <- {T_MESG_BUFF <- T_MESG_BUFF + text+'\n' T_NUM_FAILS<-T_NUM_FAILS+1 BAIL()}      // Print the text, mark the test failed, end its execution.
        void: CHK_FAIL(me string: text) <- {T_MESG_BUFF <- T_MESG_BUFF + text+'\n' T_NUM_FAILS<-T_NUM_FAILS+1}         // Print the text, mark the test failed, do not end its execution.

   //     void: CAPTURE(me string: expr) <- {INFO(expr+" = "+eval(expr))}     // Show the expression with INFO
        void: REQUIRE(me string: expr) <- {                                 // If the expression fails, show its value with FAIL().
           // if(! expr) {FAIL(expr+" = "+eval(expr))}
        }
        void: CHECK(me string: expr) <- {                                   // If the expression fails, show its value with CHK_FAIL().
          //  if(! expr) {CHK_FAIL(expr+" = "+eval(expr))}
        }

        me string: RUN_TEST(me string: testName) <- {
            // clear failFlag and mesg_buff; setTimer
            //SwitchOnTests
            // readTimer()
            // fetch and return results
        }
        void: EXEC_TESTS(me string[list]: testList) <- {
  /*          // withEach test in testList:{
                 if(! -L)
                     if (!CrashProof){
                        RUN_TEST(test)
                    } else {
                        ExecSelf with timer and fetch result
                    }
                    StoreResults()
            }
            WriteReport() // to screen and file for knowing failures. if --HTML, do html. Options allow field selection
*/
        }

        void: selectAndProcessTests() <- {
            // Construct list of tests to run. // All Tests | -t <testSPec List> | -f = run failed tests
            me string[list]: testList <- {<TEST-LIST-HERE>}
            // Sort list as needed
        }
    }
'''

def generateTestCode(objects, buildTags, tags, macroDefs):
    TestSpecFile= progSpec.fetchTagValue([tags, buildTags], 'TestSpec')
    TestSpecStr = progSpec.stringFromFile(TestSpecFile)
    print "#################################\n", TestSpecStr
    [testTagStore, testBuildSpecs, testObjectSpecs] = codeDogParser.parseCodeDogString(TestSpecStr, objects[0], objects[1], macroDefs)

    # Replace runcode if it isn't there
    # Here: generate EXEC_TESTS() and RUN_TEST()
    TestsToRun = progSpec.fetchTagValue([testTagStore], 'TestsToRun')
    TestList = TestsToRun.split()
    TestNameArray=', '.join(TestList)
    testBedUtilities = testBedUtilities.replace('<TEST-LIST-HERE>', TestNameArray)
    print "TEST TEXT:", testBedUtilities
    exit(2)
    codeDogParser.AddToObjectFromText(objects[0], objects[1], testBedUtilities )

    return testTagStore
