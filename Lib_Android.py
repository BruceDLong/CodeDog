#///////// Add routines for Java

import progSpec
import codeDogParser


def use(objects, buildSpec, tags, platform):
    GLOBAL_CODE="""
    struct random{me Random: random}
    struct GLOBAL{
        me void: logMesg()<- <%!%GLog.v("GLOBAL", %1)%>
        me x: randInt(me int: val) <- <%!javaRandomVar.nextInt((int)(%1))%>
        me void: copyAssetToWritableFolder(me string: fromPath, me string: toPath)<- <%{
            try {
                InputStream inStream = GLOBAL.static_Global.getAssets().open(fromPath);
                OutputStream outStream = GLOBAL.static_Global.openFileOutput(toPath, Context.MODE_PRIVATE);

                byte[] buf = new byte[1024];
                int len;
                while ((len = inStream.read(buf)) > 0) {
                    outStream.write(buf, 0, len);
                }
                outStream.close();
                inStream.close();
            } catch (Exception e) {
                System.out.print(e.getMessage());
            }
        }%>
        
                    
        me string: getFilesDirAsString()<- <%{
            File file = GLOBAL.static_Global.getFilesDir();
            return file.getAbsolutePath();
        }%>
    }
    
"""
    print "GLOBAL_CODE: ", GLOBAL_CODE

    codeDogParser.AddToObjectFromText(objects[0], objects[1], GLOBAL_CODE )

def GenerateMainActivity(objects, tags, runCode):

    GLOBAL_CODE="""
    struct GLOBAL: ctxTag="Android" Platform='Android' Lang='Java' LibReq="Android" attrs="public" implMode="inherit:Activity" {

        me void: onCreate(me Bundle: savedInstanceState) <- {
            super.onCreate(savedInstanceState)
            GLOBAL.static_Global <- this
            Allocate(appFuncs)
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
