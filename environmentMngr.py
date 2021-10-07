import subprocess
from progSpec import cdlog, cdErr

def checkTool(toolName):
    if toolName=='golang-go': toolName='go'  #Check for Go language
    if subprocess.call(["which", toolName], stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0:
        return True
    else:
        return None

def findPackageManager():
    installedPackageManagerList = []
    packageManagers = ["dpkg", "brew", "yum", "apt-get", "pacman", "emerge", "zypper"]

    for pmgr in packageManagers:
        if checkTool(pmgr):
            installedPackageManagerList.append(pmgr)
    return installedPackageManagerList

def packageInstalled(packageManagar, packageName):
    cdlog(1, "Package Installing: "+packageName)
    if subprocess.call(f'{packageManagar} {packageName}'+" > /dev/null 2>&1", shell=True) == 0:
        cdlog(1, "Package installed Successfully")
        return True
    else:
        cdErr(f"Unable to install package. \nPlease install {packageName} manually : " + {packageName})

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
        elif ipm == 'emerge':
            if packageInstalled("sudo emerge -pv", packageName):
                break
        elif ipm == 'zypper':
            if packageInstalled("sudo zypper install", packageName):
                break
        elif ipm == 'brew':
            if packageInstalled("brew install --cask", packageName):
                break