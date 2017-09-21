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
    typeSpec=field['typeSpec']
    fldCat=progSpec.fieldsTypeCategory(typeSpec)
    if fldCat=='func': return ['', '', '', '', '']
    if progSpec.typeIsPointer(typeSpec) and skipFlags != 'skipPtr':  # Header for a POINTER
        fieldName+='Ptr'
        innerUpdateFuncStr = 'data.'+fieldRef+'.mySymbol(data.'+fieldRef+')'
        updateFuncText+="        "+fieldName+'.update('+fieldLabel+', '+innerUpdateFuncStr+', isNull('+innerUpdateFuncStr+'))\n'
        structText += "    "+owner+" widget::dash::ptrToItem: "+fieldName+"\n"

    elif 'arraySpec' in typeSpec and typeSpec['arraySpec']!=None and skipFlags != 'skipLists': # Header and items for LIST
        innerUpdateFuncStr = '"Size:"+toString(data.'+fieldName+'.size())'
        updateFuncText="        "+fieldName+'.update('+fieldLabel+', '+innerUpdateFuncStr+', isNull('+innerUpdateFuncStr+'))\n'
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

        updateFuncText="        "+fieldName+'.update(90, 150, '+fieldLabel+', '+valStr+', isNull('+valStr+'))\n'
        structText += "    "+owner+" widget::dash::dataField: "+fieldName+"\n"

    drawFuncText  ="        "+fieldName+'.draw(cr)\n'
    setPosFuncText += '''        if(!<fieldName>.isNullLike or displayMode==fullDisplay){
            <fieldName>.setPos(x,y,extC)
            extC <- <fieldName>.extC
            y <- y + <fieldName>.height
            extX <- max(extX, <fieldName>.extX)
            extY <- max(extY, <fieldName>.extY)
            width<- max(width, <fieldName>.width)
            <fieldName>.isHidden<-false
        } else {<fieldName>.isHidden<-true}
'''.replace('<fieldName>', fieldName)
  #  updateFuncText+='        if(crntWidth<'+fieldName+'.width){crntWidth <- '+fieldName+'.width}'
    handleClicksFuncText = '            '+fieldName+'.primaryClick(event)'
    return [structText, updateFuncText, drawFuncText, setPosFuncText, handleClicksFuncText]

#---------------------------------------------------------------  DUMP MAKING CODE

def EncodeDumpFunction(classes, className, dispMode):
    global classesEncoded
    cdlog(2, "ENCODING: "+ className)
    classesEncoded[className]=1
    [textFuncBody, structTextAcc, updateFuncTextAcc, drawFuncTextAcc, setPosFuncTextAcc, handleClicksFuncTextAcc, handleClicksFuncTxtAcc2] = ['', '', '', '', '', '', '']
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
            [structText, updateFuncText, drawFuncText, setPosFuncText, handleClicksFuncText]=getDashDeclAndUpdateCode(
                'me', '"'+fieldName+'"', fieldName, fieldName, field, 'skipNone', '    ')
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
        setPosFuncTextAcc += '\n        y <- y+5'+'\n        height <- y-posY'+'\n        me int:depX <- posX+width+40\n'
        countOfRefs=0
        for field in modelRef['fields']:
            typeSpec=field['typeSpec']
            fldCat=progSpec.fieldsTypeCategory(typeSpec)
            if fldCat=='func': continue
            if progSpec.typeIsPointer(typeSpec):  # Draw dereferenced POINTER
                fieldName=field['fieldName']
                declSymbolStr='    '
                if(countOfRefs==0):declSymbolStr+='me string: '
                countOfRefs+=1
                [structText, updateFuncText, drawFuncText, setPosFuncText, handleClicksFuncText]=getDashDeclAndUpdateCode(
                    'our', '"'+fieldName+'"', fieldName, fieldName, field, 'skipPtr', '    ')
                structTextAcc += structText
                tempFuncText = updateFuncText
                updateFuncText = declSymbolStr+'mySymbol <- data.'+fieldName+'.mySymbol(data.'+fieldName+')\n'
                updateFuncText += (  '    if(data.'+fieldName+' != NULL){\n'+
                                    '        if(!dashBoard.dependentIsRegistered(mySymbol)){'
                                    '\n            Allocate('+fieldName+')\n'+
                                    tempFuncText+
                                    '\n            dashBoard.addDependent(mySymbol, '+fieldName+')'+
                                    '\n        }\n    } else {'+fieldName+' <- NULL}\n')
                updateFuncTextPart2Acc += updateFuncText
                setPosFuncTextAcc      += '''
    if(<fieldName> != NULL and !<fieldName>Ptr.refHidden){
        <fieldName>.setPos(depX, extC, extC)
        extC <- <fieldName>.extY + 40
        extX <- max(extX, <fieldName>.extX)
        extY <- max(extY, <fieldName>.extY)
        me int: fromX<fieldName> <- <fieldName>Ptr.posX+135
        me int: fromY<fieldName> <- <fieldName>Ptr.posY+12
        me int: smallToX<fieldName> <- <fieldName>.posX
        me int: largeToX<fieldName> <- <fieldName>.posX + <fieldName>.width
        me int: smallToY<fieldName> <- <fieldName>.posY
        me int: largeToY<fieldName> <- <fieldName>.posY + <fieldName>.height
        our decor::arrow:: arrow(fromX<fieldName>, fromY<fieldName>, intersectPoint(fromX<fieldName>, smallToX<fieldName>, largeToX<fieldName>), intersectPoint(fromY<fieldName>, smallToY<fieldName>, largeToY<fieldName>))
        dashBoard.decorations.pushLast(arrow)
    }
'''.replace('<fieldName>', fieldName)
                handleClicksFuncTxtAcc2+= '    if('+fieldName+' != NULL and !'+fieldName+'Ptr.refHidden){\n'+fieldName+'.isHidden<-false\n    }\n'

        Code='''
struct widget::dash::display_'''+className+'''{
    me widget::dash::dataField: header
    me mode[headerOnly, fullDisplay, noZeros]: displayMode
    their '''+className+''': data
'''+structTextAcc+'''

    void: update(me string: _label, me string: textValue, their '''+className+''': _Data) <- {
        data <- _Data
        header.update(90, 150, _label, textValue, false)
        displayMode<-headerOnly
'''+updateFuncTextAcc+'''

'''+updateFuncTextPart2Acc+'''
    }

    void: setPos(me int:x, me int:y, me int: extCursor) <- {
        posX <- x;
        posY <- y;
        extC <- extCursor
        isHidden<-false
        header.setPos(x,y,extC)
        y <- y+header.height
        width <- header.width
        height <- y-posY
        extX <- header.extX
        extY <- max(y, extC)
        if(displayMode!=headerOnly){
            x <- x+10    /- Indent fields in a struct
'''+setPosFuncTextAcc+'''
            width <- width+10
        }
    }


    me bool: primaryClick(their GUI_ButtonEvent: event) <- {
        if(isHidden){return(false)}
        me double: eventX <- event.x
        me double: eventY <- event.y
        if( header.isTouchingMe(eventX, eventY)){
            if(displayMode==headerOnly){displayMode <- noZeros}
            else if(displayMode==noZeros){displayMode <- fullDisplay}
            else if(displayMode==fullDisplay){displayMode <- headerOnly}
        } else {
'''+handleClicksFuncTextAcc+'''
        }

'''+handleClicksFuncTxtAcc2+'''

        return(true)
    }

    void: draw(me GUI_ctxt: cr) <- {
        header.isHidden <- false
        header.draw(cr)
        if(displayMode!=headerOnly){
'''+drawFuncTextAcc+'''
            cr.rectangle(posX, posY, width, height)
            cr.strokeNow()
'''+drawFuncTextPart2Acc+'''
        }
    }
}\n'''
        codeDogParser.AddToObjectFromText(classes[0], classes[1], Code)

def apply(classes, tags, className, dispMode):
    if dispMode[:4]=='TAG_':
        dispModeTagName=dispMode[4:]
        dispMode=progSpec.fetchTagValue(tags, dispModeTagName)
    if(dispMode!='none' and dispMode!='text' and dispMode!='draw' and dispMode!='both'):
        cdErr('Invalid parameter for display mode in Code Data Display pattern: '+str(dispMode))
    if dispMode=='none': return

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

    me bool: isNull(me string: value) <- {
        if(value=="0" or value=="''" or value=="Size:0" or value=="NULL" or value=="false"){return(true)}
        else{return(false)}
    }
    """
        CODE+='}\n'

        codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE)

    classesToProcess.append(className)
    for classToEncode in classesToProcess:
        pattern_GenSymbols.apply(classes, {}, [classToEncode])      # Invoke the GenSymbols pattern
        EncodeDumpFunction(classes, classToEncode, dispMode)
    return
