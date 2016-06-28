#///////// Add routines for Java

import progSpec
import codeDogParser

def createUtilityFunctions():
    S="""
    """
    return S

def use(objects, buildSpec, tags, platform):
    print "USING Java"
    progSpec.addCodeToInit(tags[1], "\nme bool: isOff\n");
    progSpec.addCodeToInit(tags[1], "\nme bool: isOn\n");
    #progSpec.addCodeToInit(tags, "Random javaRandomVar = new Random();/n");
    #progSpec.addCodeToInit(tags, "private final static Logger logger = Logger.getLogger(className.class.getName());/n");

    CODE="""

    """

    GLOBAL_CODE="""
        struct GLOBAL{
            me int32: rand()<- <%!GLOBAL.randInt()%>
            // LOGGING INTERFACE:
            me void: logMesg(me string: s) <- <%!GLOBAL.getLoggInfo(%1)%>
            me void: getLoggInfo()<- <%!{}%>
        }
    """

    #codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )



    codeDogParser.AddToObjectFromText(objects[0], objects[1], GLOBAL_CODE )

    #public static void getLoggInfo( String str)
    #{
        #final Logger logger = Logger.getLogger(testTreeMaps.class.getName());
        #logger.log(Level.INFO, str);
    #}

    #public static int randInt(int highVal)
    #{
        #Random javaRandomVar = new Random();
        #int randomNumber = javaRandomVar.nextInt(highVal + 1);
        #return randomNumber;
    #}
