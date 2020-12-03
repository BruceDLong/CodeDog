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
     'class/simple':        ['struct emptyClass{ }', 'PGB:'],
     'class/intDecl':       ['struct testClass{me int: myInt}', 'PGB:'],
     'class/strDecl':       ['struct testClass{me string: myString}', 'PGB:'],
     'class/int32Decl':     ['struct testClass{me int32: myInt32}', 'PGB:'],
     'class/int64Decl':     ['struct testClass{me int64: myInt64}', 'PGB:'],
     'class/doubleDecl':    ['struct testClass{me double: myDouble}', 'PGB:'],
     'class/uint32Decl':    ['struct testClass{me uint32: myUint32}', 'PGB:'],
     'class/uint64Decl':    ['struct testClass{me uint64: myUint64}', 'PGB:'],
     'class/boolDecl':      ['struct testClass{me bool: myBool}', 'PGB:'],
     'class/constDecl':     ['struct testClass{const int: myConst <- 2}', 'PGB:'],
     'class/charDecl':      ['struct testClass{me char: myChar}', 'PGB:'],
     'class/baseDecls':     ['''
struct testClass{
    me int: myInt
    me string: myString
    me int32: myInt32
    me int64: myInt64
    me double: myDouble
    me uint32: myUint32
    me uint64: myUint64
    me bool: myBool
    const int: myConst <- 2
    me char: myChar
}''', 'PGBR:true',['class/simple', 'class/intDecl', 'class/strDecl', 'class/int32Decl', 'class/int64Decl', 'class/doubleDecl', 'class/uint32Decl', 'class/uint64Decl', 'class/boolDecl', 'class/constDecl', 'class/charDecl']],
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
     #'class/pureVirtualFunc':   ['struct testClass{me void: runTest()<-{me pureVirtualClass::derivedClass: DC\nDC.pureVirtualFunc ()}}\nstruct pureVirtualClass{me void: pureVirtualFunc()}\nstruct pureVirtualClass::derivedClass{me void: pureVirtualFunc()<-{print("Function was called.")}}', 'PGBR:Function was called.'],
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
''', 'PGBR:Pass func arg.  Function was called.Default func param1.  Default func param2. Pass func arg.  Default func param2. ',['class/funcDefn','class/funcDecl','class/funcCallArgs', 'class/funcDefaultParams', 'class/funcPassAndDefault']],
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
     'actions/varAsgn':      ['struct testClass{me void: runTest()<-{me int: actionVarAsgn\nactionVarAsgn<-4567\nprint(actionVarAsgn)}}', 'PGBR:4567'],
     'actions/flagAsgn':     ['struct testClass{flag: isStart\nme void: runTest()<-{print(isStart)\nisStart<-true\nprint("-")\nprint(isStart)}}', 'PGBR:0-1'],
     'actions/modeAsgn':     ['struct testClass{me mode[small, medium, large]: myMode\nme void: runTest()<-{print(myModeStrings[myMode]+ "-")\nmyMode<- large\nprint(myModeStrings[myMode])}}', 'PGBR:small-large'],
     'actions/stringAsgn':   ['struct testClass{me void: runTest()<-{me string: actionStrAsgn\nactionStrAsgn<-"Hello"\nprint(actionStrAsgn)}}', 'PGBR:Hello'],
     'actions/mapAsgn':      ['struct testClass{me void: runTest()<-{me Map<me string, me string>:testMap\ntestMap["key0"]<-"value0"\nprint(testMap["key0"])}}', 'PGBR:value0'],
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
        print(isStart)
        print("-")
        isStart<-true
        print(isStart+ "-")
        print(myModeStrings[myMode]+ "-")
        myMode<- large
        print(myModeStrings[myMode]+ "-")
        me string: actionStrAsgn
        actionStrAsgn<-"Hello"
        print(actionStrAsgn+"-")
        me Map<me string, me string>:testMap
        testMap["key0"]<-"value0"
        print(testMap["key0"])
    }
}''', 'PGBR:45670-small-large-Hello-value0',['actions/varAsgn','actions/flagAsgn','actions/modeAsgn','actions/stringAsgn','actions/mapAsgn']],
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
# TODO: make tests for 'actions/repetitions':  'actions/rangeRep','actions/backRangeRep','actions/listRep','actions/backListRep','actions/listKeyRep','actions/mapRep','actions/mapKeyRep','actions/deleteMapRep','actions/deleteListRep'
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
     'actions/plusEquals':    ['struct testClass{me void: runTest()<-{me int:myInt<-2\nmyInt<+-1\nprint(myInt)}}', 'PGBR:3'],
     'actions/minusEquals':   ['struct testClass{me void: runTest()<-{me int:myInt<-2\nmyInt<--1\nprint(myInt)}}', 'PGBR:1'],
     'actions/multiply':      ['struct testClass{me void: runTest()<-{me int:myInt<-2\nprint(myInt*2)}}', 'PGBR:4'],
     'actions/modulo':        ['struct testClass{me void: runTest()<-{me int:myInt<-9\nprint(myInt%2)}}', 'PGBR:1'],
     'actions/equalEqual':    ['struct testClass{me void: runTest()<-{me int:myInt<-9\nif(myInt==myInt){print("true")}}}', 'PGBR:true'],
     'actions/bangEqual':     ['struct testClass{me void: runTest()<-{me int:myInt<-9\nif(myInt!=myInt){print("fail")}\nelse{print("true")}}}', 'PGBR:true'],
     'actions/And':           ['struct testClass{me void: runTest()<-{if(1&1){print("p")}}}','PGBR:p'],
     'actions/Xor':           ['struct testClass{me void: runTest()<-{if(1^0){print("p")}}}','PGBR:p'],
     'actions/Ior':           ['struct testClass{me void: runTest()<-{if(1|1){print("p")}}}','PGBR:p'],
     'actions/LogAnd':        ['struct testClass{me void: runTest()<-{if(true and true){print("p")}}}','PGBR:p'],
     'actions/LogOr':         ['struct testClass{me void: runTest()<-{if(true or true){print("p")}}}','PGBR:p'],
     'actions/lessThan':      ['struct testClass{me void: runTest()<-{if(1<2){print("p")}}}','PGBR:p'],
     'actions/lessThanEq':    ['struct testClass{me void: runTest()<-{if(1<=2){print("p")}}}','PGBR:p'],
     'actions/greaterThan':   ['struct testClass{me void: runTest()<-{if(2>1){print("p")}}}','PGBR:p'],
     'actions/greaterThanEq': ['struct testClass{me void: runTest()<-{if(2>=2){print("p")}}}','PGBR:p'],
     'actions/operators':     ['''
struct testClass{
    me void: runTest()<-{
        testPE(3)
        testME(3)
        testMultiply(5)
        testModulo(9)
        testequalEqual(1)
        testBangEq()
        testAnd()
        testXor()
        testIor()
        testLogAnd()
        testLogOr()
        testLessThan()
        testLessThanEq()
        testGreaterThan()
        testGreaterThanEq()
    }
    me void: testPE(me int: intArg)<-{
        intArg<+-1
        print(intArg)
    }

    me void: testME(me int: intArg)<-{
        intArg<--1
        print(intArg)
    }

    me void: testMultiply(me int: intArg)<-{
        print(intArg*2)
    }
    me void: testModulo(me int: intArg)<-{
        print(intArg%2)
    }

    me void: testequalEqual(me int: intArg)<-{
        if(intArg == intArg){
            print(" true")
        }else{print(" false")}
    }

    me void: testBangEq()<-{
        me int:myInt<-9
        if(myInt!=myInt){
            print(" fail")
        }
        else{
            print(" true")
        }
    }

    me void: testAnd()<-{
        me int: a <- 0
        me int: b <- 1
        if(a&a){
            print(" fail")
        }
        if(a&b){
            print(" fail")
        }
        if(b&a){
            print(" fail")
        }
        if(b&b){
            print(" Pass")
        }
    }

    me void: testXor()<-{
        me int: a <- 0
        me int: b <- 1
        if(a^a){
            print(" A:fail")
        }
        if(a^b){
            print(" B:pass")
        }
        if(b^a){
            print(" C:pass")
        }
        if(b^b){
            print(" D:fail")
        }
    }

    me void: testIor()<-{
        me int: a <- 0
        me int: b <- 1
        if(a|a){
            print(" A:fail")
        }
        if(a|b){
            print(" B:pass")
        }
        if(b|a){
            print(" C:pass")
        }
        if(b|b){
            print(" D:pass")
        }
    }

    me void: testLogAnd()<-{
        if(true and true){
            print(" logAndPass")
        }
    }

    me void: testLogOr()<-{
        if(true or true){
            print(" logOrPass")
        }
    }

    me void: testLessThan()<-{
        if(1<2){
            print(" p")
        }
    }

    me void: testLessThanEq()<-{
        if(1<=2){
            print("p")
        }
    }

    me void: testGreaterThan()<-{
        if(2>1){
            print("p")
        }
    }

    me void: testGreaterThanEq()<-{
        if(2>=1){
            print("p")
        }
    }
}''', 'PGBR:42101 true true Pass B:pass C:pass B:pass C:pass D:pass logAndPass logOrPass pppp',['actions/plusEquals','actions/minusEquals','actions/multiply','actions/modulo','actions/equalEqual','actions/bangEqual', 'actions/And', 'actions/Xor', 'actions/Ior','actions/LogAnd','actions/LogOr','actions/lessThan','actions/lessThanEq','actions/greaterThan','actions/greaterThanEq']],
#####################################################################################################
     'actions/defaultme':   ['struct testClass{me void: runTest()<-{me int:A\nprint(A)}}', 'PGBR:0'],
     'actions/curlyme':     ['struct testClass{me void: runTest()<-{me int: A{4}\n print(A) }} ', 'PGBR:4'],
     'actions/arrowme':     ['struct testClass{me void: runTest()<-{me int: A <- 4\n print(A) }}', 'PGBR:4'],
     'actions/arrowlistme': ['struct testClass{me void: runTest()<-{their int: A <- (4)\n print(A)}}', 'PGBR:4'],
     'actions/curlyVme':    ['struct testClass{me void: runTest()<-{me int:V \n their int:: pV\nme int: A{V}\n print(A)}}', 'PGBR:0'],
     'actions/curlypVme':   ['struct testClass{me void: runTest()<-{me int:V \n their int:: pV\nme int: A{pV}\n print(A)}}', 'PGBR:0'],
     'actions/assignVme':   ['struct testClass{me void: runTest()<-{me int:V \n their int:: pV\nme int: A<-V\n print(A)}}', 'PGBR:0'],
     'actions/assignpVme':  ['struct testClass{me void: runTest()<-{me int:V \n their int:: pV\nme int: A<-pV\n print(A)}}', 'PGBR:0'],
     'actions/meInits':     ['''
struct testClass{
    me void: runTest()<-{
        me int: V
        their int:: pV
        me int: a
        me int: b{4}
        print(b)
        me int: c <- 4
        print(c)
        me int: d <- (4)
        print(d)
        me int: e{V}
        print(e)
        me int: f{pV}
        print(f)
        me int: g <- V
        print(g)
        me int: h <- pV
        print(h)
    }
}''', 'PGBR:04440000',['actions/defaultme','actions/curlyme','actions/arrowme','actions/arrowlistme','actions/curlyVme','actions/curlypVme','actions/assignVme','actions/assignpVme' ]],
#####################################################################################################
     'actions/defaulttheir':  ['struct testClass{me void: runTest()<-{their int:A\nif(A==NULL){print("NULL")}\nelse{print(A)}}}', 'PGBR:NULL'],
     'actions/curlytheir':    ['struct testClass{me void: runTest()<-{their int: A{4}\n print(A) }} ', 'PGBR:NULL'],
     'actions/arrowtheir':    ['struct testClass{me void: runTest()<-{their int: A <- 4\n print(A) }}', 'PGBR:NULL'],
     'actions/arrowlist':     ['struct testClass{me void: runTest()<-{their int: A <- (4)\n print(A)}}', 'PGBR:NULL'],
     'actions/curlyVtheir':   ['struct testClass{me void: runTest()<-{me int:V \n their int:: pV\ntheir int: A{V}\n print(A)}}', 'PGBR:NULL'],
     'actions/curlypVtheir':  ['struct testClass{me void: runTest()<-{me int:V \n their int:: pV\ntheir int: A{pV}\n print(A)}}', 'PGBR:0'],
     'actions/assignVtheir':  ['struct testClass{me void: runTest()<-{me int:V \n their int:: pV\ntheir int: A<-V\n print(A)}}', 'PGBR:NULL'],
     'actions/assignpVtheir': ['struct testClass{me void: runTest()<-{me int:V \n their int:: pV\ntheir int: A<-pV\n print(A)}}', 'PGBR:0'],
     'actions/theirInits':    ['''
struct testClass{
    me void: runTest()<-{
        me int: V
        their int:: pV
        their int: a  //make a function called null test
        if(a == NULL){print("NULL")}
        else{print(a)}
        their int: b{4}  //build fail
        print(b)
        their int: c <- 4 //should I be using Try:, Except:   here?
        print(c)
        their int: d <- (4)
        print(d)
        their int: e{V}
        print(e)
        their int: f{pV}
        print(f)
        their int: g <- V // no error here?
        print(g) // skip need to write check for build failure. low prio
        their int: h <- pV
        print(h)
    }
}''', 'PGBR:NULL',['actions/defaulttheir','actions/curlytheir','actions/arrowtheir','actions/arrowlist','actions/curlyVtheir','actions/curlypVtheir','actions/assignVtheir','actions/assignpVtheir' ]],
#####################################################################################################
     'actions/allocateddefaulttheir':  ['struct testClass{me void: runTest()<-{their int:: A\nprint(A)}}', 'PGBR:0'],
     'actions/allocateCurlytheir':     ['struct testClass{me void: runTest()<-{their int:: A{4}\nprint(A) }}', 'PGBR:4'],
     'actions/allocateArrowtheir':     ['struct testClass{me void: runTest()<-{their int:: A<-4\nprint(A) }}', 'PGBR:4'],
     'actions/allocateArrowlistTheir': ['struct testClass{me void: runTest()<-{their int:: A <- (4)\nprint(A) }}', 'PGBR:4'],
     'actions/allocateCurlyVtheir':    ['struct testClass{me void: runTest()<-{me int:V \n their int:: pV\ntheir int:: A{V}\n print(A)}} ', 'PGBR:0'],
     'actions/allocateCurlypVtheir':   ['struct testClass{me void: runTest()<-{me int:V \n their int:: pV\ntheir int:: A{pV}\n print(A)}} ', 'PGBR:0'],
     'actions/allocateAssignVtheir':   ['struct testClass{me void: runTest()<-{me int:V \n their int:: pV\ntheir int:: A<-V\n print(A)}}', 'PGBR:0'],
     'actions/allocateAssignpVtheir':  ['struct testClass{me void: runTest()<-{me int:V \n their int:: pV\ntheir int:: A<-pV\n print(A)}}', 'PGBR:0'],
     'actions/allocateTheirInits':     ['''
struct testClass{
    me void: runTest()<-{
        me int: V
        their int:: pV
        their int:: A
        print(A)
        their int:: B{4} //causing build fail
        print(B)
        their int:: C<-4
        print(C)
        their int:: D <- (4)
        print(D)
        their int:: E{V}  //causing build fail
        print(E)
        their int:: F{pV}
        print(F)
        their int:: G <- V
        print(G)
        their int:: H <- pV  //causing build fail
        print(H)
    }
}''', 'PGBR:04400',['actions/allocateddefaulttheir','actions/allocateCurlytheir','actions/allocateArrowtheir','actions/allocateArrowlistTheir','actions/allocateCurlyVtheir','actions/allocateCurlypVtheir','actions/allocateAssignVtheir','actions/allocateAssignpVtheir' ]],
#####################################################################################################
     'actions/defaultOur':   ['struct testClass{me void: runTest()<-{our int:A\nif(A==NULL){print("NULL")}\nelse{print(A)}}}', 'PGBR:NULL'],
     'actions/curlyOur':     ['struct testClass{me void: runTest()<-{our int: A{4}\n print(A) }} ', 'PGBR:NULL'],
     'actions/arrowOur':     ['struct testClass{me void: runTest()<-{our int: A <- 4\n print(A) }}', 'PGBR:NULL'],
     'actions/arrowlistOur': ['struct testClass{me void: runTest()<-{our int: A <- (4)\n print(A)}}', 'PGBR:NULL'],
     'actions/curlyVOur':    ['struct testClass{me void: runTest()<-{me int:V \n their int:: pV\nour int: A{V}\n print(A)}}', 'PGBR:NULL'],
     'actions/curlypVOur':   ['struct testClass{me void: runTest()<-{me int:V \n their int:: pV\nour int: A{pV}\n print(A)}}', 'PGBR:0'],
     'actions/assignVOur':   ['struct testClass{me void: runTest()<-{me int:V \n their int:: pV\nour int: A<-V\n print(A)}}', 'PGBR:NULL'],
     'actions/assignpVOur':  ['struct testClass{me void: runTest()<-{me int:V \n their int:: pV\nour int: A<-pV\n print(A)}}', 'PGBR:0'],
     'actions/ourInits':     ['''
struct testClass{
    me void: runTest()<-{
        me int: V
        their int:: pV
        our int: a  //make a function called null test
        if(a == NULL){
            print("NULL")
        }
        else{
            print(a)
        }
        our int: b{4}  //build fail
        print(b)
        our int: c <- 4
        print(c)
        our int: d <- {4}
        print(d)
        our int: e{V}
        print(e)
        our int: f{pV}
        print(f)
        our int: g <- V // no error here?
        print(g) // skip need to write check for build failure. low prio
        our int: h <- pV
        print(h)

    }
}''', 'PGBR:NULL',['actions/defaultOur','actions/curlyOur','actions/arrowOur','actions/arrowlist','actions/curlyVOur','actions/curlypVOur','actions/assignVOur','actions/assignpVOur' ]],
#####################################################################################################
     'actions/allocateddefaultOur':  ['struct testClass{me void: runTest()<-{our int:: A\nprint(A)}}', 'PGBR:0'],
     'actions/allocateCurlyOur':     ['struct testClass{me void: runTest()<-{our int:: A{4}\nprint(A) }}', 'PGBR:4'],
     'actions/allocateArrowOur':     ['struct testClass{me void: runTest()<-{our int:: A<-4\nprint(A) }}', 'PGBR:4'],
     'actions/allocateArrowlistOur': ['struct testClass{me void: runTest()<-{our int:: A <- (4)\nprint(A) ', 'PGBR:4'],
     'actions/allocateCurlyVOur':    ['struct testClass{me void: runTest()<-{me int:V \ntheir int:: pV\nour int:: A{V}\n print(A)}} ', 'PGBR:0'],
     'actions/allocateCurlypVOur':   ['struct testClass{me void: runTest()<-{me int:V \ntheir int:: pV\nour int:: A{pV}\n print(A)}} ', 'PGBR:0'],
     'actions/allocateAssignVOur':   ['struct testClass{me void: runTest()<-{me int:V \ntheir int:: pV\nour int:: A<-V\n print(A)}}', 'PGBR:0'],
     'actions/allocateAssignpVOur':  ['struct testClass{me void: runTest()<-{their int:: pV<-5\nour int:: A<-pV\n print(A)}}', 'PGBR:5'],
     'actions/globalOur':            ['me int: A<-{4}\nprint(A)','PGBR:'],
     'actions/allocateOurInits':     ['''
struct testClass{
    me void: runTest()<-{
        me int: V
        their int:: pV
        our int:: A
        print(A)
        our int:: B{4} //causing build fail
        print(B)
        our int:: C<-4
        print(C)
        our int:: D <- (4)
        print(D)
        our int:: E{V}  //causing build fail
        print(E)
        our int:: F{pV}
        print(F)
        our int:: G <- V
        print(G)
        our int:: H <- pV  //causing build fail
        print(H)
    }
}''', 'PGBR:04400',['actions/allocateddefaultOur','actions/allocateCurlyOur','actions/allocateArrowOur','actions/allocateArrowlistOur','actions/allocateCurlyVOur','actions/allocateCurlypVOur','actions/allocateAssignVOur','actions/allocateAssignpVOur' ]],


#####################################################################################################
     'actions/intToString':     ['struct testClass{me void: runTest()<-{me int:A<-123\nme string:B<-toString(A)\nprint(B)}}', 'PGBR:123'],
     'actions/32intToString':   ['struct testClass{me void: runTest()<-{me int32:A<-123\nme string:B<-toString(A)\nprint(B)}}', 'PGBR:123'],
     'actions/64intToString':   ['struct testClass{me void: runTest()<-{me int64:A<-123\nme string:B<-toString(A)\nprint(B)}}', 'PGBR:123'],
     'actions/stringToInt':     ['struct testClass{me void: runTest()<-{me string:A<-"123"\nme int:B<-stoi(A)\nprint(B)}}', 'PGBR:123'],
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

        //b <- toString(b)
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

    me void: insdeExpr()<-{ // not tested
        me uint64: ui64 <- stoi("123456789012345678901234567890")
        me uint32: ui32 <- stoi("123456789012345678901234567890")
        print(ui64+ui32)
    }
}''', 'PGBR:true1233264pass',['actions/intToString','actions/32intToString','actions/64intToString','actions/stringToInt']],
#####################################################################################################
## TODO: add more loop tests?
########################################


}

tags = """BuildCmd = ""
Title = "Infomage - DataDog"
FileName = "testXlator"
Version = "0.1"
CopyrightMesg = "Copyright (c) 2015-2016 Bruce Long"
Authors = "Bruce Long"
Description = "DataDog gives you the numbers of your life."
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
    #print"    workingDirectory: ", workingDirectory
    #print"    runString: " ,runString
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
        print("testResult: ", testKey, ":  ", testResult)
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
    buildSpec = "LinuxBuild: Platform='Linux' CPU='amd64' Lang='CPP' optimize='speed';"
    runSpec = "./testXlator"
    runDirectory = workingDirectory + "/LinuxBuild"
elif(xlatorName == "swing" or xlatorName == "java" or xlatorName == "Java"):
    buildSpec = "SwingBuild: Platform='Java' CPU='JavaVM' Lang='Java' optimize='speed';"
    runSpec = "java GLOBAL"
    runDirectory = workingDirectory + "/SwingBuild"
elif(xlatorName == "swift"):
    buildSpec = "iPhoneBuild: Platform='IOS' CPU='amd64' Lang='Swift' optimize='speed';"
    runSpec = ".build/debug/testXlator"
    runDirectory = workingDirectory + "/SwiftBuild/testXlator"
else:
    print(("UNKNOWN XLATOR: ", xlatorName))
    exit(0)

testsToRun = gatherListOfTestsToRun(testListSpec)
#print "testsToRun: ",testsToRun
reportText = runListedTests(testsToRun)
print("********** T E S T    R E S U L T S **********")
print(reportText)
print("**********************************************")
writePrepend("xlatorTests/failedTests.txt", "Failed tests: \n")
writePrepend("xlatorTests/failedTests.txt","Run on: "+ str(date.today())+"\n\n")
