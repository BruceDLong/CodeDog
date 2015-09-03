
def bitsNeeded(n):
    if n <= 1:
        return 0
    else:
        return 1 + bitsNeeded((n + 1) / 2)

def fetchTagValue(tagStoreArray, tagToFind):
    for tagStore in reversed(tagStoreArray):
        if(tagToFind in tagStore):
            return tagStore[tagToFind]
    return None

structsSpec={}
MainPrgSpec={}
structNames=[]
structPtrs ={}
parserGlobalText=""
mainFuncCode=""
parserString=""


def getNameSegInfo(structName, fieldName):
    structToSearch = structsSpec[structName]
    if not structToSearch: print "struct ", structName, " not found."; exit(2);
    fieldListToSearch = structToSearch['fields']
    if not fieldListToSearch: print "struct's fields ", structName, " not found."; exit(2);
    for fieldRec in fieldListToSearch:
        if fieldRec['fieldName']==fieldName:
            print "FOR ", structName, ',', fieldName, ", returning", fieldRec
            return fieldRec
    return None

def getFieldInfo(structName, fieldNameSegments):
    # return [kind-of-last-element,  reference-string, type-of-last-element]
    structKind=""
    prevKind="ptr"
    structType=""
    referenceStr=""
    print "    Getting Field Info for:", structName, fieldNameSegments
    for fieldName in fieldNameSegments:
        REF=getNameSegInfo(structName, fieldName)
        if(REF):
            print "    REF:", REF
            if 'kindOfField' in REF:
                structKind=REF['kindOfField']
                if(prevKind=="ptr"): joiner='.' #'->'
                else: joiner='.'
                if (structKind=='flag'):
                    referenceStr+=joiner+"flags"
                elif structKind=='mode':
                    referenceStr+=joiner+'flags'
                elif structKind=='var':
                    referenceStr+= joiner+fieldName
                    structType=REF['fieldType']
                elif structKind=='ptr':
                    referenceStr+= joiner+fieldName
                    structType=REF['fieldType']
                prevKind=structKind
            structName=structType
        else: print "Problem getting name seg info:", structName, fieldName; exit(1);
    return [structKind, referenceStr, structType]

def getValueString(structName, valItem):
    if isinstance(valItem, list):
        return getFieldInfo(structName, valItem)
    else:
        return (["", valItem])

def getActionTestStrings(structName, action):
    print "################################ Getting Action and Test string for", structName, "ACTION:", action
    LHS=getFieldInfo(structName, action[0])
    print "LHS:", LHS
    RHS=getValueString(structName, action[2])
    leftKind=LHS[0]
    actionStr=""; testStr="";
    if leftKind =='flag':
        print "ACTION[0]=", action[2][0]
        actionStr="SetBits(ITEM.flags, "+action[0][-1]+", "+ action[2][0]+");"
        testStr="(flags&"+action[0][0]+")"
    elif leftKind == "mode":
        ITEM="ITEM"
        actionStr="SetBits("+ITEM+LHS[1]+", "+action[0][-1]+"Mask, "+ action[2][0]+");"
        testStr="((flags&"+action[0][-1]+"Mask)"+">>"+action[0][-1]+"Offset) == "+action[2][0]
    elif leftKind == "var":
        actionStr="ITEM"+LHS[1]+action[1]+action[2][0]+'; '
        testStr=action[0][0]+"=="+action[2][0]
    elif leftKind == "ptr":
        print "PTR - ERROR: CODE THIS"
        exit(2)
    return ([leftKind, actionStr, testStr])
#############################################   C r e a t e   A u x i l a r y   C o d e: enums, #defines, etc

def generate(objects, tagStoreArray):
    structForwardDecls="\n";
    structEnums="\n///////////////////////////////////////////////////\n////   E N U M E R A T I O N S \n\n"
    structCode =""      # for storing the struct section of generated code.
    structsData= {}
    structsList= []


    for struct in objects[1]:
        structsData[struct]={"needsFlags":False, "fields":[]}
        accessDefines=""
        structDef="    uint64_t flags;\n"
        print "Writing struct: ", struct
        bitCursor=0;
        needsFlagsVar=False
        structForwardDecls=structForwardDecls+"struct "+ struct +";   \t// Forward decl\n";
        structEnums = structEnums + "\n//// Enums for "+struct+":\n";
        for field in structsSpec[struct]['fields']:
            #print "     FIELD:", field
            kindOfField=field['kindOfField'];
            fieldName=field['fieldName'];
            if kindOfField=='flag':
                structsData[struct]["needsFlags"]=True
                structEnums += "const int "+fieldName +" = " + hex(1<<bitCursor) +";\n"
                bitCursor=bitCursor+1;
            elif kindOfField=='mode':
                structsData[struct]["needsFlags"]=True
                # calculate field and bit position
                enumSize= len(field['enumList'])
                numEnumBits=bitsNeeded(enumSize)
                #field[3]=enumSize;
                #field[4]=numEnumBits;
                enumMask=((1 << numEnumBits) - 1) << bitCursor

                structEnums = structEnums+"\nconst int "+fieldName +"Offset = " + hex(bitCursor) +";"
                structEnums = structEnums+"\nconst int "+fieldName +"Mask = " + hex(enumMask) +";"

                # enum
                count=0
                structEnums = structEnums+"\nenum " + fieldName +" {"
                for enumName in field['enumList']:
                    structEnums = structEnums+enumName+"="+hex(count<<bitCursor)
                    count=count+1
                    if(count<enumSize): structEnums = structEnums+", "
                structEnums = structEnums+"};\n";

                structEnums =structEnums+'string ' + fieldName+'Strings[] = {"'+('", "'.join(field['enumList']))+'"};\n'
                # read/write macros
                accessDefines = accessDefines + "#define "+fieldName+"is(VAL) ((inf)->flags & )"
                # str array and printer


                bitCursor=bitCursor+numEnumBits;
            elif kindOfField=='var':
    #           addField(struct, 'var', field['fieldType'], fieldName)
                structsData[struct]["fields"].append([field['fieldType'], fieldName])
            elif kindOfField=='ptr':
                structsData[struct]["fields"].append([field['fieldType']+"Ptr", fieldName])
                #progSpec.CreatePointerItems([structsSpec, objectNames ], field['fieldType'])
            elif kindOfField=='func':
                structsData[struct]["fields"].append(["FUNC", fieldName, field['returnType'], field['funcText']])
            else: print "\nWARNING!!! Invalid field type!\n";

        structsList.append(struct)

    #############################################    S y n t h e s i s   P a s s
    funcDefCode="// FUNCTION DEFINITIONS\n\n"

    # Write structs to strings in C++
    for structName in structsList:
        constructorInit=":"
        constructorArgs="    "+structName+"("
        if(structsData[structName]["needsFlags"]): structsData[structName]["fields"].append(["uint64_t", "flags", 1])
        if(structName in structPtrs):
            structsData[structName]["fields"].append(["uint", "refCnt", 0])
        structCode = structCode +"\nstruct "+structName+"{\n"
        count=0;
        for structField in structsData[structName]["fields"]:
            fieldType=structField[0]
            fieldName=structField[1]
            if fieldName=="FUNC":
                returnType=structField[2]
                if returnType=='none': returnType=""
                funcText = structField[3]
                parser=re.match("\s*(.+?\))", funcText)
                structCode += "    "+returnType + " " + parser.group(1)+";\n\n"
                funcDefCode += returnType + " " + structName +'::'+funcText+"\n\n"
            else:
                structCode += "    "+fieldType+" "+fieldName+";\n"
                if(fieldType[0:3]=="int" or fieldType[0:4]=="uint" or fieldType[-3:]=="Ptr"):
                    constructorArgs += fieldType+" _"+fieldName+"=0,"
                    constructorInit += fieldName+"("+" _"+fieldName+"),"
                    count=count+1
                elif(fieldType=="string"):
                    constructorArgs += fieldType+" _"+fieldName+'="",'
                    constructorInit += fieldName+"("+" _"+fieldName+"),"
                    count=count+1
        if(count>0):
            constructorInit=constructorInit[0:-1]
            constructorArgs=constructorArgs[0:-1]
        structCode += constructorArgs+")"+constructorInit+"{};\n" +"};\n"

    # Write pointer code
    structPtrCodeTop="//// Smart Pointer definitions:\n";
    structPtrCodeEnd="";
    for ptrStruct in structPtrs:
        structPtrCodeTop += r"typedef shared_ptr<"+structPtrs[ptrStruct]+"> "+structPtrs[ptrStruct]+"Ptr;\n"
       # structPtrCodeEnd += "\nvoid intrusive_ptr_add_ref("+structPtrs[ptrStruct]+"* p){++p->refCnt;} \nvoid intrusive_ptr_release("+structPtrs[ptrStruct]+"* p){if(--p->refCnt == 0) delete p;}\n"

    ################ Create Headers section
    hdrString="";
    includes = re.split("[,\s]+", tagStore['Include'])
    for hdr in includes:
        hdrString+="\n#include "+hdr
    hdrString += "\n\nusing namespace std; \n\n"

    #############################################    G e n e r a t e   C o d e
    headerFile  = "// "+tagStore['Title']+hdrString
    headerFile += "string enumText(string* array, int enumVal, int enumOffset){return array[enumVal >> enumOffset];}\n";
    headerFile += "#define SetBits(item, mask, val) {(item) &= ~(mask); (item)|=(val);}\n"
    headerFile += structForwardDecls;
    headerFile += tagStore['global'] + parserGlobalText

    headerFile += "\nstruct infSource{\n    uint32_t offset, length;\n};\n"
    headerFile += structEnums+"\n"+structPtrCodeTop+"\n" + structCode +"\n" + structPtrCodeEnd +"\n\n"
    headerFile += funcDefCode
    headerFile += parserString
    headerFile += mainFuncCode
    headerFile += '\n'

    return headerFile
