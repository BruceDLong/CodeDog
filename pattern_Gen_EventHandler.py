import progSpec
import codeDogParser

# TODO: Write PollEvent(), AddEvent(), Handle_*(), Prime_*()

#/////////////////////////////////////////////////  R o u t i n e s   t o   G e n e r a t e  a n   E v e n t H a n d l e r
numInstances = 0

def showDocs():
    print "Instructions and field labels."
    print "This can be used to make a GUI wrapper"

def wizard():
    print "Try to autogenerate something."

def validate():
    print "Validate / set tags used by this pattern and print any errors."

def apply(objects, tags, tagToUse):
    global numInstances
    numInstances += 1
    EH_spec = progSpec.fetchTagValue([tags], tagToUse)
    spec_ID = EH_spec['ID']
    spec_EV_Types = EH_spec['types']
    spec_runFromMain = EH_spec['runFromMain']
    spec_maxEvents = EH_spec['maxEvents']

    EventHandlerCode=''

    if(numInstances == 1):
        EventHandlerCode += 'struct event {their void: funcAddr our void: structPtr}\n\n'

    ADD_EV_Code = ""
    for EH in spec_EV_Types:
        ADD_EV_Code += "me bool: addEvent_%s(their %s: ev) <- {return (0)}\n" % (EH, EH)

    EventHandlerCode += """
    struct EventMaster_%s {
        me bool: notDone
        const uint32: maxQueueSize <-%s
        me event[%s]: events
        me uint32: crntEvent <- 0
        me uint32: head <- 0
        me uint32: tail <- 0

        %s

        me bool: pollEvent(their event: ev) <- {return (0)}
        me void: clearEvents() <- {head<-0 tail<-0 crntEvent<-0}
        me bool: primeEvents() <- {return(0)}
    """ % (spec_ID, str(spec_maxEvents), str(spec_maxEvents), ADD_EV_Code)

    #TODO: When CodeDog handles function pointers, write this in CodeDog without verbatims.
    EventHandlerCode += """
        me uint32: eventLoop() <- <%{
            event* ev;
            notDone = true;
            while(notDone)
            {
                while(pollEvent(ev))
                {
                    bool (*handler)(void *) = (bool (*)(void *))ev->funcAddr;
                    handler(ev->structPtr.get());
                }
            }
        } %>
    }
"""

    print "PARSING THIS:\n", EventHandlerCode, "\n#######################\n"
    codeDogParser.AddToObjectFromText(objects[0], objects[1], EventHandlerCode)
