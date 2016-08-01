# CodeDog Program Maker
#   This file is code to convert "string" style structures into 'struct' style structures.

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

def genParserCode():
    global rules
    global constDefs
    RuleList=''
    for rule in rules:
        if rule[1]=='term':
            RuleList+='        addTerminalProd("' + rule[0] +'", ' + rule[2] + ', "' + str(rule[3]).replace('::','_') + '")\n'
        elif rule[1]=='nonterm':
            RuleList+='        addNon_TermProd("' + rule[0] +'", ' + rule[2] + ', ' + str(rule[3]).replace('::','_') + ')\n'

    ConstList=''
    for C in constDefs:
        ConstList+='    const uint32: ' + C[0].replace('::','_') + ' <- ' + str(C[1]) + '\n'

    code= r"""

struct production{
    flag: isTerm
    mode[parseSEQ, parseALT, parseREP, parseOPT, parseAUTO]: prodType
    me string: constStr
    me uint32[list uint32]: items
    void: print(me uint32: SeqPos, me uint32: originPos) <- {
        me uint32: ProdType <- prodType
        print("[")
        print(ProdType, ": ")
        if(isTerm){
            if(SeqPos==0) {print(" > ")}
            print('"%s`constStr.data()`"')
            if(SeqPos>0) {print(" > ")}
            print(', Origin:%i`originPos`')
        } else {
            if(ProdType==parseALT and SeqPos==0) {print(" > ")}
            withEach p in items:{
                if(ProdType == parseSEQ and p_key == SeqPos){ print(" > ")}
                if(p_key){
                    if(ProdType==parseALT){print("| ")}
                }
                print('%i`p` ')
            }
            if(ProdType==parseREP){ print('(Len:%i`SeqPos`)')}
            else {if ((p_key == SeqPos and ProdType == parseSEQ or (ProdType==parseALT and SeqPos>0))) {print(" > ")}}
            print(', Origin:%i`originPos` ')
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
    void: print(their production: prod) <- {prod.print(SeqPosition, originPos)}
}
struct stateRecPtr{our stateRec: stateRecPtr}

struct stateSets{
    me stateRecPtr[list uint32]: stateRecs
    me uint64: flags
    //stateSets():flags(0){}
}

struct EParser{
    me string: textToParse
    me uint64: startProduction
    me stateSets[list uint32]: SSets
    me production[list uint32]: grammar
    me bool: parseFound
    our stateRec: LastTopLevelItem

    void: clearGrammar() <- {grammar.clear()}
    void: addTerminalProd(me string: name, me uint32: ProdType, me string: s) <- {
        me production: P
        P.prodType <- ProdType
        P.isTerm   <- true
        P.constStr <- s
        grammar.pushLast(P)
    }
    void: addNon_TermProd(me string: name, me uint32: ProdType, me uint32[list uint32]: terms) <- {
        me production: P
        P.prodType <- ProdType
        P.items <- terms
        grammar.pushLast(P)
    }

    void: dump() <- {
         withEach crntPos in RANGE(0 .. SSets.size()):{
            their stateSets: SSet <- SSets[crntPos]
            me string: ch <- "x"
            if(crntPos+1 != SSets.size()) {
                ch <- textToParse[crntPos]
            }
            print('SLOT: %i`crntPos` (%s`ch.data()`) - size:%i`(int)SSet->stateRecs.size()`\n')
            withEach SRec in SSet.stateRecs:{
                their production: prod <- grammar[SRec.productionID]
                print('    (%p`SRec` -> cause: %p`SRec->cause`, pred:%p`SRec->prev`): ')
                prod.print(SRec.SeqPosition, SRec.originPos)
                print("\n")
            }
        }
        if(parseFound){print("\nPARSE PASSED!\n\n")}
        else {print("\nPARSE failed.\n\n")}
    }

#CONST_CODE_HERE

    void: populateGrammar() <- {
        clearGrammar()
#GRAMMAR_CODE_HERE

    }

    me void: addProductionToStateSet(me uint32: crntPos, me uint32: productionID, me uint32: SeqPos, me uint32: origin, our stateRec: prev, our stateRec: cause) <- {
        print('############ ADDING rule %i`productionID` at char slot %i`crntPos` at POS %i`SeqPos`... ')
        withEach item in SSets[crntPos].stateRecs:{ // Don't add duplicates.
            // TODO: change this to be faster. Not a linear search.
            if(item.productionID==productionID and item.SeqPosition==SeqPos and item.originPos==origin){
                print("DUPLICATE\n")
                return()
            }
        }
        their production: prod <- grammar[productionID]
        me bool: thisIsTopLevelItem <- false
        if(productionID==startProduction and origin==0){
            thisIsTopLevelItem <- true
            if(SeqPos==prod.items.size()){
                parseFound <- true
                print(" <PARSE PASSED!> ")
            }
        }
        me uint32: ProdType <- prod.prodType
        if(ProdType == parseSEQ or ProdType == parseREP or ProdType == parseALT or ProdType == parseAUTO){
            prod.print(SeqPos, origin)
            our stateRec: newStateRecPtr newStateRecPtr.allocate(productionID, SeqPos, origin, crntPos, prev, cause)
            if(thisIsTopLevelItem) {LastTopLevelItem <- newStateRecPtr}
            SSets[crntPos].stateRecs.pushLast(newStateRecPtr)
            print(' ADDED \n')
        }

        if(ProdType == parseALT and SeqPos==0){
            print("  ALT-LIST\n")
            withEach AltProd in prod.items:{
                print("                                  ALT: ")
                addProductionToStateSet(crntPos, AltProd, 0, origin, prev, cause)
            }
        } else {print("  Unknown ProductionType:", ProdType)}
        print("\n")
    }

    me void: initPosStateSets(me uint64: startProd, me string: txt) <- {
        print('Will parse "%s`txt.data()` with rule %i`startProd`.\n')
        startProduction <- startProd
        textToParse <- txt
        SSets.clear()
        withEach i in RANGE(0 .. txt.size()+1):{
            me stateSets: newSSet
            SSets.pushLast(newSSet)
        }
        addProductionToStateSet(0, startProduction, 0, 0, 0,0)
    }


    me uint32: chkStr(me uint32: pos, me string: s) <- {
        me uint32: L <- s.size()
        if(pos+L > textToParse.size()){print("chkStr FAILED (target string too short)\n") return(0)}
        withEach i in RANGE(0 .. L):{
            if( s[i] != textToParse[pos+i]) {print("chkStr FAILED\n") return(0)}
        }
        print("chkStr PASSED\n")
        return(L)
    }

    me uint32: scrapeUntil(me uint32:pos, me string:endChar) <- {
        me char: ender <- endChar[0]
        me char: ch
        me uint32: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize):{
            ch <- textToParse[p]
            if(ch==ender){return(p-pos)}
        }
        return(0)
    }

    me uint32: escapedScrapeUntil(me uint32:pos, me string:endChar) <- {
        me char: ch
        me char: prevChar
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
        return(0)
    }


    me uint32: scrapeAlphaSeq(me uint32: pos) <- {
        me char: ch
        me uint32: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize):{
            ch <- textToParse[p]
            if(isalpha(ch)){}else{return(p-pos)}
        }
        return(txtSize-pos)
    }
    me uint32: scrapeUintSeq(me uint32: pos) <- {
        me char: ch
        me uint32: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize):{
            ch <- textToParse[p]
            if(isdigit(ch)){}else{return(p-pos)}
        }
        return(txtSize-pos)
    }
    me uint32: scrapeAlphaNumSeq(me uint32: pos) <- {
        me char: ch
        me uint32: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize):{
            ch <- textToParse[p]
            if(isalnum(ch)){}else{return(p-pos)}
        }
        return(txtSize-pos)
    }
    me uint32: scrapeAlphaNum_Seq(me uint32: pos) <- {
        me char: ch
        me string: chars <- "_"
        me uint32: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize):{
            ch <- textToParse[p]
            if(isalnum(ch) or ch==chars[0]){}else{return(p-pos)}
        }
        return(txtSize-pos)
    }

    me uint32: scrapePrintableSeq(me uint32: pos) <- {
        me char: ch
        me uint32: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize):{
            ch <- textToParse[p]
            if(isprint(ch)){}else{return(p-pos)}
        }
        return(txtSize-pos)
    }

    me uint32: scrapeWS(me uint32: pos) <- {
        me char: ch
        me uint32: txtSize <- textToParse.size()
        withEach p in RANGE(pos .. txtSize):{
            ch <- textToParse[p]
            if(isspace(ch)){}else{return(p-pos)}
        }
        return(txtSize-pos)
    }

    me uint32: scrapeQuotedStr1(me uint32: pos) <- {
        pos <- pos+scrapeWS(pos)
        if(chkStr(pos, "'")){pos <- pos+1}else{return(0)}
        me uint32: sLen <- escapedScrapeUntil(pos, "'")
        if(sLen==0){return(0)}
        return(sLen+2)
    }

    me uint32: scrapeQuotedStr2(me uint32: pos) <- {
        pos <- pos+scrapeWS(pos)
        if(chkStr(pos, "\"")){pos <- pos+1}else{return(0)}
        me uint32: sLen <- escapedScrapeUntil(pos, "\"")
        if(sLen==0){return(0)}
        return(sLen+2)
    }
    me uint32: scrapeCID(me uint32: pos) <- {
        me char: ch <- textToParse[pos]
        me uint32: txtSize <- textToParse.size()
        me string: chars <- "_"
        if(pos >= txtSize){
            // Set I/O Error: Read past EOS
            return(0)
        }
        if(isalpha(ch) or ch==chars[0]){
            return(scrapeAlphaNum_Seq(pos)+1)
        } else {return(0)}
    }
    // TODO: me uint32: scrapeUniID(me uint32: pos) <- { }

    me uint32: scrapeIntSeq(me uint32: pos) <- {
        me char: ch <- textToParse[pos]
        me uint32: txtSize <- textToParse.size()
        me uint32: initialChars <- 0
        me string: chars <- "+-"
        if(pos >= txtSize){
            // Set I/O Error: Read past EOS
            return(0)
        }
        if(ch==chars[0] or ch==chars[1]){ initialChars <- 1}
        return(scrapeUintSeq(pos)+initialChars)
    }
    // TODO: me uint32: scrapeRdxSeq(me uint32: pos) <- { }

    me uint32: scrapeToEOL(me uint32: pos) <- {
        return(scrapeUntil(pos, "\\n"))
    }
    me uint32: textMatches(me uint32: ProdID, me uint32: pos) <- {
        their production: Prod <- grammar[ProdID]
        print('    MATCHING "%s`Prod->constStr.data()`"... ')
        me uint32: prodType <- Prod.prodType
        if(prodType==parseSEQ){ //prod is simple text match
            return(chkStr(pos, Prod.constStr))
        } else{if(prodType==parseAUTO){
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
        return(0)
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
           // print(indent) SRec.print(prod) print("\n")
            if(SRec.child){
                displayParse(SRec.child, indent+"   | ")
            }
            if(SRec.next){
                displayParse(SRec.next, indent)
            }
        }
    }


    me bool: complete(our stateRec: SRec, me int32: crntPos) <- {
        print('        COMPLETING: check items at origin %i`SRec->originPos`... \n')
        their stateSets: SSet  <- SSets[SRec.originPos]
        withEach backSRec in SSet.stateRecs:{
            their production: backProd <- grammar[backSRec.productionID]
            print('                Checking Item #%i`backSRec_key`: ')
            me uint32: prodTypeFlag <- backProd.prodType
            me uint32: backSRecSeqPos <- backSRec.SeqPosition
            if(prodTypeFlag==parseREP){
                print(" ADVANCING REP: ")
                me uint32: MAX_ITEMS  <- backProd.items[2]
                if((backSRecSeqPos < MAX_ITEMS or MAX_ITEMS==0) and backProd.items[0] == SRec.productionID){
                    addProductionToStateSet(crntPos, backSRec.productionID, backSRecSeqPos+1, backSRec.originPos, backSRec, SRec)
                } else{print("\n")}

            } else {if(prodTypeFlag==parseSEQ){
                if(backSRecSeqPos < backProd.items.size() and backProd.items[backSRecSeqPos] == SRec.productionID){
                    print(" ADVANCING SEQ: ")
                    addProductionToStateSet(crntPos, backSRec.productionID, backSRecSeqPos+1, backSRec.originPos, backSRec, SRec)
                } else {print(" Item is NOT ADVANCING  \n")}
            } else {if(prodTypeFlag==parseALT){
                withEach backAltProdID in backProd.items:{
                    if(backSRecSeqPos == 0 and backAltProdID==SRec.productionID){
                        print(" ADVANCING ALT: ")
                        addProductionToStateSet(crntPos, backSRec.productionID, backSRecSeqPos+1, backSRec.originPos, backSRec, SRec)
                    }
                }
            }}
            }
        }
        print("\n")
    }

    me bool: ruleIsDone(me bool: isTerminal, me uint32: seqPos, me uint32: ProdType, me uint32: numItems)<-{
        if(isTerminal and seqPos==1) {return(true)}
        if(!isTerminal){
            if(ProdType==parseSEQ and seqPos==numItems) {return(true)}
            if(ProdType==parseALT and seqPos==1) {return(true)}
        }
        return(false)
    }

    me bool: doParse() <- {
        parseFound <- false
        withEach crntPos in RANGE(0 .. SSets.size()):{
            their stateSets: SSet <- SSets[crntPos]
            me string: ch <- "x"
            if(crntPos+1 != SSets.size()) {
                ch <- textToParse[crntPos]
            }
            print('At position %i`crntPos` (%s`ch.data()`) - size:%i`SSet->stateRecs.size()`\n')  //, crntPos, textToParse[crntPos], SSet.stateRecs.size())
            withEach SRec in SSet.stateRecs:{
                their production: prod <- grammar[SRec.productionID]
                me uint32: ProdType <- prod.prodType
                me uint32: isTerminal <- prod.isTerm
                me uint32: seqPos <- SRec.SeqPosition
                print('    Processing Record #%i`SRec_key`, prodID:%i`SRec->productionID`... ')
        /*        if((isTerminal and seqPos==1)
                    or  (!isTerminal and (
                        (ProdType==parseSEQ and seqPos==prod.items.size())  or
                        (ProdType==parseALT and seqPos==1)
                        )
                    )) */
                if(ruleIsDone(isTerminal, seqPos, ProdType, prod.items.size())){             // COMPLETER
                    complete(SRec, crntPos)  // Notate that SEQ is finished, actually add parent's follower.
                }else{
                    if(isTerminal){       // SCANNER
                        // print("SCANNING \n") // Scanning means Testing for a Matching terminal
                        me uint32: len <- textMatches(SRec.productionID, crntPos)
                        if(len>0){ // if match succeeded
                            addProductionToStateSet(crntPos+len, SRec.productionID, 1, crntPos, SRec, 0)  // Notate that terminal is finished, mark for adding parent's follower.
                        }
                    }else{ // non-terminal                           // PREDICTOR
                        print("NON_TERMINAL \n")
                        if(ProdType == parseREP){
                            me uint32: MIN_ITEMS <- prod.items[1]
                            me uint32: MAX_ITEMS <- prod.items[2]
                            me bool: must_be   <- seqPos < MIN_ITEMS
                            me bool: cannot_be <- seqPos > MAX_ITEMS and (MAX_ITEMS!=0)
                            if(!must_be){
                                complete(SRec, crntPos)
                                print("         REP (TENT): ")
                                addProductionToStateSet(crntPos, prod.items[0], 0, crntPos, SRec, 0) // Tentative
                            } else {if(!cannot_be){
                                print("         REP: ")
                                addProductionToStateSet(crntPos, prod.items[0], 0, crntPos, SRec, 0)
                            }}
                        } else { // Not a REP
                            print("         SEQ|ALT: ")
                            addProductionToStateSet(crntPos, prod.items[seqPos], 0, crntPos, SRec, 0)  // Add a cause SEQ with cursor at the very beginning. (0)
                        }
                    }
                }
            }
        }
        print("\n\n#####################################\n")
        dump()
    }

    our stateRec: resolve(our stateRec: LastTopLevelItem, me string: indent) <- {
        if(!LastTopLevelItem){print("\nStateRecPtr is null.\n\n") exit(1)}
        our stateRec: crntRec <- LastTopLevelItem
        me uint32: seqPos <- crntRec.SeqPosition
        me uint32: prodID <- crntRec.productionID
        their production: Prod <- grammar[prodID]
        print(indent+'grammar[%i`prodID`] = ')
        crntRec.print(Prod)
        print("\n", indent, "\n")
        if(Prod.isTerm){
        } else{
            withEach subItem in Backward RANGE(0 .. seqPos):{
                print(indent, "   item #", subItem, ": \n")
                crntRec.child <- resolve(crntRec.cause, indent+"     | ")
                crntRec.prev.next <- crntRec
                crntRec <- crntRec.prev
                print(indent, "############# ") crntRec.print(Prod) print("\n")
            }
        }
        if(indent==""){print("\nRESOLVED\n\n")}
        return(crntRec)
    }
}
    """
    code=code.replace('#CONST_CODE_HERE', ConstList, 1)
    code=code.replace('#GRAMMAR_CODE_HERE', RuleList, 1)
    print "CODE:",code
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
    # If rule already exists, return the name rather than recreate it
    # is there a rule with the same term, flags, and prodData? (Only care about term+parseSEQ+data)
    ruleExists=False
    if (ruleExists):
        ruleName = 'XXXX'
    else:
        thisIDX=len(rules)
        if not isinstance(ruleName, basestring):
            ruleName="rule"+str(thisIDX)
        constDefs.append([ruleName, str(thisIDX)])
        #print "PRODDATA:", prodData
        if isinstance(prodData, list):
            prodData='['+(', '.join(map(str,prodData))) + ']'
        rules.append([ruleName, termOrNot, pFlags, prodData])
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
    appendRule('alphaSeq',  'term', 'parseAUTO', "alphabetic string")
    appendRule('uintSeq',   'term', 'parseAUTO', '(0123456789)[]')
    appendRule('intSeq',    'term', 'parseAUTO', '+-(0123456789)[]')
    appendRule('RdxSeq',    'term', 'parseAUTO', '+-(0123456789)[].(0123456789)[]')
    appendRule('alphaNumSeq',  'term', 'parseAUTO', "alpha-numeric string")
    appendRule('ws',        'term', 'parseAUTO', 'white space[]')
    appendRule('quotedStr1','term', 'parseAUTO', "Single quoted string with escapes")
    appendRule('quotedStr2','term', 'parseAUTO', "Double quoted string with escapes")
    appendRule('CID',       'term', 'parseAUTO', 'C-like identifier')
    appendRule('UniID',     'term', 'parseAUTO', 'Unicode identifier. Uses current Locale.')
    appendRule('printables','term', 'parseAUTO', "Seq of printable ascii chars")
    appendRule('toEOL',     'term', 'parseAUTO', "Read chars to End Of Line, including EOL.")
    # TODO: delimited List, keyWord




def fetchOrWriteParseRule(modelName, field):
    fieldName  =field['fieldName']
    fieldValue =field['value']
    typeSpec   =field['typeSpec']
    fieldType  =typeSpec['fieldType']
    fieldOwner =typeSpec['owner']

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
            print "Unusable const type in fetchOrWriteParseRule():", fieldType; exit(2);

    elif fieldOwner=='me':
        if fieldType=='string':        nameOut='quotedStr1'
        elif fieldType[0:4]=='uint':   nameOut='uintSeq'
        elif fieldType[0:3]=='int':    nameOut='intSeq'
        elif fieldType[0:6]=='double': nameOut='RdxSeq'
        elif fieldType[0:4]=='char':   nameOut=appendRule(nameIn,       "term", "parseSEQ",  None)
        elif fieldType[0:4]=='bool':   nameOut=appendRule(nameIn,       "term", "parseSEQ",  None)
        elif progSpec.isStruct(fieldType):
            objName=fieldType[0]
            print 'OBJNAME:', objName
            if objName=='ws' or objName=='quotedStr1' or objName=='quotedStr2' or objName=='CID' or objName=='UniID' or objName=='printables' or objName=='toEOL' or objName=='alphaNumSeq':
                nameOut=objName
            else:
                nameOut='parse_'+fieldType[0]
        elif progSpec.isAlt(fieldType):
            pass
        elif progSpec.isOpt(fieldType):
            pass
        elif progSpec.isCofactual(fieldType):
            pass
        else:
            print "Unusable type in fetchOrWriteParseRule():", fieldType; exit(2);
    else: print "Pointer types not yet handled in fetchOrWriteParseRule():", fieldType; exit(2);

    if('arraySpec' in typeSpec and typeSpec['arraySpec']):
        global rules
        containerSpec=typeSpec['arraySpec']
        idxType=''
        if 'indexType' in containerSpec:
            idxType=containerSpec['indexType']
        datastructID = containerSpec['datastructID']
        if idxType[0:4]=='uint': pass
        if(datastructID=='list'):
            nameOut=appendRule(nameOut+'REP', "nonterm", "parseREP", [nameOut, 0, 0])
        elif datastructID=='opt':
            nameOut=appendRule(nameOut+'OPT', "nonterm", "parseREP", [nameOut, 0, 1])
    field['parseRule']=nameOut
    return nameOut

def AddFields(objects, tags, listName, fields, SeqOrAlt):
    partIndexes=[]
    for field in fields:
        fname=field['fieldName']
        if(field['isNext']==True):
            ruleIdxStr = fetchOrWriteParseRule(listName, field)
            partIndexes.append(ruleIdxStr)
        else: pass;
    nameIn='parse_'+listName
    nameOut=appendRule(nameIn, "nonterm", SeqOrAlt, partIndexes)

def fetchMemVersion(objects, objName):
    # TODO: here we assume that the memory form has '::mem' using AutoAssigners, make this work with other forms.
    seperatorIdx= objName.find("::")
    #print "OBJNAME:", objName, seperatorIdx
    memVersionName=objName
    if seperatorIdx>=0:
        memVersionName=objName[:objName.find("::")]+"::mem"
    memObj=objects[0][memVersionName]
    return [memObj, memVersionName]


def Write_ALT_Extracter(objects, field, structName, fields, VarTag, VarName, indent):
    [memObj, memVersionName]=fetchMemVersion(objects, structName)
    InnerMemObjFields=memObj['fields']
    S=""
    S+='        me int32: ruleIDX <- '+VarTag+'.child.next.child.productionID\n'
    if VarName!='memStruct':
        S+=' me string: '+VarName+'\n'
    count=0
    for altField in fields:
        S+=indent
        if(count>0): S+="else "
        S+="if(ruleIDX == " + altField['parseRule'] + "){\n"
        S+=Write_fieldExtracter(objects, altField, InnerMemObjFields, VarTag, VarName, False, indent+'    ')
        S+=indent+"}"
        count+=1
    return S

def Write_fieldExtracter(objects, field, memObjFields, VarTag, VarName, advancePtr, indent):
    ###################   G a t h e r   N e e d e d   I n f o r m a t i o n
    S=''
    fieldName  =field['fieldName']
    fieldIsNext=field['isNext']
    fieldValue =field['value']
    typeSpec   =field['typeSpec']
    fieldType  =typeSpec['fieldType']
    fieldOwner =typeSpec['owner']

    toField = progSpec.fetchFieldByName(memObjFields, fieldName)
    if(toField==None):
        # Even tho there is no LVAL, we need to move the cursor. Also, there could be a co-factual.
        toFieldType = progSpec.TypeSpecsMinimumBaseType(objects, typeSpec)
        toTypeSpec=typeSpec
        toFieldOwner=None
    else:
        toTypeSpec   = toField['typeSpec']
        toFieldType  = toTypeSpec['fieldType']
        toFieldOwner = toTypeSpec['owner']
    print "        CONVERTING:", fieldName, toFieldType, typeSpec
    print "            TOFieldTYPE1:", toField
    print "            TOFieldTYPE :", toFieldOwner, toFieldType
    print "FIELD-NAME/TYPE:", fieldName,'/', fieldType
    fields=[]
    fromIsOPT =False
    fromIsStruct=progSpec.isStruct(fieldType)
    toIsStruct=progSpec.isStruct(toFieldType)
    [fromIsALT, fields] = progSpec.isAltStruct(objects, fieldType)
    fromIsList=False
    toIsList =False
    if 'arraySpec' in typeSpec and typeSpec['arraySpec']!=None:      fromIsList=True
    if 'arraySpec' in toTypeSpec and toTypeSpec['arraySpec']!=None:  toIsList=True

    ###################   W r i t e   R V A L   C o d e
    finalCodeStr=''
    if VarName=='' or VarName=='memStruct':  # Default to the target argument name
        VarName='memStruct'
        CODE_LVAR= VarName+'.'+fieldName
    else: CODE_LVAR=VarName
    CODE_RVAL=''
    objName=''
    doNextSuffix=''
    if(fieldIsNext==True):
        if advancePtr:
            S+=indent+VarTag+' <- getNextStateRec('+VarTag+')\n'
        else: doNextSuffix='.next'
        if fieldOwner=='const'and (toFieldOwner == None):
            finalCodeStr += VarTag+'_tmpStr'+' <- makeStr('+VarTag+'.child)\n'
            #  print("'+fieldValue+'")\n'

        else:
            if toFieldType=='string':            CODE_RVAL='makeStr('+VarTag+'.child'+doNextSuffix+')'+"\n"
            elif toFieldType[0:4]=='uint':       CODE_RVAL='makeInt('+VarTag+'.child'+doNextSuffix+')'+"\n"
            elif toFieldType[0:3]=='int':        CODE_RVAL='makeInt('+VarTag+'.child'+doNextSuffix+')'+"\n"
            elif toFieldType[0:6]=='double':     CODE_RVAL='makeDblFromStr('+VarTag+'.child'+doNextSuffix+')'+"\n"
            elif toFieldType[0:4]=='char':       CODE_RVAL="crntStr[0]"+"\n"
            elif toFieldType[0:4]=='bool':       CODE_RVAL='crntStr=="true"'+"\n"
            elif toIsStruct:
                objName=toFieldType[0]
                if objName=='ws' or objName=='quotedStr1' or objName=='quotedStr2' or objName=='CID' or objName=='UniID' or objName=='printables' or objName=='toEOL' or objName=='alphaNumSeq':
                    CODE_RVAL='makeStr('+VarTag+'.child'+doNextSuffix+')'
                    toIsStruct=false; # false because it is really a base type.
                else:
                    finalCodeStr=indent+'ExtractStruct_'+fieldType[0].replace('::', '_')+'('+VarTag+'.child, '+CODE_LVAR+')\n'

    else:
        pass
        # objFieldStr+= writeContextualGet(field) #'    func int: '+fname+'_get(){}\n'
        # objFieldStr+= writeContextualSet(field)

    #print "CODE_RVAL:", CODE_RVAL

    ###################   H a n d l e   o p t i o n a l   a n d   r e p e t i t i o n   a n d   a s s i g n m e n t   c a s e s
    gatherFieldCode=''
    if fromIsOPT: pass
    elif fromIsList and toIsList:
        gatherFieldCode+='\nour stateRec: childSRec <- '+VarTag+'.child.next\n    withEach Cnt in WHILE(childSRec):{\n'
        if fromIsALT:
            childRecName='childSRec'
            gatherFieldCode+=Write_ALT_Extracter(objects, field,  fieldType[0], fields, childRecName, 'tmpVar_tmpStr', indent+'    ')
            gatherFieldCode+='\n'+indent+CODE_LVAR+'.pushLast(tmpVar_tmpStr)'
            gatherFieldCode+=indent+'    '+childRecName+' <- getNextStateRec('+childRecName+')\n'
        elif fromIsStruct and toIsStruct:
            gatherFieldCode+='\n'+indent+'me '+toFieldType+': tmpVar_tmpStr'
            gatherFieldCode+='\n'+indent+'ExtractStruct_'+fieldType[0].replace('::', '_')+'(childSRec.child, '+tmpVar+')\n'
            gatherFieldCode+='\n'+indent+CODE_LVAR+'.pushLast(tmpVar_tmpStr)'
        else:
            gatherFieldCode+='\n'+indent+CODE_LVAR+'.pushLast('+codeStr+')'

        gatherFieldCode+='\n'+indent+'}\n'
    else:
        if toIsList: print "Error: parsing a non-list to a list is not supported.\n"; exit(1);
        assignerCode=''
        if fromIsALT:
            assignerCode+=Write_ALT_Extracter(objects, field,  fieldType[0], fields, VarTag, VarName+'X', indent+'    ')
            assignerCode+=indent+CODE_LVAR+' <- '+(VarName+'X')+"\n"

        elif fromIsStruct and toIsStruct:
            assignerCode+=finalCodeStr;
        else:
           # if toFieldOwner == 'const': print "Error: Attempt to extract a parse to const field.\n"; exit(1);
            if CODE_RVAL!="": assignerCode+='        '+CODE_LVAR+' <- '+CODE_RVAL+"\n"
            elif finalCodeStr!="": assignerCode+=finalCodeStr;
        gatherFieldCode = assignerCode

    S+=gatherFieldCode
    #print "ASSIGN_CODE", S

    return S

def Write_structExtracter(objects, tags, objName, fields):
    [memObj, memVersionName]=fetchMemVersion(objects, objName)
    memObjFields=memObj['fields']
    print "OBJ FIELDS:",objName,  memObjFields

    S='    me string: SRec_tmpStr'
    for field in fields:
        S+=Write_fieldExtracter(objects, field, memObjFields, 'SRec', '', True, '    ')

    seqExtracter =  "\n    me bool: ExtractStruct_"+objName.replace('::', '_')+"(our stateRec: SRec, their "+memVersionName+": memStruct) <- {\n" + S + "    }\n"
    return seqExtracter


def CreateStructsForStringModels(objects, tags):
    print "Creating structs from string models..."

    # Define fieldResult struct
    #~ structsName = 'fetchResult'
    #~ StructFieldStr = "mode [fetchOK, fetchNotReady, fetchSyntaxError, FetchIO_Error] : FetchResult"
    #~ progSpec.addObject(objects[0], objects[1], structsName, 'struct', 'SEQ')
    #~ codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef(structsName, StructFieldStr))

    populateBaseRules()

    ExtracterCode="""

    me string: makeStr(our stateRec: SRec) <- {
        me string: S
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
        me int64: N <- atoi(S.data())
        return(N)
    }
    our stateRec: getNextStateRec(our stateRec: SRec) <- {if(SRec.next){ return(SRec.next)} return(0) }
    """

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

            # Write the rules for all the fields, and a parent rule which is either SEQ or ALT, and REP/OPT as needed.
            AddFields(objects, tags, objectName.replace('::', '_'), fields, SeqOrAlt)

            if SeqOrAlt=='parseSEQ':
                ExtracterCode += Write_structExtracter(objects, tags, objectName, fields)

    if numStringStructs==0: return


    tags['Include'] += ",<cctype>"

    # Define streamSpan struct
    structsName = 'streamSpan'
    StructFieldStr = "    me uint32: offset \n    me uint32: len"
    progSpec.addObject(objects[0], objects[1], structsName, 'struct', 'SEQ')
    codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef(structsName, StructFieldStr))



    ############  Add struct parser
    parserCode=genParserCode()
    codeDogParser.AddToObjectFromText(objects[0], objects[1], parserCode)

    structsName='EParser'
    print progSpec.wrapFieldListInObjectDef(structsName, ExtracterCode)+"\n"
    #exit(2)
    progSpec.addObject(objects[0], objects[1], structsName, 'struct', 'SEQ')
    codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef(structsName, ExtracterCode))
