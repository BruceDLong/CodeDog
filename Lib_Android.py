#///////// Add routines for Java

import progSpec
import codeDogParser

def createUtilityFunctions():
    S="""
    me x: randInt(me int: val) <- <%!javaRandomVar.nextInt((int)(%1))%>
    me void: initialize() <- <%!initialize()%>
    me void: deinitialize() <- <%!deinitialize()%>
    me void: onCreate() <- <%{
        super.onCreate();
        static_Global = this;
        javaRandomVar = new Random();
        initialize();
    }%>
    
    me void: onTerminate() <- <%{
        super.onTerminate();
        deinitialize();
    }%>
    
    me GLOBAL: getInstance() <- <%{
        return static_Global;
    }%>
    """
    return S


def use(objects, buildSpec, tags, platform):
    CODE="""struct random{me Random: random}"""
    codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )

    APP_UTILITY_CODE = createUtilityFunctions()

    GLOBAL_CODE="""
    struct GLOBAL: ctxTag="Android" Platform='Android' Lang='Java' LibReq="Android" implMode="inherit:Application" {
        me GLOBAL: static_Global
        me Random: javaRandomVar
    %s
    }
""" % (APP_UTILITY_CODE)
    print "GLOBAL_CODE: ", GLOBAL_CODE

    codeDogParser.AddToObjectFromText(objects[0], objects[1], GLOBAL_CODE )
