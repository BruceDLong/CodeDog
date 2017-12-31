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
    params={}
    if fldCat=='mode': fldCat='enum'
    elif fldCat=='double': fldCat='float'

    if fldCat=='enum': parameters={'mon', 'tue', 'wed', 'thur', 'fri', 'sat', 'sun'}
    elif fldCat=='RANGE': pareameters={1, 10}

    typeSpec=field['typeSpec']
    if 'arraySpec' in typeSpec and typeSpec['arraySpec']!=None:
        innerFieldType=typeSpec['fieldType']
        datastructID = typeSpec['arraySpec']['datastructID']
        return [datastructID, innerFieldType]
    else:
        if fldCat=='struct':
            fldCat='struct' #field['typeSpec']['fieldType'][0]
        return [fldCat, params]

def deProgify(identifier):
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
    funcTextToMakeViewWidget=''
    funcTextToUpdateViewWidget=''
    funcTextToMakeEditWidget=''
    funcTextToUpdateEditWidget=''

    funcTextToUpdateCrntFromWidget=''
    funcTextToCopyCrntToList=''

    funcTextToAllocateNewCrnt=''
    funcTextToPushCrntToList=''
    funcTextToDeleteNthItem=''
    funcTextToInitializeWidget=''


    # Find the model
    modelRef = progSpec.findSpecOf(classes[0], structTypeName, 'model')
    currentModelSpec = modelRef
    if modelRef==None:
        cdErr('To build a list GUI for list of "'+structTypeName+'" a model is needed but is not found.')

    ### Write code for each field
    fieldIdx=0
    for field in modelRef['fields']:
        fieldIdx+=1
        fldCat=progSpec.fieldsTypeCategory(field['typeSpec'])
        fieldName=field['fieldName']
        label = deProgify(fieldName)

###############
    CODE = 'struct '+listManagerStructName+": inherits = 'ListWidgetManager' {" + """
    /-me ListEditorWidget: LEW

    /- Override all these for each new list editing widget
    their GUI_item: makeViewableWidget() <- {return(NULL)}
    void: updateViewableWidget(their GUI_item: Wid) <- {}
    their GUI_item: makeEditableWidget() <- {return(NULL)}
    void: updateEditableWidget(their GUI_item: Wid) <- {}
    void: updateCrntFromEdited(their GUI_item: Wid) <- {}
    void: allocateNewCurrentItem() <- {}
    void: pushCrntToList() <- {}
    void: deleteNthItem() <- {}
    void: copyCrntBackToList() <- {}

    their GUI_item: initWidget() <- {return(LEW.init_dialog(self))}
}
"""
    codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, listManagerStructName)

def getWidgetHandlingCode(classes, fldCat, fieldName, field, structTypeName, indent):
    global newWidgetFields
    global widgetInitFuncCode
    global widgetFromVarsCode
    global varsFromWidgetCode

    label = deProgify(fieldName)
    [fieldSpec, params] = getFieldSpec(fldCat, field)
    typeName = fieldSpec+'Widget'
    if fieldSpec=='struct':
        typeName = 'GUI_Frame'
        makeTypeNameCall = 'parent.'+fieldName+'.GUI_Manager.make'+structTypeName+'Widget(parent.'+fieldName+')'
    else: makeTypeNameCall = 'make'+typeName[0].upper() + typeName[1:]+'("'+label+'")'

    CasedFieldName = fieldName[0].upper() + fieldName[1:]
    widgetFieldName = CasedFieldName + 'Widget'

    typeSpec=field['typeSpec']
    newWidgetFields += '\n'+indent+'    their '+typeName+': '+widgetFieldName
    if progSpec.typeIsPointer(typeSpec): widgetInitFuncCode += indent+'    Allocate(parent.'+fieldName+')\n'  +  indent+'    Allocate(parent.'+fieldName+'.GUI_Manager)\n'
    widgetInitFuncCode += indent+'    '+widgetFieldName+' <- '+makeTypeNameCall+'\n'

    # If this is a list, populate it
    print "WIDGET:", typeName, typeSpec
    if 'arraySpec' in typeSpec and typeSpec['arraySpec']!=None:
        innerFieldType=typeSpec['fieldType']
        print "ARRAYSPEC:",innerFieldType, field
        fldCatInner=progSpec.innerTypeCategory(innerFieldType)

        # If it hasn't already been added, make a struct <ItemType>_ListWidgetManager:ListWidgetManager{}
        listManagerStructName = structTypeName+'_ListEditorWidget'
        codeListWidgetManagerClassOverride(classes, listManagerStructName, structTypeName)

        listWidMgrName = widgetFieldName+'_LEWM'
        newWidgetFields += '\n'+indent+'    me '+listManagerStructName+': '+listWidMgrName+'\n'

        widgetListEditorName = widgetFieldName+'Editor'
   #     widgetInitFuncCode += indent+'    their '+structTypeName+': parent\n'
        widgetInitFuncCode += indent+'    their GUI_item: '+widgetListEditorName+' <- '+listWidMgrName+'.initWidget()\n'
        widgetInitFuncCode += indent+'    addToContainer(box, '+widgetListEditorName+')\n'
   #     widgetInitFuncCode += indent+"    withEach _item in parent."+fieldName+':{\n        addToContainer('+widgetFieldName+', _item.make'+structTypeName+'Widget(s))\n    }\n'

    else: # Not an ArraySpec:
        widgetInitFuncCode += indent+'    addToContainer(box, '+widgetFieldName+')\n'

def BuildGuiForList(classes, className, dialogStyle, newStructName):
    pass

def BuildGuiForStruct(classes, className, dialogStyle, newStructName):
    print "in BuildGuiForStruct\n"
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
    if modelRef==None:
        cdErr('To build a GUI for class "'+className+'" a model is needed but is not found.')

    ### Write code for each field
    fieldIdx=0
    for field in modelRef['fields']:
        fieldIdx+=1
        typeSpec=field['typeSpec']
        fldCat=progSpec.fieldsTypeCategory(typeSpec)
        fieldName=field['fieldName']
        label = deProgify(fieldName)
        print "    >"+fieldName+'   '+label+'\n'
        if fieldName=='settings':
            # add settings
            continue

        structTypeName=''
        if fldCat=='struct': # Add a new class to be processed
            structTypeName=typeSpec['fieldType'][0]
            newGUIStyle = 'Dialog'
            guiStructName = structTypeName+'_'+newGUIStyle+'_GUI'
            if not(guiStructName in classesEncoded):
                print "TO ENCODE:", guiStructName
                classesEncoded[guiStructName]=1
                classesToProcess.append([structTypeName, 'struct', 'Dialog', guiStructName])

        if 'arraySpec' in typeSpec and typeSpec['arraySpec']!=None:# Add a new list to be processed
            structTypeName=typeSpec['fieldType'][0]
            newGUIStyle = 'Dialog'
            guiStructName = structTypeName+'_'+newGUIStyle+'_LIST'
            if not(guiStructName in classesEncoded):
                print "TO ENCODE:", guiStructName
                classesEncoded[guiStructName]=1
                classesToProcess.append([structTypeName, 'list', 'Dialog', guiStructName])


        if fldCat=='func': continue

        getWidgetHandlingCode(classes, fldCat, fieldName, field, structTypeName, '')

    # Parse everything
    print "MAKE CLASS:" + className
    initFuncName = 'make'+className[0].upper() + className[1:]+'Widget'
    if dialogStyle == 'Z_stack': containerWidget='makeStoryBoardWidget()'
    else: containerWidget='makeFrameWidget()'

    newWidgetFields += '    their '+className+': parent\n'

    widgetInitFuncCode = '\n  their GUI_item: '+initFuncName+'(their '+className+': Parent) <- {\n    parent<-Parent\n    their GUI_Frame:box <- '+containerWidget+'\n' + widgetInitFuncCode + '\n    return(box)\n  }\n'
    widgetFromVarsCode += '    void: updateWidgetFromVars() <- {\n' + widgetFromVarsCode + '\n    }\n'
    varsFromWidgetCode += '    void: updateVarsFromWidget() <- {\n' + varsFromWidgetCode + '\n    }\n'
    parentStructFields = '    our ' + newStructName + ': ' + 'GUI_Manager\n'
    parentStructFields += widgetFromVarsCode + varsFromWidgetCode
    GUI_StructFields   = newWidgetFields + widgetInitFuncCode
    CODE =  'struct '+newStructName+" {\n" + GUI_StructFields + '\n}\n'         # Add the new fields to the GUI manager struct
    CODE += 'struct '+className + " {\n" + parentStructFields + '\n}\n'         # Add the new fields to the parent struct
    print '==========================================================\n'+CODE
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
    guiStructName = topClassName+'_'+appStype+'_GUI'
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
    primaryMakerFuncName = 'make'+topClassName[0].upper() + topClassName[1:]+'Widget'
    declAPP_fields = '  their '+topClassName+': primary\n'
    declAPP_fields+='''
    me void: createAppArea(me GUI_Frame: frame) <- {
        me string:s
        Allocate(primary)
        Allocate(primary.GUI_Manager)
        their GUI_storyBoard: appStoryBoard <- primary.GUI_Manager.'''+primaryMakerFuncName+'''(primary)
        gui.addToContainerAndExpand (frame, appStoryBoard)
    }
'''
    CODE = progSpec.wrapFieldListInObjectDef('APP', declAPP_fields)
    codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, 'APP')

    return
