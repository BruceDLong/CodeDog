#/////////////////////////////////////////////////  R o u t i n e s   t o   G e n e r a t e  " m a i n ( ) "
mainFuncCode=r"// No Main given"
def apply(data):
    # data[0] should be reference to the active tag-set
    data[0]['Include'] += ",<signal.h>"

    mainFuncCode=r"""
static void reportFault(int Signal){cout<<"\nSegmentation Fault.\n"; fflush(stdout); abort();}

int main(int argc, char **argv){
    if(sizeof(int)!=4) {cout<<"WARNING! int size is "<<sizeof(int)<<" bytes.\n\n";}
    signal(SIGSEGV, reportFault);
fstream fileIn("testInfon.pr");
infonParser parser;
parser.stream=&fileIn;
streamSpan cursor;
infon* topInfon;
//infonPtr topInfPtr=make_shared(topInfon);
parser.BatchParse(&cursor, *topInfon);
topInfon->printToString();
exit(0);
    eventHandler EvH;
    int ret=EvH.eventLoop();
//    EvH.shutDown();

    return ret;
}
"""
    return mainFuncCode
