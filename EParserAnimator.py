#!/usr/bin/python3

import gi

gi.require_version("Gtk", "3.0")
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk as gtk
from gi.repository import Pango, PangoCairo, Gdk

import cairo
from math import pi

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

def heachBetween(line, start, end):
    stPos = line.find(start)
    edPos = line.find(end, stPos)
    heachVal = line[stPos+len(start) : edPos]
    retLine = line[:stPos] + line[edPos+len(end):]
    return(retLine, heachVal)

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
    layout.set_text(text, -1)
    #layout.set_markup(text, -1)
    cr.move_to(x,y)
    PangoCairo.show_layout(cr, layout)

def draw_rounded(cr, area, radius):
    """ draws rectangles with rounded (circular arc) corners """
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
    numSteps = 0
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

        if nState!=None: nextIDs.append(self.states[nState][0][0])
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

        if lowestValIDX==0 or lowestValIDX==1: # Reset SeqStates and altStates
            for sItem in self.crntItem:
                sItem[1]['STATES']={}

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
###    * Draw Arrows
###    * Set states and use colors
###    * Add controls:  'peview of next', etc.
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
        self.numSteps += 1
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
            self.states.append([aRecord])
        elif opType=='PUTTING':
            self.putChars.append(aRecord)
        else: self.numSteps -= 1

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

        self.scaleFactor = 1.0
        self.area.connect("draw", self.OnDraw)
        #self.area.connect('configure-event', self.on_configure)

    scaleFactor = 1.0
    parseEvents   = []
    actionSorter  = ActionSorter()
    charColWidths = []      # Store the width in pixels of each char column for drawing
    charPositions = []

    def clear(self):
        self.parseEvents = []

    def cleanNameString(self, nameStr):
        nameStr = nameStr.replace('_str', '')
        nameStr = nameStr.replace('innerInfon', 'inInf')
        nameStr = nameStr.replace('_', '.')
        nameStr = nameStr.replace('SEQ', 'seq')
        nameStr = nameStr.replace('ALT', 'alt')
        return nameStr

    AllocMap = {}  # Look up items by their stateRec#

    def addParseEvent(self, logLine):
        #ALLOC: SREC: stateRec170: PartPath_str_REP: NULL: [REP: 3..3: PartPath_str 0 0 (pos:0) -NBL]
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
                parseEvent['prodVal'] = ''
                logLine, objType  = heachToSymbol(logLine, ":"); parseEvent['objType'] = objType
                logLine, recName  = heachToSymbol(logLine, ":"); parseEvent['recName'] = recName
                logLine, prodName = heachToSymbol(logLine, ": ")
                logLine, causeName = heachToSymbol(logLine, ": "); parseEvent['causeName'] = causeName
                logLine = logLine[1:-1] #Remove the [ ]
                logLine, prodType  = heachToSymbol(logLine, ":"); parseEvent['prodType'] = prodType
                logLine, charRange = heachToSymbol(logLine, ":")
                charRange, originPos = heachToSymbol(charRange, "."); parseEvent['originPos'] = int(originPos)
                endPos = str(charRange[1:]); parseEvent['endPos'] = int(endPos)
                seqPos = logLine[logLine.find('pos:')+4:]
                seqPos = seqPos[:seqPos.find(')')]
                iSeqPos = int(seqPos)
                parseEvent['seqPos'] = iSeqPos
                if prodType=='SEQ':
                    partName = logLine[logLine.find('> ')+2:]
                    partName = partName[:partName.find(' ')]
                    if partName.startswith('(pos'): partName="END"
                elif prodType=='ALT':
                    logLine, pos = heachBetween(logLine, '(pos:', ')')
                    logLine = logLine.replace(' ','').replace('>','').replace('|',' | ')
                    if iSeqPos==0: # Any alt
                        partName = logLine
                    else:# One alt chosen
                        altItems = logLine.split('|')
                        partName = altItems[iSeqPos-1]

                elif prodType=='Aut':
                    if prodName=="'white space or C comment'": prodName='WSC'
                    elif prodName=="'a unicode identifier'":   prodName='unicodeID'
                    elif prodName=="'a quoted string with single or double quotes and escapes'":   prodName='"string"'
                    elif prodName=="'white space'":       prodName='WS'
                    elif prodName=="'a rational number'": prodName='number'
                    if int(originPos) < int(endPos):
                        parseEvent['prodVal'] = "'"+ self.finalChars[int(originPos):int(endPos)]+"'"
                    partName = 'pos:'+seqPos
                elif prodType=='REP':
                    partName = 'item# '+seqPos

                # Clean prodName and partName
                parseEvent['prodName'] = self.cleanNameString(prodName)
                parseEvent['partName'] = self.cleanNameString(partName)

                parseEvent['eventDesc'] = ("Allocated "+parseEvent['recName']+":"
                                           +'  prodType:'+ parseEvent['prodType']
                                           +'  prodName:'+ parseEvent['prodName']
                                           +'  originPos:'+ str(parseEvent['originPos'])
                                           +'  endPos:'+ str(parseEvent['endPos'])
                                           +'  seqPos:'+ str(parseEvent['seqPos'])
                                           +'  partName:'+ str(parseEvent['partName'])
                                           +'  causeName:'+ str(parseEvent['causeName'])
                                           +'  prodVal:'+ str(parseEvent['prodVal'])
                                           )
                self.AllocMap[recName] = parseEvent
            elif opType=="ARROW":
                logLine, arrowType = heachToSymbol(logLine, ":"); parseEvent['arrowType'] = arrowType
                logLine, fieldID, fieldVal = heachArg(logLine); parseEvent[fieldID] = fieldVal
                #print("FOUND:"+ fieldID+"|"+fieldVal+"|")
                logLine, fieldID, fieldVal = heachArg(logLine); parseEvent[fieldID] = fieldVal

                parseEvent['eventDesc'] = "ARROW "+parseEvent['arrowType']+"  FROM:"+parseEvent['from']+" TO:"+parseEvent['to']
            elif opType=="STATE":
                logLine, recName  = heachToSymbol(logLine, ":"); parseEvent['recName'] = recName
                logLine, fieldID, fieldVal = heachArg(logLine);
                parseEvent['fieldID'] = fieldID
                parseEvent['fieldVal'] = fieldVal
                parseEvent['eventDesc'] = "STATE: "+recName+"."+fieldID+" = "+fieldVal
                #print(">"+parseEvent['eventDesc'])
            elif opType=="PUTTING":
                self.finalChars += logLine
                parseEvent['putChars'] = logLine
                parseEvent['eventDesc'] = "PUTTING '"+parseEvent['putChars']+"'"

            self.parseEvents.append(parseEvent)
            #print(">"+parseEvent['eventDesc'])


    lastItemDesc = ''

    def drawSeqSRec(self, cr, SRec, yPos, xPos, width):
        #print("    DRAW_SREC:", SRec[0], SRec[1]['eventDesc'])
        opType = SRec[1]['opType']
        if opType=='ALLOC':
            cr.set_line_width(4)
            #print("SREC:",SRec)
            states=SRec[1]['STATES']
            SRec[1]['startXPos']=xPos+2
            SRec[1]['startYPos']=yPos
            SRec[1]['endXPos']=xPos+width-4
            SRec[1]['endYPos']=yPos+50
            originPos = SRec[1]['originPos']
            endPos = SRec[1]['endPos']
            self.lastItemDesc=SRec[1]['eventDesc']
            cr.rectangle(xPos+2, yPos, width-2, 50)
            cr.stroke_preserve()
            cr.set_line_width(1)
            if 'child' in SRec[1]: cr.set_source_rgb(0.6,0.6,0.7)
            else: cr.set_source_rgb(0.9,0.9,0.95)

            ResolveState = 'Initial'
            if 'RESOLVE_State'  in states: ResolveState=states['RESOLVE_State']
            if ResolveState=='RESOLVE': cr.set_source_rgb(0.8,0.1,0.8)

            NextState = 'INITIAL'
            ChildState= 'INITIAL'
            if 'NEXT_State'  in states: NextState=states['NEXT_State']
            if 'CHILD_State' in states: ChildState=states['CHILD_State']
            if NextState=='RELEASED' and ChildState=='RELEASED': cr.set_source_rgb(0.1,0.8,0.0)
            elif NextState=='RELEASED': cr.set_source_rgb(0.8,0.8,0.0)
            elif ChildState=='RELEASED': cr.set_source_rgb(0.7,0.7,0.9)

            cr.rectangle(xPos+2, yPos, width-2, 50)
            cr.fill()
            cr.set_source_rgb(0,0,0)
            renderText(cr, xPos+5,yPos+3, SRec[1]['recName'], "Sans Normal 8")
            renderText(cr, xPos+5,yPos+13, SRec[1]['prodName'], "Sans Normal 8")
            renderText(cr, xPos+5,yPos+23, SRec[1]['partName'], "Sans Normal 8")
            renderText(cr, xPos+5,yPos+33, SRec[1]['prodVal'], "Sans Normal 8")
            cr.stroke()

    def drawSRecSeqSet(self, cr, pItem, xPos, yPos):
        #print("DRAW_SEQSet:")
        prevXEnd = xPos
        startXPos = prevXEnd
        parent    = pItem[1][0][1]['causeName']
        originPos = pItem[1][0][1]['originPos']
        self.charPositions[originPos] = min(self.charPositions[originPos], xPos)
        count=0
        for SRec in pItem[1]:
            #print('COUNTS:', SRec[0], ' / ',self.maxStepsToDraw )
            if SRec[0]>self.maxStepsToDraw: break
            startXPos = prevXEnd
            parent    = SRec[1]['causeName']
            if prevXEnd==xPos and parent!='NULL' and 'startXPos' in self.AllocMap[parent]:
                startXPos = max(startXPos, self.AllocMap[parent]['startXPos'])
            #originPos = SRec[1]['originPos']
            endPos    = SRec[1]['endPos']
            seqPos    = SRec[1]['seqPos']
            #originPos*self.SlotSpan+off:

            width =SRec[1]['pixWidth']

            if pItem[0]=='seqSet': cr.set_source_rgb(0,0,0)
            elif pItem[0]=='altSet': cr.set_source_rgb(1.0,0.3,0.0)
            self.drawSeqSRec(cr, SRec, yPos, startXPos, width)
            prevXEnd = startXPos + width
            count += 1
        return(count, 50)


    def drawFlatCurvedArrow(self, cr, xStart, xEnd, yPos):
        cr.save()
        width  = xEnd-xStart
        height = width/20
        if xStart<xEnd: height += 14
        else: height -= 14
        xCenter = xStart+(width/2)
        cr.translate(xCenter, yPos)
        cr.scale(abs(width)/2.0, height/2.0)
        cr.arc(0, 0, 1, pi, 2*pi)
        cr.restore()
        cr.stroke()

    def drawArrow(self, cr, pItem):
        arrow=pItem[1]
        fromArw = arrow['from']
        toArw   = arrow['to']
        arrowType = arrow['arrowType']
        #print("DRAW_ARROW:", arrowType, fromArw, toArw)
        if fromArw=='NULL': return
        if not(fromArw in self.AllocMap):
            print('Node',fromArw, 'has an arrow but is not allocated.')
            return

        arrowFrom = self.AllocMap[fromArw]
        fromXPosS=arrowFrom['startXPos']
        fromYPosS=arrowFrom['startYPos']
        fromXPosE=arrowFrom['endXPos']
        fromYPosE=arrowFrom['endYPos']

        if toArw!='NULL':
            arrowTo   = self.AllocMap[toArw]
            toXPosS  =arrowTo['startXPos']
            toYPosS  =arrowTo['startYPos']
            toXPosE  =arrowTo['endXPos']
            toYPosE  =arrowTo['endYPos']
        #print("COORDS:", fromXPos, toXPos, fromYPos, toYPos)
        cr.set_source_rgb(0,0,0)
        if arrowType=='NEXT':
            cr.set_source_rgb(1.0,0,0)
            if(toArw=='NULL' or (fromYPosE==toYPosE and (abs(fromXPosE-toXPosS)<30))):
                cr.arc(fromXPosE+3, fromYPosS, 16, pi, 0.0)
                cr.rel_line_to(-5, -5)
                cr.rel_move_to(5, 5)
                cr.rel_line_to(5, -5)
                if toArw=='NULL': renderText(cr, fromXPosE+8, fromYPosS+1, 'NULL', "Sans Normal 7")
                renderText(cr, fromXPosE-8, fromYPosS-13, 'next', "Sans Normal 6")
            else: # items aren't inline with each other
                frmX = fromXPosE-7
                toX  = toXPosS +7
                yPos = fromYPosS
                self.drawFlatCurvedArrow(cr, frmX, toX, yPos)
                cr.move_to(toX, yPos)
                cr.rel_line_to(-5, -5)
                cr.rel_move_to(5, 5)
                cr.rel_line_to(5, -5)
                cr.stroke()
                txtX = toX-5
                txty = yPos - 16
                renderText(cr, txtX, txty, 'next', "Sans Normal 6")
        elif arrowType=='PRED':
            cr.set_source_rgb(1.0,0,1.0)
            if(toArw=='NULL' or (fromYPosE==toYPosE and (abs(toXPosE-fromXPosS)<30))):
                cr.arc(fromXPosS+3, fromYPosE, 16, 0.0, pi)
                cr.rel_line_to(-5, 5)
                cr.rel_move_to(5, -5)
                cr.rel_line_to(5, 5)
                if toArw=='NULL': renderText(cr, fromXPosS-8, fromYPosE-1, 'NULL', "Sans Normal 7")
                renderText(cr, fromXPosS+8, fromYPosE+13, 'pred', "Sans Normal 6")
            else: # items aren't inline with each other
                frmX = fromXPosS+7
                toX  = toXPosE -7
                yPos = fromYPosE
                self.drawFlatCurvedArrow(cr, frmX, toX, yPos)
                cr.move_to(toX, yPos)
                cr.rel_line_to(-5, 5)
                cr.rel_move_to(5, -5)
                cr.rel_line_to(5, 5)
                cr.stroke()
                txtX = toX-12
                txty = yPos - 16
                renderText(cr, txtX, txty, 'pred', "Sans Normal 6")

        elif arrowType=='CHILD':
            arrowFrom['child']=arrowTo
            cr.set_source_rgb(0.2,0.8,0.2)
            toX  = toXPosS+((toXPosE-toXPosS)/2)  -3
            if abs(fromXPosS-toXPosS)<10:
                  frmX = toX+20
            else: frmX = fromXPosS + ((fromXPosE-fromXPosS)/2)-20 -3
            cr.move_to(frmX, fromYPosE)
            cr.line_to(toX, toYPosS)
            cr.rel_line_to(-5, -5)
            cr.rel_move_to(5, 5)
            cr.rel_line_to(5, -5)
            txtX = frmX+((toX - frmX)/2)
            txty = fromYPosE + ((toYPosS - fromYPosE)/2)
            renderText(cr, txtX+3, txty+5, 'child', "Sans Normal 6")
        elif arrowType=='CAUSE':
            cr.set_source_rgb(0,0,1.0)
            frmX = fromXPosS + ((fromXPosE-fromXPosS)/2)  +3
            if abs(fromXPosS-toXPosS)<10:
                  toX =frmX+20
            else: toX = toXPosS+((toXPosE-toXPosS)/2)-20   +3
            cr.move_to(frmX, fromYPosS)
            cr.line_to(toX, toYPosE)
            cr.rel_line_to(-5, 5)
            cr.rel_move_to(5, -5)
            cr.rel_line_to(5, 5)
            txtX = frmX+((toX - frmX)/2)
            txty = fromYPosS + ((toYPosE - fromYPosS)/2)
            renderText(cr, txtX+3, txty-5, 'cause', "Sans Normal 6")
        cr.stroke()



    putChars = ""
    finalChars = ''
    SlotSpan = 0
    maxStepsToDraw = 2
    allocsToDo = 0

    def OnDraw(self, area, cr):
        self.set_size_request(10000, 5000)
        #print("Starting Draw:",len(self.parseEvents),"steps...")
        height = self.get_allocated_height()
        width = self.get_allocated_width()
        cr.set_source_rgb(1,1,1)
        cr.rectangle(0,0,width, height)
        cr.fill()
        cr.set_source_rgb(1,1,1)

        crntY = 20
        allocCount=0
        putCount = 0
        self.putChars = ""
        Allocs=[]
        Arrows = []
        States = []
        #print("DRAWING ALL ITEMS:")
        refToLastStepDone=None
        self.actionSorter.resetIter()
        while self.actionSorter.crntItem!=None:
            pRecord = self.actionSorter.crntItem
            itemType = self.actionSorter.crntItemType
            #print('RECORD:',pRecord)
            if itemType=='seqSet' or itemType=='altSet':
                if pRecord[0][0]<=self.maxStepsToDraw:
                    Allocs.append([itemType, pRecord])
                    refToLastStepDone="ALLOC"
                allocCount += 1
            elif itemType=='arrow':
                if pRecord[0]<=self.maxStepsToDraw:
                    Arrows.append(pRecord)
                    refToLastStepDone = pRecord[1]['eventDesc']
            elif itemType=='state':
                if pRecord[0][0]<=self.maxStepsToDraw:
                    States.append([itemType, pRecord])
                    refToLastStepDone = pRecord[0][1]['eventDesc']+':'
            elif itemType=='PUTCHars':
                putCount += 1
                pItem = pRecord[1]
                self.putChars += pItem['putChars']
                refToLastStepDone = pRecord[1]['eventDesc']
            #print("ITEM#", allocCount, ':', itemType, 'maxSteps:', self.maxStepsToDraw)
            if allocCount > self.maxStepsToDraw: break # TODO: This condition goes too far
            self.actionSorter.goNext()

        # Calculate column widths and positions
        CharsPut = self.putChars+'x'
        self.SlotSpan = (width-10) / len(CharsPut)
        for ch in CharsPut: self.charColWidths.append(self.SlotSpan)
        for ch in CharsPut: self.charPositions.append(9999999)


        cr.scale(self.scaleFactor, self.scaleFactor)
        # ~ # Draw Characters at the top
        # ~ xCur = 5
        # ~ for ch in CharsPut:
            # ~ renderText(cr, xCur,crntY, ch, "Sans Normal 32")
            # ~ xCur += self.SlotSpan
        crntY += 80
        inrY = crntY
        # Draw Allocs and States
        for state in States:
            itmMap = state[1][0][1]
            objID=itmMap['recName']
            if not(objID in self.AllocMap):
                print('Node',objID, "has a STATE but isn't allocated.")
                continue
            obj  = self.AllocMap[objID]
            obj['STATES'][itmMap['fieldID']] = itmMap['fieldVal']
            #print("OBJ:",obj)
        oldStartX = 5
        oldOrigin = 0
        stepsDone = 0
        self.allocsToDo= self.maxStepsToDraw-(len(Arrows) + putCount)
        for item in Allocs:
            itmMap = item[1][0][1]
            opType = itmMap['opType']
            if opType=='ALLOC':
                parent   = itmMap['causeName']
                orignPos = itmMap['originPos']
                if parent!='NULL':
                    if 'startXPos' in self.AllocMap[parent]:
                        startXPos =self.AllocMap[parent]['startXPos']
                        startYPos =self.AllocMap[parent]['startYPos']
                    else: startXPos=oldStartX; print("START_X_POS Not Found:", parent)
                else: startXPos=oldStartX
                if orignPos != oldOrigin: inrY = startYPos+60
                newHeight = 0
                #print("DOING SEQ:", str(item)[:50])
                count, newHeight = self.drawSRecSeqSet(cr, item, startXPos, inrY)
                inrY += newHeight+10
                stepsDone += count
                #if stepsDone >= self.allocsToDo: print("OVERMAX"); break
                oldStartX = startXPos
                oldOrigin = orignPos


        # Draw Arrows
        for arrow in Arrows:
            self.drawArrow(cr, arrow)

        # Draw Characters at the top
        xCur = 5
        crntY = 20
        pos = 0
        cr.set_source_rgb(0,0,0)
        for ch in CharsPut:
            renderText(cr, self.charPositions[pos]+5 ,crntY, ch, "Sans Normal 32")
            xCur += self.SlotSpan
            pos += 1
        cr.set_source_rgb(0,0,1.0)
        if refToLastStepDone=='ALLOC': refToLastStepDone=self.lastItemDesc[:self.lastItemDesc.find(':')]
        if refToLastStepDone==None: refToLastStepDone='Beginning:'
        renderText(cr, 20 ,20, "   Step:"+str(animator.maxStepsToDraw)+" / "+str(self.actionSorter.numSteps)+": "+refToLastStepDone, "Sans Normal 24")
        print("CrntStep:", refToLastStepDone)
        crntY += 80



    def loadParseLog(self, filename):
        lineNum = 0
        try:
            with open(filename) as file:
                while (line := file.readline()):
                    line = line.rstrip()
                    lineNum += 1
                    self.addParseEvent(line)
        except IOError as err:
            fatalError(str(err))

        for pItem in self.parseEvents:
            self.actionSorter.insertPItem(pItem)

        actionItems =  []
        self.actionSorter.resetIter()
        while self.actionSorter.crntItem!=None:
            pRecord = self.actionSorter.crntItem
            itemType = self.actionSorter.crntItemType
            if itemType=='seqSet' or itemType=='altSet':
                actionItems.append([itemType, pRecord])
                # ~ print("$$",itemType)
                # ~ for itm in pRecord:
                    # ~ print("    >",itm)
            self.actionSorter.goNext()

        print("Back sizing...")
        for aItem in reversed(actionItems):
            if aItem[0]=='seqSet' or aItem[0]=='altSet':
                rec = aItem[1][0][1]
                #print("#"+str(aItem))
                S="SEQSET: "
                colNum=rec['originPos']
                minParentWidth = 0
                S+="@startPos:"+str(colNum)+"  "+rec['prodName']+": ["
                parentRecID = rec['causeName']
                for subItem in aItem[1]:
                    item = subItem[1]
                    if not 'pixWidth' in item: item['pixWidth']=100
                    minParentWidth += item['pixWidth']
                    #isNull = item['originPos']==item['endPos']
                    #if isNull
                    S+=item['partName']+'('+str(item['pixWidth'])+')  '
                if parentRecID!='NULL':
                    parentRec = self.AllocMap[parentRecID]
                    if not 'pixWidth' in parentRec: parentRec['pixWidth']=100
                    #print('CHILD:',rec['recName'],', parent:',parentRec['recName'])
                    parentRec['pixWidth']=max(minParentWidth, parentRec['pixWidth'])
                    S += '('+str(parentRec['pixWidth'])+')'

            #elif aItem[0]=='altSet':
            #print("%"+S+"]")
        print("Total Steps:", self.actionSorter.numSteps)
        #exit(0)

class Window(gtk.Window):
    viewPort = gtk.Viewport()
    def __init__(self, title="my program"):
        gtk.Window.__init__(self)
        scrollWin=gtk.ScrolledWindow()
        #viewPort =gtk.Viewport()
        scrollWin.add(self.viewPort)
        #viewPort.add()
        self.add(scrollWin)
        self.set_title(title)
        self.set_default_size(1800, 800)
        self.connect("destroy", gtk.main_quit)
        self.connect('configure_event', self.OnResize)
        self.connect("key-press-event",self.on_key_press_event)

    def OnResize(self, d, w):
        global W
        global H
        global app
        W, H = self.get_size()

    def on_key_press_event(self, widget, event):
        global animator
        #print("Key press on widget: ", widget)
        #print("          Modifiers: ", event.state)
        #print("      Key val, name: ", event.keyval, Gdk.keyval_name(event.keyval))
        keyName = Gdk.keyval_name(event.keyval)
        # check the event modifiers (can also use SHIFTMASK, etc)
        #ctrl = (event.state & Gdk.ModifierType.CONTROL_MASK)

        # see if we recognise a keypress
        #if ctrl and event.keyval == Gdk.KEY_h:
        crntScale = animator.scaleFactor
        steps = animator.maxStepsToDraw
        if keyName=='Down': animator.scaleFactor = max(crntScale-0.05, 0.05); animator.queue_draw()
        elif keyName=='Up': animator.scaleFactor = min(crntScale+0.05, 5.0); animator.queue_draw()
        elif keyName=='Left':  animator.maxStepsToDraw = max(steps-1, 1); animator.queue_draw()
        elif keyName=='Right': animator.maxStepsToDraw = min(steps+1, animator.actionSorter.numSteps); animator.queue_draw()
        elif keyName=='End':  animator.maxStepsToDraw = animator.actionSorter.numSteps; animator.queue_draw(); return True
        elif keyName=='Home': animator.maxStepsToDraw = 2; animator.queue_draw()
        #print("STEP:", animator.maxStepsToDraw,'/', animator.actionSorter.numSteps)


win = Window(title="Earley Parse Animation")
animator = DrawingAreaFrame()
win.viewPort.add(animator)
win.show_all()

animator.loadParseLog(filename)



gtk.main()

