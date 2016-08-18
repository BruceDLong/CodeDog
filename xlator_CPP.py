#xlator_CPP.py
from CodeGenerator_CPP import *

######################################################   E X P R E S S I O N   C O D I N G

def codeFactor(item, xlator):
    ####  ( value | ('(' + expr + ')') | ('!' + expr) | ('-' + expr) | varFuncRef)
    #print '                  factor: ', item
    S=''
    retType='noType'
    item0 = item[0]
    #print "ITEM0=", item0, ">>>>>", item
    if (isinstance(item0, basestring)):
        if item0=='(':
            [S2, retType] = codeExpr(item[1], xlator)
            S+='(' + S2 +')'
        elif item0=='!':
            [S2, retType] = codeExpr(item[1], xlator)
            S+='!' + S2
        elif item0=='-':
            [S2, retType] = codeExpr(item[1], xlator)
            S+='-' + S2
        elif item0=='[':
            tmp="{"
            for expr in item[1:-1]:
                [S2, retType] = codeExpr(expr, xlator)
                if len(tmp)>1: tmp+=", "
                tmp+=S2
            tmp+="}"
            S+=tmp
        else:
            retType='string'
            if(item0[0]=="'"): S+=codeUserMesg(item0[1:-1], xlator)
            elif (item0[0]=='"'): S+='"'+item0[1:-1] +'"'
            else: S+=item0;
    else:
        if isinstance(item0[0], basestring):
            S+=item0[0]
        else:
            [codeStr, retType]=codeItemRef(item0, 'RVAL', xlator)
            S+=codeStr                                # Code variable reference or function call
    return [S, retType]

def codeTerm(item, xlator):
    #print '               term item:', item
    [S, retType]=codeFactor(item[0], xlator)
    if (not(isinstance(item, basestring))) and (len(item) > 1):
        for i in item[1]:
            #print '               term:', i
            if   (i[0] == '*'): S+=' * '
            elif (i[0] == '/'): S+=' / '
            elif (i[0] == '%'): S+=' % '
            else: print "ERROR: One of '*', '/' or '%' expected in code generator."; exit(2)
            [S2, retType2] = codeFactor(i[1], xlator)
            S+=S2
    return [S, retType]

def codePlus(item, xlator):
    #print '            plus item:', item
    [S, retType]=codeTerm(item[0], xlator)
    if len(item) > 1:
        for  i in item[1]:
            #print '            plus ', i
            if   (i[0] == '+'): S+=' + '
            elif (i[0] == '-'): S+=' - '
            else: print "ERROR: '+' or '-' expected in code generator."; exit(2)
            [S2, retType2] = codeTerm(i[1], xlator)
            S+=S2
    return [S, retType]

def codeComparison(item, xlator):
    #print '         Comp item', item
    [S, retType]=codePlus(item[0], xlator)
    if len(item) > 1:
        for  i in item[1]:
            #print '         comp ', i
            if   (i[0] == '<'): S+=' < '
            elif (i[0] == '>'): S+=' > '
            elif (i[0] == '<='): S+=' <= '
            elif (i[0] == '>='): S+=' >= '
            else: print "ERROR: One of <, >, <= or >= expected in code generator."; exit(2)
            [S2, retType] = codePlus(i[1], xlator)
            S+=S2
            retType='bool'
    return [S, retType]

def codeIsEQ(item, xlator):
    #print '      IsEq item:', item
    [S, retType]=codeComparison(item[0], xlator)
    if len(item) > 1:
        for i in item[1]:
            #print '      IsEq ', i
            if   (i[0] == '=='): S+=' == '
            elif (i[0] == '!='): S+=' != '
            else: print "ERROR: 'and' expected in code generator."; exit(2)
            [S2, retType] = codeComparison(i[1], xlator)
            S+=S2
            retType='bool'
    return [S, retType]

def codeLogAnd(item, xlator):
    #print '   And item:', item
    [S, retType] = codeIsEQ(item[0], xlator)
    if len(item) > 1:
        for i in item[1]:
            #print '   AND ', i
            if (i[0] == 'and'):
                [S2, retType] = codeIsEQ(i[1], xlator)
                S+=' && ' + S2
            else: print "ERROR: 'and' expected in code generator."; exit(2)
            retType='bool'
    return [S, retType]

def codeExpr(item, xlator):
    #print 'Or item:', item
    [S, retType]=codeLogAnd(item[0], xlator)
    if not isinstance(item, basestring) and len(item) > 1:
        for i in item[1]:
            #print 'OR ', i
            if (i[0] == 'or'):
                S+=' || ' + codeLogAnd(i[1], xlator)[0]
            else: print "ERROR: 'or' expected in code generator."; exit(2)
            retType='bool'
    #print "S:",S
    return [S, retType]

#######################################################

def includeDirective(libHdr):
    S = '#include <'+libHdr+'>\n'
    return S

def fetchXlators():
    xlators = {}

    xlators['LanguageName']     = "C++"
    xlators['BuildStrPrefix']   = "g++ -g -std=gnu++14  "
    xlators['PtrConnector']     = "->"                      # Name segment connector for pointers.
    xlators['codeExpr']         = codeExpr
    xlators['includeDirective'] = includeDirective

    return(xlators)
