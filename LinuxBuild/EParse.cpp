// Workspace C++ file to help design parsing techniques

#include <fstream>
#include <cstdint>
#include <string>
#include <cstring>
#include <vector>
#include <map>
#include <cstdarg>
#include <iostream>

using namespace std;

const int startProduction=0;
string stringConstants[] = {"{", "}", "[", "]"};

enum FLAGs{maskTermMode=2, fTerm=2, maskProdMode=4+8+16, pmSEQ=4, pmALT=8, pmREP=12, pmOPT=16, maskInvert=64};

struct stateRec{
    stateRec(int prodID, int SeqPos, int origin):productionID(prodID), SeqPosition(SeqPos), originPos(origin){}
    int productionID;
    int SeqPosition;
    int originPos;
};

struct stateSets{
    vector<stateRec> stateRecs;
    uint64_t flags;
    stateSets():flags(0){};
};

struct production{
    uint32_t flags;
    string constStr;
    vector<int> items;
    production(int32_t f, string s):flags(f), constStr(s) {};
    production(int32_t f, vector<int> terms):flags(f) { for(auto t:terms) {items.push_back(t);}};
    void print(int SeqPos=0, int originPos=0){
        int ProdType=flags & maskProdMode;
        int isTerminal= flags & maskTermMode;
        printf("[");
        switch(ProdType){
        case pmSEQ: printf("SEQ:");   break;
        case pmALT: printf("ALT:");   break;
        case pmREP: printf("REP:");   break;
        case pmOPT: printf("OPT:");   break;
        }
        if(isTerminal){
            if(SeqPos==0) printf("# ");
            printf("'%s'", constStr.data());
            if(SeqPos>0) printf("# ");
        } else{
            int p;
            for(p=0; p<items.size(); ++p){
                if(p==SeqPos && ProdType!=pmREP) printf("# ");
                printf("%i ", items[p]);
            }
            if(p==SeqPos && ProdType!=pmREP) printf("# ");
            if(ProdType==pmREP){ printf("(POS:%i)", SeqPos);}
        }
        printf("]\n");
    }
};
const string toParse="BING-BING-BING-BING-BING-";
//const string toParse="Hello World!";

struct testParser{
    string textToParse;
    vector<stateSets> SSets;
    vector<production> grammar;

    void populateGrammar(){
    //    grammar.push_back(production(pmSEQ, (vector<int>){1, 2}));
    //    grammar.push_back(production(fTerm+pmSEQ, "Hello"));
    //    grammar.push_back(production(fTerm+pmSEQ, " World!"));
        grammar.push_back(production(pmREP, (vector<int>){1, 2, 6}));
        grammar.push_back(production(fTerm+pmSEQ, "BING-"));
    };
    void initPosStateSets(string txt){
        textToParse=txt;
        SSets.clear();
        for(int i=0; i<txt.size(); ++i){
            SSets.push_back(stateSets());
        }
        addProductionToStateSet(0, startProduction, 0, 0);
    };
    void addProductionToStateSet(int crntPos, int productionID, int SeqPos, int origin){
        printf("############ ADD %i at %i: ", productionID, crntPos);
        for(stateRec& item: SSets[crntPos].stateRecs){ // Don't add duplicates.
            // TODO: change this to be faster. Not a linear search.
            if(item.productionID==productionID && item.SeqPosition==SeqPos && item.originPos==origin){
                printf("DUPLICATE\n");
                return;
            }
        }

        production& prod=grammar[productionID];
        int ProdType=prod.flags & maskProdMode;
        if(ProdType == pmSEQ || ProdType == pmREP){
            grammar[productionID].print(SeqPos, origin);
            SSets[crntPos].stateRecs.push_back(stateRec(productionID, SeqPos, origin));
        } else if(ProdType == pmALT){
            printf("ALT\n");
            for(auto AltProd : prod.items){
                printf("         ALT: ");
                addProductionToStateSet(crntPos, AltProd, 0, origin);
            }
        }
    };
    int textMatches(production& Prod, int pos){
        // TODO: write textMatches()
        // TODO: handle REP and OPT
       // printf("    MATCHING: ");
        int L=Prod.constStr.size();
        if(true){ //prod is simple text match){
            if(pos+L > textToParse.size()){printf("size-fail\n"); return 0; }
            for(int i=0; i<L; ++i){
                if( Prod.constStr[i] != textToParse[pos+i]) {return 0;}
            }
        //    printf("YES (%s)\n", Prod.constStr.data());
            return L;
        } else{
        }
        return 0;
    };
    bool complete(stateRec& SRec, int crntPos){
        printf("        COMPLETER... ");
        for(stateRec backSRec:SSets[SRec.originPos].stateRecs){
            auto flags=grammar[backSRec.productionID].flags;
            int ProdType  = flags & maskProdMode;
            int isTerminal= flags & maskTermMode;
            vector<int>& items=grammar[backSRec.productionID].items;
            if(ProdType==pmREP){
                int MAX_ITEMS=items[2];
                if((backSRec.SeqPosition < MAX_ITEMS) && items[0] == SRec.productionID){
                    addProductionToStateSet(crntPos, backSRec.productionID, backSRec.SeqPosition+1, backSRec.originPos);
                }

            } else {
                if(items.size()>backSRec.SeqPosition && items[backSRec.SeqPosition] == SRec.productionID){
                    printf("     COMPLETE: ");
                    addProductionToStateSet(crntPos, backSRec.productionID, backSRec.SeqPosition+1, backSRec.originPos);
                } else printf("NOT COMPLETED  ");
            }
        }
        printf("\n");
    };
    bool doParse(){
        // TODO: Add pred links and extract a parse tree.
        for(int crntPos=0; crntPos<SSets.size(); crntPos++){
            stateSets &SSet=SSets[crntPos];
            printf("At position %i (%c) - size:%i\n", crntPos, textToParse[crntPos], (int)SSet.stateRecs.size());
            for(int crntRec=0; crntRec<SSet.stateRecs.size(); ++crntRec){
                stateRec& SRec=SSet.stateRecs[crntRec];

                production& prod=grammar[SRec.productionID];
                uint numberOfItems=prod.items.size();
                int ProdType  = prod.flags & maskProdMode;
                int isTerminal= prod.flags & maskTermMode;
                printf("    => Set/Rec: %i/%i, prodID:%i ",crntPos, crntRec, SRec.productionID);
                if((isTerminal && SRec.SeqPosition==1)
                    ||  (!isTerminal && ProdType!=pmREP && SRec.SeqPosition==numberOfItems)){             // COMPLETER
                    complete(SRec, crntPos);
                }else{
                    if((prod.flags & maskTermMode)==fTerm){       // SCANNER
                        printf("SCANNING \n");
                        int len=textMatches(prod, crntPos);
                        if(len>0){ // if match succeeded
                            printf("         MATCHED: ");
                            addProductionToStateSet(crntPos+len, SRec.productionID, 1, crntPos);
                        }
                    }else{ // non-terminal                           // PREDICTOR
                        printf("NON_TERMINAL \n");
                        if((prod.flags & maskProdMode) == pmREP){
                            int MIN_ITEMS=prod.items[1];
                            int MAX_ITEMS=prod.items[2];
                            bool must_be  = SRec.SeqPosition<MIN_ITEMS;
                            bool cannot_be= SRec.SeqPosition> MAX_ITEMS;
                            if(!must_be){
                                complete(SRec, crntPos);
                                printf("         REP (TENT): ");
                                addProductionToStateSet(crntPos, prod.items[0], 0, crntPos); // Tentative
                            } else if(!cannot_be){
                                printf("         REP: ");
                                addProductionToStateSet(crntPos, prod.items[0], 0, crntPos);
                            }
                        } else { // Not a pmREP
                            printf("         SEQ|ALT: ");
                            addProductionToStateSet(crntPos, prod.items[SRec.SeqPosition], 0, crntPos);
                        }
                    }
                }
            }
        }
    };
};


int main(int argc, char **argv){
 //   string inputFilename="toParse.txt";
 //   fstream fileIn("testInfon.pr");
 //   if (!fileIn.is_open()){cout<<"Could not open "<<inputFilename<<".\n"; exit(1);}
    testParser parser;
 //   parser.stream=&fileIn;
 //   streamSpan cursor;
 //   shared_ptr<infon> topInfon=make_shared<infon>();
    parser.populateGrammar();
    parser.initPosStateSets(toParse);
    parser.doParse();
    //topInfon->printToString();
    return 0;
}
