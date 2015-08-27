import progSpec

#/////////////////////////////////////////////////  R o u t i n e s   t o   G e n e r a t e  a n   E v e n t H a n d l e r
def apply(spec, data):
    structNames=1

    EventHandlerCode = r"""
        mode: coreRunState [corePreInit, coreParsing, coreRunning]

        var:  infon topInfon;
        var:  infonParser parser;
        var:  bool doneYet;

        func: bool: doRule(infon* i){
            switch(i->flags&coreRunStateMask){
                case corePreInit:    break;
                //case coreParsing: parser.doRule(i);    break;
                case coreRunning: topInfon.doRule(i);  break;
                default:exit(2);
            }
        } END

        func: bool: pollEvent(infon** inf){return 0;}END
        func: int: eventLoop(){
            uint64_t now=0, then=0; //SDL_GetTicks();
            uint64_t frames=0;
            infon* inf;
            while (!doneYet){
                 ++frames;
                while (pollEvent(&inf)) {
                    doRule(inf);
                }
                if(doneYet) continue;
  /*              if(portal->needsToBeDrawn) portal->needsToBeDrawn=false; else continue;
                DrawScreen(portal);
                SDL_RenderPresent(portal->viewPorts->renderer); //OgrRenderWnd->swapBuffers(false);
                update(portals[0]);  */
            }
       //     if ((now = SDL_GetTicks()) > then) printf("\nFrames per second: %2.2f\n", (((double) frames * 1000) / (now - then)));

        } END
    """

    progSpec.addStruct(spec, "eventHandler")
    progSpec.FillStructFromText(spec, "eventHandler", EventHandlerCode)
    spec[structNames].append("eventHandler")
