#!/usr/bin/env python3
import subprocess
import os
import sys
from pmgrHandler import findPackageManager

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

def downloadFile(fileName, downloadURL):
    import urllib3
    try:
        #cdlog(1, "Downloading file: " + fileName)
        print("Downloading file: " + fileName)
        http = urllib3.PoolManager()
        r = http.request('GET', downloadURL, preload_content=False)
    except:
        #cdErr("URL not found: " + downloadURL)
        print("URL not found:" + downloadURL)
    else:
        with open(fileName, 'wb') as out:
            while True:
                data = r.read(1028)
                if not data:
                    break
                out.write(data)
        r.release_conn()

def packageInstall(packageName):
    from pmgrHandler import getPackageManagerCMD
    pmgrCMD = getPackageManagerCMD(packageName, findPackageManager(),"install")
    #cdlog(1, "Package Installing: "+packageName)
    print("Package Installing: "+packageName)
    if subprocess.call(f'{pmgrCMD}'+" > /dev/null 2>&1", shell=True) == 0:
        print("Package installed Successfully")
        return True
    else:
        print("Unable to install package. \nPlease install manually : " + packageName)

def installPipPackage():
    from sys import platform
    
    toolName = "pip3"
    downloadUrl = "https://bootstrap.pypa.io/get-pip.py"
    fileName = "get-pip.py"
    
    if platform == "linux" or platform == "linux2" or platform == "linux-gnu":
        if subprocess.call(["which", "pip3"], stdout=subprocess.PIPE, stderr=subprocess.PIPE) != 0:
            packageInstall('python3-pip') # Install PIP3
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

def installPyparsing():
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyparsing"])
    
        
