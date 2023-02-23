# buildDog.py

from __future__ import unicode_literals
import progSpec
import os
import subprocess
import buildAndroid
import buildMac
import errno
import shutil
from progSpec import cdlog, cdErr
from pathlib import Path

import environmentMngr as emgr

importantFolders = {}
#TODO: error handling
def string_escape(s, encoding='utf-8'):
    return (s.encode('latin1')         # To bytes, required by 'unicode-escape'
             .decode('unicode-escape') # Perform the actual octal-escaping decode
             .encode('latin1')         # 1:1 mapping back to bytes
             .decode(encoding))        # Decode original encoding

def runCMD(myCMD, myDir):
    print("\nCOMMAND: ", myCMD, "\n")
    pipe = subprocess.Popen(myCMD, cwd=myDir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    if out:
        #print("        Result: ",out)
        pass
    if err:
        print("ERRORS:---------------\n")
        print(string_escape(str(err))[2:-1])
        print("----------------------\n")
        if (err.find(b"ERROR")) >= 0 or err.find(b"error")>=0:
            exit(1)
    #decodedOut = str(out.decode('unicode-escape')) # bytes.decode(out, 'latin1')
    #if decodedOut[-1]=='\n': decodedOut = decodedOut[:-1]
    return string_escape(str(out)).strip()

def runCmdStreaming(myCMD, myDir):
    print("\nCOMMAND: ", myCMD, "\n")
    errText=''
    process = subprocess.Popen(myCMD, cwd=myDir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines = True,)
    while process.poll() is None:
        output = process.stdout.readline()
        if output:
            print(output.strip())
        err = process.stderr.readline()
        while err!='':
            errText += err
            err = process.stderr.readline()
    returnCode = process.returncode
    if returnCode!=0 or (errText and (errText.find("ERROR")) >= 0 or errText.find("error")>=0):
        print("ERRORS:---------------\n")
        #print(string_escape(str(errText))[2:-1])
        print(errText)
        print("----------------------\n")
    return returnCode

def makeDirs(dirToGen):
    #print("dirToGen:", dirToGen)
    try:
        os.makedirs(dirToGen, exist_ok=True)
    except FileExistsError:
        # Another thread was already created the directory when
        # several simultaneous requests has come
        if os.path.isdir(os.path.dirname(dirToGen)):
            pass
        else:
            raise
    except OSError as exception:
        print("ERROR MAKING_DIR", exception)
        if exception.errno != errno.EEXIST: raise

def writeFile(path, fileName, fileSpecs, fileExtension):
    #print path
    makeDirs(path)
    fileName += fileExtension
    pathName = path + os.sep + fileName
    cdlog(1, "WRITING FILE: "+pathName)
    fo=open(pathName, 'w')
    fo.write(fileSpecs[0][1])
    fo.close()

def copyRecursive(src, dst, symlinks=False):
    # modified from python docs
    #print("COPY_TREE:", src, "   TO:", dst)
    if os.path.exists(src) and os.path.isfile(src):
        shutil.copy2(src, dst)
    else:
        names = os.listdir(src)
        makeDirs(dst)
        errors = []
        for name in names:
            srcname = os.path.join(src, name)
            dstname = os.path.join(dst, name)
            try:
                if symlinks and os.path.islink(srcname):
                    linkto = os.readlink(srcname)
                    os.symlink(linkto, dstname)
                elif os.path.isdir(srcname):
                    copyRecursive(srcname, dstname, symlinks)
                else:
                    shutil.copy2(srcname, dstname)
            except OSError as why:
                errors.append((srcname, dstname, str(why)))
            # catch the Error from the recursive copyRecursive so that we can continue with other files
            except shutil.Error as err:
                errors.extend(err.args[0])
        # ~ try:
            # ~ shutil.copystat(src, dst)
        # ~ except OSError as why:
            # ~ # can't copy file access times on Windows
            # ~ if why.winerror is None:
                # ~ errors.extend((src, dst, str(why)))
        # ~ if errors:
            # ~ raise shutil.Error(errors)
def gitClone(cloneUrl, packageName, packageDirectory):
    emgr.CheckPipModules({'GitPython':'3.1'})
    emgr.CheckPipModules({'gcg':'0.2.0'})
    import urllib.request
    from git import Repo
    packagePath = packageDirectory + '/' + packageName + '/' + packageName
    checkRepo = os.path.isdir(packagePath)
    if not checkRepo:
        try:
            urllib.request.urlopen(cloneUrl)
        except (urllib.error.URLError, urllib.error.HTTPError):
            cdErr("URL not found: " + cloneUrl)
        cdlog(1, "Cloning git repository: " + packageName)
        Repo.clone_from(cloneUrl, packagePath)
        makeDirs(packageDirectory + '/' + packageName + "/INSTALL")

def downloadPackageFile(downloadUrl, packageName, packageDirectory):
    downloadFileExtension = downloadUrl.rsplit('.', 1)[-1]
    packagePath = packageDirectory + '/' + packageName + '/' + packageName + '.' + downloadFileExtension
    makeDirs(packageDirectory + '/' + packageName + "/INSTALL")
    makeDirs(os.path.dirname(packagePath))
    checkRepo = os.path.isfile(packagePath)
    if not checkRepo:
        emgr.downloadFile(packagePath, downloadUrl)

def downloadExtractZip(downloadUrl, packageName, packageDirectory):
    zipExtension = ""
    if downloadUrl.endswith(".zip"):
        zipExtension = ".zip"
    elif downloadUrl.endswith(".tar.gz"):
        zipExtension = ".tar.gz"
    elif downloadUrl.endswith(".tar.bz2"):
        zipExtension = ".tar.bz2"
    elif downloadUrl.endswith(".tar.xz"):
        zipExtension = ".tar.xz"
    elif downloadUrl.endswith(".tar"):
        zipExtension = ".tar"
    else:
        pass

    zipFileDir  = packageDirectory + '/' + packageName
    packagePath = zipFileDir + '/' + packageName + zipExtension
    checkDir    = os.path.isdir(zipFileDir)
    zipFileName = os.path.basename(downloadUrl)
    if not checkDir:
        makeDirs(zipFileDir + "/INSTALL")
        emgr.downloadFile(packagePath, downloadUrl)
        try:
            cdlog(1, "Extracting zip file: " + zipFileName)
            shutil.unpack_archive(packagePath, zipFileDir)
        except:
            cdErr("Could not extract zip archive file: " + zipFileName)

def getPackageName(packageMap):
    if 'packageName' in packageMap:
        return(packageMap['packageName'][1:-1])
    return("")

def getInnerPackageName(packageMap):
    if 'innerPkgName' in packageMap:
        return(packageMap['innerPkgName'][1:-1])
    return(getPackageName(packageMap))

def getFetchType(packageMap):
    if 'fetchMethod' in packageMap:
        return(packageMap['fetchMethod'][1:-1].split(':', 1)[0])
    return("")

def getFetchURL(packageMap):
    if 'fetchMethod' in packageMap:
        fetchMethod = packageMap['fetchMethod'][1:-1]
        fetchURL    = packageMap['fetchMethod'][1:-1].split(':', 1)[1]
        splitSpec   = fetchURL.split('@', 1)
        if len(splitSpec)>1: print("TODO: handle fetchMethod @: ",fetchURL)
        fetchURL    = splitSpec[0]
        return(fetchURL)
    return("")

def fetchPackages(packageData, packageDirectory):
    for package in packageData:
        packageMap   = progSpec.extractMapFromTagMap(package)
        packageName  = getPackageName(packageMap)
        fetchType    = getFetchType(packageMap)
        fetchURL     = getFetchURL(packageMap)
        buildCmdsMap = {}
        if packageName=="" or fetchType=="": return
        if fetchType == "git":    gitClone(fetchURL, packageName, packageDirectory)
        elif fetchType == "file": downloadPackageFile(fetchURL, packageName, packageDirectory)
        elif fetchType == "zip":  downloadExtractZip(fetchURL, packageName, packageDirectory)
        elif fetchType == "sys":  emgr.checkAndUpgradeOSPackageVersions(packageName)
        else: pass

def FindOrFetchLibraries(buildName, packageData, platform, tools):
    #print("#############:buildName:", buildName, platform)
    packageDirectory = os.path.join(os.getcwd(), buildName)
    [includeFolders, libFolders] = ["", ""]
    fetchPackages(packageData, packageDirectory)
    for package in packageData:
        packageMap   = progSpec.extractMapFromTagMap(package)
        packageName  = getPackageName(packageMap)
        innerPkgName = getInnerPackageName(packageMap)
        buildCmdsMap = {}
        if 'buildCmds' in packageMap:
            buildCmds = packageMap['buildCmds']
            buildCmdsMap = progSpec.extractMapFromTagMap(buildCmds)
        if buildCmdsMap!={} and platform in buildCmdsMap:
            #print("###########:",platform, ' = ', buildCmdsMap[platform])
            buildCommand = buildCmdsMap[platform]
            buildCmdMap = progSpec.extractMapFromTagMap(buildCommand)
            downloadedFolder = packageDirectory+"/"+packageName+"/"+innerPkgName

            if 'buildCmd' in buildCmdMap:
                actualBuildCmd = buildCmdMap['buildCmd'][1:-1]
                for folderKey,folderVal in importantFolders.items():
                    actualBuildCmd = actualBuildCmd.replace('$'+folderKey,folderVal)
                #print("BUILDCOMMAND:", actualBuildCmd)#, "  INSTALL:", buildCmdsMap[platform][1])

                for toolName in tools:
                    if emgr.checkToolLinux('go' if toolName=='golang-go' else toolName):
                        runCmdStreaming(actualBuildCmd, downloadedFolder)
                    else:
                        packageManager = emgr.findPackageManager()
                        if not packageManager:
                            print(f"Unable to find Package Manager.\nPlease install manually : {packageName}")
                        else:
                            emgr.getPackageManagerCMD(toolName, packageManager, "install")
                        runCmdStreaming(actualBuildCmd, downloadedFolder)

            if 'installFiles' in buildCmdMap:
                installfileList = buildCmdMap['installFiles'][1]
                # ~ installFiles = progSpec.extractListFromTagList(installfileList)
                # ~ print("    DATA:", str(installFiles)[:100])
                LibsFolder = os.path.join(packageDirectory, packageName, 'INSTALL').replace("\\","/")
                makeDirs(LibsFolder)
                importantFolders[packageName+'@Install'] = LibsFolder
                importantFolders[packageName] = packageDirectory + '/' + packageName + '/' + packageName
                includeFolders += "     '"+LibsFolder+"',\n"
                libFolders     += "     '"+LibsFolder+"',\n"
                for filenameX in installfileList:
                    filename = downloadedFolder+'/'+filenameX[0][0][1:-1]
                    cdlog(1, "Install: "+filename)
                    copyRecursive(filename, LibsFolder)

    return [includeFolders, libFolders]

def buildSconsFile(fileName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData, fileExtension, tools):
    (includeFolders, libFolders) = FindOrFetchLibraries(buildName, packageData, platform, tools)
    SconsFile = "import os\n\n"
    SconsFile += "env = Environment(ENV=os.environ)\n"
    #SconsFile += "env.MergeFlags('-g -fpermissive')\n"
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
    sconsCppPaths = 'env["CPPPATH"]=[\n'+includeFolders+']\n'
    sconsLibPaths = 'env["LIBPATH"]=[\n     r"'+codeDogFolder+'",\n'+libFolders+']\n'
    libStr=""
    firstTime = True
    for libFile in libFiles:
        if libFile.startswith('pkg-config'):
            libStr += "`"+libFile+"` "
            #sconsConfigs += 'env.ParseConfig("'+libFile+'")\n'
        else:
            if libFile =='pthread':
                #sconsConfigs += 'env.MergeFlags("-pthread")\n'
                sconsConfigs += ''
            else:
                libStr += "-l"+libFile
                if not firstTime: sconsLibs += ', '
                firstTime=False
                sconsLibs += '"'+libFile+'"'
    sconsLibs += ']\n'
        #print "libStr: " + libStr
    currentDirectory = os.getcwd()
    #TODO check if above is typo
    workingDirectory = currentDirectory + "\\" + buildName
    buildStr = getBuildSting(fileName,libStr,platform,buildName)
    runStr = "./" + fileName
    SconsFileOut += '    )\n'
    SconsFile += sconsCppPaths + sconsLibPaths + sconsLibs + sconsConfigs + SconsFileOut + '\n'
    sconsFilename = fileName+".scons"
    writeFile(buildName, sconsFilename, [[[sconsFilename],SconsFile]], "")

def LinuxBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData, tools):
    fileExtension = '.cpp'
    writeFile(buildName, fileName, fileSpecs, fileExtension)
    copyRecursive("Resources", buildName+"/assets")
    (includeFolders, libFolders) = FindOrFetchLibraries(buildName, packageData, platform, tools)
    packageDirectory = os.getcwd() + '/' + buildName
    for packageName in packageData:
        fetchPackages(packageName, packageDirectory)

    #building scons file
    SconsFile = "import os\n"
    SconsFile += "\nenv = Environment(ENV=os.environ)\nenv.MergeFlags('-g -fpermissive  -fdiagnostics-color=always')\n"
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
    sconsCppPaths = 'env["CPPPATH"]=[\n'+includeFolders+']\n'
    sconsLibPaths = 'env["LIBPATH"]=[\n     r"'+codeDogFolder+'",\n'+libFolders+']\n'
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
    currentDirectory = os.getcwd()
    #TODO check if above is typo
    workingDirectory = currentDirectory + "/" + buildName
    buildStr = getBuildSting(fileName,libStr,platform,buildName)
    runStr = "./" + fileName
    SconsFileOut += '    )\n'
    SconsFile += sconsCppPaths + sconsLibPaths + sconsLibs + sconsConfigs + SconsFileOut + '\n'
    sconsFilename = fileName+".scons"
    writeFile(buildName, sconsFilename, [[[sconsFilename],SconsFile]], "")
    return [workingDirectory, buildStr, runStr]

def WindowsBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData, tools):
    buildStr = ''
    codeDogFolder = os.path.dirname(os.path.realpath(__file__))
    libStr = "-I " + codeDogFolder + " "
    #minLangStr = '-std=gnu++' + minLangVersion + ' '
    fileExtension = '.cpp'
    #outputFileStr = '-o ' + fileName
    buildSconsFile(fileName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData, fileExtension, tools)

    writeFile(buildName, fileName, fileSpecs, fileExtension)
    copyRecursive("Resources", buildName + os.sep + "assets")

    for libFile in libFiles:
        libStr += "-l"+libFile+ " "
        #print "libStr: " + libStr

    currentDirectory = os.getcwd()
    #TODO check if above is typo
    workingDirectory = currentDirectory + os.sep + buildName
    buildStr = getBuildSting(fileName,"",platform,buildName)
    runStr = fileName + ".exe"
    return [workingDirectory, buildStr, runStr]

def SwingBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs):
    fileExtension = '.java'

    writeFile(buildName, fileName, fileSpecs, fileExtension)
    copyRecursive("Resources", buildName+"/assets")
    currentDirectory = os.getcwd()
    #TODO check if above is typo
    workingDirectory = currentDirectory + "/" + buildName
    buildStr = getBuildSting(fileName,"",platform,buildName)
    runStr = "java GLOBAL"
    return [workingDirectory, buildStr, runStr]

def SwiftBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs):
    # reference https://swift.org/getting-started/#using-the-package-manager
    buildStr = ''
    fileExtension = '.swift'
    currentDirectory = os.getcwd()
    workingDirectory = currentDirectory + "/" + buildName
    makeDirs(buildName)
    writeFile(workingDirectory, fileName, fileSpecs, fileExtension)
    buildStr = getBuildSting(fileName,"",platform,buildName)
    runStr = "./" + fileName
    return [workingDirectory, buildStr, runStr]

def iOSBuilder(debugMode, minLangVersion, projectName, libFiles, buildName, platform, fileSpecs):
    # reference https://swift.org/getting-started/#using-the-package-manager
    # building without Xcode: https://theswiftdev.com/how-to-build-macos-apps-using-only-the-swift-package-manager/
    fileExtension    = '.swift'
    fileName         =  'main'
    currentDirectory = os.getcwd()
    buildDirectory   = buildName
    projectDirectory = buildDirectory + '/' + projectName
    projectSubDir    = projectDirectory + '/' + projectName
    SDK_Path         = runCMD('xcrun --sdk iphonesimulator --show-sdk-path', currentDirectory)
    TARGET           = 'x86_64-apple-ios12.0-simulator'
    ############################################################
    makeDirs(buildDirectory)
    makeDirs(projectDirectory)
    makeDirs(projectSubDir)
    makeDirs(projectSubDir+'/Assets.xcassets')
    makeDirs(projectSubDir+'.xcodeproj')
    ############################################################
    buildCmd        = 'swiftc '+projectName+'/main.swift -sdk '+SDK_Path+' -target '+TARGET+' -emit-executable -o '+projectSubDir+' -suppress-warnings'
    runCmd          = "swift run  -Xswiftc -suppress-warnings"
    ############################################################
    writeFile(projectDirectory+'/'+projectName, fileName, fileSpecs, fileExtension)
    return [projectDirectory, buildCmd, runCmd]

def BuildAndPrintResults(workingDirectory, buildStr, runStr):
    cdlog(1, "Compiling From: {}".format(workingDirectory))
    print("\n     NOTE: Build Command is: ", buildStr)
    print("     NOTE: Working Dir is: ", workingDirectory)
    print("     NOTE: Run Command is: ", runStr, "\n")

    result = runCmdStreaming(buildStr, workingDirectory)
    if result==0:
        print("\nSUCCESS\n")
    else:
        print("\nBuild failed\n")
        exit(-1)

def build(debugMode, minLangVersion, fileName, labelName, launchIconName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData, tools):
    cdlog(0,"\n##############   B U I L D I N G    S Y S T E M...   ({})".format(buildName))
    progOrLib = progOrLib.lower()
    if platform == 'Linux':
        [workingDirectory, buildStr, runStr] = LinuxBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData, tools)
    elif platform == 'Java' or  platform == 'Swing':
        [workingDirectory, buildStr, runStr] = SwingBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs)
    elif platform == 'Android':
        buildAndroid.AndroidBuilder(debugMode, minLangVersion, fileName, labelName, launchIconName, libFiles, buildName, platform, fileSpecs)
    elif platform == 'Swift':
        [workingDirectory, buildStr, runStr] = SwiftBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs)
    elif platform == 'Windows':
        [workingDirectory, buildStr, runStr] = WindowsBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData, tools)
    elif platform == 'MacOS':
        [workingDirectory, buildStr, runStr] = buildMac.macBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs)
    elif platform == 'IOS':
        [workingDirectory, buildStr, runStr] = iOSBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs)
    else:
        print("buildDog.py error: build string not generated for "+ buildName)
        exit(2)
    if platform!='Android': BuildAndPrintResults(workingDirectory, buildStr, runStr)
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

        codeDogPath = os.path.dirname(os.path.realpath(__file__))
        buildStr = f"python3 {codeDogPath}/Scons/scons.py -Q -f "+fileName+".scons"
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
        codeDogPath = os.path.dirname(os.path.realpath(__file__))
        buildStr = f"python3 {codeDogPath}/Scons/scons.py -Q -f "+fileName+".scons"
    elif platform == 'MacOS':
        buildStr = "// swift build -Xswiftc -suppress-warnings \n"
        buildStr += "// swift run  -Xswiftc -suppress-warnings \n"
    else:
        buildStr=''
    return buildStr

def buildWithScons(name, cmdLineArgs):
    #print("cmdLineArgs:", ' '.join(cmdLineArgs))
    sconsFile = lastFile = ''
    fCount = 0
    basepath = os.getcwd()
    for fname in os.listdir(basepath):
        path = os.path.join(basepath, fname)
        if os.path.isdir(path): continue
        if(fname.endswith(".scons")):
            fCount += 1
            lastFile = fname
            if fname==name+".scons":
                sconsFile = fname
                break
    if fCount==1 and name=='': sconsFile=lastFile
    if sconsFile=='':
        print("BUILDING: Could not find '"+name+".scons'\n")
        exit(1)
    else:
        if name=='' and fCount!=1:
            print("BUILDING: Could not figure out what to build.")

        codeDogPath = os.path.dirname(os.path.realpath(__file__))
        otherSconsArgs = ' '.join(cmdLineArgs)
        sconsCMD = "python3 "+codeDogPath+"/Scons/scons.py -Q -f "+sconsFile + ' '+ otherSconsArgs
        result = runCmdStreaming(sconsCMD, basepath)
        if result==0:
            print("\nSUCCESS\n")
        else:
            print("\nBuild failed\n")
            exit(-1)
