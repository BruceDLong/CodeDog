# buildWeb.py

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request

import buildDog
from progSpec import cdErr


WEB_TOOLCHAIN = ['emcc', 'em++', 'emar', 'emranlib', 'emrun']
EMSDK_ARCHIVE_URL = 'https://github.com/emscripten-core/emsdk/archive/refs/heads/main.zip'
DEFAULT_EMSDK_VERSION = '6.0.3'


def confirmDependencyInstall(description):
    autoInstall = os.environ.get('CODEDOG_AUTO_INSTALL_DEPS', '').strip().lower()
    if autoInstall in ['y', 'yes', 'true', '1']:
        return True
    if autoInstall in ['n', 'no', 'false', '0']:
        return False

    try:
        if sys.stdin.isatty():
            response = input("Install {}? [Y/n] ".format(description))
            return response.strip().lower() in ['', 'y', 'yes']
    except EOFError:
        pass
    return False


def emsdkRoot():
    configuredRoot = os.environ.get('CODEDOG_EMSDK_ROOT')
    if configuredRoot:
        return os.path.abspath(os.path.expanduser(configuredRoot))
    codeDogFolder = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(codeDogFolder, '.tools', 'emsdk')


def findWebToolchain():
    localEmscriptenFolder = os.path.join(emsdkRoot(), 'upstream', 'emscripten')
    toolchain = {}
    for toolName in WEB_TOOLCHAIN:
        toolPath = shutil.which(toolName)
        if toolPath is None:
            for suffix in ['', '.bat', '.cmd', '.py']:
                localToolPath = os.path.join(localEmscriptenFolder, toolName + suffix)
                if os.path.isfile(localToolPath):
                    toolPath = localToolPath
                    break
        toolchain[toolName] = toolPath
    return toolchain


def _emsdkLauncher(sdkRoot):
    launcherName = 'emsdk.bat' if os.name == 'nt' else 'emsdk'
    return os.path.join(sdkRoot, launcherName)


def _downloadEmsdk(sdkRoot):
    if os.path.exists(sdkRoot):
        cdErr(
            "Emscripten SDK directory exists but has no emsdk launcher: {}. "
            "Repair or remove that directory, then retry.".format(sdkRoot)
        )
    toolsFolder = os.path.dirname(sdkRoot)
    os.makedirs(toolsFolder, exist_ok=True)
    buildDog.buildStatus("Downloading the Emscripten SDK bootstrap")
    try:
        with tempfile.TemporaryDirectory(prefix='emsdk-download-', dir=toolsFolder) as tempDir:
            archivePath = os.path.join(tempDir, 'emsdk.zip')
            with urllib.request.urlopen(EMSDK_ARCHIVE_URL, timeout=60) as response:
                with open(archivePath, 'wb') as archiveFile:
                    shutil.copyfileobj(response, archiveFile)
            shutil.unpack_archive(archivePath, tempDir)
            extractedRoot = os.path.join(tempDir, 'emsdk-main')
            if not os.path.isfile(_emsdkLauncher(extractedRoot)):
                cdErr("Downloaded Emscripten SDK archive did not contain the emsdk launcher.")
            shutil.move(extractedRoot, sdkRoot)
            if os.name != 'nt':
                launcher = _emsdkLauncher(sdkRoot)
                os.chmod(
                    launcher,
                    os.stat(launcher).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
                )
    except Exception as err:
        cdErr("Unable to download the Emscripten SDK: " + str(err))


def _runEmsdk(sdkRoot, arguments):
    launcher = _emsdkLauncher(sdkRoot)
    if os.name == 'nt':
        command = ['cmd.exe', '/d', '/c', launcher] + arguments
    else:
        command = [launcher] + arguments
    return subprocess.call(command, cwd=sdkRoot)


def installWebToolchain():
    sdkRoot = emsdkRoot()
    launcher = _emsdkLauncher(sdkRoot)
    if not os.path.isfile(launcher):
        _downloadEmsdk(sdkRoot)

    sdkVersion = os.environ.get('CODEDOG_EMSDK_VERSION', DEFAULT_EMSDK_VERSION)
    buildDog.buildStatus("Installing Emscripten SDK version '{}'".format(sdkVersion))
    if _runEmsdk(sdkRoot, ['install', sdkVersion]) != 0:
        cdErr("Emscripten SDK installation failed for version: " + sdkVersion)
    if _runEmsdk(sdkRoot, ['activate', sdkVersion]) != 0:
        cdErr("Emscripten SDK activation failed for version: " + sdkVersion)


def ensureWebToolchain(toolchain):
    missingTools = [toolName for toolName in WEB_TOOLCHAIN if toolchain[toolName] is None]
    if not missingTools:
        return toolchain

    description = "Emscripten SDK under '{}'".format(emsdkRoot())
    print("WebBuild is missing required tools: " + ', '.join(missingTools))
    if not confirmDependencyInstall(description):
        cdErr(
            "Web build requires the Emscripten toolchain. Missing: {}. "
            "Install Emscripten, activate its environment, set CODEDOG_EMSDK_ROOT, "
            "or set CODEDOG_AUTO_INSTALL_DEPS=yes."
            .format(', '.join(missingTools))
        )
    installWebToolchain()
    toolchain = findWebToolchain()
    missingTools = [toolName for toolName in WEB_TOOLCHAIN if toolchain[toolName] is None]
    if missingTools:
        cdErr(
            "Emscripten installation completed, but required tools are still missing: "
            + ', '.join(missingTools)
        )
    return toolchain


def webSconsFileText(fileName, fileSpecs, includeFolders, libFolders, libFiles,
                     hasAssets, toolchain):
    codeDogFolder = os.path.dirname(os.path.realpath(__file__)).replace('\\', '/')
    linkedLibraries = []
    usePthreads = False

    for libFile in libFiles:
        if libFile == 'pthread':
            usePthreads = True
        elif libFile.startswith('pkg-config'):
            cdErr("Web builds do not yet support pkg-config link entries: " + libFile)
        else:
            linkedLibraries.append(libFile)

    sconsFile = "import os\n\n"
    sconsFile += "env = Environment(\n"
    sconsFile += "    ENV=os.environ,\n"
    sconsFile += '    CC=' + repr(toolchain['emcc'] or 'emcc') + ',\n'
    sconsFile += '    CXX=' + repr(toolchain['em++'] or 'em++') + ',\n'
    sconsFile += '    LINK=' + repr(toolchain['em++'] or 'em++') + ',\n'
    sconsFile += '    AR=' + repr(toolchain['emar'] or 'emar') + ',\n'
    sconsFile += '    RANLIB=' + repr(toolchain['emranlib'] or 'emranlib') + ',\n'
    sconsFile += "    PROGSUFFIX='.html',\n"
    sconsFile += ")\n"
    sconsFile += 'env.Decider("timestamp-newer")\n'
    sconsFile += "env.Append(CCFLAGS=['-g', '-std=gnu++17'])\n"
    sconsFile += "env.Append(LINKFLAGS=['-g', '--emrun'])\n"

    if usePthreads:
        # WebBuild currently selects the pthread Threads provider by default.
        # Keeping this conditional on the selected libraries leaves room for
        # an explicitly single-threaded Web provider in a future upgrade.
        sconsFile += "env.Append(CCFLAGS=['-pthread'])\n"
        sconsFile += "env.Append(LINKFLAGS=['-pthread', '-sPROXY_TO_PTHREAD', "
        sconsFile += "'-sPTHREAD_POOL_SIZE=navigator.hardwareConcurrency'])\n"

    if hasAssets:
        # TODO: Decide which resources belong in Emscripten's virtual file
        # system and which should remain ordinary files served by the site.
        sconsFile += "env.Append(LINKFLAGS=['--preload-file', 'assets@/assets'])\n"

    sconsFile += 'env["CPPPATH"]=[\n' + includeFolders + ']\n'
    sconsFile += 'env["LIBPATH"]=[\n     r"' + codeDogFolder + '",\n' + libFolders + ']\n'
    sconsFile += 'env["LIBS"] = ' + repr(linkedLibraries) + '\n'
    sconsFile += "program = env.Program(\n"
    sconsFile += '    target=' + repr(fileName) + ',\n'
    sconsFile += '    source=' + buildDog.sconsSourceList(fileSpecs, '.cpp') + ',\n'
    sconsFile += ")\n"
    sconsFile += 'env.SideEffect(' + repr(fileName + '.js') + ', program)\n'
    sconsFile += 'env.SideEffect(' + repr(fileName + '.wasm') + ', program)\n'
    if hasAssets:
        sconsFile += 'env.SideEffect(' + repr(fileName + '.data') + ', program)\n'

    # TODO: Add build-tag-driven optimization/debug profiles after the basic
    # Web pipeline is validated.
    # TODO: Add an optional custom Emscripten shell file after the default HTML
    # shell is working.
    return sconsFile


def WebBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform,
               fileSpecs, progOrLib, packageData, tools, buildTags=None):
    if progOrLib != 'program':
        cdErr("Web builds currently support ProgramOrLibrary='program' only.")

    fileExtension = '.cpp'
    buildDog.buildStatus("Writing generated source for {}".format(fileName))
    buildDog.writeGeneratedFiles(buildName, fileSpecs, fileExtension)
    toolchain = ensureWebToolchain(findWebToolchain())

    hasAssets = os.path.isdir('Resources')
    if hasAssets:
        buildDog.buildStatus("Copying Resources into {}".format(buildName))
        buildDog.copyRecursive('Resources', os.path.join(buildName, 'assets'))

    includeFolders, libFolders = buildDog.FindOrFetchLibraries(
        buildName, packageData, platform, tools, buildTags
    )
    sconsFile = webSconsFileText(
        fileName, fileSpecs, includeFolders, libFolders, libFiles, hasAssets,
        toolchain
    )
    sconsFilename = fileName + '.scons'
    buildDog.buildStatus("Writing SCons build script for {}".format(fileName))
    buildDog.writeTextFile(buildName, sconsFilename, sconsFile)

    workingDirectory = os.path.join(os.getcwd(), buildName)
    buildStr = buildDog.getBuildSting(fileName, '', platform, buildName)
    runStr = buildDog.quoteShellPath(toolchain['emrun']) + ' ' + fileName + '.html'

    # TODO: Add static-library output only after the program pipeline is stable.
    return [workingDirectory, buildStr, runStr]
