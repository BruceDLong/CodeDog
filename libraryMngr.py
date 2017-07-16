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

tagsFromLibFiles = {}

def getTagsFromLibFiles():
    return tagsFromLibFiles

def filterReqTags(ReqTags):
    filteredTags=[]
    for tag in ReqTags[0][1]:
        filteredTags.append(tag[0])
    return [filteredTags]
    
def extractLibTags(library):
    global tagsFromLibFiles
    libTags = loadTagsFromFile(library)
    tagsFromLibFiles[library] = libTags
    ReqTags = progSpec.fetchTagValue([libTags], 'requirements')
    if ReqTags == None: ReqTags =[]
    if len(ReqTags)>0: ReqTags = filterReqTags(ReqTags)
    interfaceTags = progSpec.fetchTagValue([libTags], 'interface')
    if interfaceTags == None: interfaceTags =[]
    return [ReqTags,interfaceTags]

featuresHandled = []

def clearFeaturesHandled():
    featuresHandled = []

def constructORListFromFiles(tags, need, files, indent):
    print indent + "--------------------------------------------------------"
    #print indent + "need: ", need
    #print indent + "files: ", files
    OR_List = ['OR', []]
    for libFile in files:
        print indent + "LIB FILE: ", libFile
        [ReqTags,interfaceTags] = extractLibTags(libFile)
        Requirements = []
        LibCanWork=True
        if need[0] == 'require':
            if 'provides' in interfaceTags:
                if need[1] in interfaceTags['provides']:
                    print indent, 'REQUIRE: ', need[1], ' in ' ,interfaceTags['provides']
                    LibCanWork = True
        for Req in ReqTags:
            #print indent + "Req: ",Req
            if Req[1][0][0]=='feature':
                print "\n    Nested Features should be implemented. Please implement them. (", Req[1], ")n"; exit(2);
            elif Req[0]=='require': 
                print indent + " FOUND REQ: ",Req
                Requirements.append(Req)
            elif Req[1][0][0]=='tagOneOf':
                print indent + "tagOneOf",Req[1][0][0]
                tagToCheck = Req[1]
                validValues = Req[2]
                parentTag = progSpec.fetchTagValue([libTags], tagToCheck)  # E.g.: "platform"
                if parentTag==None: print "WARNING: The tag", tagToCheck, "was not found in", libFile, ".\n"
                if not parentTag in validValues: LibCanWork=False


        if(LibCanWork):
            print indent + " LIB CAN WORK"
            childFileList = findLibraryChildren(os.path.basename(libFile)[:-4])
            print indent + " CHILD FILE LIST: ", childFileList
            if len(childFileList)>0:
                item = constructANDListFromNeeds(tags, Requirements, childFileList, indent + "|   ")
                item[1] = [libFile] + item[1]
                OR_List[1].extend(item)
                print "OR-LIST:", OR_List
            else: OR_List[1].append(libFile)
    print indent + "--------------------------------------------------------"
    if len(OR_List[1])==1 and isinstance(OR_List[1][0], basestring): return OR_List[1][0]
    return OR_List


def constructANDListFromNeeds(tags, needs, files, indent):
    global featuresHandled
    AND_List = ['AND', []]
    print indent + "______________________________________________________"
    print indent + "*FILE*: ", files
    print indent + "*NEEDS*: ", needs
    for need in needs:
        #print indent + "**need*: ", need 
        if need[0] == 'feature':
            if need[1] in featuresHandled: continue
            featuresHandled.append(need[1])
            filesToTry = [findLibrary(need[1])]
            #AND_List[1].append(filesToTry[0])
        else: filesToTry = files
        if len(filesToTry)>0:
            solutionOptions = constructORListFromFiles(tags, need, filesToTry, indent + "|   ")
            print indent + "**solutionOptions: ", solutionOptions 
            if len(solutionOptions[1])>0:
                AND_List[1].append(solutionOptions)
    print indent + "______________________________________________________"
    if len(AND_List[1])==1 and isinstance(AND_List[1][0], basestring): return AND_List[1][0]
    return AND_List

initCodeAcc= ""
deinitCodeAcc= ""

def getinitCodeAccs():
    global initCodeAcc
    global deinitCodeAcc
    return [initCodeAcc, deinitCodeAcc]
    
def clearInitCodeAccs():
    global initCodeAcc
    global deinitCodeAcc
    initCodeAcc= ""
    deinitCodeAcc= ""
    
def ChooseLibs(objects, buildTags, tags):
    global initCodeAcc
    global deinitCodeAcc
    clearInitCodeAccs()
    clearFeaturesHandled()
    cdlog(0,  "\n##############   C H O O S I N G   L I B R A R I E S")
    featuresNeeded = progSpec.fetchTagValue([tags], 'featuresNeeded')
    initialNeeds =[]
    for feature in featuresNeeded:
        initialNeeds.append(["feature", feature])
    #cdlog(1, "PLATFORM: {}   LANGUAGE: {}   CPU:{}   Features needed:{}".format(Platform, Language, CPU, featuresNeeded))
    compatibleLibs = constructANDListFromNeeds(tags, initialNeeds, [], "")
    print "_____________________________________________________\nCOMPATABLE LIBRARIES: \n", compatibleLibs, "\n______________________________________________________"
    exit(2)

    for lib in compatibleLibs[1]:
        #print "    lib: ", lib
        cdlog(2, "   Lib file: "+ str(lib))
        libString = progSpec.stringFromFile(lib)
        ProgSpec = {}
        objNames = []
        macroDefs= {}
        [tagStore, buildSpecs, objectSpecs] = codeDogParser.parseCodeDogString(libString, ProgSpec, objNames, macroDefs)
        if 'initCode' in tagStore:
            initCodeAcc += tagStore['initCode'] +"\n"
        if 'deinitCode' in tagStore:
            deinitCodeAcc += tagStore['deinitCode'] +"\n"
    return compatibleLibs[1]
