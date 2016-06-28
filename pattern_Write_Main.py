#/////////////////////////////////////////////////  R o u t i n e s   t o   G e n e r a t e  " m a i n ( ) "

import progSpec
import codeDogParser

mainFuncCode=r"// No Main given"
def apply(objects, tags, codeToRun):
    # TODO: Make initCode, runCode and deInitCode work better and more automated by patterns.
    runCode='';

    if 'runCode'    in tags: runCode   = tags['runCode']+';'


    # TODO: Some deInitialize items should automatically run during abort().
    # TODO: Deinitialize items should happen in reverse order.
    mainFuncCode="""
me int32: main(me int32: argc, me int32: argv ) <- <%{
    initialize();
    """ + runCode + """
    deinitialize();
    return 0;
} %>

"""

    progSpec.addObject(objects[0], objects[1], 'GLOBAL', 'struct', 'SEQ')
    codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef('GLOBAL',  mainFuncCode ))
