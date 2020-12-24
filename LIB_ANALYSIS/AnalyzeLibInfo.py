#!/usr/bin/env python3
# AnalyzeLibInfo.py
import os
from pprint import pprint

libPaths = {}
def infoFromFile(filename):
    libInfo = []
    f=open(filename)
    infoStr = f.read()
    f.close()
    libInfo = eval(infoStr)
    return libInfo

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
    print("CHILD LIB: ", child)
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
                    if found == False:print ("    ", parentID,"    missing in child.")
                    elif found != True: print ("    @@@",  parentID," is ", found," in child:")

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

