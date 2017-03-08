# buildDog.py
# import into codeDog.py and call from there
# args to build function: path, libraries etc
# get it to work with C++ or print error msg
import progSpec
import os
import subprocess
import buildAndroid
import errno

#TODO: error handling

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

def writeFile(path, fileName, fileSpecs, fileExtension):
    #print path
    makeDir(path)
    fileName += fileExtension
    fo=open(path + os.sep + fileName, 'w')
    fo.write(fileSpecs[0][1])
    fo.close()

def LinuxBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs):
    buildStr = ''
    libStr = ''
    langStr = 'g++ '
    minLangStr = '-std=gnu++' + minLangVersion + ' '
    fileExtension = '.cpp'
    fileStr = fileName + fileExtension
    outputFileStr = '-o ' + fileName

    writeFile(buildName, fileName, fileSpecs, fileExtension)

    for libFile in libFiles:
        if libFile.startswith('pkg-config'):
            libStr += "`"
            libStr += libFile
            libStr += "`"
        else:
            libStr += libFile
        #print "libStr: " + libStr
    currentDirectory = currentWD = os.getcwd()
    #TODO check if above is typo
    workingDirectory = currentDirectory + "/" + buildName
    buildStr = langStr + debugMode + " " + minLangStr + fileStr  + " " + libStr + " " + outputFileStr
    return [workingDirectory, buildStr]

def SwingBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs):
    buildStr = ''
    libStr = ''
    langStr = 'javac '
    minLangStr = ''
    fileExtension = '.java'
    fileStr = fileName + fileExtension
    outputFileStr = ''
    debugMode = ''

    writeFile(buildName, fileName, fileSpecs, fileExtension)

    for libFile in libFiles:
        libStr += libFile
        #print "libStr: " + libStr
    currentDirectory = currentWD = os.getcwd()
    #TODO check if above is typo
    workingDirectory = currentDirectory + "/" + buildName
    buildStr = langStr + debugMode + " " + minLangStr + fileStr + libStr + " " + outputFileStr
    return [workingDirectory, buildStr]
    
def SwiftBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs):
    buildStr = ''
    libStr = ''
    fileExtension = '.swift'
    sourcePath = buildName + "/" + "Sources"
    currentDirectory = currentWD = os.getcwd()
    workingDirectory = currentDirectory + "/" + buildName
    
    makeDir(buildName)
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
    return [workingDirectory, buildStr]

def printResults(workingDirectory, buildStr):
    print "buildStr: ", buildStr
    print "workingDirectory: ", workingDirectory
    pipe = subprocess.Popen(buildStr, cwd=workingDirectory, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    if out: print "Result: ",out
    if err:
        print "Error: ", err
        exit(2)

def build(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs):
    "\n\n######################   B U I L D I N G    S Y S T E M"
    if platform == 'Linux':
        [workingDirectory, buildStr] = LinuxBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs)
        printResults(workingDirectory, buildStr)
    elif platform == 'Java':
        [workingDirectory, buildStr] = SwingBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs)
        printResults(workingDirectory, buildStr)
    elif platform == 'Android':
        buildAndroid.AndroidBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs)
    elif platform == 'XCODE':
        [workingDirectory, buildStr] = SwiftBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs)
        printResults(workingDirectory, buildStr)
    else:
        print "buildDog.py error: build string not generated for "+ buildName
        exit(2)
    return
