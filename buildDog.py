# buildDog.py
# import into codeDog.py and call from there
# args to build function: path, libraries etc
# get it to work with C++ or print error msg
import progSpec
import os
import subprocess
import buildAndroid
import buildMac
import errno
import shutil
from progSpec import cdlog, cdErr
from pathlib import Path
from urllib.request import urlopen

#TODO: error handling

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
    decodedOut = bytes.decode(out)
    if decodedOut[-1]=='\n': decodedOut = decodedOut[:-1]
    return decodedOut

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

def copyTree(src, dst):
    if not(os.path.isdir(src)): makeDir(src)
    for item in os.listdir(src):
        #print "item: ", item
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            pass
#            shutil.copytree(s, d, False, None)
        else:
            shutil.copy2(s, d)

def gitClone(*args):
    return subprocess.check_call(['git'] + list(args))

# def extractZip(file):
#     pass
    
def LinuxBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData):
    fileExtension = '.cpp'

    writeFile(buildName, fileName, fileSpecs, fileExtension)
    makeDir(buildName + "/assets")
    copyTree("Resources", buildName+"/assets")

    # implement pip as a subprocess:
    packageDirectory = os.getcwd() + '/' + buildName
    for packageNo in range(len(packageData)):
        packageName = packageData[packageNo][1][0][1][0].replace("'", '')
        fetchMethod = packageData[packageNo][1][1][1][0].replace("'", '')
        # fetchMethod = packageData[packageNo][1][1][1][0].split(':',1)[0].replace("'", '')
        fetchMethodUrl = packageData[packageNo][1][1][1][0].split(':',1)[1].replace("'", '')
        if fetchMethod.startswith("git:"):
            PackagePath = os.getcwd() + '/' + buildName + '/' + packageName
            checkRepo = os.path.isdir(PackagePath)
            if not checkRepo:
                cdlog(1, "Cloning git repository: " + packageName)
                gitClone("clone", fetchMethodUrl, PackagePath, "--quiet")

        elif fetchMethod.startswith("file:"):
            fileExtensionUrl = fetchMethodUrl.rsplit('.', 1)[-1]
            PackagePath = os.getcwd() + '/' + buildName + '/' + packageName + '.' + fileExtensionUrl
            checkRepo = os.path.isfile(PackagePath)
            if not checkRepo:
                stream = urlopen(fetchMethodUrl)
                cdlog(1, "Downloading file: " + packageName)
                with open(PackagePath, 'wb') as file:
                    file.write(stream.read())
                stream.close()

        elif fetchMethod.startswith("zip:"):
            fileExtensionUrl = fetchMethodUrl.rsplit('.', 1)[-1]
            PackagePath = os.getcwd() + '/' + buildName + '/' + packageName + '.' + fileExtensionUrl
            checkDirectory = os.path.isdir(os.getcwd() + '/' + buildName + '/' + packageName)
            checkfile = os.path.isfile(PackagePath)
            if not checkDirectory and not checkfile:
                stream = urlopen(fetchMethodUrl)
                cdlog(1, "Downloading zip file: " + packageName)
                with open(PackagePath, 'wb') as file:
                    file.write(stream.read())
                stream.close()

            #Extract zip file
            checkfile = os.path.isfile(PackagePath)
            if not checkDirectory and checkfile:
                if fetchMethodUrl.endswith(".zip"):
                    cdlog(1, "Extracting zip file: " + packageName)

                elif fetchMethodUrl.endswith(".gz"):
                    cdlog(1, "Extracting zip file: " + packageName)

                elif fetchMethodUrl.endswith(".tar"):
                    cdlog(1, "Downloading zip file: " + packageName)

                else:
                    pass
        else:
            pass

    #building scons file
    SconsFile = "import os\n"
    SconsFile += "\nenv = Environment(ENV=os.environ)\nenv.MergeFlags('-g -fpermissive')\n"
    if progOrLib=='program': SconsFileType = "Program"
    elif progOrLib=='library': SconsFileType = "Library"
    elif progOrLib=='staticlibrary': SconsFileType = "StaticLibrary"
    elif progOrLib=='sharedlibrary': SconsFileType = "SharedLibrary"
    else: SconsFileType = "Library"

    SconsFileOut = 'env.'+SconsFileType+'(\n'
    SconsFileOut += '    target='+'"'+fileName+'",\n'
    SconsFileOut += '    source='+'"'+fileSpecs[0][0]+fileExtension+'",\n'

    codeDogFolder = os.path.dirname(os.path.realpath(__file__))
  #  SconsFileOut += '    env["LIBPATH"]=["'+codeDogFolder+'"],\n'
    sconsConfigs = ""

    sconsLibs     = 'env["LIBS"] = ['
    sconsLibPaths = 'env["LIBPATH"]=["'+codeDogFolder+'"],\n'
    libStr=""
    firstTime = True
    for libFile in libFiles:
        if libFile.startswith('pkg-config'):
            libStr += "`"+libFile+"` "
            sconsConfigs += 'env.ParseConfig("'+libFile+'")\n'
        else:
            if libFile =='pthread':
                sconsConfigs += 'env.MergeFlags("-pthread")\n'
            else:
                libStr += "-l"+libFile
                if not firstTime: sconsLibs += ', '
                firstTime=False
                sconsLibs += '"'+libFile+'"'
    sconsLibs += ']\n'
        #print "libStr: " + libStr
    currentDirectory = currentWD = os.getcwd()
    #TODO check if above is typo
    workingDirectory = currentDirectory + "/" + buildName
    buildStr = getBuildSting(fileName,libStr,platform,buildName)
    runStr = "./" + fileName
    SconsFileOut += '    )\n'
    SconsFile += sconsLibPaths + sconsLibs + sconsConfigs + SconsFileOut + '\n'
    writeFile(buildName, 'SConstruct', [[['SConstruct'],SconsFile]], "")
    return [workingDirectory, buildStr, runStr]

def WindowsBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs):
    buildStr = ''
    codeDogFolder = os.path.dirname(os.path.realpath(__file__))
    libStr = "-I " + codeDogFolder + " "
    #minLangStr = '-std=gnu++' + minLangVersion + ' '
    fileExtension = '.cpp'
    #outputFileStr = '-o ' + fileName

    writeFile(buildName, fileName, fileSpecs, fileExtension)
    makeDir(buildName + os.sep + "assets")
    copyTree("Resources", buildName + os.sep + "assets")

    for libFile in libFiles:
        libStr += "-l"+libFile+ " "
        #print "libStr: " + libStr

    currentDirectory = currentWD = os.getcwd()
    #TODO check if above is typo
    workingDirectory = currentDirectory + os.sep + buildName
    buildStr = getBuildSting(fileName,"",platform,buildName)
    runStr = "python " + "..\CodeDog\\" + fileName
    return [workingDirectory, buildStr, runStr]

def SwingBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs):
    fileExtension = '.java'

    writeFile(buildName, fileName, fileSpecs, fileExtension)
    makeDir(buildName + "/assets")
    copyTree("Resources", buildName+"/assets")
    currentDirectory = currentWD = os.getcwd()
    #TODO check if above is typo
    workingDirectory = currentDirectory + "/" + buildName
    buildStr = getBuildSting(fileName,"",platform,buildName)
    runStr = "java GLOBAL"
    return [workingDirectory, buildStr, runStr]

def SwiftBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs):
    # reference https://swift.org/getting-started/#using-the-package-manager
    buildStr = ''
    fileExtension = '.swift'
    currentDirectory = currentWD = os.getcwd()
    workingDirectory = currentDirectory + "/" + buildName
    makeDir(buildName)
    writeFile(workingDirectory, fileName, fileSpecs, fileExtension)
    buildStr = getBuildSting(fileName,"",platform,buildName)
    runStr = "./" + fileName
    return [workingDirectory, buildStr, runStr]

def iOSBuilder(debugMode, minLangVersion, projectName, libFiles, buildName, platform, fileSpecs):
    # reference https://swift.org/getting-started/#using-the-package-manager
    # building without Xcode: https://theswiftdev.com/how-to-build-macos-apps-using-only-the-swift-package-manager/
    fileExtension    = '.swift'
    fileName         =  'main'
    currentDirectory = currentWD = os.getcwd()
    buildDirectory   = buildName
    projectDirectory = buildDirectory + '/' + projectName
    projectSubDir    = projectDirectory + '/' + projectName
    SDK_Path         = runCMD('xcrun --sdk iphonesimulator --show-sdk-path', currentDirectory)
    TARGET           = 'x86_64-apple-ios12.0-simulator'
    ############################################################
    makeDir(buildDirectory)
    makeDir(projectDirectory)
    makeDir(projectSubDir)
    makeDir(projectSubDir+'/Assets.xcassets')
    makeDir(projectSubDir+'.xcodeproj')
    ############################################################
    buildCmd        = 'swiftc '+projectName+'/main.swift -sdk '+SDK_Path+' -target '+TARGET+' -emit-executable -o '+projectSubDir+' -suppress-warnings'
    runCmd          = "swift run  -Xswiftc -suppress-warnings"
    ############################################################
    writeFile(projectDirectory+'/'+projectName, fileName, fileSpecs, fileExtension)
    return [projectDirectory, buildCmd, runCmd]

def printResults(workingDirectory, buildStr, runStr):
    cdlog(1, "Compiling From: {}".format(workingDirectory))
    print("     NOTE: Build Command is: ", buildStr, "\n")
    print("     NOTE: Run Command is: ", runStr, "\n")
    #print ("workingDirectory: ", workingDirectory)
    pipe = subprocess.Popen(buildStr, cwd=workingDirectory, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    if out: print("Result: \n",out.decode('utf-8'))
    if err:
        decodedErr = err.decode('UTF-8')
        if "error:" in decodedErr:
            print("Error Messages:\n--------------------------\n", err.decode('UTF-8'))
            print("--------------------------")
            exit(2)
    else: cdlog(1, "SUCCESS!")

def build(debugMode, minLangVersion, fileName, labelName, launchIconName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData):
    cdlog(0,"\n##############   B U I L D I N G    S Y S T E M...   ({})".format(buildName))
    progOrLib = progOrLib.lower()
    if platform == 'Linux':
        [workingDirectory, buildStr, runStr] = LinuxBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData)
    elif platform == 'Java' or  platform == 'Swing':
        [workingDirectory, buildStr, runStr] = SwingBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs)
    elif platform == 'Android':
        buildAndroid.AndroidBuilder(debugMode, minLangVersion, fileName, labelName, launchIconName, libFiles, buildName, platform, fileSpecs)
    elif platform == 'Swift':
        [workingDirectory, buildStr, runStr] = SwiftBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs)
    elif platform == 'Windows':
        [workingDirectory, buildStr, runStr] = WindowsBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs)
    elif platform == 'MacOS':
        [workingDirectory, buildStr, runStr] = buildMac.macBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs)
    elif platform == 'IOS':
        [workingDirectory, buildStr, runStr] = iOSBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs)
    else:
        print("buildDog.py error: build string not generated for "+ buildName)
        exit(2)
    if platform!='Android': printResults(workingDirectory, buildStr, runStr)
    print("--------------------------")
    return

def getBuildSting (fileName, buildStr_libs, platform, buildName):
    global globalTagStore
    if platform == 'Linux':
        """
        debugMode='-g'
        minLangVersion='17'
        codeDogFolder = os.path.dirname(os.path.realpath(__file__))
        libStr = "-I " + codeDogFolder + " "
        langStr = 'g++'
        langStr += ' -fdiagnostics-color '  # Add color to the output
        langStr += ' -fcompare-debug-second '  # supress compiler notes
        minLangStr = '-std=gnu++' + minLangVersion + ' '
        fileExtension = '.cpp'
        fileStr = fileName + fileExtension
        outputFileStr = '-o ' + fileName
        libStr += buildStr_libs
        buildStr = langStr + debugMode + " " + minLangStr + fileStr  + " " + libStr + " " + outputFileStr
        """

        currentFileDir = os.path.dirname(__file__)
        buildStr = f"python3 {currentFileDir}/Scons/scons.py"
    elif platform == 'Java' or  platform == 'Swing':
        buildStr = ''
        libStr = ''
        langStr = 'javac '
        minLangStr = ''
        fileExtension = '.java'
        fileStr = fileName + fileExtension
        outputFileStr = ''
        debugMode = ''
        buildStr = langStr + debugMode + " " + minLangStr + fileStr + libStr + " " + outputFileStr
    elif platform == 'Android':
        currentDir     = os.getcwd()
        buildStr='     NOTE: Working Directory is  '+currentDir + '/' + buildName + "\n"
        buildStr += '//     NOTE: Build Debug command:    ./gradlew assembleDebug --stacktrace \n'
        buildStr += '//     NOTE: Build Release command:  ./gradlew assembleRelease --stacktrace \n'
        buildStr += '//     NOTE: Install command:        ./gradlew installDebug'
    elif platform == 'Swift':
        fileExtension = '.swift'
        buildStr = "swiftc -suppress-warnings " + fileName + fileExtension
    elif platform == 'Windows':
        langStr = 'cl /EHsc'
        fileExtension = '.cpp'
        fileStr  = fileName + fileExtension
        buildStr = langStr + " " + fileStr
    elif platform == 'MacOS':
        buildStr = "// swift build -Xswiftc -suppress-warnings \n"
        buildStr += "// swift run  -Xswiftc -suppress-warnings \n"
    else:
        buildStr=''
    return buildStr
