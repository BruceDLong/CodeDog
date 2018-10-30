#/////////////////  Use this pattern to gererate a GUI to manipulate a struct.

import progSpec
import codeDogParser
from progSpec import cdlog, cdErr


classesToProcess=[]
classesEncoded={}
currentClassName=''
currentModelSpec=None

# Code accmulator strings:
newWidgetFields=''
widgetInitFuncCode=''
widgetFromVarsCode=''
varsFromWidgetCode=''

def findModelRef(classes, structTypeName):
    modelRef = progSpec.findSpecOf(classes, structTypeName, 'model')
    if modelRef==None:
        cdErr('To build a list GUI for list of "'+structTypeName+'" a model is needed but is not found.')
    return modelRef

def getFieldSpec(fldCat, field):
    parameters={}
    if fldCat=='mode': fldCat='enum'
    elif fldCat=='double': fldCat='float'

    if fldCat=='enum':
        parameters=field['typeSpec']['enumList']
    elif fldCat=='RANGE':
        parameters={1, 10}

    typeSpec=field['typeSpec']
    if progSpec.isAContainer(typeSpec):
        innerFieldType=typeSpec['fieldType']
        datastructID = progSpec.getDatastructID(typeSpec)
        return [datastructID, innerFieldType]
    else:
        if fldCat=='struct':
            fldCat='struct' #field['typeSpec']['fieldType'][0]
        return [fldCat, parameters]

def deCamelCase(identifier):
    outStr=''
    chPos=0
    for ch in identifier:
        if chPos==0: outStr += ch.upper()
        else:
            if ch.isupper() and ch.isalpha():
                outStr += ' '+ch.lower()
            elif ch=='_':
                outStr += ' '
            else: outStr += ch
        chPos+=1
    return outStr

def changeDataFieldType(classes, structTypeName, typeSpec):
    retFieldType = ""
    if structTypeName[:4] == "Time": retFieldType = 'timeValue'; newFieldOwner = 'me'
    elif structTypeName[:3] == "Int": retFieldType = 'int'; newFieldOwner = 'me'
    else: print "ERROR: UNKNOWN WIDGET DATA TYPE CONVERSION: ", structTypeName
    if retFieldType != "": typeSpec['fieldType'][0] = retFieldType;typeSpec['owner'] = newFieldOwner
    return retFieldType

def addNewStructToProcess(guiStructName, structTypeName, structOrList, widgetStyle):
    global classesEncoded
    if guiStructName == 'timeValue_Dialog_GUI': return
    if not(guiStructName in classesEncoded)and not(structTypeName=='DateValue' or structTypeName=='Agreement' or structTypeName=='timeOfDay' or structTypeName=='DateTime' or structTypeName=='matterTerm' or structTypeName=='FoodData' or structTypeName=='MealData' or structTypeName=='MedItemData' or structTypeName=='MedBunchData'):
        classesEncoded[guiStructName]=1
        classesToProcess.append([structTypeName, structOrList, widgetStyle, guiStructName])

def getButtonHandlingCode(classes, buttonLabel, fieldName):
    global newWidgetFields
    global widgetInitFuncCode
    # Add a button to widget and put it in box
    buttonsWidgetName = buttonLabel+'Button'
    widgetInitFuncCode   += '        their GUI_button: '+buttonsWidgetName+' <- makeButtonWidget("'+buttonLabel+'")\n'
    # make its onclick trigger
    # g_signal_connect(G_OBJECT(EnterButton), "clicked", G_CALLBACK(EntryPad_Dialog__EnterBtnCB), Data.get());
    widgetInitFuncCode   += '        GUI.setBtnCallback2('+buttonsWidgetName+', "clicked", '+ buttonsWidgetName +'_CB, Data, _data.'+fieldName+'())\n'
    widgetInitFuncCode   += '        addToContainer(box, '+buttonsWidgetName+')\n'
    # onClick() should call this.callback()
    #   GTK: void EntryPad_Dialog__EnterBtnCB(GtkWidget* wid, EntryPad* EPad){EPad->enter_btn();}

def codeListWidgetManagerClassOverride(classes, listManagerStructName, structTypeName):
    funcTextToUpdateViewWidget      = ''
    funcTextToUpdateEditWidget      = ''
    funcTextToUpdateCrntFromWidget  = ''
    funcTextToPushCrntToListView    = ''
    rowHeaderCode                   = ''
    rowViewCode                     = ''

    # Find the model
    modelRef = findModelRef(classes[0], structTypeName)
    currentModelSpec = modelRef
    ### Write code for each field
    for field in modelRef['fields']:
        typeSpec        = field['typeSpec']
        fldCat          = progSpec.fieldsTypeCategory(typeSpec)
        fieldName       = field['fieldName']
        label           = deCamelCase(fieldName)
        CasedFieldName  = fieldName[0].upper() + fieldName[1:]
        widgetName      = CasedFieldName + 'Widget'

        if not progSpec.isAContainer(typeSpec):
            if(fldCat!='struct'):
                rowHeaderCode   += '        their GUI_Frame: '+fieldName + '_header <- makeLabelWidget("'+fieldName+'")\n'
                rowHeaderCode   += '        setLabelWidth('+fieldName+'_header, 15)\n'
                rowHeaderCode   += '        addToContainer(headerBox, '+fieldName+'_header)\n'

            if fldCat=='struct':
                funcTextToUpdateViewWidget     += ''
                funcTextToUpdateEditWidget     += '   /- updateWidgetFromVars()\n'
                funcTextToUpdateCrntFromWidget += '   /- updateVarsFromWidget()\n'
            elif fldCat=='enum' or fldCat=='mode':
                funcTextToUpdateViewWidget     += ''
                funcTextToUpdateEditWidget     += ''
                funcTextToUpdateCrntFromWidget += ''#  crntRecord.'+fieldName+' <- dialog.' + widgetName + '.getValue()\n'
            elif fldCat=='bool':
                funcTextToUpdateViewWidget     += ''
                funcTextToUpdateEditWidget     += ''
                funcTextToUpdateCrntFromWidget += '    crntRecord.'+fieldName+' <- dialog.' + widgetName + '.getValue()\n'
            elif fldCat=='string':
                funcTextToUpdateViewWidget     += ''
                funcTextToUpdateEditWidget     += '    dialog.' + widgetName + '.setValue('+structTypeName+'_ListData[N].'+fieldName+')\n'
                funcTextToUpdateCrntFromWidget += '    me string: '+widgetName+'Str <- string(dialog.' + widgetName + '.getValue())\n'
                funcTextToUpdateCrntFromWidget += '    crntRecord.'+fieldName+' <- '+widgetName+'Str\n'
                rowViewCode                    += '        their GUI_Frame: '+fieldName + '_value <- makeLabelWidget(crntRecord.'+fieldName+')\n'
                rowViewCode                    += '        setLabelWidth('+fieldName+'_value, 15)\n'
                rowViewCode                    += '        addToContainer(rowBox, '+fieldName+'_value)\n'
                rowViewCode                    += '        showWidget('+fieldName+'_value)\n'
            elif fldCat=='int':
                funcTextToUpdateViewWidget     += ''
                funcTextToUpdateEditWidget     += '    dialog.' + widgetName + '.setValue('+structTypeName+'_ListData[N].'+fieldName+')\n'
                #funcTextToUpdateCrntFromWidget += '    me string: '+widgetName+'Str <- string(dialog.' + widgetName + '.getValue())\n'
                #funcTextToUpdateCrntFromWidget += '    crntRecord.'+fieldName+' <- dataStr\n'
                rowViewCode                    += '        their GUI_Frame: '+fieldName + '_value <- makeLabelWidget(toString(crntRecord.'+fieldName+'))\n'
                rowViewCode                    += '        setLabelWidth('+fieldName+'_value, 15)\n'
                rowViewCode                    += '        addToContainer(rowBox, '+fieldName+'_value)\n'
                rowViewCode                    += '        showWidget('+fieldName+'_value)\n'
            else: print'pattern_MakeGUI.codeListWidgetManagerClassOverride fldCat not specified: ', fldCat;  exit(2)

###############
    CODE = 'struct '+listManagerStructName+''': inherits=ListWidgetManager{
    our <STRUCTNAME>: crntRecord
    our <STRUCTNAME>[our list]: <STRUCTNAME>_ListData
    me <STRUCTNAME>_Dialog_GUI: dialog
    their GUI_Frame: box
    their GUI_Frame:            listViewWidget
    their GUI_Frame[their list]:rows
    their GUI_Frame:            crntRow

    /- Override all these for each new list editing widget
    their GUI_Frame: makeListHeader() <- {
        box                        <- makeYStack("")
        their GUI_Frame: headerRow <- makeRowWidget("")
        their GUI_Frame: headerBox <- makeXStack("")
        <ROWHEADERCODE>
        addToContainer(headerRow, headerBox)
        addToContainer(box, headerRow)
        return(box)
    }

    their GUI_Frame: makeRowView(our <STRUCTNAME>: item) <- {
        crntRecord <- item
        their GUI_Frame: rowBox <- makeXStack("")
        <ROWVIEWCODE>
        showWidget(rowBox)
        return(rowBox)
    }

    their listWidget: makeListViewWidget() <- {
        listViewWidget <- makeListWidget('')
        setListWidgetSelectionMode (listViewWidget, SINGLE)
        withEach item in <STRUCTNAME>_ListData {
            their GUI_Frame: row <- makeRowView(item)
            addToContainer(listViewWidget, row)
        }
        return(listViewWidget)
    }

    me int: pushCrntToList(me int: N) <- {
        <STRUCTNAME>_ListData.pushLast(crntRecord);
        me int: listLength <- getListLength()
        print('listLength: ', listLength)
        their GUI_Frame: row <- makeRowView(crntRecord)
        rows.pushLast(row)
        addToContainer(listViewWidget, row)
        return(listLength)
    }

    void: deleteNthRow(me int: N) <- {
        rows.deleteNth(N)
    }

    their GUI_Frame: getNthRow(me int: N) <-{
        crntRow <- rows[N]
    }

    me int: deleteNthItem(me int: N) <- {
        <STRUCTNAME>_ListData.deleteNth(N)
        me int: retVal <- getListLength()
        return(retVal)
    }

    void: updateViewableWidget() <- {<funcTextToUpdateViewWidget>}
    their GUI_item: makeEditableWidget() <- {return(dialog.make<STRUCTNAME>Widget(crntRecord))}
    void: updateEditableWidget(me int: N) <- {<funcTextToUpdateEditWidget>}
    void: updateCrntFromEdited(me int: N) <- {<funcTextToUpdateCrntFromWidget>}
    void: allocateNewCurrentItem() <- {Allocate(crntRecord)}
    void: copyCrntBackToList(me int: N) <- {<STRUCTNAME>_ListData[N] <- crntRecord}
    void: copyCrntBackToListView(me int: N) <- {
        print('copyCrntBackToListView ', N)
    }
    void: setCurrentItem(me int: idx) <- {crntRecord <- <STRUCTNAME>_ListData[idx]}
    void: setValue(our <STRUCTNAME>[our list]: ListData) <- {<STRUCTNAME>_ListData <- ListData}
    me int: getListLength() <- {return(<STRUCTNAME>_ListData.size())}

    their GUI_item: initWidget(our <STRUCTNAME>[our list]: Data) <- {
        <STRUCTNAME>_ListData <- Data
        Allocate(rows)
        return(ListEdBox.init_dialog(self))
    }
}
'''
    CODE = CODE.replace('<STRUCTNAME>', structTypeName)
    CODE = CODE.replace('<funcTextToUpdateViewWidget>', funcTextToUpdateViewWidget)
    CODE = CODE.replace('<funcTextToUpdateEditWidget>', funcTextToUpdateEditWidget)
    CODE = CODE.replace('<funcTextToUpdateCrntFromWidget>', funcTextToUpdateCrntFromWidget)
    CODE = CODE.replace('<funcTextToPushCrntToListView>', funcTextToPushCrntToListView)
    CODE = CODE.replace('<ROWHEADERCODE>', rowHeaderCode)
    CODE = CODE.replace('<ROWVIEWCODE>', rowViewCode)
    #print '==========================================================\n'+CODE
    codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, listManagerStructName)

def getWidgetHandlingCode(classes, fldCat, fieldName, field, structTypeName, dialogStyle, classPrimaryGuiItem, indent):
    # _Dialog_GUI is editable widget
    global newWidgetFields
    global widgetInitFuncCode
    global widgetFromVarsCode
    global varsFromWidgetCode

    label               = deCamelCase(fieldName)
    [fieldSpec, params] = getFieldSpec(fldCat, field)
    typeName            = fieldSpec+'Widget'
    CasedFieldName      = fieldName[0].upper() + fieldName[1:]
    widgetName          = CasedFieldName + 'Widget'
    typeSpec            = field['typeSpec']
    innerFieldType      = typeSpec['fieldType']
    fieldType           = innerFieldType[0]
    widgetBoxName       = widgetName
    localWidgetVarName  = widgetName
    makeTypeNameCall    = ''

    if fieldType=='timeValue':
        typeName              = 'dateWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      =  'Allocate('+widgetName+');\n' + widgetBoxName + ' <- '+ widgetName+'.makeDateWidget("'+label+'")\n'
        widgetFromVarsCode   += '        ' + widgetName+ '.setValue(var.'+ fieldName +')\n'
        varsFromWidgetCode   += '        _data.' + fieldName + ' <- ' + widgetName + '.getValue()\n'
    elif fieldType=='Agreement':
        typeName              = 'AgreeWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = '        Allocate('+widgetName+')\n'
        makeTypeNameCall     += '        ' + widgetBoxName + ' <- '+ widgetName+'.makeAgreeWidget("'+fieldName+'")\n'
        widgetFromVarsCode   += ''
        varsFromWidgetCode   += ''
    elif fieldType=='DateValue':
        typeName              = 'DateWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = '        Allocate('+widgetName+')\n'
        makeTypeNameCall     += '        ' + widgetBoxName + ' <- '+ widgetName+'.initCrnt("'+label+'")\n'
        widgetFromVarsCode   += ''
        varsFromWidgetCode   += '        '+widgetName+'.getValue()\n'
    elif fieldType=='timeOfDay':
        typeName              = 'TimeWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = '        Allocate('+widgetName+')\n'
        makeTypeNameCall     += '        ' + widgetBoxName + ' <- '+ widgetName+'.initCrnt("'+label+'")\n'
        widgetFromVarsCode   += ''
        varsFromWidgetCode   += '        '+widgetName+'.getValue()\n'
    elif fieldType=='DateTime':
        typeName              = 'DateTimeWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = '        Allocate('+widgetName+')\n'
        makeTypeNameCall     += '        ' + widgetBoxName + ' <- '+ widgetName+'.initCrnt("'+label+'")\n'
        widgetFromVarsCode   += ''
        varsFromWidgetCode   += '        '+widgetName+'.getValue()\n'
    elif fieldType=='FoodData':
        typeName              = 'FoodDataWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = '        Allocate('+widgetName+')\n'
        makeTypeNameCall     += '        ' + widgetBoxName + ' <- '+ widgetName+'.makeFoodDataWidget("'+label+'", _data.'+fieldName+')\n'
        #widgetFromVarsCode   += '        '+widgetName+'.setValue(var.'+ fieldName +')\n'
        #varsFromWidgetCode   += '        '+widgetName+'.getValue()\n'
    elif fieldType=='MealData':
        typeName              = 'MealDataWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = '        Allocate('+widgetName+')\n'
        makeTypeNameCall     += '        ' + widgetBoxName + ' <- '+ widgetName+'.makeMealDataWidget("'+label+'", _data.'+fieldName+')\n'
        #widgetFromVarsCode   += '        '+widgetName+'.setValue(var.'+ fieldName +')\n'
        varsFromWidgetCode   += '        '+widgetName+'.getValue()\n'
    elif fieldType=='MedItemData':
        typeName              = 'MedItemDataWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = '        Allocate('+widgetName+')\n'
        makeTypeNameCall     += '        ' + widgetBoxName + ' <- '+ widgetName+'.makeMedItemDataWidget("'+label+'", _data.'+fieldName+')\n'
        #widgetFromVarsCode   += '        '+widgetName+'.setValue(var.'+ fieldName +')\n'
        #varsFromWidgetCode   += '        '+widgetName+'.getValue()\n'
    elif fieldType=='MedBunchData':
        typeName              = 'MedBunchDataWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = '        Allocate('+widgetName+')\n'
        makeTypeNameCall     += '        ' + widgetBoxName + ' <- '+ widgetName+'.makeMedBunchDataWidget("'+label+'", _data.'+fieldName+')\n'
        #widgetFromVarsCode   += '        '+widgetName+'.setValue(var.'+ fieldName +')\n'
        #varsFromWidgetCode   += '        '+widgetName+'.getValue()\n'
    elif fieldType=='matterTerm':
        typeName              = 'MatterTermWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = '        Allocate('+widgetName+')\n'
        makeTypeNameCall     += '        ' + widgetBoxName + ' <- '+ widgetName+'.makeMatterTermWidget("'+label+'", _data.'+fieldName+')\n'
        widgetFromVarsCode   += '        '+widgetName+'.setValue(var.'+ fieldName +')\n'
        varsFromWidgetCode   += '        '+widgetName+'.getValue()\n'
    elif fieldSpec=='widget':
        if fieldType=='graphWidget': 
            print 'widget: ', fieldType
            typeName              = fieldType
            widgetName            = fieldName +'Widget'
            widgetBoxName         = fieldName
            localWidgetVarName    = fieldName
            newWidgetFields      += '    their GUI_item' + ': ' + fieldName + '\n'
            makeTypeNameCall      = widgetName+' <- Data.' + fieldName + '\n' + fieldName + '<- '+widgetName+'.init("'+label+'")\n'
        else:
            typeName              = fieldType
            widgetName            = fieldName +'Widget'
            widgetBoxName         = fieldName+'Canvas'
            localWidgetVarName    = fieldName
            dataType = changeDataFieldType(classes, structTypeName, typeSpec)
            makeTypeNameCall      = '        Allocate('+widgetName+')\n'
            makeTypeNameCall     += '        their GUI_canvas:    '+fieldName+'Canvas <- ' + widgetName+'.init("'+label+'")\n'
            #widgetFromVarsCode   += '        '+widgetName+'.setValue(var.'+ fieldName +')\n'
            varsFromWidgetCode   += '        _data.' + fieldName + ' <- ' +widgetName+'.getValue()\n'
    elif fieldSpec=='struct':
        typeName              = 'GUI_Frame'
        guiStructName         = structTypeName + '_Dialog_GUI'
        guiMgrName            = fieldType + '_GUI_Mgr'
        if progSpec.typeIsPointer(typeSpec): widgetInitFuncCode += '        Allocate(_data.'+fieldName+')\n'
        widgetInitFuncCode   += '        Allocate('+guiMgrName+')\n'
        makeTypeNameCall      = widgetName+' <- '+guiMgrName+'.make'+structTypeName+'Widget(_data.'+fieldName+')\n'
        makeTypeNameCall     +=  guiMgrName + '.parentGuiMgr <- self\n'
        newWidgetFields      += '    our ' + guiStructName + ': '+ guiMgrName+'\n'
        widgetFromVarsCode   += '        ' + guiMgrName+ '.setValue(var.'+fieldName+')\n'
        varsFromWidgetCode   += '        ' + guiMgrName + '.getValue()\n'
    elif fieldSpec=='enum':
        typeName = 'enumWidget'
        EnumItems=[]
        for enumItem in params: EnumItems.append('"'+deCamelCase(enumItem)+'"')
        optionString          = '[' + ', '.join(EnumItems) + ']'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = 'Allocate('+widgetName+'); ' + widgetBoxName+' <- '+ widgetName+'.makeEnumWidget("'+label+'", '+optionString+')\n'
        widgetFromVarsCode   += '        ' + widgetName+ '.setValue(var.'+ fieldName +')\n'
        varsFromWidgetCode   += '        _data.' + fieldName + ' <- ' + widgetName + '.getValue()\n'
    elif fieldSpec=='string':
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = 'Allocate('+widgetName+'); ' + widgetBoxName + ' <- '+ widgetName+'.makeStringWidget("'+label+'")\n'
        widgetFromVarsCode   += '        ' + widgetName+ '.setValue(var.'+ fieldName +')\n'
        varsFromWidgetCode   += '        _data.' + fieldName + ' <- ' + widgetName + '.getValue()\n'
    elif fieldSpec=='int':
        widgetBoxName         = widgetName +'.box'
        makeTypeNameCall      = 'Allocate('+widgetName+')\n'
        if progSpec.typeIsNumRange(innerFieldType):
            typeName = 'intRangeWidget'
            range1 = innerFieldType[0]
            range2 = innerFieldType[2]
            makeTypeNameCall += '        '+widgetName+'.minValue <- '+range1+'\n        '+widgetName+'.maxValue <- '+range2+'\n'
            makeTypeNameCall += '        '+widgetBoxName+' <- '+ widgetName+'.makeIntRangeWidget("'+label+'")\n'
        else:
            makeTypeNameCall += '        '+widgetBoxName+' <- '+widgetName+'.makeIntWidget("'+label+'")\n'
        widgetFromVarsCode   += '        '+widgetName+'.setValue(var.'+ fieldName +')\n'
        varsFromWidgetCode   += '        _data.'+fieldName+' <- '+widgetName+'.getValue()\n'
    elif fieldSpec=='bool':
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      =  'Allocate('+widgetName+'); ' + widgetBoxName + ' <- '+ widgetName+'.makeBoolWidget("'+label+'")\n'
        widgetFromVarsCode   += '        ' + widgetName+ '.setValue(var.'+ fieldName +')\n'
        varsFromWidgetCode   += '        _data.' + fieldName + ' <- ' + widgetName + '.getValue()\n'
    elif fieldSpec=='list' or fieldSpec=='map': pass
    else: print'pattern_MakeGUI.getWidgetHandlingCode fieldSpec not specified: ', fieldSpec;  exit(2)

    # If this is a list or map, populate it
    if progSpec.isAContainer(typeSpec):
        makeTypeNameCall      =  widgetName+' <- make'+typeName[0].upper() + typeName[1:]+'("'+label+'")\n'
        fldCatInner           = progSpec.innerTypeCategory(innerFieldType)

        # If it hasn't already been added, make a struct <ItemType>_ListWidgetManager:ListWidgetManager{}
        listManagerStructName = structTypeName+'_ListWidgetManager'
        codeListWidgetManagerClassOverride(classes, listManagerStructName, structTypeName)

        listWidMgrName        = widgetName+'_LEWM'
        newWidgetFields      += '    me '+listManagerStructName+': '+listWidMgrName+'\n'

        widgetListEditorName  = widgetName+'_Editor'
        localWidgetVarName    = widgetListEditorName
        if progSpec.typeIsPointer(typeSpec): widgetInitFuncCode += '        Allocate(_data.'+fieldName+')\n'
        widgetInitFuncCode   += '        their GUI_item: '+widgetListEditorName+' <- '+listWidMgrName+'.initWidget(_data.'+fieldName+')\n'
        if classPrimaryGuiItem==fieldName: widgetInitFuncCode   += '        addToContainerAndExpand(box, '+widgetListEditorName+')\n'
        else: widgetInitFuncCode   += '        addToContainer(box, '+widgetListEditorName+')\n'
        widgetFromVarsCode   += '        ' + listWidMgrName + '.setValue(var.'+ fieldName +')\n'
#        varsFromWidgetCode   += '        ' + listWidMgrName + ' <- ' + widgetName + '.getValue()\n'
    elif dialogStyle == 'WizardStack':
        newWidgetFields      += '    our '+typeName+': '+widgetName+'\n'
        widgetInitFuncCode   += '        '+makeTypeNameCall
        widgetInitFuncCode   += '        addToZStack(wiz.ZStack, '+widgetBoxName+', "'+CasedFieldName+'")\n'
        widgetInitFuncCode   += '        wiz.children.pushLast("'+CasedFieldName+'")\n'
    elif dialogStyle   == 'Z_stack': 
        widgetBoxName         =  guiMgrName +'.box'
        newWidgetFields      += '    our '+typeName+': '+widgetName+'\n'
        widgetInitFuncCode   += '        '+makeTypeNameCall+'\n'
        widgetInitFuncCode   += '        addToZStack(Zbox, '+widgetBoxName+', "'+CasedFieldName+'")\n'
        widgetInitFuncCode   += '        children.pushLast("'+CasedFieldName+'")\n'
    else: # Not an ArraySpec:
        newWidgetFields      += '    our '+typeName+': '+widgetName+'\n'
        widgetInitFuncCode   += '        '+makeTypeNameCall
        if classPrimaryGuiItem==fieldName: widgetInitFuncCode   += '        addToContainerAndExpand(box, '+widgetBoxName+')\n'
        else: widgetInitFuncCode   += '        addToContainer(box, '+widgetBoxName+')\n'
    if dialogStyle == 'TabbedStack':
        widgetInitFuncCode+='             '+'setTabLabelText(box, '+ localWidgetVarName+', "'+label+'")\n'

def BuildGuiForList(classes, className, dialogStyle, newStructName):
    # This makes 4 types of changes to the class:
    #   It adds a widget variable for items in model // newWidgetFields: '    their '+typeName+': '+widgetName
    #   It adds a set Widget from Vars function      // widgetFromVarsCode: Func UpdateWidgetFromVars()
    #   It adds a set Vars from Widget function      // varsFromWidgetCode: Func UpdateVarsFromWidget()
    #   It add an initialize Widgets function.       // widgetInitFuncCode: widgetName+' <- '+makeTypeNameCall+'\n    addToContainer(box, '+widgetName+')\n'

    # dialogStyles: 'Z_stack', 'X_stack', 'Y_stack', 'TabbedStack', 'FlowStack', 'WizardStack', 'Dialog', 'SectionedDialogStack'
    # also, handle non-modal dialogs

    global classesEncoded
    global currentClassName
    global currentModelSpec
    classesEncoded[className]=1
    currentClassName = className

    # reset the string vars that accumulate the code
    global newWidgetFields
    global widgetInitFuncCode
    global widgetFromVarsCode
    global varsFromWidgetCode

    newWidgetFields=''
    widgetInitFuncCode=''
    widgetFromVarsCode=''
    varsFromWidgetCode=''

    # Find the model
    modelRef            = findModelRef(classes[0], className)
    currentModelSpec    = modelRef
    rowHeaderCode       = ''
    rowViewCode         = ''
    for field in modelRef['fields']:
        fieldName       = field['fieldName']
        typeSpec        = field['typeSpec']
        fldCat          = progSpec.fieldsTypeCategory(typeSpec)
        fieldType       = progSpec.fieldTypeKeyword(field['typeSpec']['fieldType'])
        [fieldSpec, params] = getFieldSpec(fldCat, field)
        structTypeName  =''
        if fldCat=='struct': # Add a new class to be processed
            structTypeName =typeSpec['fieldType'][0]
            newGUIStyle    = 'Dialog'
            guiStructName  = structTypeName+'_'+newGUIStyle+'_GUI'
            addNewStructToProcess(guiStructName, structTypeName, 'struct', 'Dialog')

        if progSpec.isAContainer(typeSpec):# Add a new list to be processed
            structTypeName = typeSpec['fieldType'][0]
            guiStructName  = structTypeName+'_LIST_View'
            addNewStructToProcess(guiStructName, structTypeName, 'list', 'Dialog')


    CODE =  '''struct <NEWSTRUCTNAME>{
    our <CLASSNAME>[our list]: <CLASSNAME>_ListData
    our <CLASSNAME>:   crntRecord
}
'''

    CODE = CODE.replace('<NEWSTRUCTNAME>', newStructName)
    CODE = CODE.replace('<CLASSNAME>', className)
    CODE = CODE.replace('<NEWWIDGETFIELDS>', newWidgetFields)
    CODE = CODE.replace('<WIDGETFROMVARSCODE>', widgetFromVarsCode)
    CODE = CODE.replace('<VARSFROMWIDGETCODE>', varsFromWidgetCode)
    #print '==========================================================\n'+CODE
    codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, newStructName)

def BuildGuiForStruct(classes, className, dialogStyle, newStructName):
    # This makes 4 types of changes to the class:
    #   It adds a widget variable for items in model // newWidgetFields: '    their '+typeName+': '+widgetName
    #   It adds a set Widget from Vars function      // widgetFromVarsCode: Func UpdateWidgetFromVars()
    #   It adds a set Vars from Widget function      // varsFromWidgetCode: Func UpdateVarsFromWidget()
    #   It add an initialize Widgets function.       // widgetInitFuncCode: widgetName+' <- '+makeTypeNameCall+'\n    addToContainer(box, '+widgetName+')\n'

    # dialogStyles: 'Z_stack', 'X_stack', 'Y_stack', 'TabbedStack', 'FlowStack', 'WizardStack', 'Dialog', 'SectionedDialogStack', 'V_viewable'
    # also, handle non-modal dialogs
    global classesEncoded
    global currentClassName
    global currentModelSpec
    classesEncoded[className]=1
    currentClassName = className

    # reset the string vars that accumulate the code
    global newWidgetFields
    global widgetInitFuncCode
    global widgetFromVarsCode
    global varsFromWidgetCode

    newWidgetFields    = ''
    widgetInitFuncCode = ''
    widgetFromVarsCode = ''
    varsFromWidgetCode = ''
    containerWidget    = ''
    boxFooterCode      = ''
    makeBoxFooter      = False
    makeBackBtn        = False
    makeNextBtn        = False

    # Find the model
    modelRef         = findModelRef(classes[0], className)
    currentModelSpec = modelRef
    classPrimaryGuiItem=progSpec.searchATagStore(modelRef['tags'], 'primaryGuiItem')
    if classPrimaryGuiItem != None: # This GUI Item is important visually
        classPrimaryGuiItem = classPrimaryGuiItem[0]
    guiStyleTag=progSpec.searchATagStore(modelRef['tags'], 'dialogStyle')
    if guiStyleTag != None: # This GUI Item is important visually
        guiStyleTag = guiStyleTag[0]
        if guiStyleTag == 'WizardStack': dialogStyle = 'WizardStack'
        if guiStyleTag == 'Z_stack':     dialogStyle = 'Z_stack'
        if guiStyleTag == 'WizardChild': 
            dialogStyle    = 'WizardChild'
            makeBoxFooter  = True
            makeBackBtn    = True
            makeNextBtn    = True
            clickNextLabel = "Next"
        if guiStyleTag == 'WizardChildLast':
            dialogStyle    = 'WizardChild'
            makeBoxFooter  = True
            makeBackBtn    = True
            makeNextBtn    = True
            clickNextLabel = "Done" 
        if guiStyleTag == 'WizardChildFirst':
            dialogStyle    = 'WizardChild'
            makeBoxFooter  = True
            makeNextBtn    = True
            clickNextLabel = "Next" 

    ### Write code for each field
    for field in modelRef['fields']:
        typeSpec     = field['typeSpec']
        fldCat       = progSpec.fieldsTypeCategory(typeSpec)
        fieldName    = field['fieldName']
        labelText    = deCamelCase(fieldName)
        if fieldName=='settings':
            # add settings
            continue

        structTypeName=''
        if fldCat=='struct': # Add a new class to be processed
            structTypeName =typeSpec['fieldType'][0]
            if (progSpec.doesClassDirectlyImlementThisField(classes, structTypeName, structTypeName+':managedWidget')
                    or structTypeName.endswith('Widget')):
                fldCat = 'widget'
            else:
                newGUIStyle    = 'Dialog'
                guiStructName  = structTypeName+'_'+newGUIStyle+'_GUI'
                addNewStructToProcess(guiStructName, structTypeName, 'struct', 'Dialog')

        if fldCat != 'widget' and progSpec.isAContainer(typeSpec):# Add a new list to be processed
            structTypeName = typeSpec['fieldType'][0]
            guiStructName  = structTypeName+'_LIST_View'
            addNewStructToProcess(guiStructName, structTypeName, 'list', 'Dialog')

        #TODO: make actions for each function
        if fldCat=='func':
            if fieldName[-4:]== '_btn':
                buttonLabel = deCamelCase(fieldName[:-4])
                # Add a button whose click calls this.
                print 'ADDING BUTTON FOR:', fieldName
                getButtonHandlingCode(classes, buttonLabel, fieldName)

        else: # Here is the main case where code to edit this field is written
            getWidgetHandlingCode(classes, fldCat, fieldName, field, structTypeName, dialogStyle, classPrimaryGuiItem, '')

    # Parse everything
    initFuncName        = 'make'+className[0].upper() + className[1:]+'Widget'
    retrunCode          = 'return(box)'
    if dialogStyle   == 'Z_stack':     
        newWidgetFields   += '    their GUI_ZStack: Zbox\n'
        newWidgetFields   += '    me string[list]: children\n'
        newWidgetFields   += '    me int: activeScreenIdx <-1\n'
        newWidgetFields   += '    void: setActiveChild(me int: N) <- {\n'
        newWidgetFields   += '        if (N >= 0 and N < children.size()){'
        newWidgetFields   += '            me string: childName <- children[N]\n'
        #newWidgetFields   += '            print("^^^setZStackActive: ",N)\n'
        newWidgetFields   += '            setZStackActive(Zbox, childName)\n'
        newWidgetFields   += '        }\n'
        newWidgetFields   += '    }\n'
        containerWidget    = 'Zbox <- makeZStack("'+className+'")\n'
        retrunCode         = '    setActiveChild(0)\n'
        retrunCode        += '    return(Zbox)\n'
        # addToContainer or 
    elif dialogStyle == 'TabbedStack': containerWidget='their GUI_Frame:box <- makeTabbedWidget("makeTabbedWidget")'
    elif dialogStyle == 'WizardStack':
        newWidgetFields    += '    our wizardWidget: wiz\n'
        newWidgetFields    += '    their GUI_Frame: box\n'
        newWidgetFields    += '''    void: clickNext() <-{
            me int: size <- wiz.children.size()
            if (wiz.activeScreenIdx == size-1){
                _data.wizardFinished(wiz.widgetID)
            }
            else if (wiz.activeScreenIdx < size-1){
                wiz.activeScreenIdx <- wiz.activeScreenIdx+1
                wiz.setActiveChild(wiz.activeScreenIdx)
            }
        }\n'''
        newWidgetFields    += '''    void: clickBack() <-{
            me int: size <- wiz.children.size()
	        if (wiz.activeScreenIdx > 0){wiz.activeScreenIdx <- wiz.activeScreenIdx-1}
            wiz.setActiveChild(wiz.activeScreenIdx)
        }\n'''
        containerWidget     = 'Allocate(wiz)\n'
        containerWidget    += '        box <- wiz.makeWizardWidget("'+currentClassName+'")\n'
        containerWidget    += '        wiz._data <- _data\n'
        containerWidget    += '        wiz.parentGuiMgr <- self\n'
        widgetInitFuncCode += '        wiz.setActiveChild(0)\n'
    else: 
        newWidgetFields    += '    their GUI_Frame:box\n'
        containerWidget     ='box <- makeYStack("")'
    if makeBoxFooter:
        newWidgetFields    += '    their GUI_Frame:  boxFooter\n'
        boxFooterCode      += '        boxFooter       <- makeXStack("")\n'
        if makeBackBtn:
            newWidgetFields    += '    their GUI_button: backBtn\n'
            newWidgetFields    += '    void: clickBack() <-{parentGuiMgr.clickBack()}\n'
            boxFooterCode      += '        backBtn         <- makeButtonWidget("Back")\n'
            boxFooterCode      += '        GUI.setBtnCallback(backBtn, "clicked", clickBack, this)\n'
            boxFooterCode      += '        addToContainer(boxFooter, backBtn)\n'
        if makeNextBtn:
            newWidgetFields    += '    their GUI_button: nextBtn\n'
            #newWidgetFields    += '    void: clickNext() <-{parentGuiMgr.clickNext()}\n'
            newWidgetFields    += '    void: clickNext() <-{if(isComplete()){parentGuiMgr.clickNext()}}\n'
            boxFooterCode      += '        nextBtn         <- makeButtonWidget("'+clickNextLabel+'")\n'
            boxFooterCode      += '        GUI.setBtnCallback(nextBtn, "clicked", clickNext, this)\n'
            boxFooterCode      += '        addToContainer(boxFooter, nextBtn)\n'   
        boxFooterCode      += '        addToContainer(box, boxFooter)\n'

    CODE =  '''
struct <CLASSNAME>:inherits=appComponentData{}
struct <NEWSTRUCTNAME>:inherits=appComponentGUI{
    <NEWWIDGETFIELDS>
    our <CLASSNAME>: _data
    their GUI_Frame: <INITFUNCNAME>(our <CLASSNAME>: Data) <- {
        _data <- Data
        _data.guiMgr <- self
        <CONTAINERWIDGET>
        <WIDGETINITFUNCCODE>
        '''+boxFooterCode+'''
        <RETURNCODE>
    }
    void: setValue(our <CLASSNAME>: var) <- {
        <WIDGETFROMVARSCODE>
    }
    void: getValue() <- {
        <VARSFROMWIDGETCODE>
    }
}\n'''  # TODO: add <VARSFROMWIDGETCODE>

    CODE = CODE.replace('<NEWSTRUCTNAME>', newStructName)
    CODE = CODE.replace('<NEWWIDGETFIELDS>', newWidgetFields)
    CODE = CODE.replace('<CLASSNAME>', className)
    CODE = CODE.replace('<WIDGETINITFUNCCODE>', widgetInitFuncCode)
    CODE = CODE.replace('<INITFUNCNAME>', initFuncName)
    CODE = CODE.replace('<WIDGETFROMVARSCODE>', widgetFromVarsCode)
    CODE = CODE.replace('<VARSFROMWIDGETCODE>', varsFromWidgetCode)
    CODE = CODE.replace('<CONTAINERWIDGET>', containerWidget)
    CODE = CODE.replace('<RETURNCODE>', retrunCode)
    #print '==========================================================\n'+CODE
    codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, newStructName)

def apply(classes, tags, topClassName):
    print 'APPLY: in Apply\n'
    global classesToProcess
    global classesEncoded
    classesEncoded={}

    # Choose an appropriate app style
    appStyle='default'
    topWhichScreenFieldID = topClassName+'::whichScreen(int)'
    if (progSpec.doesClassDirectlyImlementThisField(classes[0], topClassName, topWhichScreenFieldID)): # if all data fields are classes
        appStyle='Z_stack'
    else: appStyle='TabbedStack'
    guiStructName = topClassName+'_GUI'
    classesEncoded[guiStructName]=1
    classesToProcess=[[topClassName, 'struct', appStyle, guiStructName]]

    # Amend items to each GUI data class
    for classToAmend in classesToProcess:
        [className, widgetType, dialogStyle, newStructName] = classToAmend
        cdlog(1, 'BUILDING '+dialogStyle+' GUI for '+widgetType+' ' + className + ' ('+newStructName+')')
        if widgetType == 'struct':
            BuildGuiForStruct(classes, className, dialogStyle, newStructName)
        elif widgetType == 'list':
            BuildGuiForList(classes, className, dialogStyle, newStructName)

    # Fill createAppArea()
    primaryGUIName = 'primary_GUI_Mgr'
    primaryMakerFuncName = 'make'+topClassName[0].upper() + topClassName[1:]+'Widget'

    CODE ='''
struct APP{
    our <TOPCLASSNAME>: primary
    our <GUI_STRUCTNAME>: <PRIMARY_GUI>
    me void: createAppArea(me GUI_Frame: frame) <- {
        Allocate(primary)
        Allocate(<PRIMARY_GUI>)
        their GUI_storyBoard: appStoryBoard <- <PRIMARY_GUI>.<PRIMARY_MAKERFUNCNAME>(primary)
        initializeAppGui()
        gui.addToContainerAndExpand (frame, appStoryBoard)
    }
}'''

    CODE = CODE.replace('<PRIMARY_GUI>', primaryGUIName)
    CODE = CODE.replace('<TOPCLASSNAME>', topClassName)
    CODE = CODE.replace('<GUI_STRUCTNAME>', guiStructName)
    CODE = CODE.replace('<PRIMARY_MAKERFUNCNAME>', primaryMakerFuncName)
    #print '==========================================================\n'+CODE
    codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, 'APP')

    return
