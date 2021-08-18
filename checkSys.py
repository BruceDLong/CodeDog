import subprocess
import pkg_resources
import os

def AddSystemPath():
    pathList = os.get_exec_path()
    codeDogPath = os.path.dirname(os.path.realpath(__file__))
    if codeDogPath in pathList: return
    addPathPermission = input("Do you want to add CodeDog to the System Path? [Y/n] ")
    if addPathPermission.lower() == 'y' or addPathPermission.lower() == 'yes' or addPathPermission == '':
        # Research how to permanently set the path for Linux, Mac, Windows via python3
        pass
    else:
        print("If you wish to add CodeDog to the system path manually, it is:\n    ", codeDogPath)

def DownloadInstallPipModules(pipCMD):
    pipe = subprocess.Popen(pipCMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    decodedOut = bytes.decode(err)
    if err:
        print("\n\n", decodedOut)

def CheckPipModules():
    AddSystemPath()
    requiredMinimumModulesList = {'pyparsing':'2.4.6', 'GitPython':'3.1.18', 'pycurl':'7'}
    modulesList = []
    for moduleName in requiredMinimumModulesList:
        try:
            # version = importlib_metadata.version(moduleName)
            version = pkg_resources.get_distribution(moduleName).version
        except:
            modulesList.append("%s==%s" % (moduleName, requiredMinimumModulesList[moduleName]))
        else:
            version = version.split(".")
            installedModuleVersion = float(".".join(version[:2]))
            moduleVersion = requiredMinimumModulesList[moduleName].split(".")
            requiredModuleVersion = float(".".join(moduleVersion[:2]))
            if installedModuleVersion < requiredModuleVersion:
                modulesList.append("%s==%s" % (moduleName, requiredMinimumModulesList[moduleName]))

    if modulesList:
        print("CodeDog must be used with Python Modules")
        for module in modulesList:
            print("     %s" % module)

        installationPermission = input("Do you want to install? [Y/n] ")
        if installationPermission.lower() == 'y' or installationPermission.lower() == 'yes' or installationPermission == '':
            for module in modulesList:
                moduleBaseName = module[:module.find("==")]
                print("\nInstalling package: ", moduleBaseName)
                pipCMD = 'pip3 install -q %s --disable-pip-version-check' % moduleBaseName
                DownloadInstallPipModules(pipCMD)
        else:
            print("\n\nERROR: CodeDog must be used with python modules\n")
            for module in modulesList:
                print("     %s" % module)
            exit(1)
