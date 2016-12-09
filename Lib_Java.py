#///////// Add routines for Java

import progSpec
import codeDogParser

#TODO: make conversion for rand to GLOBAL.getRandInt & main return(0)
def createUtilityFunctions():
    S="""
        me x: endFunc(me int: val) <- <%!%G %>
        me x: randInt(me int: val) <- <%!javaRandomVar.nextInt((int)(%1))%>
        me x: print(me string: s)<- <%!%GSystem.out(%1)%>
        me string: logMesg(me string: mesg) <- <%!%GSystem.out.println(%1)%>
        me void: initialize() <- <%!initialize()%>
        me void: deinitialize() <- <%!deinitialize()%>
        me void: exit(me int: val) <- <%!%GSystem.exit(%1)%>
        me bool: isdigit(me char: ch) <- <%!%GCharacter.isDigit(%1)%>
        me bool: isalpha(me char: ch) <- <%!%GCharacter.isLetter(%1)%>
        me bool: isspace(me char: ch) <- <%!%GCharacter.isWhitespace(%1)%>
        me bool: isalnum(me char: ch) <- <%!%GCharacter.isLetterOrDigit(%1)%>
        me int64: stoi(me string: str) <- <%!%GInteger.parseInt(%1)%>
        me bool: isprint(me char: ch) <- <%!%GCharacter.isISOControl(%1)%>
        me long: getCurrentTimeStamp() <- <%!date.getTime()%>
        me string: readFileAsString(me string: fileName) <- <%!%Gfuncs.readFileAsString(%1)%>
        me timeOutID: callPeriodically(): cmd="addImplementsToClass" <- <%!%GScheduledExecutorService timerID=Executors.newSingleThreadScheduledExecutor(); timerID.scheduleAtFixedRate(%1, 0, %2, TimeUnit.MILLISECONDS)%>

    """
    return S


def use(objects, buildSpec, tags, platform):
    print "USING Java"
    #progSpec.addCodeToInit(tags[1], "me Random: javaRandomVar \n");
    #progSpec.addCodeToInit(tags[1], "const Logger: log <- Logger.getLogger('log')\n");

    CODE="""
        struct random{me Random: random}
        struct timeValue{me long: timeValue}
        """
    codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )

    APP_UTILITY_CODE = createUtilityFunctions()

    GLOBAL_CODE="""
        struct GLOBAL{
            me GLOBAL: static_Global
            me Random: javaRandomVar
            me Date: date
            // LOGGING INTERFACE:
""" + (APP_UTILITY_CODE) + """
        }
"""


    print "GLOBAL_CODE: ", GLOBAL_CODE

    codeDogParser.AddToObjectFromText(objects[0], objects[1], GLOBAL_CODE )
