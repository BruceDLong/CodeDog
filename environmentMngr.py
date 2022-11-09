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

#def detPackageNomenclature(packageName)
    #TODO: add OS-specific detection to handle different package nomenclatures
    # package base-names can be fed through a package manager query to identify the most common package names

def findPackageManager():
    installedPackageManagerList = []
    packageManagers = ["dpkg", "brew", "yum", "gdebi", "apt-get", "pacman", "emerge", "zypper", "dnf", "rpm"]

    for pmgr in packageManagers:
        if checkToolLinux(pmgr):
            installedPackageManagerList.append(pmgr)
    return installedPackageManagerList
    
def setPackageMgrFlags(packageManager, packageName):
    # TODO: There should be some heirarchy for choosing between these depending on the detected OS. We could even
    # make this a configurable choice
    """
    Each package manager utilizes different strings, args, and flags for similar functions. Use the template below to add new ones:
        pmgrPrepend      = "sudo " # usually will be 'sudo', but not all distros include sudo. This variable is first in the concatinated command string
        pmgrInstallFlag = "-get install -y " # post-{pmgr} args and flags to induce an installation
        pmgrQueryLocal   = "-cache policy " # post-{pmgr} args and flags to query for an installed package
        pmgrRemoveFlag  = "-get remove " # post-{pmgr} args and flags to induce a Removal
        pmgrQueryAvail = "-get upgrade " # post-{pmgr} args and flags to induce an upgrade
        queryNotInstalled = " | grep -ic none" # end of line filtering. Output expects integer count of queries that return "not installed". 0 indicates the package 'is' installed
        getLocalVersion = " | grep -i Installed" # end of line filtering. Output expects a single token containing the version number of the currently installed version
        getAvailVersion = " | grep -i Candidate" # end of line filtering. Output expects a single token containing the version number of the available or updated version
    """
    pmgr = packageManager
    if pmgr == 'dpkg':
        pmgrPrepend      = "echo 'yes' | sudo "
        pmgrInstallFlag = "-i "
        pmgrQueryLocal   = "-l "
        pmgrRemoveFlag  = "-r "
        pmgrQueryAvail = "-I "
        queryNotInstalled = " | grep -ic 'no packagesfound\|error'"
        getLocalVersion = " | grep ii | awk '{print $3}'"
        getAvailVersion = " | grep -i version"
        return pmgrPrepend,pmgrInstallFlag,pmgrQueryLocal,pmgrRemoveFlag,pmgrQueryAvail,queryNotInstalled,getLocalVersion,getAvailVersion
    elif pmgr == 'apt-get' or 'apt':
        pmgrPrepend      = "sudo "
        pmgrInstallFlag = "-get install -y "
        pmgrQueryLocal   = "-cache policy "
        pmgrRemoveFlag  = "-get remove "
        pmgrQueryAvail = "-get upgrade "
        queryNotInstalled = " | grep -ic none"
        getLocalVersion = " | grep -i Installed"
        getAvailVersion = " | grep -i Candidate"
        return pmgrPrepend,pmgrInstallFlag,pmgrQueryLocal,pmgrRemoveFlag,pmgrQueryAvail,queryNotInstalled,getLocalVersion,getAvailVersion
    elif pmgr == 'gdebi':
        pmgrPrepend      = "sudo "
        pmgrInstallFlag = "--q --o install -y "
        pmgrQueryLocal   = ""
        pmgrRemoveFlag  = "--q --o remove -y "
        pmgrQueryAvail = ""
        queryNotInstalled = " | grep -ic none"
        getLocalVersion = " | grep -i Installed"
        getAvailVersion = " | grep -i Candidate"
        return pmgrPrepend,pmgrInstallFlag,pmgrQueryLocal,pmgrRemoveFlag,pmgrQueryAvail,queryNotInstalled,getLocalVersion,getAvailVersion
    elif pmgr == 'yum' or 'dnf':
        pmgrPrepend      = "sudo "
        pmgrInstallFlag = "install "
        pmgrQueryLocal   = "list "
        pmgrRemoveFlag  = "remove "
        pmgrQueryAvail   = "list available "
        queryNotInstalled = " | grep -ic \"no packages found\|error\""
        getLocalVersion = " | grep -i Installed"
        getAvailVersion = " | grep -i Candidate"
        return pmgrPrepend,pmgrInstallFlag,pmgrQueryLocal,pmgrRemoveFlag,pmgrQueryAvail,queryNotInstalled,getLocalVersion,getAvailVersion
    elif pmgr == 'pacman':
        pmgrPrepend      = "sudo "
        pmgrInstallFlag = "-S "
        pmgrQueryLocal   = "-Q "
        pmgrRemoveFlag  = "-R "
        pmgrQueryAvail   = "-Ss "
        queryNotInstalled = " | grep -ic none"
        getLocalVersion = " | awk '{print $2}'"
        getAvailVersion = " | grep '[^a-z]"+packageName+"' | head -n 1 | awk '{print $2}'"
        return pmgrPrepend,pmgrInstallFlag,pmgrQueryLocal,pmgrRemoveFlag,pmgrQueryAvail,queryNotInstalled,getLocalVersion,getAvailVersion

    # TODO: All package managers beyond this point need to be reworked to correctly function
    elif pmgr == 'rpm':
        pmgrPrepend      = "sudo "
        pmgrInstallFlag = "-i "
        pmgrQueryLocal   = "-q "
        pmgrRemoveFlag  = "-e "
        pmgrQueryAvail = ""
        queryNotInstalled = " | grep -ic none"
        getLocalVersion = " | grep -i Installed"
        getAvailVersion = " | grep -i Candidate"
        return pmgrPrepend,pmgrInstallFlag,pmgrQueryLocal,pmgrRemoveFlag,pmgrQueryAvail,queryNotInstalled,getLocalVersion,getAvailVersion
    elif pmgr == 'emerge':
        pmgrPrepend      = "sudo "
        pmgrInstallFlag = "-pv "
        pmgrQueryLocal   = "-l "
        pmgrRemoveFlag  = "-r "
        pmgrQueryAvail   = "-i "
        queryNotInstalled = " | grep -ic none"
        getLocalVersion = " | grep -i Installed"
        getAvailVersion = " | grep -i Candidate"
        return pmgrPrepend,pmgrInstallFlag,pmgrQueryLocal,pmgrRemoveFlag,pmgrQueryAvail,queryNotInstalled,getLocalVersion,getAvailVersion
    elif pmgr == 'zypper':
        pmgrPrepend      = "sudo "
        pmgrInstallFlag = "-i "
        pmgrQueryLocal   = "-l "
        pmgrRemoveFlag  = "-r "
        pmgrQueryAvail   = "-i "
        queryNotInstalled = " | grep -ic none"
        getLocalVersion = " | grep -i Installed"
        getAvailVersion = " | grep -i Candidate"
        return pmgrPrepend,pmgrInstallFlag,pmgrQueryLocal,pmgrRemoveFlag,pmgrQueryAvail,queryNotInstalled,getLocalVersion,getAvailVersion
    elif pmgr == 'brew':
        pmgrPrepend      = "sudo "
        pmgrInstallFlag = "install --cask "
        pmgrQueryLocal   = "list "
        pmgrRemoveFlag  = "uninstall "
        pmgrQueryAvail   = "list available "
        queryNotInstalled = " | grep -ic none"
        getLocalVersion = " | grep -i Installed"
        getAvailVersion = " | grep -i Candidate"
        return pmgrPrepend,pmgrInstallFlag,pmgrQueryLocal,pmgrRemoveFlag,pmgrQueryAvail,queryNotInstalled,getLocalVersion,getAvailVersion

# TODO: The four definitions below can be optimized into a single definition with a little effort. Will tackle this after it works
def packageInstall(packageName):
    pmgr = getPackageManagerCMD(packageName, findPackageManager())
    pmgrPrepend,pmgrInstallFlag,pmgrQueryLocal,pmgrRemoveFlag,pmgrQueryAvail,queryNotInstalled,getLocalVersion,getAvailVersion = setPackageMgrFlags(pmgr, packageName)
    cdlog(1, "Package Installing: "+packageName)
    if subprocess.call(f'{pmgrPrepend}{pmgr}{pmgrInstallFlag}{packageName}'+" > /dev/null 2>&1", shell=True) == 0:
        cdlog(1, "Package installed Successfully")
        return True
    else:
        cdErr("Unable to install package. \nPlease install manually : " + packageName)

def packageRemove(packageName):
    pmgr = getPackageManagerCMD(packageName, findPackageManager())
    pmgrPrepend,pmgrInstallFlag,pmgrQueryLocal,pmgrRemoveFlag,pmgrQueryAvail,queryNotInstalled,getLocalVersion,getAvailVersion = setPackageMgrFlags(pmgr, packageName)
    cdlog(1, "Package Removing: "+packageName)
    if subprocess.call(f'{pmgrPrepend}{pmgr}{pmgrRemoveFlag}{packageName}'+" > /dev/null 2>&1", shell=True) == 0:
        cdlog(1, "Package removed Successfully")
        return True
    else:
        cdErr("Unable to remove package. \nPlease remove manually : " + packageName)

def packageInstalled(packageName):
    pmgr = getPackageManagerCMD(packageName, findPackageManager())
    pmgrPrepend,pmgrInstallFlag,pmgrQueryLocal,pmgrRemoveFlag,pmgrQueryAvail,queryNotInstalled,getLocalVersion,getAvailVersion = setPackageMgrFlags(pmgr, packageName)
    cdlog(1, "Checking for installed Package: "+packageName)
    print("Package Query Command:")
    print(f'{pmgrPrepend}{pmgr}{pmgrQueryLocal}{packageName}')
    checkInstalled = subprocess.Popen(f'{pmgrPrepend}{pmgr}{pmgrQueryLocal}{packageName}{queryNotInstalled}', stdout=subprocess.PIPE, shell=True)
    _packageToCheck = int(checkInstalled.stdout.read())
    print("Package to check ")
    print(_packageToCheck)
    if _packageToCheck == 0:
        cdlog(1, "Package Is Currently Installed")
        _installedVersion = subprocess.Popen(f'{pmgrPrepend}{pmgr}{pmgrQueryLocal}{packageName}{getLocalVersion}', stdout=subprocess.PIPE, shell=True)
        installedVersion = str(_installedVersion.stdout.read()).split(" ")[-1].replace('\\n\'','')
        cdlog(1, "Installed Version: "+installedVersion)
        _candidateVersion = subprocess.Popen(f'{pmgrPrepend}{pmgr}{pmgrQueryLocal}{packageName}{getAvailVersion}', stdout=subprocess.PIPE, shell=True)
        candidateVersion = str(_candidateVersion.stdout.read()).split(" ")[-1].replace('\\n\'','')
        cdlog(1, "Candidate Version: "+candidateVersion)
        return True,installedVersion,candidateVersion
    else:
        cdlog(1, "Package Is NOT Currently Installed")
        _candidateVersion = subprocess.Popen(f'{pmgrPrepend}{pmgr}{pmgrQueryLocal}{packageName}{getAvailVersion}', stdout=subprocess.PIPE, shell=True)
        candidateVersion = str(_candidateVersion.stdout.read()).split(" ")[-1].replace('\\n\'','')
        cdlog(1, "Candidate Version: "+candidateVersion)
        return False,"(none)",candidateVersion

# Simple sorting algorithm for packages and package managers
def getPackageManagerCMD(packageName, installedPackageManagerList):
    packageManagers = list(installedPackageManagerList)
    packageExtension = packageName.split(".")[-1]
    for ipm in packageManagers:
        if ipm == 'gdebi' and packageExtension == 'deb':
            return "gdebi"
            # if packageInstall("gdebi", packageName):
            #     break
        elif ipm == 'dpkg' and packageExtension == 'deb':
            return "dpkg"
        elif ipm == 'rpm' and packageExtension == 'rpm':
            return "rpm"
        elif ipm == 'apt-get':
            return "apt"
        elif ipm == 'yum':
            return "yum"
        elif ipm == 'pacman':
            return "pacman"
        elif ipm == 'dnf':
            return "dnf"
        elif ipm == 'emerge':
            return "emerge"
        elif ipm == 'zypper':
            return "zypper"
        elif ipm == 'brew':
            return "brew"

def checkAndUpgradeOSPackageVersions(packageName):
    cdlog(1, f"Searching for package: {packageName}")
    currentlyInstalled,installedVersion,candidateVersion = packageInstalled(packageName)
    if currentlyInstalled == 'True':
        cdlog(1, f"Candidate Package available: {candidateVersion}")
        # Compare versions and apply updates only if needed
        if installedVersion or candidateVersion == '(none)':
            if installedVersion < candidateVersion:
                packageInstall(packageName)
            else:
                cdlog(1, f"Package already Installed: {packageName}")
    else:
        packageInstall(packageName)


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
    toolName = "pip3"
    downloadUrl = "https://bootstrap.pypa.io/get-pip.py"
    fileName = "get-pip.py"
    
    if platform == "linux" or platform == "linux2" or platform == "linux-gnu":
        if not checkToolLinux(toolName):
            checkAndUpgradeOSPackageVersions('python3-pip') # Install PIP3

    elif platform == "darwin":
        if not checkToolLinux(toolName):
            downloadFile(fileName, downloadUrl)
            os.system('python get-pip.py') # Install PIP3

    elif platform == "win32" or platform == "win64":
        if not checkToolWindows(toolName):
            downloadFile(fileName, downloadUrl)
            os.system('py get-pip.py') # Install PIP3
            