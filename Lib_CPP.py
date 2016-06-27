#///////// Add routines for C++
import progSpec
import codeDogParser

def createUtilityFunctions():
    S="""
    """
    return S

def use(objects, buildSpec, tags, platform):
    print "USING CPP************************"
    #progSpec.addCodeToInit(tags, "\nme Random: javaRandomVar\n");
    #progSpec.addCodeToInit(tags, "\nme Logger: logger <- Logger.getLogger(className.class.getName())\n");
    #progSpec.addCodeToInit(tags, "private final static Logger logger = Logger.getLogger(className.class.getName());/n");

    CODE="""
   
    """
    
    GLOBAL_CODE="""
        struct GLOBAL{

        }
    """
  
    #codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )


    
    codeDogParser.AddToObjectFromText(objects[0], objects[1], GLOBAL_CODE )
