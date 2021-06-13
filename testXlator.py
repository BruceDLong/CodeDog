#!/usr/bin/env python3
# CodeDog Xlator tester
import os
from progSpec import cdlog
import errno
import subprocess
import sys;  sys.dont_write_bytecode = True
from datetime import date
buildSpec = ""
runSpec = ""
workingDirectory = ""
runDirectory = ""

testDefinitions = {
    #TODO make more cases for strings and chars with various combinations of double and single quotes
     'class/simple':        ['struct emptyClass{ }', 'PGB:'],
     'class/intDecl':       ['struct testClass{ me void: runTest()<-{me int: myInt <- 123        \n print(myInt)}}',    'PGBR:123'],
     'class/strDecl':       ['struct testClass{ me void: runTest()<-{me string: myString <- "one"\n print(myString)}}', 'PGBR:one'],
     'class/int32Decl':     ['struct testClass{ me void: runTest()<-{me int32: myInt32 <- 123    \n print(myInt32)}}',  'PGBR:123'],
     'class/int64Decl':     ['struct testClass{ me void: runTest()<-{me int64: myInt64 <- 123    \n print(myInt64)}}',  'PGBR:123'],
     'class/doubleDecl':    ['struct testClass{ me void: runTest()<-{me double: myDb <- 12.34    \n print(myDb)}}',     'PGBR:12.34'],
     'class/uint32Decl':    ['struct testClass{ me void: runTest()<-{me uint32: myInt <- 123     \n print(myInt)}}',    'PGBR:123'],
     'class/uint64Decl':    ['struct testClass{ me void: runTest()<-{me uint64: myInt <- 123     \n print(myInt)}}',    'PGBR:123'],
     'class/boolDecl':      ['struct testClass{ me void: runTest()<-{me bool: myBool <- true     \n if(myBool){print("p")}}}','PGBR:p'],
     'class/constDecl':     ['struct testClass{ me void: runTest()<-{const int: myInt <- 2       \n print(myInt)}}',    'PGBR:2'],
     'class/charDecl':      ['struct testClass{ me void: runTest()<-{me char: myChar<- "c"       \n print(myChar)}}',   'PGBR:c'],
     'class/baseDecls':     ['''
struct testClass{
    me void: runTest()<-{
        me int: myInt <- 2
        print(myInt)
        me string: myString <- "one"
        print(myString)
        me int32: myInt32 <- 3
        print(myInt32)
        me int64: myInt64 <- 4
        print(myInt64)
        me double: myDouble <- 12.34
        print(myDouble)
        me uint32: myUint32 <- 6
        print(myUint32)
        me uint64: myUint64 <-7
        print(myUint64)
        me bool: myBool <- true
        if(myBool){print("p")}
        const int: myConst <- 8
        print(myConst)
        me char: myChar <-"c"
        print(myChar)
    }
}''', 'PGBR:2one3412.3467p8c',['class/simple', 'class/intDecl', 'class/strDecl', 'class/int32Decl', 'class/int64Decl', 'class/doubleDecl', 'class/uint32Decl', 'class/uint64Decl', 'class/boolDecl', 'class/constDecl', 'class/charDecl']],
#####################################################################################################
#############################################################
     #'class/strListDecl':  ['struct testClass{me List<me string>: myStringList}', 'PGB:'],
     #'class/mapDecl':      ['struct testClass{me Map<me int, me string>: testMap}', 'PGB:'],
     #'class/multimapDecl':[],
     #'class/treeDecl':    [],
     #'class/graphDecl':   [],
     #const string: constStr <- "Hello"
     #const double: pi <- 3.14
     'class/funcDefn':          ['struct testClass{me int: myInt <- 7-3}', 'PGB:'],
     'class/funcDecl':          ['struct testClass{me void: runTest()<-{print("Function was called.")}}', 'PGBR:Function was called.'],
     'class/funcCallArgs':      ['struct testClass{me void: runTest()<-{testFunc2("Pass func arg.")}\nme void: testFunc2(me string: strArg)<-{print(strArg)}}', 'PGBR:Pass func arg.'],
     'class/pureVirtualFunc':   ['struct testClass{me void: runTest()<-{me derivedClass: DC; DC.pureVirtualFunc()}} \nstruct pureVirtualClass{me void: pureVirtualFunc()} \nstruct derivedClass: inherits=pureVirtualClass{me void: pureVirtualFunc()<-{print("Function was called.")}}', 'PGBR:Function was called.'],
     'class/funcDefaultParams': ['struct testClass{me void: runTest()<-{DefaultParams()}\nme void: DefaultParams(me string: defaultParam<-"Default func param1.  ",me string: defaultParam2<-"Default func param2. ")<-{print(defaultParam,defaultParam2)}}', 'PGBR:Default func param1.  Default func param2. '],
     'class/funcPassAndDefault':['struct testClass{me void: runTest()<-{PassAndDefault("Pass func arg.  ")}\nme void: PassAndDefault(me string: defaultParam<-"Default func param1.  ",me string: defaultParam2<-"Default func param2. ")<-{print(defaultParam,defaultParam2)}}', 'PGBR:Pass func arg.  Default func param2. '],
     'class/funcs':             ['''
struct testClass{
    me void: runTest()<-{
        testFunc2("Pass func arg.  ")
        me derivedClass: DC
        DC.pureVirtualFunc ()
        DefaultParams()
        PassAndDefault("Pass func arg.  ")
    }
    me void: testFunc2(me string: strArg)<-{print(strArg)}
    me void: DefaultParams(me string: defaultParam<-"Default func param1.  ",me string: defaultParam2<-"Default func param2. ")<-{
        print(defaultParam,defaultParam2)
    }
    me void: PassAndDefault(me string: defaultParam<-"Default func param1.  ",me string: defaultParam2<-"Default func param2. ")<-{
        print(defaultParam,defaultParam2)
    }
}
struct pureVirtualClass{
    me void: pureVirtualFunc()
}
struct derivedClass: inherits=pureVirtualClass{
    me void: pureVirtualFunc()<-{
        print("Function was called.")
    }
}
''', 'PGBR:Pass func arg.  Function was called.Default func param1.  Default func param2. Pass func arg.  Default func param2. ',['class/funcDefn','class/funcDecl','class/funcCallArgs', 'class/pureVirtualFunc', 'class/funcDefaultParams', 'class/funcPassAndDefault']],
#####################################################################################################
     'actions/varDecl':      ['struct testClass{me void: runTest()<-{me int: actionVarDecl}}', 'PGB:'],
     'actions/mapDecl':      ['struct testClass{me void: runTest()<-{me Map<me string, me string>:testMap}}', 'PGB:'],
     'actions/decls':        ['''
struct testClass{
    me void: runTest()<-{
        me int: actionVarDecl
        me Map<me string, me string>:testMap
    }
}''', 'PGB:',['actions/varDecl','actions/mapDecl']],
#####################################################################################################
     'actions/varAsgn':      ['struct testClass{me void: runTest()<-{me int: actionVarAsgn \n actionVarAsgn<-4567 \n print(actionVarAsgn)}}', 'PGBR:4567'],
     'actions/flagAsgn':     ['struct testClass{flag: isStart \n me void: runTest()<-{print(isStart) \n isStart<-true \n print("-") \n  print(isStart)}}', 'PGBR:0-1'],
     'actions/modeAsgn':     ['struct testClass{me mode[small, medium, large]: myMode \n me void: runTest()<-{print(myModeStrings[myMode]+ "-") \n myMode<- large \n print(myModeStrings[myMode])}}', 'PGBR:small-large'],
     'actions/stringAsgn':   ['struct testClass{me void: runTest()<-{me string: actionStrAsgn \n actionStrAsgn<-"Hello" \n print(actionStrAsgn)}}', 'PGBR:Hello'],
     #'actions/listAsgn':      ['struct testClass{\nme void: runTest()<-{\nme List<me string>: testList \ntestList[0] <- "HELLO" \nprint(testList[0])}}', 'PGBR:HELLO'],
     'actions/mapAsgn':      ['struct testClass{me void: runTest()<-{me Map<me string, me string>:testMap \n testMap["key0"]<-"value0" \n print(testMap["key0"])}}', 'PGBR:value0'],
     #'actions/dictAsgn':
     #'actions/mapPush':     ['struct testClass{me void: runTest()<-{me List<me string, me string>:testMap<-{"key":"value"}}}', 'PGB:'],
     'actions/assigns':      ['''
struct testClass{
    flag: isStart
    me mode[small, medium, large]: myMode
    me void: runTest()<-{
        me int: actionVarAsgn
        actionVarAsgn<-4567
        print(actionVarAsgn)
        print(" Bool:")
        print(isStart)
        isStart<-true
        print(" Bool:")
        print(isStart)
        print(" Mode:"+myModeStrings[myMode])
        myMode<- large
        print(" Mode:"+myModeStrings[myMode])
        me string: actionStrAsgn
        actionStrAsgn<-"Hello"
        print(" AsgnStr:"+actionStrAsgn)
        //me List<me string>: testList
        //testList[0] <- "HELLO"
        //print(" AsgnLst:", testList[0])
        me Map<me string, me string>:testMap
        testMap["key0"]<-"value0"
        print(" IDX:"+testMap["key0"])
    }
}''', 'PGBR:4567 Bool:0 Bool:1 Mode:small Mode:large AsgnStr:Hello IDX:value0',['actions/varAsgn','actions/flagAsgn','actions/modeAsgn','actions/stringAsgn','actions/mapAsgn']],
#####################################################################################################
     'actions/conditional':  ['struct testClass{me void: runTest()<-{testFunc(true)}\nme void: testFunc(me bool: isTrue)<-{if (isTrue){print("true")}\nelse{print("false")}}}', 'PGB:'],
     'actions/switch':       ['struct testClass{me void: runTest()<-{me int:myInt<-3\nswitch(myInt){case 3:{print("3")}case 2:{print("2")}default:{print("default")}}}}', 'PGBR:3'],
     'actions/misc':         ['''
struct testClass{
    me void: runTest()<-{
        me int:myInt<-3
        testFunc(true)
        testFunc(false)
        switch(myInt){
            case 3:{print("3")}
            case 2:{print("2")}
            default:{print("default")}
        }
    }
    me void: testFunc(me bool: isTrue)<-{
        if (isTrue){print("true ")}
        else{print("false ")}
    }
}''', 'PGBR:true false 3',['actions/conditional','actions/switch']],
#####################################################################################################
# TODO: make tests for 'actions/deleteMapRep'
     'actions/rangeRep':     ['struct testClass{me void: runTest()<-{withEach spec in RANGE(2..6){print(spec," ")}}}', 'PGBR:2 3 4 5 '],
     'actions/backRangeRep': ['struct testClass{me void: runTest()<-{withEach RB in Backward RANGE(2..6){print(RB," ")}}}', 'PGBR:5 4 3 2 '],
     'actions/listRep':      ['struct testClass{me void: runTest()<-{me List<me int>:testList<-[2,13,-22,188]\nwithEach T in testList {print(T," ")}}}', 'PGBR:2 13 -22 188 '],
     'actions/backListRep':  ['struct testClass{me void: runTest()<-{me List<me int>:testListBackward<-[2,13,-22,188]\nwithEach TB in Backward testListBackward {print(TB," ")}}}', 'PGBR:188 -22 13 2 '],
     'actions/listKeyRep':   ['struct testClass{me void: runTest()<-{me List<me int>:testKeyList<-[2,3,5,8,13,21]\nwithEach TK in testKeyList {print(TK_key,"-", TK, " ")}}}', 'PGBR:0-2 1-3 2-5 3-8 4-13 5-21 '],
     'actions/mapRep':       ['struct testClass{me void: runTest()<-{me Map<me string, me string>:testMap\ntestMap["E"]<-"every"\ntestMap["G"]<-"good"\ntestMap["B"]<-"boy"\ntestMap["D"]<-"does"\ntestMap["F"]<-"fine"\nwithEach M in testMap {print(M," ")}}}', 'PGBR:boy does every fine good '],
     'actions/mapKeyRep':    ['struct testClass{me void: runTest()<-{me Map<me string, me string>:testMapKey\ntestMapKey["E"]<-"every"\ntestMapKey["G"]<-"good"\ntestMapKey["B"]<-"boy"\ntestMapKey["D"]<-"does"\ntestMapKey["F"]<-"fine"\nwithEach MK in testMapKey {print(MK_key,"-",MK," ")}}}', 'PGBR:B-boy D-does E-every F-fine G-good '],
     'actions/deleteListRep':['struct testClass{me void: runTest()<-{me List<me int>:testDelList<-[2,3,5,8,13,21]\nwithEach TD in testDelList {if(TD_key==3){testDelList.erase(TD_key)\nTDIdx<-TDIdx-1}\nelse{print(TD, " ")}}}}', 'PGBR:2 3 5 13 21 '],
     'actions/repetitions':  ['''
struct testClass{
    me void: runTest()<-{
        withEach spec in RANGE(2..6) {print(spec," ")}
        withEach RB in Backward RANGE(2..6) {print(RB," ")}
        me List<me int>:testList<-[2,13,-22,188]
        withEach T in testList {print(T," ")}
        me List<me int>:testListBackward<-[2,13,-22,188]
        withEach TB in Backward testListBackward {print(TB," ")}
        me List<me int>:testKeyList<-[2,3,5,8,13,21]
        withEach TK in testKeyList {print(TK_key,"-", TK, " ")}
        me Map<me string, me string>:testMap\ntestMap["E"]<-"every"\ntestMap["G"]<-"good"\ntestMap["B"]<-"boy"\ntestMap["D"]<-"does"\ntestMap["F"]<-"fine"
        withEach M in testMap {print(M," ")}
        me Map<me string, me string>:testMapKey\ntestMapKey["E"]<-"every"\ntestMapKey["G"]<-"good"\ntestMapKey["B"]<-"boy"\ntestMapKey["D"]<-"does"\ntestMapKey["F"]<-"fine"
        withEach MK in testMapKey {print(MK_key,"-",MK," ")}
        me List<me int>:testDelList<-[2,3,5,8,13,21]\nwithEach TD in testDelList {if(TD_key==3){testDelList.erase(TD_key)\nTDIdx<-TDIdx-1}\nelse{print(TD, " ")}}
    }
}''', 'PGBR:2 3 4 5 5 4 3 2 2 13 -22 188 188 -22 13 2 0-2 1-3 2-5 3-8 4-13 5-21 boy does every fine good B-boy D-does E-every F-fine G-good 2 3 5 13 21 ',
    ['actions/rangeRep','actions/backRangeRep','actions/listRep','actions/backListRep','actions/listKeyRep','actions/mapRep','actions/mapKeyRep','actions/deleteListRep']],
###################################################################################################
     'actions/plusEquals':    ['struct testClass{me void: runTest()<-{me int:A<-2 \n A<+-1 \n print(A)}}', 'PGBR:3'],
     'actions/minusEquals':   ['struct testClass{me void: runTest()<-{me int:A<-2 \n A<--1 \n print(A)}}', 'PGBR:1'],
     'actions/multiply':      ['struct testClass{me void: runTest()<-{me int:A<-2 \n print(A*2)}}', 'PGBR:4'],
     'actions/modulo':        ['struct testClass{me void: runTest()<-{me int:A<-9 \n print(A%2)}}', 'PGBR:1'],
     'actions/equalEqual':    ['struct testClass{me void: runTest()<-{me int:A<-9 \n if(A==9){print("p")}}}', 'PGBR:p'],
     'actions/bangEqual':     ['struct testClass{me void: runTest()<-{me int:A<-9 \n if(A!=9){print("f")}\nelse{print("t")}}}', 'PGBR:t'],
     'actions/And':           ['struct testClass{me void: runTest()<-{me int: T<-1; me int: F<-0; if(T&T)    {print("p")}}}','PGBR:p'],
     'actions/Xor':           ['struct testClass{me void: runTest()<-{me int: T<-1; me int: F<-0; if(T^F)    {print("p")}}}','PGBR:p'],
     'actions/Ior':           ['struct testClass{me void: runTest()<-{me int: T<-1; me int: F<-0; if(T|F){print("p")}}}','PGBR:p'],
     'actions/LogAnd':        ['struct testClass{me void: runTest()<-{if(1 and 1){print("p")}}}','PGBR:p'],
     'actions/LogOr':         ['struct testClass{me void: runTest()<-{if(1 or 1) {print("p")}}}','PGBR:p'],
     'actions/lessThan':      ['struct testClass{me void: runTest()<-{if(1<2)    {print("p")}}}','PGBR:p'],
     'actions/lessThanEq':    ['struct testClass{me void: runTest()<-{if(1<=2)   {print("p")}}}','PGBR:p'],
     'actions/greaterThan':   ['struct testClass{me void: runTest()<-{if(2>1)    {print("p")}}}','PGBR:p'],
     'actions/greaterThanEq': ['struct testClass{me void: runTest()<-{if(2>=2)   {print("p")}}}','PGBR:p'],
     'actions/compNullPtrs':  ['struct testClass{me void: runTest()<-{our string: Q \n their string: P \n if(!(P or Q)){print("p")}}}','PGBR:p'],
     'actions/operators':     ['''
struct testClass{
    me void: runTest()<-{
        me int:A<-7
        A<+-1
        print(A)
        A<--1
        print(A)
        print(A*2)
        print(A%2)
        if(A==7){print("==p")}
        if(A!=7){print("f")}else{print("!=p")}
        testAnd()
        testXor()
        testIor()
        if(1 and 1){print("and p")}
        if(1 or 1) {print("or p")}
        if(1<2)    {print("<p")}
        if(1<=2)   {print("<=p")}
        if(2>1)    {print(">p")}
        if(2>=1)   {print(">=p")}
        our string: Q
        their string: P
        if(!(P or Q)){print(" Ptr p")}
    }
    me void: testAnd()<-{
        me int: a <- 0
        me int: b <- 1
        if(a&a){print("&f")}
        if(a&b){print("&f")}
        if(b&a){print("&f")}
        if(b&b){print("&p")}
    }
    me void: testXor()<-{
        me int: a <- 0
        me int: b <- 1
        if(a^a){print("^f")}
        if(a^b){print("^p")}
        if(b^a){print("^p")}
        if(b^b){print("^f")}
    }
    me void: testIor()<-{
        me int: a <- 0
        me int: b <- 1
        if(a|a){print("|f")}
        if(a|b){print("|p")}
        if(b|a){print("|p")}
        if(b|b){print("|p")}
    }
}''', 'PGBR:87141==p!=p&p^p^p|p|p|pand por p<p<=p>p>=p Ptr p',['actions/plusEquals','actions/minusEquals','actions/multiply','actions/modulo','actions/equalEqual','actions/bangEqual', 'actions/And', 'actions/Xor', 'actions/Ior','actions/LogAnd','actions/LogOr','actions/lessThan','actions/lessThanEq','actions/greaterThan','actions/greaterThanEq','actions/compNullPtrs']],
#####################################################################################################
     'actions/defaultme':   ['struct testClass{me void: runTest()<-{me int:A          \n print(A)}}', 'PGBR:0'],
     'actions/arrowme':     ['struct testClass{me void: runTest()<-{me int: A <- 4    \n print(A)}}', 'PGBR:4'],
     'actions/arrowlistme': ['struct testClass{me void: runTest()<-{me int: A<-(4)    \n print(A)}}', 'PGBR:4'],
     'actions/assignVme':   ['struct testClass{me void: runTest()<-{me int:V <- 5     \n me int: A<-V  \n print(A)}}', 'PGBR:5'],
     'actions/assignpVme':  ['struct testClass{me void: runTest()<-{our int:: pV<-4   \n me int: A<-pV \n print(A)}}', 'PGBR:4'],
     'actions/meInits':     ['''
struct testClass{
    me void: runTest()<-{
        me int: V <- 7
        our int:: pV <- 8
        me int: c <- 5
        print(c)
        me int: d <- (6)
        print(d)
        me int: g <- V
        print(g)
        me int: h <- pV
        print(h)
    }
}''', 'PGBR:5678',['actions/defaultme','actions/arrowme','actions/arrowlistme','actions/assignVme','actions/assignpVme' ]],
#####################################################################################################
     #'actions/defaulttheir':  ['struct testClass{me void: runTest()<-{their int:A \n if(A==NULL){print("NULL")} \n else{print(A)}}}', 'PGBR:NULL'],
     #'actions/arrowtheir':    ['struct testClass{me void: runTest()<-{their int: A <- 4  \n print(A)}}', 'PGBR:NULL'],         # Should throw an error
     #'actions/arrowlist':     ['struct testClass{me void: runTest()<-{their int: A <- (4)\n print(A)}}', 'PGBR:NULL'],         # Should throw an error
     #'actions/assignVtheir':  ['struct testClass{me void: runTest()<-{me int:V \n their int: A<-V \n print(A)}}', 'PGBR:NULL'],  # Should throw an error
     'actions/assignpVtheir': ['struct testClass{me void: runTest()<-{their int:: pV<-4  \n their int: A<-pV \n print(A)}}', 'PGBR:4'],
     'actions/assignConstTheir':  ['struct testClass{me void: runTest()<-{const int: A <- 5 \n their int:: B \n B <deep- A \n print(B)}}', 'PGBR:5'],
     'actions/theirInits':    ['''
struct testClass{
    me void: runTest()<-{
        me int: V <- 3
        their int:: pV <- 4
        //their int: a  //make a function called null test
        //if(a == NULL){print("NULL")}
        //else{print(a)}
        //their int: c <- 4
        //print(c)
        //their int: d <- (4)
        //print(d)
        //their int: g <- V // no error here?
        //print(g) // skip need to write check for build failure. low prio
        their int: h <- pV
        print(h)
        //assignConstTheir
        const int: A <- 5
        their int:: B
        B <deep- A
        print(B)
    }
}''', 'PGBR:45',['actions/assignpVtheir','actions/assignConstTheir']],
#####################################################################################################
     'actions/allocateddefaulttheir':  ['struct testClass{me void: runTest()<-{their int:: A     \n print(A)}}', 'PGBR:0'],
     'actions/allocateArrowtheir':     ['struct testClass{me void: runTest()<-{their int:: A<-4  \n print(A)}}', 'PGBR:4'],
     'actions/allocateArrowlistTheir': ['struct testClass{me void: runTest()<-{their int:: A<-(4)\n print(A)}}', 'PGBR:4'],
     'actions/allocateAssignVtheir':   ['struct testClass{me void: runTest()<-{me int:V <- 7     \n their int:: A<-V \n print(A)}}', 'PGBR:7'],
     'actions/allocateAssignpVtheir':  ['struct testClass{me void: runTest()<-{their int:: pV<-8 \n their int:: A<-pV\n print(A)}}', 'PGBR:8'],
     'actions/allocateTheirInits':     ['''
struct testClass{
    me void: runTest()<-{
        me int: V <- 7
        their int:: pV <- 8
        their int:: A
        print(A)
        their int:: C<-5
        print(C)
        their int:: D <- (6)
        print(D)
        their int:: G <- V
        print(G)
        their int:: H <- pV
        print(H)
    }
}''', 'PGBR:05678',['actions/allocateddefaulttheir','actions/allocateArrowtheir','actions/allocateArrowlistTheir','actions/allocateAssignVtheir','actions/allocateAssignpVtheir' ]],
#####################################################################################################
     #'actions/defaultOur':   ['struct testClass{me void: runTest()<-{our int:A \n if(A==NULL){print("NULL")}\nelse{print(A)}}}', 'PGBR:NULL'],
     #'actions/arrowOur':     ['struct testClass{me void: runTest()<-{our int: A <- 4 \n print(A)}}', 'PGBR:NULL'],   # Should throw an error
     #'actions/arrowlistOur': ['struct testClass{me void: runTest()<-{our int: A <- (4) \n print(A)}}', 'PGBR:NULL'], # Should throw an error
     #'actions/assignVOur':   ['struct testClass{me void: runTest()<-{me int:V<-4       \n our int: A<-V  \n print(A)}}', 'PGBR:NULL'],
     'actions/assignpVOur':  ['struct testClass{me void: runTest()<-{our int:: pV<-4 \n our int: A<-pV \n print(A)}}', 'PGBR:4'],
     'actions/ourInits':     ['''
struct testClass{
    me void: runTest()<-{
        me int: V <- 3
        our int:: pV <- 4
        //our int: a  //make a function called null test
        //if(a == NULL){print("NULL")}
        //else{print(a)}
        //our int: c <- 4
        //print(c)
        //our int: d <- (4)
        //print(d)
        //our int: g <- V // no error here?
        //print(g) // skip need to write check for build failure. low prio
        our int: h <- pV
        print(h)
    }
}''', 'PGBR:4',['actions/assignpVOur' ]],
#####################################################################################################
     'actions/allocateddefaultOur':  ['struct testClass{me void: runTest()<-{our int:: A     \n print(A)}}', 'PGBR:0'],
     'actions/allocateArrowOur':     ['struct testClass{me void: runTest()<-{our int:: A<-4  \n print(A)}}', 'PGBR:4'],
     'actions/allocateArrowlistOur': ['struct testClass{me void: runTest()<-{our int:: A<-(4)\n print(A)}} ', 'PGBR:4'],
     'actions/allocateAssignVOur':   ['struct testClass{me void: runTest()<-{me int:V<-4     \n our int:: A<-V \n print(A)}}', 'PGBR:4'],
     'actions/allocateAssignpVOur':  ['struct testClass{me void: runTest()<-{our int:: pV<-4 \n our int:: A<-pV\n print(A)}}', 'PGBR:4'],
     'actions/globalOur':            ['me int: A<-{4}\n print(A)','PGBR:'],
     'actions/allocateOurInits':     ['''
struct testClass{
    me void: runTest()<-{
        me int: V <- 2
        our int:: pV <- 3
        our int:: A
        print(A)
        our int:: C<-5
        print(C)
        our int:: D <- (6)
        print(D)
        our int:: G <- V
        print(G)
        our int:: H <- pV
        print(H)
    }
}''', 'PGBR:05623',['actions/allocateddefaultOur','actions/allocateArrowOur','actions/allocateArrowlistOur','actions/allocateAssignVOur','actions/allocateAssignpVOur']],

#####################################################################################################
     'actions/curlyMeLit':          ['struct testClass{me void: runTest()<-{me int: A{4}      \n print(A)}}', 'PGBR:4'],
     'actions/curlyMeMe':           ['struct testClass{me void: runTest()<-{me int:V <- 5     \n me int: A{V}     \n print(A)}}', 'PGBR:5'],
     'actions/curlyMeOur':          ['struct testClass{me void: runTest()<-{our int:: pV<-4   \n me int: A{pV}    \n print(A)}}', 'PGBR:4'],
     'actions/curlyTheirOur':       ['struct testClass{me void: runTest()<-{our int:: pV<-4   \n their int: A{pV} \n print(A)}}', 'PGBR:4'],
     'actions/curlyOurOur':         ['struct testClass{me void: runTest()<-{our int:: pV<-4   \n our int: A{pV}   \n print(A)}}', 'PGBR:4'],
     'actions/allocCurlyTheirLit':  ['struct testClass{me void: runTest()<-{their int:: A{4}  \n print(A)}}', 'PGBR:4'],
     'actions/allocCurlyTheirMe':   ['struct testClass{me void: runTest()<-{me int:V <- 7     \n their int:: A{V} \n print(A)}}', 'PGBR:7'],
     'actions/allocCurlyTheirOur':  ['struct testClass{me void: runTest()<-{our int:: pV<-8   \n their int:: A{pV}\n print(A)}}', 'PGBR:8'],
     'actions/allocCurlyOurLit':    ['struct testClass{me void: runTest()<-{our int:: A{4}    \n print(A)}}', 'PGBR:4'],
     'actions/allocCurlyOurMe':     ['struct testClass{me void: runTest()<-{me int:V<-4       \n our int:: A{V}   \n print(A)}}', 'PGBR:4'],
     #'actions/allocCurlyOurOur':    ['struct testClass{me void: runTest()<-{our int:: pV<-4   \n our int:: A{pV}  \n print(A)}}', 'PGBR:4'],
     #'actions/curlyVtheir':        ['struct testClass{me void: runTest()<-{me int:V\n their int: A{V}\n print(A)}}', 'PGBR:NULL'],  # Should throw an error
     #'actions/curlyOur':           ['struct testClass{me void: runTest()<-{our int: A{4} \n print(A)}} ', 'PGBR:NULL'],    # Should throw an error
     #'actions/curlyVOur':          ['struct testClass{me void: runTest()<-{me int:V<-4       \n our int: A{V}  \n print(A)}}', 'PGBR:NULL'],
     'actions/curlyParamList':      ['''
struct testClass{
    me void: runTest()<-{
        me int: V <- 2
        our int:: pV <- 3
        me int: A{4}
        print(A)
        me int: B{V}
        print(B)
        me int: C{pV}
        print(C)
        their int: D{pV}
        print(D)
        our int: E{pV}
        print(E)
        their int:: F{5}
        print(F)
        their int:: G{V}
        print(G)
        their int:: H{pV}
        print(H)
        our int:: I{6}
        print(I)
        our int:: J{V}
        print(J)
        //our int:: K{pV}
        //print(K)
    }
}''', 'PGBR:4233352362',['actions/curlyMeLit','actions/curlyMeMe','actions/curlyMeOur','actions/curlyTheirOur','actions/curlyOurOur','actions/allocCurlyTheirLit','actions/allocCurlyTheirMe','actions/allocCurlyTheirOur','actions/allocCurlyOurLit','actions/allocCurlyOurMe']],
#####################################################################################################
     'actions/intToString':     ['struct testClass{me void: runTest()<-{me int: A<-123     \n me string:B<-toString(A) \n print(B)}}', 'PGBR:123'],
     'actions/32intToString':   ['struct testClass{me void: runTest()<-{me int32: A<-123   \n me string:B<-toString(A) \n print(B)}}', 'PGBR:123'],
     'actions/64intToString':   ['struct testClass{me void: runTest()<-{me int64: A<-123   \n me string:B<-toString(A) \n print(B)}}', 'PGBR:123'],
     'actions/stringToInt':     ['struct testClass{me void: runTest()<-{me string: A<-"123"\n me int:B<-stoi(A)        \n print(B)}}', 'PGBR:123'],
     'actions/boolToInt':       ['struct testClass{me void: runTest()<-{me bool: b <- true \n print(toString(b))}}', 'PGBR:true'],
     'actions/typeConversions': ['''
struct testClass{
    me void: runTest()<-{
        testStrConversion()
        testStoi()
    }
    me void: testStrConversion()<-{
        me int: a <- 123
        me bool: b <- true  //maybe add bool to string test later
        print(toString(b))
        me int32: eye32 <- 32
        me int64: eye64 <- 64
        me string: s <- toString(a)
        me string: s32 <- toString(eye32)
        me string: s64 <- toString(eye64)
        print(s)
        print(s32)
        print(s64)
    }
    me void: testStoi()<-{
        me string: s <- "123"
        me int: i <- stoi(s)
        if(i == 123){
            print("pass")
        }
        else{
            print("stoi fail")
        }
    }
}''', 'PGBR:true1233264pass',['actions/intToString','actions/32intToString','actions/64intToString','actions/stringToInt','actions/boolToInt']],


#####################################################################################################

    # TEST CONSTANT VARIABLES

    # const
    'class/structAsgn':        ['struct testClass{ me void: runTest()<-{me A: a{"A"} }}struct A{me string: testStr}', 'PGBR:'],
    # const string
    'class/constStrAsgn':      ['struct testClass{ const string: constStr <- "Hello"  me void: runTest()<-{ print(constStr)}}', 'PGBR:Hello'],
    # const char
    'class/constCharAsgn':     ['struct testClass{ const char: myChar <- "M"    me void: runTest()<-{ print("M")}}', 'PBGR:M'],
    # const double
    'class/constDblAsgn':      ['struct testClass{ const double: pi <- 3.14           me void: runTest()<-{ print(pi)}}', 'PGBR:3.14'],
    # const ints
    'class/constIntAsgn':      ['struct testClass{ const int: constInt <- 123         me void: runTest()<-{ print(constInt)}}',    'PGBR:123'],
    'class/constInt32Asgn':    ['struct testClass{ const int32: constInt32 <- 123       me void: runTest()<-{ print(constInt32)}}',    'PGBR:123'],
    'class/constInt64Asgn':    ['struct testClass{ const int64: constInt64 <- 123       me void: runTest()<-{ print(constInt64)}}',    'PGBR:123'],
    # const uints
    'class/constUint32Asgn':   ['struct testClass { const uint32: constUint32 <- 123    me void: runTest()<-{ print(constUint32)}}', 'PBGR:123'],
    'class/constUint64Asgn':   ['struct testClass { const uint64: constUint64 <- 123    me void: runTest()<-{ print(constUint64)}}', 'PBGR:123'],
    # const bool
    'class/boolAsgn':          ['struct testClass { const bool: myBool <- true  me void runTest()<-{ if(myBool){print("p")} }}', 'PGBR:p'],

    # 'class/Asgn':             ['struct testClass{me void: runTest()<-{}}', 'PGBR:'],
    # 'class/boolAsgn':         ['struct testClass{me void: runTest()<-{}}', 'PGBR:'],

    'class/varAssigns': ['''
struct testClass{
    const string: constStr <- "Hello"
    const double: pi <- 3.14
    me A: a {'A'}
    me void: runTest()<-{
        print(constStr)
        print(pi)
    }
}
struct A{
    me string: testStr
}
''', 'PGBR:Hello3.14', ['class/constStrAsgn', 'class/constDblAsgn', 'class/structAsgn']],
#####################################################################################################


#####################################################################################################
## TODO: add more loop tests?
########################################

}

tags = """
Title = "testXlator"
FileName = "testXlator"
Version = "0.1"
CopyrightMesg = "Copyright (c) 2015-2016 Bruce Long"
Authors = "Bruce Long"
Description = "Xlator Tests."
ProgramOrLibrary = "program"
featuresNeeded = [List]
LicenseText = `This file is part of the "Proteus suite" All Rights Reserved.`
runCode=<runCodeGoesHere>"""

def makeDir(dirToGen):
    try:
        os.makedirs(dirToGen)
    except OSError as exception:
        if exception.errno != errno.EEXIST: raise

def clearErrorFile():
    makeDir("xlatorTests")
    erfClear = open("xlatorTests/failedTests.txt","w")
    erfClear.close()

def writePrepend(fileName, testName):
    with open(fileName, 'r+') as f:
        content = f.read()
        f.seek(0,0) # add global counter to stop the reverse order of the tests?
        f.write(testName.rstrip('\r\n') + "\n" + content)

def writeFile(path, fileName, testString):
    makeDir(path)
    makeDir(path+"/Resources")
    pathName = path + os.sep + fileName
    fo=open(pathName, 'w')
    fo.write(testString)
    fo.close()

def runCmd(workingDirectory, runString):
    pipe = subprocess.Popen(runString, cwd=workingDirectory, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    return out, err

def RunCodeDogPrg(testString):
    path = "xlatorTests"
    fileName = "testXlator.dog"
    writeFile(path, fileName, testString)
    runString ="codeDog " + fileName
    workingDirectory = os.getcwd() + "/" + path
    out, err = runCmd(workingDirectory, runString)
    return out, err

def ExecCodeDogTest(testSpec, buildSpec, testName,toPrint):
    global tags
    global runSpec
    global workingDirectory
    testString = buildSpec+"\n"
    reqSpec =""
    if(len(testSpec)>1):
        colonPos = testSpec[1].find(':')
    else:
        print("Missing Test Spec")
        exit(0)
    willRun = False
    if(colonPos):
        reqSpec = testSpec[1][(colonPos+1):]
        testSpec[1] = testSpec[1][:(colonPos)]
    if(testSpec[1]=='PGB'):
        testString += tags.replace('<runCodeGoesHere>', '``') + "\n"
    elif(testSpec[1]=='PGBR'):
        willRun = True
        testString += tags.replace('<runCodeGoesHere>', '`\nme testClass: TC\nTC.runTest()\n`') + "\n"
    else:
        print(("Unknown test spec: ",testSpec[1]))
        exit(0)

    testString += testSpec[0] + "\n"
    out, err = RunCodeDogPrg(testString)
    #print(("out: ", out))
    if out:
        decodedOut = bytes.decode(out)
        if(decodedOut.find('Marker: Parse Successful')==-1):
            if(toPrint):
                errorFile = open("xlatorTests/failedTests.txt","a")
                errorFile.write("***\nParse Fail***\n")
                errorFile.write(testName + "\n")
                errorFile.write(testSpec[0]+"\n\n")
                errorFile.close()
            #print(decodedOut)
            return "***Parse Fail***"
        if (decodedOut.find('Marker: Code Gen Successful')==-1):
            if(toPrint):
                errorFile = open("xlatorTests/failedTests.txt","a")
                errorFile.write("***\nCode Gen Fail***\n")
                errorFile.write(testName + "\n")
                errorFile.write(testSpec[0]+"\n\n")
                errorFile.close()
            return "***Code Gen Fail***"
        buildMarker = decodedOut.find('Marker: Build Successful')
        if (buildMarker==-1):
            if(toPrint):
                errorFile = open("xlatorTests/failedTests.txt","a")
                errorFile.write("\n***Build Fail***\n")
                errorFile.write(testName + "\n")
                errorFile.write(testSpec[0]+"\n\n")
                errorFile.close()
            return "***Build Fail***"
        if(not willRun):
            return "Success"
        else:
            out, err = runCmd(runDirectory, runSpec)
            decodedOut = bytes.decode(out)
            #print("out: ", out)
            if (reqSpec != ""):
                if (reqSpec == decodedOut):
                    return "Success"
                else:
                    return "***Run Fail*** expected '"+str(reqSpec)+"' not '"+decodedOut+"'"
    else: return "***Error: no out***"

def runDeps(testKey):
    global buildSpec
    global testDefinitions
    depsList=[]
    depsReportText = ""
    if (len(testDefinitions[testKey])>2):
        depsList = testDefinitions[testKey][2]
    for dep in depsList:
        testResult = ExecCodeDogTest(testDefinitions[dep], buildSpec,dep,True)
        depsReportText +=  "        " + dep + " : "+testResult+  "\n"
        if(testResult != "Success"):
            writePrepend("xlatorTests/failedTests.txt",dep)
    return depsReportText

def runListedTests(testsToRun):
    global buildSpec
    global testDefinitions
    clearErrorFile()
    reportText = ""
    for testKey in testsToRun:
        #print(("Running test: ", testKey))
        testResult = ExecCodeDogTest(testDefinitions[testKey], buildSpec, testKey,False)
        print(".")
        reportText+= testKey + ": "+testResult+  "\n"
        if(testResult!="Success"):
            depsReportText = runDeps(testKey)
            reportText+= depsReportText
    return reportText

def gatherListOfTestsToRun(keywordList):
    global testDefinitions
    testList = []
    if len(keywordList)>0:
        testList = keywordList
    else:
        for key in testDefinitions:
            if (len(testDefinitions[key])>2 and  len(testDefinitions[key][2])>0):
                testList.append(key)
    return testList

###################################
# Get command line: tests and xlator name
if len(sys.argv)==1:
    print(("\nUsage:", sys.argv[0], "<xlatorName> [test-names...]\n"))
    exit(0)

xlatorName = sys.argv[1]
testListSpec = sys.argv[2:]

workingDirectory = os.getcwd() + "/xlatorTests"
if (xlatorName == "cpp"):
    buildSpec = "LinuxBuild: Platform='Linux' CPU='amd64' Lang='CPP' optimize='speed';\n"
    buildSpec += "//SwingBuild: Platform='Swing' CPU='JavaVM' Lang='Java' optimize='speed';\n"
    buildSpec += "//SwiftBuild: Platform='Swift' CPU='amd64' Lang='Swift' optimize='speed';"
    runSpec = "./testXlator"
    runDirectory = workingDirectory + "/LinuxBuild"
elif(xlatorName == "swing" or xlatorName == "java" or xlatorName == "Java"):
    buildSpec = "SwingBuild: Platform='Swing' CPU='JavaVM' Lang='Java' optimize='speed';\n"
    buildSpec += "//LinuxBuild: Platform='Linux' CPU='amd64' Lang='CPP' optimize='speed';\n"
    buildSpec += "//SwiftBuild: Platform='Swift' CPU='amd64' Lang='Swift' optimize='speed';"
    runSpec = "java GLOBAL"
    runDirectory = workingDirectory + "/SwingBuild"
elif(xlatorName == "swift" or xlatorName == "Swift" ):
    buildSpec = "SwiftBuild: Platform='Swift' CPU='amd64' Lang='Swift' optimize='speed';\n"
    buildSpec += "//SwingBuild: Platform='Swing' CPU='JavaVM' Lang='Java' optimize='speed';\n"
    buildSpec += "//LinuxBuild: Platform='Linux' CPU='amd64' Lang='CPP' optimize='speed';"
    runSpec = "./testXlator"
    runDirectory = workingDirectory + "/SwiftBuild"
else:
    print(("UNKNOWN XLATOR: ", xlatorName))
    exit(0)

testsToRun = gatherListOfTestsToRun(testListSpec)
reportText = runListedTests(testsToRun)
print("********** T E S T    R E S U L T S **********")
print(reportText)
print("**********************************************")
writePrepend("xlatorTests/failedTests.txt", "Failed tests: \n")
writePrepend("xlatorTests/failedTests.txt","Run on: "+ str(date.today())+"\n\n")
