# buildDog.py
# import into codeDog.py and call from there
# args to build function: path, libraries etc
# get it to work with C++ or print error msg
import progSpec
import os
import subprocess
import buildAndroid
import errno

#TODO: error handling

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

def LinuxBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, outStr):
    buildStr = ''
    libStr = ''
    langStr = 'g++ '
    minLangStr = '-std=gnu++' + minLangVersion + ' '
    fileExtension = '.cpp'
    fileStr = fileName + fileExtension
    outputFileStr = '-o ' + fileName 
    
    writeFile(buildName, fileName, outStr, fileExtension)
    
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
    buildStr = langStr + debugMode + " " + minLangStr + fileStr  + " " + libStr + " " + outputFileStr
    return [workingDirectory, buildStr]

def SwingBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, outStr):
    buildStr = ''
    libStr = ''
    langStr = 'javac '
    minLangStr = ''
    fileExtension = '.java'
    fileStr = fileName + fileExtension
    outputFileStr = ''
    debugMode = ''
    
    writeFile(buildName, fileName, outStr, fileExtension)
    
    for libFile in libFiles:
        libStr += libFile
        #print "libStr: " + libStr
    currentDirectory = currentWD = os.getcwd()
    #TODO check if above is typo
    workingDirectory = currentDirectory + "/" + buildName
    buildStr = langStr + debugMode + " " + minLangStr + fileStr + libStr + " " + outputFileStr
    return [workingDirectory, buildStr]

def build(debugMode, minLangVersion, fileName, libFiles, buildName, outStr):
    if buildName == 'LinuxBuild':
        [workingDirectory, buildStr] = LinuxBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, outStr)
    elif buildName == 'SwingBuild':
        [workingDirectory, buildStr] = SwingBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, outStr)
    elif buildName == 'AndroidBuild':
        [workingDirectory, buildStr] = buildAndroid.AndroidBuilder(debugMode, minLangVersion, fileName, libFiles, buildName, outStr)
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

