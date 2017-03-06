#///////// Native CodeDog library

import progSpec
import codeDogParser

def use(objects, buildSpec, tags):  #, classesReferenced):
  #  TODO: Make this include only classes that have been referenced and their dependancies
  #  for C in classesReferenced:
  #      if C is in this library, include it and it's dependancies

    CODE='''
    struct stringScanner{
        me string: S
        me int: pos<-0
        stringScanner(me string: str) <- {S<-str  reset()}
        void: reset() <- {pos<-0}

        me int: skipWS() <- {       // Skip past 0 or more whitespace characters.  Return the new pos
            me char: ch
            me uint32: txtSize <- S.size()
            withEach p in RANGE(pos .. txtSize):{
                ch <- S[p]
                if(! isspace(ch)){break()}
            }
            pos<-p
            return(pos)
    }

        me int: skipPast(me string: txt) <- {       // Skip past <txt>.  Return pos or -1 if End-of-string reached

        }

        me int64: chkStr(me uint32: pos, me string: s) <- {
            me uint32: L <- s.size()
            if(pos+L > S.size()){return(-1)}
            withEach i in RANGE(0 .. L):{
                if( s[i] != S[pos+i]) {
      //              print("                                 chkStr FAILED\n")
                    return(-1)
                }
            }
      //      print("                                 chkStr PASSED\n")
            pos <- pos+L
            return(pos)
        }
    }

    '''

    codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )
