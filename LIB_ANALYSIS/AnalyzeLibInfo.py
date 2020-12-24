#!/usr/bin/env python3
# AnalyzeLibInfo.py
import os
from pprint import pprint

libPaths  = {}
libReport = ""

def infoFromFile(filename):
    libInfo = []
    f=open(filename)
    infoStr = f.read()
    f.close()
    libInfo = eval(infoStr)
    return libInfo

def writeReportFile():
    global libReport
    fileName = "LibraryAnalysisReport.txt"
    print("WRITING FILE: "+fileName)
    fo=open(fileName, 'w')
    fo.write(libReport)
    fo.close()

def collectLibFilenamesFromFolder():
    global libPaths
    folderPath = os.getcwd()
    for filename in os.listdir(folderPath):
        if filename.endswith("Lib.dog.info"):
            dotPos=filename.find(".")
            libKey = filename[:dotPos]
            if not libKey in libPaths:
                parent   = ""
                children = []
                libPaths[libKey] = {"parent":parent, "children":children}
            if filename == libKey+".Lib.dog.info":
                libPaths[libKey]["parent"]=filename
            else:
                libPaths[libKey]["children"].append(filename)

def findInChild(className, parentID, childInfo):
    #print(parentID)
    for childClass in childInfo[0][1]:
        childClassName = childClass['className']
        if childClassName == className:
            for childField in childClass['fields']:
                childID = childField['fieldID']
                if childID == parentID:
                    if childField['status'] == 'Impl':return True
                    else: return childField['status']
    return False

def analyzeParentChild(parent, child):
    global libReport
    libReport = libReport + "CHILD LIB: "+ child + "\n"
    parentInfo = infoFromFile(parent)
    childInfo  = infoFromFile(child)
    for parentClass in parentInfo[0][1]:
        if len(parentClass['fields'])==0: continue
        className = parentClass['className']
        #print(className)
        for parentField in parentClass['fields']:
            if 'status' in parentField:
                if parentField['status'] != 'Impl':
                    parentID = parentField['fieldID']
                    found = findInChild(className, parentID, childInfo)
                    if found == False:
                        libReport = libReport + "    " + parentID + "    missing in child.\n"
                    elif found != True:
                        libReport = libReport + "    " + parentID + " is " + found+ " in child.\n"
    #print(libReport)

def getParentChild():
    global libPaths
    for libKey in libPaths:
        if len(libPaths[libKey]) < 2: continue
        parent = libPaths[libKey]["parent"]
        children = libPaths[libKey]["children"]
        if len(children) == 0:continue
        if libKey == "List": continue
        for child in children:
            analyzeParentChild(parent, child)

collectLibFilenamesFromFolder()
getParentChild()
writeReportFile()
