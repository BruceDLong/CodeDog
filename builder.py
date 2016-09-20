# builder.py
# import into codeDog.py and call from there
# args to build function: path, libraries etc
# get it to work with C++ or print error msg
import progSpec
import os

def build(Lang, debugMode, minLangVersion, fileName, libFiles, buildName):
    buildStr = ''
    libStr = ''
    
    if Lang == 'CPP': 
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
        workingDirectory = currentDirectory + "/" + buildName
    elif Lang == 'Java':
        langStr = 'javac '
        minLangStr = ''
        fileStr = fileName + '.java'
        outputFileStr = ''
        debugMode = ""
        
        for libFile in libFiles:
            libStr += libFile
            #print "libStr: " + libStr
        currentDirectory = currentWD = os.getcwd()
        workingDirectory = currentDirectory + "/" + buildName
    else: 
        print "Builer.py error: build string not generated for "+ Lang
        exit(2)
 
    buildStr = langStr + debugMode + " " + minLangStr + fileStr + libStr + " " + outputFileStr
    return [buildStr, workingDirectory]

