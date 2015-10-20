import re
import progSpec
import codeDogParser
from pyparsing import Word, alphas, nums, Literal, Keyword, Optional, OneOrMore, ZeroOrMore, delimitedList, Group, ParseException, quotedString, Forward, StringStart, StringEnd, SkipTo

#/////////////////////////////////////////////////  R o u t i n e s   t o   G e n e r a t e   P a r s e r s
parserString = ""

def parseParserSpec():
    ParseElement = Forward()
    fieldsName=Word(alphas+'_0123456789')
    FieldSpec = Group(fieldsName + Optional((Literal('.') | Literal('->')).suppress() + fieldsName))
    ValueSpec = FieldSpec | Word(nums) | (Keyword('true') | Keyword('false')) | quotedString
    WhitespaceEL = Keyword("WS")
    BaseEL = Group((WhitespaceEL| Keyword('STRING') | Keyword('CID') | Keyword('UNICODE_ID')
         | Keyword("DEC_NUM")  | Keyword("HEX_NUM")  | Keyword("BIN_NUM") ) + Optional(':'+fieldsName))
    SetFieldStmt = Group(FieldSpec + '=' + ValueSpec)
    PeekNotEL = "!" + quotedString
    LiteralEL = quotedString
    StructEL  = '#'+Word(alphas) + Optional(':' + fieldsName)
    ListEL = Group((Literal("+") | Literal("*")) + ParseElement)
    OptionEL = Group("<" + ParseElement + ">")
    CoFactualEL  = "(" + Group(ParseElement + "<=>" + Group(OneOrMore(SetFieldStmt + Literal(';').suppress())))  + ")"
    SequenceEL   = "{" + Word(alphas) + Group(OneOrMore(ParseElement)) + "}"
    AlternateEl  = "[" + Word(alphas) + Group(OneOrMore(ParseElement + Optional("|").suppress())) + "]"
    ParseElement <<= (Group(SequenceEL) | Group(AlternateEl) | Group(CoFactualEL) | ListEL | OptionEL | Group(StructEL) | LiteralEL | Group(PeekNotEL) | BaseEL)
    structParserSpec = Keyword("StructParser") + Word(alphas) + "=" + ParseElement
    #structParserSpec=structParserSpec.setDebug()
    StartSym = StringStart() + Literal("{").suppress() + OneOrMore(Group(structParserSpec)) +Literal("}").suppress()
    return StartSym

def getBaseTypeStr(typeSpec):
    if(isinstance(typeSpec, basestring)): return typeSpec
    return getBaseTypeStr(typeSpec[1])


tagModifier=1
def TraverseParseElement(objMap, structName, parseEL, BatchParser, PulseParser, PrintFunc, indent):
    # BatchParser[0] = text of parsing function being built.
    # BatchParser[1] = text of functions to add to the class.
    print "TraverseParseElement: ", structName
    global tagModifier
    indent2=indent+"    "
    batchArgs=["", ""]; pulseArgs=["", ""]; printerArgs=["", ""];
    #if it's a string can change to is instance progSpec.baseString()
    if(type(parseEL)==type("")):
        movTag=""
        #if(???) movTag=
        if(parseEL[0]=='"' or parseEL[0]=="'"):
            batchArgs[1] += "nxtTok(cursor, "+parseEL+")"
            printerArgs[1] ='S+='+parseEL+';'
        elif(parseEL=='WS'):
            batchArgs[1] += "RmvWSC(cursor)"
            printerArgs[1] ='S+=" ";\n'
        else:
            batchArgs[1] +=  "<-WTF" +parseEL+ ">"
    # check for 
    elif(parseEL[0]=='('):
        #print indent, "Co-Factual"
        actionStr=""; testStr="";
        #print "PREPING ACTION..."
        count=0
        for action in parseEL[1][2]:
            #print "ACTION:",action
            resultStrs=progSpec.getActionTestStrings(objMap, structName, action)
            #print resultStrs
            actionStr+=resultStrs[1]
            if(count>0): testStr+=" && "
            count+=1
            testStr+=resultStrs[2]

        Item = parseEL[1][0]
        #print "=========================>",Item
        batchArgs=["", ""]; pulseArgs=["", ""]; printerArgs=["", ""];
        TraverseParseElement(objMap, structName, Item, batchArgs, pulseArgs, printerArgs, indent2)
        batch0="    func var bool: parseCoFactual_"+str(tagModifier)+"(rPtr streamSpan:  cursor, rPtr "+structName+": ITEM)<%{\n"
        batch0+= "    "+"if(" + batchArgs[1] + ") {"+actionStr+"} else {MARK_ERROR; return false;}\n"
        batchArgs[0]+="\n"+batch0+"    }; %>\n"
        batchArgs[1]="parseCoFactual_"+str(tagModifier)+"(cursor, ITEM)"

        printerArgs[1]=indent+"if("+testStr+"){"+printerArgs[1]+"}\n"
        tagModifier+=1

    elif(parseEL[0]=='{'):
        #print indent, "Sequence"
        tagModifierS=parseEL[1]
        print1=""
        batch1=""
        batch0="";
        batch0+="    func var bool: parseSequence_"+tagModifierS+"(rPtr streamSpan:  cursor, rPtr "+structName+": ITEM ) <%{\n"
        for firstItem in parseEL[2]:
            batch0 += "    "+"if(!"
            batchArgs=["", ""]; pulseArgs=["", ""]; printerArgs=["", ""];
            TraverseParseElement(objMap, structName, firstItem, batchArgs, pulseArgs, printerArgs, indent2)
            batch1+=batchArgs[0]
            batch0+=batchArgs[1]
            batch0+=") {MARK_ERROR; return false;}\n"

            print1+=printerArgs[1]

        batch0+="    "+"return true;\n    }; %>\n\n\n"
        batchArgs[0]=batch1+"\n"+batch0
        batchArgs[1]="parseSequence_"+tagModifierS+"(cursor, ITEM)"
        printerArgs[1]=print1

    elif(parseEL[0]=='['):
        #print indent, "OneOf"
        tagModifierS=parseEL[1]
        print1=""
        batch1=""
        batch0="    func var bool: parseAltList_"+tagModifierS+"(rPtr streamSpan:  cursor, rPtr "+structName+": ITEM )<%{\n"
        for firstItem in parseEL[2]:
            batch0 += "    "+"if("
            batchArgs=["", ""]; pulseArgs=["", ""]; printerArgs=["", ""];
            TraverseParseElement(objMap, structName, firstItem, batchArgs, pulseArgs, printerArgs, indent2)
            batch1+=batchArgs[0]
            batch0+=batchArgs[1]
            batch0+=") {return true;}\n"

            print1+=printerArgs[1]
        batch0+="    "+"return false;\n    }; %>\n\n\n"
        batchArgs[0]=batch1+"\n"+batch0
        batchArgs[1]="parseAltList_"+tagModifierS+"(cursor, ITEM)"

        printerArgs[1]=print1

    elif(parseEL[0]=='<'):   # OPTIONAL
        batch1=""
        batch0="";
        batchArgs=["", ""]; pulseArgs=["", ""]; printerArgs=["", ""];
        #print "PARSEEL[1]:", parseEL[1]
        TraverseParseElement(objMap, structName, parseEL[1], batchArgs, pulseArgs, printerArgs, indent2)
        #print "     =", batchArgs
        batch1+=batchArgs[0]
        batch0+=batchArgs[1]
        batchArgs[1] = "(" + batch0 + "||true)"

    elif(parseEL[0]=='!'):   # NOT LITERAL
        batch1=""
        batch0="";
        batchArgs=["", ""]; pulseArgs=["", ""]; printerArgs=["", ""];
        TraverseParseElement(objMap, structName, parseEL[1], batchArgs, pulseArgs, printerArgs, indent2)
        batch1+=batchArgs[0]
        batch0+=batchArgs[1]
        batchArgs[1] = "!(" + batch0 + ")"
    elif(parseEL[0]=='#'):   # Sub-STRUCT
        FieldData=progSpec.getFieldInfo(objMap, structName, [parseEL[1]])
        sType=getBaseTypeStr(FieldData[2])
        printCmd=""
        print "#####################: ", FieldData[0]
        if(sType==""): sType=structName
        if(FieldData[0]=="var"):
            sField="&ITEM->"+parseEL[1]
        elif(FieldData[0]=="rPtr"):
            sField="ITEM->"+parseEL[1]
            printCmd="->printToString();\n"
        elif(FieldData[0]=="sPtr" or FieldData[0]=="uPtr"):
            sField="ITEM->"+parseEL[1]+".get()"
        elif(FieldData[0]=="list"):
			#TODO Handle List
			print "PARSE NEEDS CODED FOR LIST: ", parseEL[1]
			batch1=""
			print1=""
			batch0 = "func var bool: parse_Repetition_"+ str(tagModifier) + "(rPtr streamSpan: cursor, rPtr " + structName + ": ITEM )<%{\n"
			batch0 += "    " + 'bool notDone = '
			batchArgs = ["", ""]
			pulseArgs = ["", ""]
			printerArgs = ["", ""]
			TraverseParseElement(objMap, structName, parseEL[1], batchArgs, pulseArgs, printerArgs, indent2)
			batch1 += batchArgs[0]
			batch0 += batchArgs[1]
			batch0 += ';\n'+ "    " + 'while(notDone)\n'
			batch0 += "    " + "    " + '{notDone = '
			batch0 += batchArgs[1]
			batch0 +=  '}\n'
			batch0 += "    " + "return true;\n    }; %>\n\n\n"
			#print1 += printerArgs[1]
			
			batchArgs[0] = batch1 + '\n' + batch0
			sType = "Repetition_" + str(tagModifier) 
			#printerArgs[1]=print1
			sField = "ITEM->"+parseEL[1]
			tagModifier+=1
        else:
            sField = "ITEM->"+parseEL[1]
            printCmd=".printToString();\n"
        print "XXXXXXXXXX", sType, parseEL[1];
        batchArgs[1] = "parse_"+sType+"(cursor, "+sField+")"
        printerArgs[1] = "    " + "S += "+parseEL[1]+printCmd

    else:
        opAssignTag=''
        bufTypeTag=''
        if len(parseEL)>1: opAssignTag=parseEL[2]
        funcName="parseBuffer_"+parseEL[0]+str(tagModifier)
        batch0="    func var bool: "+funcName+"(rPtr streamSpan:  cursor, rPtr "+structName+": ITEM )<%{\n"
        tagModifier+=1
        if(parseEL[0]=='STRING'):
            bufTypeTag="ABC"

        elif(parseEL[0]=='CID'):
            bufTypeTag="cTok"

        elif(parseEL[0]=='UNICODE_ID'):
            bufTypeTag="unicodeTok"

        elif(parseEL[0]=='DEC_NUM'):
            bufTypeTag="123"

        elif(parseEL[0]=='HEX_NUM'):
            bufTypeTag="0x#"

        elif(parseEL[0]=='BIN_NUM'):
            bufTypeTag="0b#"

        elif(parseEL[0]=='WS'):
            batch0=""
            batchArgs[1] += "RmvWSC(cursor)"

        else:
            print "Unknown parse", "    ", parseEL
            exit(1)

        printerArgs[1] ='S+=" ";\n'
        if(parseEL[0] != 'WS'):
            batch0+='    if(!nxtTok(cursor, "'+bufTypeTag+'")) {return false;}\n    else {opAssign_'+opAssignTag+'(ITEM, buf);}\n'
            batch0+="    "+"return true;\n    };\n%>\n\n"
            batchArgs[0] = batch0
            batchArgs[1] = funcName+"(cursor, ITEM)"

    BatchParser[0]+=batchArgs[0]; BatchParser[1]+=batchArgs[1];
    PulseParser[0]+=pulseArgs[0]; PulseParser[1]+=pulseArgs[1];
    #PrintFunc[0]+=printerArgs[0]; PrintFunc[1]+=printerArgs[1];

def apply(objects, tags, parserSpecTag, startSymbol):
    parserSpec = tags[parserSpecTag]
    AST = parseParserSpec()
    print "PARSE.....PRINT.....PARSE.....PRINT....."
    try:
        print "Parsing Syntax Definition"
        results = AST.parseString(parserSpec, parseAll=True)
        print "Syntax Parsed"
    except ParseException, pe:
        print "ERROR Creating Grammar:", parserSpec, " ==> ", pe
        exit()
    else:
        print "SUCCESS Creating Grammar.\n"
        BatchParserUtils="" #// Batch Parsing utility parsing functions:
        PulseParserUtils=""
        BatchParser = "    func rPtr "+startSymbol + ": BatchParse( rPtr streamSpan: cursor, rPtr "+startSymbol + ": ITEM ) <%{\n    if(ITEM){reset_"+startSymbol+"_forParsing(ITEM);} else {ITEM=new "+startSymbol + "();}\n    return parse_"+startSymbol+"(cursor, ITEM);\n}; %>\n"
        PulseParser = "    func rPtr "+startSymbol + ": PulseParse"+startSymbol+"()<%{\n    if(ITEM){reset_"+startSymbol+"_forParsing(ITEM);} else {ITEM=new "+startSymbol + "();}\n    }; %>\n"

        for STRCT in results:
            objName=STRCT[1]
            print "struct ",objName,"="
            batchArgs=["",""]; PulseArgs=["",""]; printArgs=["",""];
            TraverseParseElement(objects[0], objName, STRCT[3], batchArgs, PulseArgs, printArgs, "        ")
            #progSpec.CreatePointerItems([structsSpec, structNames ], objName)

            BatchParserUtils+=batchArgs[0]
            BatchParser+="\n    func rPtr "+objName + ": parse_"+objName+"(rPtr streamSpan:  cursor, "+"rPtr "+objName+": ITEM ) <%{\n        if(ITEM){reset_"+objName+"_forParsing(ITEM);} else {ITEM=new "+objName+"();}\n        if("+batchArgs[1]+") return ITEM; else return 0;;\n    }; %>\n"
            BatchParser+="\n    func var void: reset_" + objName + "_forParsing(rPtr "+objName+": ITEM)<%{}; %>\n"

            PrinterFunc = '    func var string: printToString() <%{\n        string S="";\n' + printArgs[1] + "        return S;\n    };%>\n"
            PrinterFunc=progSpec.wrapFieldListInObjectDef(objName, PrinterFunc)
            # old code: progSpec.FillStructFromText([structsSpec, structNames ], objName, PrinterFunc)
            codeDogParser.AddToObjectFromText(objects[0], objects[1], PrinterFunc)


        BatchParserFuncs= BatchParserUtils + "\n\n" + BatchParser
        PulseParserFuncs= PulseParserUtils + "\n\n" + PulseParser


    CPP_GlobalText = r"""

const int bufmax = 32*1024;
#define streamEnd (stream->eof() || stream->fail())
#define ChkNEOF {if(streamEnd) {flags|=fileError; statusMesg="Unexpected End of file"; break;}}
#define getbuf(cursor, c) {ChkNEOF; buf=""; for(p=0;(c) && !streamEnd ; ++p){buf+=streamGet(cursor); if (p>=bufmax) {flags|=fileError; statusMesg="String unreasonably long"; break;}}}
#define nxtTok(cursor, tok) nxtTokN(cursor, 1,tok)

#define U8_IS_SINGLE(c) (((c)&0x80)==0)

UErrorCode err=U_ZERO_ERROR;
const UnicodeSet TagChars(UnicodeString("[[:XID_Continue:]']"), err);
const UnicodeSet TagStarts(UnicodeString("[:XID_Start:]"), err);
bool iscsymOrUni (char nTok) {return (iscsym(nTok) || (nTok&0x80));}
bool isTagStart(char nTok) {return (iscsymOrUni(nTok)&&!isdigit(nTok)&&(nTok!='_'));}
bool isAscStart(char nTok) {return (iscsym(nTok)&&!isdigit(nTok));}
bool isBinDigit(char ch) {return (ch=='0' || ch=='1');}
const icu::Normalizer2 *tagNormer=Normalizer2::getNFKCCasefoldInstance(err);
#define MARK_ERROR "ERROR"

bool tagIsBad(string tag, const char* locale) {
    UErrorCode err=U_ZERO_ERROR;
    if(!TagStarts.contains(tag.c_str()[0])) return 1; // First tag character is invalid
    if((size_t)TagChars.spanUTF8(tag.c_str(), -1, USET_SPAN_SIMPLE) != tag.length()) return 1;
    USpoofChecker *sc = uspoof_open(&err);
    uspoof_setChecks(sc, USPOOF_SINGLE_SCRIPT|USPOOF_INVISIBLE, &err);
    uspoof_setAllowedLocales(sc, locale, &err);
    int result=uspoof_checkUTF8(sc, tag.c_str(), -1, 0, &err);
    return (result!=0);
}

"""
    parserFields=r"""
        flag: fullyLoaded
        flag: userMode
        flag: parseError
        flag: fileError
        flag: isParsing
        var  string: statusMesg

        var char: nTok
        var string: buf

        rPtr istream: stream
        var string: streamName
        var string: streamPath
        var uint32: line
        var char: prevChar

        var string: textStreamed
        var posRecStore: textPositions
     //   var vector<int64_t> *punchInOut
        rPtr attrStore: attributes

        var infonPtr: ti

//        func var none: ~infonParser()<%{delete punchInOut;} %>

        func var char: streamGet(rPtr streamSpan: cursor)<%{
            switch(flags&(fullyLoaded|userMode)){
                case(userMode):  // !fully loaded | userMode
                    while(cursor->offset > textStreamed.size()){
                        textStreamed += stream->get();
                        if(stream->eof()){
                            flags|=fullyLoaded;
                        } else if(stream->fail()){
                            flags|=fileError;
                            return 0;
                        }
                    }
                    break;
                case(0): // !fullyLoaded | !userMode
                    stream->seekg(0, std::ios::end);
                    int streamSize=stream->tellg();
                    if(streamSize<=0) {printf("Problem with stream Stream size is %i.\n", streamSize); exit(1);}
                    textStreamed.resize(streamSize);
                    stream->seekg(0, std::ios::beg);
                    stream->read((char*)textStreamed.data(), textStreamed.size());
                    flags|=fullyLoaded;
                    break;
            }
            char ch = textStreamed[cursor->offset++];
            return ch;
        }  %>

        func var void: scanPast(rPtr streamSpan: cursor, rPtr char: str)<%{
            char p; char* ch=str;
            while(*ch!='\0'){
                p=streamGet(cursor);
                if (streamEnd){
                    if (strcmp(str,"<%")==0) return;
                    throw (string("Expected String not found before end-of-file: '")+string(str)+"'").c_str();
                }
                if (*ch==p) ch++; else ch=str;
                if (p=='\n') ++line;
            }
        } %>

        func var bool: chkStr(<% streamSpan* cursor, const char* tok %>) <%{
            int startPos=cursor->offset;
            if (tok==0) return 0;
            for(const char* p=tok; *p; p++) {
                if ((*p)==' ') RmvWSC(cursor);
                else if ((*p) != streamGet(cursor)){
                    cursor->offset=startPos;
                    return false;
                }
            }
            return true;
        } %>

        func var void: streamPut(rPtr streamSpan: cursor, var int32: nChars)<%{cursor->offset-=nChars; for(int n=nChars; n>0; --n){stream->putback(textStreamed[textStreamed.size()-1]); textStreamed.resize(textStreamed.size()-1);}} %>

        func <% const char* %> :nxtTokN(<% streamSpan* cursor, int n, ... %>) <%{
            char* tok; va_list ap; va_start(ap,n); int i,p;
            for(i=n; i; --i){
                tok=va_arg(ap, char*); nTok=WSPeek(cursor);
                if(strcmp(tok,"cTok")==0) {if(iscsym(nTok)&&!isdigit(nTok)&&(nTok!='_')) {getbuf(cursor, iscsym(pPeek(cursor))); break;} else tok=0;}
                else if(strcmp(tok,"unicodeTok")==0) {if(isTagStart(nTok)) {getbuf(cursor, iscsymOrUni(pPeek(cursor))); break;} else tok=0;}
                else if(strcmp(tok,"<abc>")==0) {if(chkStr(cursor, "<")) {getbuf(cursor, (pPeek(cursor)!='>')); chkStr(cursor, ">"); break;} else tok=0;}
                else if(strcmp(tok,"123")==0) {if(isdigit(nTok)) {getbuf(cursor, (isdigit(pPeek(cursor))||pPeek(cursor)=='.')); break;} else tok=0;}
                else if(strcmp(tok,"0x#")==0) {if(isxdigit(nTok)) {getbuf(cursor, (isxdigit(pPeek(cursor))||pPeek(cursor)=='.')); break;} else tok=0;}
                else if(strcmp(tok,"0b#")==0) {if(isBinDigit(nTok)) {getbuf(cursor, (isBinDigit(pPeek(cursor))||pPeek(cursor)=='.')); break;} else tok=0;}
                else if (chkStr(cursor, tok)) break; else tok=0;
            }
            va_end(ap);
            return tok;
        }%>


        func var char: pPeek(<% streamSpan* cursor %>) <%{
            while(textStreamed.length() < cursor->offset){
                if(flags&fullyLoaded){return 0;}
                char ch=stream->get();
                if(stream->eof()){}
                if(stream->fail()){}
                textStreamed + ch;
            }
            return(textStreamed[cursor->offset]);
        } %>

        func var char: WSPeek(<% streamSpan* cursor %>)<%{RmvWSC(cursor); return pPeek(cursor);} %>

        func var bool: RmvWSC(<% streamSpan* cursor %>)<%{ //, attrStorePtr attrs=0){
            char p,p2;
            for (p=pPeek(cursor); (p==' '||p=='/'||p=='\n'||p=='\r'||p=='\t'||p=='%'); p=pPeek(cursor)){
                if (p=='/') {
                    streamGet(cursor); p2=pPeek(cursor);
                    if (p2=='/') {
        //              punchInOut->push_back(textStreamed.size()-1);  // Record start of line comment.
                        string comment="";
                        for (p=pPeek(cursor); !streamEnd && p!='\n'; p=pPeek(cursor)) comment+=streamGet(cursor);
        //                punchInOut->push_back(-textStreamed.size());  // Record end of line comment.
                    /*    if (attrs){
                            if     (comment.substr(1,7)=="author=") attrs->a.insert(pair<string,string>("author",comment.substr(8)));
                            else if(comment.substr(1,6)=="image=") attrs->a.insert(pair<string,string>("image",comment.substr(7)));
                            else if(comment.substr(1,9)=="engTitle=") attrs->a.insert(pair<string,string>("engTitle",comment.substr(10)));
                            else if(comment.substr(1,7)=="import=") attrs->a.insert(pair<string,string>("import",comment.substr(8)));
                            else if(comment.substr(1,8)=="summary=") attrs->a.insert(pair<string,string>("summary",comment.substr(9)));
                            else if(comment.substr(1,5)=="link=") attrs->a.insert(pair<string,string>("link",comment.substr(6)));
                            else if(comment.substr(1,9)=="category=") attrs->a.insert(pair<string,string>("category",comment.substr(10)));
                            else if(comment.substr(1,7)=="posted=") attrs->a.insert(pair<string,string>("posted",comment.substr(8)));
                            else if(comment.substr(1,8)=="updated=") attrs->a.insert(pair<string,string>("updated",comment.substr(9)));
                        } */
                    } else if (p2=='*') {
         //               punchInOut->push_back(textStreamed.size()-1);  // Record start of block comment.
                        for (p=streamGet(cursor); !streamEnd && !(p=='*' && pPeek(cursor)=='/'); p=streamGet(cursor))
                            if (p=='\n') ++line;
                        if (streamEnd) throw "'/*' Block comment never terminated";
                        streamGet(cursor);
         //               punchInOut->push_back(-(textStreamed.size()));  // Record end of block comment.
                    } else {streamPut(cursor, 1); return true;}
                } else if (p=='%'){
                    streamGet(cursor); p2=pPeek(cursor);
                    if(p2=='>'){scanPast(cursor, (char*)"<%");} else {streamPut(cursor, 1); return true;}
                }
                if (streamGet(cursor)=='\n') {++line; prevChar='\n';} else prevChar='\0';
            }
            return true;
        }   %>


        func var bool: doRule(<%infon* i%>) <%{
            uint64_t parsePhase = flags&InfParsePhaseMask;
            if(parsePhase==iStartParse){
          //      if(nxtTok(i->curPos, "@")){i->flags |= asDesc;}
           //     if(nxtTok(i->curPos, "`")){i->flags |= toExec;}
            } else if(parsePhase==iParseIdents){
            } else if(parsePhase==iParseFuncArgs){
            }
            return 1;
        } %>

    """

    progSpec.setCodeHeader('cpp', CPP_GlobalText)
    parserStructsName = startSymbol+"Parser"
    progSpec.addObject(objects[0], objects[1], parserStructsName)
    codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef(parserStructsName, BatchParserFuncs))
    codeDogParser.AddToObjectFromText(objects[0], objects[1], progSpec.wrapFieldListInObjectDef(parserStructsName, parserFields))
