#/////////////////  Use this pattern to respond to command-line arguments, etc.

import progSpec
import codeDogParser


def apply(classes, tags):
    progSpec.appendToStringTagValue(tags, 'initCode', 'CommandLineManager.processCmdLine(prgArgs, false)')

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
    }

    struct CmdLineArgsMngr {
        me string: cmdLineText
        our optionRecord[list]: options

        void: defineOption(me string: groupID, me string: optionID, me string: shortName, me string: longName, me string: helpText) <- {
            our optionRecord: rec
            Allocate(rec, groupID, optionID, shortName, longName, helpText)
            options.pushLast(rec)
        }

        me string: getOption(me string: groupID, me string: optionID) <- {
            me stringScanner: scanner
            me string: argToReturn <- ""
            scanner.initialize(cmdLineText)
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
            return(argToReturn)
        }

        me string: helpText() <- {
            return("This is the help text")
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
