#/////////////////////////////////////////////////  R o u t i n e s   t o   G e n e r a t e  " m a i n ( ) "

import progSpec
import codeDogParser

mainFuncCode=r"// No Main given"
def apply(objects, tags, parserSpecTag):

    tags['Include'] += ",<signal.h>"

    mainFuncCode=r"""

    func var int32: main(<% var int32: argc, rPtr int32: argv %>) <%{
        if(sizeof(int)!=4) {cout<<"WARNING! int size is "<<sizeof(int)<<" bytes.\n\n";}
        signal(SIGSEGV, reportFault);
    string inputFilename="testInfon.pr";
    fstream fileIn("testInfon.pr");
    if (!fileIn.is_open()){cout<<"Could not open "<<inputFilename<<".\n"; exit(1);}
    infonParser parser;
    parser.stream=&fileIn;
    streamSpan cursor;
    shared_ptr<infon> topInfon=make_shared<infon>();
    parser.BatchParse(&cursor, topInfon.get());
    //topInfon->printToString();
    exit(0);
    //    eventHandler EvH;
    //    int ret=EvH.eventLoop();
    //    EvH.shutDown();

        return 0;//ret;
    } %>

"""

    progSpec.addObject(objects[0], objects[1], 'MAIN')
    codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef('MAIN', mainFuncCode))
