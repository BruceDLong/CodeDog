# buildAndroid.py

import os
import subprocess
import errno

def writeFile(workingDir, packageDir, fileName, outStr, fileExt, packageName):
    #print "Path:", packageDir
    makeDir(workingDir+packageDir)
    fileName += fileExt
    fo=open(workingDir+packageDir + os.sep + fileName, 'w')
    packageHeader = "package " + packageName + ";\n\n"
    outStr =  packageHeader +  outStr[0][1]
    fo.write(outStr)
    fo.close()

def runCMD(myCMD, myDir):
    print "        COMMAND: ", myCMD, "\n"
    pipe = subprocess.Popen(myCMD, cwd=myDir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    if out:
        print "        Result: ",out
    if err:
        print "\n", err
        if (err.find("ERROR")) >= 0:
            exit(1)
    return [out, err]

def makeDir(dirToGen):
    #print "dirToGen:", dirToGen
    try:
        os.makedirs(dirToGen)
    except OSError as exception:
        if exception.errno != errno.EEXIST: raise

def pathAndroid(workingDir, dirsToGen):
    print '--------------------------------   G e n e r a t i n g   F o l d e r   S t r u c t u r e \n'
    makeDir(workingDir)
    for dirToGen in dirsToGen:
        makeDir(workingDir + dirToGen)

def androidManifest(topDomain, domain, appName, workingDir):
    print '--------------------------------   G e n e r a t i n g   M a n i f e s t \n'
    manifestName = "AndroidManifest.xml"

    outStr = '<?xml version="1.0" encoding="utf-8"?>\n' \
            '<manifest xmlns:android="http://schemas.android.com/apk/res/android"\n' \
            '    package="' + topDomain + '.' + domain + '.' + appName + '">\n' \
            '    <application android:label="' + appName + '">\n' \
            '        <activity android:name="' + appName + '">\n' \
            '            <intent-filter>\n' \
            '                <action android:name="android.intent.action.MAIN" />\n' +\
            '                <category android:name="android.intent.category.LAUNCHER" />\n' \
            '            </intent-filter>\n' \
            '        </activity>\n' \
            '    </application>\n' \
            '</manifest>\n' \

    fo=open(workingDir + os.sep + manifestName, 'w')
    fo.write(outStr)
    fo.close()

def generateAndroid(workingDir):
    print '--------------------------------   G e n e r a t i n g   R . j a v a   f o r   R e s o u r c e s'
    outputDir = "-J gen/ "
    creatOutDir = "-m "
    pathToResources = "-S " + workingDir + "/res/ "
    pathToAndroidJar = '-I "$ANDROID_HOME/platforms/android-23/android.jar" '
    pathToManifest = "-M AndroidManifest.xml "
    forceOverwrite = "-f "

    myCMD = 'aapt package ' + forceOverwrite + pathToManifest + pathToAndroidJar + pathToResources + outputDir + creatOutDir
    [out, err] = runCMD(myCMD, workingDir)
    #TODO: if error "The type ClassName cannot be found in source files" try clean then build

def compileAndroid(buildName):
    print '--------------------------------   C o m p i l i n g   w i t h   J a c k   T o o l c h a i n'
    # generates out/classes.dex  file
    classpath = '--classpath "$ANDROID_HOME/platforms/android-23/android.jar" '
    importTag = ''
    outputTag = '--output-dex ' + buildName + '/out ' + buildName + '/src/ ' + buildName + '/gen/ '
    #jack = 'java -jar "$ANDROID_HOME/build-tools/24.0.1/jack.jar" '
    jack = 'java -jar "$ANDROID_HOME/build-tools/24.0.2/jack.jar" '
    myCMD = jack + classpath + importTag + outputTag
    [out, err] = runCMD(myCMD, '.')

def packageAndroid(appName, buildName, workingDir):
    # Android Asset Packaging Tool
    print '--------------------------------   P a c k a g i n g   A P K'
    # First, we create the initial package file with the manifest and resources
    outputDir = '-J ' + buildName + '/gen/ '
    creatOutDir = "-m "
    pathToDrawablesAndLayouts = '-S ' + buildName + '/res/ '
    pathToAndroidJar = '-I "$ANDROID_HOME/platforms/android-23/android.jar" '
    pathToManifest = '-M ' + buildName + '/AndroidManifest.xml '
    forceOverwrite = "-f "
    apkOutFile = '-F ' + buildName + '/out/' + appName +'.apk '
    pathToAssets = '-A ' + buildName + '/assets/ '

    myCMD = 'aapt package ' + forceOverwrite + pathToManifest + pathToAndroidJar + pathToDrawablesAndLayouts + apkOutFile + pathToAssets
    [out, err] = runCMD(myCMD, '.')
    print '--------------------------------   A d d i n g   c l a s s e s . d e x'
    # Now we add our compiled classes.dex
    # change to /out directory
    workingDir = workingDir + "/out"
    apkFile = appName + '.apk '
    dexFile = 'classes.dex'

    myCMD = 'aapt add ' + apkFile + dexFile
    [out, err] = runCMD(myCMD, workingDir)

def signAndroid(appName, buildName):
    print '--------------------------------   S i g n i n g   A P K'
    keystoreTag = '-keystore ~/.android/debug.keystore '
    keystorePassword = '-storepass android '
    keyPassword = '-keypass android '
    outFile = buildName + '/out/' + appName +'.apk '
    keyAlias = 'androiddebugkey '

    myCMD = 'jarsigner -verbose ' + keystoreTag + keystorePassword + keyPassword + outFile + keyAlias
    [out, err] = runCMD(myCMD, '.')

def zipalignAndroid(appName, buildName):
    print '--------------------------------   Z i p a l i g n i n g   A P K'
    forceOverwrite = "-f "
    allignmentTag = '4 '
    inFile = buildName + '/out/' + appName +'.apk  '
    outFile = buildName + '/out/' + appName +'-aligned.apk '

    myCMD = 'zipalign ' + forceOverwrite + allignmentTag + inFile + outFile
    [out, err] = runCMD(myCMD, '.')

def uploadAndroid(appName, buildName):
    print '--------------------------------   U p l o a d i n g   A P K'
    replaceExistingApp = '-r '
    pathToAPK = buildName + '/out/' + appName +'-aligned.apk'

    myCMD = 'adb install ' + replaceExistingApp + pathToAPK
    [out, err] = runCMD(myCMD, '.')

def runAndroid(packageName):
    print '--------------------------------   R u n n i n g'
    myCMD = 'adb shell am start ' + packageName +'/.GLOBAL'
    [out, err] = runCMD(myCMD, '.')

def AndroidBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, outStr):
    fileExt = '.java'
    topDomain = "com"
    domain = "infomage"
    currentDir = os.getcwd()
    workingDir = currentDir + '/' + buildName
    fileName = 'GLOBAL'
    packageDir = '/src/'+topDomain+'/'+domain+'/'+fileName
    packageName = topDomain+'.'+domain+'.'+fileName
    targetPlatform = ""
    dirsToGen = ['/assets', '/gen', '/libs', '/out', '/res/drawable', '/res/layout', packageDir]

    print 'Building for Android'
    pathAndroid(workingDir, dirsToGen)
    writeFile(workingDir, packageDir, fileName, outStr, fileExt, packageName)
    androidManifest(topDomain, domain, fileName, workingDir)
    generateAndroid(workingDir)
    compileAndroid(buildName)
    packageAndroid(fileName, buildName, workingDir)
    signAndroid(fileName, buildName)
    zipalignAndroid(fileName, buildName)
    uploadAndroid(fileName, buildName)
    runAndroid(packageName)
    print 'Finished Building for Android'
