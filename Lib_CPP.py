#///////// Add routines for C++
import progSpec
import codeDogParser
from progSpec import cdlog, cdErr


def use(objects, buildSpec, tags, platform):
    cdlog(2,"USING Lib_CPP")
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
        me void: endFunc(me int: val) <- <%!return(0)%>
        me int: randInt(me int: val) <- <%!(rand() % %1)%>
        me string: toString(me int: val) <- <%!std::to_string(%1)%>

    }
    struct timeValue{me int64: timeValue}

    struct logger::mem{
        me bool: isLogVisible
        me void: LogEntry() <- <%!%Gcout<<%1<<%2<<"\\n"%>
        /-me void: Show() <- <%!isLogVisible = true;%>
        /-me void: Hide() <- <%!isLogVisible = false;%>
        /-me void: Route(me string: routeSpec) <- <%!cout<<%1;%>
    }

"""
    codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )
