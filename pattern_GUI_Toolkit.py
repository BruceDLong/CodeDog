#/////////////////  Routines For Graphics, Text, Audio, User-I/O, fileMgmt, etc.

import progSpec
import codeDogParser


def apply(objects, tags):
    progSpec.appendToStringTagValue(tags, 'initCode', 'Allocate(appFuncs.gui) \n appFuncs.gui.GUI_Init()')
    progSpec.appendToStringTagValue(tags, 'runCode', 'appFuncs.gui.GUI_Run()')
    progSpec.appendToStringTagValue(tags, 'deinitCode', 'appFuncs.gui.GUI_Deinit()')

    # Based on tags, choose a set of libraries and mark-activate them.
    progSpec.setFeaturesNeeded(tags, ['GUI_ToolKit', 'Mouse', 'Keyboard', 'Audio', 'Locale', 'Unicode'], 'GUI_PATTERN')

    # Provide wrapper commands

    # Make a class with init, event-loop, deInit (Can be activated from main.)
    title=progSpec.searchATagStore(tags, 'Title')[0]
    GUI_TK_code = """
    struct GUI {
        const string: title <- "%s"
    }

    """ % title

    codeDogParser.AddToObjectFromText(objects[0], objects[1], GUI_TK_code )
