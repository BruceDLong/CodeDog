import subprocess
from pip._internal.utils.misc import get_installed_distributions as getPipList

def InstallPipModules():
    installedModulesList = {"%s==%s" % (i.key, i.version) for i in getPipList()}
    requiredModulesList = {'mutagen==1.45.1', 'gtts==2.2.3', 'pyproj==3.1.0'}
    modulesList = requiredModulesList.difference(installedModulesList)
    if modulesList:
        print("CodeDog must be used with Python Modules")
        for module in modulesList:
            print("     %s" % module)
        # ModulesList = " ".join(ModulesList)

        installationPermission = input("Do you want to install? [Y/n] ")
        if installationPermission.lower()=='y' or installationPermission.lower()=='yes':
            for module in modulesList:
                print("Installing collected packages: ", module)
                subprocess.check_call(['pip', 'install', '-q', module, '--disable-pip-version-check'])
        else:
            print("\n\nERROR: CodeDog must be used with python modules\n")
            for module in modulesList:
                print("     %s" % module)
            exit(1)