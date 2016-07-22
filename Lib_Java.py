#///////// Add routines for Java

import progSpec
import codeDogParser

#TODO: make conversion for rand to GLOBAL.getRandInt & main return(0)
def createUtilityFunctions():
    S="""
        me x: endFunc(me int: val) <- <%!%>
        me x: randInt(me int: val) <- <%!GLOBAL.static_Global.javaRandomVar.nextInt((int)(%1))%>
        me x: print(me string: s)<- <%!System.out(%1)%>
        me string: logMesg(me string: mesg) <- <%!System.out.println(%1)%>
        me void: initialize() <- <%!static_Global.initialize()%>
        me void: deinitialize() <- <%!static_Global.deinitialize()%>

    """
    return S


def use(objects, buildSpec, tags, platform):
    print "USING Java"
    #progSpec.addCodeToInit(tags[1], "me Random: javaRandomVar \n");
    #progSpec.addCodeToInit(tags[1], "const Logger: log <- Logger.getLogger('log')\n");

    CODE="""struct random{me Random: random}"""
    codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )

    APP_UTILITY_CODE = createUtilityFunctions()

    GLOBAL_CODE="""
        struct GLOBAL{
            me GLOBAL: static_Global
            me Random: javaRandomVar
            // LOGGING INTERFACE:
         %s
        }
""" % (APP_UTILITY_CODE)
    print "GLOBAL_CODE: ", GLOBAL_CODE

    codeDogParser.AddToObjectFromText(objects[0], objects[1], GLOBAL_CODE )
