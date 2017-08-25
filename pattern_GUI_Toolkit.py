#/////////////////  Routines For Graphics, Text, Audio, User-I/O, fileMgmt, etc.

import progSpec
import codeDogParser


def apply(classes, globalTags):
    progSpec.appendToStringTagValue(globalTags, 'initCode', ' Allocate(thisApp.gui) \n thisApp.gui.GUI_Init()')
    progSpec.appendToStringTagValue(globalTags, 'runCode', 'thisApp.gui.GUI_Run()')
    progSpec.appendToStringTagValue(globalTags, 'deinitCode', 'thisApp.gui.GUI_Deinit()')

    progSpec.setFeaturesNeeded(globalTags, ['GUI_ToolKit'])

    # Provide wrapper commands

    # Make a class with init, event-loop, deInit (Can be activated from main.)
    title=progSpec.searchATagStore(globalTags, 'Title')[0]
    GUI_TK_code = """
    struct GUI {
        me string: title <- "%s"
    }

    """ % title

    codeDogParser.AddToObjectFromText(classes[0], classes[1], GUI_TK_code )
