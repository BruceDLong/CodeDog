#/////////////////  Use this pattern to generate platform specific menus

import progSpec
import codeDogParser


def apply(classes, tags, modulesToCheck):
    print("MODULES:", modulesToCheck)
    S=''
    # Get 'MainMenu' tags from libs and patterns run.
    # fetch all the menuSets
    # sort them by priority
    # for each menuSet
        # Add menu or separator bar
        # for each menuItem in set
            # Add the menuItem to menu
