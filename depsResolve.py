#!/usr/bin/env python3
import subprocess

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
        if subprocess.call(["which", "pip3"], stdout=subprocess.PIPE, stderr=subprocess.PIPE) != 0:
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


    print("pyparsingmodule not found")
    if subprocess.call(["which", "pip3"], stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0:
        if subprocess.call(f'pip3 install pyparsing > /dev/null 2>&1', shell=True) == 0:
            print("Installed PyParsing Module")
    else:
        print("python3-pip is not currently installed")
        from environmentMngr import installPipPackage
        installPipPackage()
        subprocess.call(f'python3 -m pip install pyparsing > /dev/null 2>&1', shell=True)