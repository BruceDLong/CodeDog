#///////// Add routines for Java

import progSpec
import codeDogParser

def createUtilityFunctions():
    S="""

    """
    return S

def createMenubar():
    S="""
    // menu bar code here
      """
    return S


def createMainAppArea():
    S="""
    // main app area code here
"""
    return S


def createStatusBar():
    S="""
    // Status bar code here
"""
    return S

def use(objects, buildSpec, tags, platform):
    print "USING Java"
    progSpec.addCodeToInit(tags[1], "me Random: javaRandomVar \n");
    #static Random javaRandomVar = new Random();
    #progSpec.addCodeToInit(tags[1], "const Logger: log <- Logger.getLogger('log')\n");

    CODE="""
        struct Random{me Random: Random}
    """
    codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )

    APP_UTILITY_CODE = createUtilityFunctions()
    MENU_BAR_CODE = createMenubar()
    MAIN_APP_CODE = createMainAppArea()
    STATUS_BAR_CODE=createStatusBar()
    
    GLOBAL_CODE="""
        struct GLOBAL{
        me RANDOM: javaRandomVar <- Random()
        
        me int32: randInt(me int32: highVal)<-{
            me int32: randomNumber <- javaRandomVar.nextInt(highVal + 1)
            return (randomNumber)
        }

            // LOGGING INTERFACE:
        
        
         %s
        ////////////////////  A d d  A p p l i c a t i o n   M e n u
          %s

        ////////////////////  A d d   A p p l i c a t i o n   I t e m s
          %s

        ////////////////////  A d d  S t a t u s   A r e a
          %s
        }
""" % (APP_UTILITY_CODE, MENU_BAR_CODE, MAIN_APP_CODE, STATUS_BAR_CODE)

    codeDogParser.AddToObjectFromText(objects[0], objects[1], GLOBAL_CODE )
