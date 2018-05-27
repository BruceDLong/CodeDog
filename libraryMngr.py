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
        if filename.endswith("Lib.dog"):
            libDescriptionFileList.append(os.path.join(folderPath, filename))
        elif filename.endswith("Lib.dog.proxy"):
            line = open(os.path.join(folderPath, filename)).readline()
            line=line.strip()
            baseName = os.path.basename(line)
            #print"baseName: ", baseName
            if (filename.strip('.proxy') == baseName):
                libDescriptionFileList.append(os.path.realpath(line))
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

def findLibrary(feature):
    for item in libDescriptionFileList:
        if(os.path.basename(item) == feature+".Lib.dog"):
            return item
    return ""

def findLibraryChildren(libID):
    libs=[]
    for item in libDescriptionFileList:
        itemBaseName = os.path.basename(item)
        if(itemBaseName.endswith('Lib.dog') and itemBaseName.startswith(libID)):
            innerName = itemBaseName[len(libID)+1:-8]
            if (innerName != '' and innerName.find('.')==-1):
                libs.append(item)
    return libs

def replaceFileName(fileMatch):
    fileName = fileMatch.group(1)
    currentWD = os.getcwd()
    pathName = abspath(currentWD) +"/"+fileName
    if not os.path.isfile(pathName):
        dirname, filename = os.path.split(abspath(getsourcefile(lambda:0)))
        pathName = dirname +"/"+fileName
        if not os.path.isfile(pathName):
            cdErr("Cannot find include file '"+fileName+"'")

    includedStr = progSpec.stringFromFile(pathName)
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

def libListType(libList):
    if isinstance(libList, basestring): return "STRING"
    op=libList[0]
    if (op=='AND' or op=='OR'):
        return op
    print "WHILE EXAMINING:", libList
    cdErr('Invalid type encountered for a library identifier:'+str(op))

def reduceSolutionOptions(options, indent):
    #print indent+"OPTIONS:", options
    optionsOp=libListType(options)
    if optionsOp != 'STRING':
        i=0
        while i<len(options[1]):
            opt=options[1][i]
            if not isinstance(opt, basestring):
                reduceSolutionOptions(options[1][i], indent+'|   ')
                if len(opt[1])==0: del options[1][i]; print "DELETED:", i; continue;
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
                        print "CROSS"

                   # removeDuplicates(options)  # TODO: Make this line remove duplicates

            i+=1
def fetchFeaturesNeededByLibrary(feature):
    return []

def checkIfLibFileMightSatisyNeedWithRequirements(tags, need, libFile, indent):
    [ReqTags,interfaceTags] = extractLibTags(libFile)
    print "NEED:", need
    print "REQUIREMENTs:", ReqTags
    Requirements = []
    LibCanWork=True
    if need[0] == 'require':
        LibCanWork=False
        if 'provides' in interfaceTags:
            if need[1] in interfaceTags['provides']:
                #print indent, 'REQUIRE: ', need[1], ' in ' ,interfaceTags['provides']
                LibCanWork = True

    for Req in ReqTags:
       # print "REQUIREMENT:", Req[0], Req[1]
        if Req[0]=='feature':
            print "\n    Nested Features should be implemented. Please implement them. (", Req[1], ")n"; exit(2);
        elif Req[0]=='require':
            Requirements.append(Req)
        elif Req[0]=='tagOneOf':
            tagToCheck = Req[1]
            validValues = progSpec.extractListFromTagList(Req[2])
            parentTag = progSpec.fetchTagValue(tags, tagToCheck)  # E.g.: "platform"
            if parentTag==None: LibCanWork=False;  cdErr("ERROR: The tag '"+ tagToCheck + "' was not found in" + libFile + ".\n");
            if not parentTag in validValues: LibCanWork=False
            else: cdlog(1, "  Validated: "+tagToCheck+" = "+parentTag)

    return [LibCanWork, Requirements]

def constructORListFromFiles(tags, need, files, indent):
    OR_List = ['OR', []]
    for libFile in files:
        #print indent + "LIB FILE: ", libFile
        [LibCanWork, Requirements] = checkIfLibFileMightSatisyNeedWithRequirements(tags, need, libFile, indent)
        if(LibCanWork):
            #print indent + " LIB CAN WORK:", libFile
            childFileList = findLibraryChildren(os.path.basename(libFile)[:-8])
            if len(childFileList)>0:
                solutionOptions = constructANDListFromNeeds(tags, Requirements, childFileList, indent + "|   ")
                solutionOptions[1] = [libFile] + solutionOptions[1]
                OR_List[1].append(solutionOptions)
            else: OR_List[1].append(libFile)
    if len(OR_List[1])==1 and isinstance(OR_List[1][0], basestring): return OR_List[1][0]  # Optimization
    return OR_List

def constructANDListFromNeeds(tags, needs, files, indent):
    global featuresHandled
    AND_List = ['AND', []]
    for need in needs:
        #print indent + "**need*: ", need
        if need[0] == 'feature':
            if need[1] in featuresHandled: continue
            cdlog(1, "FEATURE: "+str(need[1]))
            featuresHandled.append(need[1])
            filesToTry = [findLibrary(need[1])]
            if filesToTry[0]=='': cdErr('Could not find a dog file for feature '+need[1])
        else: filesToTry = files
        if len(filesToTry)>0:
            solutionOptions = constructORListFromFiles(tags, need, filesToTry, indent + "|   ")
            if len(solutionOptions[1])>0:
                AND_List[1].append(solutionOptions)
    return AND_List

def ChooseLibs(classes, buildTags, tags):
    clearFeaturesHandled()
    cdlog(0,  "\n##############   C H O O S I N G   L I B R A R I E S")
    featuresNeeded = progSpec.fetchTagValue([tags], 'featuresNeeded')
    print "FEATURES-NEEDED:", featuresNeeded
    initialNeeds =[]
    for feature in featuresNeeded:
        featuresNeeded.extend(fetchFeaturesNeededByLibrary(feature))
        initialNeeds.append(["feature", feature])
    solutionOptions = constructANDListFromNeeds([tags, buildTags], initialNeeds, [], "")
    reduceSolutionOptions(solutionOptions, '')
    for libPath in solutionOptions[1]: cdlog(2, "USING LIBRARY:"+libPath)
    return solutionOptions[1]
