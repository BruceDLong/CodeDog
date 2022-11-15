#!/usr/bin/env python3
from depsResolve import checkToolLinux

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
            pmgr = "dpkg"
            pre = ""
            if commandType == "install":
                pre = "echo 'yes' | sudo "
                post = " -i "
            elif commandType == "queryLocalInstall":
                pre = "sudo "
                post = " -l "+packageName+" | grep -ic 'no packagesfound\|error'"
            elif commandType == "queryLocalVer":
                pre = "sudo "
                post = " -l "+packageName+" | grep ii"
            elif commandType == "remove":
                pre = "echo 'yes' | sudo "
                post  = " -r "
            elif commandType == "queryAvailVer":
                pre = "sudo "
                post = " -I "+packageName+" | grep -i version"
            pmgrCMD = pre+ipm+post
            break
        elif ipm == 'apt-get' or 'apt':
            pmgr = "apt"
            pre = "sudo "
            if commandType == "install":
                post = "-get install -y "+packageName
            elif commandType == "queryLocalInstall":
                post = "-cache policy "+packageName+" | grep -ic 'none\|Unable'"
            elif commandType == "queryLocalVersion":
                post = "-cache policy "+packageName+" | grep -i Installed | awk '{print $2}'"
            elif commandType == "remove":
                post  = "-get remove -y "+packageName
            elif commandType == "queryAvailVer":
                post = " list "+packageName+" 2>&1 | grep '^"+packageName+"\/' | head -n 1 | awk '{print $2}'"
            pmgrCMD = pre+pmgr+post
            break
        elif ipm == 'yum' or 'dnf':
            pmgr = ipm
            pre = "sudo "
            if commandType == "install":
                post = "-get install -y "
            elif commandType == "queryLocalInstall":
                post = "-cache policy "+packageName+"| grep -ic 'none\|Unable'"
            elif commandType == "queryLocalVersion":
                post = "-cache policy | grep -i Installed "
            elif commandType == "remove":
                post  = "-get remove -y"
            elif commandType == "queryAvailVer":
                post = "-I | grep -i version"
            pmgrCMD = pre+pmgr+post
            break
        elif ipm == 'pacman':
            pmgr = 'pacman'
            pre = "sudo "
            if commandType == "install":
                post = "-S --noconfirm "
            elif commandType == "queryLocalInstall":
                post = "-Ss | grep '\/"+packageName+"[^-]' | grep -ic 'installed'"
            elif commandType == "queryLocalVersion":
                post = "-Ss | grep '\/"+packageName+"[^-]' | grep -i Installed"
            elif commandType == "remove":
                post  = "-R --noconfirm "
            elif commandType == "queryAvailVer":
                post = "-Ss | grep '\/"+packageName+"[^-]' | awk '{print $2}'"
            pmgrCMD = pre+pmgr+post
            break
        # TODO: All package managers beyond this point need to be reworked to correctly function
        elif ipm == 'emerge':
            pmgr = "apt"
            pre = "sudo "
            if commandType == "install":
                post = "-get install -y "
            elif commandType == "queryLocalInstall":
                post = "-cache policy "+packageName+"| grep -ic 'none\|Unable'"
            elif commandType == "queryLocalVersion":
                post = "-cache policy | grep -i Installed "
            elif commandType == "remove":
                post  = "-get remove -y"
            elif commandType == "queryAvailVer":
                post = "-I | grep -i version"
            pmgrCMD = pre+pmgr+post
            break
        elif ipm == 'zypper':
            pmgr = "apt"
            pre = "sudo "
            if commandType == "install":
                post = "-get install -y "
            elif commandType == "queryLocalInstall":
                post = "-cache policy "+packageName+"| grep -ic 'none\|Unable'"
            elif commandType == "queryLocalVersion":
                post = "-cache policy | grep -i Installed "
            elif commandType == "remove":
                post  = "-get remove -y"
            elif commandType == "queryAvailVer":
                post = "-I | grep -i version"
            pmgrCMD = pre+pmgr+post
            break
        elif ipm == 'brew':
            pmgr = "apt"
            pre = "sudo "
            if commandType == "install":
                post = "-get install -y "+packageName
            elif commandType == "queryLocalInstall":
                post = "-cache policy "+packageName+"| grep -ic 'none\|Unable'"
            elif commandType == "queryLocalVersion":
                post = "-cache policy "+packageName+" | grep -i Installed "
            elif commandType == "remove":
                post  = "-get remove -y "+packageName
            elif commandType == "queryAvailVer":
                post = "-I "+packageName+" | grep '^"+packageName+" -"
            pmgrCMD = pre+pmgr+post
            break
        elif ipm == 'gdebi' and packageExtension == 'deb':
            pmgr = "apt"
            pre = "sudo "
            pCMD = pre+pmgr
            if commandType == "install":
                post = "-get install -y "+packageName
            elif commandType == "queryLocalInstall":
                post = "-cache policy "+packageName+"| grep -ic 'none\|Unable'"
            elif commandType == "queryLocalVersion":
                post = "-cache policy "+packageName+" | grep -i Installed "
            elif commandType == "remove":
                post  = "-get remove -y "+packageName
            elif commandType == "queryAvailVer":
                post = "-I "+packageName+" | grep -i version "
            pmgrCMD = pCMD+post
            break
    # Return the correct command
    return pmgrCMD
  