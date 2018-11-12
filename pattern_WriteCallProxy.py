#/////////////////   pattern_WriteCallProxy.py
#/////////////////  Use this pattern to gererate call proxies. e.g. callback functions
import progSpec
import codeDogParser
from progSpec import cdlog, cdErr

def findStructRef(classes, structTypeName):
    structRef = progSpec.findSpecOf(classes, structTypeName, 'struct')
    if structRef==None:
        cdErr('To build a list GUI for list of "'+structTypeName+'" a struct is needed but is not found.')
    return structRef
def getFieldSpec(fieldName, structRef):
    #print "    Searching",structRef['name'],"for", fieldName
    if structRef==None:
        cdErr('To build a list GUI for list of "'+structTypeName+'" a struct is needed but is not found.')
    for field in structRef['fields']:
        if field['fieldName'] == fieldName: return field
    cdErr('Field not found in model "'+fieldName+'".')

def apply(classes, tags, proxyStyle, className, funcName, platformTag):
    print 'APPLY: in pattern_WriteCallProxy.apply: ',proxyStyle, '::', className,'\n'
    newParamFields = ''
    runParams      = ''
    structRef      = findStructRef(classes[0], className)
    funcSpec       = getFieldSpec(funcName, structRef)
    typeSpec       = funcSpec['typeSpec']
    fieldOwner     = typeSpec['owner']
    argList        = typeSpec['argList']
    fieldType      = typeSpec['fieldType']
    if className[0] == '%': className = className[1:]
    callbackName   = className+'_'+funcName+'_CB'
    bundleName     = className+'_'+funcName+'_bundle'
    if proxyStyle == "bundledArgs" and platformTag == "Linux":
        #print "Linux BundledArgs: ", callbackName, typeSpec
        if len(argList)>0:
            count=0
            for arg in argList:
                argName      = arg['fieldName']
                argTypeSpec  = arg['typeSpec']
                argOwner     = argTypeSpec['owner']
                argFieldType = progSpec.getFieldType(argTypeSpec)
                if not isinstance(argFieldType, basestring): argFieldType=argFieldType[0]
                if count > 0:
                    runParams      = runParams+', '
                    newParamFields = newParamFields+ '    '
                runParams      = runParams+' bundle.'+argName
                newParamFields = newParamFields + argOwner+' '+ argFieldType+': '+ argName + '\n'
                count = count + 1

        CODE =  '''
struct GLOBAL {
    bool: '''+callbackName+'''(their '''+bundleName+''': bundle) <- {
        bundle._object.'''+funcName+'''('''+runParams+''')
        return(false)
    }
}
struct '''+bundleName+''' {
    their '''+className+''': _object
    '''+newParamFields+'''

}\n'''
        codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, callbackName)
    elif proxyStyle == "bundledArgs" and platformTag == "Android":
        #print "Android BundledArgs: ", callbackName, funcSpec
        if len(argList)>0:
            count=0
            for arg in argList:
                argName      = arg['fieldName']
                argTypeSpec  = arg['typeSpec']
                argOwner     = argTypeSpec['owner']
                argFieldType = progSpec.getFieldType(argTypeSpec)
                if not isinstance(argFieldType, basestring): argFieldType=argFieldType[0]
                if count > 0:
                    runParams      = runParams+', '
                    newParamFields = newParamFields+ '    '
                runParams=runParams+argName
                newParamFields = newParamFields + argOwner+' '+ argFieldType+': '+ argName + '\n'
                count = count + 1

        CODE =  '''
struct '''+bundleName+''': implements=Runnable{
    their '''+className+''': objToCall
    '''+newParamFields+'''

    void: run() <- {
        objToCall.'''+funcName+'''('''+runParams+''')
    }
}\n'''

        codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, callbackName)
    elif proxyStyle == "widgetData" and platformTag == "Linux":
        #print "Linux widgetData: ", callbackName, funcSpec
        
        CODE =  '''
struct GLOBAL {
    void: '''+callbackName+'''(their GtkWidget: wid, their '''+className+''': _obj) <- {
       _obj.'''+funcName+'''()
    }
}\n'''

        codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, callbackName)
    elif proxyStyle == "widgetData" and platformTag == "Android":
        print "Android widgetData: ", callbackName, funcSpec
    else: print "###ERROR: unknown proxyStyle & Platform: ", proxyStyle, platformTag; exit(1)
    #print '==========================================================\n'+CODE

