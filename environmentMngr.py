import os
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
    packageManagers = ["dpkg", "brew", "yum", "apt-get", "pacman", "emerge", "zypper", "dnf"]

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
        print(f"Unable to install package. \nPlease install manually : {packageName}")
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


#TODO: error handling
def string_escape(s, encoding='utf-8'):
    return (s.encode('latin1')         # To bytes, required by 'unicode-escape'
             .decode('unicode-escape') # Perform the actual octal-escaping decode
             .encode('latin1')         # 1:1 mapping back to bytes
             .decode(encoding))        # Decode original encoding


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
