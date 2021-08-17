import subprocess
import pkg_resources
# import importlib_metadata

def DownloadInstallPipModules(pipCMD):
    pipe = subprocess.Popen(pipCMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    decodedOut = bytes.decode(err)
    if err:
        print("\n\n", decodedOut)

def CheckPipModules():
    requiredMinimumModulesList = {'pyparsing':'3.0.0b2', 'GitPython':'3.1.18', 'scons':'4.2.0', 'pycurl':'7.43.0.6'}
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
            if not installedModuleVersion >= requiredModuleVersion:
                modulesList.append("%s==%s" % (moduleName, requiredMinimumModulesList[moduleName]))

    if modulesList:
        print("CodeDog must be used with Python Modules")
        for module in modulesList:
            print("     %s" % module)

        installationPermission = input("Do you want to install? [Y/n] ")
        if installationPermission.lower() == 'y' or installationPermission.lower() == 'yes':
            for module in modulesList:
                print("\nInstalling collected packages: ", module)
                pipCMD = 'pip install -q %s --disable-pip-version-check' % module
                DownloadInstallPipModules(pipCMD)

        else:
            print("\n\nERROR: CodeDog must be used with python modules\n")
            for module in modulesList:
                print("     %s" % module)
            exit(1)

def AddSystemPath():
    addPathPermission = input("Do you want to add CodeDog to System Path? [Y/n] ")
    if addPathPermission.lower() == 'y' or addPathPermission.lower() == 'yes':
        pass
