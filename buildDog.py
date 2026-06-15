# buildDog.py

from __future__ import unicode_literals
import progSpec
import os
import sys
import subprocess
import buildAndroid
import buildMac
import errno
import filecmp
import hashlib
import json
import shutil
import queue
import threading
import time
from progSpec import cdlog, cdErr
from pathlib import Path

import environmentMngr as emgr

importantFolders = {}

def buildStatus(message):
    print("STATUS [{}] {}".format(time.strftime("%H:%M:%S"), message), flush=True)

def safePathSegment(value):
    value = str(value)
    return ''.join(ch if ch.isalnum() or ch in ('-', '_', '.') else '_' for ch in value)

def targetKeyFromBuildTags(buildTags, platform=None):
    if buildTags == None:
        return safePathSegment(platform if platform else "unknown")
    platformVal = platform if platform else buildTags.get('Platform', 'unknown')
    parts = [
        platformVal,
        buildTags.get('CPU', 'any'),
        buildTags.get('Lang', 'unknown'),
        buildTags.get('LangVersion', 'default'),
        buildTags.get('Configuration', buildTags.get('optimize', 'default')),
        buildTags.get('Linkage', buildTags.get('linkage', 'default')),
    ]
    return safePathSegment('-'.join(str(part) for part in parts if part != None and str(part) != ""))

def tagValueToString(value):
    while (
        not isinstance(value, (str, bytes, dict))
        and hasattr(value, "__len__")
        and hasattr(value, "__getitem__")
        and len(value) == 1
    ):
        value = value[0]
    text = str(value)
    if len(text) >= 2 and ((text[0] == "'" and text[-1] == "'") or (text[0] == '"' and text[-1] == '"')):
        return text[1:-1]
    return text

def installSpecPath(filenameSpec):
    return tagValueToString(filenameSpec).replace("\\", "/")

def sconsPathEntries(paths):
    return ''.join('     r"{}",\n'.format(path.replace("\\", "/")) for path in paths)

def replacePackageAliases(command, aliases):
    for folderKey in sorted(aliases, key=len, reverse=True):
        command = command.replace('$'+folderKey, aliases[folderKey])
    return command

def appendExistingPath(paths, path):
    normPath = os.path.normpath(path)
    if os.path.isdir(normPath):
        normPath = normPath.replace("\\", "/")
        if normPath not in paths:
            paths.append(normPath)

def parseFetchMethod(fetchMethod):
    fetchMethod = tagValueToString(fetchMethod)
    if ':' in fetchMethod:
        fetchType, fetchSpec = fetchMethod.split(':', 1)
    else:
        fetchType, fetchSpec = fetchMethod, ""
    qualifiers = {}
    if '@' in fetchSpec:
        fetchSpec, qualifierText = fetchSpec.split('@', 1)
        for qualifier in qualifierText.split(','):
            if '=' in qualifier:
                key, val = qualifier.split('=', 1)
                qualifiers[key.strip()] = val.strip()
            elif qualifier.strip():
                qualifiers['ref'] = qualifier.strip()
    return {
        'type': fetchType,
        'url': fetchSpec,
        'ref': qualifiers.get('ref') or qualifiers.get('commit') or qualifiers.get('tag') or qualifiers.get('branch'),
        'qualifiers': qualifiers,
    }

def packageWorkspace(packageDirectory, targetKey, packageName):
    return os.path.join(packageDirectory, ".codedog", "deps", targetKey, packageName)

def packageSourceParent(packageRoot):
    return os.path.join(packageRoot, "src")

def packageBuildDir(packageRoot):
    return os.path.join(packageRoot, "build")

def packageStageDir(packageRoot):
    return os.path.join(packageRoot, "stage")

def packageManifestPath(packageRoot):
    return os.path.join(packageRoot, "manifest.json")

#TODO: error handling
def string_escape(s, encoding='utf-8'):
    return (s.encode('latin1')         # To bytes, required by 'unicode-escape'
             .decode('unicode-escape') # Perform the actual octal-escaping decode
             .encode('latin1')         # 1:1 mapping back to bytes
             .decode(encoding))        # Decode original encoding

def windowsToolDirs():
    if os.name != 'nt':
        return []
    candidates = [
        r"C:\Program Files\CMake\bin",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\MSBuild\Current\Bin",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\MSBuild\Current\Bin\amd64",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\amd64",
        r"C:\Program Files\Go\bin",
    ]
    return [path for path in candidates if os.path.isdir(path)]

def commandEnvironment():
    env = os.environ.copy()
    toolDirs = windowsToolDirs()
    if toolDirs:
        env["PATH"] = os.pathsep.join(toolDirs + [env.get("PATH", "")])
    return env

def executableExistsInDirs(toolName, dirs):
    extensions = [""] if os.path.splitext(toolName)[1] else ["", ".exe", ".bat", ".cmd"]
    for directory in dirs:
        for extension in extensions:
            if os.path.isfile(os.path.join(directory, toolName + extension)):
                return True
    return False

def runCMD(myCMD, myDir):
    print("\nCOMMAND: ", myCMD, "\n")
    pipe = subprocess.Popen(myCMD, cwd=myDir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=commandEnvironment())
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
    outputQueue = queue.Queue()
    heartbeatSeconds = 30
    process = subprocess.Popen(myCMD, cwd=myDir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines = True, bufsize=1, env=commandEnvironment())
    startTime = time.monotonic()
    lastOutputTime = startTime

    def queueOutput(streamName, stream):
        try:
            for line in iter(stream.readline, ''):
                if line:
                    outputQueue.put((streamName, line))
        finally:
            stream.close()

    stdoutThread = threading.Thread(target=queueOutput, args=('stdout', process.stdout))
    stderrThread = threading.Thread(target=queueOutput, args=('stderr', process.stderr))
    stdoutThread.daemon = True
    stderrThread.daemon = True
    stdoutThread.start()
    stderrThread.start()
    buildStatus("Started command in {}".format(myDir))

    def printQueuedOutput():
        nonlocal errText, lastOutputTime
        printed = False
        while True:
            try:
                streamName, output = outputQueue.get_nowait()
            except queue.Empty:
                return printed
            lastOutputTime = time.monotonic()
            printed = True
            if streamName == 'stderr':
                errText += output
            print(output.rstrip())

    nextHeartbeat = startTime + heartbeatSeconds
    while process.poll() is None:
        printed = printQueuedOutput()
        if printed:
            nextHeartbeat = time.monotonic() + heartbeatSeconds
        else:
            now = time.monotonic()
            if now >= nextHeartbeat:
                elapsed = now - startTime
                idleTime = now - lastOutputTime
                buildStatus("Still running: {:.0f}s elapsed, no command output for {:.0f}s".format(elapsed, idleTime))
                nextHeartbeat = now + heartbeatSeconds
            time.sleep(0.25)

    stdoutThread.join(timeout=2)
    stderrThread.join(timeout=2)
    printQueuedOutput()
    returnCode = process.returncode
    if returnCode!=0 or (errText and ((errText.find("ERROR")) >= 0 or errText.find("error")>=0)):
        print("ERRORS:---------------\n")
        if errText:
            print(errText)
        else:
            print("Command exited with return code {}".format(returnCode))
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

def writeTextFile(path, fileName, fileText):
    #print path
    makeDirs(path)
    pathName = path + os.sep + fileName
    if os.path.isfile(pathName):
        try:
            with open(pathName, 'r') as fo:
                if fo.read() == fileText:
                    cdlog(1, "UNCHANGED FILE: "+pathName)
                    return
        except OSError:
            pass
    cdlog(1, "WRITING FILE: "+pathName)
    with open(pathName, 'w') as fo:
        fo.write(fileText)

def writeFile(path, fileName, fileSpecs, fileExtension):
    writeTextFile(path, fileName + fileExtension, fileSpecs[0][1])

def generatedFileName(fileSpec, defaultExtension):
    filename = fileSpec[0]
    if isinstance(filename, list):
        filename = filename[0]
    if os.path.splitext(filename)[1] == "":
        filename += defaultExtension
    return filename

def writeGeneratedFiles(path, fileSpecs, defaultExtension):
    for fileSpec in fileSpecs:
        writeTextFile(path, generatedFileName(fileSpec, defaultExtension), fileSpec[1])

def sconsSourceList(fileSpecs, defaultExtension):
    sourceFiles = []
    sourceExtensions = {'.c', '.cc', '.cpp', '.cxx'}
    for fileSpec in fileSpecs:
        filename = generatedFileName(fileSpec, defaultExtension)
        if os.path.splitext(filename)[1].lower() in sourceExtensions:
            sourceFiles.append(filename)
    if not sourceFiles:
        sourceFiles.append(generatedFileName(fileSpecs[0], defaultExtension))
    return '[' + ', '.join('r"{}"'.format(sourceFile.replace('"', '\\"')) for sourceFile in sourceFiles) + ']'

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

def copyWindowsRuntimeDlls(buildName):
    buildPath = Path(buildName)
    if not buildPath.is_dir():
        return
    dllPaths = list(buildPath.glob("*/INSTALL/**/*.dll"))
    dllPaths.extend(buildPath.glob(".codedog/deps/*/*/stage/**/*.dll"))
    for dllPath in dllPaths:
        targetPath = buildPath / dllPath.name
        if dllPath.resolve() == targetPath.resolve():
            continue
        if targetPath.exists():
            try:
                if filecmp.cmp(str(dllPath), str(targetPath), shallow=False):
                    continue
            except OSError:
                pass
        try:
            shutil.copy2(str(dllPath), str(targetPath))
        except PermissionError:
            if targetPath.exists():
                buildStatus("WARNING: Runtime DLL '{}' is locked; keeping existing copy".format(targetPath.name))
                continue
            raise

def gitClone(cloneUrl, packageName, packageDirectory, sourceRef=None):
    emgr.CheckPipModules({'GitPython':'3.1'})
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
    if sourceRef:
        repo = Repo(packagePath)
        currentRef = repo.head.commit.hexsha
        if not currentRef.startswith(sourceRef):
            cdlog(1, "Checking out {} at {}".format(packageName, sourceRef))
            repo.git.checkout(sourceRef)

def gitCloneToSource(cloneUrl, packageName, sourceParent, sourceRef=None):
    emgr.CheckPipModules({'GitPython':'3.1'})
    import urllib.request
    from git import Repo
    makeDirs(sourceParent)
    packagePath = os.path.join(sourceParent, packageName)
    checkRepo = os.path.isdir(os.path.join(packagePath, ".git"))
    if not checkRepo:
        try:
            urllib.request.urlopen(cloneUrl)
        except (urllib.error.URLError, urllib.error.HTTPError):
            cdErr("URL not found: " + cloneUrl)
        cdlog(1, "Cloning git repository: " + packageName)
        Repo.clone_from(cloneUrl, packagePath)
    if sourceRef:
        repo = Repo(packagePath)
        currentRef = repo.head.commit.hexsha
        if not currentRef.startswith(sourceRef):
            cdlog(1, "Checking out {} at {}".format(packageName, sourceRef))
            repo.git.checkout(sourceRef)

def downloadPackageFile(downloadUrl, packageName, packageDirectory):
    downloadFileExtension = downloadUrl.rsplit('.', 1)[-1]
    packagePath = packageDirectory + '/' + packageName + '/' + packageName + '.' + downloadFileExtension
    makeDirs(packageDirectory + '/' + packageName + "/INSTALL")
    makeDirs(os.path.dirname(packagePath))
    checkRepo = os.path.isfile(packagePath)
    if not checkRepo:
        emgr.downloadFile(packagePath, downloadUrl)

def downloadPackageFileToSource(downloadUrl, packageName, sourceParent):
    downloadFileExtension = downloadUrl.rsplit('.', 1)[-1]
    packagePath = os.path.join(sourceParent, packageName + '.' + downloadFileExtension)
    makeDirs(os.path.dirname(packagePath))
    if not os.path.isfile(packagePath):
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
    zipFileName = os.path.basename(downloadUrl)
    if not os.path.isfile(packagePath):
        makeDirs(zipFileDir + "/INSTALL")
        emgr.downloadFile(packagePath, downloadUrl)
    if os.path.isfile(packagePath):
        extractedContent = [
            child for child in Path(zipFileDir).iterdir()
            if child.name not in ["INSTALL", os.path.basename(packagePath)]
        ]
        if not extractedContent:
            try:
                cdlog(1, "Extracting zip file: " + zipFileName)
                shutil.unpack_archive(packagePath, zipFileDir)
            except:
                try:
                    os.remove(packagePath)
                    emgr.downloadFile(packagePath, downloadUrl)
                    cdlog(1, "Extracting zip file: " + zipFileName)
                    shutil.unpack_archive(packagePath, zipFileDir)
                except:
                    cdErr("Could not extract zip archive file: " + zipFileName)

def downloadExtractArchiveToSource(downloadUrl, packageName, sourceParent):
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

    makeDirs(sourceParent)
    packagePath = os.path.join(sourceParent, packageName + zipExtension)
    zipFileName = os.path.basename(downloadUrl)
    if not os.path.isfile(packagePath):
        emgr.downloadFile(packagePath, downloadUrl)
    if os.path.isfile(packagePath):
        extractedContent = [
            child for child in Path(sourceParent).iterdir()
            if child.name != os.path.basename(packagePath)
        ]
        if not extractedContent:
            try:
                cdlog(1, "Extracting archive file: " + zipFileName)
                shutil.unpack_archive(packagePath, sourceParent)
            except:
                try:
                    os.remove(packagePath)
                    emgr.downloadFile(packagePath, downloadUrl)
                    cdlog(1, "Extracting archive file: " + zipFileName)
                    shutil.unpack_archive(packagePath, sourceParent)
                except:
                    cdErr("Could not extract archive file: " + zipFileName)

def getPackageName(packageMap):
    if 'packageName' in packageMap:
        return(tagValueToString(packageMap['packageName']))
    return("")

def getInnerPackageName(packageMap):
    if 'innerPkgName' in packageMap:
        return(tagValueToString(packageMap['innerPkgName']))
    return(getPackageName(packageMap))

def getFetchType(packageMap):
    if 'fetchMethod' in packageMap:
        return(parseFetchMethod(packageMap['fetchMethod'])['type'])
    return("")

def getFetchURL(packageMap):
    if 'fetchMethod' in packageMap:
        return(parseFetchMethod(packageMap['fetchMethod'])['url'])
    return("")

def getFetchRef(packageMap):
    if 'fetchMethod' in packageMap:
        return(parseFetchMethod(packageMap['fetchMethod'])['ref'])
    return(None)

def isHeaderPath(path):
    return os.path.splitext(path)[1].lower() in [".h", ".hh", ".hpp", ".hxx"]

def isLibraryPath(path):
    return os.path.splitext(path)[1].lower() in [".a", ".lib", ".so", ".dylib"]

def isRuntimePath(path):
    return os.path.splitext(path)[1].lower() in [".dll", ".exe"]

def installDestination(sourcePath, installFile, stageDir):
    normInstall = installFile.replace("\\", "/").strip("/")
    if installFile == ".":
        return stageDir
    parts = [part for part in normInstall.split("/") if part != ""]
    firstPart = parts[0].lower() if parts else ""
    baseName = os.path.basename(normInstall)
    if firstPart in ["include", "includes"]:
        relPath = os.path.join(*parts[1:]) if len(parts) > 1 else ""
        return os.path.join(stageDir, "include", relPath)
    if firstPart in ["lib", "lib64"] or firstPart == "x64" or isLibraryPath(baseName):
        if os.path.isdir(sourcePath):
            return os.path.join(stageDir, "lib")
        return os.path.join(stageDir, "lib", baseName)
    if firstPart in ["bin", "bin64"] or isRuntimePath(baseName):
        if os.path.isdir(sourcePath):
            return os.path.join(stageDir, "bin")
        return os.path.join(stageDir, "bin", baseName)
    if isHeaderPath(baseName):
        return os.path.join(stageDir, "include", baseName)
    if os.path.isdir(sourcePath):
        return os.path.join(stageDir, baseName)
    return os.path.join(stageDir, baseName)

def installPayloadDestinationExists(sourcePath, installFile, stageDir):
    destination = installDestination(sourcePath, installFile, stageDir)
    if os.path.isfile(sourcePath):
        return os.path.isfile(destination)
    if os.path.isdir(sourcePath):
        if not os.path.isdir(destination):
            return False
        try:
            return len(os.listdir(destination)) > 0
        except OSError:
            return False
    return False

def copyInstallPayload(sourcePath, installFile, stageDir):
    if not os.path.exists(sourcePath):
        cdErr("Package install payload not found: " + sourcePath)
    destination = installDestination(sourcePath, installFile, stageDir)
    if os.path.isfile(sourcePath):
        makeDirs(os.path.dirname(destination))
        shutil.copy2(sourcePath, destination)
    else:
        copyRecursive(sourcePath, destination)

def packageManifest(packageName, targetKey, packageRoot, stageDir, sourceRef):
    includeDirs = []
    libDirs = []
    runtimeFiles = []
    appendExistingPath(includeDirs, os.path.join(stageDir, "include"))
    appendExistingPath(includeDirs, stageDir)
    appendExistingPath(libDirs, os.path.join(stageDir, "lib"))
    appendExistingPath(libDirs, stageDir)
    if os.path.isdir(stageDir):
        for runtimePath in Path(stageDir).rglob("*"):
            if runtimePath.is_file() and isRuntimePath(str(runtimePath)):
                runtimeFiles.append(str(runtimePath).replace("\\", "/"))
    return {
        "package": packageName,
        "targetKey": targetKey,
        "sourceRef": sourceRef,
        "stage": stageDir.replace("\\", "/"),
        "includeDirs": includeDirs,
        "libDirs": libDirs,
        "libs": [],
        "defines": [],
        "cflags": [],
        "linkFlags": [],
        "runtimeFiles": runtimeFiles,
    }

def writePackageManifest(packageName, targetKey, packageRoot, stageDir, sourceRef):
    manifest = packageManifest(packageName, targetKey, packageRoot, stageDir, sourceRef)
    manifestPath = packageManifestPath(packageRoot)
    makeDirs(os.path.dirname(manifestPath))
    with open(manifestPath, 'w') as manifestFile:
        json.dump(manifest, manifestFile, indent=2, sort_keys=True)
    return manifest

def packageInstallFingerprint(platform, buildCommand, installfileList):
    installFiles = []
    for filenameX in installfileList:
        installFiles.append(installSpecPath(filenameX[0][0]))
    fingerprintText = platform + "\n" + buildCommand + "\n" + "\n".join(installFiles)
    return hashlib.sha256(fingerprintText.encode('utf-8')).hexdigest()

def packageBuildMarkerPath(libsFolder, platform):
    safePlatform = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in platform)
    return os.path.join(libsFolder, ".codedog_build_{}.sha256".format(safePlatform))

def packageInstallIsCurrent(libsFolder, platform, buildCommand, installfileList):
    markerPath = packageBuildMarkerPath(libsFolder, platform)
    if not os.path.isfile(markerPath):
        return False
    try:
        with open(markerPath, 'r') as markerFile:
            return markerFile.read().strip() == packageInstallFingerprint(platform, buildCommand, installfileList)
    except OSError:
        return False

def writePackageBuildMarker(libsFolder, platform, buildCommand, installfileList):
    markerPath = packageBuildMarkerPath(libsFolder, platform)
    with open(markerPath, 'w') as markerFile:
        markerFile.write(packageInstallFingerprint(platform, buildCommand, installfileList))

def packageInstallPayloadExists(downloadedFolder, libsFolder, installfileList):
    if not os.path.isdir(libsFolder):
        return False
    for filenameX in installfileList:
        installFile = installSpecPath(filenameX[0][0])
        sourcePath = os.path.normpath(os.path.join(downloadedFolder, installFile))
        if not installPayloadDestinationExists(sourcePath, installFile, libsFolder):
            return False
    return True

def fetchPackages(packageData, packageDirectory):
    for package in packageData:
        packageMap   = progSpec.extractMapFromTagMap(package)
        packageName  = getPackageName(packageMap)
        fetchType    = getFetchType(packageMap)
        fetchURL     = getFetchURL(packageMap)
        fetchRef     = getFetchRef(packageMap)
        buildCmdsMap = {}
        if packageName=="" or fetchType=="": return
        buildStatus("Checking package '{}' ({})".format(packageName, fetchType))
        if fetchType == "git":    gitClone(fetchURL, packageName, packageDirectory, fetchRef)
        elif fetchType == "file": downloadPackageFile(fetchURL, packageName, packageDirectory)
        elif fetchType == "zip":  downloadExtractZip(fetchURL, packageName, packageDirectory)
        elif fetchType == "sys":  emgr.checkAndUpgradeOSPackageVersions(packageName)
        else: pass

def fetchPackageToWorkspace(packageMap, packageName, packageRoot):
    sourceParent = packageSourceParent(packageRoot)
    makeDirs(sourceParent)
    makeDirs(packageBuildDir(packageRoot))
    makeDirs(packageStageDir(packageRoot))
    fetchType = getFetchType(packageMap)
    fetchURL = getFetchURL(packageMap)
    fetchRef = getFetchRef(packageMap)
    if packageName=="" or fetchType=="":
        return
    buildStatus("Checking package '{}' ({})".format(packageName, fetchType))
    if fetchType == "git":
        gitCloneToSource(fetchURL, packageName, sourceParent, fetchRef)
    elif fetchType == "file":
        downloadPackageFileToSource(fetchURL, packageName, sourceParent)
    elif fetchType == "zip":
        downloadExtractArchiveToSource(fetchURL, packageName, sourceParent)
    elif fetchType == "sys":
        emgr.checkAndUpgradeOSPackageVersions(packageName)

def toolIsAvailable(platform, toolName):
    toolName = 'go' if toolName == 'golang-go' else toolName
    if platform == 'Windows':
        return emgr.checkToolWindows(toolName) or executableExistsInDirs(toolName, windowsToolDirs())
    return emgr.checkToolLinux(toolName)

def ensureToolsAvailable(platform, tools):
    for toolName in tools:
        checkToolName = 'go' if toolName == 'golang-go' else toolName
        if toolIsAvailable(platform, toolName):
            continue
        packageManagers = emgr.findPackageManager()
        if not packageManagers:
            cdErr("Required build tool not found and no package manager is available: " + checkToolName)
        emgr.packageInstall(toolName)
        if not toolIsAvailable(platform, toolName):
            cdErr("Required build tool is still unavailable after install attempt: " + checkToolName)

def FindOrFetchLibraries(buildName, packageData, platform, tools, buildTags=None):
    #print("#############:buildName:", buildName, platform)
    packageDirectory = os.path.join(os.getcwd(), buildName)
    targetKey = targetKeyFromBuildTags(buildTags, platform)
    includePaths = []
    libPaths = []
    folderAliases = {}
    buildStatus("Resolving {} package(s) for {}".format(len(packageData), buildName))
    for package in packageData:
        packageMap   = progSpec.extractMapFromTagMap(package)
        packageName  = getPackageName(packageMap)
        innerPkgName = getInnerPackageName(packageMap)
        packageRoot = packageWorkspace(packageDirectory, targetKey, packageName)
        stageDir = packageStageDir(packageRoot)
        fetchPackageToWorkspace(packageMap, packageName, packageRoot)
        downloadedFolder = os.path.normpath(os.path.join(packageSourceParent(packageRoot), innerPkgName))
        folderAliases[packageName] = downloadedFolder.replace("\\","/")
        folderAliases[packageName+'@Source'] = downloadedFolder.replace("\\","/")
        folderAliases[packageName+'@Stage'] = stageDir.replace("\\","/")
        folderAliases[packageName+'@Install'] = stageDir.replace("\\","/")
        buildCmdsMap = {}
        if 'buildCmds' in packageMap:
            buildCmds = packageMap['buildCmds']
            buildCmdsMap = progSpec.extractMapFromTagMap(buildCmds)
        if buildCmdsMap!={} and platform in buildCmdsMap:
            #print("###########:",platform, ' = ', buildCmdsMap[platform])
            buildCommand = buildCmdsMap[platform]
            buildCmdMap = progSpec.extractMapFromTagMap(buildCommand)
            installfileList = []
            LibsFolder = stageDir.replace("\\","/")
            if 'installFiles' in buildCmdMap:
                installfileList = buildCmdMap['installFiles'][1]
                makeDirs(LibsFolder)

            actualBuildCmd = ""
            if 'buildCmd' in buildCmdMap:
                actualBuildCmd = tagValueToString(buildCmdMap['buildCmd'])
                actualBuildCmd = replacePackageAliases(actualBuildCmd, folderAliases)
                #print("BUILDCOMMAND:", actualBuildCmd)#, "  INSTALL:", buildCmdsMap[platform][1])

            installIsCurrent = False
            if installfileList:
                installIsCurrent = packageInstallIsCurrent(LibsFolder, platform, actualBuildCmd, installfileList)
                if not actualBuildCmd and not installIsCurrent and packageInstallPayloadExists(downloadedFolder, LibsFolder, installfileList):
                    writePackageBuildMarker(LibsFolder, platform, actualBuildCmd, installfileList)
                    installIsCurrent = True
                if installIsCurrent:
                    buildStatus("Using cached package build '{}'".format(packageName))

            if actualBuildCmd and not installIsCurrent:
                ensureToolsAvailable(platform, tools)
                result = runCmdStreaming(actualBuildCmd, downloadedFolder)
                if result != 0:
                    cdErr("Package build failed: " + packageName)

            if installfileList and not installIsCurrent:
                for filenameX in installfileList:
                    installFile = installSpecPath(filenameX[0][0])
                    filename = os.path.normpath(os.path.join(downloadedFolder, installFile))
                    cdlog(1, "Install: "+filename)
                    copyInstallPayload(filename, installFile, LibsFolder)
                writePackageBuildMarker(LibsFolder, platform, actualBuildCmd, installfileList)
            if installfileList:
                manifest = writePackageManifest(packageName, targetKey, packageRoot, LibsFolder, getFetchRef(packageMap))
                for includeDir in manifest["includeDirs"]:
                    appendExistingPath(includePaths, includeDir)
                for libDir in manifest["libDirs"]:
                    appendExistingPath(libPaths, libDir)

    return [sconsPathEntries(includePaths), sconsPathEntries(libPaths)]

def buildSconsFile(fileName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData, fileExtension, tools, buildTags=None):
    buildStatus("Preparing SCons build script for {}".format(fileName))
    (includeFolders, libFolders) = FindOrFetchLibraries(buildName, packageData, platform, tools, buildTags)
    SconsFile = "import os\n\n"
    SconsFile += "env = Environment(ENV=os.environ)\n"
    SconsFile += 'env.Decider("timestamp-newer")\n'
    if platform == 'Windows':
        SconsFile += 'env.Append(CCFLAGS=["/EHsc", "/std:c++17", "/MD"])\n'
        SconsFile += 'env.Append(CPPDEFINES=["NOMINMAX"])\n'
    #SconsFile += "env.MergeFlags('-g -fpermissive')\n"
    if progOrLib=='program': SconsFileType = "Program"
    elif progOrLib=='library': SconsFileType = "Library"
    elif progOrLib=='staticlibrary': SconsFileType = "StaticLibrary"
    elif progOrLib=='sharedlibrary': SconsFileType = "SharedLibrary"
    else: SconsFileType = "Library"

    SconsFileOut = 'env.'+SconsFileType+'(\n'
    SconsFileOut += '    target='+'"'+fileName+'",\n'
    SconsFileOut += '    source='+sconsSourceList(fileSpecs, fileExtension)+',\n'

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

def LinuxBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData, tools, buildTags=None):
    fileExtension = '.cpp'
    buildStatus("Writing generated source for {}".format(fileName))
    writeGeneratedFiles(buildName, fileSpecs, fileExtension)

    if os.path.isdir("Resources"):
        buildStatus("Copying Resources into {}".format(buildName))
        copyRecursive("Resources", buildName+"/assets")
    (includeFolders, libFolders) = FindOrFetchLibraries(buildName, packageData, platform, tools, buildTags)

    #building scons file
    SconsFile = "import os\n"
    SconsFile += "\nenv = Environment(ENV=os.environ)\nenv.MergeFlags('-g -std=gnu++17 -fpermissive  -fdiagnostics-color=always')\n"
    SconsFile += 'env.Decider("timestamp-newer")\n'
    if progOrLib=='program': SconsFileType = "Program"
    elif progOrLib=='library': SconsFileType = "Library"
    elif progOrLib=='staticlibrary': SconsFileType = "StaticLibrary"
    elif progOrLib=='sharedlibrary': SconsFileType = "SharedLibrary"
    else: SconsFileType = "Library"

    SconsFileOut = 'env.'+SconsFileType+'(\n'
    SconsFileOut += '    target='+'"'+fileName+'",\n'
    SconsFileOut += '    source='+sconsSourceList(fileSpecs, fileExtension)+',\n'

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
    buildStatus("Writing SCons build script for {}".format(fileName))
    writeFile(buildName, sconsFilename, [[[sconsFilename],SconsFile]], "")
    return [workingDirectory, buildStr, runStr]

def WindowsBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData, tools, buildTags=None):
    buildStr = ''
    codeDogFolder = os.path.dirname(os.path.realpath(__file__))
    libStr = "-I " + codeDogFolder + " "
    #minLangStr = '-std=gnu++' + minLangVersion + ' '
    fileExtension = '.cpp'
    #outputFileStr = '-o ' + fileName
    buildSconsFile(fileName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData, fileExtension, tools, buildTags)

    buildStatus("Writing generated source for {}".format(fileName))
    writeGeneratedFiles(buildName, fileSpecs, fileExtension)
    if os.path.isdir("Resources"):
        buildStatus("Copying Resources into {}".format(buildName))
        copyRecursive("Resources", buildName + os.sep + "assets")
    buildStatus("Copying Windows runtime DLLs")
    copyWindowsRuntimeDlls(buildName)

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

def kotlinCompilerCommand():
    localKotlinc = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".tools", "kotlin-apt", "usr", "share", "kotlin", "kotlinc", "bin", "kotlinc")
    if os.path.isfile(localKotlinc):
        return '"' + localKotlinc + '"'
    return "kotlinc"

def quoteShellPath(path):
    return '"' + path.replace('"', '\\"') + '"'

def swiftCompilerCommand():
    envSwiftc = os.environ.get("CODEDOG_SWIFTC")
    if envSwiftc:
        return quoteShellPath(envSwiftc)

    swiftlyHome = os.environ.get("SWIFTLY_HOME_DIR", os.path.expanduser("~/.local/share/swiftly"))
    swiftlyConfig = os.path.join(swiftlyHome, "config.json")
    try:
        with open(swiftlyConfig, "r") as configFile:
            config = json.load(configFile)
        inUse = config.get("inUse")
        if inUse:
            swiftcPath = os.path.join(swiftlyHome, "toolchains", inUse, "usr", "bin", "swiftc")
            if os.path.isfile(swiftcPath):
                return quoteShellPath(swiftcPath)
    except (OSError, ValueError):
        pass

    return "swiftc"

def swiftModuleCacheOption():
    cachePath = os.environ.get("CODEDOG_SWIFT_MODULE_CACHE", "/tmp/codedog-swift-module-cache")
    return "-module-cache-path " + quoteShellPath(cachePath)

def KotlinBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs):
    fileExtension = '.kt'
    currentDirectory = os.getcwd()
    workingDirectory = currentDirectory + "/" + buildName
    makeDirs(buildName)
    writeFile(workingDirectory, fileName, fileSpecs, fileExtension)
    buildStr = getBuildSting(fileName, "", platform, buildName)
    runStr = "java -jar " + fileName + ".jar"
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

    startTime = time.monotonic()
    buildStatus("Starting SCons build")
    result = runCmdStreaming(buildStr, workingDirectory)
    if result==0:
        buildStatus("SCons build finished in {:.1f}s".format(time.monotonic() - startTime))
        print("\nSUCCESS\n")
    else:
        buildStatus("SCons build failed in {:.1f}s".format(time.monotonic() - startTime))
        print("\nBuild failed\n")
        exit(-1)

def build(debugMode, minLangVersion, fileName, labelName, launchIconName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData, tools, buildTags=None):
    cdlog(0,"\n##############   B U I L D I N G    S Y S T E M...   ({})".format(buildName))
    buildStatus("Preparing {} build '{}'".format(platform, buildName))
    progOrLib = progOrLib.lower()
    if platform == 'Linux':
        [workingDirectory, buildStr, runStr] = LinuxBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData, tools, buildTags)
    elif platform == 'Java' or  platform == 'Swing':
        [workingDirectory, buildStr, runStr] = SwingBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs)
    elif platform == 'Android':
        buildAndroid.AndroidBuilder(debugMode, minLangVersion, fileName, labelName, launchIconName, libFiles, buildName, platform, fileSpecs, buildTags)
    elif platform == 'Swift':
        [workingDirectory, buildStr, runStr] = SwiftBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs)
    elif platform == 'Kotlin':
        [workingDirectory, buildStr, runStr] = KotlinBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs)
    elif platform == 'Windows':
        [workingDirectory, buildStr, runStr] = WindowsBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, fileSpecs, progOrLib, packageData, tools, buildTags)
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
        pythonExe = '"' + sys.executable + '"'
        buildStr = f"{pythonExe} {codeDogPath}/Scons/scons.py -Q -f "+fileName+".scons"
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
        buildStr = swiftCompilerCommand() + " -suppress-warnings " + swiftModuleCacheOption() + " " + fileName + fileExtension
    elif platform == 'Kotlin':
        fileExtension = '.kt'
        buildStr = kotlinCompilerCommand() + " " + fileName + fileExtension + " -include-runtime -d " + fileName + ".jar"
    elif platform == 'Windows':
        codeDogPath = os.path.dirname(os.path.realpath(__file__))
        pythonExe = '"' + sys.executable + '"'
        buildStr = f"{pythonExe} {codeDogPath}/Scons/scons.py -Q -f "+fileName+".scons"
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
        pythonExe = '"' + sys.executable + '"'
        sconsCMD = pythonExe+" "+codeDogPath+"/Scons/scons.py -Q -f "+sconsFile + ' '+ otherSconsArgs
        result = runCmdStreaming(sconsCMD, basepath)
        if result==0:
            print("\nSUCCESS\n")
        else:
            print("\nBuild failed\n")
            exit(-1)
