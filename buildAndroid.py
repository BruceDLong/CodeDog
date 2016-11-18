# buildAndroid.py

import os
import subprocess
import errno

def writeFile(path, fileName, outStr, fileExtension):
    print path 
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST: raise
    fileName += fileExtension
    fo=open(path + os.sep + fileName, 'w')
    fo.write(outStr)
    fo.close()

def runCMD(myCMD, myDir):
    #print "        myCMD: ", myCMD
    #print "        myDir: ", myDir
    pipe = subprocess.Popen(myCMD, cwd=myDir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    if out:
        print "        Result: ",out
    if err:
        print "Error: ", err
        print "        myCMD: ", myCMD
        exit(1)
    return [out, err]

def makeDir(dirToGen):
    print dirToGen
    try:
        os.makedirs(dirToGen)
    except OSError as exception:
        if exception.errno != errno.EEXIST: raise

def pathAndroid(appPaths, workingDirectory):
    print '    Generating folder structure'
    dirsToGen = [workingDirectory, workingDirectory + "/gen", workingDirectory + "/lib", workingDirectory + "/out", workingDirectory + "/res", workingDirectory + "/res/drawable-xhdpi", workingDirectory + "/res/layout", workingDirectory + "/src" ]
    for path in appPaths:
        path = workingDirectory + path
        print path
        dirsToGen.append(path )
        
    for dirToGen in dirsToGen:
        makeDir(dirToGen)

def androidManifest(appName, workingDirectory):
    manifestName = "AndroidManifest.xml"
    
    outStr = '<?xml version="1.0" encoding="utf-8"?>' \
            '<manifest xmlns:android="http://schemas.android.com/apk/res/android"' \
            '    package="com.infomage.' + appName + '">' \
            '    <application android:label="' + appName + '">' \
            '        <activity android:name="MainActivity">' \
            '            <intent-filter>' \
            '                <action android:name="android.intent.action.MAIN" />' +\
            '                <category android:name="android.intent.category.LAUNCHER" />' \
            '            </intent-filter>' \
            '        </activity>' \
            '    </application>' \
            '</manifest>' \
    
    fo=open(workingDirectory + os.sep + manifestName, 'w')
    fo.write(outStr)
    fo.close()

def generateAndroid(workingDirectory):
    print '    Generating R.java'
    outputDir = "-J gen/ "
    creatOutDir = "-m "
    pathToDrawablesAndLayouts = "-S " + workingDirectory + "/res/ "
    pathToAndroidJar = '-I "$ANDROID_HOME/platforms/android-23/android.jar" '
    pathToManifest = "-M AndroidManifest.xml " 
    forceOverwrite = "-f "
    
    myCMD = 'aapt package ' + forceOverwrite + pathToManifest + pathToAndroidJar + pathToDrawablesAndLayouts + outputDir + creatOutDir 
    [out, err] = runCMD(myCMD, workingDirectory)
    #TODO: if error "The type ClassName cannot be found in source files" try clean then build

def compileAndroid(buildDirectory):
    print '    Compiling with Jack toolchain'
    print"@@@@@@@@"
    classpath = '--classpath "$ANDROID_HOME/platforms/android-23/android.jar" '
    importTag = ''
    outputTag = '--output-dex ' + buildDirectory + '/out ' + buildDirectory + '/src/ ' + buildDirectory + '/gen/ '
    jack = 'java -jar "$ANDROID_HOME/build-tools/24.0.2/jack.jar" '
    myCMD = jack + classpath + importTag + outputTag 
    [out, err] = runCMD(myCMD, '.')

def packageAndroid(appName, buildDirectory, workingDirectory):
    print '    Packaging APK '
    outputDir = '-J ' + buildDirectory + '/gen/ '
    creatOutDir = "-m "
    pathToDrawablesAndLayouts = '-S ' + buildDirectory + '/res/ '
    pathToAndroidJar = '-I "$ANDROID_HOME/platforms/android-23/android.jar" '
    pathToManifest = '-M ' + buildDirectory + '/AndroidManifest.xml ' 
    forceOverwrite = "-f "
    apkOutFile = '-F ' + buildDirectory + '/' + appName +'.apk '
    
    myCMD = 'aapt package ' + forceOverwrite + pathToManifest + pathToAndroidJar + pathToDrawablesAndLayouts + apkOutFile
    [out, err] = runCMD(myCMD, '.')
    
    myCMD = 'aapt add ' + appName + '.apk ' + buildDirectory + '/out/classes.dex'
    [out, err] = runCMD(myCMD, workingDirectory)

def signAndroid(appName, buildDirectory):
    print '    Signing APK'
    keystoreTag = '-keystore ~/.android/debug.keystore '
    keystorePassword = '-storepass android '
    keyPassword = '-keypass android '
    outFile = buildDirectory + '/' + appName +'.apk '
    keyAlias = 'androiddebugkey '
    
    myCMD = 'jarsigner -verbose ' + keystoreTag + keystorePassword + keyPassword + outFile + keyAlias 
    [out, err] = runCMD(myCMD, '.')

def zipalignAndroid(appName, buildDirectory):
    print '    Zipaligning APK'
    forceOverwrite = "-f "
    allignmentTag = '4 '
    inFile = buildDirectory + '/' + appName +'.apk  '
    outFile = buildDirectory + '/' + appName +'-aligned.apk '
    
    myCMD = 'zipalign ' + forceOverwrite + allignmentTag + inFile + outFile
    [out, err] = runCMD(myCMD, '.')
    
def uploadAndroid(appName, buildDirectory):
    print '    Uploading APK'
    replaceExistingApp = '-r '
    pathToAPK = buildDirectory + '/' + appName +'-aligned.apk'
    
    myCMD = 'adb install ' + replaceExistingApp + pathToAPK
    [out, err] = runCMD(myCMD, '.')

def runAndroid(appName):
    print '    Running '
    
    
    myCMD = 'adb shell am start com.infomage.' + appName +'/.MainActivity'
    [out, err] = runCMD(myCMD, '.')

def AndroidBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, outStr):
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
    currentDirectory = os.getcwd()
    buildDirectory  = buildName
    workingDirectory = currentDirectory + '/' + buildDirectory
    # TODO: pass appPaths
    appPaths = ['/src/com', '/src/com/infomage', '/src/com/infomage/dataDog']
    fileExtension = '.java'
    
    print 'Building for Android' 
    pathAndroid(appPaths, workingDirectory)
    writeFile(buildName + "/src/com/infomage/dataDog", fileName, outStr, fileExtension)
    androidManifest(fileName, workingDirectory)
    generateAndroid(workingDirectory)
    compileAndroid(buildDirectory)
    packageAndroid(fileName, buildDirectory, workingDirectory)
    signAndroid(fileName, buildDirectory)
    zipalignAndroid(fileName, buildDirectory)
    uploadAndroid(fileName, buildDirectory)
    runAndroid(fileName)
    print 'Finished Building for Android'
