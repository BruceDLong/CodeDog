#!/usr/bin/env python3
import subprocess
import os
import sys
import glob
import importlib
import io
import json
import shutil
import urllib.request
import zipfile
from pmgrHandler import checkToolLinux, checkToolWindows, findPackageManager

PYPARSING_REQUIREMENT = "pyparsing>=3.3"
LOCAL_PY_DEPS_DIR = ".codedog-python"

def _projectRoot():
    return os.path.dirname(os.path.abspath(__file__))

def _localPyDepsPath():
    return os.path.join(_projectRoot(), LOCAL_PY_DEPS_DIR)

def _versionAtLeast(version, minimum=(3, 3)):
    try:
        parts = []
        for part in str(version).split(".")[:len(minimum)]:
            digits = ""
            for ch in part:
                if ch.isdigit():
                    digits += ch
                else:
                    break
            parts.append(int(digits or "0"))
        while len(parts) < len(minimum):
            parts.append(0)
        return tuple(parts) >= minimum
    except (TypeError, ValueError):
        return False

def _addLocalPyDepsToPath():
    localPath = _localPyDepsPath()
    if os.path.isdir(localPath) and localPath not in sys.path:
        sys.path.insert(0, localPath)

def _hasRequiredPyparsing():
    _addLocalPyDepsToPath()
    importlib.invalidate_caches()
    try:
        import pyparsing
    except Exception:
        return False
    if _versionAtLeast(getattr(pyparsing, "__version__", None)):
        return True
    for moduleName in list(sys.modules):
        if moduleName == "pyparsing" or moduleName.startswith("pyparsing."):
            del sys.modules[moduleName]
    importlib.invalidate_caches()
    return False

def _runCommand(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def _printInstallFailure(label, result):
    print(label + " failed.")
    errText = (result.stderr or result.stdout or "").strip()
    if errText:
        print(errText.splitlines()[-1])

def _pythonCommandsToTry():
    candidates = []
    if sys.executable:
        candidates.append([sys.executable])
    for name in ["python3", "python3.14", "python3.13", "python3.12", "python3.11", "python"]:
        path = shutil.which(name)
        if path:
            candidates.append([path])
    if os.name == "nt" and shutil.which("py"):
        candidates.append(["py", "-3"])

    unique = []
    seen = set()
    for cmd in candidates:
        key = tuple(cmd)
        if key not in seen:
            unique.append(cmd)
            seen.add(key)
    return unique

def _installWithPip(cmd, targetPath=None):
    installCmd = cmd + ["-m", "pip", "install", "--upgrade"]
    if targetPath:
        installCmd += ["--target", targetPath]
    installCmd.append(PYPARSING_REQUIREMENT)
    return _runCommand(installCmd)

def _clearLocalPyparsing(targetPath):
    shutil.rmtree(os.path.join(targetPath, "pyparsing"), ignore_errors=True)
    for path in glob.glob(os.path.join(targetPath, "pyparsing-*.dist-info")):
        shutil.rmtree(path, ignore_errors=True)

def _downloadUrl(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()

def _installPyparsingWheelDirect(targetPath):
    os.makedirs(targetPath, exist_ok=True)
    metadata = json.loads(_downloadUrl("https://pypi.org/pypi/pyparsing/json").decode("utf-8"))
    wheelCandidates = []
    for version, releaseFiles in metadata.get("releases", {}).items():
        if not _versionAtLeast(version):
            continue
        for releaseFile in releaseFiles:
            filename = releaseFile.get("filename", "")
            if releaseFile.get("packagetype") == "bdist_wheel" and filename.endswith("py3-none-any.whl"):
                wheelCandidates.append((_versionSortKey(version), releaseFile.get("url")))
    if not wheelCandidates:
        raise RuntimeError("No compatible pyparsing wheel found on PyPI.")

    wheelCandidates.sort(reverse=True)
    wheelUrl = wheelCandidates[0][1]
    if not wheelUrl:
        raise RuntimeError("PyPI did not provide a download URL for pyparsing.")

    wheelBytes = _downloadUrl(wheelUrl)
    _clearLocalPyparsing(targetPath)
    with zipfile.ZipFile(io.BytesIO(wheelBytes)) as wheel:
        wheel.extractall(targetPath)

def _versionSortKey(version):
    key = []
    for part in str(version).split("."):
        digits = ""
        for ch in part:
            if ch.isdigit():
                digits += ch
            else:
                break
        key.append(int(digits or "0"))
    return tuple(key)

def downloadFileNoLog(fileName, downloadURL):
    import urllib3
    try:
        #cdlog(1, "Downloading file: " + fileName)
        print("Downloading file: " + fileName)
        http = urllib3.PoolManager()
        r = http.request('GET', downloadURL, preload_content=False)
    except:
        #cdErr("URL not found: " + downloadURL)
        print("URL not found:" + downloadURL)
    else:
        with open(fileName, 'wb') as out:
            while True:
                data = r.read(1028)
                if not data:
                    break
                out.write(data)
        r.release_conn()

def packageInstallNoLog(packageName):
    from pmgrHandler import getPackageManagerCMD
    pmgrCMD = getPackageManagerCMD(packageName, findPackageManager(),"install")
    #cdlog(1, "Package Installing: "+packageName)
    print(f"Package Installing: {packageName}")
    if subprocess.call(f"{pmgrCMD} > /dev/null 2>&1", shell=True) == 0:
        print("Package installed Successfully")
        return True
    else:
        print(f"Unable to install package. \nPlease install manually : {packageName}")

def installPipPackage():
    from sys import platform
    
    toolName = "pip3"
    downloadUrl = "https://bootstrap.pypa.io/get-pip.py"
    fileName = "get-pip.py"
    
    if platform == "linux" or platform == "linux2" or platform == "linux-gnu":
        if subprocess.call(["which", "pip3"], stdout=subprocess.PIPE, stderr=subprocess.PIPE) != 0:
            from pmgrHandler import getPackageManagerCMD
            pmgrCMD = getPackageManagerCMD("python-pip", findPackageManager(),"install")
            print("Package Installing: python3-pip") # Install PIP3
            if subprocess.call(f"{pmgrCMD} > /dev/null 2>&1", shell=True) == 0:
                print("pip3 installed Successfully")
                return True
            # If package manager fails to install, try using the bootstrap script
            elif not checkToolLinux(toolName):
                print("Package install of pip3 failed...")
                print("Attempting install using bootstrap script.")
                downloadFileNoLog(fileName, downloadUrl)
                if os.system('python3 get-pip.py') == 0:
                    print("pip3 installed Successfully")
                    return True
                else:
                    print("Unable to install package. \nPlease install manually : python3-pip")
                    return False
        # # If package manager fails to install, try using the bootstrap script
        # if not checkToolLinux(toolName):
        #     downloadFile(fileName, downloadUrl)
        #     os.system('python3 get-pip.py') # Install PIP3
        #     return True

    elif platform == "darwin":
        if shutil.which(toolName) is None:
            downloadFileNoLog(fileName, downloadUrl)
            subprocess.call([sys.executable, fileName]) # Install PIP3

    elif platform == "win32" or platform == "win64":
        if not checkToolWindows(toolName):
            downloadFileNoLog(fileName, downloadUrl)
            os.system('py get-pip.py') # Install PIP3

def installPyparsing():
    if _hasRequiredPyparsing():
        return True

    result = _installWithPip([sys.executable])
    if result.returncode == 0 and _hasRequiredPyparsing():
        return True
    _printInstallFailure("Installing pyparsing with the active Python", result)

    localPath = _localPyDepsPath()
    os.makedirs(localPath, exist_ok=True)
    for pythonCmd in _pythonCommandsToTry():
        result = _installWithPip(pythonCmd, localPath)
        if result.returncode == 0 and _hasRequiredPyparsing():
            print("Installed pyparsing into " + localPath)
            return True

    try:
        _installPyparsingWheelDirect(localPath)
        if _hasRequiredPyparsing():
            print("Installed pyparsing into " + localPath)
            return True
    except Exception as exc:
        print("Direct pyparsing wheel install failed: " + str(exc))

    raise RuntimeError(
        "Unable to install pyparsing. The active Python pip may be broken. "
        "Try repairing Python/pip, or manually install pyparsing>=3.3 into " + localPath
    )
