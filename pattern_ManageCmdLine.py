#/////////////////  Use this pattern to respond to command-line arguments, etc.

import progSpec
import codeDogParser

firstRun = True

def apply(classes, tags):
    global firstRun
    if not firstRun: return
    firstRun = False
    progSpec.addCodeToInit(tags, 'CommandLineManager.processCmdLine(prgArgs, false)')

    code = r"""
    struct GLOBAL{
        me CmdLineArgsMngr: CommandLineManager
    }

    struct optionRecord{
        me string: groupID
        me string: optionID
        me string: shortName
        me string: longName
        me string: helpText
        me string: defaultVal   // "_REQIRED" = required
    }

    struct CmdLineArgsMngr {
        me string: cmdLineText
        me List<our optionRecord>: options

        void: defineOption(me string: groupID, me string: optionID, me string: shortName, me string: longName, me string: helpText, me string: defaultTxt) <- {
            our optionRecord: rec
            Allocate(rec, groupID, optionID, shortName, longName, helpText, defaultTxt)
            options.append(rec)
        }

        me string: getOption(me string: groupID, me string: optionID) <- {
            me stringScanner: scanner
            me string: argToReturn <- ""
            scanner.initialize(cmdLineText)
            if(cmdLineText=="-h" or cmdLineText=="--help"){
                print(helpText())
                exit(1)
            }
            // Find optionRecord
            me int: recIdx <- -1
            withEach optRec in options{
                if(optRec.optionID==optionID){
                    recIdx <- optRec_key
                    break()
                }
            }
            if(recIdx==-1){return("")}
            me string: shortName <- options[recIdx].shortName
            me string: longName  <- options[recIdx].longName
            me string: defaultTxt   <- options[recIdx].defaultVal
            me int: scanPos  <- scanner.pos
            me int: foundPos <- scanner.skipPast(shortName)
            me int: startPos <- scanner.skipWS()
            me int: endPos   <- 0
            if(foundPos>=0){
                endPos <- scanner.skipTo(" -")
                argToReturn <- cmdLineText.subStr(startPos, endPos-startPos)
            } else {
                scanner.pos <- scanPos
                foundPos <- scanner.skipPast(longName)
                startPos <- scanner.skipWS()
                if(foundPos>=0){
                    endPos <- scanner.skipTo(" -")
                    argToReturn <- cmdLineText.subStr(startPos, endPos-startPos)
                }
            }
            if(argToReturn==""){
                if(defaultTxt=="_REQIRED"){
                    print("\nOption '", optionID, "' is required.\n")
                    print(helpText())
                    exit(1)
                } else {
                    argToReturn <- defaultTxt
                }
            }
            return(argToReturn)
        }

        me string: helpText() <- {
            me string: helpTxt <- "\nOPTIONS:\n"
            withEach optRec in options{
                me string: defaultVal <- "(default: "+optRec.defaultVal+")"
                if(optRec.defaultVal=="_REQIRED"){defaultVal <- "REQUIRED"}
                helpTxt <+- "    "+optRec.shortName+" \t"+alignLeft(optRec.longName, 12)+" "+alignLeft(optRec.helpText, 25)+" \t"+defaultVal+"\n"
            }
            helpTxt <+- "    -h \t"+alignLeft("--help", 12)+" "+alignLeft("Print this help text", 25)+"\n"
            return(helpTxt+"\n")
        }

        void: processCmdLine(me string:prgArgs, me bool: exitOnInvalid) <- {
            cmdLineText <- prgArgs
            me int: txtSize <- cmdLineText.size()

    // TODO: make this handle multiple options of each kind e.g., as with a compiler having multiple link options.
    //          ALSO: add features from posix's or java's command line style
    //        me char: ch
    //        withEach p in RANGE(0 .. txtSize){
    //            ch <- cmdLineText[p]
    //        }
        }
    }

    """

    codeDogParser.AddToObjectFromText(classes[0], classes[1], code , 'Pattern: Manage Command-Line')
