#/////////////////  Use this pattern to write dump() or drawData() to display each member of the model for a struct.

import progSpec
import codeDogParser
from progSpec import cdlog, cdErr

thisPatternAlreadyUsedOnce=False

classesToProcess=[]
classesEncoded={}

#---------------------------------------------------------------  TEXT GEN
def displayTextFieldAction(label, fieldName, field, fldCat):
    global classesToProcess
    global classesEncoded
    valStr=''
    if(fldCat=='int' or fldCat=='double'):
        valStr='toString('+fieldName+')'
    elif(fldCat=='string' or fldCat=='char'):
        valStr= "'"+fieldName+"'"
    elif(fldCat=='flag' or fldCat=='bool'):
        valStr='dispBool('+fieldName+')'
    elif(fldCat=='mode'):
        valStr='toString('+fieldName+')'  #fieldName+'Strings['+fieldName+'] '
    elif(fldCat=='struct'):
        valStr=fieldName+'.dump(indent+"|   ")\n'

        structTypeName=field['typeSpec']['fieldType'][0]
        if not(structTypeName in classesEncoded):
            #print "TO ENDODE:", structTypeName
            classesEncoded[structTypeName]=1
            classesToProcess.append(structTypeName)
    if(fldCat=='struct'):
        S="    "+'print(indent, dispFieldAsText("'+label+'", 15), "\\n")\n    '+valStr+'\n    print("\\n")\n'
    else:
        S="    "+'print(indent, dispFieldAsText("'+label+'", 15), '+valStr+', "\\n")\n'
    return S

def encodeFieldText(fieldName, field, fldCat):
    S=""
    if fldCat=='func': return ''
    typeSpec=field['typeSpec']
    if 'arraySpec' in typeSpec and typeSpec['arraySpec']!=None:
        innerFieldType=typeSpec['fieldType']
        #print "ARRAYSPEC:",innerFieldType, field
        fldCatInner=progSpec.innerTypeCategory(innerFieldType)
        calcdName=fieldName+'["+toString(_item_key)+"]'
        S+="    withEach _item in "+fieldName+":{\n"
        S+="        "+displayTextFieldAction(calcdName, '_item', field, fldCatInner)+"    }\n"
    else: S+=displayTextFieldAction(fieldName, fieldName, field, fldCat)
    if progSpec.typeIsPointer(typeSpec):
        T ="    if("+fieldName+' == NULL){print('+'indent, dispFieldAsText("'+fieldName+'", 15)+"NULL\\n")}\n'
        T+="    else{\n    "+S+"    }\n"
        S=T
    return S

#---------------------------------------------------------------  DRAW GEN
def displayDrawFieldAction(label, fieldName, field, fldCat):
    global classesToProcess
    global classesEncoded
    valStr=''
    if(fldCat=='int' or fldCat=='double'):
        valStr='toString('+fieldName+')'
    elif(fldCat=='string' or fldCat=='char'):
        valStr= "'"+fieldName+"'"
    elif(fldCat=='flag' or fldCat=='bool'):
        valStr='dispBool('+fieldName+')'
    elif(fldCat=='mode'):
        valStr= label+'Strings['+fieldName+'] '
    elif(fldCat=='struct'):
        valStr= '"0x12345678"' #fieldName+'.drawData(cr, x+20, y)\n'

        structTypeName=field['typeSpec']['fieldType'][0]
        if not(structTypeName in classesEncoded):
            classesEncoded[structTypeName]=1
            classesToProcess.append(structTypeName)
    if(fldCat=='struct'):
        S="    "+'y<-y+drawField(cr, x,y, "'+label+'", '+valStr+')\n'
    else:
        S="    "+'y<-y+drawField(cr, x,y, "'+label+'", '+valStr+')\n'
    return S

def encodeFieldDraw(fieldName, field, fldCat):
    S=""
    if fldCat=='func': return ''
    typeSpec=field['typeSpec']
    if 'arraySpec' in typeSpec and typeSpec['arraySpec']!=None:
        innerFieldType=typeSpec['fieldType']
        fldCatInner=progSpec.innerTypeCategory(innerFieldType)
        calcdName=fieldName+'["+toString(_item_key)+"]'
        S+="    withEach _item in "+fieldName+":{\n"
        S+="        "+displayDrawFieldAction(calcdName, '_item', field, fldCatInner)+"    }\n"
    else: S+=displayDrawFieldAction(fieldName, fieldName, field, fldCat)
    if progSpec.typeIsPointer(typeSpec):
        T ="    if("+fieldName+' == NULL){drawField(cr, '+'x,y, "'+fieldName+'", "NULL")}\n'
        T+="    else{\n    "+S+"    }\n"
        S=T
    return S

#---------------------------------------------------------------  DUMP MAKING CODE

def EncodeDumpFunction(classes, className, dispMode):
    global classesEncoded
    cdlog(2, "ENCODING: "+ className)
    classesEncoded[className]=1
    textFuncBody=''
    drawFuncBody=''
    modelRef = progSpec.findSpecOf(classes[0], className, 'model')
    if modelRef==None:
        cdErr('To write a dump function for class '+className+' a model is needed but is not found.')
    for field in modelRef['fields']:
        fldCat=progSpec.fieldsTypeCategory(field['typeSpec'])
        fieldName=field['fieldName']

        if(dispMode=='text' or dispMode=='both'):
            textFuncBody+=encodeFieldText(fieldName, field, fldCat)
        if(dispMode=='draw' or dispMode=='both'):
            drawFuncBody+=encodeFieldDraw(fieldName, field, fldCat)

    if(dispMode=='text' or dispMode=='both'):
        Code="me void: dump(me string:indent) <- {\n"+textFuncBody+"    }\n"
        Code=progSpec.wrapFieldListInObjectDef(className, Code)
        codeDogParser.AddToObjectFromText(classes[0], classes[1], Code)

    if(dispMode=='draw' or dispMode=='both'):
        Code="me int: drawData(me GUI_ctxt: cr, me int:x, me int:y) <- {\n"+drawFuncBody+"    }\n"
        Code=progSpec.wrapFieldListInObjectDef(className, Code)
        codeDogParser.AddToObjectFromText(classes[0], classes[1], Code)

def apply(classes, tags, className, dispMode):
    global classesToProcess
    global thisPatternAlreadyUsedOnce
    if(not thisPatternAlreadyUsedOnce):
        thisPatternAlreadyUsedOnce=True
        CODE="""
struct GLOBAL{
    me string: dispBool(me bool: tf) <- {
        if(tf){return("true")} else {return("false")}
    }
    """
        if(dispMode=='text' or dispMode=='both'):
            CODE+="""
    me string: dispFieldAsText(me string: label, me int:labelLen) <- {
        me string: S <- ""
        me int: labelSize<-label.size()
        withEach count in RANGE(0..labelLen):{
            if (count<labelSize){S <- S+label[count]}
            else if(count==labelSize){ S <- S+":"}
            else {S <- S+" "}
        }
        return(S)
    }
    """
        if(dispMode=='draw' or dispMode=='both'):
            CODE+="""
    const int: fontSize <- 10
    me int: drawField(me GUI_ctxt: cr, me int:x, me int:y, me string: label, me string: value) <- {
        renderText(cr, label, "Ariel",  fontSize, x, y)
        renderText(cr, value, "Ariel",  fontSize, x+90, y)
        return(15)
    }
    """
        CODE+="""
}
    """
        codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE)

    classesToProcess.append(className)
    for classToEncode in classesToProcess:
        EncodeDumpFunction(classes, classToEncode, dispMode)
    return
