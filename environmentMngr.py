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
    pmgr = packageManager
    if pmgr == 'dpkg':
        pmgrPrepend      = "echo 'yes' | sudo "
        pmgrInstallFlags = "-i "
        pmgrQueryFlags   = "-l "
        pmgrRemoveFlags  = "-r "
        pmgrUpgradeFlags = "-i "
        queryNotInstalled = " | grep -ic 'no packagesfound\|error'"
        queryInstalled = " | grep ii | awk '{print $3}'"
        queryCandidate = "-I | grep -i version"
        return pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags,queryNotInstalled,queryInstalled,queryCandidate
    elif pmgr == 'apt-get' or 'apt':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "-get install -y "
        pmgrQueryFlags   = "-cache policy "
        pmgrRemoveFlags  = "-get remove "
        pmgrUpgradeFlags = "-get upgrade "
        queryNotInstalled = " | grep -ic none"
        queryInstalled = " | grep -i Installed"
        queryCandidate = " | grep -i Candidate"
        return pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags,queryNotInstalled,queryInstalled,queryCandidate
    elif pmgr == 'gdebi':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "--q --o install -y "
        pmgrQueryFlags   = ""
        pmgrRemoveFlags  = "--q --o remove -y "
        pmgrUpgradeFlags = "--q --o upgrade -y "
        queryNotInstalled = " | grep -ic none"
        queryInstalled = " | grep -i Installed"
        queryCandidate = " | grep -i Candidate"
        return pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags,queryNotInstalled,queryInstalled,queryCandidate
    elif pmgr == 'rpm':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "-i "
        pmgrQueryFlags   = "-q "
        pmgrRemoveFlags  = "-e "
        pmgrUpgradeFlags = "-U "
        queryNotInstalled = " | grep -ic none"
        queryInstalled = " | grep -i Installed"
        queryCandidate = " | grep -i Candidate"
        return pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags,queryNotInstalled,queryInstalled,queryCandidate
    elif pmgr == 'yum':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "install "
        pmgrQueryFlags   = "check-update "
        pmgrRemoveFlags  = "remove "
        pmgrUpgradeFlags = "upgrade "
        queryNotInstalled = " | grep -ic none"
        queryInstalled = " | grep -i Installed"
        queryCandidate = " | grep -i Candidate"
        return pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags,queryNotInstalled,queryInstalled,queryCandidate
    elif pmgr == 'pacman':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "-S "
        pmgrQueryFlags   = "-Q "
        pmgrRemoveFlags  = "-R "
        pmgrUpgradeFlags = "-U "
        queryNotInstalled = " | grep -ic none"
        queryInstalled = " | grep -i Installed"
        queryCandidate = " | grep -i Candidate"
        return pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags,queryNotInstalled,queryInstalled,queryCandidate
    elif pmgr == 'dnf':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "install "
        pmgrQueryFlags   = "check "
        pmgrRemoveFlags  = "remove "
        pmgrUpgradeFlags = "upgrade "
        queryNotInstalled = " | grep -ic none"
        queryInstalled = " | grep -i Installed"
        queryCandidate = " | grep -i Candidate"
        return pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags,queryNotInstalled,queryInstalled,queryCandidate
    elif pmgr == 'emerge':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "-pv "
        # TODO: not familiar enough with this manager. leaving some junk strings for now
        pmgrQueryFlags   = "-l "
        pmgrRemoveFlags  = "-r "
        pmgrUpgradeFlags = "-i "
        queryNotInstalled = " | grep -ic none"
        queryInstalled = " | grep -i Installed"
        queryCandidate = " | grep -i Candidate"
        return pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags,queryNotInstalled,queryInstalled,queryCandidate
    elif pmgr == 'zypper':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "-i "
        pmgrQueryFlags   = "-l "
        pmgrRemoveFlags  = "-r "
        pmgrUpgradeFlags = "-i "
        queryNotInstalled = " | grep -ic none"
        queryInstalled = " | grep -i Installed"
        queryCandidate = " | grep -i Candidate"
        return pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags,queryNotInstalled,queryInstalled,queryCandidate
    elif pmgr == 'brew':
        pmgrPrepend      = "sudo "
        pmgrInstallFlags = "install --cask "
        pmgrQueryFlags   = "list "
        pmgrRemoveFlags  = "uninstall "
        pmgrUpgradeFlags = "upgrade "
        queryNotInstalled = " | grep -ic none"
        queryInstalled = " | grep -i Installed"
        queryCandidate = " | grep -i Candidate"
        return pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags,queryNotInstalled,queryInstalled,queryCandidate

# TODO: The four definitions below can be optimized into a single definition with a little effort. Will tackle this after it works
def packageInstall(packageName):
    pmgr = getPackageManagerCMD(packageName, findPackageManager())
    pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags,queryNotInstalled,queryInstalled,queryCandidate = setPackageMgrFlags(pmgr)
    cdlog(1, "Package Installing: "+packageName)
    if subprocess.call(f'{pmgrPrepend}{pmgr}{pmgrInstallFlags}{packageName}'+" > /dev/null 2>&1", shell=True) == 0:
        cdlog(1, "Package installed Successfully")
        return True
    else:
        cdErr("Unable to install package. \nPlease install manually : " + packageName)

def packageRemove(packageName):
    pmgr = getPackageManagerCMD(packageName, findPackageManager())
    pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags,queryNotInstalled,queryInstalled,queryCandidate = setPackageMgrFlags(pmgr)
    cdlog(1, "Package Installing: "+packageName)
    if subprocess.call(f'{pmgrPrepend}{pmgr}{pmgrRemoveFlags}{packageName}'+" > /dev/null 2>&1", shell=True) == 0:
        cdlog(1, "Package removed Successfully")
        return True
    else:
        cdErr("Unable to remove package. \nPlease remove manually : " + packageName)

# TODO: This is broken at the moment
def packageInstalled(packageName):
    pmgr = getPackageManagerCMD(packageName, findPackageManager())
    pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags,queryNotInstalled,queryInstalled,queryCandidate = setPackageMgrFlags(pmgr)
    cdlog(1, "Checking for installed Package: "+packageName)
    # packageInstalled = os.popen(f'apt-cache policy {packageName} | grep Installed')
    # if packageInstalled.read():
    #     installedPackage = os.popen(f'apt-cache policy {packageName} | grep Installed')
    #     candidatePackage = os.popen(f'apt-cache policy {packageName} | grep Candidate')
    #     installedVersion = installedPackage.read().split(" ")[-1].replace('\n','')
    #     candidateVersion = candidatePackage.read().split(" ")[-1].replace('\n','')
    pkgCMD = ''
    print("Package Query Command:")
    print(f'{pmgrPrepend}{pmgr}{pmgrQueryFlags}{packageName}')
    checkInstalled = subprocess.Popen(f'{pmgrPrepend}{pmgr}{pmgrQueryFlags}{packageName}{queryNotInstalled}', stdout=subprocess.PIPE, shell=True)
    _packageToCheck = int(checkInstalled.stdout.read())
    print("Package to check ")
    print(_packageToCheck)
    if _packageToCheck == 0:
        cdlog(1, "Package Is Currently Installed")
        _installedVersion = subprocess.Popen(f'{pmgrPrepend}{pmgr}{pmgrQueryFlags}{packageName}{queryInstalled}', stdout=subprocess.PIPE, shell=True)
        installedVersion = str(_installedVersion.stdout.read()).split(" ")[-1].replace('\\n\'','')
        print("is Package Installed ")
        print(installedVersion)
        _candidateVersion = subprocess.Popen(f'{pmgrPrepend}{pmgr}{pmgrQueryFlags}{packageName}{queryCandidate}', stdout=subprocess.PIPE, shell=True)
        candidateVersion = str(_candidateVersion.stdout.read()).split(" ")[-1].replace('\\n\'','')
        print(candidateVersion)
        return True,installedVersion,candidateVersion
    else:
        cdlog(1, "Package Is NOT Currently Installed")
        _candidateVersion = subprocess.Popen(f'{pmgrPrepend}{pmgr}{pmgrQueryFlags}{packageName}{queryCandidate}', stdout=subprocess.PIPE, shell=True)
        candidateVersion = str(_candidateVersion.stdout.read()).split(" ")[-1].replace('\\n\'','')
        print("Available Package Version ")
        print(candidateVersion)
        return False,"(none)",candidateVersion

def packageUpdate(packageName):
    pmgr = getPackageManagerCMD(packageName, findPackageManager())
    pmgrPrepend,pmgrInstallFlags,pmgrQueryFlags,pmgrRemoveFlags,pmgrUpgradeFlags,queryNotInstalled,queryInstalled,queryCandidate = setPackageMgrFlags(pmgr)
    cdlog(1, "Package Updating: "+packageName)
    if subprocess.call(f'{pmgrPrepend}{pmgr}{pmgrUpgradeFlags}{packageName}'+" > /dev/null 2>&1", shell=True) == 0:
        cdlog(1, "Package updated Successfully")
        return True
    else:
        cdErr("Unable to update package. \nPlease try manually : " + packageName)

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
    # Choose a package manager from those installed, after applying logic based on extension type
    # Depreciated, after migrating this to each pmgr function
    # pmgr = getPackageManagerCMD(packageName, findPackageManager())
    # Uses a concatanated string from the package manager and flags, returns a boolean result for positive or negative [0|1]
    # installedPackage = os.popen(f'{pmgr} {pmgrQueryFlags} {packageName} > /dev/null 2>&1 ; echo -e $?')
    currentlyInstalled,installedVersion,candidateVersion = packageInstalled(packageName)
    # If 0 (detected as installed):
    if currentlyInstalled == 'True':
        # Pull base label for currently installed package version0
        #_installedPackage = packageInstalled.installedVersion({pmgr}, {packageName})
        # Pull base label for candidate installer version
        #_candidatePackage = packageInstalled.candidateVersion({pmgr}, {packageName})
        # Parse version number from base labels
        # installedVersion = _installedPackage.read().split(" ")[-1].replace('\n','')
        # candidateVersion = _candidatePackage.read().split(" ")[-1].replace('\n','')
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
            getPackageManagerCMD('python3-pip', findPackageManager()) # Install PIP3

    elif platform == "darwin":
        if not checkToolLinux(toolName):
            downloadFile(fileName, downloadUrl)
            os.system('python get-pip.py') # Install PIP3

    elif platform == "win32" or platform == "win64":
        if not checkToolWindows(toolName):
            downloadFile(fileName, downloadUrl)
            os.system('py get-pip.py') # Install PIP3
            