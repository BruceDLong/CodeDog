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
            RuleList+='        addTerminalProd("' + rule[0] +'", ' + rule[2] + ', "' + str(rule[3]) + '")\n'
        elif rule[1]=='nonterm':
            RuleList+='        addNon_TermProd("' + rule[0] +'", ' + rule[2] + ', ' + str(rule[3]) + ')\n'

    ConstList=''
    for C in constDefs:
        ConstList+='    const uint32: ' + C[0].replace('::','_') + ' <- ' + str(C[1]) + '\n'

    code= r"""
struct stateRec{
   // stateRec(me uint32: prodID, me uint32: SeqPos, me uint32: origin, stateRec* Prev, stateRec* Child):productionID(prodID), SeqPosition(SeqPos), originPos(origin), prev(Prev), child(Child){}
    me uint32: productionID
    me uint32: SeqPosition
    me uint32: originPos
    our stateRec: prev
    our stateRec: child
}
struct stateRecPtr{our stateRec: stateRecPtr}

struct stateSets{
    me stateRecPtr[list uint32]: stateRecs
    me uint64: flags
    //stateSets():flags(0){}
}

struct production{
    flag: isTerm
    mode[parseSEQ, parseALT, parseREP, parseOPT, parseInt, parseUint, parseQuoted1String, parseQuoted2String, parseBool, parseRadix, parseChar]: prodType
    me string: constStr
    me uint32[list uint32]: items
    void: print(me uint32: SeqPos, me uint32: originPos) <- {
        me uint32: ProdType <- prodType
        print("[")
        print(prodType, ": ")
        if(isTerm){
            if(SeqPos==0) {print(" > ")}
            print('"%s`constStr.data()`"')
            if(SeqPos>0) {print(" > ")}
            print(', Origin:%i`originPos`')
        } else {
            withEach p in items:{
                if(p_key==SeqPos and ProdType!=parseREP){ print(" > ")}
                print('%i`p` ')
            }
            if(ProdType==parseREP){ print('(POS:%i`SeqPos`)')}
            print(', Origin:%i`originPos` ')
        }
        print("]\n")
    }
}


struct EParser{
    me string: textToParse
    me uint64: startProduction
    me stateSets[list uint32]: SSets
    me production[list uint32]: grammar
    me bool: parseFound

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
            print('"SLOT: %i`crntPos` (%s`ch.data()`) - size:%i`(int)SSet->stateRecs.size()`\n')
            withEach SRec in SSet.stateRecs:{
                their production: prod <- grammar[SRec.productionID]
                print('    %p`SRec` (%p`SRec->child`, %p`SRec->prev`): ')
                prod.print(SRec.SeqPosition, SRec.originPos)
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

    me void: addProductionToStateSet(me uint32: crntPos, me uint32: productionID, me uint32: SeqPos, me uint32: origin, our stateRec: prev, our stateRec: child) <- {
        print('############ ADDING rule %i`productionID` at char slot %i`crntPos` (prev=%p`prev`): ')
        withEach item in SSets[crntPos].stateRecs:{ // Don't add duplicates.
            // TODO: change this to be faster. Not a linear search.
            if(item.productionID==productionID and item.SeqPosition==SeqPos and item.originPos==origin){
                print("DUPLICATE\n")
                return()
            }
        }
        their production: prod <- grammar[productionID]
        if(productionID==startProduction and SeqPos==prod.items.size() and origin==0){
            parseFound <- true
            print("\n\nPARSE PASSED!!!\n\n")
        }
        me uint32: ProdType <- prod.prodType
        if(ProdType == parseSEQ or ProdType == parseREP){
            prod.print(SeqPos, origin)
            our stateRec: newStateRecPtr newStateRecPtr.allocate(productionID, SeqPos, origin, prev, child)
            SSets[crntPos].stateRecs.pushLast(newStateRecPtr)
            print('                         ADDED with SeqPos=%i`SeqPos`, %p`prev`\n')
        } else {if(ProdType == parseALT){
            print("                         ALT\n")
            withEach AltProd in prod.items:{
                print("                                  ALT: ")
                addProductionToStateSet(crntPos, AltProd, 0, origin, prev, child)
            }
        }}
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

    void: resolve() <- {}

    me uint32: textMatches(their production: Prod, me uint32: pos) <- {
        // TODO: write textMatches()
        // TODO: handle REP and OPT
        print('    MATCHING %s`Prod->constStr.data()`: ')
        me uint32: L <- Prod.constStr.size()
        if(true){ //prod is simple text match
            if(pos+L > textToParse.size()){print("FAILED (target string too short)\n") return(0)}
            withEach i in RANGE(0 .. L):{
                if( Prod.constStr[i] != textToParse[pos+i]) {print("FAILED\n") return(0)}
            }
            print("PASSED\n")
            return(L)
        } else{
        }
        print("Huh???\n")
        return(0)
    }

    me bool: complete(our stateRec: SRec, me int32: crntPos) <- {
        print('        COMPLETER... %p`SRec`')
        their stateSets: SSet  <- SSets[SRec.originPos]
        withEach backSRec in SSet.stateRecs:{
            me uint32[list uint32]: items <- grammar[backSRec.productionID].items
            print('************* SRec.child=%p`SRec->child`, %p`backSRec`\n')
            if(grammar[backSRec.productionID].prodType==parseREP){
                me uint32: MAX_ITEMS  <- items[2]
                if((backSRec.SeqPosition < MAX_ITEMS) and items[0] == SRec.productionID){
                    addProductionToStateSet(crntPos, backSRec.productionID, backSRec.SeqPosition+1, backSRec.originPos, backSRec, SRec)

                }

            } else {
                if(items.size()>backSRec.SeqPosition and items[backSRec.SeqPosition] == SRec.productionID){
                    print("     COMPLETE: ")
                    addProductionToStateSet(crntPos, backSRec.productionID, backSRec.SeqPosition+1, backSRec.originPos, backSRec, SRec)
                } else {print("NOT COMPLETED  ")}
            }
        }
        print("\n")
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
                print('    => Set/Rec: %i`crntPos` / %i`SRec_key`, prodID:%i`SRec->productionID` ') //, crntPos, SRec_key, SRec.productionID)
                if((isTerminal and SRec.SeqPosition==1)
                    or  (!isTerminal and ProdType!=parseREP and SRec.SeqPosition==prod.items.size())){             // COMPLETER
                    complete(SRec, crntPos)
                }else{
                    if(isTerminal){       // SCANNER
                        print("SCANNING \n")
                        me uint32: len <- textMatches(prod, crntPos)
                        if(len>0){ // if match succeeded
                            print("         MATCHED: ")
                            addProductionToStateSet(crntPos+len, SRec.productionID, 1, crntPos, 0, 0)
                        }
                    }else{ // non-terminal                           // PREDICTOR
                        print("NON_TERMINAL \n")
                        if(ProdType == parseREP){
                            me uint32: MIN_ITEMS <- prod.items[1]
                            me uint32: MAX_ITEMS <- prod.items[2]
                            me bool: must_be   <- SRec.SeqPosition<MIN_ITEMS
                            me bool: cannot_be <- SRec.SeqPosition>MAX_ITEMS and (MAX_ITEMS!=0)
                            if(!must_be){
                                complete(SRec, crntPos)
                                print("         REP (TENT): ")
                                addProductionToStateSet(crntPos, prod.items[0], 0, crntPos, 0, 0) // Tentative
                            } else {if(!cannot_be){
                                print("         REP: ")
                                addProductionToStateSet(crntPos, prod.items[0], 0, crntPos, 0, 0)
                            }}
                        } else { // Not a REP
                            print("         SEQ|ALT: ")
                            addProductionToStateSet(crntPos, prod.items[SRec.SeqPosition], 0, crntPos, 0, 0)
                        }
                    }
                }
            }
        }
        print("\n\n#####################################\n")
        dump()
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
        print "PRODDATA:", prodData
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


def fetchOrWriteParseRule(modelName, field):
    print "WRITE PARSE RULE:", modelName, field
    fieldName  =field['fieldName']
    fieldValue =field['value']
    typeSpec   =field['typeSpec']
    fieldType  =typeSpec['fieldType']
    fieldOwner =typeSpec['owner']

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
        if fieldType=='string':        nameOut=appendRule(nameIn, "term", "parseQuoted2String", None)
        elif fieldType[0:4]=='uint':   nameOut=appendRule(nameIn, "term", "parseREP",  "0123456789")
        elif fieldType[0:3]=='int':    nameOut=appendRule(nameIn, "term", "parseInt",   None)
        elif fieldType[0:6]=='double': nameOut=appendRule(nameIn, "term", "parseRadix", None)
        elif fieldType[0:4]=='char':   nameOut=appendRule(nameIn, "term", "parseChar",  None)
        elif fieldType[0:4]=='bool':   nameOut=appendRule(nameIn, "term", "parseBool",  None)
        elif progSpec.isStruct(fieldType): nameOut='parse_'+fieldType[0]
        elif progSpec.isAlt(fieldType):
            pass
        elif progSpec.isOpt(fieldType):
            pass
        elif progSpec.isCofactual(fieldType):
            pass
        else:
            print "Unusable type in fetchOrWriteParseRule():", fieldType; exit(2);
    else: print "Pointer types not yet handled in fetchOrWriteParseRule():", fieldType; exit(2);

    if typeSpec['arraySpec']: nameOut=appendRule(nameIn, "nonterm", "parseREP", [crntIdx, 0, 0])


    return nameOut

def AddFields(objects, tags, listName, fields, SeqOrAlt):
    partIndexes=[]
    for field in fields:
        fname=field['fieldName']
        print "        ", field
        if(field['isNext']==True):
            ruleIdxStr = fetchOrWriteParseRule(listName, field)
            partIndexes.append(ruleIdxStr)
        else: pass;
    nameIn='parse_'+listName
    nameOut=appendRule(nameIn, "nonterm", SeqOrAlt, partIndexes)
    #if typeSpec['arraySpec']: nameOut=appendRule(nameIn, "nonterm", "parseREP", [crntIdx, 0, 0])

def Write_Fetch_and_Set_Functions_For_Each_Field(objects, tags, listName, fields, SeqOrAlt):
    #### First, write fetch function for this field...
    #objFieldTypeStr=codeDogTypeToString(objects, tags, field)
    for field in fields:
        fname=field['fieldName']
        print "        ", field
        if(field['isNext']==True):
            pass
           # objFieldStr+="    flag: "+fname+'_hasPos\n'
           # objFieldStr+="    flag: "+fname+'_hasLen\n'
           # objFieldStr+="    me streamSpan: "+fname+'_span\n'
           # objFieldStr+= writePositionalFetch(objects, tags, field)
           # objFieldStr+= writePositionalSet(field)
        else:
            pass
           # objFieldStr+= writeContextualGet(field) #'    func int: '+fname+'_get(){}\n'
           # objFieldStr+= writeContextualSet(field)


def CreateStructsForStringModels(objects, tags):
    print "Creating structs from string models..."

    # Define fieldResult struct
    #~ structsName = 'fetchResult'
    #~ StructFieldStr = "mode [fetchOK, fetchNotReady, fetchSyntaxError, FetchIO_Error] : FetchResult"
    #~ progSpec.addObject(objects[0], objects[1], structsName, 'struct', 'SEQ')
    #~ codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef(structsName, StructFieldStr))

    # Define streamSpan struct
    structsName = 'streamSpan'
    StructFieldStr = "    me uint32: offset \n    me uint32: len"
    progSpec.addObject(objects[0], objects[1], structsName, 'struct', 'SEQ')
    codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef(structsName, StructFieldStr))


    populateBaseRules()

    for objectName in objects[1]:
        print "OBJECT:", objectName
        if objectName[0] == '!': continue
        ObjectDef = objects[0][objectName]
        if(ObjectDef['stateType'] == 'string'):

            print "    WRITING STRING-STRUCT:", objectName
            # TODO: modelExists = progSpec.findModelOf(objMap, structName)
            fields=ObjectDef['fields']
            configType=ObjectDef['configType']
            SeqOrAlt=''
            if configType=='SEQ': SeqOrAlt='parseSEQ'
            elif configType=='ALT': SeqOrAlt='parseALT'

            # Write the rules for all the fields, and a parent rule which is either SEQ or ALT, and REP/OPT as needed.
            AddFields(objects, tags, objectName.replace('::', '_'), fields, SeqOrAlt)

            Write_Fetch_and_Set_Functions_For_Each_Field(objects, tags, objectName, fields, SeqOrAlt)


            #if(configType=='SEQ'):  primaryFetchFuncText+='    return(fetchOK)\n'
            #elif(configType=='ALT'):primaryFetchFuncText+='    return(fetchSyntaxError)\n'
            #primaryFetchFuncText+='\n}\n'
            #objFieldStr += primaryFetchFuncText
            #print "#################################### objFieldStr:\n", objFieldStr, '\n####################################'
            #structsName = objectName+"_struct"
            #progSpec.addObject(objects[0], objects[1], structsName, 'struct', 'SEQ')
            #codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef(structsName, objFieldStr))

    ############  Add struct parser
    parserCode=genParserCode()
    codeDogParser.AddToObjectFromText(objects[0], objects[1], parserCode)
