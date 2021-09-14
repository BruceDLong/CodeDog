#!/usr/bin/python3

import gi

gi.require_version("Gtk", "3.0")
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk as gtk
from gi.repository import Pango, PangoCairo

import cairo
import math

import sys

if len(sys.argv) > 1:
    filename = sys.argv[-1]
    print("'"+filename+"'")
else:
    filename = "codeDog.log"


def heachToSymbol(line, symbol):
    line = line.lstrip()
    symPos = line.find(symbol)
    heachVal = line[:symPos].rstrip()
    line = line[symPos+1:].lstrip()
    #print("FOUND:",line, heachVal)
    return(line, heachVal)

def heachArg(line):
    #print("LINE_IN:", line)
    line = line.lstrip()
    equalPos = line.find('=')
    heachVal = line[:equalPos].rstrip()
    line = line[equalPos+1:].lstrip()
    line, keyWord = heachToSymbol(line, ";")
    #print("heachArg:",line,"|", heachVal,"|", keyWord)
    return(line, heachVal, keyWord)

def messageBox(self, text, title):
    dlg = gtk.MessageDialog(parent=self, flags=0, message_type=gtk.MessageType.INFO, buttons=gtk.ButtonsType.CLOSE, text=title)
    dlg.set_title(title)
    dlg.format_secondary_text(text)
    dlg.run()
    dlg.destroy()

fontDesc="Sans Normal 16"

def renderText(cr, x, y, text, fontStr=""):
    global fontDesc
    if fontStr=="":
        fontStr = fontDesc
    layout = PangoCairo.create_layout(cr)
    layout.set_font_description(Pango.font_description_from_string(fontStr))
    layout.set_alignment(Pango.Alignment.CENTER)
    layout.set_markup(text, -1)
    cr.move_to(x,y)
    PangoCairo.show_layout(cr, layout)

def draw_rounded(cr, area, radius):
    """ draws rectangles with rounded (circular arc) corners """
    from math import pi
    a,b,c,d=area
    cr.arc(a + radius, c + radius, radius, 2*(pi/2), 3*(pi/2))
    cr.arc(b - radius, c + radius, radius, 3*(pi/2), 4*(pi/2))
    cr.arc(b - radius, d - radius, radius, 0*(pi/2), 1*(pi/2))  # ;o)
    cr.arc(a + radius, d - radius, radius, 1*(pi/2), 2*(pi/2))
    cr.close_path()
    cr.stroke()

def fatalError(mesg):
    messageBox(win, mesg, "Error")
    exit(-1)

class ActionSorter:
    seqSets = []
    altSets = []
    states  = []
    arrows  = []
    putChars= []

    SeqSetIdx = {}
    AltSetIdx = {}

    aItemIdx  = {}
    IdxNum = 1

    # iteration vars and methods
    crntPutChars = ""
    crntItem       = None
    crntItemType   = None  # 'seqSet', 'altSet', 'arrow', 'state', 'PUTCHars'
    crntSeqSet     = 0
    crntAltSet     = 0
    crntArrow      = 0
    crntStateDelta = 0
    crntPUT        = 0

    def resetIter(self):
        self.crntPutChars = ""
        self.crntItem       = None
        self.crntSeqSet     = -1
        self.crntAltSet     = -1
        self.crntArrow      = -1
        self.crntStateDelta = -1
        self.crntPUT        = -1
        self.goNext()
    '''
    def peekNextSeqItem(self):
        if self.crntSeq+1 < len(self.seqSets[self.crntSeqSet]):
            return(self.crntSeq+1, self.crntSeqSet)
        elif self.crntSeqSet+1 < len(self.seqSets):
            return(0, self.crntSeqSet+1)
        else: return(None, None)

    def peekNextAltItem(self):
        if self.crntAlt+1 < len(self.altSets[self.crntAltSet]):
            return(self.crntAlt+1, self.crntAltSet)
        elif self.crntAltSet+1 < len(self.altSets):
            return(0, self.crntAltSet+1)
        else: return(None, None)
'''

    def peekNextSeqItem(self):
        if self.crntSeqSet+1 < len(self.seqSets):
            return self.crntSeqSet+1
        else: return None

    def peekNextAltItem(self):
        if self.crntAltSet+1 < len(self.altSets):
            return self.crntAltSet+1
        else: return None

    def peekNextState(self):
        if self.crntStateDelta+1 < len(self.states):
            return self.crntStateDelta+1
        else: return None

    def peekNextArrow(self):
        if self.crntArrow+1 < len(self.arrows):
            return self.crntArrow+1
        else: return None

    def peekNextPUT(self):
        if self.crntPUT+1 < len(self.putChars):
            return self.crntPUT+1
        else: return None


    def goNext(self):
        nextIDs = []
        nSeqSet = self.peekNextSeqItem()
        nAltSet = self.peekNextAltItem()
        nState = self.peekNextState()
        nArrow = self.peekNextArrow()
        nPUT   = self.peekNextPUT()

        # Find each item's idx
        if nSeqSet!=None: nextIDs.append(self.seqSets[nSeqSet][0][0])
        else: nextIDs.append(None)

        if nAltSet!=None: nextIDs.append(self.altSets[nAltSet][0][0])
        else: nextIDs.append(None)

        if nState!=None: nextIDs.append(self.states[nState][0])
        else: nextIDs.append(None)

        if nArrow!=None: nextIDs.append(self.arrows[nArrow][0])
        else: nextIDs.append(None)

        if nPUT!=None: nextIDs.append(self.putChars[nPUT][0])
        else: nextIDs.append(None)

        # Find lowest idx
        lowestValIDX = -1
        lowestValue = 9999999999
        for idx in range(0,5):
            if nextIDs[idx]!=None and nextIDs[idx] <= lowestValue:
                lowestValIDX = idx
                lowestValue = nextIDs[idx]

        # EOL?
        if lowestValIDX == -1:
            self.crntItem = None
            return None

        # Update iterator position
        if   lowestValIDX==0: self.crntItem = self.seqSets[nSeqSet];  self.crntSeqSet=nSeqSet;      self.crntItemType='seqSet'
        elif lowestValIDX==1: self.crntItem = self.altSets[nAltSet];  self.crntAltSet=nAltSet;      self.crntItemType='altSet'
        elif lowestValIDX==2: self.crntItem = self.states[nState];    self.crntStateDelta = nState; self.crntItemType='state'
        elif lowestValIDX==3: self.crntItem = self.arrows[nArrow];    self.crntArrow = nArrow;      self.crntItemType='arrow'
        elif lowestValIDX==4: self.crntItem = self.putChars[nPUT];    self.crntPUT   = nPUT;        self.crntItemType='PUTCHars'

        return self.crntItem

    def dump(self):
        print("\n################################################# SeqSets")
        for sset in self.seqSets:
            for sItem in sset:
                print(">>:"+str(sItem[1]['eventDesc']))
        print("\n################################################# AltSets")
        for sset in self.altSets:
            for sItem in sset:
                print(">>:"+str(sItem[1]['eventDesc']))
            print()
        print("\n################################################# State Changes")
        for delta in self.states:
            print(">>:"+str(delta[1]['eventDesc']))
        print("\n################################################# Arrows Added")
        for arrow in self.arrows:
            print(">>:"+str(arrow[1]['eventDesc']))
        print("\n################################################# Chars Added")
        for PUTs in self.putChars:
            print(">>:"+str(PUTs[1]['eventDesc']))

### TODO NEXT:
###    * Integrate and test action-sorting. Esp Alloc.Seq, Arrow, State, Putting
###    * Choose correct key for addAsAltSet and test it
###    * Make iteration of this: InitIteration(), GetNext()
###
###    * Draw SeqSet, Seq*, AltSet
###    * Draw Arrows
###    * Set states and use colors
###    * Add controls: next, prev, zoom+-, 'peview of next', etc.
    def addAsSeqSet(self, aRecord):
        aItem = aRecord[1]
        SetKey = aItem['prodName']+"%%"+str(aItem['originPos'])
        if SetKey in self.SeqSetIdx:
            self.SeqSetIdx[SetKey].append(aRecord)
        else:
            newSeqSet = [aRecord]
            self.SeqSetIdx[SetKey] = newSeqSet
            self.seqSets.append(newSeqSet)

    def addAsAltSet(self, aRecord):
        aItem = aRecord[1]
        SetKey = aItem['prodName']+"##"+str(aItem['originPos'])
        if SetKey in self.AltSetIdx:
            self.AltSetIdx[SetKey].append(aRecord)
        else:
            newAltSet = [aRecord]
            self.AltSetIdx[SetKey] = newAltSet
            self.altSets.append(newAltSet)

    def insertPItem(self, pItem):
        aRecord = [self.IdxNum, pItem]
        self.IdxNum += 1
        opType = pItem['opType']
        if opType=='ALLOC':
            prodType = pItem['prodType']
            if prodType in ['SEQ', 'Aut', 'REP']:
                self.addAsSeqSet(aRecord)
            elif prodType=='ALT':
                self.addAsAltSet(aRecord)
            else: fatalError('Invalid production type '+prodType)
            self.aItemIdx[pItem['recName']] = pItem
        elif opType=="ARROW":
            self.arrows.append(aRecord)
        elif opType=='STATE':
            self.states.append(aRecord)
        elif opType=='PUTTING':
            self.putChars.append(aRecord)

class DrawingAreaFrame(gtk.Frame):
    def __init__(self, css=None, border_width=0):
        super().__init__()
        self.set_border_width(border_width)
        self.set_size_request(100, 100)
        self.vexpand = True
        self.hexpand = True
        self.surface = None

        self.area = gtk.DrawingArea()
        self.add(self.area)

        self.area.connect("draw", self.OnDraw)
        #self.area.connect('configure-event', self.on_configure)

    parseEvents = []
    actionSorter= ActionSorter()

    def clear(self):
        self.parseEvents = []

    def addParseEvent(self, logLine):
        #ALLOC: SREC: stateRec155: [ALT: 1..2: infon_str_ALT41_SEQ42  > | infon_str_ALT41_SEQ43 | innerInfon_str  >  (pos:0)]
        #ALLOC: SREC: stateRec156: [SEQ: 1..2: wsc bang_OPT infon_str_ALT41  > ws funcParts_str quoteBack_OPT  (pos:0)]
        #ALLOC: SREC: stateRec157: [Aut: 2..2:  > "white space" (pos:0)] =''
        #ALLOC: SREC: stateRec179: [REP: 3..3: PartRef_str 0 1 (pos:0) -NBL]

        #ARROW: NEXT: from=stateRec155 to=stateRec179

        #STATE: stateRec179: EXTRACT=WAITING // START, NOTREADY, WAIT, DONE_WAITING, EXTRACTED

        logLine, opType = heachToSymbol(logLine, ":")
        if opType=="MESG": logLine, opType = heachToSymbol(logLine, ":")
        if opType in ["ALLOC", "ARROW", "STATE", "PUTTING"]:
            #print("'"+opType+"'", ", '"+logLine+"'")
            parseEvent = {}
            parseEvent['opType'] = opType
            if opType=="ALLOC":
                logLine, objType  = heachToSymbol(logLine, ":"); parseEvent['objType'] = objType
                logLine, recName  = heachToSymbol(logLine, ":"); parseEvent['recName'] = recName
                logLine, prodName = heachToSymbol(logLine, ": "); parseEvent['prodName'] = prodName
                logLine = logLine[1:-1] #Remove the [ ]
                logLine, prodType  = heachToSymbol(logLine, ":"); parseEvent['prodType'] = prodType
                logLine, charRange = heachToSymbol(logLine, ":")
                charRange, originPos = heachToSymbol(charRange, "."); parseEvent['originPos'] = int(originPos)
                endPos = str(charRange[1:]); parseEvent['endPos'] = int(endPos)
                seqPos = logLine[logLine.find('pos:')+4:]
                seqPos = seqPos[:seqPos.find(')')]
                parseEvent['seqPos'] = int(seqPos)
                if prodType=='SEQ':
                    pass
                elif prodType=='ALT':
                    pass
                elif prodType=='Aut':
                    pass
                elif prodType=='REP':
                    pass


                parseEvent['eventDesc'] = ("ALLOCATED "+parseEvent['objType']+" as "+parseEvent['recName']
                                           +'  prodType:'+ parseEvent['prodType']
                                           +'  prodName:'+ parseEvent['prodName']
                                           +'  originPos:'+ str(parseEvent['originPos'])
                                           +'  endPos:'+ str(parseEvent['endPos'])
                                           +'  seqPos:'+ str(parseEvent['seqPos'])
                                           )
            elif opType=="ARROW":
                logLine, arrowType = heachToSymbol(logLine, ":"); parseEvent['arrowType'] = arrowType
                logLine, fieldID, fieldVal = heachArg(logLine); parseEvent[fieldID] = fieldVal
                #print("FOUND:"+ fieldID+"|"+fieldVal+"|")
                logLine, fieldID, fieldVal = heachArg(logLine); parseEvent[fieldID] = fieldVal

                parseEvent['eventDesc'] = "ARROW "+parseEvent['arrowType']+"  FROM:"+parseEvent['from']+" TO:"+parseEvent['to']
            elif opType=="STATE":
                parseEvent['eventDesc'] = "STATE update "
            elif opType=="PUTTING":
                parseEvent['putChars'] = logLine
                parseEvent['eventDesc'] = "PUTTING '"+parseEvent['putChars']+"'"
            self.parseEvents.append(parseEvent)
            #print(">"+parseEvent['eventDesc'])

    def drawSeqSRec(self, cr, SRec, yPos, xPos, xEnd):
        print("    DRAW_SREC:", SRec[0], SRec[1]['eventDesc'])
        opType = SRec[1]['opType']
        if opType=='ALLOC':
            cr.set_line_width(1)
            off = 0# self.SlotSpan / 2
            originPos = SRec[1]['originPos']
            endPos = SRec[1]['endPos']
            cr.set_source_rgb(0.5,0.5,0.5)
            cr.rectangle(xPos, yPos, 100, 50)
            cr.stroke()
            renderText(cr, xPos+5,yPos+3, SRec[1]['recName'], "Sans Normal 8")
            renderText(cr, xPos+5,yPos+10, SRec[1]['prodName'], "Sans Normal 8")

        elif opType=='STATE':
            pass

    def drawSRecSeqSet(self, cr, pItem, yPos):
        crntXPos = 0
        prevXPos = 0
        prevXEnd = 0
        print("DRAW_SRecSet:")
        for SRec in pItem:
            originPos = SRec[1]['originPos']
            endPos = SRec[1]['endPos']
            seqPos = SRec[1]['seqPos']
            #originPos*self.SlotSpan+off
            if originPos==endPos:
                xPos = prevXEnd
                xEnd = xPos+100
            else:
                xPos = originPos*self.SlotSpan
                xEnd = xPos+100
            self.drawSeqSRec(cr, SRec, yPos, xPos, xEnd)
            prevXPos=crntXPos
            prevXEnd=xEnd
        return(50)

    def drawSRecAltSet(self, cr, pItem, yPos):
        pass

    def drawArrow(self, pItem):
        print("DRAW_ARROW:", pItem[0], pItem[1]['eventDesc'])




    putChars = ""
    SlotSpan = 0
    maxStepsToDraw = 30

    def OnDraw(self, area, cr):
        self.maxStepsToDraw
        #print("Starting Draw:",len(self.parseEvents),"steps...")
        height = self.get_allocated_height()
        width = self.get_allocated_width()
        cr.set_source_rgb(0,0,0)
        cr.rectangle(0,0,width, height)
        cr.fill()
        cr.set_source_rgb(1, 1, 0)

        crntY = 20
        count=0
        self.putChars = ""
        self.actionSorter.resetIter()
        AllocsAndStates=[]
        Arrows = []
        print("DRAWING ALL ITEMS:")
        while self.actionSorter.crntItem!=None:
            pRecord = self.actionSorter.crntItem
            itemType = self.actionSorter.crntItemType
            if itemType=='seqSet' or itemType=='altSet':
                AllocsAndStates.append([itemType, pRecord])
            elif itemType=='arrow':
                Arrows.append(pRecord)
            elif itemType=='state':
                AllocsAndStates.append(pRecord)
            elif itemType=='PUTCHars':
                pItem = pRecord[1]
                self.putChars += pItem['putChars']
            if count > self.maxStepsToDraw: break
            self.actionSorter.goNext()
            count += 1

        # Draw Characters at the top
        self.SlotSpan = width / len(self.putChars)
        xCur = 0 #self.SlotSpan/2
        for ch in self.putChars:
            renderText(cr, xCur,crntY, ch, "Sans Normal 32")
            xCur += self.SlotSpan
        crntY += 80

        # Draw Allocs and States
        for item in AllocsAndStates:
            newHeight = 0
            if item[0]=='seqSet':
                newHeight = self.drawSRecSeqSet(cr, item[1], crntY)
            elif item[0]=='altSet':
                newHeight = self.drawSRecAltSet(cr, item, crntY)
            crntY += newHeight+10

        # Draw Arrows
        for arrow in Arrows:
            self.drawArrow(arrow)


    def loadParseLog(self, filename):
        lineNum = 0
        try:
            with open(filename) as file:
                while (line := file.readline().rstrip()):
                    lineNum += 1
                    self.addParseEvent(line)
        except IOError as err:
            fatalError(str(err))

        for pItem in self.parseEvents:
            self.actionSorter.insertPItem(pItem)
        #self.actionSorter.dump()
        #self.actionSorter.resetIter()
        #while self.actionSorter.crntItem!=None:
        #    print(">>>", self.actionSorter.crntItem[0], self.actionSorter.crntItem[1]['eventDesc'])
        #    self.actionSorter.goNext()

class Window(gtk.Window):
    def __init__(self, title="my program"):
        gtk.Window.__init__(self)
        self.set_title(title)
        self.set_default_size(1800, 800)
        self.connect("destroy", gtk.main_quit)
        self.connect('configure_event', self.OnResize)

    def OnResize(self, d, w):
        global W
        global H
        global app
        W, H = self.get_size()


win = Window(title="Earley Parse Animation")
animator = DrawingAreaFrame()
win.add(animator)
win.show_all()

animator.loadParseLog(filename)



gtk.main()

# ~ drawing_area.connect('motion-notify-event', motion_notify_event_cb)
 # ~ drawing_area.connect('button-press-event', button_press_event_cb)

 # ~ drawing_area.set_events(gdk.BUTTON_PRESS_MASK | gdk.POINTER_MOTION_MASK)


  # ~ def button_press_event_cb(widget, event):
    # ~ if event.button == 1:
      # ~ ... do something, when the first button is pressed ...
    # ~ elif event.button == 3:
      # ~ ... do something, when the third buttin is pressed ...
    # ~ return True
