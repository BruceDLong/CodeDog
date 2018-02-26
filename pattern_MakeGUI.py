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

def getFieldSpec(fldCat, field):
    parameters={}
    if fldCat=='mode': fldCat='enum'
    elif fldCat=='double': fldCat='float'

    if fldCat=='enum':
        parameters=field['typeSpec']['enumList']
    elif fldCat=='RANGE':
        parameters={1, 10}

    typeSpec=field['typeSpec']
    if 'arraySpec' in typeSpec and typeSpec['arraySpec']!=None:
        innerFieldType=typeSpec['fieldType']
        datastructID = typeSpec['arraySpec']['datastructID']
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

def codeListWidgetManagerClassOverride(classes, listManagerStructName, structTypeName):
    funcTextToUpdateViewWidget=''
    funcTextToUpdateEditWidget=''
    funcTextToUpdateCrntFromWidget=''

    # Find the model
    modelRef = progSpec.findSpecOf(classes[0], structTypeName, 'model')
    currentModelSpec = modelRef
    if modelRef==None:
        cdErr('To build a list GUI for list of "'+structTypeName+'" a model is needed but is not found.')

    ### Write code for each field
    fieldIdx=0
    for field in modelRef['fields']:
        fieldIdx+=1
        typeSpec=field['typeSpec']
        fldCat=progSpec.fieldsTypeCategory(typeSpec)
        fieldName=field['fieldName']
        label = deCamelCase(fieldName)
        CasedFieldName = fieldName[0].upper() + fieldName[1:]
        widgetFieldName = CasedFieldName + 'Widget'

        if not ('arraySpec' in typeSpec and typeSpec['arraySpec']!=None):
            if fldCat=='struct':
                funcTextToUpdateViewWidget     += ''
                funcTextToUpdateEditWidget     += '   /- updateWidgetFromVars()\n'
                funcTextToUpdateCrntFromWidget += '   /- updateVarsFromWidget()\n'
            elif fldCat=='enum' or fldCat=='mode':
                funcTextToUpdateViewWidget     += ''
                funcTextToUpdateEditWidget     += ''
                funcTextToUpdateCrntFromWidget += '    crntRecord.'+fieldName+' <- dialog.' + widgetFieldName + '.getValue()\n'
            elif fldCat=='bool':
                funcTextToUpdateViewWidget     += ''
                funcTextToUpdateEditWidget     += ''
                funcTextToUpdateCrntFromWidget += '    crntRecord.'+fieldName+' <- dialog.' + widgetFieldName + '.getValue()\n'
            else:
                funcTextToUpdateViewWidget     += ''
                funcTextToUpdateEditWidget     += '    dialog.' + widgetFieldName + '.setValue(crntRecord.'+fieldName+')\n'
                funcTextToUpdateCrntFromWidget += '    crntRecord.'+fieldName+' <- dialog.' + widgetFieldName + '.getValue()\n'
                funcTextToUpdateCrntFromWidget += '    pushCrntToList()\n'


###############
    CODE = 'struct '+listManagerStructName+''': inherits = "ListWidgetManager" {
    /-me ListEditorWidget: LEW
    our <STRUCTNAME>: crntRecord
    our <STRUCTNAME>[their list]: <STRUCTNAME>_ListData
    me <STRUCTNAME>_Dialog_GUI: dialog
    their <STRUCTNAME>_LIST_View: <STRUCTNAME>_listView
    /- Override all these for each new list editing widget
    their GUI_item: makeListViewWidget() <- {
        their GUI_Frame: box <- makeFrameWidget()
        Allocate(<STRUCTNAME>_listView)
        their GUI_Frame: listBox <- <STRUCTNAME>_listView.makeListWidget(<STRUCTNAME>_ListData)
        addToContainer(box, listBox)
        return(box)
    }
    void: updateViewableWidget(their GUI_item: Wid) <- {<funcTextToUpdateViewWidget>}
    their GUI_item: makeEditableWidget() <- {
        their GUI_item: ret <- dialog.make<STRUCTNAME>Widget(crntRecord)
        return(ret)
    }
    void: updateEditableWidget(their GUI_item: Wid) <- {<funcTextToUpdateEditWidget>}
    void: updateCrntFromEdited(their GUI_item: Wid) <- {<funcTextToUpdateCrntFromWidget>}
    void: allocateNewCurrentItem() <- {Allocate(crntRecord)}
    void: pushCrntToList() <- {} /-grandParent.<STRUCTNAME>.pushLast(crntRecord)}
    void: deleteNthItem(me int: N) <- {}
    void: copyCrntBackToList() <- {}

    their GUI_item: initWidget(our <STRUCTNAME>[their list]: Data) <- {
        <STRUCTNAME>_ListData <- Data
        return(LEW.init_dialog(self))
    }
}
'''
    CODE = CODE.replace('<STRUCTNAME>', structTypeName)
    CODE = CODE.replace('<funcTextToUpdateViewWidget>', funcTextToUpdateViewWidget)
    CODE = CODE.replace('<funcTextToUpdateEditWidget>', funcTextToUpdateEditWidget)
    CODE = CODE.replace('<funcTextToUpdateCrntFromWidget>', funcTextToUpdateCrntFromWidget)
    codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, listManagerStructName)

def getWidgetHandlingCode(classes, fldCat, fieldName, field, structTypeName, indent):
    global newWidgetFields
    global widgetInitFuncCode
    global widgetFromVarsCode
    global varsFromWidgetCode

    label = deCamelCase(fieldName)
    [fieldSpec, params] = getFieldSpec(fldCat, field)
    typeName = fieldSpec+'Widget'
    CasedFieldName = fieldName[0].upper() + fieldName[1:]
    widgetFieldName = CasedFieldName + 'Widget'
    fieldType = field['typeSpec']['fieldType'][0]
    typeSpec=field['typeSpec']

    if fieldSpec=='struct':
        typeName = 'GUI_Frame'
        if progSpec.typeIsPointer(typeSpec): widgetInitFuncCode += indent+'    Allocate('+currentClassName+'_data.'+fieldName+')\n'  +  indent+'    Allocate('+fieldType+'_GUI_Mgr)\n'
        makeTypeNameCall = fieldType+'_GUI_Mgr.make'+structTypeName+'Widget('+currentClassName+'_data.'+fieldName+')'
        newWidgetFields += '\n' + indent+ 'our ' + structTypeName + '_Dialog_GUI: '+ fieldType + '_GUI_Mgr'
    elif fieldSpec=='enum':
        typeName = 'enumWidget'
        EnumItems=[]
        for enumItem in params: EnumItems.append('"'+deCamelCase(enumItem)+'"')
        optionString = '[' + ', '.join(EnumItems) + ']'
        makeTypeNameCall = 'makeEnumWidget("'+label+'", '+optionString+')'
    else:
        makeTypeNameCall = 'make'+typeName[0].upper() + typeName[1:]+'("'+label+'")'
    '''
    if fldCat=='struct':
        pass
    elif fldCat=='mode':
        pass
    else:
        widgetFromVarsCode += indent+'    GUI_Manager.'+widgetFieldName+'.setValue('+fieldName+')\n'
        varsFromWidgetCode += indent+'    '+fieldName+' <- GUI_Manager.'+widgetFieldName+'.getValue()\n'
    '''

    newWidgetFields += '\n'+indent+'    their '+typeName+': '+widgetFieldName
    widgetInitFuncCode += indent+'    '+widgetFieldName+' <- '+makeTypeNameCall+'\n'

    # If this is a list, populate it
    if 'arraySpec' in typeSpec and typeSpec['arraySpec']!=None:
        innerFieldType=typeSpec['fieldType']
        fldCatInner=progSpec.innerTypeCategory(innerFieldType)

        # If it hasn't already been added, make a struct <ItemType>_ListWidgetManager:ListWidgetManager{}
        listManagerStructName = structTypeName+'_ListEditorWidget'
        codeListWidgetManagerClassOverride(classes, listManagerStructName, structTypeName)

        listWidMgrName = widgetFieldName+'_LEWM'
        newWidgetFields += '\n'+indent+'    me '+listManagerStructName+': '+listWidMgrName+'\n'

        widgetListEditorName = widgetFieldName+'Editor'
        if progSpec.typeIsPointer(typeSpec): widgetInitFuncCode += indent+'    Allocate('+currentClassName+'_data.'+fieldName+')\n'
        widgetInitFuncCode += indent+'    their GUI_item: '+widgetListEditorName+' <- '+listWidMgrName+'.initWidget('+currentClassName+'_data.'+fieldName+')\n'
        widgetInitFuncCode += indent+'    addToContainer(box, '+widgetListEditorName+')\n'
   #     widgetInitFuncCode += indent+"    withEach _item in crntRecord."+fieldName+':{\n        addToContainer('+widgetFieldName+', _item.make'+structTypeName+'Widget(s))\n    }\n'

    else: # Not an ArraySpec:
        widgetInitFuncCode += indent+'    addToContainer(box, '+widgetFieldName+')\n'

def BuildGuiForList(classes, className, dialogStyle, newStructName):
    # This makes 4 types of changes to the class:
    #   It adds a widget variable for items in model // newWidgetFields: '    their '+typeName+': '+widgetFieldName
    #   It adds a set Widget from Vars function      // widgetFromVarsCode: Func UpdateWidgetFromVars()
    #   It adds a set Vars from Widget function      // varsFromWidgetCode: Func UpdateVarsFromWidget()
    #   It add an initialize Widgets function.       // widgetInitFuncCode: widgetFieldName+' <- '+makeTypeNameCall+'\n    addToContainer(box, '+widgetFieldName+')\n'

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
    modelRef = progSpec.findSpecOf(classes[0], className, 'model')
    if modelRef==None: cdErr('To build a GUI for a list of "'+className+'" a model is needed but is not found.')
    currentModelSpec = modelRef
    listFields = modelRef['fields']
    listFieldsCode =''
    for field in listFields:
        fieldName =  field['fieldName']
        fieldType =  field['typeSpec']['fieldType']
        fieldType = fieldType[0].upper() + fieldType[1:]
        valueField = 'crntRecord.'+fieldName
        label = deCamelCase(fieldName)
        listFieldsCode += '        their GUI_Frame: '+fieldName+'_label <- makeLabelWidget("'+label+'")\n'
        listFieldsCode += '        addToContainer(row, '+fieldName+'_label)\n'
        listFieldsCode += '        their GUI_Frame: '+fieldName+'_value <- make'+fieldType+'Widget('+valueField+')\n'
        listFieldsCode += '        addToContainer(row, '+fieldName+'_value)\n'
    
    newWidgetFields += '\n\n    our '+className+'[their list]: '+className+'_ListData\n'
    newWidgetFields += '    our '+className+': crntRecord\n'
    listTitle = className+ ' List View!!!'
    #TODO: write func body for: widgetFromVarsCode & varsFromWidgetCode
    makeListWidgetCode =  '\n    their GUI_Frame: '+'makeListWidget'+'(our '+className+'[their list]: Data) <- {\n'
    makeListWidgetCode += '        '+className+'_ListData<-Data\n'
    makeListWidgetCode += '        their listWidget:listWid <- makeLabelWidget("'+listTitle+'")\n' 
    makeListWidgetCode += '        withEach item in '+className+'_ListData:{\n crntRecord <- item\nmakeRowView()\n}\n' 
    makeListWidgetCode += '        return(listWid)\n  }\n'
    makeRowViewFuncCode = '\n  their GUI_Frame: '+'makeRowView'+'() <- {\n'
    makeRowViewFuncCode += '    their GUI_Frame:row <- makeLabelWidget("ROW")\n'
    makeRowViewFuncCode += '\n'+ listFieldsCode
    makeRowViewFuncCode += '    return(row)\n  }\n'
    widgetFromVarsCode += '    void: updateWidgetFromCrnt() <- {\n' + widgetFromVarsCode + '\n    }\n'
    varsFromWidgetCode += '    void: updateCrntFromWidget() <- {\n' + varsFromWidgetCode + '\n    }\n'
    #parentStructFields = '    our ' + newStructName + ': ' + 'GUI_Manager\n'
    #parentStructFields += widgetFromVarsCode + varsFromWidgetCode
    GUI_StructFields   = newWidgetFields + makeListWidgetCode + widgetInitFuncCode + makeRowViewFuncCode
    CODE =  'struct '+newStructName+" {\n" + GUI_StructFields + '\n}\n'         # Add the new fields to the GUI manager struct
    #CODE += 'struct '+className + " {\n" + parentStructFields + '\n}\n'         # Add the new fields to the parent struct
    #print '==========================================================\n'+CODE
    codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, newStructName)


def BuildGuiForStruct(classes, className, dialogStyle, newStructName):
    # This makes 4 types of changes to the class:
    #   It adds a widget variable for items in model // newWidgetFields: '    their '+typeName+': '+widgetFieldName
    #   It adds a set Widget from Vars function      // widgetFromVarsCode: Func UpdateWidgetFromVars()
    #   It adds a set Vars from Widget function      // varsFromWidgetCode: Func UpdateVarsFromWidget()
    #   It add an initialize Widgets function.       // widgetInitFuncCode: widgetFieldName+' <- '+makeTypeNameCall+'\n    addToContainer(box, '+widgetFieldName+')\n'

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
    modelRef = progSpec.findSpecOf(classes[0], className, 'model')
    currentModelSpec = modelRef
    if modelRef==None: cdErr('To build a GUI for class "'+className+'" a model is needed but is not found.')
    #TODO: write func body for: widgetFromVarsCode(selected item & click edit) & varsFromWidgetCode(ckick OK from editMode)
    ### Write code for each field
    fieldIdx=0
    for field in modelRef['fields']:
        fieldIdx+=1
        typeSpec=field['typeSpec']
        fldCat=progSpec.fieldsTypeCategory(typeSpec)
        fieldName=field['fieldName']
        label = deCamelCase(fieldName)
        if fieldName=='settings':
            # add settings
            continue

        structTypeName=''
        if fldCat=='struct': # Add a new class to be processed
            structTypeName=typeSpec['fieldType'][0]
            newGUIStyle = 'Dialog'
            guiStructName = structTypeName+'_'+newGUIStyle+'_GUI'
            if not(guiStructName in classesEncoded):
                classesEncoded[guiStructName]=1
                classesToProcess.append([structTypeName, 'struct', 'Dialog', guiStructName])

        if 'arraySpec' in typeSpec and typeSpec['arraySpec']!=None:# Add a new list to be processed
            structTypeName=typeSpec['fieldType'][0]
            guiStructName = structTypeName+'_LIST_View'
            if not(guiStructName in classesEncoded):
                classesEncoded[guiStructName]=1
                classesToProcess.append([structTypeName, 'list', 'Dialog', guiStructName])

        #TODO: make actions for each function
        if fldCat=='func': continue

        getWidgetHandlingCode(classes, fldCat, fieldName, field, structTypeName, '')

    # Parse everything
    initFuncName = 'make'+className[0].upper() + className[1:]+'Widget'
    if dialogStyle == 'Z_stack': containerWidget='makeStoryBoardWidget("makeStoryBoardWidget")'
    else: containerWidget='makeFrameWidget()'

    newWidgetFields += '\n\n    their '+className+': '+className+'_data\n'

    widgetInitFuncCode = '\n  their GUI_Frame: '+initFuncName+'(their '+className+': Data) <- {\n   '+className+'_data<-Data\n    their GUI_Frame:box <- '+containerWidget+'\n' + widgetInitFuncCode + '\n    return(box)\n  }\n'
    widgetFromVarsCode += ''#    void: updateWidgetFromVars() <- {\n' + widgetFromVarsCode + '\n    }\n'
    varsFromWidgetCode += ''#    void: updateVarsFromWidget() <- {\n' + varsFromWidgetCode + '\n    }\n'
    parentStructFields = widgetFromVarsCode + varsFromWidgetCode
    GUI_StructFields   = newWidgetFields + widgetInitFuncCode
    CODE =  'struct '+newStructName+" {\n" + GUI_StructFields + '\n}\n'         # Add the new fields to the GUI manager struct
    CODE += 'struct '+className + " {\n" + parentStructFields + '\n}\n'         # Add the new fields to the parent struct
    #print '==========================================================\n'+CODE
    codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, newStructName)


def apply(classes, tags, topClassName):
    print "APPLY: in Apply\n"
    global classesToProcess
    global classesEncoded
    classesEncoded={}

    # Choose an appropriate app style
    appStype='default'
    if (True): # if all data fields are classes
        appStype='Z_stack'
    guiStructName = topClassName+'_GUI'
    classesEncoded[guiStructName]=1
    classesToProcess=[[topClassName, 'struct', appStype, guiStructName]]

    # Amend items to each GUI data class
    for classToAmend in classesToProcess:
        className    = classToAmend[0]
        widgetType   = classToAmend[1]
        dialogStyle  = classToAmend[2]
        newStructName= classToAmend[3]
        cdlog(2, "BUILDING "+dialogStyle+" GUI for "+widgetType+" " + className + ' ('+newStructName+')')
        if widgetType == 'struct':
            BuildGuiForStruct(classes, className, dialogStyle, newStructName)
        elif widgetType == 'list':
            BuildGuiForList(classes, className, dialogStyle, newStructName)


    # Fill createAppArea()
    primaryGUIName = 'primary_GUI_Mgr'
    primaryMakerFuncName = 'make'+topClassName[0].upper() + topClassName[1:]+'Widget'
    declAPP_fields = '  their '+topClassName+': primary\n'
    declAPP_fields += '  our ' + guiStructName+': ' + primaryGUIName + '\n'
    declAPP_fields+='''
    me void: createAppArea(me GUI_Frame: frame) <- {
        me string:s
        Allocate(primary)
        Allocate(<PRIMARY_GUI>)
        their GUI_storyBoard: appStoryBoard <- <PRIMARY_GUI>.'''+primaryMakerFuncName+'''(primary)
        gui.addToContainerAndExpand (frame, appStoryBoard)
    }
'''
    declAPP_fields = declAPP_fields.replace('<PRIMARY_GUI>', primaryGUIName)
    CODE = progSpec.wrapFieldListInObjectDef('APP', declAPP_fields)
    codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, 'APP')

    return
