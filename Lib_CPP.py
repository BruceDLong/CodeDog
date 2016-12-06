#///////// Add routines for C++
import progSpec
import codeDogParser


def use(objects, buildSpec, tags, platform):
    print "USING CPP"
    progSpec.addCodeToInit(tags[1], "signal(SIGSEGV, reportFault)");
   # progSpec.addCodeToInit(tags, "sync_with_stdio(false)");  #std::ios_base::sync_with_stdio(false)"

    CODE="""
    struct stream{
        me void: open(me string: filename) <- <%!open(%1)%>
        me int: getChar() <- <%!get()%>
        me void: getLine(me string: S) <- <%!getLine(%1)%>
        me bool: EOF() <- <%!eof()%>
    }

    struct GLOBAL{
        me x: endFunc(me int: val) <- <%!return(0)%>
        me x: randInt(me int: val) <- <%!(rand() % %1)%>

    }
    struct timeValue{me uint64: timeValue}
"""
    codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )
