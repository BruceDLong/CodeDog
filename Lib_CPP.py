#///////// Add routines for C++
import progSpec
import codeDogParser

def createUtilityFunctions():
    S="""
        me x: endFunc(me int: val) <- <%!return(0)%>
        me x: randInt(me int: val) <- <%!(rand() % %1)%>
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
    print "USING CPP"
    progSpec.addCodeToInit(tags[1], "signal(SIGSEGV, reportFault)");
   # progSpec.addCodeToInit(tags, "sync_with_stdio(false)");  #std::ios_base::sync_with_stdio(false)"

    CODE="""

    """

    codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )

    APP_UTILITY_CODE = createUtilityFunctions()
    MENU_BAR_CODE = createMenubar()
    MAIN_APP_CODE = createMainAppArea()
    STATUS_BAR_CODE=createStatusBar()
    
    GLOBAL_CODE="""
    struct GLOBAL{
        
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
