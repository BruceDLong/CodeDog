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

def copyTree(src, dst):
    for item in os.listdir(src):
        print "item: ", item
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, False, None)
        else:
            print"else"
            shutil.copy2(s, d)

def pathAndroid(workingDir, dirsToGen):
    print '--------------------------------   G e n e r a t i n g   F o l d e r   S t r u c t u r e \n'
    makeDir(workingDir)
    for dirToGen in dirsToGen:
        makeDir(workingDir + dirToGen)

def gradleFile(topDomain, domain, appName, workingDir):
    print '--------------------------------   G e n e r a t i n g   G r a d l e \n'
    fileName = "build.gradle"

    outStr =    'buildscript {\n' \
                '    repositories {\n' \
                '        mavenCentral()\n' \
                '        jcenter()\n' \
                '        google()\n' \
                '    }\n' \
                '    dependencies {\n' \
                '        classpath "com.android.tools.build:gradle:3.0.1"\n' \
                '    }\n' \
                '}\n' \
                'apply plugin: "com.android.application"\n' \
                'android {\n' \
                '    compileSdkVersion 26\n' \
                '    defaultConfig {\n' \
                '        targetSdkVersion 26\n' \
                '        minSdkVersion 16\n' \
                '  }\n' \
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
                '    compile fileTree(dir: "libs", include: ["*.jar"])\n' \
                '    compile "com.android.support:appcompat-v7:23.1.1"\n' \
                '}\n' \

    fo=open(workingDir + os.sep + fileName, 'w')
    fo.write(outStr)
    fo.close()
    
def androidManifest(topDomain, domain, appName, workingDir):
    print '--------------------------------   G e n e r a t i n g   M a n i f e s t \n'
    fileName = "AndroidManifest.xml"

    outStr = '<?xml version="1.0" encoding="utf-8"?>\n' \
            '<manifest xmlns:android="http://schemas.android.com/apk/res/android"\n' \
            '    package="' + topDomain + '.' + domain + '.' + appName + '">\n' \
            '    <application android:label="' + appName + '"\n' \
            '        android:theme="@style/Theme.AppCompat.Light.NoActionBar">\n' \
            '        <activity android:name="' + appName + '"\n' \
            '            android:label="' + appName + '">\n' \
            '            <intent-filter>\n' \
            '                <action android:name="android.intent.action.MAIN" />\n' \
            '                <category android:name="android.intent.category.LAUNCHER" />\n' \
            '            </intent-filter>\n' \
            '        </activity>\n' \
            '    </application>\n' \
            '</manifest>\n' \

    fo=open(workingDir + os.sep + fileName, 'w')
    fo.write(outStr)
    fo.close()

def AndroidBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, platform, outStr):
    fileExt = '.java'
    topDomain = "com"
    domain = "infomage"
    currentDir = os.getcwd()
    workingDir = currentDir + '/' + buildName
    fileName = 'GLOBAL'
    packageDir = '/src/main/'+topDomain+'/'+domain+'/'+fileName
    packageName = topDomain+'.'+domain+'.'+fileName
    targetPlatform = ""
    dirsToGen = ['/assets', packageDir]

    print 'Building for Android'
    pathAndroid(workingDir, dirsToGen)
    copyTree("Resources", buildName+"/assets")
    writeFile(workingDir, packageDir, fileName, outStr, fileExt, packageName)
    gradleFile(topDomain, domain, fileName, workingDir)
    androidManifest(topDomain, domain, fileName, workingDir+'/src/main')
    [out, err] = runCMD( 'gradle tasks ', workingDir)
    [out, err] = runCMD( 'gradle assembleDebug --stacktrace', workingDir)
    [out, err] = runCMD( 'gradle installDebug ', workingDir)
    print 'Finished Building for Android'
