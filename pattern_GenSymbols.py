#/////////////////  Use this pattern to generate and manage symbolic representations for pointers to classes

import progSpec
import codeDogParser

classesTracked = {}   # track to make sure we do not track a class twice.

def apply(classes, tags, classesToTrack):
    S=""
    if isinstance(classesToTrack,str):
        classesToTrack =[classesToTrack]
    for className in classesToTrack:
        if className in classesTracked: continue
        else: classesTracked[className] = True
        C= '''
    struct <CLASSNAME> {
        we uint: symbolCount <- 0
        we Map<me uint, me uint>: ptrToUint
        we string: classTag <- "<CLASSNAME>"
        we Mutex: chkMySymbol

    me string: mySymbol() <- {  // find or generate symbol
        their <CLASSNAME>: obj <- self
        if(obj==NULL){return("NULL")}
        protect(chkMySymbol){
            me uint: objID <- uniqueObjectID(obj)
            if(! ptrToUint.containsKey(objID)){
                symbolCount <+- 1
                ptrToUint[objID] <- symbolCount
                return(classTag + toString(symbolCount))
            } else {
                me uint: item <- ptrToUint.at(objID)
                me uint: symbol <- item
                return(classTag + toString(symbol))
            }
        }
    }

    // their <CLASSNAME>: classPtrFromSymbol(me string: symbol) <- {}  // what about our, my, me, ...?
     void: clearSymbol(their <CLASSNAME>: obj) <- {
        protect(chkMySymbol){
            me uint: objID <- uniqueObjectID(obj)
            ptrToUint.erase(objID)
        }
    }

        '''.replace("<CLASSNAME>", className)

        C += "}\n"
        S += C + "\n"
    #print(S)

    codeDogParser.AddToObjectFromText(classes[0], classes[1], S, 'Pattern: generate symbols' )
