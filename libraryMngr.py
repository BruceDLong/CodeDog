# This module manages dog files that form libraries

from inspect import getsourcefile
import os
from os.path import abspath
import re

import codeDogParser
import progSpec
from progSpec import cdlog, cdErr

from pyparsing import ParseResults


libPaths = []
featuresHandled = []
tagsFromLibFiles = {}
currentFilesPath = ""
childLibList = []
'''
T h e   b e s t   l i b r a r y   c h o i c e s   f o r   y o u r   p r o g r a m
  And the best programs for your library

Whether you are writing a program for which library choices will be made,
or a library which will be chosen for use with different programs,
you want to have codeDog make the best choices.

You can get the results you want by knowing how CodeDog makes its decisions
about which libraries to use.

The way libraries are chosen in most languages
is that they're given by the programmer.
But code written to work on many different platforms
is easiest to create when the decision is left to the compiler.

In codeDog the problem is solved by telling
the compiler about features and needs instead of about the libraries.
The compiler then chooses which libraries to link from the listed program needs.

There are two kinds of need that the programmer can specify in dog files:
We'll call them 'features' and 'components'. Features are functionality that
must be added to codeDog in order for your program to work (GUI-toolkit,
Unicode, Math-kit, Networking.) Features often correspond to actual libraries.
Components are files that describe libraries that may be specific to particular
platforms. GTK3, XCODE, etc. Both features and components are "needs"
that are specified with tags.
'''

def getTagsFromLibFiles():
    """simple getter for module level variable"""
    return tagsFromLibFiles

def collectLibFilenamesFromFolder(folderPath):
    for filename in os.listdir(folderPath):
        if filename.endswith("Lib.dog"):
            libPaths.append(os.path.join(folderPath, filename))
        elif filename.endswith("Lib.dog.proxy"):
            line = open(os.path.join(folderPath, filename)).readline()
            line=line.strip()
            baseName = os.path.basename(line)
            #print("baseName: {}".format(baseName))
            if (filename.strip('.proxy') == baseName):
                libPaths.append(os.path.realpath(line))
            else:
                cdErr("File name "+filename+" does not match path name.")

def collectFromFolderOrLIB(pathName):
    collectLibFilenamesFromFolder(pathName)
    LIBFOLDER = os.path.join(pathName, "LIBS")
    if(os.path.isdir(LIBFOLDER)):
        collectLibFilenamesFromFolder(LIBFOLDER)

def findLibraryFiles():
    dogFileFolder = os.getcwd()
    codeDogFolder = os.path.dirname(os.path.realpath(__file__))
    collectFromFolderOrLIB(dogFileFolder)
    if (dogFileFolder!=codeDogFolder):
        collectFromFolderOrLIB(codeDogFolder)
    libPaths.sort()

def findLibrary(feature):
    """Returns the filepath of LIB that matches '[input].Lib.dog'. If no match
    is found returns empty string"""

    for libPath in libPaths:
        if isinstance(feature, ParseResults) and len(feature)==1:
            feature = feature[0]
        if os.path.basename(libPath) == feature+".Lib.dog":
            return libPath
    return ""

def findLibraryChildren(libID):
    """Given a lib prefix string (ie. Logger) return list of paths to children
    LIB files (ie. Logger.CPP.Lib.dog, Logger.Android.Lib.dog)"""
    libs=[]
    for item in libPaths:
        itemBaseName = os.path.basename(item)
        if(itemBaseName.endswith('Lib.dog') and itemBaseName.startswith(libID)):
            innerName = itemBaseName[len(libID)+1:-8]
            if (innerName != '' and innerName.find('.')==-1):
                libs.append(item)
    return libs

def replaceFileName(fileMatch):
    global currentFilesPath
    fileName = fileMatch.group(1)
    currentWD = os.getcwd()
    pathName = abspath(currentWD) +"/"+fileName
    if not os.path.isfile(pathName):
        dirname, filename = os.path.split(abspath(getsourcefile(lambda:0)))
        pathName = dirname +"/"+fileName
        if not os.path.isfile(pathName):
            pathName = currentFilesPath +"/"+fileName
            if not os.path.isfile(pathName):
                cdErr("Cannot find include file '"+fileName+"'")

    includedStr = progSpec.stringFromFile(pathName)
    includedStr = processIncludedFiles(includedStr, pathName)
    return includedStr

def processIncludedFiles(fileString, fileName):
    global currentFilesPath
    dirname, filename = os.path.split(abspath(fileName))
    currentFilesPath = dirname
    pattern = re.compile(r'#include +([\w -\.\/\\]+)')
    return pattern.sub(replaceFileName, fileString)

def loadTagsFromFile(fileName):
    codeDogStr = progSpec.stringFromFile(fileName)
    codeDogStr = processIncludedFiles(codeDogStr, fileName)
    return codeDogParser.parseCodeDogLibTags(codeDogStr)

def filterReqTags(ReqTags):
    '''Change requirement tags from a list containing one parseResult element
    to a list of lists containing strings. (see exceptions). Each inner list
    corresponds to an element in the requirements list in the LIB.

    Exception: when requirement is in another list, ie. cases of tagOneOf,
    the element is appended to inner list as ParseResults rather than string.
    TODO: look into extracting the ParseResults
    '''
    filteredTags=[]
    for ReqTag in ReqTags:
        filteredTag = []
        for tagItem in ReqTag.tagListContents:
            filteredTag.append(tagItem.tagValue[0])
        filteredTags.append(filteredTag)
    return filteredTags

def extractLibTags(library):
    libTags = loadTagsFromFile(library)
    tagsFromLibFiles[library] = libTags
    ReqTags = progSpec.fetchTagValue([libTags], 'requirements')
    if ReqTags == None:
        ReqTags =[]
    elif len(ReqTags)>0:
        ReqTags = filterReqTags(ReqTags)
    interfaceTags = progSpec.fetchTagValue([libTags], 'interface')
    if interfaceTags == None:
        interfaceTags =[]
    return [ReqTags,interfaceTags]

def libListType(libList):
    if isinstance(libList, str): return "STRING"
    op=libList[0]
    if (op=='AND' or op=='OR'):
        return op
    print("WHILE EXAMINING:", libList)
    cdErr('Invalid type encountered for a library identifier:'+str(op))

def reduceSolutionOptions(options, indent):
    #print indent+"OPTIONS:", options
    optionsOp=libListType(options)
    if optionsOp != 'STRING':
        i=0
        while i<len(options[1]):
            opt=options[1][i]
            if not isinstance(opt, str):
                reduceSolutionOptions(options[1][i], indent+'|   ')
                if len(opt[1])==0:
                    del options[1][i]
                    cdlog(1, "DELETED:", i)
                    continue
                changesMade=True
                while changesMade:
                    changesMade=False
                    opt=options[1][i]
                    optOp=libListType(opt)
                    optionsOp=libListType(options)
                    if (optOp=='AND' or optOp=='OR') and (optOp==optionsOp or len(opt[1])==1):  # Both AND or both OR so unwrap child list
                        options[1][i:i+1]=opt[1]
                        changesMade=True
                    elif optionsOp=='AND' and optOp=='OR':
                        print("CROSS")
                   # removeDuplicates(options)  # TODO: Make this line remove duplicates
            i+=1

def fetchFeaturesNeededByLibrary(feature):
    libFile = findLibrary(feature)
    libTags = loadTagsFromFile(libFile)
    if 'featuresNeeded' in libTags:
        featuresNeeded = libTags['featuresNeeded']
        return featuresNeeded
    return []

def checkIfLibFileMightSatisyNeedWithRequirements(tags, need, libFile, indent):
    [ReqTags,interfaceTags] = extractLibTags(libFile)
    Requirements = []
    LibCanWork=True
    if need[0] == 'require':
        LibCanWork=False
        if 'provides' in interfaceTags:
            if need[1] in interfaceTags['provides']:
                #print(indent, '{}REQUIRE: {} in {}'.format(indent, need[1], interfaceTags['provides']))
                LibCanWork = True

    for ReqTag in ReqTags:
        #print("REQUIREMENT: {}".format(ReqTag))
        if ReqTag[0]=='feature':
            print("\n    Nested Features should be implemented. Please implement them. (", ReqTag[1], ")n")
            exit(2)
        elif ReqTag[0]=='require':
            Requirements.append(ReqTag)
        elif ReqTag[0]=='tagOneOf':
            tagToCheck = ReqTag[1]
            validValues = progSpec.extractListFromTagList(ReqTag[2])
            parentTag = progSpec.fetchTagValue(tags, tagToCheck)  # E.g.: "platform"
            if parentTag==None:
                LibCanWork=False
                cdErr("ERROR: The tag '"+ tagToCheck + "' was not found in" + libFile + ".\n")
            if not parentTag in validValues: LibCanWork=False
            else: cdlog(1, "  Validated: "+tagToCheck+" = "+parentTag)

    return [LibCanWork, Requirements]

def constructORListFromFiles(tags, need, files, indent):
    global childLibList
    OR_List = ['OR', []]
    for libFile in files:
        #print("{}LIB FILE: {}".format(indent, libFile))
        [LibCanWork, Requirements] = checkIfLibFileMightSatisyNeedWithRequirements(tags, need, libFile, indent)
        if(LibCanWork):
            #print("{} LIB CAN WORK: {}".format(indent, libFile))
            childFileList = findLibraryChildren(os.path.basename(libFile)[:-8])
            if len(childFileList)>0:
                childLibList = childLibList + childFileList
                solutionOptions = constructANDListFromNeeds(tags, Requirements, childFileList, indent + "|   ")
                solutionOptions[1] = [libFile] + solutionOptions[1]
                OR_List[1].append(solutionOptions)
            else: OR_List[1].append(libFile)
    if len(OR_List[1])==1 and isinstance(OR_List[1][0], str):
        return OR_List[1][0]  # Optimization
    return OR_List

def constructANDListFromNeeds(tags, needs, files, indent):
    AND_List = ['AND', []]
    for need in needs:
        #print(indent, "**need*: ", need)
        if need[0] == 'feature':
            if need[1] in featuresHandled: continue
            cdlog(1, "FEATURE: "+str(need[1]))
            featuresHandled.append(need[1])
            filesToTry = [findLibrary(need[1])]
            if filesToTry[0]=='': cdErr('Could not find a dog file for feature '+need[1])
        else:
            filesToTry = files

        if len(filesToTry)>0:
            solutionOptions = constructORListFromFiles(tags, need, filesToTry, indent + "|   ")
            if len(solutionOptions[1])>0:
                AND_List[1].append(solutionOptions)
    progSpec.setLibLevels(childLibList)
    return AND_List

def ChooseLibs(classes, buildTags, tags):
    """Entry point to libraryMngr

    tags: dict
    """

    featuresHandled.clear()
    cdlog(0,  "\n##############   C H O O S I N G   L I B R A R I E S")
    featuresNeeded = progSpec.fetchTagValue([tags], 'featuresNeeded')
    initialNeeds1 = []
    for feature in featuresNeeded:
        featuresNeeded.extend(fetchFeaturesNeededByLibrary(feature))
        if not feature in initialNeeds1: initialNeeds1.append(feature)

    initialNeeds2 =[]
    for feature in initialNeeds1:
        initialNeeds2.append(['feature',feature])
    solutionOptions = constructANDListFromNeeds([tags, buildTags], initialNeeds2, [], "")
    reduceSolutionOptions(solutionOptions, '')
    for libPath in solutionOptions[1]:
        cdlog(2, "USING LIBRARY:"+libPath)
    return solutionOptions[1]
