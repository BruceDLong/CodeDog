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
    if not(guiStructName in classesEncoded)and not(structTypeName=='DateValue' or structTypeName=='Agreement' or structTypeName=='timeOfDay' or structTypeName=='DateTime' or structTypeName=='matterTerm' or structTypeName=='MedItemData' or structTypeName=='MedData'):
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

def getListWidgetMgrCode(classes, listManagerStructName, rowTypeName, fieldName, classOptionsTags):
    # New listWidgetMgr code generator
    # Find the model
    rowWidgetName = rowTypeName + 'Widget'
    listWidgetStyle = progSpec.fetchTagValue([classOptionsTags], fieldName+'.style.widgetStyle')
    if listWidgetStyle == None: listWidgetStyle = 'simpleList'
    modelRef = progSpec.findSpecOf(classes[0], rowWidgetName, 'struct')
    if modelRef == None:
        print "modelRef: ", modelRef, rowTypeName
        addNewStructToProcess(rowWidgetName, rowTypeName, 'struct', 'rowWidget')
    filename = './preDynamicTypes/' + listWidgetStyle + '.dog'
    classSpec = progSpec.stringFromFile(filename)
    classSpec = classSpec.replace('<ROW_TYPE>', rowTypeName)
    classSpec = classSpec.replace('<LIST_CLASS_NAME>', listManagerStructName)
    #print '==========================================================\n'+classSpec
    codeDogParser.AddToObjectFromText(classes[0], classes[1], classSpec, rowWidgetName)

def getWidgetHandlingCode(classes, fldCat, fieldName, field, structTypeName, dialogStyle, classPrimaryGuiItem, classOptionsTags, indent):
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
        makeTypeNameCall      =  'Allocate('+widgetName+');\n' + widgetBoxName + ' <- '+ widgetName+'.initWidget("'+label+'")\n'
        makeTypeNameCall     += '        ' + widgetName + '.parentGuiMgr <- self\n'
        widgetFromVarsCode   += '        ' + widgetName+ '.setValue(var.'+ fieldName +')\n'
        varsFromWidgetCode   += '        _data.' + fieldName + ' <- ' + widgetName + '.getValue()\n'
    elif fieldType=='Agreement':
        typeName              = 'AgreeWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = 'Allocate('+widgetName+')\n'
        makeTypeNameCall     += '        ' + widgetBoxName + ' <- '+ widgetName+'.initWidget("'+fieldName+'")\n'
        makeTypeNameCall     += '        ' + widgetName + '.parentGuiMgr <- self\n'
        widgetFromVarsCode   += ''
        varsFromWidgetCode   += ''
    elif fieldType=='DateValue':
        typeName              = 'DateWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = 'Allocate('+widgetName+')\n'
        makeTypeNameCall     += '        ' + widgetBoxName + ' <- '+ widgetName+'.initCrnt("'+label+'")\n'
        makeTypeNameCall     += '        ' + widgetName + '.parentGuiMgr <- self\n'
        widgetFromVarsCode   += ''
        varsFromWidgetCode   += '        '+widgetName+'.getValue()\n'
    elif fieldType=='timeOfDay':
        typeName              = 'TimeWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = 'Allocate('+widgetName+')\n'
        makeTypeNameCall     += '        ' + widgetBoxName + ' <- '+ widgetName+'.initCrnt("'+label+'")\n'
        makeTypeNameCall     += '        ' + widgetName + '.parentGuiMgr <- self\n'
        widgetFromVarsCode   += ''
        varsFromWidgetCode   += '        '+widgetName+'.getValue()\n'
    elif fieldType=='DateTime':
        typeName              = 'DateTimeWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = 'Allocate('+widgetName+')\n'
        makeTypeNameCall     += '        ' + widgetBoxName + ' <- '+ widgetName+'.initCrnt("'+label+'")\n'
        makeTypeNameCall     += '        ' + widgetName + '.parentGuiMgr <- self\n'
        widgetFromVarsCode   += ''
        varsFromWidgetCode   += '        '+widgetName+'.getValue()\n'
    elif fieldType=='FoodData':
        typeName              = 'FoodDataWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = 'Allocate('+widgetName+')\n'
        makeTypeNameCall     += '        ' + widgetBoxName + ' <- '+ widgetName+'.initWidget("'+label+'", _data.'+fieldName+')\n'
        #widgetFromVarsCode   += '        '+widgetName+'.setValue(var.'+ fieldName +')\n'
        #varsFromWidgetCode   += '        '+widgetName+'.getValue()\n'
    elif fieldType=='MedItemData':
        typeName              = 'MedItemDataWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = 'Allocate('+widgetName+')\n'
        makeTypeNameCall     += '        ' + widgetBoxName + ' <- '+ widgetName+'.initWidget("'+label+'", _data.'+fieldName+')\n'
        #widgetFromVarsCode   += '        '+widgetName+'.setValue(var.'+ fieldName +')\n'
        #varsFromWidgetCode   += '        '+widgetName+'.getValue()\n'
    elif fieldType=='MedData':
        typeName              = 'MedBunchDataWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = 'Allocate('+widgetName+')\n'
        makeTypeNameCall     += 'Allocate(_data.'+fieldName+')\n'
        makeTypeNameCall     += '        ' + widgetBoxName + ' <- '+ widgetName+'.initWidget("'+label+'", _data.'+fieldName+')\n'
        #widgetFromVarsCode   += '        '+widgetName+'.setValue(var.'+ fieldName +')\n'
        varsFromWidgetCode   += '        '+widgetName+'.getValue()\n'
    elif fieldType=='matterTerm':
        typeName              = 'MatterTermWidget'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = 'Allocate('+widgetName+')\n'
        makeTypeNameCall     += '        ' + widgetBoxName + ' <- '+ widgetName+'.initWidget("'+label+'", _data.'+fieldName+')\n'
        makeTypeNameCall     += '        ' + widgetName + '.parentGuiMgr <- self\n'
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
            widgetBoxName         = widgetName +'.box'
            localWidgetVarName    = fieldName
            dataType = changeDataFieldType(classes, structTypeName, typeSpec)
            makeTypeNameCall      = 'Allocate('+widgetName+')\n'
            makeTypeNameCall     += '        '+widgetBoxName+' <- '+widgetName+'.initWidget("'+label+'")\n'
            #makeTypeNameCall     += '        ' + widgetName + '.parentGuiMgr <- self\n'
            #widgetFromVarsCode   += '        '+widgetName+'.setValue(var.'+ fieldName +')\n'
            varsFromWidgetCode   += '        _data.' + fieldName + ' <- ' +widgetName+'.getValue()\n'
    elif fieldSpec=='struct':
        typeName              = 'GUI_Frame'
        guiStructName         = structTypeName + '_Dialog_GUI'
        guiMgrName            = fieldType + '_GUI_Mgr'
        if progSpec.typeIsPointer(typeSpec): widgetInitFuncCode += '        Allocate(_data.'+fieldName+')\n'
        widgetInitFuncCode   += 'Allocate('+guiMgrName+')\n'
        makeTypeNameCall      = widgetName+' <- '+guiMgrName+'.initWidget(_data.'+fieldName+')\n'
        makeTypeNameCall     += '        ' + guiMgrName + '.parentGuiMgr <- self\n'
        newWidgetFields      += '    our ' + guiStructName + ': '+ guiMgrName+'\n'
        widgetFromVarsCode   += '        ' + guiMgrName+ '.setValue(var.'+fieldName+')\n'
        varsFromWidgetCode   += '        ' + guiMgrName + '.getValue()\n'
        makeTypeNameCall     += '        ' + guiMgrName + '.load()\n'
    elif fieldSpec=='enum':
        typeName = 'enumWidget'
        EnumItems=[]
        for enumItem in params: EnumItems.append('"'+deCamelCase(enumItem)+'"')
        optionString          = '[' + ', '.join(EnumItems) + ']'
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = 'Allocate('+widgetName+'); ' + widgetBoxName+' <- '+ widgetName+'.initWidget("'+label+'", '+optionString+')\n'
        makeTypeNameCall     += '        ' + widgetName + '.parentGuiMgr <- self\n'
        widgetFromVarsCode   += '        ' + widgetName+ '.setValue(var.'+ fieldName +')\n'
        varsFromWidgetCode   += '        _data.' + fieldName + ' <- ' + widgetName + '.getValue()\n'
    elif fieldSpec=='string':
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      = 'Allocate('+widgetName+'); ' + widgetBoxName + ' <- '+ widgetName+'.initWidget("'+label+'")\n'
        makeTypeNameCall     += '        ' + widgetName + '.parentGuiMgr <- self\n'
        widgetFromVarsCode   += '        ' + widgetName+ '.setValue(var.'+ fieldName +')\n'
        varsFromWidgetCode   += '        _data.' + fieldName + ' <- ' + widgetName + '.getValue()\n'
    elif fieldSpec=='int':
        widgetBoxName         = widgetName +'.box'
        makeTypeNameCall      = 'Allocate('+widgetName+')\n'
        makeTypeNameCall     += '        ' + widgetName + '.parentGuiMgr <- self\n'
        if progSpec.typeIsNumRange(innerFieldType):
            typeName = 'intRangeWidget'
            range1 = innerFieldType[0]
            range2 = innerFieldType[2]
            makeTypeNameCall += '        '+widgetName+'.minValue <- '+range1+'\n        '+widgetName+'.maxValue <- '+range2+'\n'
            makeTypeNameCall += '        '+widgetBoxName+' <- '+ widgetName+'.initWidget("'+label+'")\n'
        else:
            makeTypeNameCall += '        '+widgetBoxName+' <- '+widgetName+'.initWidget("'+label+'")\n'
        widgetFromVarsCode   += '        '+widgetName+'.setValue(var.'+ fieldName +')\n'
        varsFromWidgetCode   += '        _data.'+fieldName+' <- '+widgetName+'.getValue()\n'
    elif fieldSpec=='bool':
        widgetBoxName         =  widgetName +'.box'
        makeTypeNameCall      =  'Allocate('+widgetName+'); ' + widgetBoxName + ' <- '+ widgetName+'.initWidget("'+label+'")\n'
        makeTypeNameCall     += '        ' + widgetName + '.parentGuiMgr <- self\n'
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
        getListWidgetMgrCode(classes, listManagerStructName, structTypeName, fieldName, classOptionsTags)

        listWidMgrName        = 'LEWM'
        newWidgetFields      += '    me '+listManagerStructName+': '+listWidMgrName+'\n'

        widgetListEditorName  = widgetName+'_Editor'
        localWidgetVarName    = widgetListEditorName
        if progSpec.typeIsPointer(typeSpec): widgetInitFuncCode += 'Allocate(_data.'+fieldName+')\n'
        widgetInitFuncCode   += '        their GUI_YStack: '+widgetListEditorName+' <- '+listWidMgrName+'.initWidget(_data.'+fieldName+', "'+fieldName+'")\n'
        if classPrimaryGuiItem==fieldName: widgetInitFuncCode   += '        addToContainerAndExpand(box, '+widgetListEditorName+')\n'
        else: widgetInitFuncCode   += '        addToContainer(box, '+widgetListEditorName+')\n'
#        widgetFromVarsCode   += '        ' + listWidMgrName + '.setValue(var.'+ fieldName +')\n'
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
        else: widgetInitFuncCode   += '        addToContainerAndExpand(box, '+widgetBoxName+')\n'
    if dialogStyle == 'TabbedStack':
        widgetInitFuncCode+='             '+'setTabLabelText(box, '+ localWidgetVarName+', "'+label+'")\n'

def buildListRowView(classes, className, dialogStyle, newStructName):
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
    funcTextToUpdateViewWidget= ''
    funcTextToUpdateEditWidget= ''
    funcTextToUpdateCrntFromWidget= ''

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
            guiStructName  = structTypeName+'_ROW_View'
            addNewStructToProcess(guiStructName, structTypeName, 'list', 'Dialog')
        else:
            print "field::", fieldName, fldCat
            if(fldCat!='struct'):
                rowHeaderCode   += '        their GUI_Label: '+fieldName + '_header <- makeLabelWidget("'+fieldName+'")\n'
                rowHeaderCode   += '        setLabelWidth('+fieldName+'_header, 15)\n'
                rowHeaderCode   += '        addToContainer(headerBox, '+fieldName+'_header)\n'
            if fldCat=='struct':
                funcTextToUpdateViewWidget     += ''
            elif fldCat=='enum' or fldCat=='mode':
                funcTextToUpdateViewWidget     += ''
                #funcTextToUpdateEditWidget     += ''
                funcTextToUpdateCrntFromWidget += ''#  crntRecord.'+fieldName+' <- dialog.' + widgetName + '.getValue()\n'
            elif fldCat=='bool':
                funcTextToUpdateViewWidget     += ''
            elif fldCat=='string':
                #funcTextToUpdateViewWidget     += ''
                #funcTextToUpdateEditWidget     += '    dialog.' + widgetName + '.setValue('+structTypeName+'_ListData[N].'+fieldName+')\n'
                #funcTextToUpdateCrntFromWidget += '    me string: '+widgetName+'Str <- dialog.' + widgetName + '.getValue()\n'
                #funcTextToUpdateCrntFromWidget += '    crntRecord.'+fieldName+' <- '+widgetName+'Str\n'
                rowViewCode                    += '        their GUI_Label: '+fieldName + '_value <- makeLabelWidget2(Data.'+fieldName+')\n'
                rowViewCode                    += '        setLabelWidth('+fieldName+'_value, 15)\n'
                rowViewCode                    += '        addToContainer(box, '+fieldName+'_value)\n'
                rowViewCode                    += '        showWidget('+fieldName+'_value)\n'
            elif fldCat=='int':
                funcTextToUpdateViewWidget     += ''
                #funcTextToUpdateEditWidget     += '    dialog.' + widgetName + '.setValue('+structTypeName+'_ListData[N].'+fieldName+')\n'
                #funcTextToUpdateCrntFromWidget += '    me string: '+widgetName+'Str <- string(dialog.' + widgetName + '.getValue())\n'
                #funcTextToUpdateCrntFromWidget += '    crntRecord.'+fieldName+' <- dataStr\n'
                rowViewCode                    += '        their GUI_Label: '+fieldName + '_value <- makeLabelWidget2(toString(Data.'+fieldName+'))\n'
                rowViewCode                    += '        setLabelWidth('+fieldName+'_value, 15)\n'
                rowViewCode                    += '        addToContainer(box, '+fieldName+'_value)\n'
                rowViewCode                    += '        showWidget('+fieldName+'_value)\n'
            else: print'pattern_MakeGUI.codeListWidgetManagerClassOverride fldCat not specified: ', fldCat;  exit(2)

    CODE =  '''struct '''+newStructName+'''{
    their GUI_Frame:            box
    their GUI_Frame: makeHeaderView() <- {
        their GUI_Frame: headerBox <- makeXStack("")
        '''+rowHeaderCode+'''
        showWidget(headerBox)
        return(headerBox)
    }
    their GUI_Frame: initWidget(our '''+className+''': Data) <- {
        box <- makeXStack("")
        '''+rowViewCode+'''
        showWidget(box)
        return(box)
    }
}
'''
    #print '==========================================================\n'+CODE
    codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, newStructName)

def BuildGuiForStruct(classes, className, dialogStyle, newStructName):
    # This makes 4 types of changes to the class:
    #   It adds a widget variable for items in model // newWidgetFields: '    their '+typeName+': '+widgetName
    #   It adds a set Widget from Vars function      // widgetFromVarsCode: Func setValue()
    #   It adds a set Vars from Widget function      // varsFromWidgetCode: Func getValue()
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
    scrollerCode       = ''
    onLoadedCode       = ''
    tagCode            = ''
    makeBoxFooter      = False
    makeBackBtn        = False
    makeNextBtn        = False
    makeVScroller      = False

    # Find the model
    modelRef         = findModelRef(classes[0], className)
    currentModelSpec = modelRef
    classPrimaryGuiItem=progSpec.searchATagStore(modelRef['tags'], 'primaryGuiItem')
    if classPrimaryGuiItem != None: # This GUI Item is important visually
        classPrimaryGuiItem = classPrimaryGuiItem[0]
    classOptionsTags=progSpec.searchATagStore(modelRef['tags'], 'classOptions')
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
    classProperties = progSpec.searchATagStore(modelRef['tags'], 'properties')
    if classProperties != None:
        for classProperty in classProperties:
            if classProperty[0] == 'vScroller': makeVScroller = True
    ### Write code for each field
    for field in modelRef['fields']:
        typeSpec     = field['typeSpec']
        fldCat       = progSpec.fieldsTypeCategory(typeSpec)
        fieldName    = field['fieldName']
        labelText    = deCamelCase(fieldName)
        fieldType    = typeSpec['fieldType']
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
            if not isinstance(fieldType, basestring): fieldType=fieldType[0]
            structTypeName = fieldType
            guiStructName  = structTypeName+'_ROW_View'
            addNewStructToProcess(guiStructName, structTypeName, 'list', 'Dialog')

        #TODO: make actions for each function
        if fldCat=='func':
            if fieldName[-4:]== '_btn':
                buttonLabel = deCamelCase(fieldName[:-4])
                # Add a button whose click calls this.
                print 'ADDING BUTTON FOR:', fieldName
                getButtonHandlingCode(classes, buttonLabel, fieldName)

        else: # Here is the main case where code to edit this field is written
            getWidgetHandlingCode(classes, fldCat, fieldName, field, structTypeName, dialogStyle, classPrimaryGuiItem, classOptionsTags, '')

    onLoadedCode           = 'onLoaded()\n'
    returnCode             = '        return(box)'
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
        onLoadedCode       = 'setActiveChild(0)\n'
        onLoadedCode      += '        onLoaded()\n'
        returnCode         = '        return(Zbox)\n'
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
        containerWidget    += '        box <- wiz.initWidget("'+currentClassName+'")\n'
        containerWidget    += '        wiz._data <- _data\n'
        containerWidget    += '        wiz.parentGuiMgr <- self\n'
        widgetInitFuncCode += '        wiz.activeScreenIdx <- 0\n'
        widgetInitFuncCode += '        wiz.setActiveChild(wiz.activeScreenIdx)\n'
    elif dialogStyle   == 'X_stack':
        newWidgetFields    += '    their GUI_XStack:box\n'
        containerWidget     ='box <- makeXStack("")'
    elif dialogStyle   == 'rowWidget':
        newWidgetFields    += '    their GUI_XStack: box\n'
        containerWidget     ='box <- makeXStack("")'
    else:
        newWidgetFields    += '    their GUI_Frame:box\n'
        containerWidget     ='box <- makeYStack("")'
    if makeBoxFooter:
        newWidgetFields    += '    their GUI_Frame:  boxFooter\n'
        boxFooterCode      += 'boxFooter       <- makeXStack("")\n'
        if makeBackBtn:
            newWidgetFields    += '    their GUI_button: backBtn\n'
            newWidgetFields    += '    void: clickBack() <-{parentGuiMgr.clickBack()}\n'
            boxFooterCode      += '        backBtn         <- makeButtonWidget("Back")\n'
            boxFooterCode      += '        GUI.setBtnCallback(backBtn, "clicked", clickBack, this)\n'
            boxFooterCode      += '        addToContainer(boxFooter, backBtn)\n'
        if makeNextBtn:
            newWidgetFields    += '    their GUI_button: nextBtn\n'
            newWidgetFields    += '''    void: clickNext() <-{
                if(isComplete()){
                    save()
                    parentGuiMgr.clickNext()
                }
            }\n'''
            newWidgetFields    += '''    void: setNextBtnActive(me bool: checkState) <-{
                nextBtn.setWidgetActive(checkState)
            }\n'''
            newWidgetFields    += '''    void: onChanged() <- {
                getValue()
                setNextBtnActive(isComplete())
            }\n'''
            boxFooterCode      += '        nextBtn         <- makeButtonWidget("'+clickNextLabel+'")\n'
            boxFooterCode      += '        nextBtn.setWidgetActive(false)\n'
            boxFooterCode      += '        GUI.setBtnCallback(nextBtn, "clicked", clickNext, this)\n'
            boxFooterCode      += '        addToContainer(boxFooter, nextBtn)\n'
        boxFooterCode      += '        addToContainer(box, boxFooter)\n'
    if makeVScroller:
        scrollerCode  = 'their GUI_VerticalScroller: scroller <- makeVerticalScroller()\n'
        scrollerCode += 'addToContainerAndExpand(scroller, box)\n'
        returnCode    = 'return (scroller)'

    CODE =  '''
struct <CLASSNAME>:inherits=appComponentData{}
struct <NEWSTRUCTNAME>:inherits=appComponentGUI '''+tagCode+'''{
    '''+newWidgetFields+'''
    our <CLASSNAME>: _data
    their GUI_Frame: initWidget(our <CLASSNAME>: Data) <- {
        _data <- Data
        _data.guiMgr <- self
        '''+containerWidget+'''
        '''+widgetInitFuncCode+'''
        '''+boxFooterCode+'''
        '''+scrollerCode+'''
        '''+onLoadedCode+'''
        '''+returnCode+'''
    }
    void: setValue(our <CLASSNAME>: var) <- {
        '''+widgetFromVarsCode+'''
    }
    void: getValue() <- {
        '''+varsFromWidgetCode+'''
    }
}\n'''  # TODO: add <VARSFROMWIDGETCODE>

    CODE = CODE.replace('<NEWSTRUCTNAME>', newStructName)
    CODE = CODE.replace('<CLASSNAME>', className)
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
        #elif widgetType == 'list':
            #buildListRowView(classes, className, dialogStyle, newStructName)

    # Fill createAppArea()
    primaryGUIName = 'primary_GUI_Mgr'

    CODE ='''
struct APP{
    our '''+topClassName+''': primary
    our '''+guiStructName+''': <PRIMARY_GUI>
    me void: createAppArea(me GUI_Frame: frame) <- {
        Allocate(primary)
        Allocate(<PRIMARY_GUI>)
        their GUI_storyBoard: appStoryBoard <- <PRIMARY_GUI>.initWidget(primary)
        initializeAppGui()
        gui.addToContainerAndExpand (frame, appStoryBoard)
    }
}'''

    CODE = CODE.replace('<PRIMARY_GUI>', primaryGUIName)
    #print '==========================================================\n'+CODE
    codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, 'APP')

    return
