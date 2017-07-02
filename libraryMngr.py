# This module manages dog files that describe libraries

import os
import progSpec
import re
import codeDogParser
from progSpec import cdlog, cdErr
from os.path import abspath
from inspect import getsourcefile

libDescriptionFileList = []

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


def ChooseLibs(objects, buildTags, tags):
    cdlog(0,  "\n##############   C H O O S I N G   L I B R A R I E S")
    # TODO: Why is fetchTagValue called with tags, not [tags]?
    #libList = progSpec.fetchTagValue([tags], 'libraries')
    Platform= progSpec.fetchTagValue([tags, buildTags], 'Platform')
    Language= progSpec.fetchTagValue([tags, buildTags], 'Lang')
    CPU     = progSpec.fetchTagValue([tags, buildTags], 'CPU')
    cdlog(1, "PLATFORM: {}   LANGUAGE: {}   CPU:{}".format(Platform, Language, CPU))
    
    featuresNeeded = progSpec.fetchTagValue([tags], 'featuresNeeded')
    compatibleLibs=[]
    for feature in featuresNeeded:
        featurePath = findLibrary(feature)
        cdlog(2, "Parsing feature file: " + featurePath)
        childLibsList= findLibraryChildren(os.path.basename(featurePath)[:-4])
        for lib in childLibsList:
            libTags = loadTagsFromFile(lib)
            #print "        libTags: ", libTags
            libPlatforms=libTags['LibDescription']['platforms']
            libBindings =libTags['LibDescription']['bindings']
            libCPUs     =libTags['LibDescription']['CPUs']
            libFeatures =libTags['LibDescription']['features']
            LibCanWork=True
            
            if not (libPlatforms and Platform in libPlatforms): LibCanWork=False;
            if not (libBindings and Language in libBindings): LibCanWork=False;
          #  if not (libCPUs and CPU in libCPUs): LibCanWork=False;

            if(LibCanWork):
                print "LibCanWork: ", lib
                cdlog(2, "NOTE: {} would work for this system.".format(lib))
                compatibleLibs.append([feature, featurePath, libTags])
    #print"compatibleLibs:", compatibleLibs
    
    for lib in compatibleLibs:
        cdlog(1, "ERROR PARSING: ")
        cdlog(2, "   Lib file: "+ lib[1])
        libString = progSpec.stringFromFile(lib[1])
        ProgSpec = {}
        objNames = []
        macroDefs= {}
        [tagStore, buildSpecs, objectSpecs] = codeDogParser.parseCodeDogString(libString, ProgSpec, objNames, macroDefs)
    return compatibleLibs



