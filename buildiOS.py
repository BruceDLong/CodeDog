# buildiOS.py

import os
import subprocess
import errno
import shutil
from progSpec import cdlog, cdErr


def writeFile(path, fileName, fileSpecs, fileExtension):
    #print path
    makeDir(path)
    fileName += fileExtension
    pathName = path + os.sep + fileName
    cdlog(1, "WRITING FILE: "+pathName)
    fo=open(pathName, 'w')
    fo.write(fileSpecs[0][1])
    fo.close()

def runCMD(myCMD, myDir):
    print "        COMMAND: ", myCMD, "\n"
    pipe = subprocess.Popen(myCMD, cwd=myDir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    if out:
        print "        Result: ",out
    if err:
        print "\n", err
        if (err.find("ERROR")) >= 0:
            exit(1)
    return [out, err]

def makeDir(dirToGen):
    #print "dirToGen:", dirToGen
    try:
        os.makedirs(dirToGen)
    except OSError as exception:
        if exception.errno != errno.EEXIST: raise



def swiftBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, outStr):
    # reference https://swift.org/getting-started/#using-the-package-manager
    buildStr = ''
    libStr = ''
    fileExtension = '.swift'
    sourcePath = buildName + "/" + fileName + "/" + "Sources"
    currentDirectory = currentWD = os.getcwd()
    workingDirectory = currentDirectory + "/" + buildName + "/" + fileName

    makeDir(buildName)
    makeDir(buildName + "/" + fileName)
    runCMD("swift package init --type executable", workingDirectory)
    writeFile(sourcePath, "main", fileSpecs, fileExtension)

    for libFile in libFiles:
        if libFile.startswith('pkg-config'):
            libStr += "`"
            libStr += libFile
            libStr += "`"
        else:
            libStr += libFile
        #print "libStr: " + libStr

    buildStr = "swift build"
    runStr = ".build/debug/" + fileName
    return [workingDirectory, buildStr, runStr]

def pbxprojFileCreate(workingDir):
    print '--------------------------------   Generating project.pbxproj \n'
    fileName = "project.pbxproj"
    outStr = '// !$*UTF8*$!\n'\
             '{\n'\
             '    archiveVersion = 1;\n'\
             '    classes = {};\n'\
             '    objectVersion = 48;\n'\
             '    objects = {};\n'\
             '    rootObject = '+KEY+' /* Project object */;\n'\
             '}\n'\

    fo=open(workingDir + os.sep + fileName, 'w')
    fo.write(outStr)
    fo.close()


def createProject(workingDirectory, fileName, fileSpecs):
    projectDir=workingDirectory+'.xcodeproj'
    makeDir(projectDir)
    sourceDir=workingDirectory+'/'+fileName
    makeDir(sourceDir)
    writeFile(sourceDir, fileName, fileSpecs, '.swift')
    pbxprojFileCreate(workingDirectory)




def xCodeCompile(fileName, workingDirectory):
    print"    Generating .app file"
    outputTag = 'OBJROOT='+workingDirectory+'/Obj.root SYMROOT='+workingDirectory+'/sym.root '
    buildStr = "xcodebuild -target "+ fileName+outputTag
    runCMD(buildStr, workingDirectory)

#def SignAndBundle(workingDirectory,fileName):
    # reference https://code.tutsplus.com/tutorials/continuous-integration-scripting-xcode-builds--pre-25512
    #outputTag = '-o "'+workingDirectory+'/'+fileName+'.ipa" --sign'
    #myCMD='xcrun -sdk iphoneos PackageApplication -v "'+fileName+'.app"'
    #symDir=workingDirectory+"/sym.root "
    #runCMD(myCMD, symDir)


def iOSBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs):
    sourcePath = buildName + "/" + fileName + "/" + "Sources"
    currentDirectory = currentWD = os.getcwd()
    workingDirectory = currentDirectory + "/" + buildName + "/" + fileName
    makeDir(buildName)
    makeDir(buildName + "/" + fileName)

    print 'Building for iOS'

    [osStr, err]=runCMD("uname", currentDirectory)
    if osStr[:6]=='Darwin':
        createProject(workingDirectory, fileName, fileSpecs)
        xCodeCompile(fileName, workingDirectory)




    else:
        print"buildDog.iosBuilder: unknown OS: '", osStr, "'"
        exit(1)

    print 'Finished Building for iOS'
