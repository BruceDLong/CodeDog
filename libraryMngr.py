# This module manages dog files that describe libraries

import os
import progSpec
from progSpec import cdlog, cdErr

libDescriptionFileList = []

def collectLibFilenamesFromFolder(folderPath):
    for filename in os.listdir(folderPath):
        if filename.startswith('Lib."):
            if filename.endswith(".dog"):
                libDescriptionFileList.append(os.path.join(folderPath, filename))
            elif filename.endswith(".dog.proxy"):
                # TODO: Make proxy lib files work.
                pass

def collectFromFolderOrLIB(pathName):
    collectLibsFromFolder(pathName)
    LIBFOLDER = os.path.join(pathName, "/LIBS")
    if(os.path.isdir(LIBFOLDER)):
        collectLibsFromFolder(LIBFOLDER)

def findLibraryFiles():
    dogFileFolder = os.getcwd()
    codeDogFolder = os.path.dirname(os.path.realpath(__file__))
    collectLibsFromFolder(dogFileFolder)
    collectLibsFromFolder(codeDogFolder)

def indexLibrary(filename):
    pass

def indexLibraries():
    global libDescriptionFileList
    for filename in libDescriptionFileList:
        indexLibrary(fileName)

def chooseLibraries():
    pass
