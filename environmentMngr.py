import os
import subprocess
from progSpec import cdlog, cdErr

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
        installedVersion = str(_installedVersion.stdout.read()).split(" ")[-0].replace('\\n\'','').replace('b\'','')
        cdlog(1, "Installed Version: "+installedVersion)
        pmgrCMD = getPackageManagerCMD(packageName,findPackageManager(),"queryAvailVer")
        _candidateVersion = subprocess.Popen(f'{pmgrCMD}', stdout=subprocess.PIPE, shell=True)
        candidateVersion = str(_candidateVersion.stdout.read()).split("-")[-0].replace('\\n\'','').replace('b\'','')
        cdlog(1, "Candidate Version: "+candidateVersion)
        return True,installedVersion,candidateVersion
    else:
        cdlog(1, "Package Is NOT Currently Installed")
        pmgrCMD = getPackageManagerCMD(packageName,findPackageManager(),"queryAvailVer")
        _candidateVersion = subprocess.Popen(f'{pmgrCMD}', stdout=subprocess.PIPE, shell=True)
        candidateVersion = str(_candidateVersion.stdout.read()).split("-")[-0].replace('\\n\'','').replace('b\'','')
        cdlog(1, "Candidate Version: "+candidateVersion)
        return False,"(none)",candidateVersion

def checkAndUpgradeOSPackageVersions(packageName):
    cdlog(1, f"Searching for package: {packageName}")
    currentlyInstalled,installedVersion,candidateVersion = checkPackageStatus(packageName)
    if currentlyInstalled == False:
        cdlog(1, f"Candidate Package available: {candidateVersion}")
        packageInstall(packageName)
    elif currentlyInstalled == True:
        cdlog(1, f"Candidate Package available: {candidateVersion}")
        # Compare versions and apply updates only if needed
        if installedVersion < candidateVersion:
            packageInstall(packageName)
        else:
            cdlog(1, f"Package already Installed: {packageName}")

def downloadFile(fileName, downloadURL):
    CheckPipModules({'urllib3':'1.25'})
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

def DownloadInstallPipModules(pipCMD):
    # Start a sub-process to run pip and a communications pipe to capture stdout and errors for display
    pipe = subprocess.Popen(pipCMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    decodedOut = bytes.decode(err)
    if err:
        print("\n\n", decodedOut)

def CheckPipModules(requiredMinimumModulesList):
    try:
        import pkg_resources
    except ModuleNotFoundError:
        DownloadInstallPipModules("pip3 install -q %s --disable-pip-version-check pkg_resources")
    
    try:
        import pyparsing
    except ModuleNotFoundError:
        DownloadInstallPipModules("pip3 install -q %s --disable-pip-version-check pyparsing")
    # Check environment first
    AddSystemPath()
    # Initialize array of modules
    modulesList = []
    # Iterate through list of modules 
    for moduleName in requiredMinimumModulesList:
        
        try:
            # Check available package versions
            # version = importlib_metadata.version(moduleName)
            version = pkg_resources.get_distribution(moduleName).version
        except:
            # Add each module that string matches from requiredMinimumModulesList with the avoilable packages to the modulesList array
            # Each string match is a module that is on the required list and also available from distributions
            modulesList.append("%s~=%s" % (moduleName, requiredMinimumModulesList[moduleName]))
        else:
            # If unmatched...
            # Initialize a splitting function
            version = version.split(".")
            # Parse version currently installed
            installedModuleVersion = float(".".join(version[:2]))
            # Load package name from module list
            moduleVersion = requiredMinimumModulesList[moduleName].split(".")
            # Parse required package version
            requiredModuleVersion = float(".".join(moduleVersion[:2]))
            # Compare required to installed
            if installedModuleVersion < requiredModuleVersion:
                modulesList.append("%s==%s" % (moduleName, requiredMinimumModulesList[moduleName]))

    # For any modules required and available
    if modulesList:
        print("This program must be used with Python Modules")
        # Iterate through list of modules and print list
        for module in modulesList:
            print("     %s" % module)

        # Request permissions to install from user
        installationPermission = input("Do you want to install? [Y/n] ")
        if installationPermission.lower() == 'y' or installationPermission.lower() == 'yes' or installationPermission == '':
            # If user accepts, Iterate through modules:
            for module in modulesList:
                # set the module base name (omitting versions)
                moduleBaseName = module[:module.find("==")]
                # Parse the module's latest version
                latestModule = module.replace('==','~=')
                print("\nInstalling package: ", moduleBaseName)
                # send module installation to pip via subprocess
                pipCMD = 'pip3 install -q %s --disable-pip-version-check' % latestModule
                DownloadInstallPipModules(pipCMD)
        else:
            # If user declines:
            print("\n\nERROR: CodeDog must be used with python modules\n")
            # Iterate and list required modules
            for module in modulesList:
                print("     %s" % module)
            exit(1)
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

def installPipPackage():
    from sys import platform
    toolName = "pip3"
    downloadUrl = "https://bootstrap.pypa.io/get-pip.py"
    fileName = "get-pip.py"
    
    if platform == "linux" or platform == "linux2" or platform == "linux-gnu":
        if not checkToolLinux(toolName):
            checkAndUpgradeOSPackageVersions('python3-pip') # Install PIP3
        # If package manager fails to install, try using the bootstrap script
        if not checkToolLinux(toolName):
            downloadFile(fileName, downloadUrl)
            os.system('python3 get-pip.py') # Install PIP3

    elif platform == "darwin":
        if not checkToolLinux(toolName):
            downloadFile(fileName, downloadUrl)
            os.system('python get-pip.py') # Install PIP3

    elif platform == "win32" or platform == "win64":
        if not checkToolWindows(toolName):
            downloadFile(fileName, downloadUrl)
            os.system('py get-pip.py') # Install PIP3

def AddSystemPath():
    from sys import platform
    # load system PATH environment variable from OS
    pathList = os.get_exec_path()
    # Detect current script path
    codeDogPath = os.path.dirname(os.path.realpath(__file__))
    # If current location is found in the system path, return true
    if codeDogPath in pathList: return
    # TODO: Research how to permanently set the path for Linux, Mac, Windows via python3
    # If a linux or gnu-like terminal is detected (cygwin and msys are bash ports for Windows)
    if platform == "linux" or platform == "linux2" or platform == "linux-gnu" or platform == "cygwin" or platform == "msys":
        # most linux bash environments utilize ~/.bashrc for user-specific environment config
        bashfile = os.path.join(os.path.expanduser('~'), '.bashrc')
        # reset flag to detect whether CodeDog is already on system PATH
        sytemflag = 0
        # bashrc string for setting up codedog env
        systemPath = 'PATH="$PATH:$HOME/devl/CodeDog"'
        # Parse bashfile and match for exsting string
        with open(bashfile, 'r') as f:
            if systemPath in f.read():
                # If match is positive, set systemflag 1 (installed)
                sytemflag = 1
        # If parse finds no match (systemflag = 0), ask the user if they want to add it
        if not sytemflag:
            # Ask user to add to system path or not
            addPathPermission = input("Do you want to add CodeDog to the System Path? [Y/n] ")
            if addPathPermission.lower() == 'y' or addPathPermission.lower() == 'yes' or addPathPermission == '':
                # If yes, open and write to system bashrc
                with open(bashfile, 'a') as f:
                    f.write('\n%s\n' %systemPath)
            else:
                # Offer manual instructions for adding system PATH to user
                print("If you wish to add CodeDog to the system path manually, it is:\n    ", codeDogPath)

    # If platform detected is MacOS
    elif platform == "darwin":
        # reset flag to detect whether CodeDog is already on system PATH
        sytemflag = 0
        # macOS shell environments utilize ~/.zshrc for user-specific environment config
        zshrcfile = os.path.join(os.path.expanduser('~'), '.zshrc')
        systemPath = 'export PATH="$PATH:$HOME/devl/CodeDog"'
        with open(zshrcfile, 'a+') as f:
            if systemPath in f.read():
                sytemflag = 1

        if not sytemflag:
            addPathPermission = input("Do you want to add CodeDog to the System Path? [Y/n] ")
            if addPathPermission.lower() == 'y' or addPathPermission.lower() == 'yes' or addPathPermission == '':
                with open(zshrcfile, 'a+') as f:
                    f.write('\n%s\n' %systemPath)
            else:
                print("If you wish to add CodeDog to the system path manually, it is:\n    ", codeDogPath)

    # If platform detected is Windows
    elif platform == "win32" or platform == "win64":
        import sys
        sytemflag = 0
        # load library for handling windows registry files
        import winreg as reg
        # Set up alias for querying windows registry for Environment Variables
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, 'Environment', 0, reg.KEY_ALL_ACCESS)
        # Query keys for the system's PATH
        try:
            value, _ = reg.QueryValueEx(key, 'PATH')
        except WindowsError:
            value = ''
        # If CodeDog is detected in the path, set systemflag = 1 (installed)
        if 'CodeDog' in value:
            sytemflag = 1
        # If parse finds no match (systemflag = 0), ask the user if they want to CodeDog to the system path 
        if not sytemflag:
            addPathPermission = input("Do you want to add CodeDog to the System Path? [Y/n] ")
            if addPathPermission.lower() == 'y' or addPathPermission.lower() == 'yes' or addPathPermission == '':
                codeDogPath = os.getcwd()
                value += ";" + codeDogPath + "\CodeDog;"
                reg.SetValueEx(key, 'PATH', 0, reg.REG_EXPAND_SZ, value)
                reg.CloseKey(key)
            else:
                print("If you wish to add CodeDog to the system path manually, it is:\n    ", codeDogPath)
