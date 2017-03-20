#/////////////////  Add GUI-Toolkit features using Java Swing

import progSpec
import codeDogParser

def use(objects, buildSpec, tags, platform):
    CODE="""


struct JavaGUI_ctxt: ctxTag="Swing" Platform='Java' Lang='Java' LibReq="swing" implMode="inherit:JPanel" {
    their Graphics2D: gr
    me GeneralPath: GPath
    me double: cur_x
    me double: cur_y


    me void: paintComponent(me Graphics: g) <- <%    {
        super.paintComponent(g);
        this.addMouseListener(new CustomMouseListener());
        this.addMouseMotionListener(new CustomMouseMotionListener());
        GPath.reset();
        gr=(Graphics2D)(g);
        GLOBAL.static_Global.drawAppArea_cb(this, this);
    }%>
}

struct CustomMouseListener: ctxTag="Swing" Platform='Java' Lang='Java' LibReq="swing" implMode="implement:MouseListener" {
    me void: mouseClicked(me MouseEvent: e)<-     {
        me float: eventX <- e.getX()
        me float: eventY <- e.getY()
    }
    me void: mousePressed(me MouseEvent: e)<-     {
        me float: eventX <- e.getX()
        me float: eventY <- e.getY()
        /-GLOBAL.static_Global.appFuncs.gui.pointerDown(GLOBAL.static_Global.drawing_area, eventX, eventY)
    }
    me void: mouseReleased(me MouseEvent: e)<-     {
        me float: eventX <- e.getX()
        me float: eventY <- e.getY()
    }
    me void: mouseEntered(me MouseEvent: e)<-     {
        me float: eventX <- e.getX()
        me float: eventY <- e.getY()
    }
    me void: mouseExited(me MouseEvent: e)<-     {
        me float: eventX <- e.getX()
        me float: eventY <- e.getY()
    }
}

struct CustomMouseMotionListener: ctxTag="Swing" Platform='Java' Lang='Java' LibReq="swing" implMode="implement:MouseMotionListener" {
    me void: mouseMoved(me MouseEvent: e)<-     {
        me float: eventX <- e.getX()
        me float: eventY <- e.getY()
    }
    me void: mouseDragged(me MouseEvent: e)<-     {
        me float: eventX <- e.getX()
        me float: eventY <- e.getY()
    }
}

struct GUI_ctxt{their JavaGUI_ctxt:GUI_ctxt}
struct GUI_rect{me double: x1 me double: y1 me double: x2 me double: y2}
struct GUI_offset{their GtkAdjustment:GUI_offset}
struct GUI_item{me Object: GUI_item}
struct GUI_menuBar{me JMenuBar: GUI_menuBar}
struct GUI_menu{me JMenu: GUI_menu}
struct GUI_menuItem{me JMenuItem: GUI_menuItem}
struct GUI_canvas{me JavaGUI_ctxt: GUI_canvas}
struct GUI_container{me JFrame:GUI_container}
struct GUI_frame{me JFrame:GUI_frame}
struct GUI_ScrollingWindow{me JScrollPane: GUI_ScrollingWindow}
struct GUI_callback{me GCallback: GUI_callback}
struct GUI_MotionEvent{their GdkEventMotion: GUI_MotionEvent}
struct GUI {
    me uint32: GUI_Init() <- <%{return(0);}%>

    me void: GUI_PopulateAndExec() <- <% {
        JFrame frame = new JFrame(title);
        frame.setSize(1000, 700);
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        GLOBAL.static_Global.appFuncs.createAppMenu(frame);
        GLOBAL.static_Global.appFuncs.createAppArea(frame);
        frame.setVisible(true);
    } %>

    me uint32: GUI_Run() <- <% {
        int status=0;
        javax.swing.SwingUtilities.invokeLater(new Runnable() {
            public void run() {
                GUI_PopulateAndExec();
            }
        });

        return(status);
    } %>
    me void: GUI_Deinit() <- {

    }

    me GUI_menuItem: create_MenuItem(me GUI_menu: ParentMenu, me string: label) <- {
        me GUI_menuItem: menuitem
        menuitem <- GUI_menuItemWithLabel(label)
        addItemToMenu(ParentMenu, menuitem)
        showWidget(menuitem)

        return(menuitem)
    }

    me GUI_menu: create_SubMenu(me GUI_menu: ParentMenu, me string: label) <- {
        me GUI_menu: SubMenu
        SubMenu <- GUI_menuWithLabel(label)
        addItemToMenu(ParentMenu, SubMenu)
        return(SubMenu)
    }

    me GUI_menu: create_TopSubMenu(me GUI_menuBar: ParentMenu, me string: label) <- {
        me GUI_menu: SubMenu
        SubMenu <- GUI_menuWithLabel(label)
        addItemToMenu(ParentMenu, SubMenu)
        return(SubMenu)
    }
}

struct tm{
    me Calendar: tm
}
struct timeStringer{
    me String: time12Hour() <- <%{
        Calendar timeRec = Calendar.getInstance();
        String AmPm = "am";
        int hours = timeRec.get(Calendar.HOUR);
        /-if (hours>=12) {hours = hours-12; AmPm="pm";}
        if (timeRec.get(Calendar.AM_PM)==Calendar.PM){AmPm="pm";}
        if (hours==0) {hours = 12;}
        String SH = (Integer.toString(hours)+":");
        int min = timeRec.get(Calendar.MINUTE);
        if (min<10){SH = SH+"0";}
        SH = SH + Integer.toString(min);

        SH=SH+":";
        int sec = timeRec.get(Calendar.SECOND);
        if (sec<10){SH = SH+"0";}
        SH = SH + Integer.toString(sec);
        SH=SH+AmPm;
        return(SH);
    } %>
}


struct INK_Image{me BufferedImage: INK_Image}
struct GLOBAL{

    me thisApp: appFuncs

    /- DRAWING ROUTINES:

    me void: renderText(me GUI_ctxt: cr, me string: text, me string: fontName, me int: fontSize, me int: x, me int: y) <- <%{
        cr.gr.setFont(new Font(fontName, Font.PLAIN, (int)(fontSize*1.4)));
        cr.gr.drawString(text, x, y);
    } %>



    me INK_Image[map string]: InkImgCache
    me void: displayImage(me GUI_ctxt: cr, me string: filename, me double: x, me double: y, me double: scale) <- <%{
        filename = "assets/" + filename;
        BufferedImage picPtr=InkImgCache.get(filename);
        if (picPtr==null) {
            try{
                picPtr=ImageIO.read(new File(filename));
            } catch(IOException ioe){System.out.println("Cannot read image file " + ioe.getMessage()); System.exit(2);}
            InkImgCache.put(filename, picPtr);
            }
        cr.gr.drawImage(picPtr, null, 0,0);
    } %>

    me void: close_window() <- {
         /- gtk_main_quit()
    }
    me void: markDirtyArea(me GUI_item: widget, me int32: x, me int32: y, me int32: width, me int32: height) <- <%!%G%1.repaint(%2, %3, %4, %5)%>
    me long: ticksPerSec() <- <%!%G1000%>
    me void: copyAssetToWritableFolder(me string: fromPath, me string: toPath)<- <%{
        /-TODO finish this if need to package swing build
    }%>
    me string: getFilesDirAsString()<- <%{
        String s = Paths.get(".").toAbsolutePath().normalize().toString();
        System.out.println("Current relative path is: " + s);
        return s;
    }%>
}

struct GUI{
    me void: fetchAreaToBeDrawn(me GUI_rect: area) <- <%!;%>
    me void: showWidget(me GUI_item: widget) <-  <%!%1.setVisible(true)%>
    me GUI_item: newCanvas() <- <%!%Gnew JavaGUI_ctxt()%>
    me GUI_item: GUI_frame(me string: label) <- <%!%Gnew JFrame(%1)%>
    me GUI_item: GUI_menuItemWithLabel(me string: label) <- <%!%Gnew JMenuItem(%1)%>
    me GUI_item: GUI_menuWithLabel(me string: label) <- <%!%Gnew JMenu(%1)%>
    me void: setWidgetSize(me GUI_item: widget, me uint32: width, me uint32: height) <- <%!%G%1.setPreferredSize(new Dimension(%2, %3))%>
    me GUI_offset: newGUI_offset(me double: value, me double: upper, me double: lower, me double: step_increment, me double: page_increment, me double: page_size) <- <%!gtk_adjustment_new(%1, %2, %3, %4, %5, %6)%>
    me GUI_item: newScrollingWindow() <- <%!%Gnew JScrollPane()%>
    me GUI_item: newViewport(me GUI_offset: H_Offset, me GUI_offset: V_Offset) <- <%!gtk_viewport_new(%1, %2)%>
    me void: addToContainer(me GUI_container: container, me GUI_item: widget) <- <%!%G%1.add(%2)%>
    me void: addToViewport(me GUI_container: container, me GUI_item: widget) <- <%!%G%1.setViewportView(%2)%>
    me void: addItemToMenu(me GUI_menu: ParentMenu, me GUI_menuItem: menuitem) <- <%!%G%1.add(%2)%>
    me void: addMenuBar(me GUI_menuBar: menubar) <- <%!%G%1.setJMenuBar(%2)%>
    me void: create_MenuItem()<- <%!gui.create_MenuItem(%1, %2)%>
    me void: create_TopSubMenu()<- <%!gui.create_TopSubMenu(%1, %2)%>
    me void: create_SubMenu()<- <%!gui.create_SubMenu(%1, %2)%>
    me void: setCallback() <- <%!%G %>
}

struct GUI_ctxt: ctxTag="Swing" Platform='Java' Lang='Java' LibReq="swing" implMode="inherit:JPanel" {
    me void: reset() <- <%!GPath = new GeneralPath()%>
    me void: setRGBA(me double: red, me double: green, me double: blue, me double: alpha) <- <%!gr.setColor(new Color(%1, %2, %3, %4))%>
    me void: setRGB (me double: red, me double: green, me double: blue) <- <%!gr.setColor(new Color(%1, %2, %3))%>
    me void: setLineWidth(me double: width) <- <%!gr.setStroke(new BasicStroke(%1))%>
    me void: moveTo(me double: x, me double: y) <- <%!%0.cur_x=%1; %0.cur_y=%2; %0.GPath.moveTo(%1, %2)%>
    me void: lineTo(me double: x, me double: y) <- <%!%0.cur_x=%1; %0.cur_y=%2; %0.GPath.lineTo(%1, %2)%>
    me void: moveRel(me double: dx, me double: dy) <- <%!GPath.moveTo(cr.cur_x+%1, cr.cur_y+%2)%>
    me void: lineRel(me double: dx, me double: dy) <- <%!GPath.lineTo(cr.cur_x+%1, cr.cur_y+%2)%>
    me void: curveTo(me double: x1, me double: y1, me double: x2, me double: y2, me double: x3, me double: y3) <- <%!GPath.curve_to(cr, %1, %2, %3, %4, %5, %6)%>
    me void: curveRel(me double: dx1, me double: dy1, me double: dx2, me double: dy2, me double: dx3, me double: dy3) <- <%!rel_curve_to(cr, %1, %2, %3, %4, %5, %6)%>
    me void: paintNow() <- <%!gr.fill(cr.GPath)%>
    me void: strokeNow() <- <%!gr.draw(cr.GPath)%>
    me void: fillNow() <- <%!gr.fill(cr.GPath)%>
    me void: renderFrame() <- <%!repaint()%>
}
    """

    codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )
