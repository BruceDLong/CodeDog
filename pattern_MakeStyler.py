import progSpec
import codeDogParser

def apply(classes, tags):
    code = r"""
    struct GLOBAL{
        our Styler:: styler
    } 
    struct ColorPalet{
		our cdColor:: background
		our cdColor:: forground
		our cdColor:: highlight1
		our cdColor:: highlight2
		our cdColor:: highlight3
    }
    struct FontPalet{
		our fontSpec:: main
		our fontSpec:: title
		our fontSpec:: H1
		our fontSpec:: H2
		our fontSpec:: H3
		our fontSpec:: H4
		our fontSpec:: H5
		our fontSpec:: H6
    }
    struct SkinPalet{
		/- color gradient or image
    }
    struct Theme{
		our ColorPalet: colorPalet
		our FontPalet:  fontPalet
		our SkinPalet:  skinPalet	/- optional
    }
    struct Styler{
		const int: backgroundColor <- 1
		const int: foregroundColor <- 2
		const int: highlightColor  <- 3
		
		our cdColor[map string]: userColors
		me cdColor:  foreground  <- White
		me cdColor:  background  <- Black
		me cdColor:  textPrimary <- White
		me cdColor:  highlight1  <- Cornflower
		me cdColor:  highlight2  <- OrangeRed
		me fontSpec: fontDefault
		me fontSpec: fontTitle
		me fontSpec: fontSmall

		void: INIT()<-{
			fontDefault.name <- "Ariel"
			fontDefault.size <- 10
			fontTitle.name   <- "Ariel"
			fontTitle.size   <- 16
			fontSmall.name   <- "Ariel"
			fontSmall.size   <- 8
		}
		void: addColor(me string: colorName, me cdColor: color) <- {
		    our cdColor:: tmpColor <- color
		    userColors.insert(colorName, tmpColor)
		}
		our cdColor: getColor(me string: colorName) <- {
		    return(userColors.get(colorName))
		}
    }
    """
    codeDogParser.AddToObjectFromText(classes[0], classes[1], code , 'Pattern: MakeStyler')
