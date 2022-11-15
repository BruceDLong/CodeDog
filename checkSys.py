import subprocess
import os
from environmentMngr import checkAndUpgradeOSPackageVersions
from environmentMngr import downloadFile

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

