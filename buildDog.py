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
import urllib
from urllib.request import urlopen


#TODO: error handling

def runCMD(myCMD, myDir):
    print("        COMMAND: ", myCMD, "\n")
    pipe = subprocess.Popen(myCMD, cwd=myDir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    if out:
        #print("        Result: ",out)
        pass
    if err:
        print("\n", err)
        if (err.find(b"ERROR")) >= 0:
            exit(1)
    decodedOut = bytes.decode(out)
    if decodedOut[-1]=='\n': decodedOut = decodedOut[:-1]
    return decodedOut

def makeDirs(dirToGen):
    #print("dirToGen:", dirToGen)
    try:
        os.makedirs(dirToGen, exist_ok=True)
    except FileExistsError:
        # Another thread was already created the directory when
        # several simultaneous requests has come
        if os.path.isdir(os.path.dirname(abs_path)):
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
    import urllib.request
    from git import Repo
    packagePath = packageDirectory + '/' + packageName + '/' + packageName
    checkRepo = os.path.isdir(packagePath)
    if not checkRepo:
        cdlog(1, "Cloning git repository: " + packageName)
        Repo.clone_from(cloneUrl, packagePath)
        makeDirs(packageDirectory + '/' + packageName + "/INSTALL")

def downloadFile(downloadUrl, packageName, packageDirectory):
    import pycurl
    downloadFileExtension = downloadUrl.rsplit('.', 1)[-1]
    packagePath = packageDirectory + '/' + packageName + '/' + packageName + '.' + downloadFileExtension
    makeDirs(packageDirectory + '/' + packageName + "/INSTALL")
    makeDirs(os.path.dirname(packagePath))
    checkRepo = os.path.isfile(packagePath)
    if not checkRepo:
        try:
            cdlog(1, "Downloading file: " + packageName)
            with open(packagePath, 'wb') as f:
                c = pycurl.Curl()
                c.setopt(c.URL, downloadUrl)
                c.setopt(c.WRITEDATA, f)
                c.perform()
                # print('Status: %d' % c.getinfo(c.RESPONSE_CODE))
                c.close()
        except:
            cdErr("URL not found : " + downloadUrl)

def downloadExtractZip(downloadUrl, packageName, packageDirectory):
    import pycurl
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

    zipFileDirectory = packageDirectory + '/' + packageName
    packagePath = zipFileDirectory + '/' + packageName + zipExtension
    checkDirectory = os.path.isdir(zipFileDirectory)
    zipFileName = os.path.basename(downloadUrl)
    if not checkDirectory:
        try:
            makeDirs(zipFileDirectory + "/INSTALL")
            cdlog(1, "Downloading zip file: " + zipFileName)
            with open(packagePath, 'wb') as f:
                c = pycurl.Curl()
                c.setopt(c.URL, downloadUrl)
                c.setopt(c.WRITEDATA, f)
                c.perform()
                # print('Status: %d' % c.getinfo(c.RESPONSE_CODE))
                c.close()
        except:
            cdErr("URL not found : " + downloadUrl)
        else:
            try:
                cdlog(1, "Extracting zip file: " + zipFileName)
                shutil.unpack_archive(packagePath, zipFileDirectory)
            except:
                cdErr("Could not extract zip archive file: " + zipFileName)

def FindOrFetchLibraries(buildName, packageData, platform):
    #print("#############:buildName:", buildName, platform)
    packageDirectory = os.getcwd() + '/' + buildName
    [includeFolders, libFolders] = ["", ""]
    for package in packageData:
        packageMap = progSpec.extractMapFromTagMap(package)
        packageName = fetchType = fetchURL = fetchCommit = ""
        buildCmdsMap = {}
        if 'packageName' in packageMap:
            packageName = packageMap['packageName'][1:-1]
        if 'fetchMethod' in packageMap:
            fetchMethod = packageMap['fetchMethod'][1:-1]
            fetchSpec   = packageMap['fetchMethod'][1:-1].split(':', 1)
            fetchType   = fetchSpec[0]
            splitSpec   = fetchSpec[1].split('@', 1)
            fetchURL    = splitSpec[0]
            if len(splitSpec)>=2: fetchCommit = splitSpec[1]
        if 'buildCmds' in packageMap:
            buildCmds = packageMap['buildCmds']
            buildCmdsMap = progSpec.extractMapFromTagMap(buildCmds)

        if packageName!="" and fetchMethod!="":
            if fetchType == "git":
                gitClone(fetchURL, packageName, packageDirectory)
            elif fetchType == "file":
                downloadFile(fetchURL, packageName, packageDirectory)
            elif fetchType == "zip":
                downloadExtractZip(fetchURL, packageName, packageDirectory)
            else:
                pass

        if buildCmdsMap!={} and platform in buildCmdsMap:
            #print("###########:",platform, ' = ', buildCmdsMap[platform])
            buildCommand = buildCmdsMap[platform]
            buildCmdMap = progSpec.extractMapFromTagMap(buildCommand)
            downloadedFolder = packageDirectory+"/"+packageName+"/"+packageName

            if 'buildCmd' in buildCmdMap:
                actualBuildCmd = buildCmdMap['buildCmd'][1:-1]
                #print("BUILDCMMAND:", actualBuildCmd)#, "  INSTALL:", buildCmdsMap[platform][1])
                runCMD(actualBuildCmd, downloadedFolder)

            if 'installFiles' in buildCmdMap:
                installfileList = buildCmdMap['installFiles'][1]
                # ~ installFiles = progSpec.extractListFromTagList(installfileList)
                # ~ print("    DATA:", str(installFiles)[:100])
                LibsFolder = packageDirectory + '/' + packageName + "/INSTALL"
                includeFolders += "     '"+LibsFolder+"',\n"
                libFolders     += "     '"+LibsFolder+"',\n"
                for filenameX in installfileList:
                    filename = downloadedFolder+'/'+filenameX[0][0][1:-1]
                    cdlog(1, "Install: "+filename)
                    copyRecursive(filename, LibsFolder)

    return [includeFolders, libFolders]

def LinuxBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData):
    fileExtension = '.cpp'

    writeFile(buildName, fileName, fileSpecs, fileExtension)
    copyRecursive("Resources", buildName+"/assets")

    (includeFolders, libFolders) = FindOrFetchLibraries(buildName, packageData, platform)

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
                try:
                    response = urlopen(fetchMethodUrl)
                except (urllib.error.URLError, urllib.error.HTTPError):
                    cdErr("URL not found : " + fetchMethodUrl)
                else:
                    cdlog(1, "Cloning git repository: " + packageName)
                    gitClone("clone", fetchMethodUrl, PackagePath, "--quiet")

        elif fetchMethod.startswith("file:"):
            fileExtensionUrl = fetchMethodUrl.rsplit('.', 1)[-1]
            PackagePath = os.getcwd() + '/' + buildName + '/' + packageName + '.' + fileExtensionUrl
            checkExistFile = os.path.isfile(PackagePath)
            DownloadFileName = os.path.basename(PackagePath)
            if not checkExistFile:
                try:
                    fileStream = urlopen(fetchMethodUrl)
                except (urllib.error.URLError, urllib.error.HTTPError):
                    cdErr("URL not found : " + fetchMethodUrl)
                else:
                    cdlog(1, "Downloading file: " + DownloadFileName)
                    with open(PackagePath, 'wb') as file:
                        file.write(fileStream.read())
                    fileStream.close()

        elif fetchMethod.startswith("zip:"):
            if fetchMethodUrl.endswith(".zip"):
                fileExtensionUrl = ".zip"
            elif fetchMethodUrl.endswith(".tar.gz"):
                fileExtensionUrl = ".tar.gz"
            elif fetchMethodUrl.endswith(".tar.bz2"):
                fileExtensionUrl = ".tar.bz2"
            elif fetchMethodUrl.endswith(".tar.xz"):
                fileExtensionUrl = ".tar.xz"
            elif fetchMethodUrl.endswith(".tar"):
                fileExtensionUrl = ".tar"
            else:
                pass

            PackagePath = os.getcwd() + '/' + buildName + '/' + packageName + fileExtensionUrl
            checkDirectory = os.path.isdir(os.getcwd() + '/' + buildName + '/' + packageName)
            checkfile = os.path.isfile(PackagePath)
            zipFileName = os.path.basename(PackagePath)
            if not checkDirectory and not checkfile:
                try:
                    zipStream = urlopen(fetchMethodUrl)
                except (urllib.error.URLError, urllib.error.HTTPError):
                    cdErr("URL not found : " + fetchMethodUrl)
                else:
                    cdlog(1, "Downloading zip file: " + zipFileName)
                    with open(PackagePath, 'wb') as file:
                        file.write(zipStream.read())
                    zipStream.close()

            #Extract zip file
            checkfile = os.path.isfile(PackagePath)
            if not checkDirectory and checkfile:
                if zipFileName.endswith(".zip"):
                    cdlog(1, "Extracting zip file: " + zipFileName)
                    extractCMD = 'unzip ' + PackagePath + ' -d ' + packageDirectory + '/' + packageName
                    extractZip(extractCMD, zipFileName)

                elif zipFileName.endswith(".tar.gz"):
                    cdlog(1, "Extracting zip file: " + zipFileName)
                    extractCMD = 'tar' + ' xzf ' + PackagePath + ' -C ' + packageDirectory + ' --one-top-level'
                    extractZip(extractCMD, zipFileName)

                elif zipFileName.endswith(".tar.bz2"):
                    cdlog(1, "Extracting zip file: " + zipFileName)
                    extractCMD = 'tar' + ' xjf ' + PackagePath + ' -C ' + packageDirectory + ' --one-top-level'
                    extractZip(extractCMD, zipFileName)

                elif zipFileName.endswith(".tar.xz"):
                    cdlog(1, "Extracting zip file: " + zipFileName)
                    extractCMD = 'tar' + ' xJf ' + PackagePath + ' -C ' + packageDirectory + ' --one-top-level'
                    extractZip(extractCMD, zipFileName)

                elif zipFileName.endswith(".tar"):
                    cdlog(1, "Extracting zip file: " + zipFileName)
                    extractCMD = 'tar' + ' xf ' + PackagePath + ' -C ' + packageDirectory + ' --one-top-level'
                    extractZip(extractCMD, zipFileName)
                else:
                    pass
        else:
            pass

    # implement pip as a subprocess:
    packageDirectory = os.getcwd() + '/' + buildName
    for packageNo in range(len(packageData)):
        packageName = packageData[packageNo][1][0][1][0].replace("'", '')
        fetchMethod = packageData[packageNo][1][1][1][0].replace("'", '')
        # fetchMethod = packageData[packageNo][1][1][1][0].split(':',1)[0].replace("'", '')
        fetchMethodUrl = packageData[packageNo][1][1][1][0].split(':',1)[1].replace("'", '')
        if fetchMethod.startswith("git:"):
            PackagePath = os.getcwd() + '/' + buildName + '/' + packageName + '/' + packageName
            makeDir(os.getcwd() + '/' + buildName + '/' + packageName + "/LIBS")
            checkRepo = os.path.isdir(PackagePath)
            if not checkRepo:
                try:
                    response = urlopen(fetchMethodUrl)
                except (urllib.error.URLError, urllib.error.HTTPError):
                    cdErr("URL not found : " + fetchMethodUrl)
                else:
                    cdlog(1, "Cloning git repository: " + packageName)
                    gitClone("clone", fetchMethodUrl, PackagePath, "--quiet")

        elif fetchMethod.startswith("file:"):
            fileExtensionUrl = fetchMethodUrl.rsplit('.', 1)[-1]
            PackagePath = packageDirectory + '/' + packageName + '/' + packageName + '/' + packageName + '.' + fileExtensionUrl
            makeDir(packageDirectory + '/' + packageName + "/LIBS")
            makeDir(os.path.dirname(PackagePath))
            checkExistFile = os.path.isfile(PackagePath)
            DownloadFileName = os.path.basename(PackagePath)
            if not checkExistFile:
                try:
                    fileStream = urlopen(fetchMethodUrl)
                except (urllib.error.URLError, urllib.error.HTTPError):
                    cdErr("URL not found : " + fetchMethodUrl)
                else:
                    cdlog(1, "Downloading file: " + DownloadFileName)
                    with open(PackagePath, 'wb') as file:
                        file.write(fileStream.read())
                    fileStream.close()

        elif fetchMethod.startswith("zip:"):
            if fetchMethodUrl.endswith(".zip"):
                fileExtensionUrl = ".zip"
            elif fetchMethodUrl.endswith(".tar.gz"):
                fileExtensionUrl = ".tar.gz"
            elif fetchMethodUrl.endswith(".tar.bz2"):
                fileExtensionUrl = ".tar.bz2"
            elif fetchMethodUrl.endswith(".tar.xz"):
                fileExtensionUrl = ".tar.xz"
            elif fetchMethodUrl.endswith(".tar"):
                fileExtensionUrl = ".tar"
            else:
                pass

            zipFileDirectory = packageDirectory + '/' + packageName
            makeDir(zipFileDirectory + "/LIBS")
            PackagePath = packageDirectory + '/' + packageName + '/' + packageName + fileExtensionUrl
            checkDirectory = os.path.isdir(zipFileDirectory + '/' + packageName)
            checkfile = os.path.isfile(PackagePath)
            zipFileName = os.path.basename(PackagePath)
            if not checkDirectory and not checkfile:
                try:
                    zipStream = urlopen(fetchMethodUrl)
                except (urllib.error.URLError, urllib.error.HTTPError):
                    cdErr("URL not found : " + fetchMethodUrl)
                else:
                    cdlog(1, "Downloading zip file: " + zipFileName)
                    with open(PackagePath, 'wb') as file:
                        file.write(zipStream.read())
                    zipStream.close()

            #Extract zip file
            checkfile = os.path.isfile(PackagePath)
            if not checkDirectory and checkfile:
                if zipFileName.endswith(".zip"):
                    cdlog(1, "Extracting zip file: " + zipFileName)
                    extractCMD = 'unzip ' + PackagePath + ' -d ' + zipFileDirectory + '/' + packageName
                    extractZip(extractCMD, zipFileName)

                elif zipFileName.endswith(".tar.gz"):
                    cdlog(1, "Extracting zip file: " + zipFileName)
                    extractCMD = 'tar' + ' xzf ' + PackagePath + ' -C ' + zipFileDirectory + ' --one-top-level'
                    extractZip(extractCMD, zipFileName)

                elif zipFileName.endswith(".tar.bz2"):
                    cdlog(1, "Extracting zip file: " + zipFileName)
                    extractCMD = 'tar' + ' xjf ' + PackagePath + ' -C ' + zipFileDirectory + ' --one-top-level'
                    extractZip(extractCMD, zipFileName)

                elif zipFileName.endswith(".tar.xz"):
                    cdlog(1, "Extracting zip file: " + zipFileName)
                    extractCMD = 'tar' + ' xJf ' + PackagePath + ' -C ' + zipFileDirectory + ' --one-top-level'
                    extractZip(extractCMD, zipFileName)

                elif zipFileName.endswith(".tar"):
                    cdlog(1, "Extracting zip file: " + zipFileName)
                    extractCMD = 'tar' + ' xf ' + PackagePath + ' -C ' + zipFileDirectory + ' --one-top-level'
                    extractZip(extractCMD, zipFileName)
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
    sconsCppPaths = 'env["CPPPATH"]=[\n'+includeFolders+']\n'
    sconsLibPaths = 'env["LIBPATH"]=[\n     "'+codeDogFolder+'",\n'+libFolders+']\n'
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
    currentDirectory = os.getcwd()
    #TODO check if above is typo
    workingDirectory = currentDirectory + "/" + buildName
    buildStr = getBuildSting(fileName,libStr,platform,buildName)
    runStr = "./" + fileName
    SconsFileOut += '    )\n'
    SconsFile += sconsCppPaths + sconsLibPaths + sconsLibs + sconsConfigs + SconsFileOut + '\n'
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
    copyRecursive("Resources", buildName + os.sep + "assets")

    for libFile in libFiles:
        libStr += "-l"+libFile+ " "
        #print "libStr: " + libStr

    currentDirectory = os.getcwd()
    #TODO check if above is typo
    workingDirectory = currentDirectory + os.sep + buildName
    buildStr = getBuildSting(fileName,"",platform,buildName)
    runStr = "python " + "..\CodeDog\\" + fileName
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
        if "error:" in decodedErr or "SyntaxError:" in decodedErr:
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
