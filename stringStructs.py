# CodeDog Program Maker
#   This file is code to convert "string" style structures into 'struct' style structures.

import re
import progSpec
import codeDogParser

def codeDogTypeToString(objects, tags, field):
    print "FIELD:", field
    S=''
    fieldName=field['fieldName']
    fieldType=field['fieldType']
    fieldValue =field['value']
    fieldOwner =field['owner']
    if(fieldType == 'flag'):
        if fieldValue!=None and fieldValue!=0 and fieldValue!='false':
            S+='flag: ' + fieldName + ' <- true\n'
        else: S+='flag: ' + fieldName +'\n'
    elif fieldType=='mode':
        if fieldValue!=None:
            S+='mode ['+field['enumList']+']: ' + fieldName + ' <- '+fieldValue+'\n'
        else: S+='mode ['+field['enumList']+']: ' + fieldName +'\n'
    elif fieldOwner=='const':
        print 'const ', fieldType, ': ', fieldName, ' <- ',fieldValue
        #S+='const '+fieldType+': ' + fieldName + ' <- '+fieldValue+'\n'
    elif fieldOwner=='const':
        print "Finish This"

    return S

rules=[]
constDefs=[]
ruleSet={}      # Used to track duplicates
globalFieldCount=0

def genParserCode():
    global rules
    global constDefs
    RuleList=''
    for rule in rules:
        if rule[1]=='term':
            RuleList+='        addTerminalProd("' + rule[0] +'", ' + rule[2] + ', "' + str(rule[3]).replace('::','_') + '")\n'
        elif rule[1]=='nonterm':
            RuleList+='        addNon_TermProd("' + rule[0] +'", ' + rule[2] + ', ' + str(rule[3]).replace('::','_')  + ')\n'

    ConstList=''
    for C in constDefs:
        ConstList+='    const uint32: ' + C[0].replace('::','_') + ' <- ' + str(C[1]) + '\n'

    code= r"""

struct production{
    flag: isTerm
    mode[parseSEQ, parseALT, parseREP, parseOPT, parseAUTO]: prodType
    me string: constStr
    me uint32[list]: items
    void: print(me uint32: SeqPos, me uint32: originPos, me string[their list]: rnames) <- {
        me uint32: ProdType <- prodType
        me string: ProdStr <- ""
        print("[")
        if     (ProdType==parseALT) {ProdStr<-"ALT"}
        else if(ProdType==parseAUTO){ProdStr<-"Aut"}
        else if(ProdType==parseSEQ) {ProdStr<-"SEQ"}
        else if(ProdType==parseREP) {ProdStr<-"REP"}
        print(ProdStr, " from slot:", originPos, ": ")
        if(isTerm){
            if(SeqPos==0) {print(" > ")}
            print('"', constStr,'"')
            if(SeqPos>0) {print(" > ")}
        } else {
            if(ProdType==parseALT and SeqPos==0) {print(" > ")}
            withEach p in items:{
                if(ProdType == parseSEQ and p_key == SeqPos){ print(" > ")}
                if(p_key!=0){
                    if(ProdType==parseALT){print("| ")}
                }
                if(ProdType==parseREP and p_key>0){ print(p, " ")}
                else {print(rnames[p], " ")}
            }
            if(ProdType==parseREP){ print('(Len:%i`SeqPos`)')}
            else {if ((p_key == SeqPos and ProdType == parseSEQ or (ProdType==parseALT and SeqPos>0))) {print(" > ")}}
        }
        print("] ")
    }
}

struct stateRec{
    me uint32: productionID
    me uint32: SeqPosition
    me uint32: originPos
    me uint32: crntPos
    our stateRec: prev
    our stateRec: cause
    our stateRec: next
    our stateRec: child
    //void: print(their production: prod) <- {prod.print(SeqPosition, originPos)}
    void: print(their EParser: EP) <- {
        their production: prod <- EP.grammar[productionID]
        prod.print(SeqPosition, originPos, EP.rnames)}
}
struct stateRecPtr{our stateRec: stateRecPtr}

struct stateSets{
    me stateRecPtr[list]: stateRecs
    me uint64: flags
    //stateSets():flags(0){}
}

struct EParser{
    me string: textToParse
    me uint64: startProduction
    me stateSets[list]: SSets
    me production[list]: grammar
    me bool: parseFound
    our stateRec: lastTopLevelItem
    me string: errorMesg
    me uint32: errLineNum
    me uint32: errCharPos
    me string[list]: rnames

    void: clearGrammar() <- {grammar.clear() rnames.clear()}
    void: addTerminalProd(me string: name, me uint32: ProdType, me string: s) <- {
        me production: P
        P.prodType <- ProdType
        P.isTerm   <- true
        P.constStr <- s
        grammar.pushLast(P)
        rnames.pushLast(name)
    }
    void: addNon_TermProd(me string: name, me uint32: ProdType, me uint32[list]: terms) <- {
        me production: P
        P.prodType <- ProdType
        P.items <- terms
        grammar.pushLast(P)
        rnames.pushLast(name)
    }

    void: dump() <- {
    /*
         withEach crntPos in RANGE(0 .. SSets.size()):{
            their stateSets: SSet <- SSets[crntPos]
            me string: ch <- "x"
            if(crntPos+1 != SSets.size()) {
                ch <- textToParse[crntPos]
            }
            print('SLOT: %i`crntPos` (%s`ch.data()`) - size:%i`(int)SSet->stateRecs.size()`\n')
            withEach SRec in SSet.stateRecs:{
                their production: prod <- grammar[SRec.productionID]
                print("    ")
                SRec.print(this)
                print("\n")
            }
        }
        if(parseFound){print("\nPARSE PASSED!\n\n")}
        else {print("\nPARSE failed.\n\n")}
    */
    }

#CONST_CODE_HERE

    void: populateGrammar() <- {
        clearGrammar()
#GRAMMAR_CODE_HERE

    }

    me void: addProductionToStateSet(me uint32: crntPos, me uint32: productionID, me uint32: SeqPos, me uint32: origin, our stateRec: prev, our stateRec: cause) <- {
        me bool: Duplicate <- false
        their production: prod <- grammar[productionID]
        me uint32: ProdType <- prod.prodType
        withEach item in SSets[crntPos].stateRecs:{ // Don't add duplicates.
            // TODO: change this to be faster. Not a linear search.
            if(item.productionID==productionID and item.originPos==origin){
          //  print ("POSES", item.SeqPosition, ', ', SeqPos, "::")
                if(item.SeqPosition==SeqPos or (ProdType==parseREP and item.SeqPosition+1 == SeqPos)){
          //          print("############ DUPLICATE rule#", productionID, " at slot ", crntPos, ", POS:", SeqPos, "\n")
                    Duplicate <- true
                }
            }
        }

        me bool: thisIsTopLevelItem <- false
        if(productionID==startProduction and origin==0){
            thisIsTopLevelItem <- true
            if(SeqPos==prod.items.size()){
                parseFound <- true
             // TODO: investigate the cases where the line below prints. There could be a subtle bug.
               // print(" <PARSE PASSES HERE> ")
            }
        }

        if(!Duplicate){
            if(ProdType == parseSEQ or ProdType == parseREP or ProdType == parseALT or ProdType == parseAUTO){
                our stateRec: newStateRecPtr Allocate(newStateRecPtr)
                newStateRecPtr.productionID <- productionID
                newStateRecPtr.SeqPosition <- SeqPos
                newStateRecPtr.originPos <- origin
                newStateRecPtr.crntPos <- crntPos
                newStateRecPtr.prev <- prev
                newStateRecPtr.cause <- cause
                if(thisIsTopLevelItem) {lastTopLevelItem <- newStateRecPtr}
                SSets[crntPos].stateRecs.pushLast(newStateRecPtr)
  //              print("############ ADDING To SLOT ", crntPos, ":")
  //              newStateRecPtr.print(this)
                applyPartialCompletion(newStateRecPtr)
  //              print("\n")
            } //else {print("  Unknown ProductionType:", ProdType, "\n")}
        }

        if(ProdType == parseALT and SeqPos==0){
           // print("  ALT-LIST\n")
            withEach AltProd in prod.items:{
   //             print("                                  ALT: ")
                addProductionToStateSet(crntPos, AltProd, 0, origin, prev, cause)
            }
        } else if(ProdType == parseAUTO and productionID == ws and SeqPos==0){  // Whitespace is nullable
            addProductionToStateSet(crntPos, productionID, 1, origin, prev, cause)
        }
    }

    me void: initPosStateSets(me uint64: startProd, me string: txt) <- {
       // print('Will parse "', txt, '" with rule ', startProd, '.\n')
        startProduction <- startProd
        textToParse <- txt
        SSets.clear()
        withEach i in RANGE(0 .. txt.size()+1):{
            me stateSets: newSSet
            SSets.pushLast(newSSet)
        }
        addProductionToStateSet(0, startProduction, 0, 0, NULL, NULL)
    }


    me int64: chkStr(me uint32: pos, me string: s) <- {
        me uint32: L <- s.size()
        if(pos+L > textToParse.size()){return(-1)}
        withEach i in RANGE(0 .. L):{
            if( s[i] != textToParse[pos+i]) {
  //              print("                                 chkStr FAILED\n")
                return(-1)
            }
        }
  //      print("                                 chkStr PASSED\n")
        return(L)
    }

    me int64: scrapeUntil(me uint32:pos, me string:endChar) <- {
        me char: ender <- endChar[0]
        me char: ch
        me uint32: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize):{
            ch <- textToParse[p]
            if(ch==ender){return(p-pos)}
        }
        return(-1)
    }

    me int64: escapedScrapeUntil(me uint32:pos, me string:endChar) <- {
        me char: ch
        me string: prevCharStr <- " "
        me char: prevChar <- prevCharStr[0]
        me char: ender <- endChar[0]
        me uint32: txtSize <- textToParse.size()
        me string: escCharStr <- "\\ "
        me char: escChar <- escCharStr[0]
        withEach p in RANGE(pos .. txtSize):{
            ch <- textToParse[p]
            if(prevChar!=escChar and ch==ender){return(p-pos)}
            if(prevChar==escChar and ch==escChar) {prevChar<-escCharStr[1]}
            else {prevChar <- ch}
        }
        return(-1)
    }


    me int64: scrapeAlphaSeq(me uint32: pos) <- {
        me char: ch
        me uint32: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize):{
            ch <- textToParse[p]
            if(isalpha(ch)){}else{if(p==pos){return(-1)} else{return(p-pos)}}
        }
        return(txtSize-pos)
    }
    me int64: scrapeUintSeq(me uint32: pos) <- {
        me char: ch
        me uint32: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize):{
            ch <- textToParse[p]
            if(isdigit(ch)){}else{if(p==pos){return(-1)} else{return(p-pos)}}
        }
        return(txtSize-pos)
    }
    me int64: scrapeAlphaNumSeq(me uint32: pos) <- {
        me char: ch
        me uint32: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize):{
            ch <- textToParse[p]
            if(isalnum(ch)){}else{if(p==pos){return(-1)} else{return(p-pos)}}
        }
        return(txtSize-pos)
    }
    me int64: scrapeAlphaNum_Seq(me uint32: pos) <- {
        me char: ch
        me string: chars <- "_"
        me uint32: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize):{
            ch <- textToParse[p]
            if(isalnum(ch) or ch==chars[0]){}else{if(p==pos){return(-1)} else{return(p-pos)}}
        }
        return(txtSize-pos)
    }

    me int64: scrapePrintableSeq(me uint32: pos) <- {
        me char: ch
        me uint32: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize):{
            ch <- textToParse[p]
            if(isprint(ch)){}else{if(p==pos){return(-1)} else{return(p-pos)}}
        }
        return(txtSize-pos)
    }

    me int64: scrapeWS(me uint32: pos) <- {
        me char: ch
        me uint32: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize):{
            ch <- textToParse[p]
            if(isspace(ch)){}else{if(p==pos){return(-1)} else{return(p-pos)}}
        }
        return(txtSize-pos)
    }

    me int64: scrapeQuotedStr1(me uint32: pos) <- {
        if(chkStr(pos, "'")>=0){pos <- pos+1}else{return(-1)}
        me int64: sLen <- escapedScrapeUntil(pos, "'")
        if(sLen<0){return(-1)}
        return(sLen+2)
    }

    me int64: scrapeQuotedStr2(me uint32: pos) <- {
        if(chkStr(pos, "\"")>=0){pos <- pos+1}else{return(-1)}
        me int64: sLen <- escapedScrapeUntil(pos, "\"")
        if(sLen<0){return(-1)}
        return(sLen+2)
    }
    me int64: scrapeCID(me uint32: pos) <- {
        me uint32: txtSize <- textToParse.size()
        me string: chars <- "_"
        if(pos >= txtSize){
            // Set I/O Error: Read past EOS
            return(-1)
        }
        me char: ch <- textToParse[pos]
        if(isalpha(ch) or ch==chars[0]){
            return(scrapeAlphaNum_Seq(pos)+1)
        } else {return(-1)}
    }
    // TODO: me int64: scrapeUniID(me uint32: pos) <- { }

    me int64: scrapeIntSeq(me uint32: pos) <- {
        me char: ch <- textToParse[pos]
        me uint32: txtSize <- textToParse.size()
        me uint32: initialChars <- 0
        me string: chars <- "+-"
        if(pos >= txtSize){
            // Set I/O Error: Read past EOS
            return(-1)
        }
        if(ch==chars[0] or ch==chars[1]){ initialChars <- 1}
        return(scrapeUintSeq(pos)+initialChars)
    }
    // TODO: me uint32: scrapeRdxSeq(me uint32: pos) <- { }

    me int64: scrapeToEOL(me uint32: pos) <- {
        return(scrapeUntil(pos, "\\n"))
    }
    me int64: textMatches(me uint32: ProdID, me uint32: pos) <- {
        their production: Prod <- grammar[ProdID]
 //       print('    MATCHING "%s`Prod->constStr.data()`"... ')
        me uint32: prodType <- Prod.prodType
        if(prodType==parseSEQ){ //prod is simple text match
            return(chkStr(pos, Prod.constStr))
        } else{if(prodType==parseAUTO){
 //           print("\n")
            if(ProdID==alphaSeq)    {return(scrapeAlphaSeq(pos))}
            if(ProdID==uintSeq)     {return(scrapeUintSeq(pos))}
            if(ProdID==alphaNumSeq) {return(scrapeAlphaNumSeq(pos))}
            if(ProdID==printables)  {return(scrapePrintableSeq(pos))}
            if(ProdID==ws)          {return(scrapeWS(pos))}
            if(ProdID==quotedStr1)  {return(scrapeQuotedStr1(pos))}
            if(ProdID==quotedStr2)  {return(scrapeQuotedStr2(pos))}
            if(ProdID==CID)         {return(scrapeCID(pos))}
         //   if(ProdID==UniID)       {return(scrapeUniID(pos))}
            if(ProdID==intSeq)      {return(scrapeIntSeq(pos))}
         //   if(ProdID==RdxSeq)      {return(scrapeRdxSeq(pos))}
            if(ProdID==toEOL)       {return(scrapeToEOL(pos))}

        }}
        print("Huh???\n")
        return(-1)
    }

    //////////////// Late Completion Code
    //  This code handles the case where productions are added with the same origin (crntPos) as their (null) predecessor and must have completions applied from past completions.
    our stateRec[list]: SRecsToComplete
    me int32: crntPos

    void: resetCompletions(me int32: CrntPos) <- {
        SRecsToComplete.clear()
        crntPos <- CrntPos
    }

    void: registerCompletion(our stateRec: SRecToComplete) <- {
        SRecsToComplete.pushLast(SRecToComplete)
    }

    void: applyPartialCompletion(our stateRec: backSRec) <- {
        their production: backProd <- grammar[backSRec.productionID]
      //  print('                Checking New Item :') backSRec.print(this)
        me uint32: prodTypeFlag <- backProd.prodType
        me uint32: backSRecSeqPos <- backSRec.SeqPosition
        withEach SRec in SRecsToComplete:{
            if(!(crntPos==SRec.originPos and backSRec.productionID==SRec.productionID and backSRec.SeqPosition==SRec.SeqPosition and backSRec.originPos==SRec.originPos)){
                if(prodTypeFlag==parseREP){
                    me uint32: MAX_ITEMS  <- backProd.items[2]
                    if((backSRecSeqPos < MAX_ITEMS or MAX_ITEMS==0) and backProd.items[0] == SRec.productionID ){
    //                    print(" ADVANCING REP: ")
                        addProductionToStateSet(crntPos, backSRec.productionID, backSRecSeqPos+1, backSRec.originPos, backSRec, SRec)
                    }// else{print(" TOO MANY REPS\n")}
                } else if(prodTypeFlag==parseSEQ){
                    if(backSRecSeqPos < backProd.items.size() and backProd.items[backSRecSeqPos] == SRec.productionID){
     //                   print(" ADVANCING SEQ: ")
                        addProductionToStateSet(crntPos, backSRec.productionID, backSRecSeqPos+1, backSRec.originPos, backSRec, SRec)
                    }// else {print(" SEQ is NOT ADVANCING  \n")}
                } else if(prodTypeFlag==parseALT){
                    if(backSRecSeqPos == 0){
                        withEach backAltProdID in backProd.items:{
                            if(backAltProdID==SRec.productionID){
    //                            print(" ADVANCING ALT: ")
                                addProductionToStateSet(crntPos, backSRec.productionID, backSRecSeqPos+1, backSRec.originPos, backSRec, SRec)
                                break()
                            } //else {if(backAltProdID_key) {print("                                  ")} print(" SKIP ALT\n")}
                        }
                    }
                } //else {print(" NOTHING for prodType ", prodTypeFlag, "\n")}
            } //else {print("Triggering Item... Skipping.\n")}
        }
    }

    /////////////////////////////////////

    void: complete(our stateRec: SRec, me int32: crntPos) <- {
    //    print('        COMPLETING: check items at origin %i`SRec->originPos`... \n')
        registerCompletion(SRec)
        their stateSets: SSet  <- SSets[SRec.originPos]
        withEach backSRec in SSet.stateRecs:{
            their production: backProd <- grammar[backSRec.productionID]
    //        print('                Checking Item #%i`backSRec_key`: ')
            me uint32: prodTypeFlag <- backProd.prodType
            me uint32: backSRecSeqPos <- backSRec.SeqPosition
            if(!(crntPos==SRec.originPos and backSRec.productionID==SRec.productionID and backSRec.SeqPosition==SRec.SeqPosition and backSRec.originPos==SRec.originPos)){
                if(prodTypeFlag==parseREP){
                    me uint32: MAX_ITEMS  <- backProd.items[2]
                    if((backSRecSeqPos < MAX_ITEMS or MAX_ITEMS==0) and backProd.items[0] == SRec.productionID ){
    //                    print(" ADVANCING REP: ")
                        addProductionToStateSet(crntPos, backSRec.productionID, backSRecSeqPos+1, backSRec.originPos, backSRec, SRec)
                    } //else{print(" TOO MANY REPS\n")}
                } else if(prodTypeFlag==parseSEQ){
                    if(backSRecSeqPos < backProd.items.size() and backProd.items[backSRecSeqPos] == SRec.productionID){
     //                   print(" ADVANCING SEQ: ")
                        addProductionToStateSet(crntPos, backSRec.productionID, backSRecSeqPos+1, backSRec.originPos, backSRec, SRec)
                    }// else {print(" SEQ is NOT ADVANCING  \n")}
                } else if(prodTypeFlag==parseALT){
                    if(backSRecSeqPos == 0){
                        withEach backAltProdID in backProd.items:{
                            if(backAltProdID==SRec.productionID){
     //                           print(" ADVANCING ALT: ")
                                addProductionToStateSet(crntPos, backSRec.productionID, backSRecSeqPos+1, backSRec.originPos, backSRec, SRec)
                                break()
                            } //else {if(backAltProdID_key) {print("                                  ")} print(" SKIP ALT\n")}
                        }
                    }
                }// else {print(" NOTHING for prodType ", prodTypeFlag, "\n")}
            } //else {print("Triggering Item... Skipping.\n")}
        }
    //    print("\n")
    }

    me bool: ruleIsDone(me bool: isTerminal, me uint32: seqPos, me uint32: ProdType, me uint32: numItems)<-{
        if(isTerminal and seqPos==1) {return(true)}
        if(!isTerminal){
            if(ProdType==parseSEQ and seqPos==numItems) {return(true)}
            if(ProdType==parseALT and seqPos==1) {return(true)}
        }
        return(false)
    }

    void: doParse() <- {
        parseFound <- false
        withEach crntPos in RANGE(0 .. SSets.size()):{
            their stateSets: SSet <- SSets[crntPos]

    //        print('\n\n%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%   PROCESSING SLOT: %i`crntPos` "%s`ch.data()`"   %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n')
            resetCompletions(crntPos)
            withEach SRec in SSet.stateRecs:{
//TODO: above loop tracker doesn't work in Java and below doesn't work in C++ without removing the *
            //withEach crntSRec in RANGE(0 .. SSet.stateRecs.size()):{
                //our stateRec: SRec <- SSet.stateRecs[crntSRec]
                their production: prod <- grammar[SRec.productionID]
                me uint32: ProdType <- prod.prodType
                me bool  : isTerminal <- (prod.isTerm != 0)
                me uint32: seqPos <- SRec.SeqPosition
     //           print('    PROCESSING-RECORD #%i`SRec_key`:')
    //            SRec.print(this)
                if(ruleIsDone(isTerminal, seqPos, ProdType, prod.items.size())){             // COMPLETER
                    complete(SRec, crntPos)  // Notate that SEQ is finished, actually add parent's follower.
                }else{
                    if(isTerminal){       // SCANNER
                        // print("SCANNING for matching termiinal...\n") // Scanning means Testing for a Matching terminal
                        me int64: len <- textMatches(SRec.productionID, crntPos)
                        if(len>=0 and crntPos+len<SSets.size()){ // if match succeeded
                            addProductionToStateSet(crntPos+len, SRec.productionID, 1, crntPos, SRec, NULL)  // Notate that terminal is finished, mark for adding parent's follower.
                        }
                    }else{ // non-terminal                           // PREDICTOR
                        //print("NON_TERMINAL \n")
                        if(ProdType == parseREP){
                            me uint32: MIN_ITEMS <- prod.items[1]
                            me uint32: MAX_ITEMS <- prod.items[2]
                            me bool: must_be   <- seqPos < MIN_ITEMS
                            me bool: cannot_be <- seqPos > MAX_ITEMS and (MAX_ITEMS!=0)
                            if(!must_be){
                                complete(SRec, crntPos)
     //                           print("         REP (TENT): ")
                                addProductionToStateSet(crntPos, prod.items[0], 0, crntPos, SRec, NULL) // Tentative
                            } else {if(!cannot_be){
     //                           print("         REP: ")
                                addProductionToStateSet(crntPos, prod.items[0], 0, crntPos, SRec, NULL)
                            }}
                        } else { // Not a REP
    //                        print("         SEQ|ALT: ")
                            addProductionToStateSet(crntPos, prod.items[seqPos], 0, crntPos, SRec, NULL)  // Add a cause SEQ with cursor at the very beginning. (0)
                        }
                    }
                }
            }
        }
  //      print("\n\n#####################################\n")
  //      dump()
    }

    void: countLinesToCharPos(me uint32: charPos) <- {
        errLineNum <- 1
        me uint32: lastLinePos <- 0
        withEach C in RANGE(0..charPos):{
            me uint32: LHS <- textToParse[C]
            if(LHS == 13){
                errLineNum <- errLineNum+1
                lastLinePos <- C
            }
        }
        errCharPos <- charPos-lastLinePos+1
    }

    me bool: doesParseHaveError() <- {
  //      logMesg("\n\nChecking for Parse Errors...\n")
        errorMesg <- ""
        me uint32: lastSSetIDX <- SSets.size()
        me uint32: lastPosWithItems <- 0
        withEach ssetIDX in Backward RANGE(0 .. lastSSetIDX):{
            their stateSets: SSet <- SSets[ssetIDX]
            me uint32: numItems <- SSet.stateRecs.size()
            if(numItems>0 and lastPosWithItems==0){lastPosWithItems <- ssetIDX}
         //   print("Position ", ssetIDX, " has ", numItems, "items.\n")
        }
  //      print("lastPosWithItems:", lastPosWithItems, "\n")

        their stateSets: lastSSet <- SSets[lastPosWithItems]

        me uint32: lastSRecIDX <- lastSSet.stateRecs.size()-1
        our stateRec: lastSRec // <- lastSSet.stateRecs[lastSRecIDX]
        their production: prod
        me uint32: ProdType <- 0
        me uint32: isTerminal<- 0
        me uint32: seqPos<- 0
      //  lastSRec.print(this) print("\n----\n")

        withEach SRec in lastSSet.stateRecs:{
            lastSRec <- SRec
            prod <- grammar[SRec.productionID]
            ProdType <- prod.prodType
            isTerminal <- prod.isTerm
            seqPos <- SRec.SeqPosition
            if (SRec.productionID==startProduction and SRec.originPos==0 and ((lastPosWithItems+1)==lastSSetIDX) and seqPos==prod.items.size()){
 //               print("Passed\n")  // !!!!!!!!!!!!!!!!!!! This tells when the parse passes.
                return(false)
            }
            //SRec.print(this) //print(" ", seqPos, ' - ', SRec.prev, "\n")
        }

        //lastSRec.print(this) print("\n----\n", seqPos)
        if(isTerminal!=0){
            if(seqPos==0){
                errorMesg <- "Expected '" + prod.constStr + "'"
                countLinesToCharPos(lastPosWithItems)
            }
        }

        if(errorMesg=="" and (lastPosWithItems+1)!=lastSSetIDX){
            errorMesg<-'Parse failed for unknown reason.'
        }
        if(errorMesg=="") {return(false)}
        else {return(true)}
    }

    our stateRec: resolve(our stateRec: LastTopLevelItem, me string: indent) <- {
        if(LastTopLevelItem == NULL){print("\nStateRecPtr is null.\n\n") exit(1)}
        our stateRec: crntRec <- LastTopLevelItem
        me uint32: seqPos <- crntRec.SeqPosition
        me uint32: prodID <- crntRec.productionID
        their production: Prod <- grammar[prodID]
   //     print(indent+'grammar[%i`prodID`] = ')
   //     crntRec.print(this)
   //     print("\n", indent, "\n")
        if(Prod.isTerm){
        } else if(seqPos>0){
            withEach subItem in Backward RANGE(0 .. seqPos):{
             //   print(indent, "   item #", subItem, ": \n")
                crntRec.child <- resolve(crntRec.cause, indent+"     | ")
                crntRec.prev.next <- crntRec
                crntRec <- crntRec.prev
            //    print(indent, "############# ") crntRec.print(this) print("\n")
            }
        }
        if(indent==""){
//            print("\nRESOLVED\n\n")
        }
        return(crntRec)
    }

    void: displayParse(our stateRec: SRec, me string: indent) <- {
        their production: prod <- grammar[SRec.productionID]
        if(prod.isTerm){
            print(indent, "'")
            withEach i in RANGE(SRec.originPos .. SRec.crntPos):{
                print(textToParse[i])
            }
            print("'\n")
        } else {
           // print(indent) SRec.print(this) print("\n")
            if(SRec.child){
                displayParse(SRec.child, indent+"   | ")
            }
            if(SRec.next){
                displayParse(SRec.next, indent)
            }
        }
    }

}
    """
    code=code.replace('#CONST_CODE_HERE', ConstList, 1)
    code=code.replace('#GRAMMAR_CODE_HERE', RuleList, 1)
    return code

def writePositionalFetch(objects, tags, field):
    fname=field['fieldName']
    fieldType=str(field['fieldType'])
    S="""
    me fetchResult: fetch_%s() <- {
        if(%s_hasVal) {return (fetchOK)}
        }
"""% (fname, fname)
    return S




    print 'FIELD::', fname, field['owner'], '"'+fieldType+'"'
    if(field['owner']=='const' and fieldType=='string'):
        S+='    %s_hasLen <- true \n    %s_span.len <- '% (fname, fname) + str(len(field['value']))
    S+="        if(! %s_hasPos){pos <- pred.pos+pred.len}\n" % (fname)
    S+="        if( %s_hasPos){\n" % (fname)
    # Scoop Data
    S+=' FieldTYpe("' + fieldType +'")\n'
    if progSpec.isStruct(fieldType):
        print " Call stuct's fetch()"
    #elif fieldType=='':
    # Set and propogate length
    S+="        }\n"
    S+='    }'

    return S

def writePositionalSet(field):
    return "    // Positional Set() TBD\n";

def writeContextualGet(field):
    return "    // Contextual Get() TBD\n";

def writeContextualSet(field):
    return "    // Contextual Set() TBD\n";


def appendRule(ruleName, termOrNot, pFlags, prodData):
    global rules
    global constDefs
    global ruleSet
    # If rule already exists, return the name rather than recreate it
    # is there a rule with the same term, flags, and prodData? (Only care about term+parseSEQ+data)
    if (ruleName in ruleSet):
        ruleSet[ruleName]+=1
    else:
        thisIDX=len(rules)
        if not isinstance(ruleName, basestring):
            ruleName="rule"+str(thisIDX)
        constDefs.append([ruleName, str(thisIDX)])
        #print "PRODDATA:", prodData
        if isinstance(prodData, list):
            prodData='['+(', '.join(map(str,prodData))) + ']'
        rules.append([ruleName, termOrNot, pFlags, prodData])
        ruleSet[ruleName]=0
    return ruleName


definedRules={}

def populateBaseRules():
    definedRulePairs=[['{','lBrace'],  ['}','rBrace'], ['(','lParen'],  [')','rParen'],  ['[','lBrckt'],  [']','rBrckt'],  [' ','space'],  [',','comma'],
            ['!','bang'],  ['.','period'],  ['/','slash'],  ['?','question'],  [':','colon'],  ['`','quoteBack'],  ["'",'quote1'],  [r'\"','quote2'],
            ['-','minus'],  ['+','plus'],  ['=','equals'],  ['*','star'], ['<','lessThan'],  ['>','grtrThan'],  ['@','atSign'], ['#','hashMark'],  ['$','dollarSign'],
            ['%','percent'],  ['^','carot'], ['~','tilde'], ['_','underscore'],  ['|','bar'], [r'\\','backSlash'],  [';','semiColon'] ]

    for pair in definedRulePairs:
        appendRule(pair[1], "term", "parseSEQ",  pair[0])
        definedRules[pair[0]]=pair[1]

    # Define common string formats
    appendRule('alphaSeq',  'term', 'parseAUTO', "an alphabetic string")
    appendRule('uintSeq',   'term', 'parseAUTO', 'an unsigned integer')
    appendRule('intSeq',    'term', 'parseAUTO', 'an integer')
    appendRule('RdxSeq',    'term', 'parseAUTO', 'a number')
    appendRule('alphaNumSeq',  'term', 'parseAUTO', "an alpha-numeric string")
    appendRule('ws',        'term', 'parseAUTO', 'white space')
    appendRule('quotedStr1','term', 'parseAUTO', "a single quoted string with escapes")
    appendRule('quotedStr2','term', 'parseAUTO', "a double quoted string with escapes")
    appendRule('CID',       'term', 'parseAUTO', 'a C-like identifier')
    appendRule('UniID',     'term', 'parseAUTO', 'a unicode identifier for the current locale')
    appendRule('printables','term', 'parseAUTO', "a seqence of printable chars")
    appendRule('toEOL',     'term', 'parseAUTO', "to read chars to End Of Line, including EOL.")
    # TODO: delimited List, keyWord



nextParseNameID=0 # Global used to uniquify sub-seqs and sub-alts in a struct parse. E.g.: ruleName: parse_myStruct_sub1
def fetchOrWriteTerminalParseRule(modelName, field):
    global nextParseNameID
    #print "FIELD_IN:", modelName, field
    fieldName='N/A'
    fieldValue=''
    if 'value' in field: fieldValue =field['value']
    typeSpec   =field['typeSpec']
    fieldType  =typeSpec['fieldType']
    fieldOwner =typeSpec['owner']
    if 'fieldName' in field: fieldName  =field['fieldName']
    print "WRITE PARSE RULE:", modelName, fieldName

    nameIn=None
    nameOut=None
    if fieldOwner=='const':
        if fieldType=='string':
            if fieldValue in definedRules: nameOut=definedRules[fieldValue]
            else: nameOut=appendRule(nameIn, "term", "parseSEQ",  fieldValue)
        elif fieldType[0:4]=='uint':   nameOut=appendRule(nameIn, "term", "parseSEQ",  fieldValue)
        elif fieldType[0:3]=='int':    nameOut=appendRule(nameIn, "term", "parseSEQ",  fieldValue)
        elif fieldType[0:6]=='double': nameOut=appendRule(nameIn, "term", "parseSEQ",  fieldValue)
        elif fieldType[0:4]=='char':   nameOut=appendRule(nameIn, "term", "parseSEQ",  fieldValue)
        elif fieldType[0:4]=='bool':   nameOut=appendRule(nameIn, "term", "parseSEQ",  fieldValue)
        else:
            print "Unusable const type in fetchOrWriteTerminalParseRule():", fieldType; exit(2);

    elif fieldOwner=='me' or  fieldOwner=='their' or  fieldOwner=='our':
        if fieldType=='string':        nameOut='quotedStr1'
        elif fieldType[0:4]=='uint':   nameOut='uintSeq'
        elif fieldType[0:3]=='int':    nameOut='intSeq'
        elif fieldType[0:6]=='double': nameOut='RdxSeq'
        elif fieldType[0:4]=='char':   nameOut=appendRule(nameIn,       "term", "parseSEQ",  None)
        elif fieldType[0:4]=='bool':   nameOut=appendRule(nameIn,       "term", "parseSEQ",  None)
        elif progSpec.isStruct(fieldType):
            objName=fieldType[0]
            if objName=='ws' or objName=='quotedStr1' or objName=='quotedStr2' or objName=='CID' or objName=='UniID' or objName=='printables' or objName=='toEOL' or objName=='alphaNumSeq':
                nameOut=objName
            else:
                if objName=='[' or objName=='{': # This is an ALT or SEQ sub structure
                    print "ERROR: These should be handled in writeNonTermParseRule().\n"
                    exit(1)
                else: nameOut=objName+'_str'
        elif progSpec.isAlt(fieldType):
            pass
        elif progSpec.isCofactual(fieldType):
            pass
        else:
            print "Unusable type in fetchOrWriteTerminalParseRule():", fieldType; exit(2);
    else: print "Pointer types not yet handled in fetchOrWriteTerminalParseRule():", fieldType; exit(2);

    if('arraySpec' in typeSpec and typeSpec['arraySpec']):
        global rules
        containerSpec=typeSpec['arraySpec']
        idxType=''
        if 'indexType' in containerSpec:
            idxType=containerSpec['indexType']
        datastructID = containerSpec['datastructID']
        if idxType[0:4]=='uint': pass
        if(datastructID=='list'):
            nameOut=appendRule(nameOut+'_REP', "nonterm", "parseREP", [nameOut, 0, 0])
        elif datastructID=='opt':
            nameOut=appendRule(nameOut+'_OPT', "nonterm", "parseREP", [nameOut, 0, 1])
    field['parseRule']=nameOut
    return nameOut

def writeNonTermParseRule(objects, tags, modelName, fields, SeqOrAlt, nameSuffix):
    global nextParseNameID
    nameIn=modelName+nameSuffix

    # Allocate or fetch a rule identifier for each '>' field.
    partIndexes=[]
    for field in fields:
        fname=field['fieldName']
        if fname==None: fname=''
        else: fname='_'+fname
        typeSpec   =field['typeSpec']
        if(field['isNext']==True):
            firstItm=field['typeSpec']['fieldType'][0]
            if firstItm=='[' or firstItm=='{': # Handle an ALT or SEQ sub structure
                nextParseNameID+=1
                if firstItm=='[':
                    innerSeqOrAlt='parseALT'
                    newNameSuffix = nameSuffix+fname+'_ALT'+str(nextParseNameID)
                else:
                    innerSeqOrAlt='parseSEQ'
                    newNameSuffix = nameSuffix+fname+'_SEQ'+str(nextParseNameID)
                innerFields=field['innerDefs']
                ruleIdxStr = writeNonTermParseRule(objects, tags, modelName, innerFields, innerSeqOrAlt, newNameSuffix)
                field['parseRule']=ruleIdxStr


                if('arraySpec' in typeSpec and typeSpec['arraySpec']):
                    global rules
                    containerSpec=typeSpec['arraySpec']
                    idxType=''
                    if 'indexType' in containerSpec:
                        idxType=containerSpec['indexType']
                    datastructID = containerSpec['datastructID']
                    if idxType[0:4]=='uint': pass
                    if(datastructID=='list'):
                        ruleIdxStr=appendRule(ruleIdxStr+'_REP', "nonterm", "parseREP", [ruleIdxStr, 0, 0])
                    elif datastructID=='opt':
                        ruleIdxStr=appendRule(ruleIdxStr+'_OPT', "nonterm", "parseREP", [ruleIdxStr, 0, 1])
            else:
                ruleIdxStr = fetchOrWriteTerminalParseRule(modelName, field)

            partIndexes.append(ruleIdxStr)
        else: pass; # These fields probably have corresponding cofactuals

    nameOut=appendRule(nameIn, "nonterm", SeqOrAlt, partIndexes)
    return nameOut

def fetchMemVersion(objects, objName):
    if objName=='[' or objName=='{': return [None, None]
    # TODO: here we assume that the memory form has '::mem' using AutoAssigners, make this work with other forms.
    seperatorIdx= objName.find("::")
    #print "OBJNAME:", objName, seperatorIdx
    memVersionName=objName
    if seperatorIdx>=0:
        memVersionName=objName[:objName.find("::")]+"::mem"
    if not memVersionName in objects[0]: return [None, None]
    memObj=objects[0][memVersionName]
    return [memObj, memVersionName]


def Write_ALT_Extracter(objects, field, parentStructName, fields, VarTag, VarName, indent, level):
    # Structname should be the name of the structure being parsed. It will be converted to the mem version to get 'to' fields.
    # Fields is the list of alternates.
    # VarTag is a string used to create local variables.
    # VarName is the LVAL variable name.
    [memObj, memVersionName]=fetchMemVersion(objects, parentStructName)
    InnerMemObjFields=memObj['fields']
    nxtLvlString=''
    for lvl in range(0,level): nxtLvlString+='.next.child'
    S=""
    loopVarName = "ruleIDX"+str(level)
    S+='        me int32: '+loopVarName+' <- '+VarTag+'.child'+nxtLvlString+'.productionID\n'
    print "RULEIDX:", indent, parentStructName, VarName
    if VarName!='memStruct':
        S+=indent + 'me string: '+VarName+'\n'
    count=0
    for altField in fields:
        #print 'ALTFIELD:', altField
        if(altField['isNext']!=True): continue; # This field isn't in the parse stream.
        S+=indent
        if(count>0): S+="else "
        if not 'parseRule' in altField: print "Error: Is syntax missing a '>'?"; exit(2);
        S+="if("+loopVarName+" == " + altField['parseRule'] + "){\n"
        coFactualCode=''
        if 'coFactuals' in altField:
            #Extract field and cofactsList
            coFactualCode="\n"
            for coFact in altField['coFactuals']:
                coFactualCode+= indent + VarName + '.' + coFact[0] + ' <- ' + coFact[2] + "\n"
        print indent,"    GOING TO WRITE FIELD:", count
        S+=Write_fieldExtracter(objects, parentStructName, altField, InnerMemObjFields, VarTag, VarName, False, indent+'    ', level)
        S+=coFactualCode
        S+=indent+"}"
        count+=1
    return S


def CodeRValExpr(toFieldType, VarTag, doNextSuffix):
    if   toFieldType=='string':          CODE_RVAL='makeStr('+VarTag+'.child'+doNextSuffix+')'+"\n"
    elif toFieldType[0:4]=='uint':       CODE_RVAL='makeInt('+VarTag+'.child'+doNextSuffix+')'+"\n"
    elif toFieldType[0:3]=='int':        CODE_RVAL='makeInt('+VarTag+'.child'+doNextSuffix+')'+"\n"
    elif toFieldType[0:6]=='double':     CODE_RVAL='makeDblFromStr('+VarTag+'.child'+doNextSuffix+')'+"\n"
    elif toFieldType[0:4]=='char':       CODE_RVAL="crntStr[0]"+"\n"
    elif toFieldType[0:4]=='bool':       CODE_RVAL='crntStr=="true"'+"\n"
    else: print "TOFIELDTYPE:", toFieldType; exit(2);
    return CODE_RVAL


def Write_fieldExtracter(objects, ToStructName, field, memObjFields, VarTag, VarName, advancePtr, indent, level):
    boob=False # Erase this line
    ###################   G a t h e r   N e e d e d   I n f o r m a t i o n
    global  globalFieldCount
    S=''
    fieldName  =field['fieldName']
    fieldIsNext=field['isNext']
    fieldValue =field['value']
    typeSpec   =field['typeSpec']
    fieldType  =typeSpec['fieldType']
    fieldOwner =typeSpec['owner']
    fromIsEmbeddedAlt = (not isinstance(fieldType, basestring) and fieldType[0]=='[')
    fromIsEmbeddedSeq = (not isinstance(fieldType, basestring) and fieldType[0]=='{')
    fromIsEmbedded    = fromIsEmbeddedAlt or fromIsEmbeddedSeq

    if(fieldIsNext!=True): return '' # This field isn't in the parse stream.

    [memObj, memVersionName]=fetchMemVersion(objects, ToStructName)

    toField = progSpec.fetchFieldByName(memObjFields, fieldName)
    if(toField==None):
        print "TOFIELD == None"
        # Even tho there is no LVAL, we need to move the cursor. Also, there could be a co-factual.
        toFieldType = progSpec.TypeSpecsMinimumBaseType(objects, typeSpec)
        toTypeSpec=typeSpec
        toFieldOwner="me"
    else:
        print "TOFIELD:", toField
        toTypeSpec   = toField['typeSpec']
        toFieldType  = toTypeSpec['fieldType']
        toFieldOwner = toTypeSpec['owner']

    LHS_IsPointer=progSpec.typeIsPointer(toTypeSpec)

   # print "        CONVERTING:", fieldName, str(toFieldType)[:100]+'... ', str(typeSpec)[:100]+'... '
   # print "            TOFieldTYPE1:", str(toField)[:100]
    print "            TOFieldTYPE :", toFieldOwner, toFieldType
    print "       fieldValue:",ToStructName, fieldType, fieldValue

    #!#!#!# Test Code #!#!#!# Test Code #!#!#!# Test Code #!#!#!# Test Code #!#!#!# Test Code #!#!#!# Test Code #!#!#!# Test Code
    if fieldName==None and fieldType[0]=='listInfo':
        print "FIELDDATA:", fieldType[0], typeSpec
        boob=True

    fields=[]
    fromIsStruct=progSpec.isStruct(fieldType)
    toIsStruct=progSpec.isStruct(toFieldType)
    ToIsEmbedded = toIsStruct and (toFieldType[0]=='[' or toFieldType[0]=='{')
    [fromIsALT, fields] = progSpec.isAltStruct(objects, fieldType)
    fromIsOPT =False
    fromIsList=False
    toIsList  =False
    if 'arraySpec' in typeSpec and typeSpec['arraySpec']!=None:
        datastructID = typeSpec['arraySpec']['datastructID']
        if datastructID=='opt': fromIsOPT=True;
        else: fromIsList=True

    if 'arraySpec' in toTypeSpec and toTypeSpec['arraySpec']!=None:
        if datastructID != 'opt': toIsList=True

    if boob:
        print '        fromIsOPT:', fromIsOPT
        print '        fromIsList:', fromIsList
        print '        toIsList:', toIsList
        print '        fromIsStruct:', fromIsStruct
        print '        toIsStruct:', toIsStruct
        print '        toTypeSpec:', toTypeSpec
        print '        ToStructName:', ToStructName
        print '        memVersionName:', memVersionName
    ###################   W r i t e   L V A L   R e f e r e n c e
    finalCodeStr=''
    CodeLVAR_Alloc=''
    CODE_LVAR_v2=''
    if VarName=='' or VarName=='memStruct':  # Default to the target argument name
        if VarName=='': print "        VARNAME was ''; FIELDNAME:", fieldName
        VarName='memStruct'
        if(fieldName==None): # Field hasn't a name so in memory it's a cofactual or this is a parser marker.
            globalFieldCount+=1
            # We need two versions in case this is set in a function instead of assignment
            CODE_LVAR_v2 = 'S'+str(globalFieldCount)
            CodeLVAR_Alloc='    me string: '+CODE_LVAR_v2
            CODE_LVAR = CodeLVAR_Alloc
            if boob: print '        CODE_LVARS:', CODE_LVAR
        else:
            CODE_LVAR = VarName+'.'+fieldName
            CODE_LVAR_v2 = CODE_LVAR
    else:
        CODE_LVAR = VarName
        CODE_LVAR_v2 = CODE_LVAR

    ###################   W r i t e   R V A L   C o d e
    CODE_RVAL=''
    objName=''
    doNextSuffix=''
    fetchSuffix=''
    if advancePtr:
        if boob: print '        fetchSuffix:', VarTag
        S+=indent+VarTag+' <- getNextStateRec('+VarTag+')\n'
    else:
        doNextSuffix='.next'
        fetchSuffix=".child.next"


    if fieldOwner=='const'and (toField == None):
        finalCodeStr += indent + VarTag+'_tmpStr'+' <- makeStr('+VarTag+'.child)\n'
        #  print("'+fieldValue+'")\n'

    else:
        if toIsStruct:
            if boob: print '        toFieldType:', toFieldType
            if not ToIsEmbedded:
                objName=toFieldType[0]
                if objName=='ws' or objName=='quotedStr1' or objName=='quotedStr2' or objName=='CID' or objName=='UniID' or objName=='printables' or objName=='toEOL' or objName=='alphaNumSeq':
                    CODE_RVAL='makeStr('+VarTag+'.child'+doNextSuffix+')'
                    toIsStruct=False; # false because it is really a base type.
                else:
                    print "TOFIELDTYPE:", objName
                  #  print "        toObjName:", objName
                    [toMemObj, toMemVersionName]=fetchMemVersion(objects, objName)
                    if toMemVersionName==None:
                        # make alternate finalCodeStr. Also, write the extractor that extracts toStruct fields to memVersion of this
                        extractorFuncName = fieldType[0].replace('::', '_')+'_to_'+memVersionName.replace('::', '_')
                        finalCodeStr=(indent + CodeLVAR_Alloc + '\n' +indent+'    Extract_'+extractorFuncName+'('+VarTag+fetchSuffix+'.child, memStruct)\n')

                        print "TOSTRUNCTSNAME:", objName, extractorFuncName
                        ToFields=objects[0][objName+'::str']['fields']
                        Write_structExtracter(objects, ToStructName, ToFields, extractorFuncName)
                    else:
                        finalCodeStr=indent + CodeLVAR_Alloc + '\n' +indent+'    Extract_'+fieldType[0].replace('::', '_')+'_str'+'('+VarTag+fetchSuffix+'.child, '+CODE_LVAR_v2+')\n'
                if boob: print '        finalCodeStr:', finalCodeStr
        else:
            CODE_RVAL = CodeRValExpr(toFieldType, VarTag, doNextSuffix)


    #print "CODE_RVAL:", CODE_RVAL

    ###################   H a n d l e   o p t i o n a l   a n d   r e p e t i t i o n   a n d   a s s i g n m e n t   c a s e s
    gatherFieldCode=''
    if fromIsList and toIsList:
        CODE_RVAL='tmpVar_tmpStr'
        globalFieldCount +=1
        childRecName='childSRec' + str(globalFieldCount)
        gatherFieldCode+='\n'+indent+'\nour stateRec: '+childRecName+' <- '+VarTag+'.child.next\n    withEach Cnt in WHILE('+childRecName+'):{\n'
        if fromIsALT:
            print "ALT-#1"
            gatherFieldCode+=Write_ALT_Extracter(objects, field,  fieldType[0], fields, childRecName, 'tmpVar_tmpStr', indent+'    ', level)

        elif fromIsStruct and toIsStruct:
            print "toFieldType:", toFieldOwner, ">>>", toFieldType
            gatherFieldCode+='\n'+indent+toFieldOwner+' '+progSpec.baseStructName(toFieldType[0])+': tmpVar_tmpStr'
            if toFieldOwner!='me':
                gatherFieldCode+='\n'+indent+'Allocate('+CODE_RVAL+')'
            gatherFieldCode+='\n'+indent+'Extract_'+fieldType[0].replace('::', '_')+'_str'+'('+childRecName+'.child, tmpVar_tmpStr)\n'

        else:
            CODE_RVAL = CodeRValExpr(toFieldType, childRecName, '')
            #CODE_RVAL=childRecName+'.child'

        # Now code to push the chosen alternative into the data field# This is a LIST, not an OPT:
        gatherFieldCode+='\n'+indent+CODE_LVAR+'.pushLast('+CODE_RVAL+')'

        gatherFieldCode+=indent+'    '+childRecName+' <- getNextStateRec('+childRecName+')\n'

        gatherFieldCode+='\n'+indent+'}\n'
        if(fromIsOPT):
            print "Handle when the optional item is a list.";
            exit(2)
    else:
        if toIsList: print "Error: parsing a non-list to a list is not supported.\n"; exit(1);
        assignerCode=''
        oldIndent=indent
        if (fromIsOPT):
            setTrueCode=''
            assignerCode+='\n'+indent+'if('+VarTag+'.child.next'+' == NULL){'
            if toFieldOwner=='me':
                if boob: print '        toFieldOwner:', toFieldOwner
                ## if fieldName==None and a model of fromFieldType has no cooresponding model But we are in EXTRACT_ mode:
                        ## Make a special form of Extract_fromFieldType_to_ToFieldType()
                        ## Call that function instead of the one in Code_LVAR
                # First, create a new flag field
                if fieldName==None: fieldName="TEMP"
                newFieldsName='has_'+fieldName
                fieldDef=progSpec.packField(False, 'me', 'flag', None, newFieldsName, None, None, None)
                progSpec.addField(objects[0], memVersionName, fieldDef)

                # Second, generate the code to set the flag
                assignerCode+='\n'+indent+'    '+VarName+'.'+newFieldsName+' <- false'
                setTrueCode += VarName+'.'+newFieldsName+' <- true'
            elif LHS_IsPointer: # If owner is my, our or their
                assignerCode+='\n'+indent+'    '+CODE_LVAR+' <- NULL'
            else:
                print"ERROR: OPTional fields must not be '"+toFieldOwner+"'.\n"
                exit(1)
            assignerCode+='\n'+indent+'} else {\n'
            indent+='    '
            assignerCode+=indent+setTrueCode+'\n'


        if fromIsALT or fromIsEmbeddedAlt:
            if(fromIsEmbeddedAlt):
                print "ALT-#2"
                assignerCode+=Write_ALT_Extracter(objects, field,  ToStructName, field['innerDefs'], VarTag, VarName, indent+'    ', level+1)
            else:
                print "ALT-#3"
                assignerCode+=Write_ALT_Extracter(objects, field,  fieldType[0], fields, VarTag, VarName+'X', indent+'    ', level)
                assignerCode+=indent+CODE_LVAR+' <- '+(VarName+'X')+"\n"
        elif fromIsEmbeddedSeq:
            globalFieldCount +=1
            childRecName='childSRec' + str(globalFieldCount)
            assignerCode+='\n'+indent+'me string: '+childRecName+'_tmpStr'
            assignerCode+='\n'+indent+'our stateRec: '+childRecName+' <- '+VarTag+'.child.next.child\n'
            for innerField in field['innerDefs']:
                assignerCode+=Write_fieldExtracter(objects, ToStructName, innerField, memObjFields, childRecName, '', True, '    ', level)
        elif fromIsStruct and toIsStruct:
            assignerCode+=finalCodeStr;
            if boob: print '        assignerCode:', assignerCode
        else:
           # if toFieldOwner == 'const': print "Error: Attempt to extract a parse to const field.\n"; exit(1);
            if CODE_RVAL!="":
                if LHS_IsPointer:
                    assignerCode+='        '+CODE_LVAR+' <deep- '+CODE_RVAL+"\n"
                else: assignerCode+='        '+CODE_LVAR+' <- '+CODE_RVAL+"\n"
            elif finalCodeStr!="": assignerCode+=finalCodeStr;

        if (fromIsOPT):
            indent=oldIndent
            assignerCode += indent+'}\n'
            #print '######################\n'+assignerCode, memVersionName, '\n'
           # exit(2)
        gatherFieldCode = assignerCode

    if LHS_IsPointer: # LVAL is a pointer and should be allocated or cleared.
        S+= indent + 'AllocateOrClear(' +CODE_LVAR +')\n'

    S+=gatherFieldCode
    #print "ASSIGN_CODE", S
 #   if boob: exit(2)
    return S

extracterFunctionAccumulator = ""
alreadyWrittenFunctions={}

def Write_structExtracter(objects, ToStructName, fields, nameForFunc):
    global extracterFunctionAccumulator
    global alreadyWrittenFunctions
    if nameForFunc in alreadyWrittenFunctions: return
    alreadyWrittenFunctions[nameForFunc]=True
    [memObj, memVersionName]=fetchMemVersion(objects, ToStructName)
    memObjFields=memObj['fields']
    print "WRITING STRUCT EXTRACTOR:",nameForFunc
    S='    me string: SRec_tmpStr'
    for field in fields: # Extract all the fields in the string version.
        S+=Write_fieldExtracter(objects, ToStructName, field, memObjFields, 'SRec', '', True, '    ', 0)

    seqExtracter =  "\n    void: Extract_"+nameForFunc.replace('::', '_')+"(our stateRec: SRec, their "+memVersionName+": memStruct) <- {\n" + S + "    }\n"
    extracterFunctionAccumulator += seqExtracter


def CreateStructsForStringModels(objects, tags):
    print "Creating structs from string models..."

    # Define fieldResult struct
    #~ structsName = 'fetchResult'
    #~ StructFieldStr = "mode [fetchOK, fetchNotReady, fetchSyntaxError, FetchIO_Error] : FetchResult"
    #~ progSpec.addObject(objects[0], objects[1], structsName, 'struct', 'SEQ')
    #~ codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef(structsName, StructFieldStr))

    populateBaseRules()

    global extracterFunctionAccumulator
    extracterFunctionAccumulator=""
    ExtracterCode="""

    me string: makeStr(our stateRec: SRec) <- {
        me string: S <- ""
        me uint64: startPos <- SRec.originPos
        me uint64: endPos <- SRec.crntPos
        me uint32: prod <- SRec.productionID
        if(prod == quotedStr1 or prod == quotedStr2){
            startPos <- startPos+1
            endPos <- endPos-1
        }
        withEach i in RANGE(startPos .. endPos):{
            S <- S+textToParse[i]
        }
        return(S)
    }
    me uint64: makeInt(our stateRec: SRec) <- {
        me string: S <- makeStr(SRec)
        me int64: N <- stoi(S)
        return(N)
    }
    our stateRec: getNextStateRec(our stateRec: SRec) <- {if(SRec.next){ return(SRec.next)} return(NULL) }
    """

    global nextParseNameID
    nextParseNameID=0
    numStringStructs=0
    for objectName in objects[1]:
        if objectName[0] == '!': continue
        ObjectDef = objects[0][objectName]
        if(ObjectDef['stateType'] == 'string'):
            numStringStructs+=1
            print "    WRITING STRING-STRUCT:", objectName
            # TODO: modelExists = progSpec.findModelOf(objMap, structName)
            fields=ObjectDef['fields']
            configType=ObjectDef['configType']
            SeqOrAlt=''
            if configType=='SEQ': SeqOrAlt='parseSEQ'
            elif configType=='ALT': SeqOrAlt='parseALT'

            normedObjectName = objectName.replace('::', '_')
            # Write the rules for all the fields, and a parent rule which is either SEQ or ALT, and REP/OPT as needed.
            ruleID = writeNonTermParseRule(objects, tags, normedObjectName, fields, SeqOrAlt, '')

            if SeqOrAlt=='parseSEQ':
                Write_structExtracter(objects, objectName, fields, objectName)

    if numStringStructs==0: return

    ExtracterCode += extracterFunctionAccumulator

    tags['Include'] += ",<cctype>"

    # Define streamSpan struct
    structsName = 'streamSpan'
    StructFieldStr = "    me uint32: offset \n    me uint32: len"
    progSpec.addObject(objects[0], objects[1], structsName, 'struct', 'SEQ')
    codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef(structsName, StructFieldStr))



    ############  Add struct parser
    parserCode=genParserCode()
    print "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n", parserCode
    codeDogParser.AddToObjectFromText(objects[0], objects[1], parserCode)

    structsName='EParser'
    print progSpec.wrapFieldListInObjectDef(structsName, ExtracterCode)+"\n"
    #exit(2)
    progSpec.addObject(objects[0], objects[1], structsName, 'struct', 'SEQ')
    codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef(structsName, ExtracterCode))
