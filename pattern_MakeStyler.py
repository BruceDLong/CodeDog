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

styler.titleFontname
styler.normalFontname
styler.H1_fontname
styler.H2_fontname
styler.H3_fontname
styler.H4_fontname
styler.H5_fontname
styler.H6_fontname
styler.timesFontname
styler.sansSerifFontname
styler.comicFontname
styler.scriptFontname
styler.monoFontname

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
        titleFontname = 'Ariel Bold'
        normalFontname = 'Ariel'
        H1_font = sysDefaultH1_fontname

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
            setFunc  = 'setCustomFontname'
            defaultVars = ['titleFontname', 'normalFontname', 'H1_fontname', 'H2_fontname', 'H3_fontname', 'H4_fontname', 'H5_fontname', 'H6_fontname', 'timesFontname', 'sansSerifFontname', 'comicFontname', 'scriptFontname', 'monoFontname']
        elif tag =="fontSizes":
            varOwner = 'me'
            varType  = 'string'
            setFunc  = 'setCustomFontSize'
            defaultVars = ['verySmallFontSize', 'smallFontSize', 'normalFontSize', 'largeFontSize', 'veryLargeFontSize']
        elif tag =="strs":
            varOwner = 'me'
            varType  = 'string'
            setFunc  = 'setCustomString'
            defaultVars = []
        elif tag =="nums":
            varOwner = 'me'
            varType  = 'int'
            setFunc  = 'setCustomInteger'
            defaultVars = []
        elif tag =="doubles":
            varOwner = 'me'
            varType  = 'double'
            setFunc  = 'setCustomDouble'
            defaultVars = []
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

//TODO: Why don't these constructor inits work?
    our fontSpec:: defaultFont{"Ariel", 10, 0}
    our fontSpec:: titleFont{"Ariel", 16, 0}
    our fontSpec:: smallFont{"Ariel", 8, 0}
    our fontSpec:: verySmallFont{"Ariel", 5, 0}

    void: setCustomColor(me string: ID, me cdColor: color) <- {
        our cdColor:: tmpColor <- color
        userColors.insert(ID, tmpColor)
    }
    me cdColor: color(me string: ID, me cdColor: defaultColor) <- {
        our cdColor[itr map string]: colorItr <- userColors.find(ID)
        if(colorItr != userColors.end()){return(colorItr.val)}
        return(defaultColor)
    }


    // FONT NAMES
    me Map<me string, me string>: userFontNames
    me string: titleFontname
    me string: normalFontname
    me string: H1_fontname
    me string: H2_fontname
    me string: H3_fontname
    me string: H4_fontname
    me string: H5_fontname
    me string: H6_fontname
    me string: timesFontname
    me string: sansSerifFontname
    me string: comicFontname
    me string: scriptFontname
    me string: monoFontname

    void: setCustomFont(me string: ID, me string: fontName) <- {
        userFontNames.insert(ID, fontName)
    }
    me string: font(me string: ID) <- {return(userFontNames.at(ID))}

    // FONT SIZES
    me Map<me string, me int>: userFontSizes
    me int: verySmallFontSize
    me int: smallFontSize
    me int: normalSizeFontSize
    me int: largeFontSize
    me int: veryLargeFontSize

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

    // OTHER KEY/VALUES
    me Map<me string, me string>: userStrings
    void: setCustomString(me string: key, me string: value) <- {
        userStrings.insert(key, value)
    }

    me Map<me string, me int>: userIntegers
    void: setCustomInteger(me string: key, me string: value) <- {
        userIntegers.insert(key, toInt(value))
    }

    me Map<me string, me int>: userDoubles
    void: setCustomDouble(me string: key, me string: value) <- {
        userIntegers.insert(key, toDouble(value))
    }

    void: INIT()<-{
        <INITCODE>
        Allocate(defaultFont, "ariel", "14")
        Allocate(titleFont, "ariel", "20")
        Allocate(smallFont, "ariel", "10")
        Allocate(verySmallFont, "ariel", "5")
    }


}
    """
    code = code.replace('<INITCODE>', initCode)
    #print '==========================================================\n'+code
    codeDogParser.AddToObjectFromText(classes[0], classes[1], code , 'Pattern: MakeStyler')
