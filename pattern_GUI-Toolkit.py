#/////////////////  Routines For Graphics, Text, Audio, User-I/O, fileMgmt, etc.

import progSpec
import codeDogParser


def apply(objects, tags):
    # Based on tags, choose a set of libraries and mark-activate them.

    # Provide wrapper commands

    # Make a class with init, event-loop, deInit (Can be activated from main.)
    title=searchATagStore(tags, 'Title')
    GUI_TK_code = """
    struct GUI_TK {
        their SDL_Window: window <- 0
        their SDL_Renderer: renderer <- 0
        me string title
        me bool: prepareDefaultWindow()  <- {
            title <- '%s'
            window <- SDL_CreateWindow(title, 10,10,700,500, SDL_WINDOW_RESIZABLE)
            renderer <- SDL_CreateRenderer(window, -1, SDL_RENDERER_SOFTWARE)
            SDL_SetRenderDrawColor(renderer, 0xA0, 0xA0, 0xc0, 0xFF)
        }

        me void: StreamEvents(){
            me uint64  frames=0
            me uint64: then=SDL_GetTicks()
            me uint64: now=0

            me SDL_Event ev
            while (!doneYet){
                frames <- frames + 1
                while (SDL_PollEvent(&ev)) {
                    HandleEvent(portalView, window, ev)
                }
                if(!doneYet) {
                    if(needsToBeDrawn) {
                        needsToBeDrawn<-false
                        DrawScreen(portal)
                        SDL_RenderPresent(portal->viewPorts->renderer)
                        update()
                        SDL_Delay(10)
                    }
                }
            }
            doneYet=true;
            if ((now = SDL_GetTicks()) > then) print("\nFrames per second: %i`(((double) frames * 1000) / (now - then))`\n");

        }

        me void: cleanUp(){
            SDL_DestroyRenderer(renderer)
            SDL_DestroyWindow(window)
        }
    }

    """ % title
