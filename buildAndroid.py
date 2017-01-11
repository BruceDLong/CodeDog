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
    #print "dirToGen:", dirToGen
    try:
        os.makedirs(dirToGen)
    except OSError as exception:
        if exception.errno != errno.EEXIST: raise

def pathAndroid(workingDir, dirsToGen):
    print '    Generating folder structure'
    makeDir(workingDir)
    for dirToGen in dirsToGen:
        makeDir(workingDir + dirToGen)

def androidManifest(topDomain, domain, appName, workingDir):
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
    print '    Generating R.java'
    outputDir = "-J gen/ "
    creatOutDir = "-m "
    pathToDrawablesAndLayouts = "-S " + workingDir + "/res/ "
    pathToAndroidJar = '-I "$ANDROID_HOME/platforms/android-23/android.jar" '
    pathToManifest = "-M AndroidManifest.xml "
    forceOverwrite = "-f "

    myCMD = 'aapt package ' + forceOverwrite + pathToManifest + pathToAndroidJar + pathToDrawablesAndLayouts + outputDir + creatOutDir
    [out, err] = runCMD(myCMD, workingDir)
    #TODO: if error "The type ClassName cannot be found in source files" try clean then build

def compileAndroid(buildName):
    print '    Compiling with Jack toolchain'
    classpath = '--classpath "$ANDROID_HOME/platforms/android-23/android.jar" '
    importTag = ''
    outputTag = '--output-dex ' + buildName + '/out ' + buildName + '/src/ ' + buildName + '/gen/ '
    #jack = 'java -jar "$ANDROID_HOME/build-tools/24.0.1/jack.jar" '
    jack = 'java -jar "$ANDROID_HOME/build-tools/24.0.2/jack.jar" '
    myCMD = jack + classpath + importTag + outputTag
    [out, err] = runCMD(myCMD, '.')

def packageAndroid(appName, buildName, workingDir):
    print '    Packaging APK '
    outputDir = '-J ' + buildName + '/gen/ '
    creatOutDir = "-m "
    pathToDrawablesAndLayouts = '-S ' + buildName + '/res/ '
    pathToAndroidJar = '-I "$ANDROID_HOME/platforms/android-23/android.jar" '
    pathToManifest = '-M ' + buildName + '/AndroidManifest.xml '
    forceOverwrite = "-f "
    apkOutFile = '-F ' + buildName + '/' + appName +'.apk '

    myCMD = 'aapt package ' + forceOverwrite + pathToManifest + pathToAndroidJar + pathToDrawablesAndLayouts + apkOutFile
    [out, err] = runCMD(myCMD, '.')

    myCMD = 'aapt add ' + appName + '.apk ' + buildName + '/out/classes.dex'
    [out, err] = runCMD(myCMD, workingDir)

def signAndroid(appName, buildName):
    print '    Signing APK'
    keystoreTag = '-keystore ~/.android/debug.keystore '
    keystorePassword = '-storepass android '
    keyPassword = '-keypass android '
    outFile = buildName + '/' + appName +'.apk '
    keyAlias = 'androiddebugkey '

    myCMD = 'jarsigner -verbose ' + keystoreTag + keystorePassword + keyPassword + outFile + keyAlias
    [out, err] = runCMD(myCMD, '.')

def zipalignAndroid(appName, buildName):
    print '    Zipaligning APK'
    forceOverwrite = "-f "
    allignmentTag = '4 '
    inFile = buildName + '/' + appName +'.apk  '
    outFile = buildName + '/' + appName +'-aligned.apk '

    myCMD = 'zipalign ' + forceOverwrite + allignmentTag + inFile + outFile
    [out, err] = runCMD(myCMD, '.')

def uploadAndroid(appName, buildName):
    print '    Uploading APK'
    replaceExistingApp = '-r '
    pathToAPK = buildName + '/' + appName +'-aligned.apk'

    myCMD = 'adb install ' + replaceExistingApp + pathToAPK
    [out, err] = runCMD(myCMD, '.')

def runAndroid(packageName):
    print '    Running '


    myCMD = 'adb shell am start ' + packageName +'/.MainActivity'
    [out, err] = runCMD(myCMD, '.')

def AndroidBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, outStr):
    topDomain = "com"
    domain = "infomage"
    currentDir = os.getcwd()
    workingDir = currentDir + '/' + buildName
    #fileName = 'GLOBAL'
    packageDir = '/src/'+topDomain+'/'+domain+'/'+fileName
    packageName = topDomain+'.'+domain+'.'+fileName
    dirsToGen = ['/gen', '/libs', '/out', '/res/drawable-xhdpi', '/res/layout', packageDir]
    fileExt = '.java'

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
