#///////// Add routines for Java

import progSpec
import codeDogParser

#TODO: make conversion for rand to GLOBAL.getRandInt & main return(0)
def createUtilityFunctions():
    S="""
        me void: endFunc(me int: val) <- <%!%G %>
        me int: randInt(me int: val) <- <%!javaRandomVar.nextInt((int)(%1))%>
        me void: print(me string: s)<- <%!%GSystem.out(%1)%>
        me void: exit(me int: val) <- <%!%GSystem.exit(%1)%>
        me bool: isdigit(me char: ch) <- <%!%GCharacter.isDigit(%1)%>
        me bool: isalpha(me char: ch) <- <%!%GCharacter.isLetter(%1)%>
        me bool: isspace(me char: ch) <- <%!%GCharacter.isWhitespace(%1)%>
        me bool: isalnum(me char: ch) <- <%!%GCharacter.isLetterOrDigit(%1)%>
        me int64: stoi(me string: str) <- <%!%GInteger.parseInt(%1)%>
        me bool: isprint(me char: ch) <- <%!%GCharacter.isISOControl(%1)%>
        me long: getCurrentTimeStamp() <- <%!%Gnew Date().getTime()%>
        me string: readFileAsString(me string: fileName) <- <%!%readFileAsString(%1)%>
        me timeOutID: callPeriodically(me string: varClass, me string: funcToCall, me int:microSecs): COMMAND_addImplements="Runnable:ToClass:%1" <- <%!%GScheduledExecutorService timerID=Executors.newSingleThreadScheduledExecutor(); timerID.scheduleAtFixedRate(%2, 0, %3, TimeUnit.MILLISECONDS)%>
        me string: toString(me int: val) <- <%!%GInteger.toString(%1)%>
    """
    return S


def use(classes, buildSpec, tags, platform):
    print "USING Java"

    CODE="""
        struct random{me Random: random}
        struct timeValue{me long: timeValue}
        """
    codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE )

    APP_UTILITY_CODE = createUtilityFunctions()

    GLOBAL_CODE="""
        struct GLOBAL{
            we GLOBAL: static_Global
            me Random: javaRandomVar
            me string: readFileAsString(me string: filePath)<- <%{
                try {
                    DataInputStream dis = new DataInputStream(new FileInputStream(filePath));
                    try {
                        long len = new File(filePath).length();
                        if (len > Integer.MAX_VALUE) return "";
                        byte[] bytes = new byte[(int) len];
                        dis.readFully(bytes);
                        return new String(bytes, "UTF-8");
                    } finally {
                        dis.close();
                    }
                } catch (IOException ioe) {
                    System.out.println("Cannot read file " + ioe.getMessage());
                    return "";
                }
            }%>

            me bool: doesFileExist(me string: filePath)<- <%{
                File f = new File(filePath);
                if(f.exists() && f.isFile()) {
                    return true;
                }
                return false;

            }%>
            /- LOGGING INTERFACE:
""" + (APP_UTILITY_CODE) + """
        }
"""


  #  print "GLOBAL_CODE: ", GLOBAL_CODE

    codeDogParser.AddToObjectFromText(classes[0], classes[1], GLOBAL_CODE )
