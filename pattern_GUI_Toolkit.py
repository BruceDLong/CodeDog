#/////////////////  Routines For Graphics, Text, Audio, User-I/O, fileMgmt, etc.

import progSpec
import codeDogParser


def apply(objects, tags):
    progSpec.appendToStringTagValue(tags, 'initCode', 'gui_tk.GUI_Init()')
    progSpec.appendToStringTagValue(tags, 'runCode', 'gui_tk.GUI_Run()')
    progSpec.appendToStringTagValue(tags, 'deinitCode', 'gui_tk.GUI_Deinit()')

    # Based on tags, choose a set of libraries and mark-activate them.
    progSpec.setFeaturesNeeded(tags, ['GUI_ToolKit', 'Mouse', 'Keyboard', 'Audio', 'Locale', 'Unicode'], 'GUI_PATTERN')

    # Provide wrapper commands

    # Make a class with init, event-loop, deInit (Can be activated from main.)
    title=progSpec.searchATagStore(tags, 'Title')[0]
    GUI_TK_code = """
    struct GLOBAL {
        const string: title <- "%s"
    }

    """ % title

    codeDogParser.AddToObjectFromText(objects[0], objects[1], GUI_TK_code )
