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
currentFuncCode=''
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

def codeListWidgetManagerClassOverride(listManagerStructName, structTypeName):
    # if class listManagerStructName already exists,: return
    CODE = 'struct '+listManagerStructName+':'+ ListWidgetManager + """
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

    their GUI_item: initWidget(me gpointer: theList) <- {return(LEW.init_dialog(self)}
    """


def getWidgetHandlingCode(fldCat, fieldName, field, structTypeName, indent):
    global newWidgetFields
    global currentFuncCode
    global widgetFromVarsCode
    global varsFromWidgetCode

    label = deProgify(fieldName)
    [fieldSpec, params] = getFieldSpec(fldCat, field)
    typeName = fieldSpec+'Widget'
    if fieldSpec=='struct':
        typeName = 'GUI_Frame'
        makeTypeNameCall = fieldName+'.make'+structTypeName+'Widget("'+label+'")'
    else: makeTypeNameCall = 'make'+typeName[0].upper() + typeName[1:]+'("'+label+'")'

    CasedFieldName = fieldName[0].upper() + fieldName[1:]
    widgetFieldName = CasedFieldName + 'Widget'

    typeSpec=field['typeSpec']
    newWidgetFields += '\n'+indent+'    their '+typeName+': '+widgetFieldName
    if progSpec.typeIsPointer(typeSpec): currentFuncCode += indent+'    Allocate('+fieldName+')\n'
    currentFuncCode += indent+'    '+widgetFieldName+' <- '+makeTypeNameCall+'\n'

    # If this is a list, populate it
    print "WIDGET:", typeName, typeSpec
    if 'arraySpec' in typeSpec and typeSpec['arraySpec']!=None:
        innerFieldType=typeSpec['fieldType']
        print "ARRAYSPEC:",innerFieldType, field
        fldCatInner=progSpec.innerTypeCategory(innerFieldType)

        # If it hasn't already been added, make a struct <ItemType>_ListWidgetManager:ListWidgetManager{}
        listManagerStructName = structTypeName+'_ListEditorWidget'
        codeListWidgetManagerClassOverride(listManagerStructName, structTypeName)

        listWidMgrName = widgetFieldName+'_LEWM'
        newWidgetFields += '\n'+indent+'    me '+listManagerStructName+': '+listWidMgrName+'\n'

        widgetListEditorName = widgetFieldName+'Editor'
        currentFuncCode += indent+'    their GUI_item: '+widgetListEditorName+' <- '+listWidMgrName+'.initWidget(self)\n'
        currentFuncCode += indent+'    addToContainer(box, '+widgetListEditorName+')\n'
        currentFuncCode += indent+"    withEach _item in "+fieldName+':{\n        addToContainer('+widgetFieldName+', _item.make'+structTypeName+'Widget(s))\n    }\n'

    else: # Not an ArraySpec:
        currentFuncCode += indent+'    addToContainer(box, '+widgetFieldName+')\n'

def BuildGuiClass(classes, className, dialogStyle):
    print "in BuildGuiClass\n"
    # This makes 4 types of changes to the class:
    #   It adds a widget variable for items in model // newWidgetFields: '    their '+typeName+': '+widgetFieldName
    #   It adds a set Widget from Vars function      // widgetFromVarsCode: Func UpdateWidgetFromVars()
    #   It adds a set Vars from Widget function      // varsFromWidgetCode: Func UpdateVarsFromWidget()
    #   It add an initialize Widgets function.       // currentFuncCode: widgetFieldName+' <- '+makeTypeNameCall+'\n    addToContainer(box, '+widgetFieldName+')\n'
    global classesEncoded
    global currentClassName
    global currentModelSpec
    classesEncoded[className]=1
    currentClassName = className

    # reset the string vars that accumulate the code
    global newWidgetFields
    global currentFuncCode
    global widgetFromVarsCode
    global varsFromWidgetCode

    newWidgetFields=''
    currentFuncCode=''
    widgetFromVarsCode=''
    varsFromWidgetCode=''

    # Find the model
    modelRef = progSpec.findSpecOf(classes[0], className, 'model')
    currentModelSpec = modelRef
    if modelRef==None:
        cdErr('To build a GUI for class "'+className+'" a model is needed but is not found.')

    # Choose an appropriate app style
    if (True): # if all data fields are classes
        appStype='Z_stack'
    #else: 'X_stack', 'Y_stack', 'TabbedStack', 'FlowStack', 'WizardStack', 'Dialog', 'SectionedDialogStack'
    # also, handle non-modal dialogs


    ### Write code for each field
    fieldIdx=0
    for field in modelRef['fields']:
        fieldIdx+=1
        fldCat=progSpec.fieldsTypeCategory(field['typeSpec'])
        fieldName=field['fieldName']
        label = deProgify(fieldName)
        print "    >"+fieldName+'   '+label+'\n'
        if fieldName=='settings':
            # add settings
            continue

        structTypeName=''
        if fldCat=='struct': # Add a new class to be processed
            structTypeName=field['typeSpec']['fieldType'][0]
            if not(structTypeName in classesEncoded):
                print "TO ENCODE:", structTypeName
                classesEncoded[structTypeName]=1
                classesToProcess.append(structTypeName)

        if fldCat=='func': continue

        getWidgetHandlingCode(fldCat, fieldName, field, structTypeName, '')

    # Parse everything
    print "MAKE CLASS:" + className
    initFuncName = 'make'+className[0].upper() + className[1:]+'Widget'
    if dialogStyle == 'Z_stack': containerWidget='makeStoryBoardWidget()'
    else: containerWidget='makeFrameWidget()'

    currentFuncCode = '\n  their GUI_item: '+initFuncName+'(me string: S) <- {\n    me string:s\n    their GUI_Frame:box <- '+containerWidget+'\n' + currentFuncCode + '\n    return(box)\n  }\n'
    widgetFromVarsCode += '    void: updateWidgetFromVars() <- {\n' + widgetFromVarsCode + '\n    }\n'
    varsFromWidgetCode += '    void: updateVarsFromWidget() <- {\n' + varsFromWidgetCode + '\n    }\n'
    functionsCode = newWidgetFields + currentFuncCode + widgetFromVarsCode + varsFromWidgetCode
    CODE = 'struct '+className+" {\n" + functionsCode + '\n}\n'         # Add the new fields to the STRUCT being processed
    print '==========================================================\n'+CODE
    codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, className)


def apply(classes, tags, className):
    print "APPLY: in Apply\n"
    global classesToProcess
    global classesEncoded
    classesToProcess=[className]
    classesEncoded={}

    # Amend items to each GUI data class
    classIDX=0
    for classToAmend in classesToProcess:
        cdlog(2, "BUILDING GUI for class:" + classToAmend)
        classIDX+=1
        if classIDX==1: dialogStyle='Z_stack'
        else: dialogStyle=''
        BuildGuiClass(classes, classToAmend, dialogStyle)


    # Fill createAppArea()
    primaryMakerFuncName = 'make'+className[0].upper() + className[1:]+'Widget'
    declAPP_fields = '  their '+className+': primary\n'
    declAPP_fields+='''
    me void: createAppArea(me GUI_Frame: frame) <- {
        me string:s
        Allocate(primary)
        their GUI_storyBoard: appStoryBoard <- primary.'''+primaryMakerFuncName+'''(s)
        gui.addToContainerAndExpand (frame, appStoryBoard)
    }
'''
    CODE = progSpec.wrapFieldListInObjectDef('APP', declAPP_fields)
    codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, 'APP')

    return
