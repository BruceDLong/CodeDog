#/////////////////  Routines For Graphics, Text, Audio, User-I/O, fileMgmt, etc.

import progSpec
import codeDogParser


def apply(objects, globalTags):
    progSpec.appendToStringTagValue(globalTags, 'initCode', ' Allocate(appFuncs.gui) \n appFuncs.gui.GUI_Init()')
    progSpec.appendToStringTagValue(globalTags, 'runCode', 'appFuncs.gui.GUI_Run()')
    progSpec.appendToStringTagValue(globalTags, 'deinitCode', 'appFuncs.gui.GUI_Deinit()')

    progSpec.setFeaturesNeeded(globalTags, ['GUI_ToolKit'])

    # Provide wrapper commands

    # Make a class with init, event-loop, deInit (Can be activated from main.)
    print "GUI TAG TITLE:", globalTags
    title=progSpec.searchATagStore(globalTags, 'Title')[0]
    GUI_TK_code = """
    struct GUI {
        me string: title <- "%s"
    }

    """ % title

    codeDogParser.AddToObjectFromText(objects[0], objects[1], GUI_TK_code )
