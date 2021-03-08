# pattern_MakeStyler.py

import progSpec

'''
These styler fields are always available:
our Styler: styler

# The ISO color names. E.g.: styler.Black
styler.frGndColor
styler.bkGndColor
styler.highlight1Color
styler.highlight2Color
styler.highlight3Color

styler.setCustomColor(me string: ID, me cdColor: C)
styler.color(me string: ID, me cdColor: default)

styler.titleFont
styler.normalFont
styler.H1_font
styler.H2_font
styler.H3_font
styler.H4_font
styler.H5_font
styler.H6_font
styler.timesFont
styler.sansSerifFont
styler.comicFont
styler.scriptFont
styler.monoFont

styler.setCustomFont(me string: ID, me string: fontName)
styler.font(me string: ID)

styler.fontSizeVerySmall
styler.fontSizeSmall
styler.fontSizeNormalSize
styler.fontSizeLarge
styler.fontSizeVeryLarge

styler.setCustomFontSize(me string: ID, me string: fontSize)
styler.fontSize(me string: ID)

==========================
New style items can be added as well as the above items overridden by using tags.
Examples:

mainStyle = {
    colors = {
        frGndColor = sysDefaultFrGndColor
        //bkGndColor = [0, 0, 0]   // RGB
        highlight1Color = LightGreen

        MySpecialColor = SlateBlue
    }

    fontNames = {
        titleFont = 'Ariel Bold'
        normalFont = 'Ariel'
        H1_font = sysDefaultH1_font

        LogoFont = 'CompanyFont'
    }

    fontSizes = {
        styler.fontSizeVerySmall = sysDefaultFontSizeVerySmall
        styler.fontSizeSmall = ":pp8"
        styler.fontSizeLarge = ":sp20"
        styler.LogoFontSize = ":dp18"
    }

    implDetails = {

    }
}

NOTES:
    1. If one of the always available fields is not given in the tags, its "sysDefaultxxxxx" value is given.
       This value is platform dependent if the platform as a value, otherwise the value is a standard CodeDog value.

    2. ISO color names are constants and cannot be changed. But the others are variables and can be assigned.

'''
import progSpec
import codeDogParser

def stringifyList(theList):
    S=''
    count=0
    for item in theList:
        if not(isinstance(item, str)):cdErr("List item not basesring")
        if count >0: S = S+', '
        S = S + item
        count = count +1
    return S

def processStylerMap(stylerTags, varOwner, varType, setFunc, defaultVars):
    S=''
    for varName in stylerTags:
        varValue = stylerTags[varName]
        if isinstance(varValue, str):
            RHS=' <- '+varValue
        elif isinstance(varValue, list):
            RHS=stringifyList(varValue)
            RHS=' <- '+varType+'('+RHS+')'
        else: cdErr("UNKNOWN RHS type: "+varName)
        if varName in defaultVars:
            S = S+'        ' + varName + RHS +'\n'
        else:
            S = S+'        '+setFunc+'("'+ varName +'", '+ varValue +')\n'
    return S

def processStyler(stylerTagValue):
    varOwner = ''
    varType  = ''
    S        = ''
    for tag in stylerTagValue:
        if tag =="colors":
            varOwner = 'me'
            varType  = 'cdColor'
            setFunc  = 'setCustomColor'
            defaultVars = ['frGndColor', 'bkGndColor', 'highlight1Color', 'highlight2Color', 'highlight3Color']
        elif tag =="fontNames":
            varOwner = 'me'
            varType  = 'string'
            setFunc  = 'setCustomFont'
            defaultVars = ['titleFont', 'normalFont', 'H1_font', 'H2_font', 'H3_font', 'H4_font', 'H5_font', 'H6_font', 'timesFont', 'sansSerifFont', 'comicFont', 'scriptFont', 'monoFont']
        elif tag =="fontSizes":
            varOwner = 'me'
            varType  = 'string'
            setFunc  = 'setCustomFontSize'
            defaultVars = ['fontSizeVerySmall', 'fontSizeSmall', 'fontSizeNormalSize', 'fontSizeLarge', 'fontSizeVeryLarge']
        elif tag == "fontSizeMode":
            varOwner = ''
            varType  = 'pixelMode'
            setFunc  = ''
            defaultVars = []
            RHS      = ' <- '+ stylerTagValue[tag]
        else:
            print('    tag not found')

        if isinstance(stylerTagValue[tag], dict):
            S = S + processStylerMap(stylerTagValue[tag], varOwner, varType, setFunc, defaultVars)
        elif isinstance(stylerTagValue[tag], str):
            S = S + '        ' + varType + RHS +'\n'
        else: print("!!!!!!!!!!!!!!!!!!styler not map or basestring", stylerTagValue[tag])
    return S

def apply(classes, tags, stylerTagName):
    if not(isinstance(stylerTagName,str)):
        cdErr("Styler tag name must be a string")
    stylerTagValue = progSpec.fetchTagValue(tags, stylerTagName)
    initCode = processStyler(stylerTagValue)


    code = r"""
struct GLOBAL{
    our Styler:: styler
}
struct Styler{
    me Map<me string, our cdColor>: userColors
    me cdColor:  frGndColor      <- Black
    me cdColor:  bkGndColor      <- White
    me cdColor:  highlight1Color <- Black
    me cdColor:  highlight2Color <- Cornflower
    me cdColor:  highlight3Color <- OrangeRed
    me cdColor:  primaryTextColor <- Black
    me cdColor:  data1Color <- Cornflower
    me cdColor:  data2Color <- Turquoise
    me cdColor:  data3Color <- Magenta
    me cdColor:  data4Color <- MediumVioletRed
    me cdColor:  data5Color <- OrangeRed
    me cdColor:  data6Color <- Gold


    our fontSpec:: fontDefault{"Ariel", 10, 0}
    our fontSpec:: fontTitle{"Ariel", 16, 0}
    our fontSpec:: fontSmall{"Ariel", 8, 0}
    our fontSpec: fontVerySmall
    our fontSpec: fontLabelWidgetAndroid
    our fontSpec: fontEntryWidgetAndroid
    our fontSpec: fontTitleAndroid
    our fontSpec: fontTextAndroid

    void: setCustomColor(me string: ID, me cdColor: color) <- {
        our cdColor:: tmpColor <- color
        userColors.insert(ID, tmpColor)
    }
    me cdColor: color(me string: ID, me cdColor: defaultColor) <- {
        our cdColor[itr map string]: colorItr <- userColors.find(ID)
        if(colorItr != userColors.end()){return(colorItr.val)]
        return(defaultColor)
    }


    // FONT NAMES
    me Map<me string, me string>: userFontNames
    me string: titleFont
    me string: normalFont
    me string: H1_font
    me string: H2_font
    me string: H3_font
    me string: H4_font
    me string: H5_font
    me string: H6_font
    me string: timesFont
    me string: sansSerifFont
    me string: comicFont
    me string: scriptFont
    me string: monoFont

    void: setCustomFont(me string: ID, me string: fontName) <- {
        userFontNames.insert(ID, fontName)
    }
    me string: font(me string: ID) <- {return(userFontNames.at(ID))}

    // FONT SIZES
    me Map<me string, me int>: userFontSizes
    me int: fontSizeVerySmall
    me int: fontSizeSmall
    me int: fontSizeNormalSize
    me int: fontSizeLarge
    me int: fontSizeVeryLarge

    void: setCustomFontSize(me string: ID, me int: fontSize) <- {
        userFontSizes.insert(ID, fontSize)
    }
    me int: fontSize(me string: ID) <- {
        return(userFontSizes.at(ID))
    }

    // FONT SIZE MODES
    me mode[pp, dp, sp]: pixelMode <- pp

    me int: widgetLabelBoxWidth <- 100
    me int: widgetValueBoxWidth <- 100

    void: INIT()<-{
        <INITCODE>
        Allocate(fontDefault, "ariel", "14")
        Allocate(fontTitle, "ariel", "20")
        Allocate(fontSmall, "ariel", "10")
        Allocate(fontVerySmall, "ariel", "5")
        Allocate(fontLabelWidgetAndroid, "ariel", "25")
        Allocate(fontEntryWidgetAndroid, "ariel", "25")
        Allocate(fontTitleAndroid, "ariel", "25")
        Allocate(fontTextAndroid, "ariel", "20")
    }


}
    """
    code = code.replace('<INITCODE>', initCode)
    #print '==========================================================\n'+code
    codeDogParser.AddToObjectFromText(classes[0], classes[1], code , 'Pattern: MakeStyler')
