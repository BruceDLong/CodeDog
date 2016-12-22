#///////// Add routines for Java

import progSpec
import codeDogParser

def createUtilityFunctions():
    S="""
    me x: randInt(me int: val) <- <%!javaRandomVar.nextInt((int)(%1))%>
//    me void: initialize() <- <%!initialize()%>
//    me void: deinitialize() <- <%!deinitialize()%>
//    me void: onCreate() <- <%{
//        super.onCreate();
//        static_Global = this;
//        javaRandomVar = new Random();
//        initialize();
//    }%>

//    me void: onTerminate() <- <%{
//        super.onTerminate();
//        deinitialize();
//    }%>

//    me GLOBAL: getInstance() <- <%{
//        return static_Global;
//    }%>
    """
    return S


def use(objects, buildSpec, tags, platform):
    CODE="""struct random{me Random: random}"""
    codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )

    APP_UTILITY_CODE = createUtilityFunctions()

    GLOBAL_CODE="""
    struct GLOBAL{
    %s
    }
""" % (APP_UTILITY_CODE)
    print "GLOBAL_CODE: ", GLOBAL_CODE

    codeDogParser.AddToObjectFromText(objects[0], objects[1], GLOBAL_CODE )

def GenerateMainActivity(objects, tags, runCode):

    GLOBAL_CODE="""
    struct GLOBAL: ctxTag="Android" Platform='Android' Lang='Java' LibReq="Android" implMode="inherit:Activity" {
//        me GLOBAL: static_Global
//        me Random: javaRandomVar

        me void: onCreate(me Bundle: savedInstanceState) <- {
            super.onCreate(savedInstanceState)
            GLOBAL.static_Global <- this
            initialize()
        }

        me void: onStart() <- {
            super.onStart()
            // The activity is about to become visible. Load state
            """ + runCode + """
        }


        me void: onResume() <- {
            super.onResume()
            // The activity has become visible (it is now "resumed"). Restart animations, etc.
        }

        me void:  onPause() <- {
            super.onPause()
            // Another activity is taking focus (this activity is about to be "paused"). Pause animations, etc.
        }

        me void:  onStop() <- {
            super.onStop()
            // The activity is no longer visible (it is now "stopped")
            // Make sure state is saved as we may quit soon.
        }

        me void:  onDestroy() <- {
            super.onDestroy()
            deinitialize()
        }


    }
"""
    codeDogParser.AddToObjectFromText(objects[0], objects[1], GLOBAL_CODE )
