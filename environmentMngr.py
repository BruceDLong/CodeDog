import os
import subprocess
from progSpec import cdlog, cdErr
import checkSys


def checkToolLinux(toolName):
    if subprocess.call(["which", toolName], stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0:
        return True
    else:
        return None

def checkToolWindows(toolName):
    if subprocess.call(["Where", toolName], stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0:
        return True
    else:
        return None

def findPackageManager():
    installedPackageManagerList = []
    packageManagers = ["dpkg", "brew", "yum", "apt-get", "pacman", "emerge", "zypper", "dnf"]

    for pmgr in packageManagers:
        if checkToolLinux(pmgr):
            installedPackageManagerList.append(pmgr)
    return installedPackageManagerList


def packageInstalled(packageManagar, packageName):
    cdlog(1, "Package Installing: "+packageName)
    if subprocess.call(f'{packageManagar} {packageName}'+" -y > /dev/null 2>&1", shell=True) == 0:
        cdlog(1, "Package installed Successfully")
        return True
    else:
        cdErr("Unable to install package. \nPlease install manually : " + packageName)


def getPackageManagerCMD(packageName, installedPackageManagerList):
    packageExtension = packageName.split(".")[-1]

    for ipm in installedPackageManagerList:
        if ipm == 'dpkg' and packageExtension == 'deb':
            if packageInstalled("sudo dpkg -i", packageName):
                break
        elif ipm == 'apt-get':
            if packageInstalled("sudo apt-get install", packageName):
                break
        elif ipm == 'yum':
            if packageInstalled("sudo yum install", packageName):
                break
        elif ipm == 'pacman':
            if packageInstalled("sudo pacman -S", packageName):
                break
        elif ipm == 'dnf':
            if packageInstalled("sudo dnf install", packageName):
                break
        elif ipm == 'emerge':
            if packageInstalled("sudo emerge -pv", packageName):
                break
        elif ipm == 'zypper':
            if packageInstalled("sudo zypper install", packageName):
                break
        elif ipm == 'brew':
            if packageInstalled("brew install --cask", packageName):
                break


def checkAndUpgradeOSPackageVersions(packageName):
    cdlog(1, f"Searching for package: {packageName}")
    installedPackage = os.popen(f'apt-cache policy {packageName} | grep Installed')
    if installedPackage.read():
        installedPackage = os.popen(f'apt-cache policy {packageName} | grep Installed')
        candidatePackage = os.popen(f'apt-cache policy {packageName} | grep Candidate')
        installedVersion = installedPackage.read().split(" ")[-1].replace('\n','')
        candidateVersion = candidatePackage.read().split(" ")[-1].replace('\n','')
        cdlog(1, f"Candidate Package available: {candidateVersion}")
        if installedVersion or installedVersion == '(none)':
            if installedVersion != candidateVersion:
                getPackageManagerCMD(packageName, findPackageManager())
            else:
                cdlog(1, f"Package already Installed: {packageName}")
    else:
        print(f"Unable to find package. \nPlease install manually : {packageName}")


def downloadFile(fileName, downloadURL):
    checkSys.CheckPipModules({'urllib3':'1.25'})
    import urllib3
    try:
        cdlog(1, "Downloading file: " + fileName)
        http = urllib3.PoolManager()
        r = http.request('GET', downloadURL, preload_content=False)
    except:
        cdErr("URL not found: " + downloadURL)
    else:
        with open(fileName, 'wb') as out:
            while True:
                data = r.read(1028)
                if not data:
                    break
                out.write(data)
        r.release_conn()


def installPipPackage():
    from sys import platform
    if platform == "linux" or platform == "linux2":
        toolName = "pip3"
        if not checkToolLinux(toolName):
            getPackageManagerCMD('python3-pip', findPackageManager()) # Install PIP3

    elif platform == "darwin":
        toolName = "pip3"
        if not checkToolLinux(toolName):
            downloadUrl = "https://bootstrap.pypa.io/get-pip.py"
            fileName = "get-pip.py"
            downloadFile(fileName, downloadUrl)
            os.system('python get-pip.py') # Install PIP3

    elif platform == "win32" or platform == "win64":
        toolName = "pip3"
        if not checkToolWindows(toolName):
            downloadUrl = "https://bootstrap.pypa.io/get-pip.py"
            fileName = "get-pip.py"
            downloadFile(fileName, downloadUrl)
            os.system('py get-pip.py') # Install PIP3