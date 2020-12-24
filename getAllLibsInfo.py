#!/usr/bin/env python3
# AnalyzeLibs.py
import progSpec
import os
import subprocess
import buildAndroid
import errno
import shutil
from progSpec import cdlog, cdErr



libPaths    = []
##################################################
def runCMD(myCMD):
    currentDirectory = currentWD = os.getcwd()
    pipe = subprocess.Popen(myCMD, cwd=currentDirectory, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    if out:
        print("        Result: ",out)
    if err:
        print("\n", err)
        exit(1)
    return [out, err]

def connectLibraries():
    global libPaths
    for filename in libPaths:
        runCMD("python3 getLibInfo.py "+filename+"")

def collectLibFilenamesFromFolder(folderPath):
    global libPaths
    for filename in os.listdir(folderPath):
        if filename.endswith("Lib.dog"):
            libPaths.append(os.path.join(folderPath, filename))

def analyzeAllLibs():
    global libPaths
    collectLibFilenamesFromFolder("LIBS/")
    connectLibraries()

analyzeAllLibs()

