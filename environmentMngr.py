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

# Simple sorting algorithm for packages and package managers
def getPackageManagerCMD(packageName, installedPackageManagerList, commandType):
    packageManagers = list(installedPackageManagerList)
    packageExtension = packageName.split(".")[-1]
    pmgrCMD = ''
    pre = ''
    post = ''
    for ipm in packageManagers:
        if ipm == 'dpkg' and packageExtension == 'deb':

            pmgr = ipm
            pre = "echo 'yes' | sudo "
            if commandType == "install":
                post = "-i "
                return post
            elif commandType == "queryLocalInstall":
                post = "-l  | grep -ic 'no packagesfound\|error'"
                return post
            elif commandType == "queryLocalVer":
                post = "-l | grep ii"
                return post
            elif commandType == "remove":
                post  = "-r "
                return post
            elif commandType == "queryAvailVer":
                post = "-I | grep -i version"
                return post
            pmgrCMD = pre+ipm+post
            
        elif ipm == 'apt-get' or 'apt':
            pmgr = ipm
            pre = "sudo "
            if commandType == "install":
                post = "-get install -y "
                return post
            elif commandType == "queryLocalInstall":
                post = "-cache policy "+packageName+"| grep -ic 'none\|Unable'"
                return post
            elif commandType == "queryLocalVersion":
                post = "-cache policy | grep -i Installed "
                return post
            elif commandType == "remove":
                post  = "-get remove -y"
                return post
            elif commandType == "queryAvail":
                post = "-I | grep -i version"
                return post
            pmgrCMD = pre+pmgr+post

        elif ipm == 'yum' or 'dnf':
            pmgrCMD = ''
            post = ''
            pmgr = ipm
            pre = "sudo "
            if commandType == "install":
                post = "-get install -y "
                return post
            elif commandType == "queryLocalInstall":
                post = "-cache policy "+packageName+"| grep -ic 'none\|Unable'"
                return post
            elif commandType == "queryLocalVersion":
                post = "-cache policy | grep -i Installed "
                return post
            elif commandType == "remove":
                post  = "-get remove -y"
                return post
            elif commandType == "queryAvail":
                post = "-I | grep -i version"
                return post
            pmgrCMD = pre+pmgr+post
            
        elif ipm == 'pacman':
            pmgr = ipm
            pre = "sudo "
            if commandType == "install":
                post = "-S --noconfirm "
                return post
            elif commandType == "queryLocalInstall":
                post = "-Ss | grep '\/"+packageName+"[^-]' | grep -ic 'installed'"
                return post
            elif commandType == "queryLocalVersion":
                post = "-Ss | grep '\/"+packageName+"[^-]' | grep -i Installed"
                return post
            elif commandType == "remove":
                post  = "-R --noconfirm "
                return post
            elif commandType == "queryAvail":
                post = "-Ss | grep '\/"+packageName+"[^-]' | awk '{print $2}'"
                return post
            pmgrCMD = pre+pmgr+post
            
# TODO: All package managers beyond this point need to be reworked to correctly function
        elif ipm == 'emerge':
            pmgr = "apt"
            pre = "sudo "
            if commandType == "install":
                post = "-get install -y "
                return post
            elif commandType == "queryLocalInstall":
                post = "-cache policy "+packageName+"| grep -ic 'none\|Unable'"
                return post
            elif commandType == "queryLocalVersion":
                post = "-cache policy | grep -i Installed "
                return post
            elif commandType == "remove":
                post  = "-get remove -y"
                return post
            elif commandType == "queryAvail":
                post = "-I | grep -i version"
                return post
            pmgrCMD = pre+pmgr+post
            
        elif ipm == 'zypper':
            pmgr = "apt"
            pre = "sudo "
            if commandType == "install":
                post = "-get install -y "
                return post
            elif commandType == "queryLocalInstall":
                post = "-cache policy "+packageName+"| grep -ic 'none\|Unable'"
                return post
            elif commandType == "queryLocalVersion":
                post = "-cache policy | grep -i Installed "
                return post
            elif commandType == "remove":
                post  = "-get remove -y"
                return post
            elif commandType == "queryAvail":
                post = "-I | grep -i version"
                return post
            pmgrCMD = pre+pmgr+post
            
        elif ipm == 'brew':
            pmgr = "apt"
            pre = "sudo "
            if commandType == "install":
                post = "-get install -y "
                return post
            elif commandType == "queryLocalInstall":
                post = "-cache policy "+packageName+"| grep -ic 'none\|Unable'"
                return post
            elif commandType == "queryLocalVersion":
                post = "-cache policy | grep -i Installed "
                return post
            elif commandType == "remove":
                post  = "-get remove -y"
                return post
            elif commandType == "queryAvail":
                post = "-I | grep -i version"
                return post
            pmgrCMD = pre+pmgr+post
        
        elif ipm == 'gdebi' and packageExtension == 'deb':
            pmgr = "apt"
            pre = "sudo "
            if commandType == "install":
                post = "-get install -y "
                return post
            elif commandType == "queryLocalInstall":
                post = "-cache policy "+packageName+"| grep -ic 'none\|Unable'"
                return post
            elif commandType == "queryLocalVersion":
                post = "-cache policy | grep -i Installed "
                return post
            elif commandType == "remove":
                post  = "-get remove -y"
                return post
            elif commandType == "queryAvail":
                post = "-I | grep -i version"
                return post
            pmgrCMD = pre+pmgr+post
        # Return the correct command    
        return pmgrCMD

# TODO: The four definitions below can be optimized into a single definition with a little effort. Will tackle this after it works
def packageInstall(packageName):
    pmgrCMD = getPackageManagerCMD(packageName, findPackageManager(),"install")
    cdlog(1, "Package Installing: "+packageName)
    if subprocess.call(f'{pmgrCMD}'+" > /dev/null 2>&1", shell=True) == 0:
        cdlog(1, "Package installed Successfully")
        return True
    else:
        cdErr("Unable to install package. \nPlease install manually : " + packageName)

def packageRemove(packageName):
    pmgrCMD = getPackageManagerCMD(packageName, findPackageManager(),"remove")
    cdlog(1, "Package Removing: "+packageName)
    if subprocess.call(f'{pmgrCMD}'+" > /dev/null 2>&1", shell=True) == 0:
        cdlog(1, "Package removed Successfully")
        return True
    else:
        cdErr("Unable to remove package. \nPlease remove manually : " + packageName)

def checkPackageStatus(packageName):
    # pmgr = getPackageManagerCMD(packageName, findPackageManager())
    # pmgrPrepend,pmgrInstallFlag,pmgrQueryLocal,pmgrRemoveFlag,pmgrQueryAvail,queryNotInstalled,getLocalVersion,getAvailVersion = setPackageMgrFlags(pmgr, packageName)
    cdlog(1, "Checking for installed Package: "+packageName)
    pmgrCMD = getPackageManagerCMD(packageName,findPackageManager(),"queryLocalInstall")
    checkInstalled = subprocess.Popen(f'{pmgrCMD}', stdout=subprocess.PIPE, shell=True)
    _packageToCheck = int(checkInstalled.stdout.read())
    if _packageToCheck == 0:
        cdlog(1, "Package Is Currently Installed")
        pmgrCMD = getPackageManagerCMD(packageName,findPackageManager(),"queryLocalVer")
        _installedVersion = subprocess.Popen(f'{pmgrCMD}', stdout=subprocess.PIPE, shell=True)
        installedVersion = str(_installedVersion.stdout.read()).split(" ")[-1].replace('\\n\'','')
        cdlog(1, "Installed Version: "+installedVersion)
        pmgrCMD = getPackageManagerCMD(packageName,findPackageManager(),"queryAvailVer")
        _candidateVersion = subprocess.Popen(f'{pmgrCMD}', stdout=subprocess.PIPE, shell=True)
        candidateVersion = str(_candidateVersion.stdout.read()).split(" ")[-1].replace('\\n\'','')
        cdlog(1, "Candidate Version: "+candidateVersion)
        return True,installedVersion,candidateVersion
    else:
        cdlog(1, "Package Is NOT Currently Installed")
        pmgrCMD = getPackageManagerCMD(packageName,findPackageManager(),"queryAvailVer")
        _candidateVersion = subprocess.Popen(f'{pmgrCMD}', stdout=subprocess.PIPE, shell=True)
        candidateVersion = str(_candidateVersion.stdout.read()).split(" ")[-1].replace('\\n\'','')
        cdlog(1, "Candidate Version: "+candidateVersion)
        return False,"(none)",candidateVersion

def checkAndUpgradeOSPackageVersions(packageName):
    cdlog(1, f"Searching for package: {packageName}")
    currentlyInstalled,installedVersion,candidateVersion = checkPackageStatus(packageName)
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
            