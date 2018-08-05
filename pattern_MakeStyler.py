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
styler.color(me string: ID)

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
        bkGndColor = [45, 100, 220]   /- RGB
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

    2. ISO color cames are constants and cannot be changed. But the others are variables and can be assigned.

'''
import progSpec
import codeDogParser

def stringifyList(theList):
    S=''
    count=0
    for item in theList:
        if not(isinstance(item, basestring)):cdErr("List item not basesring")
        if count >0: S = S+', '
        S = S + item
        count = count +1
    return S
        
def processStylerMap(stylerTags, varOwner, varType, defaultVars):
    S=''
    for varName in stylerTags:
        varValue = stylerTags[varName]
        if isinstance(varValue, basestring): 
			print"stylerTags: ", stylerTags
			RHS=' <- '+varValue
        elif isinstance(varValue, list): 
            RHS=stringifyList(varValue)
            RHS=' <- '+varType+'('+RHS+')'
        else: cdErr("UNKNOWN RHS type: "+varName)
        if varName in defaultVars:
            S = S+'        ' + varName + RHS +'\n'
        else:
            S = S+'        setCustomColor("'+ varName +'", '+ varValue +')\n'
            print varName+ ' not in defaultVars!!!!!!!!!!!!!!', S
    return S
    
def processStyler(stylerTagValue):
    varOwner = ''
    varType  = ''
    S        = ''
    for tag in stylerTagValue:
        if tag =="colors":
            varOwner = 'me'
            varType  = 'cdColor'
            defaultVars = ['frGndColor', 'bkGndColor', 'highlight1Color', 'highlight2Color', 'highlight3Color']
        elif tag =="fontNames":
            varOwner = 'me'
            varType  = 'string'
            defaultVars = ['titleFont', 'normalFont', 'H1_font', 'H2_font', 'H3_font', 'H4_font', 'H5_font', 'H6_font', 'timesFont', 'sansSerifFont', 'comicFont', 'scriptFont', 'monoFont']
            '''elif tag =="fontSizes":
            varOwner = 'me'
            varType  = 'string'
            defaultVars = []'''
        else:
            print '    tag not found'

        if isinstance(stylerTagValue[tag], dict): 
            S = S + processStylerMap(stylerTagValue[tag], varOwner, varType,defaultVars)
        else: print"!!!!!!!!!!!!!!!!!!styler not map", stylerTagValue[tag]
    return S
        
def apply(classes, tags, stylerTagName):
    if not(isinstance(stylerTagName,basestring)):
        cdErr("Styler tag name must be a string")
    stylerTagValue = progSpec.fetchTagValue(tags, stylerTagName)
    initCode = processStyler(stylerTagValue)
    
        
    code = r"""
struct GLOBAL{
    our Styler:: styler
} 
struct Styler{
    our cdColor[map string]: userColors
    me cdColor:  frGndColor      <- White
    me cdColor:  bkGndColor      <- Black
    me cdColor:  highlight1Color <- White
    me cdColor:  highlight2Color <- Cornflower
    me cdColor:  highlight3Color <- OrangeRed

        our fontSpec:: fontDefault <- ("Ariel", 10, 0)
        our fontSpec:: fontTitle <- ("Ariel", 16, 0)
        our fontSpec:: fontSmall <- ("Ariel", 8, 0)
    
    void: setCustomColor(me string: ID, me cdColor: C) <- {}
    me cdColor: color(me string: ID) <- {}
    
    /- FONT NAMES
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
    
    void: setCustomFont(me string: ID, me string: fontName) <- {}
    me string: font(me string: ID) <- {}
    
    /- FONT SIZES
    me string: fontSizeVerySmall
    me string: fontSizeSmall
    me string: fontSizeNormalSize
    me string: fontSizeLarge
    me string: fontSizeVeryLarge
    
    void: setCustomFontSize(me string: ID, me string: fontSize) <- {}
    me string: fontSize(me string: ID) <- {}

    void: INIT()<-{
        <INITCODE>    }
    void: addColor(me string: colorName, me cdColor: color) <- {
        our cdColor:: tmpColor <- color
        userColors.insert(colorName, tmpColor)
    }
    our cdColor: getColor(me string: colorName) <- {
        return(userColors.get(colorName))
    }
}
    """
    code = code.replace('<INITCODE>', initCode)
    #print '==========================================================\n'+code
    codeDogParser.AddToObjectFromText(classes[0], classes[1], code , 'Pattern: MakeStyler')
