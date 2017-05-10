#///////// Add routines for C++
import progSpec
import codeDogParser


def use(objects, buildSpec, tags, platform):
    print "USING Lib_Swift"
    CODE="""
    struct GLOBAL{
        /-me bool: isBoolTest

        /- LOGGING INTERFACE:
        /-me void: logMesg(me string: s) <- <%!logPrint(logMode: "MESSAGE: ", s: %1)%>
        /-me void: logInfo(me string: s) <- <%!logPrint(logMode: "", s: %1)%>
        /-me void: logCriticalIssue(me string: s) <- <%!logPrint(logMode: "CRITICAL ERROR: ", s: %1)%>
        /-me void: logFatalError(me string: s) <- <%!logPrint(logMode: "FATAL ERROR: ", s: %1)%>
        /-me void: logWarning(me string: s) <- <%!logPrint(logMode: "WARNING: ", s: %1)%>
        /-me void: logDebug(me string: s) <- <%!logPrint(logMode: "DEBUG: ", s: %1)%>
        /-me void: assert(condition) <- {}
    }
        """
    codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )
