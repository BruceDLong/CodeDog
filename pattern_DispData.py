#/////////////////  Use this pattern to write dump() or drawData() to display each member of the model for a struct.

import progSpec
import codeDogParser
from progSpec import cdlog, cdErr

import pattern_GenSymbols

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
        valStr='dispBool('+fieldName+'!=0)'
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

def getDashDeclAndUpdateCode(owner, fieldLabel, fieldRef, fieldName, field, skipFlags, indent):
    global classesToProcess
    global classesEncoded
    [structText, updateFuncText, setPosFuncText, drawFuncText, handleClicksFuncText]=['', '', '', '', '']
    codeToMoveCursorDown = '\n        y <- y + '+fieldName+'.height\n'
    typeSpec=field['typeSpec']
    fldCat=progSpec.fieldsTypeCategory(typeSpec)
    if fldCat=='func': return ['', '', '', '', '']
    if progSpec.typeIsPointer(typeSpec) and skipFlags != 'skipPtr':  # Header for a POINTER
     #   fieldName+='Ptr'
        updateFuncText+="        "+fieldName+'.update('+fieldLabel+', data.'+fieldRef+'.mySymbol())\n'
        structText += "    "+owner+" widget::dash::ptrToItem: "+fieldName+"\n"

    elif 'arraySpec' in typeSpec and typeSpec['arraySpec']!=None and skipFlags != 'skipLists': # Header and items for LIST
        updateFuncText="        "+fieldName+'.update('+fieldLabel+', "Size:"+toString(data.'+fieldName+'.size()))\n'
         ## Now push each item
        innerFieldType=typeSpec['fieldType']
        #print "ARRAYSPEC:",innerFieldType, field
        fldCatInner=progSpec.innerTypeCategory(innerFieldType)
        newFieldRef=fieldName+'[_item_key]'
        newFieldLabel='"'+fieldName+'["+toString(_item_key)+"]"'
        updateFuncText+="\n        withEach _item in data."+fieldName+":{\n"
        [innerStructText, innerUpdateFuncText, innerDrawFuncText, innerSetPosFuncText, innerHandleClicksFuncText]=getDashDeclAndUpdateCode('our', newFieldLabel, newFieldRef, 'newItem', field, 'skipLists', '    ')
        updateFuncText+=innerStructText+'\n        Allocate(newItem)\n'+innerUpdateFuncText
        updateFuncText+="\n        "+fieldName+'.updatePush(newItem)'
        updateFuncText+='\n        }\n'
        structText += "    "+owner+" widget::dash::listOfItems: "+fieldName+"\n"
    elif(fldCat=='struct'):  # Header for a STRUCT
        updateFuncText="        "+fieldName+'.update('+fieldLabel+', ">", data.'+fieldRef+')\n'
        structTypeName=field['typeSpec']['fieldType'][0]
        structText += "    "+owner+" widget::dash::display_"+structTypeName+': '+fieldName+"\n"


        # Add new classname to a list so it can be encoded.
        if not(structTypeName in classesEncoded):
            classesEncoded[structTypeName]=1
            classesToProcess.append(structTypeName)

    else:   # Display field for a BASIC TYPES
        valStr=''
        if(fldCat=='int' or fldCat=='double'):
            valStr='toString(data.'+fieldName+')'
        elif(fldCat=='string' or fldCat=='char'):
            valStr= '"\'"+'+'data.'+fieldName+'+"\'"'
        elif(fldCat=='flag' or fldCat=='bool'):
            valStr='dispBool(data.'+fieldName+'!=0)'
        elif(fldCat=='mode'):
            valStr= fieldRef+'Strings[data.'+fieldName+'] '

        updateFuncText="        "+fieldName+'.update(90, 150, '+fieldLabel+', '+valStr+')\n'
        structText += "    "+owner+" widget::dash::dataField: "+fieldName+"\n"

    drawFuncText  ="        "+fieldName+'.draw(cr)\n'
    setPosFuncText+="        "+fieldName+'.setPos(x,y)' + codeToMoveCursorDown
  #  updateFuncText+='        if(crntWidth<'+fieldName+'.width){crntWidth <- '+fieldName+'.width}'
    handleClicksFuncText = '            if('+fieldName+'.isTouchingMe(eventX, eventY)){'+fieldName+'.handleClicks(widget, event)}'
    return [structText, updateFuncText, drawFuncText, setPosFuncText, handleClicksFuncText]

#---------------------------------------------------------------  DUMP MAKING CODE

def EncodeDumpFunction(classes, className, dispMode):
    global classesEncoded
    cdlog(2, "ENCODING: "+ className)
    classesEncoded[className]=1
    [textFuncBody, structTextAcc, updateFuncTextAcc, drawFuncTextAcc, setPosFuncTextAcc, handleClicksFuncTextAcc] = ['', '', '', '', '', '']
    updateFuncTextPart2Acc=''; drawFuncTextPart2Acc=''
    modelRef = progSpec.findSpecOf(classes[0], className, 'model')
    if modelRef==None:
        cdErr('To write a dump function for class '+className+' a model is needed but is not found.')
    ### Write code for each field
    for field in modelRef['fields']:
        fldCat=progSpec.fieldsTypeCategory(field['typeSpec'])
        fieldName=field['fieldName']

        if(dispMode=='text' or dispMode=='both'):
            textFuncBody+=encodeFieldText(fieldName, field, fldCat)
        if(dispMode=='draw' or dispMode=='both'):
            [structText, updateFuncText, drawFuncText, setPosFuncText, handleClicksFuncText]=getDashDeclAndUpdateCode('me', '"'+fieldName+'"', fieldName, fieldName, field, 'skipNone', '    ')
            structTextAcc     += structText
            updateFuncTextAcc += updateFuncText
            drawFuncTextAcc   += drawFuncText
            setPosFuncTextAcc += setPosFuncText
            handleClicksFuncTextAcc += handleClicksFuncText


    if(dispMode=='text' or dispMode=='both'):
        Code="me void: dump(me string:indent) <- {\n"+textFuncBody+"    }\n"
        Code=progSpec.wrapFieldListInObjectDef(className, Code)
        codeDogParser.AddToObjectFromText(classes[0], classes[1], Code)

    if(dispMode=='draw' or dispMode=='both'):
        for field in modelRef['fields']:
            typeSpec=field['typeSpec']
            fldCat=progSpec.fieldsTypeCategory(typeSpec)
            if fldCat=='func': continue
            if progSpec.typeIsPointer(typeSpec):  # Draw dereferenced POINTER
                fieldName=field['fieldName']
 #               [structText, updateFuncText, drawFuncText, setPosFuncText, handleClicksFuncText]=getDashDeclAndUpdateCode('our', '"'+fieldName+'"', fieldName, fieldName, field, 'skipPtr', '    ')
 #               structTextAcc   += structText
 #               updateFuncTextPart2Acc += updateFuncText
 #               drawFuncTextPart2Acc += drawFuncText

        Code='''
struct widget::dash::display_'''+className+'''{
    me widget::dash::dataField: header
    me mode[headerOnly, fullDisplay, noZeros]: displayMode
    their '''+className+''': data
'''+structTextAcc+'''
    void: update(me string: _label, me string: textValue, their '''+className+''': _Data) <- {
        data <- _Data
        header.update(90, 150, _label, textValue)
'''+updateFuncTextAcc+'''

'''+updateFuncTextPart2Acc+'''
    }

    void: setPos(me int:x, me int:y) <- {
        posX <- x; posY <- y;
        header.setPos(x,y)
        y <- y+header.height
        if(displayMode!=headerOnly){
            x <- x+10    /- Indent fields in a struct
'''+setPosFuncTextAcc+'''
        }
        y <- y+5
        width <- 150
        height <- y-posY
    }

    me bool: handleClicks(me GUI_item: widget, their ButtonEvent: event) <- {
        if(event.type==4){ /-GDK_BUTTON_PRESS){
            me int: eventX <- event.x
            me int: eventY <- event.y
            if( header.isTouchingMe(eventX, eventY)){
                if(displayMode==headerOnly){displayMode <- fullDisplay}
                else if(displayMode==fullDisplay){displayMode <- headerOnly}
            } else {
'''+handleClicksFuncTextAcc+'''
            }
        }
        return(false)
    }

    void: draw(me GUI_ctxt: cr) <- {
        header.draw(cr)
        if(displayMode!=headerOnly){
'''+drawFuncTextAcc+'''
            cr.rectangle(posX, posY, width, height)
            cr.strokeNow()
        }
'''+drawFuncTextPart2Acc+'''
    }
}\n'''
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
}

struct widget::dash::dataField {
    me string: label
    me string: value
    me int: midPos
    void: update(me int:MidPos, me int:w, me string: Label, me string: Value) <- {
        midPos<-MidPos; label<-Label; value<-Value;
    }

    void: setPos(me int:x, me int:y) <- {
        posX <- x; posY <- y;
        height <- 15
        width <- 150
    }

    void: draw(me GUI_ctxt: cr) <- {
        renderText(cr, label, "Ariel",  fontSize, posX, posY+15)
        renderText(cr, value, "Ariel",  fontSize, posX+midPos, posY+15)
    }
}

struct widget::dash::ptrToItem {
    me widget::dash::dataField: header
    our widget::dash: dashPtr

    void: update(me string: Label, me string: textValue) <- {
        header.update(90, 150, Label, textValue)
    }

    void: setPos(me int:x, me int:y) <- {
        posX <- x; posY <- y;
        header.setPos(x, y)
        height <- header.height
    }

    void: draw(me GUI_ctxt: cr) <- {
        header.draw(cr)
    }
}


struct widget::dash::listOfItems {
    me mode[headerOnly, fullDisplay, noZeros]: displayMode
    me widget::dash::dataField: header
    our widget::dash[list]: elements

    void: update(me string: Label, me string: textValue) <- {
        header.update(90, 150, Label, textValue)
        elements.clear()
    }

    void: updatePush(our widget::dash: element) <- {
        elements.pushLast(element)
    }

    void: setPos(me int:x, me int:y) <- {
        posX <- x; posY <- y;
        header.setPos(x, y)
        y <- y+header.height
        if(displayMode!=headerOnly){
            x <- x+8
            withEach element in elements:{
                element.setPos(x,y)

                y <- y+element.height
            }
        }
        width <- 150
        height <- y-posY
    }

    me bool: handleClicks(me GUI_item: widget, their ButtonEvent: event) <- {
        if(event.type==4){ /-GDK_BUTTON_PRESS){
            me int: eventX <- event.x
            me int: eventY <- event.y
            if( header.isTouchingMe(eventX, eventY)){
                if(displayMode==headerOnly){displayMode <- fullDisplay}
                else if(displayMode==fullDisplay){displayMode <- headerOnly}
            } else {
                withEach element in elements:{
                    if(element.isTouchingMe(eventX, eventY)){
                        element.handleClicks(widget, event)
                    }
                }
            }
        }
        return(false)
    }

    void: draw(me GUI_ctxt: cr) <- {
        header.draw(cr)
        if(displayMode!=headerOnly){
            withEach element in elements:{
                element.draw(cr)
            }
        }
    }
}

    """

        codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE)

    classesToProcess.append(className)
    for classToEncode in classesToProcess:
        pattern_GenSymbols.apply(classes, {}, [classToEncode])      # Invoke the GenSymbols pattern
        EncodeDumpFunction(classes, classToEncode, dispMode)
    return
