# builder.py
# import into codeDog.py and call from there
# args to build function: path, libraries etc
# get it to work with C++ or print error msg
import progSpec
import os
import subprocess


def LinuxBuilder(debugMode, minLangVersion, fileName, libFiles, buildName):
    buildStr = ''
    libStr = ''
    langStr = 'g++ '
    minLangStr = '-std=gnu++' + minLangVersion + ' '
    fileStr = fileName + '.cpp '
    outputFileStr = '-o ' + fileName 
    
    for libFile in libFiles:
        if libFile.startswith('pkg-config'):
            libStr += "`"
            libStr += libFile
            libStr += "`"
        else:
            libStr += libFile
        #print "libStr: " + libStr
    currentDirectory = currentWD = os.getcwd()
    #TODO check if above is typo
    workingDirectory = currentDirectory + "/" + buildName
    buildStr = langStr + debugMode + " " + minLangStr + fileStr + libStr + " " + outputFileStr
    return [workingDirectory, buildStr]

def SwingBuilder(debugMode, minLangVersion, fileName, libFiles, buildName):
    buildStr = ''
    libStr = ''
    langStr = 'javac '
    minLangStr = ''
    fileStr = fileName + '.java'
    outputFileStr = ''
    debugMode = ''
    
    for libFile in libFiles:
        libStr += libFile
        #print "libStr: " + libStr
    currentDirectory = currentWD = os.getcwd()
    #TODO check if above is typo
    workingDirectory = currentDirectory + "/" + buildName
    buildStr = langStr + debugMode + " " + minLangStr + fileStr + libStr + " " + outputFileStr
    return [workingDirectory, buildStr]
    
def AndroidBuilder(debugMode, minLangVersion, fileName, libFiles, buildName):
    buildStr = ''
    libStr = ''
    langStr = ''
    minLangStr = ''
    outputFileStr = ''
    debugMode = ''
    lang = "Java"
    platform = "Android"
    sourceFiles = []
    libs = []
    homePath = ""
    
    print 'Building for Android' 
    generateAndroid()
    compileAndroid()
    packageAndroid(fileName)
    signAndroid(fileName)
    zipalignAndroid(fileName)
    uploadAndroid(fileName)
    runAndroid(fileName)
    print 'Finished Building for Android'
    
#TODO: error handling
def runCMD(myCMD, myDir):
    print "        myCMD: ", myCMD
    #print "        myDir: ", myDir
    pipe = subprocess.Popen(myCMD, cwd=myDir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    if out:
        print "        Result: ",out
    if err:
        print "Error: ", err
        print "        myCMD: ", myCMD
    return [out, err]
        
def generateAndroid():
    print '    Generating R.java'
    outputDir = "-J gen/ "
    creatOutDir = "-m "
    pathToDrawablesAndLayouts = "-S res/ "
    pathToAndroidJar = '-I "$ANDROID_HOME/platforms/android-23/android.jar" '
    pathToManifest = "-M AndroidManifest.xml " 
    forceOverwrite = "-f "
    
    myCMD = 'aapt package ' + forceOverwrite + pathToManifest + pathToAndroidJar + pathToDrawablesAndLayouts + outputDir + creatOutDir 
    [out, err] = runCMD(myCMD, '.')
    #TODO: if error "The type ClassName cannot be found in source files" try clean then build
    
def compileAndroid():
    print '    Compiling with Jack toolchain'
    classpath = '--classpath "$ANDROID_HOME/platforms/android-23/android.jar" '
    importTag = ''
    outputTag = '--output-dex out/ src/ gen/ '
    jack = 'java -jar "$ANDROID_HOME/build-tools/24.0.2/jack.jar" '
    myCMD = jack + classpath + importTag + outputTag 
    [out, err] = runCMD(myCMD, '.')
    
def packageAndroid(fileName):
    print '    Packaging APK '
    outputDir = "-J gen/ "
    creatOutDir = "-m "
    pathToDrawablesAndLayouts = "-S res/ "
    pathToAndroidJar = '-I "$ANDROID_HOME/platforms/android-23/android.jar" '
    pathToManifest = "-M AndroidManifest.xml " 
    forceOverwrite = "-f "
    apkOutFile = '-F out/' + fileName +'.apk '
    
    myCMD = 'aapt package ' + forceOverwrite + pathToManifest + pathToAndroidJar + pathToDrawablesAndLayouts + apkOutFile
    [out, err] = runCMD(myCMD, '.')
    
        
    myCMD = 'aapt add ' + fileName + '.apk classes.dex'
    currentDirectory = os.getcwd()
    workingDirectory = currentDirectory + "/out"
    [out, err] = runCMD(myCMD, workingDirectory)
    
def signAndroid(fileName):
    print '    Signing APK'
    keystoreTag = '-keystore ~/.android/debug.keystore '
    keystorePassword = '-storepass android '
    keyPassword = '-keypass android '
    outFile = 'out/' + fileName +'.apk '
    keyAlias = 'androiddebugkey '
    
    myCMD = 'jarsigner -verbose ' + keystoreTag + keystorePassword + keyPassword + outFile + keyAlias 
    [out, err] = runCMD(myCMD, '.')
    
def zipalignAndroid(fileName):
    print '    Zipaligning APK'
    forceOverwrite = "-f "
    allignmentTag = '4 '
    inFile = 'out/' + fileName +'.apk  '
    outFile = 'out/' + fileName +'-aligned.apk '
    
    myCMD = 'zipalign ' + forceOverwrite + allignmentTag + inFile + outFile
    [out, err] = runCMD(myCMD, '.')
    
def uploadAndroid(fileName):
    print '    Uploading APK'
    replaceExistingApp = '-r '
    pathToAPK = 'out/' + fileName +'-aligned.apk'
    
    myCMD = 'adb install ' + replaceExistingApp + pathToAPK
    [out, err] = runCMD(myCMD, '.')
    
def runAndroid(fileName):
    print '    Running '
    
    
    myCMD = 'adb shell am start com.infomage.' + fileName +'/.MainActivity'
    [out, err] = runCMD(myCMD, '.')

    
def build(debugMode, minLangVersion, fileName, libFiles, buildName):
    if buildName == 'LinuxBuild':
        [workingDirectory, buildStr] = LinuxBuilder(debugMode, minLangVersion, fileName, libFiles, buildName)
    elif buildName == 'SwingBuild':
        [workingDirectory, buildStr] = SwingBuilder(debugMode, minLangVersion, fileName, libFiles, buildName)
    elif buildName == 'AndroidBuild':
        
        [workingDirectory, buildStr] = AndroidBuilder(debugMode, minLangVersion, fileName, libFiles, buildName)
        #                              AndroidBuilder(lang, platform, sourceFiles, libs, homePath, fileName )
    else: 
        print "Builer.py error: build string not generated for "+ buildName
        exit(2)
    
    print "buildStr: ", buildStr
    print "workingDirectory: ", workingDirectory
    pipe = subprocess.Popen(buildStr, cwd=workingDirectory, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    if out: print "Result: ",out
    if err: print "Error: ", err
    return 

