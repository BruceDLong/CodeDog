#///////// Add routines for Java

import progSpec
import codeDogParser




def use(objects, buildSpec, tags, platform):
    CODE="""struct random{me Random: random}"""
    codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )


    GLOBAL_CODE="""
    struct GLOBAL{
        // DRAWING ROUTINES:

    me void: renderText(me GUI_ctxt: cr, me string: text, me string: fontName, me int: fontSize) <- <%{
        cr.gr.setFont(new Font(fontName, Font.PLAIN, fontSize));
        cr.gr.drawString(text, (int)cr.cur_x, (int)cr.cur_y);
    } %>



    me INK_Image[map string]: InkImgCache
    me void: displayImage(me GUI_ctxt: cr, me string: filename, me double: x, me double: y, me double: scale) <- <%{
        BufferedImage picPtr=InkImgCache.get(filename);
        if (picPtr==null) {
            try{
                picPtr=ImageIO.read(new File(filename));
            } catch(IOException ioe){System.out.println("Cannot read image file " + ioe.getMessage()); System.exit(2);}
            InkImgCache.put(filename, picPtr);
            }
        cr.gr.drawImage(picPtr, null, 0,0);
    } %>



    }
"""
    print "GLOBAL_CODE: ", GLOBAL_CODE

    codeDogParser.AddToObjectFromText(objects[0], objects[1], GLOBAL_CODE )

def GenerateMainActivity(objects, tags, runCode):

    GLOBAL_CODE="""
    struct GLOBAL: ctxTag="Android" Platform='Android' Lang='Java' LibReq="Android" implMode="inherit:Activity" {
        me GLOBAL: static_Global
        me Random: javaRandomVar

        me void: onCreate(me Bundle: savedInstanceState) <- {
            super.onCreate(savedInstanceState)
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
