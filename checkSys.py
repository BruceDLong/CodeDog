import subprocess
import pkg_resources
import os

def AddSystemPath():
    from sys import platform
    pathList = os.get_exec_path()
    codeDogPath = os.path.dirname(os.path.realpath(__file__))
    if codeDogPath in pathList: return
    # Research how to permanently set the path for Linux, Mac, Windows via python3
    if platform == "linux" or platform == "linux2":
        bashfile = os.path.join(os.path.expanduser('~'), '.bashrc')
        sytemflag = 0
        systemPath = 'PATH="$PATH:$HOME/devl/CodeDog"'
        with open(bashfile, 'r') as f:
            if systemPath in f.read():
                sytemflag = 1

        if not sytemflag:
            addPathPermission = input("Do you want to add CodeDog to the System Path? [Y/n] ")
            if addPathPermission.lower() == 'y' or addPathPermission.lower() == 'yes' or addPathPermission == '':
                with open(bashfile, 'a') as f:
                    f.write('\n%s\n' %systemPath)
            else:
                print("If you wish to add CodeDog to the system path manually, it is:\n    ", codeDogPath)

    elif platform == "darwin":
        sytemflag = 0
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

    elif platform == "win32" or platform == "win64":
        import sys
        sytemflag = 0
        import winreg as reg
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, 'Environment', 0, reg.KEY_ALL_ACCESS)
        try:
            value, _ = reg.QueryValueEx(key, 'PATH')
        except WindowsError:
            value = ''
        if 'CodeDog' in value:
            sytemflag = 1
        if not sytemflag:
            addPathPermission = input("Do you want to add CodeDog to the System Path? [Y/n] ")
            if addPathPermission.lower() == 'y' or addPathPermission.lower() == 'yes' or addPathPermission == '':
                codeDogPath = os.getcwd()
                value += ";" + codeDogPath + "\CodeDog;"
                reg.SetValueEx(key, 'PATH', 0, reg.REG_EXPAND_SZ, value)
                reg.CloseKey(key)
            else:
                print("If you wish to add CodeDog to the system path manually, it is:\n    ", codeDogPath)

def DownloadInstallPipModules(pipCMD):
    pipe = subprocess.Popen(pipCMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    decodedOut = bytes.decode(err)
    if err:
        print("\n\n", decodedOut)

def CheckPipModules(requiredMinimumModulesList):
    AddSystemPath()
    modulesList = []
    for moduleName in requiredMinimumModulesList:
        try:
            # version = importlib_metadata.version(moduleName)
            version = pkg_resources.get_distribution(moduleName).version
        except:
            modulesList.append("%s~=%s" % (moduleName, requiredMinimumModulesList[moduleName]))
        else:
            version = version.split(".")
            installedModuleVersion = float(".".join(version[:2]))
            moduleVersion = requiredMinimumModulesList[moduleName].split(".")
            requiredModuleVersion = float(".".join(moduleVersion[:2]))
            if installedModuleVersion < requiredModuleVersion:
                modulesList.append("%s==%s" % (moduleName, requiredMinimumModulesList[moduleName]))

    if modulesList:
        print("This program must be used with Python Modules")
        for module in modulesList:
            print("     %s" % module)

        installationPermission = input("Do you want to install? [Y/n] ")
        if installationPermission.lower() == 'y' or installationPermission.lower() == 'yes' or installationPermission == '':
            for module in modulesList:
                moduleBaseName = module[:module.find("==")]
                latestModule = module.replace('==','~=')
                print("\nInstalling package: ", moduleBaseName)
                pipCMD = 'pip3 install -q %s --disable-pip-version-check' % latestModule
                DownloadInstallPipModules(pipCMD)
        else:
            print("\n\nERROR: CodeDog must be used with python modules\n")
            for module in modulesList:
                print("     %s" % module)
            exit(1)
