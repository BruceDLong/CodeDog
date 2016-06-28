#///////// Add routines for C++
import progSpec
import codeDogParser

def createUtilityFunctions():
    S="""
    """
    return S

def use(objects, buildSpec, tags, platform):
    print "USING CPP************************"
    progSpec.addCodeToInit(tags, "signal(SIGSEGV, reportFault)");
    progSpec.addCodeToInit(tags, "sync_with_stdio(false)");  #std::ios_base::sync_with_stdio(false)"

    CODE="""

    """

    GLOBAL_CODE="""
        struct GLOBAL{

        }
    """

    #codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )



    codeDogParser.AddToObjectFromText(objects[0], objects[1], GLOBAL_CODE )
