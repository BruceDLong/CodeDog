# CodeDog Program Maker
# This file is code to convert "string" style structures into 'struct' style structures.

import re
import progSpec
import codeDogParser
from progSpec import cdlog, cdErr

def codeDogTypeToString(classes, tags, field):
    #print "FIELD:", field
    S=''
    fieldName=field['fieldName']
    fieldType=progSpec.getFieldType(field)
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
        #print 'const ', fieldType, ': ', fieldName, ' <- ',fieldValue
        #S+='const '+fieldType+': ' + fieldName + ' <- '+fieldValue+'\n'
        pass
    elif fieldOwner=='const':
        print("Finish This")

    return S

rules=[]
constDefs=[]
ruleSet={}      # Used to track duplicates
globalFieldCount=0
globalTempVarIdx=0

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
        ConstList+='    const int: ' + C[0].replace('::','_') + ' <- ' + str(C[1]) + '\n'

    code= r"""
struct EParser{
#CONST_CODE_HERE

    void: populateGrammar() <- {
        setQuickParse(false)
        clearGrammar()
#GRAMMAR_CODE_HERE
        preCalcNullability()
        preCalcStreamPoints()
    }
}
    """
    code=code.replace('#CONST_CODE_HERE', ConstList, 1)
    code=code.replace('#GRAMMAR_CODE_HERE', RuleList, 1)
    return code

def writePositionalFetch(classes, tags, field):
    fname=field['fieldName']
    fieldType=str(progSpec.getFieldType(field))
    S="""
    me fetchResult: fetch_%s() <- {
        if(%s_hasVal) {return (fetchOK)}
        }
"""% (fname, fname)
    return S




    #print 'FIELD:', fname, field['owner'], '"'+fieldType+'"'
    if(field['owner']=='const' and fieldType=='string'):
        S+='    %s_hasLen <- true \n    %s_span.len <- '% (fname, fname) + str(len(field['value']))
    S+="        if(! %s_hasPos){pos <- pred.pos+pred.len}\n" % (fname)
    S+="        if( %s_hasPos){\n" % (fname)
    # Scoop Data
    S+=' FieldTYpe("' + fieldType +'")\n'
    if progSpec.isStruct(fieldType):
        #print " Call stuct's fetch()"
        pass
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
        if not isinstance(ruleName, str):
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
    appendRule('alphaSeq',    'term', 'parseAUTO', "an alphabetic string")
    appendRule('uintSeq',     'term', 'parseAUTO', 'an unsigned integer')
    appendRule('intSeq',      'term', 'parseAUTO', 'an integer')
    appendRule('RdxSeq',      'term', 'parseAUTO', 'a number')
    appendRule('alphaNumSeq', 'term', 'parseAUTO', "an alpha-numeric string")
    appendRule('ws',          'term', 'parseAUTO', 'white space')
    appendRule('wsc',         'term', 'parseAUTO', 'white space or C comment')
    appendRule('quotedStr',   'term', 'parseAUTO', "a quoted string with single or double quotes and escapes")
    appendRule('quotedStr1',  'term', 'parseAUTO', "a single quoted string with escapes")
    appendRule('quotedStr2',  'term', 'parseAUTO', "a double quoted string with escapes")
    appendRule('HexNum_str',  'term', 'parseAUTO', "a hexadecimal number")
    appendRule('BinNum_str',  'term', 'parseAUTO', "a binary number")
    appendRule('BigInt',      'term', 'parseAUTO', "an integer")
    appendRule('FlexNum',     'term', 'parseAUTO', "a rational number")
    appendRule('CID',         'term', 'parseAUTO', 'a C-like identifier')
    appendRule('UniID',       'term', 'parseAUTO', 'a unicode identifier for the current locale')
    appendRule('printables',  'term', 'parseAUTO', "a seqence of printable chars")
    appendRule('toEOL',       'term', 'parseAUTO', "read to End Of Line, including EOL.")
    # TODO: delimited List, keyWord



nextParseNameID=0 # Global used to uniquify sub-seqs and sub-alts in a struct parse. E.g.: ruleName: parse_myStruct_sub1
def fetchOrWriteTerminalParseRule(modelName, field, logLvl):
    global nextParseNameID
    #print "FIELD_IN:", modelName, field
    fieldName='N/A'
    fieldValue=''
    if 'value' in field: fieldValue =field['value']
    typeSpec   = field['typeSpec']
    fieldType  = progSpec.getFieldType(typeSpec)
    fieldOwner = typeSpec['owner']
    if 'fieldName' in field: fieldName  =field['fieldName']
    cdlog(logLvl, "WRITING PARSE RULE for: {}.{}".format(modelName, fieldName))
    #print "WRITE PARSE RULE:", modelName, fieldName

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
            print("Unusable const type in fetchOrWriteTerminalParseRule():", fieldType); exit(2);

    elif fieldOwner=='me' or  fieldOwner=='their' or  fieldOwner=='our':
        if fieldType=='string':        nameOut='quotedStr'
        elif fieldType[0:4]=='uint':   nameOut='uintSeq'
        elif fieldType[0:3]=='int':    nameOut='intSeq'
        elif fieldType[0:6]=='double': nameOut='RdxSeq'
        elif fieldType[0:4]=='char':   nameOut=appendRule(nameIn,       "term", "parseSEQ",  None)
        elif fieldType[0:4]=='bool':   nameOut=appendRule(nameIn,       "term", "parseSEQ",  None)
        elif progSpec.isStruct(fieldType):
            objName=fieldType[0]
            if (objName=='ws' or objName=='wsc' or objName=='quotedStr' or objName=='quotedStr1' or objName=='quotedStr2'
                  or objName=='CID' or objName=='UniID' or objName=='printables' or objName=='toEOL' or objName=='alphaNumSeq'
                  or progSpec.typeIsInteger(objName)):
                nameOut=objName
            else:
                if objName=='[' or objName=='{': # This is an ALT or SEQ sub structure
                    print("ERROR: These should be handled in writeNonTermParseRule().\n")
                    exit(1)
                else: nameOut=objName+'_str'
        elif progSpec.isAlt(fieldType):
            pass
        elif progSpec.isCofactual(fieldType):
            pass
        else:
            print("Unusable type in fetchOrWriteTerminalParseRule():", fieldType); exit(2);
    else: print("Pointer types not yet handled in fetchOrWriteTerminalParseRule():", fieldType); exit(2);

    if progSpec.isAContainer(typeSpec):
        global rules
        containerTypeSpec = progSpec.getContainerSpec(typeSpec)
        idxType=''
        if 'indexType' in containerTypeSpec:
            idxType=containerTypeSpec['indexType']
        if(isinstance(containerTypeSpec['datastructID'], str)):
            datastructID = containerTypeSpec['datastructID']
        else:   # it's a parseResult
            datastructID = containerTypeSpec['datastructID'][0]
        if idxType[0:4]=='uint': pass
        if(datastructID=='list'):
            nameOut=appendRule(nameOut+'_REP', "nonterm", "parseREP", [nameOut, 0, 0])
        elif datastructID=='opt':
            nameOut=appendRule(nameOut+'_OPT', "nonterm", "parseREP", [nameOut, 0, 1])
            #print("NAMEOUT:", nameOut)
    field['parseRule']=nameOut
    return nameOut

def writeNonTermParseRule(classes, tags, modelName, fields, SeqOrAlt, nameSuffix, logLvl):
    global nextParseNameID
    nameIn=modelName+nameSuffix

    # Allocate or fetch a rule identifier for each '>' field.

    partIndexes=[]
    for field in fields:
        fname=field['fieldName']
        if fname==None: fname=''
        else: fname='_'+fname
        typeSpec   =field['typeSpec']
        if(field['isNext']==True): # means in the parse there was a '>' symbol, a sequence seperator
            firstItm=progSpec.getFieldType(field['typeSpec'])[0]
            if firstItm=='[' or firstItm=='{': # Handle an ALT or SEQ sub structure
                cdlog(logLvl, "NonTERM: {} = {}".format(fname, firstItm))
                nextParseNameID+=1
                if firstItm=='[':
                    innerSeqOrAlt='parseALT'
                    newNameSuffix = nameSuffix+fname+'_ALT'+str(nextParseNameID)
                else:
                    innerSeqOrAlt='parseSEQ'
                    newNameSuffix = nameSuffix+fname+'_SEQ'+str(nextParseNameID)
                innerFields=field['innerDefs']
                ruleIdxStr = writeNonTermParseRule(classes, tags, modelName, innerFields, innerSeqOrAlt, newNameSuffix, logLvl+1)
                field['parseRule']=ruleIdxStr


                if progSpec.isAContainer(typeSpec):
                    # anything with [] is a container: lists and optionals
                    global rules
                    containerTypeSpec = progSpec.getContainerSpec(typeSpec)
                    idxType=''
                    if 'indexType' in containerTypeSpec:
                        idxType=containerTypeSpec['indexType']
                    if(isinstance(containerTypeSpec['datastructID'], str)):
                        datastructID = containerTypeSpec['datastructID']
                    else:   # it's a parseResult
                        datastructID = containerTypeSpec['datastructID'][0]
                    if idxType[0:4]=='uint': pass
                    if(datastructID=='list'):
                        ruleIdxStr=appendRule(ruleIdxStr+'_REP', "nonterm", "parseREP", [ruleIdxStr, 0, 0])
                    elif datastructID=='opt':
                        ruleIdxStr=appendRule(ruleIdxStr+'_OPT', "nonterm", "parseREP", [ruleIdxStr, 0, 1])
            else:
                ruleIdxStr = fetchOrWriteTerminalParseRule(modelName, field, logLvl)

            partIndexes.append(ruleIdxStr)
        else: pass; # These fields probably have corresponding cofactuals

    nameOut=appendRule(nameIn, "nonterm", SeqOrAlt, partIndexes)
    return nameOut

#######################################################   E x t r a c t i o n   F u n c t i o n s

def getFunctionName(fromName, toName):
    if len(fromName)>=5 and fromName[-5:-3]=='::': fromName=fromName[:-5]
    if len(toName)>=5 and toName[-5:-3]=='::': toName=toName[:-5]
    S='Extract_'+fromName.replace('::', '_')+'_to_'+toName.replace('::', '_')
    return S

def fetchMemVersion(classes, objName):
    if objName=='[' or objName=='{': return [None, None]
    memObj = progSpec.findSpecOf(classes[0], objName, 'struct')
    if memObj==None: return [None, None]
    return [memObj, objName]


def Write_ALT_Extracter(classes, parentStructName, fields, VarTagBase, VarTagSuffix, VarName, indent, level, logLvl):
    # Structname should be the name of the structure being parsed. It will be converted to the mem version to get 'to' fields.
    # Fields is the list of alternates.
    # VarTag is a string used to create local variables.
    # VarName is the LVAL variable name.
    global  globalFieldCount
    cdlog(logLvl, "WRITING code to extract one of {} from parse tree...".format(parentStructName))
    InnerMemObjFields = []
    progSpec.populateCallableStructFields(InnerMemObjFields, classes, parentStructName)
    if parentStructName.find('::') != -1: cdErr("TODO: Make string parsing work on derived classes. Probably just select the correct fields for the destination struct.")
    S=""
    # Code to fetch the ruleIDX of this ALT. If the parse was terminal (i.e., 'const'), it will be at a different place.
    if(level==-1):
        level=1
        VarTag='SRec1'
        VarTagSuffix='0'
        RHS = VarTagBase+VarTagSuffix
    else:
        globalFieldCount+=1
        VarTag=VarTagBase+str(level)
        RHS= 'getChildStateRec('+ VarTagBase + str(level-1)+')'+VarTagSuffix

    indent2 = indent+'    '
    S+='\n'+indent+'{\n'
    S+='\n'+indent2+'our stateRec: '+VarTag+' <- '+RHS+'\n'   #   shared_ptr<stateRec > SRec1 = SRec0->child;
    loopVarName = "ruleIDX"+str(globalFieldCount)
    S+=indent2+'me int: '+loopVarName+' <- getChildStateRec('+VarTag+').productionID\n'

    #print "RULEIDX:", indent, parentStructName, VarName
    if VarName!='memStruct':
        S+=indent2 + 'me string: '+VarName+'\n'
    count=0
    S+= indent2+"switch("+loopVarName+"){\n"
    for altField in fields:
        if(altField['isNext']!=True): continue; # This field isn't in the parse stream.
        cdlog(logLvl+1, "ALT: {}".format(altField['parseRule']))
        if not 'parseRule' in altField: print("Error: Is syntax missing a '>'?"); exit(2);
        S+=indent2+"    case " + altField['parseRule'] + ":{\n"
        coFactualCode=''
        if 'coFactuals' in altField:
            #Extract field and cofactsList
            for coFact in altField['coFactuals']:
                coFactualCode+= indent2 +'        ' + VarName + '.' + coFact[0] + ' <- ' + coFact[2] + "\n"
                cdlog(logLvl+2, "Cofactual: "+coFactualCode)
        S+=coFactualCode
        S+=Write_fieldExtracter(classes, parentStructName, altField, InnerMemObjFields, VarTagBase, VarName, False, coFactualCode, indent2+'        ', level, logLvl+1)
        S+=indent2+"    }\n"
        count+=1
    S+=indent2+"}"
    S+=indent+"}"
    return S


def CodeRValExpr(toFieldType, VarTag, suffix):
    if   toFieldType=='string':          CODE_RVAL='makeStr('+VarTag+'.child.next'+suffix+')'+"\n"
    elif toFieldType[0:4]=='uint':       CODE_RVAL='makeInt('+VarTag+'.child.next'+suffix+')'+"\n"
    elif toFieldType[0:3]=='int':        CODE_RVAL='makeInt('+VarTag+'.child.next'+suffix+')'+"\n"
    elif toFieldType[0:6]=='double':     CODE_RVAL='makeDblFromStr('+VarTag+'.child.next'+suffix+')'+"\n"
    elif toFieldType[0:4]=='char':       CODE_RVAL="crntStr[0]"+"\n"
    elif toFieldType[0:4]=='bool':       CODE_RVAL='crntStr=="true"'+"\n"
    elif toFieldType[0:4]=='flag':       CODE_RVAL=''
    else: print("TOFIELDTYPE:", toFieldType); exit(2);
    return CODE_RVAL


def Write_fieldExtracter(classes, ToStructName, field, memObjFields, VarTagBase, VarName, advancePtr, coFactualCode, indent, level, logLvl):
    debugTmp=False # Erase this line
    VarTag=VarTagBase+str(level)
    ###################   G a t h e r   N e e d e d   I n f o r m a t i o n
    global  globalFieldCount
    global  globalTempVarIdx
    S=''
    fieldName  = field['fieldName']
    fieldIsNext= field['isNext']
    fieldValue = field['value']
    typeSpec   = field['typeSpec']
    fieldType  = progSpec.getFieldType(typeSpec)
    fieldOwner =typeSpec['owner']
    fromIsEmbeddedAlt = (not isinstance(fieldType, str) and fieldType[0]=='[')
    fromIsEmbeddedSeq = (not isinstance(fieldType, str) and fieldType[0]=='{')
    fromIsEmbedded    = fromIsEmbeddedAlt or fromIsEmbeddedSeq

    if(fieldIsNext!=True): return '' # This field isn't in the parse stream.

    [memObj, memVersionName]=fetchMemVersion(classes, ToStructName)

    toField = progSpec.fetchFieldByName(memObjFields, fieldName)
    if(toField==None):
        #print "   TOFIELD == None", fieldName
        # Even tho there is no LVAL, we need to move the cursor. Also, there could be a co-factual.
        toFieldType = progSpec.TypeSpecsMinimumBaseType(classes, typeSpec)
        toTypeSpec=typeSpec
        toFieldOwner="me"
    else:
        toTypeSpec   = toField['typeSpec']
        toFieldType  = progSpec.getFieldType(toTypeSpec)
        toFieldOwner = progSpec.getContainerFirstElementOwner(toTypeSpec)

        if debugTmp:
            print('        toFieldType:', toFieldType)

    LHS_IsPointer=progSpec.typeIsPointer(toTypeSpec)

   # print "        CONVERTING:", fieldName, str(toFieldType)[:100]+'... ', str(typeSpec)[:100]+'... '
   # print "            TOFieldTYPE1:", str(toField)[:100]
   # print "            TOFieldTYPE :", toFieldOwner, toFieldType
   # print "       fieldValue:",ToStructName, fieldType, fieldValue
    cdlog(logLvl, "FIELD {}: '{}'".format(fieldName, str(fieldValue)))

    fields=[]
    fromIsStruct=progSpec.isStruct(fieldType)
    toIsStruct=progSpec.isStruct(toFieldType)
    ToIsEmbedded = toIsStruct and (toFieldType[0]=='[' or toFieldType[0]=='{')
    [fromIsALT, fields] = progSpec.isAltStruct(classes, fieldType)
    fromIsOPT =False
    fromIsList=False
    toIsList  =False
    optionalWhiteSpace =False
    if progSpec.isAContainer(typeSpec):
        datastructID = progSpec.getDatastructID(typeSpec)
        if datastructID=='opt': fromIsOPT=True;
        else: fromIsList=True

    if progSpec.isAContainer(toTypeSpec):
        if datastructID != 'opt': toIsList=True

    if debugTmp:
        print('        fromIsOPT:', fromIsOPT)
        print('        fromIsList:', fromIsList)
        print('        toIsList:', toIsList)
        print('        fromIsStruct:', fromIsStruct)
        print('        toIsStruct:', toIsStruct)
        print('        fieldType:', fieldType)
        print('        ToIsEmbedded:', ToIsEmbedded)
        print('        ToStructName:', ToStructName)
        print('        memVersionName:', memVersionName, "\n")
    ###################   W r i t e   L V A L   R e f e r e n c e
    finalCodeStr=''
    CodeLVAR_Alloc=''
    CODE_LVAR_v2=''
    if VarName=='' or VarName=='memStruct':  # Default to the target argument name
        #if VarName=='': print "        VARNAME was ''; FIELDNAME:", fieldName
        VarName='memStruct'
        if(fieldName==None): # Field hasn't a name so in memory it's a cofactual or this is a parser marker.
            globalFieldCount+=1
            # We need two versions in case this is set in a function instead of assignment
            CODE_LVAR_v2 = 'S'+str(globalFieldCount)
            CodeLVAR_Alloc='    me string: '+CODE_LVAR_v2
            CODE_LVAR = CodeLVAR_Alloc
            if debugTmp: print('        CODE_LVARS:', CODE_LVAR)
        else:
            CODE_LVAR = VarName+'.'+fieldName
            if fieldName=='inf': CODE_LVAR = VarName
            CODE_LVAR_v2 = CODE_LVAR
    else:
        CODE_LVAR = VarName
        CODE_LVAR_v2 = CODE_LVAR

    ###################   W r i t e   R V A L   C o d e
    CODE_RVAL=''
    objName=''
    humanIDType= VarTag+' ('+str(fieldName)+' / '+str(fieldValue) + ' / '+str(fieldType)[:40] +')'
    humanIDType=humanIDType.replace('"', "'")
    #print humanIDType

    if advancePtr:
        S+=indent+VarTag+' <- getNextStateRec('+VarTag+')\n'
        # UNCOMMENT FOR DEGUG: S+='    docPos('+str(level)+', '+VarTag+', "Get Next in SEQ for: '+humanIDType+'")\n'


    if fieldOwner=='const'and (toField == None):
        #print'CONSTFIELDVALUE("'+fieldValue+'")\n'
        finalCodeStr += indent + 'tmpStr'+' <- makeStr('+VarTag+"<LVL_SUFFIX>"+'.child)\n'

    else:
        if toIsStruct:
            if debugTmp: print('        toFieldType:', toFieldType)
            if not ToIsEmbedded:
                objName=toFieldType[0]
                if  progSpec.typeIsInteger(objName):
                    strFieldType = fieldType[0]
                    if(strFieldType == "HexNum"):
                        CODE_RVAL='makeHexInt('+VarTag+'.child.next'+')'
                    elif(strFieldType == "BinNum"):
                        CODE_RVAL='makeBinInt('+VarTag+'.child.next'+')'
                    else:
                        CODE_RVAL='makeStr('+VarTag+'.child.next'+')'
                    toIsStruct=False; # false because it is really a base type.
                elif (objName=='quotedStr1' or objName=='quotedStr2' or objName=='CID' or objName=='UniID'
                      or objName=='printables' or objName=='toEOL' or objName=='alphaNumSeq'):
                    CODE_RVAL='makeStr('+VarTag+'.child.next'+')'
                    toIsStruct=False; # false because it is really a base type.
                elif (objName=='ws' or objName=='wsc'):
                    CODE_RVAL='makeStr('+VarTag+'.child.next'+')'
                    optionalWhiteSpace = True
                    toIsStruct=False; # false because it is really a base type.
                else:
                    #print "toObjName:", objName, memVersionName, fieldName
                    [toMemObj, toMemVersionName]=fetchMemVersion(classes, objName)
                    if toMemVersionName==None:
                        # make alternate finalCodeStr. Also, write the extractor that extracts toStruct fields to memVersion of this
                        finalCodeStr=(indent + CodeLVAR_Alloc + '\n' +indent+'    '+getFunctionName(fieldType[0], memVersionName)+'(getChildStateRec('+VarTag+"<LVL_SUFFIX>"+'), memStruct)\n')
                        objSpec = progSpec.findSpecOf(classes[0], objName, 'string')
                        ToFields=objSpec['fields']
                        FromStructName=objName
                        Write_Extracter(classes, ToStructName, FromStructName, logLvl+1)
                    else:
                        fromFieldTypeCID = fieldType[0].replace('::', '_')
                        toFieldTypeCID = toMemVersionName.replace('::', '_')
                        #print "FUNC:", getFunctionName(fromFieldTypeCID, toFieldTypeCID)
                        if fromFieldTypeCID != toFieldTypeCID:
                            Write_Extracter(classes, toFieldTypeCID, fromFieldTypeCID, logLvl+1)
                        finalCodeStr=indent + CodeLVAR_Alloc + '\n' +indent+'    '+getFunctionName(fromFieldTypeCID, toFieldTypeCID)+'(getChildStateRec('+VarTag+"<LVL_SUFFIX>"+'), '+CODE_LVAR_v2+')\n'
            else: pass

        else:
            CODE_RVAL = CodeRValExpr(toFieldType, VarTag, "")


    #print "CODE_RVAL:", CODE_RVAL

    ###################   H a n d l e   o p t i o n a l   a n d   r e p e t i t i o n   a n d   a s s i g n m e n t   c a s e s
    gatherFieldCode=''
    if fromIsList and toIsList:
        CODE_RVAL='tmpVar'
        globalFieldCount +=1
        childRecName='SRec' + str(globalFieldCount)
        gatherFieldCode+='\n'+indent+'\nour stateRec: '+childRecName+' <- '+VarTag+'.child'
        gatherFieldCode+='\n'+indent+'while('+childRecName+' != NULL and getNextStateRec('+childRecName+') !=NULL){\n'
        if fromIsALT:
          #  print "ALT-#1"
            gatherFieldCode+=Write_ALT_Extracter(classes, fieldType[0], fields, childRecName, '', 'tmpVar', indent+'    ', level)
            gatherFieldCode+='\n'+indent+CODE_LVAR+'.pushLast('+CODE_RVAL+')'

        elif fromIsStruct and toIsStruct:
            gatherFieldCode+='\n'+indent+toFieldOwner+' '+progSpec.baseStructName(toFieldType[0])+': tmpVar'
            if toFieldOwner!='me':
                gatherFieldCode+='\n'+indent+'Allocate('+CODE_RVAL+')'
            gatherFieldCode+='\n'+indent+CODE_LVAR+'.pushLast('+CODE_RVAL+')'
            #print "##### FUNCT:", getFunctionName(fieldType[0], fieldType[0])
            gatherFieldCode+='\n'+indent+getFunctionName(fieldType[0], toFieldType[0])+'(getChildStateRec('+childRecName+') , tmpVar)\n'

        else:
            CODE_RVAL = CodeRValExpr(toFieldType, childRecName, ".next")
            gatherFieldCode+='\n'+indent+CODE_LVAR+'.pushLast('+CODE_RVAL+')'

        #gatherFieldCode+='\n'+indent+CODE_LVAR+'.pushLast('+CODE_RVAL+')'

        gatherFieldCode+=indent+'    '+childRecName+' <- getNextStateRec('+childRecName+')\n'
        # UNCOMMENT FOR DEGUG: S+= '    docPos('+str(level)+', '+VarTag+', "Get Next in LIST for: '+humanIDType+'")\n'


        gatherFieldCode+='\n'+indent+'}\n'
        if(fromIsOPT):
            print("Handle when the optional item is a list.");
            exit(2)
    else:
        if toIsList: print("Error: parsing a non-list to a list is not supported.\n"); exit(1);
        levelSuffix=''
        assignerCode=''
        oldIndent=indent
        if (fromIsOPT):
            setTrueCode=''
            assignerCode+='\n'+indent+'if('+VarTag+'.child' +' == NULL or '+VarTag+'.child.next' +' == NULL){'
            if toFieldOwner=='me':
                if debugTmp: print('        toFieldOwner:', toFieldOwner)
                ## if fieldName==None and a model of fromFieldType has no cooresponding model But we are in EXTRACT_ mode:
                        ## Make a special form of Extract_fromFieldType_to_ToFieldType()
                        ## Call that function instead of the one in Code_LVAR
                # First, create a new flag field
                if fieldName==None:
                    fieldName="TEMP"+str(globalTempVarIdx)
                    globalTempVarIdx += globalTempVarIdx
                newFieldsName=fieldName   #'has_'+fieldName
                fieldDef=progSpec.packField(ToStructName, False, 'me', 'flag', None, None, newFieldsName, None, None, None, False, False)
                progSpec.addField(classes[0], memVersionName, 'struct', fieldDef)

                # Second, generate the code to set the flag
                assignerCode+='\n'+indent+'    '+VarName+'.'+newFieldsName+' <- false'
                setTrueCode += VarName+'.'+newFieldsName+' <- true'
            elif LHS_IsPointer: # If owner is my, our or their
                assignerCode+='\n'+indent+'    '+CODE_LVAR+' <- NULL'
            else:
                print("ERROR: OPTional fields must not be '"+toFieldOwner+"'.\n")
                exit(1)
            assignerCode+='\n'+indent+'} else {\n'
            levelSuffix='.child'
            indent+='    '
            assignerCode+=indent+setTrueCode+'\n'


        if fromIsALT or fromIsEmbeddedAlt:
            if(fromIsEmbeddedAlt):
               # print "ALT-#2"
                assignerCode+=Write_ALT_Extracter(classes, ToStructName, field['innerDefs'], VarTagBase, levelSuffix, VarName, indent+'    ', level+1, logLvl+1)
            else:
              #  print "ALT-#3"
                assignerCode+=Write_ALT_Extracter(classes, fieldType[0], fields, VarTagBase, levelSuffix, VarName+'X', indent+'    ', level, logLvl+1)
                assignerCode+=indent+CODE_LVAR+' <- '+(VarName+'X')+"\n"
        elif fromIsEmbeddedSeq:
            globalFieldCount +=1
            childRecNameBase='childSRec' + str(globalFieldCount)
            childRecName=childRecNameBase+str(level)
            assignerCode+='\n'+indent+'our stateRec: '+childRecName+' <- '+VarTag+levelSuffix+'.child\n'
            advance=False
            for innerField in field['innerDefs']:
                assignerCode+=Write_fieldExtracter(classes, ToStructName, innerField, memObjFields, childRecNameBase, '', advance, coFactualCode, '    ', level, logLvl+1)
                advance = True
        elif fromIsStruct and toIsStruct:
            assignerCode+=finalCodeStr.replace("<LVL_SUFFIX>", levelSuffix);
            if debugTmp: print('        assignerCode:', assignerCode)
        elif optionalWhiteSpace:
            assignerCode += '\n'+indent+'if('+VarTag+'.child' +' != NULL){'+CODE_LVAR+' <- '+CODE_RVAL+'}\n'
        else:
           # if toFieldOwner == 'const': print "Error: Attempt to extract a parse to const field.\n"; exit(1);
            if CODE_RVAL!="":
                if LHS_IsPointer:
                    assignerCode+='        '+CODE_LVAR+' <deep- '+CODE_RVAL+"\n"
                else: assignerCode+='        '+CODE_LVAR+' <- '+CODE_RVAL+"\n"
            elif finalCodeStr!="": assignerCode+=finalCodeStr.replace("<LVL_SUFFIX>", levelSuffix);

        if (fromIsOPT):
            indent=oldIndent
            assignerCode += indent+'}\n'
            #print '######################\n'+assignerCode, memVersionName, '\n'
           # exit(2)
        gatherFieldCode = assignerCode
    #print ("##########################\n",S,"\n#####################################\n")
    if LHS_IsPointer: # LVAL is a pointer and should be allocated or cleared.
        S+= indent + 'AllocateOrClear(' +CODE_LVAR +')\n'
        S+=coFactualCode
    S+=gatherFieldCode
    #print "ASSIGN_CODE", S
 #   if debugTmp: exit(2)
    return S

extracterFunctionAccumulator = ""
alreadyWrittenFunctions={}

def Write_structExtracter(classes, ToStructName, FromStructName, fields, nameForFunc, logLvl):
    memObjFields=[]
    progSpec.populateCallableStructFields(memObjFields, classes, ToStructName)
    if memObjFields==None: cdErr("struct {} is not defined".format(ToStructName.replace('str','mem')))
    S='        me string: tmpStr;\n'
    advance=False
    for field in fields: # Extract all the fields in the string version.
        S+=Write_fieldExtracter(classes, ToStructName, field, memObjFields, 'SRec', '', advance, '', '    ', 0, logLvl+1)
        advance=True
    if  ToStructName== FromStructName and progSpec.doesClassContainFunc(classes, ToStructName, 'postParseProcessing'):
        S += '        memStruct.postParseProcessing()\n'
    return S

def Write_Extracter(classes, ToStructName, FromStructName, logLvl):
    global extracterFunctionAccumulator
    global alreadyWrittenFunctions
    nameForFunc=getFunctionName(FromStructName, ToStructName)
    cdlog(logLvl, "WRITING function {}() to extract struct {} from parse tree: stage 1...".format(nameForFunc, ToStructName))
    if nameForFunc in alreadyWrittenFunctions: return
    alreadyWrittenFunctions[nameForFunc]=True
    S=''
    ObjectDef = progSpec.findSpecOf(classes[0], FromStructName, 'string')
    fields=ObjectDef["fields"]
    configType=ObjectDef['configType']
    SeqOrAlt=''
    if configType=='SEQ': SeqOrAlt='parseSEQ'
    elif configType=='ALT': SeqOrAlt='parseALT'
    cdlog(logLvl, "WRITING function {}() to extract struct {} from parse tree: stage 2...".format(nameForFunc, ToStructName))
    if configType=='SEQ':
        S+=Write_structExtracter(classes, ToStructName, FromStructName, fields, nameForFunc, logLvl)
    elif configType=='ALT':
        S+=Write_ALT_Extracter(classes, ToStructName, fields, 'SRec', '', 'tmpStr', '    ', -1, logLvl)

    seqExtracter =  "\n    void: "+nameForFunc+"(our stateRec: SRec0, their "+ToStructName+": memStruct) <- {\n" + S + "    }\n"
    extracterFunctionAccumulator += seqExtracter
    #print "########################## extracterFunctionAccumulator\n",extracterFunctionAccumulator,"\n#####################################\n"

def writeParserWrapperFunction(classes, className):
    S='''
struct GLOBAL{
    our <CLASSNAME>: Parse_<CLASSNAME>(me string: textIn) <- {
        our <CLASSNAME>: result
        me EParser: parser
        parser.populateGrammar()
        parser.initParseFromString(parser.<CLASSNAME>_str, textIn)
        parser.doParse()
        if (parser.doesParseHaveError()) {
            print("Parse Error:" + parser.errorMesg + "\\n")
        } else {
            our stateRec: topItem <- parser.topDownResolve(parser.lastTopLevelItem, "")
            Allocate(result)
            parser.Extract_<CLASSNAME>_to_<CLASSNAME>(topItem, result)
        }
        return(result)
    }
}
struct <CLASSNAME>ExtracterThread: inherits=Threads{
    their Threaded_<CLASSNAME>ParseAndExtractor: ctrls
    our stateRec: parseTree
    our <CLASSNAME>: topItem

    void: init(their Threaded_<CLASSNAME>ParseAndExtractor: Ctrls, our stateRec: ParseTree, our <CLASSNAME>: TopItem) <- {
        topItem <- TopItem
        parseTree <- ParseTree
        ctrls <- Ctrls
        ctrls.extractCompleted <- false
    }
    void: run() <- {
        log("OPENING EXTRACT_THREAD")
        ctrls.parser.Extract_<CLASSNAME>_to_<CLASSNAME>(parseTree, topItem)
        log("Finished_<CLASSNAME>:"+toString(topItem))
        log("CLOSING EXTRACT_THREAD")
        //me SyncLock: lock<-{ctrls.chkExtractDone}
        //ctrls.extractCompleted <- true
        //lock.notify_one();
    }
}

struct <CLASSNAME>ParserThread: inherits=Threads{
    their Threaded_<CLASSNAME>ParseAndExtractor: ctrls
    our strBuf: userStream

    void: init(their Threaded_<CLASSNAME>ParseAndExtractor: Ctrls) <- {
        ctrls <- Ctrls
        ctrls.parseCompleted <- false
    }
    void: run() <- {
        log("OPENING PARSE_THREAD")
        ctrls.parser.doParse()
        log("CLOSING PARSE_THREAD")
        log("parser.lastTopLevelItem:"+ctrls.parser.lastTopLevelItem.mySymbol())
        ctrls.parser.dumpGraph("ParseDone", 1)
        our <CLASSNAME>: crnt_<CLASSNAME>
        if(ctrls.parser.doesParseHaveError()){
            ctrls.parser.errorMesg <- "Proteus syntax error: " + ctrls.parser.errorMesg + " at line " + toString(ctrls.parser.errLineNum) + ":" + toString(ctrls.parser.errCharPos)
            log(ctrls.parser.errorMesg)
            crnt_<CLASSNAME> <- NULL
        }
    }
}
struct Threaded_<CLASSNAME>ParseAndExtractor{
    their EParser: parser
    our stateRec: leftParseNode
    me bool: parseCompleted
    me bool: extractCompleted
    me Mutex: chkParseDone
    me Mutex: chkExtractDone
    me SyncLock: parseDoneLock
    me SyncLock: extractDoneLock
    me <CLASSNAME>ParserThread: parserThread
    me <CLASSNAME>ExtracterThread: extracterThread

    void: waitForParseCompletion()<-{
        me MutexMngr: MtxMgr{chkParseDone}
        while(!parseCompleted){
            parseDoneLock.wait(MtxMgr)
        }
    }
    void: waitForExtractCompletion()<-{
        me MutexMngr: MtxMgr{chkExtractDone}
        while(!extractCompleted){
            extractDoneLock.wait(MtxMgr)
        }
    }
    void: waitForThreadsToExit() <- {
        parserThread.waitForExit()
        extracterThread.waitForExit()
    }
    void: start(their EParser: iParser, their strBuf: streamToParse, our <CLASSNAME>: topItem) <- {
        parser<-iParser
        me int: startProduction <- parser.<CLASSNAME>_str
        parser.errorMesg <- ""
        parser.setStreamingMode(true)
        leftParseNode <- parser.initParseFromStream(startProduction, streamToParse)
        extracterThread.init(self, leftParseNode, topItem)
        extracterThread.start()
        parserThread.init(self)
        parserThread.start()
    }
}
'''.replace('<CLASSNAME>', className)
    codeDogParser.AddToObjectFromText(classes[0], classes[1], S, 'Parse_'+className+'()')

def CreateStructsForStringModels(classes, newClasses, tags):
    # Define fieldResult struct
    #~ structsName = 'fetchResult'
    #~ StructFieldStr = "mode [fetchOK, fetchNotReady, fetchSyntaxError, FetchIO_Error] : FetchResult"
    #~ progSpec.addObject(classes[0], classes[1], structsName, 'struct', 'SEQ')
    #~ codeDogParser.AddToObjectFromText(classes[0], classes[1], progSpec.wrapFieldListInObjectDef(structsName, StructFieldStr))

    if len(newClasses)==0: return
    populateBaseRules()

    global extracterFunctionAccumulator
    extracterFunctionAccumulator=""
    global nextParseNameID
    nextParseNameID=0
    numStringStructs=0
    for className in newClasses:
        if className[0] == '!': continue
        ObjectDef = classes[0][className]
        if(ObjectDef['stateType'] == 'string'):
            className=className[1:]
            cdlog(1, "  Writing parse system for "+className)
            numStringStructs+=1
            fields    = ObjectDef["fields"]
            configType= ObjectDef['configType']
            classTags = ObjectDef['tags']
            if 'StartSymbol' in classTags:
                writeParserWrapperFunction(classes, className)
            SeqOrAlt=''
            if configType=='SEQ': SeqOrAlt='parseSEQ'   # seq has {}
            elif configType=='ALT': SeqOrAlt='parseALT' # alt has []

            normedObjectName = className.replace('::', '_')
            if normedObjectName==className: normedObjectName+='_str'
            # Write the rules for all the fields, and a parent rule which is either SEQ or ALT, and REP/OPT as needed.
            cdlog(2, "CODING Parser Rules for {}".format(normedObjectName))
            ruleID = writeNonTermParseRule(classes, tags, normedObjectName, fields, SeqOrAlt, '', 3)

            if SeqOrAlt=='parseSEQ':
                [memObj, memVersionName]=fetchMemVersion(classes, className)
                if memObj!=None:
                    Write_Extracter(classes, className, className, 2)
                else: cdlog(2, "NOTE: Skipping {} because it has no struct version defined.".format(className))

    if numStringStructs==0: return

    ExtracterCode = extracterFunctionAccumulator

    ############  Add struct parser
    parserCode=genParserCode()
    codeDogParser.AddToObjectFromText(classes[0], classes[1], parserCode, 'Parser for '+className)

    structsName='EParser'
    progSpec.addObject(classes[0], classes[1], structsName, 'struct', 'SEQ')
    codeDogParser.AddToObjectFromText(classes[0], classes[1], progSpec.wrapFieldListInObjectDef(structsName, ExtracterCode), 'class '+structsName)
