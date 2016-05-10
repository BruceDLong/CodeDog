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

def genParserCode(consts, parseRuleList):
    code= r"""
//enum FLAGs{maskTermMode=2, fTerm=2, maskProdMode=4+8+16, pmSEQ=4, pmALT=8, pmREP=12, pmOPT=16, maskInvert=64};
model productionLvl {mode [terminal, non_terminal] : productionLvl}
model productionMode {mode [SEQ, ALT, REP, OPT] : productionMode}

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
    mode[SEQ, ALT, REP, OPT]: prodType
    me string: constStr
    me uint32[list uint32]: items
   // production(me uint32: f, me string: s):flags(f), constStr(s) {}
   // production(me uint32: f, vector<int> terms):flags(f) { for(auto t:terms) {items.push_back(t)}}
    me void: print(me uint32: SeqPos, me uint32: originPos) <- {
        me uint32: ProdType ProdType <- prodType
        print("[")
        print(prodType)
        if(isTerm){
            if(SeqPos==0) {print("# ")}
            print('"%s`constStr.data()`"')
            if(SeqPos>0) {print("# ")}
            print(', Origin:%i`originPos`')
        } else{
            withEach p in items:{
                if(p_key==SeqPos and ProdType!=REP){ print("# ")}
                print('%i`p` ')
            }
            if(ProdType==REP){ print('(POS:%i`SeqPos`)')}
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

    me void: dump() <- <% {
        for(int crntPos=0; crntPos<=SSets.size(); crntPos++){
            stateSets &SSet=SSets[crntPos];
            printf("SLOT: %i (%c) - size:%i\n", crntPos, textToParse[crntPos], (int)SSet.stateRecs.size());
            for(int crntRec=0; crntRec<SSet.stateRecs.size(); ++crntRec){
//                stateRec &SRec = &SSet.stateRecs[crntRec];
//                production& prod=grammar[SRec->productionID];
//                printf("    %p (%p, %p): ", SRec, SRec->child, SRec->prev); prod.print(SRec->SeqPosition, SRec->originPos);
            }
        }
    }; %>

    me void: populateGrammar() <- {
    //    grammar.push_back(production(SEQ, (vector<int>){1, 2}));
    //    grammar.push_back(production(fTerm+SEQ, "Hello"));
    //    grammar.push_back(production(fTerm+SEQ, " World!"));
//        grammar.push_back(production(REP, (vector<int>){1, 2, 6}));
//        grammar.push_back(production(SEQ, (vector<int>){2, 3, 4}));
//        grammar.push_back(production(fTerm+SEQ, "{"));
//        grammar.push_back(production(fTerm+SEQ, "X"));
//        grammar.push_back(production(fTerm+SEQ, "} "));
    }

    me void: addProductionToStateSet(me uint32: crntPos, me uint32: productionID, me uint32: SeqPos, me uint32: origin, our stateRec: prev, our stateRec: child) <- {
        print('############ ADD %i`productionID` at %i`crntPos` (prev=%p`prev`): ')
        withEach item in SSets[crntPos].stateRecs:{ // Don't add duplicates.
            // TODO: change this to be faster. Not a linear search.
            if(item.productionID==productionID and item.SeqPosition==SeqPos and item.originPos==origin){
                print("DUPLICATE\n")
                return()
            }
        }

        me uint32: ProdType ProdType <- grammar[productionID].prodType
        if(ProdType == SEQ or ProdType == REP){
            grammar[productionID].print(SeqPos, origin)
            our stateRec: newStateRecPtr newStateRecPtr.allocate(productionID, SeqPos, origin, prev, child)
            SSets[crntPos].stateRecs.pushLast(newStateRecPtr)
            print('ADDED %i`SeqPos`, %p`prev`\n')
        } else {if(ProdType == ALT){
            print("ALT\n")
            withEach AltProd in grammar[productionID].items:{
                print("         ALT: ")
                addProductionToStateSet(crntPos, AltProd, 0, origin, prev, child)
            }
        }}
    }

    me void: initPosStateSets(me uint64: startProd, me string: txt) <- {
        startProduction <- startProd
        textToParse <- txt
        SSets.clear()
        withEach i in RANGE(0 .. txt.size()+1):{
            me stateSets: newSSet
            SSets.pushLast(newSSet)
        }
        addProductionToStateSet(0, startProduction, 0, 0, 0,0)
    }

    me uint32: textMatches(their production: Prod, me uint32: pos) <- {
        // TODO: write textMatches()
        // TODO: handle REP and OPT
        print("    MATCHING: ")
        me uint32: L L <- Prod.constStr.size()
        if(true){ //prod is simple text match
            if(pos+L > textToParse.size()){print("size-fail\n") return(0)}
            withEach i in RANGE(0 .. L):{
//                if( Prod.constStr[i] != textToParse[pos+i]) {return(0)}
            }
        //    printf("YES (%s)\n", Prod.constStr.data());
            return(L)
        } else{
        }
        return(0)
    }

    me bool: complete(our stateRec: SRec, me int32: crntPos) <- {
        print('        COMPLETER... %p`SRec`')
        their stateSets: SSet SSet <- SSets[SRec.originPos]
        withEach backSRec in SSet.stateRecs:{
            me uint32[list uint32]: items items <- grammar[backSRec.productionID].items
            print('************* SRec.child=%p`SRec->child`, %p`backSRec`\n')
            if(grammar[backSRec.productionID].prodType==REP){
                me uint32: MAX_ITEMS MAX_ITEMS <- items[2]
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
        // TODO: Add pred links and extract a parse tree.
        withEach crntPos in RANGE(0 .. SSets.size()):{
            their stateSets: SSet SSet <- SSets[crntPos]
            print("At position %i`crntPos` (%c`textToParse[crntPos]`) - size:%i`(int)SSet.stateRecs.size()`\n")
            withEach SRec in SSet.stateRecs:{
                their production: prod prod <- grammar[SRec.productionID]
                me uint32: ProdType   ProdType  <- prod.prodType
                me uint32: isTerminal isTerminal<- prod.isTerm
                print("    => Set/Rec: %i`crntPos`/%i`SRec_key`, prodID:%i`SRec->productionID` ")
                if((isTerminal and SRec.SeqPosition==1)
                    or  (!isTerminal and ProdType!=REP and SRec.SeqPosition==prod.items.size())){             // COMPLETER
                    complete(SRec, crntPos)
                }else{
                    if(isTerminal){       // SCANNER
                        print("SCANNING \n")
                        me uint32: len len <- textMatches(prod, crntPos)
                        if(len>0){ // if match succeeded
                            print("         MATCHED: ")
                            addProductionToStateSet(crntPos+len, SRec.productionID, 1, crntPos, 0, 0)
                        }
                    }else{ // non-terminal                           // PREDICTOR
                        print("NON_TERMINAL \n")
                        if(ProdType == REP){
                            me uint32: MIN_ITEMS MIN_ITEMS <- prod.items[1]
                            me uint32: MAX_ITEMS MAX_ITEMS <- prod.items[2]
                            me bool: must_be   must_be  <- SRec.SeqPosition<MIN_ITEMS
                            me bool: cannot_be cannot_be<- SRec.SeqPosition>MAX_ITEMS
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

def populateBaseRules():
    rules=[]
    constDefs=[]

    return [constDefs, rules]

def writeParseRule(crIdx, modelName, field):
    print "WRITE PARSE RULE:", crIdx, modelName, field
    rules=[]
    constDefs=[]
    fieldName  =field['fieldName']
    fieldValue =field['value']
    typeSpec   =field['typeSpec']
    fieldType  =typeSpec['fieldType']
    fieldOwner =typeSpec['owner']

    if fieldOwner=='const':
        if fieldType=='string':        rules.append(["fTerm+pmSEQ", '"'+fieldValue+'"'])
        elif fieldType[0:4]=='uint':   rules.append(["fTerm+pmUint",  fieldValue])
        elif fieldType[0:3]=='int':    rules.append(["fTerm+pmInt",   fieldValue])
        elif fieldType[0:6]=='double': rules.append(["fTerm+pmRadix", fieldValue])
        elif fieldType[0:4]=='char':   rules.append(["fTerm+pmChar",  fieldValue])
        elif fieldType[0:4]=='bool':   rules.append(["fTerm+pmBool",  fieldValue])
        else:
            print "Unusable const type in writeParseRule()"; exit(2);

    elif fieldOwner=='me':
        if fieldType=='string':        rules.append(["fTerm+pmQuotedString", None])
        elif fieldType[0:4]=='uint':   rules.append(["fTerm+pmUint",  None])
        elif fieldType[0:3]=='int':    rules.append(["fTerm+pmInt",   None])
        elif fieldType[0:6]=='double': rules.append(["fTerm+pmRadix", None])
        elif fieldType[0:4]=='char':   rules.append(["fTerm+pmChar",  None])
        elif fieldType[0:4]=='bool':   rules.append(["fTerm+pmBool",  None])
        elif progSpec.isStruct(fieldType):      rules.append(["pmSeq", ["parse_"+fieldType]])
        elif progSpec.isAlt(fieldType):
            pass
        elif progSpec.isOpt(fieldType):
            pass
        elif progSpec.isCofactual(fieldType):
            pass
        else:
            print "Unusable type in writeParseRule()"; exit(2);

    if typeSpec['arraySpec']:         rules.append(["pmRep", [crntIdx, 0, None]])


    return [constDefs, rules]

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


    constsMap={}      # store const defs to be coded
    parseRuleList=[]  # store rule defs to be coded
    [consts, parseRules] = populateBaseRules()
    constsMap.update(consts)
    parseRuleList+=parseRules
    for objectName in objects[1]:
        print "OBJECT:", objectName
        if objectName[0] == '!': continue
        ObjectDef = objects[0][objectName]
        if(objectName[0] != '!' and ObjectDef['stateType'] == 'string'):

            print "    WRITING STRING-STRUCT:", objectName
            # TODO: modelExists=findCoorespondingModel()  this function may already be coded somewhere.
            numIsNextFields=0
            thisStructsIDX=len(parseRuleList)
            constsMap["parse_"+objectName]=thisStructsIDX
            parseRuleList.append(["pmSEQ", []])  # Fill this in below
            for field in ObjectDef['fields']:
                fname=field['fieldName']
                print "        ", field

                #### First, write fetch function for this field...
                #objFieldTypeStr=codeDogTypeToString(objects, tags, field)
                if(field['isNext']==True):
                    numIsNextFields+=1
                    crIdx=thisStructsIDX+numIsNextFields
                    [consts, parseRules] = writeParseRule(crIdx, objectName, field)
                    constsMap.update(consts)
                    parseRuleList+=parseRules


                   # objFieldStr+="    flag: "+fname+'_hasPos\n'
                   # objFieldStr+="    flag: "+fname+'_hasLen\n'
                   # objFieldStr+="    me streamSpan: "+fname+'_span\n'
                   # objFieldStr+= writePositionalFetch(objects, tags, field)
                   # objFieldStr+= writePositionalSet(field)
                else:
                    pass
                   # objFieldStr+= writeContextualGet(field) #'    func int: '+fname+'_get(){}\n'
                   # objFieldStr+= writeContextualSet(field)
            parseRuleList[thisStructsIDX][1]=range(thisStructsIDX+1, thisStructsIDX+numIsNextFields) # Complete the structs parse rule

            #if(configType=='SEQ'):  primaryFetchFuncText+='    return(fetchOK)\n'
            #elif(configType=='ALT'):primaryFetchFuncText+='    return(fetchSyntaxError)\n'
            #primaryFetchFuncText+='\n}\n'
            #objFieldStr += primaryFetchFuncText
            #print "#################################### objFieldStr:\n", objFieldStr, '\n####################################'
            #structsName = objectName+"_struct"
            #progSpec.addObject(objects[0], objects[1], structsName, 'struct', 'SEQ')
            #codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef(structsName, objFieldStr))

    ############  Add struct parser
    parserCode=genParserCode(consts, parseRuleList)
    structsName = "chartParser"
    #progSpec.addObject(objects[0], objects[1], structsName, 'struct', 'SEQ')
    codeDogParser.AddToObjectFromText(objects[0], objects[1], parserCode)
