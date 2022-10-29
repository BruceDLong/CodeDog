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

def setPackageMgrFlags(packageManager):
    # TODO: Set up arrays for multiple package managers [e.g. pkgMgr1Install(apt-get) mkgMgr2Install(gdebi)]
    # TODO: For now, Need to ensure only one match is made. I believe this will loop and select the last one returned. 
    # There should be some heirarchy for choosing between these depending on the detected OS. We could even
    # make this a user choice
    pm = {packageManager}
    if pm == 'dpkg':
        pmgrPrepend      = "echo 'yes' | sudo "
        pmgrInstallFlags = "-i"
        pmgrQueryFlags = "-l"
        pmgrRemoveFlags  = "-r"
        pmgrUpgradeFlags = "-i"
    elif pm == 'apt-get':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "install -y"
        # TODO: need to either create a separate workflow for apt-get/apt-cache or we need to use apt instead as the original binary does not have query function
        pmgrQueryFlags = "-l"
        pmgrRemoveFlags  = "remove"
        pmgrUpgradeFlags = "upgrade"
    elif pm == 'gdebi':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "--q --o install -y"
        pmgrQueryFlags = "-l"
        pmgrRemoveFlags  = "--q --o remove -y"
        pmgrUpgradeFlags = "--q --o upgrade -y"
    elif pm == 'rpm':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "-i"
        pmgrQueryFlags = "-q"
        pmgrRemoveFlags  = "-e"
        pmgrUpgradeFlags = "-U"
    elif pm == 'yum':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "install"
        pmgrQueryFlags = "check-update"
        pmgrRemoveFlags  = "remove"
        pmgrUpgradeFlags = "upgrade"
    elif pm == 'pacman':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "-S"
        pmgrQueryFlags = "-Q"
        pmgrRemoveFlags  = "-R"
        pmgrUpgradeFlags = "-U"
    elif pm == 'dnf':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "install"
        pmgrQueryFlags = "check"
        pmgrRemoveFlags  = "remove"
        pmgrUpgradeFlags = "upgrade"
    elif pm == 'emerge':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "-pv"
        # TODO: not familiar enough with this manager. leaving some junk strings for now
        pmgrQueryFlags = "-l"
        pmgrRemoveFlags  = "-r"
        pmgrUpgradeFlags = "-i"
    elif pm == 'zypper':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "-i"
        pmgrQueryFlags = "-l"
        pmgrRemoveFlags  = "-r"
        pmgrUpgradeFlags = "-i"
    elif pm == 'brew':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "install --cask"
        pmgrQueryFlags = "list"
        pmgrRemoveFlags  = "uninstall"
        pmgrUpgradeFlags = "upgrade"

    return pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags

def packageInstall(packageManager, packageName):
    pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags = setPackageMgrFlags({packageManager})
    cdlog(1, "Package Installing: "+packageName)
    if subprocess.call(f'{pmgrPrepend} {packageManager} {pmgrInstallFlags} {packageName}'+" > /dev/null 2>&1", shell=True) == 0:
        cdlog(1, "Package installed Successfully")
        return True
    else:
        cdErr("Unable to install package. \nPlease install manually : " + packageName)

def packageRemove(packageManager, packageName):
    pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags = setPackageMgrFlags({packageManager})
    cdlog(1, "Package Installing: "+packageName)
    if subprocess.call(f'{pmgrPrepend} {packageManager} {pmgrRemoveFlags} {packageName}'+" > /dev/null 2>&1", shell=True) == 0:
        cdlog(1, "Package removed Successfully")
        return True
    else:
        cdErr("Unable to remove package. \nPlease remove manually : " + packageName)

def packageInstalled(packageManager, packageName):
    pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags = setPackageMgrFlags({packageManager})
    cdlog(1, "Checking for installed Package: "+packageName)
    _packageToCheck = subprocess.call(f'{pmgrPrepend} {packageManager} {pmgrQueryFlags} {packageName}', shell=True)
    print("Package to check "+{_packageToCheck})
    _isPackageInstalled = subprocess.call(f'{pmgrPrepend} {packageManager} {pmgrQueryFlags} {packageName}'+" | grep -i installed", shell=True)
    print("is Package Installed "+ {_isPackageInstalled})
    _isPackageAvailable = subprocess.call(f'{pmgrPrepend} {packageManager} {pmgrQueryFlags} {packageName}'+" | grep -i candidate", shell=True)
    print ("is Package Available "+{_isPackageAvailable})
    installedVersion = _isPackageInstalled.read().split(" ")[-1].replace('\n','')
    print ("installed Version "+ {installedVersion})
    candidateVersion = _isPackageAvailable.read().split(" ")[-1].replace('\n','')
    print ("candidate Version "+ {candidateVersion})
    if _packageToCheck():
        cdlog(1, "Package Is Currently Installed")
        return True,installedVersion,candidateVersion
    else:
        cdlog(1, "Package Is NOT Currently Installed")
        return False,candidateVersion

def packageUpdate(packageManager, packageName):
    pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags = setPackageMgrFlags({packageManager})
    cdlog(1, "Package Updating: "+packageName)
    if subprocess.call(f'{pmgrPrepend} {packageManager} {pmgrUpgradeFlags} {packageName}'+" > /dev/null 2>&1", shell=True) == 0:
        cdlog(1, "Package updated Successfully")
        return True
    else:
        cdErr("Unable to update package. \nPlease try manually : " + packageName)

def getPackageManagerCMD(packageName, installedPackageManagerList):
    packageExtension = packageName.split(".")[-1]
    for ipm in installedPackageManagerList:
        if ipm == 'gdebi' and packageExtension == 'deb':
            return "gdebi"
            # if packageInstall("gdebi", packageName):
            #     break
        elif ipm == 'dpkg' and packageExtension == 'deb':
            return "dpkg"
        elif ipm == 'rpm' and packageExtension == 'rpm':
            return "rpm"
        elif ipm == 'apt-get':
            return "apt-get"
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
    pmgr = getPackageManagerCMD({packageName}, findPackageManager())
    # Uses a concatanated string from the package manager and flags, returns a boolean result for positive or negative [0|1]
    # installedPackage = os.popen(f'{pmgr} {pmgrQueryFlags} {packageName} > /dev/null 2>&1 ; echo -e $?')
    currentlyInstalled = packageInstalled({pmgr}, {packageName})
    # If 0 (detected as installed):
    if currentlyInstalled == 'True':
        # Pull base label for currently installed package version0
        #_installedPackage = packageInstalled.installedVersion({pmgr}, {packageName})
        # Pull base label for candidate installer version
        #_candidatePackage = packageInstalled.candidateVersion({pmgr}, {packageName})
        # Parse version number from base labels
        # installedVersion = _installedPackage.read().split(" ")[-1].replace('\n','')
        # candidateVersion = _candidatePackage.read().split(" ")[-1].replace('\n','')
        installedVersion = packageInstalled.installedVersion({pmgr}, {packageName})
        candidateVersion = packageInstalled.candidateVersion({pmgr}, {packageName})
        cdlog(1, f"Candidate Package available: {candidateVersion}")
        # Compare versions and apply updates only if needed
        if installedVersion or candidateVersion == '(none)':
            if installedVersion != candidateVersion:
                packageInstall(packageName, pmgr)
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
    toolName = "pip3"
    downloadUrl = "https://bootstrap.pypa.io/get-pip.py"
    fileName = "get-pip.py"
    
    if platform == "linux" or platform == "linux2" or platform == "linux-gnu":
        if not checkToolLinux(toolName):
            getPackageManagerCMD('python3-pip', findPackageManager()) # Install PIP3

    elif platform == "darwin":
        if not checkToolLinux(toolName):
            downloadFile(fileName, downloadUrl)
            os.system('python get-pip.py') # Install PIP3

    elif platform == "win32" or platform == "win64":
        if not checkToolWindows(toolName):
            downloadFile(fileName, downloadUrl)
            os.system('py get-pip.py') # Install PIP3
            