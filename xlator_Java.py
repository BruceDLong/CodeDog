import xlator_CPP

#######################################################

def includeDirective(libHdr):
    S = 'import '+libHdr+';\n'
    return S

def fetchXlators():
    xlators = {}

    xlators['LanguageName']     = "Java"
    xlators['BuildStrPrefix']   = "Javac "
    xlators['PtrConnector']     = "."                      # Name segment connector for pointers.
    xlators["codeExpr"]         = xlator_CPP.codeExpr
    xlators['includeDirective'] = includeDirective

    return(xlators)
