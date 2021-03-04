# buildAndroid.py

import os
import subprocess
import errno
import shutil

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
    print("        COMMAND: ", myCMD, "\n")
    pipe = subprocess.Popen(myCMD, cwd=myDir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    if out:
        print("        Result: ",out)
    if err:
        print("\n", err)
        if (err.find("ERROR")) >= 0:
            exit(1)
    return [out, err]

def makeDir(dirToGen):
    #print "dirToGen:", dirToGen
    try:
        os.makedirs(dirToGen)
    except OSError as exception:
        if exception.errno != errno.EEXIST: raise

def copyTree(src, dst):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, False, None)
        else:
            shutil.copy2(s, d)
def copyFile(fileName, src, dst):
    s = os.path.join(src, fileName)
    d = os.path.join(dst, fileName)
    if os.path.isdir(s):
        shutil.copytree(s, d, False, None)
    else:
        shutil.copy2(s, d)

def pathAndroid(workingDir, dirsToGen):
    print('--------------------------------   G e n e r a t i n g   F o l d e r   S t r u c t u r e \n')
    makeDir(workingDir)
    for dirToGen in dirsToGen:
        makeDir(workingDir + dirToGen)

def gradleFile(topDomain, domain, appName, workingDir):
    print('--------------------------------   G e n e r a t i n g   G r a d l e \n')
    fileName = "build.gradle"

    outStr =    'buildscript {\n' \
                '    repositories {\n' \
                '        mavenCentral()\n' \
                '        jcenter()\n' \
                '        google()\n' \
                '    }\n' \
                '    dependencies {\n' \
                '        classpath "com.android.tools.build:gradle:3.6.2"\n' \
                '    }\n' \
                '}\n' \
                'apply plugin: "com.android.application"\n' \
                'android {\n' \
                '    compileSdkVersion 28\n' \
                '    defaultConfig {\n' \
                '        targetSdkVersion 28\n' \
                '        minSdkVersion 24\n' \
                '    }\n' \
                '    sourceSets {main{res.srcDirs = [\'res\']}}\n'\
                '    buildTypes {\n' \
                '        release {\n' \
                '            minifyEnabled false\n' \
                '            proguardFiles getDefaultProguardFile("proguard-android.txt"), "proguard-rules.pro"\n' \
                '        }\n' \
                '    }\n' \
                '}\n' \
                'allprojects {\n' \
                '    repositories {\n' \
                '        jcenter()\n' \
                '        maven {\n' \
                '            url "https://maven.google.com"\n' \
                '        }\n' \
                '    }\n' \
                '}\n' \
                'dependencies {\n' \
                '    implementation fileTree(dir: "libs", include: ["*.jar"])\n' \
                '    implementation "com.android.support:appcompat-v7:24.1.1"\n' \
                '    implementation "com.android.support:support-v4:24.2.1"\n' \
                '    implementation "com.android.support:design:24.2.1"\n' \
                '}\n' \

    fo=open(workingDir + os.sep + fileName, 'w')
    fo.write(outStr)
    fo.close()

def androidManifest(topDomain, domain, moduleName, labelName, launchIconName, mainDir):
    print('--------------------------------   G e n e r a t i n g   M a n i f e s t \n')
    fileName = "AndroidManifest.xml"
    if launchIconName: iconTag = 'android:icon="@drawable/' + launchIconName + '"'
    else: iconTag = ''

    outStr = '<?xml version="1.0" encoding="utf-8"?>\n' \
            '<manifest xmlns:android="http://schemas.android.com/apk/res/android"\n' \
            '    package="' + topDomain + '.' + domain + '.' + moduleName + '">\n' \
            '    <application ' + iconTag + ' android:label="' + labelName + '"\n' \
            '        android:theme="@style/Theme.AppCompat.Light.NoActionBar">\n' \
            '        <activity android:name="' + moduleName + '">\n' \
            '            <intent-filter>\n' \
            '                <action android:name="android.intent.action.MAIN" />\n' \
            '                <category android:name="android.intent.category.LAUNCHER" />\n' \
            '            </intent-filter>\n' \
            '        </activity>\n' \
            '    </application>\n' \
            '</manifest>\n' \

    fo=open(mainDir + os.sep + fileName, 'w')
    fo.write(outStr)
    fo.close()

def AndroidBuilder(debugMode, minLangVersion, fileName, labelName, launchIconName, libFiles, buildName, platform, outStr):
    fileExt        = '.java'
    topDomain      = "com"
    domain         = "infomage"
    currentDir     = os.getcwd()
    workingDir     = currentDir + '/' + buildName
    moduleName     = 'GLOBAL'
    packageDir     = '/src/main/java/'+topDomain+'/'+domain+'/'+moduleName
    assetsDir      = '/src/main/assets'
    drawableDir    = '/res/drawable'
    drawablePath   = workingDir + drawableDir
    packageName    = topDomain+'.'+domain+'.'+moduleName
    targetPlatform = ""
    dirsToGen = [assetsDir, packageDir, drawableDir]
    print('Building for Android: ', drawablePath)
    pathAndroid(workingDir, dirsToGen)
    copyTree("Resources", buildName+assetsDir)
    if launchIconName:
        launchIconName = launchIconName+'.png'
        copyFile(launchIconName, currentDir, drawablePath)
    writeFile(workingDir, packageDir, moduleName, outStr, fileExt, packageName)
    gradleFile(topDomain, domain, moduleName, workingDir)
    androidManifest(topDomain, domain, moduleName, labelName, launchIconName, workingDir+'/src/main')
    # TODO: add missing files to workingDir
    #[out, err] = runCMD( './gradlew tasks ', workingDir)
    #[out, err] = runCMD( './gradlew assembleDebug --stacktrace', workingDir)
    #[out, err] = runCMD( './gradlew installDebug ', workingDir)
    print('     NOTE: Working Directory is  '+currentDir + '/' + buildName)
    print('     NOTE: Build Debug command:    ./gradlew assembleDebug --stacktrace')
    print('     NOTE: Build Release command:  ./gradlew assembleRelease --stacktrace')
    print('     NOTE: Install command:        ./gradlew installDebug')
    print('Finished Building for Android')
