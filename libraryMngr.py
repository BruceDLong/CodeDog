# This module manages dog files that describe libraries

import os
import progSpec
import re
import codeDogParser
from progSpec import cdlog, cdErr
from os.path import abspath
from inspect import getsourcefile

libDescriptionFileList = []

'''
T h e   b e s t   l i b r a r y   c h o i c e s   f o r   y o u r   p r o g r a m
  And the best programs for your library

Whether you are writing a program for which library choices will be made, or a library which will be
chosen for use with different programs, you want to have codeDog make the best choices.

You can get the results you want by knowing how CodeDog makes its descision about which libraries to use.

The way libraries are chosen in most languages
is that they're given by the programmer.
But code written to work on many different platforms
is easiest to create when the decision is left to the compiler.

In codeDog the problem is solved by telling
the compiler about features and needs instead of about the libraries.
The compiler then chooses which libraries to link from needs the progam has listed.

There are two kinds of need that the programmer can then specify in dog files:
We'll call them 'features' and 'components'. Features are functionality that must be added to codeDog
in order for your program to work. GUI-toolkit, Unicode, Math-kit, Networking. Feautures often
correspond to actual libraries. Components are files that describe libraries that may be specific to
particular platforms. GTK3, XCODE, etc. Both features and components are "needs" that are specified with tags.



'''

def collectLibFilenamesFromFolder(folderPath):
    for filename in os.listdir(folderPath):
        if filename.startswith('Lib.'):
            if filename.endswith(".dog"):
                libDescriptionFileList.append(os.path.join(folderPath, filename))
            elif filename.endswith(".dog.proxy"):
                line = open(os.path.join(folderPath, filename)).readline()
                line=line.strip()
                baseName = os.path.basename(line)
                if (filename.strip('.proxy') == baseName):
                    libDescriptionFileList.append(line)
                else:
                    cdErr("File name does not match path name.")

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

def findLibrary(feature):
    for item in libDescriptionFileList:
        if(os.path.basename(item) == "Lib."+feature+".dog"):
            return item
    return ""

def findLibraryChildren(libID):
    libs=[]
    for item in libDescriptionFileList:
        itemBaseName = os.path.basename(item)
        if(itemBaseName.endswith('.dog') and itemBaseName.startswith(libID)):
            innerName = itemBaseName[len(libID)+1:-4]
            if (innerName != '' and innerName.find('.')==-1):
                libs.append(item)
    return libs

def replaceFileName(fileMatch):
    dirname, filename = os.path.split(abspath(getsourcefile(lambda:0)))
    includedStr = progSpec.stringFromFile(dirname +"/"+fileMatch.group(1))
    includedStr = processIncludedFiles(includedStr)
    return includedStr

def processIncludedFiles(fileString):
    pattern = re.compile(r'#include +([\w -\.\/\\]+)')
    return pattern.sub(replaceFileName, fileString)

def loadTagsFromFile(fileName):
    codeDogStr = progSpec.stringFromFile(fileName)
    codeDogStr = processIncludedFiles(codeDogStr)
    return codeDogParser.parseCodeDogLibTags(codeDogStr)

def constructORListFromFiles(tags, needs, files):
    OR_List = ['OR', []]
    for libFileName in files:
        libTags = loadTagsFromFile(libFileName)
        ReqTags = progSpec.fetchTagValue([libTags], 'requirements')
        #print "        libTags: ", libTags
        Requirements = []
        LibCanWork=True
        for Req in ReqTags:
            if Req[0]=='feature':
                print "\nNested Features should be implemented. Please implement them. (", Req[1], ")n"; exit(2);
            elif Req[0]=='require': Requirements.append(Req)
            elif Req[0]=='tagOneOf':
                tagToCheck = Req[1]
                validValues = Req[2]
                parentTag = progSpec.fetchTagValue([libTags], tagToCheck)  # E.g.: "platform"
                if parentTag==None: print "WARNING: The tag", tagToCheck, "was not found in", libFileName, ".\n"
                if not parentTag in validValues: LibCanWork=False


        if(LibCanWork):
            print "LibCanWork: ", lib
            childFileList = findLibraryChildren(os.path.basename(featurePath)[:-4])
            item = constructANDListFromNeeds(tags, Reqs, childFileList)
            OR_List.append(item)

    return OR_List


def constructANDListFromNeeds(tags, needs, files):
    AND_List = ['AND', []]
    for N in needs:
        if N[0] == 'feature':
            filesToTry = findLibrary(N[1])
        else: filesToTry = files
        solutionOptions = constructORListFromFiles(tags, N, filesToTry)
        if len(solutionOptions[1])==0:
            cdErr("Library not found for " + str(N))
        AND_List.append(solutionOptions)
    return AND_List

def ChooseLibs(objects, buildTags, tags):
    cdlog(0,  "\n##############   C H O O S I N G   L I B R A R I E S")
    featuresNeeded = progSpec.fetchTagValue([tags], 'featuresNeeded')
    #cdlog(1, "PLATFORM: {}   LANGUAGE: {}   CPU:{}   Features needed:{}".format(Platform, Language, CPU, featuresNeeded))
    compatibleLibs = constructANDListFromNeeds(tags, featuresNeeded, [])


    for lib in compatibleLibs:
        cdlog(1, "ERROR PARSING: ")
        cdlog(2, "   Lib file: "+ lib[1])
        libString = progSpec.stringFromFile(lib[1])
        ProgSpec = {}
        objNames = []
        macroDefs= {}
        [tagStore, buildSpecs, objectSpecs] = codeDogParser.parseCodeDogString(libString, ProgSpec, objNames, macroDefs)
    return compatibleLibs
