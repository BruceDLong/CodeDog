# buildMac.py

import os
import subprocess
import errno
import shutil
from progSpec import cdlog, cdErr


def runCMD(myCMD, myDir):
    print("        COMMAND: ", myCMD, "\n")
    pipe = subprocess.Popen(myCMD, cwd=myDir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    if out:
        print("        Result: ",out)
    if err:
        print("\n", err)
        if (err.find("ERROR")) >= 0:
            exit(1)
    return [out, err]

def makeDir(dirToGen):
    #print "dirToGen:", dirToGen
    try:
        os.makedirs(dirToGen)
    except OSError as exception:
        if exception.errno != errno.EEXIST: raise

def writeFile(path, fileName, fileSpecs, fileExtension):
    #print path
    makeDir(path)
    fileName += fileExtension
    pathName = path + os.sep + fileName
    cdlog(1, "WRITING FILE: "+pathName)
    fo=open(pathName, 'w')
    fo.write(fileSpecs[0][1])
    fo.close()

def macBuilder(debugMode, minLangVersion, projectName, libFiles, buildName, platform, fileSpecs):
    # reference https://swift.org/getting-started/#using-the-package-manager
    # building without Xcode: https://theswiftdev.com/how-to-build-macos-apps-using-only-the-swift-package-manager/
    fileExtension    = '.swift'
    fileName         =  "main"
    currentDirectory = currentWD = os.getcwd()
    buildDirectory   = currentDirectory + "/" + buildName
    projectDirectory = buildDirectory + "/" + projectName
    makeDir(buildName)
    makeDir(buildName+"/"+projectName)
    ############################################################
    rmPackageCmd    = "rm Package.swift"
    packageInitCmd  = "swift package init --type executable"
    buildCmd        = "swift build -Xswiftc -suppress-warnings"
    runCmd          = "swift run "
    ############################################################
    runCMD(rmPackageCmd, projectDirectory)
    runCMD(packageInitCmd, projectDirectory)
    writeFile(projectDirectory+"/Sources/"+projectName, fileName, fileSpecs, fileExtension)
    #runCMD(buildCmd, projectDirectory)
    return [projectDirectory, buildCmd, runCmd]
