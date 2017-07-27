#/////////////////  Use this pattern to generate and manage symbolic representations for pointers to classes

import progSpec
import codeDogParser

classesTracked = {}   # track to make sure we do not track a class twice.

def apply(classes, tags, classesToTrack):
    S=""
    for className in classesToTrack:
        if className in classesTracked: continue
        else: classesTracked[className] = True
        C= '''
    struct <CLASSNAME> {
        we uint: symbolCount
        me uint[we map their <CLASSNAME>]: ptrToUint
    /-    me <CLASSNAME>[their map]: uintToPtr
        we string: classTag <- "<CLASSNAME>"

    me string: mySymbol() <- {  /- find or generate symbol
        me uint[itr map their <CLASSNAME>]: item <- ptrToUint.find(this)
        if (item==ptrToUint.end()){
            symbolCount <- symbolCount+1
            ptrToUint[this] <- symbolCount
            return(classTag + toString(symbolCount))
        }
        else {
            me uint: symbol <- item
            return(classTag + toString(symbol))
        }
    }

    /- their <CLASSNAME>: classPtrFromSymbol(me string: symbol) <- {}  /- what about our, my, me, ...?
    /- void: clearSymbol(me string: symbol) <- {}

        '''.replace("<CLASSNAME>", className)

        C += "}\n"
        S += C + "\n"


    codeDogParser.AddToObjectFromText(classes[0], classes[1], S )
