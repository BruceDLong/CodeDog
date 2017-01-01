#/////////////////  Add GUI-Toolkit features using Java Swing

import progSpec
import codeDogParser

def use(objects, buildSpec, tags, platform):
    CODE="""

struct DroidView: ctxTag="Android" Platform='Java' Lang='Java' LibReq="" implMode="inherit:View" {
    me Path: GPath
    me double: cur_x
    me double: cur_y


    me void: onDraw(me Canvas: canvas) <- <%    {
        cur_x=0; cur_y=0;
        GPath.reset();
        GLOBAL.static_Global.drawAppArea_cb(this, this);
    }%>
}

struct GUI_rect{me Rect: GUI_rect}
//struct GUI_offset{their GtkAdjustment:GUI_offset}
struct GUI_item{me Object: GUI_item}
//struct GUI_menuBar{me Menu: GUI_menuBar}
//struct GUI_menu{me Menu: GUI_subMenu}
//struct GUI_menuItem{me MenuItem: GUI_menuItem}
struct GUI_canvas{me GUI_ctxt: GUI_canvas}
struct GUI_container{me LinearLayout:GUI_container}
struct GUI_frame{me LinearLayout:GUI_frame}
struct GUI_ScrollingWindow{me ScrollView: GUI_ScrollingWindow}
struct GUI_callback{me GCallback: GUI_callback}
struct GUI_MotionEvent{their GdkEventMotion: GUI_MotionEvent}
struct INK_Image{their Paint: INK_Image}      // How will the ink look?

struct GUI: {
    me LinearLayout:: drawingArea(GLOBAL.static_Global)
    me ScrollView:: vScroller(GLOBAL.static_Global)
    me HorizontalScrollView:: hScroller(GLOBAL.static_Global)

    me uint32: GUI_Init() <- <%{return(0);}%>
    me ScrollView: newScrollingWindow(me Long: A, me Long:B) <- <%{
        ScrollView vScroller = new ScrollView(GLOBAL.static_Global);
        HorizontalScrollView hScroller = new HorizontalScrollView(GLOBAL.static_Global);
        vScroller.addView(hScroller);
        LinearLayout layoutArea = new LinearLayout(GLOBAL.static_Global);
        layoutArea.setOrientation(LinearLayout.VERTICAL);
        hScroller.addView(layoutArea);
        return(vScroller);
    }%>
    me void: GUI_PopulateAndExec() <- <% {
        LinearLayout frame = new LinearLayout(GLOBAL.static_Global);
        frame.setLayoutParams(new LayoutParams(LayoutParams.MATCH_PARENT,LayoutParams.MATCH_PARENT));
//        frame.setDefaultCloseOperation(LinearLayout.EXIT_ON_CLOSE);
//        GLOBAL.static_Global.appFuncs.createAppMenu(frame);
        GLOBAL.static_Global.appFuncs.createAppArea(frame);
//        frame.setVisible(true);
    } %>

    me uint32: GUI_Run() <- <% {
        int status=0;
        GUI_PopulateAndExec();
        return(status);
    } %>
    me void: GUI_Deinit() <- {

    }
/*
    me GUI_menuItem: create_MenuItem(me GUI_menu: ParentMenu, me string: label) <- {
        me MenuItem:  menuitem <- parentMenu.add(label)
//        me GUI_menuItem: menuitem
//        menuitem <- GUI_menuItemWithLabel(label)
//        addItemToMenu(ParentMenu, menuitem)
        showWidget(menuitem)

        return(menuitem)
    }

    me GUI_menu: create_SubMenu(me GUI_menu: ParentMenu, me string: label) <- {
        me GUI_menu: subMenu
        subMenu <- GUI_menuWithLabel(label)
        addItemToMenu(ParentMenu, SubMenu)
        return(subMenu)
    }

    me SubMenu: create_TopSubMenu(me Menu: menuBar, me string: label) <- {
        me SubMenu: subMenu <- menuBar.addSubMenu(label)
        return(subMenu)
    }
*/
}

struct tm{
    me Calendar: tm
}
struct timeStringer{
    me String: time12Hour() <- <%{
        Calendar timeRec = Calendar.getInstance();
        String AmPm = "am";
        int hours = timeRec.get(Calendar.HOUR);
        //if (hours>=12) {hours = hours-12; AmPm="pm";}
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

struct GLOBAL{

    me thisApp: appFuncs
    me void: close_window() <- {
         // gtk_main_quit()
    }

    // DRAWING ROUTINES:

    me void: renderText(me GUI_ctxt: cr, me string: text, me string: fontName, me int: fontSize) <- <%{
       // cr.paint.setStyle(Style.FILL);
        cr.paint.setTextSize(fontSize);
       // cr.setFont(new Font(fontName, Font.PLAIN, (int)(fontSize*1.4)));
        cr.drawText(text, (float)cr.cur_x, (float)cr.cur_y, cr.paint);
    } %>



    me INK_Image[map string]: InkImgCache
    me void: displayImage(me GUI_ctxt: cr, me string: filename, me double: x, me double: y, me double: scale) <- <%{
     /*   BufferedImage picPtr=InkImgCache.get(filename);
        if (picPtr==null) {
            try{
                picPtr=ImageIO.read(new File(filename));
            } catch(IOException ioe){System.out.println("Cannot read image file " + ioe.getMessage()); System.exit(2);}
            InkImgCache.put(filename, picPtr);
            }
        cr.gr.drawImage(picPtr, null, 0,0);  */
    } %>


    me void: markDirtyArea(me GUI_item: widget, me int32: x, me int32: y, me int32: width, me int32: height) <- <%!%G;%>
    me long: ticksPerSec() <- <%!%G1000%>

    //me bool: drawAppArea_cb (me GUI_item: widget, me GUI_ctxt: cr) <- <%!drawAppArea_cb(me GUI_ctxt: cr)%>
}

struct GUI{
//    me void: fetchAreaToBeDrawn(me GUI_rect: area) <- <%!;%>
    me void: showWidget(me GUI_item: widget) <-  <%!%1.setVisible(true)%>
    me GUI_item: newCanvas() <- <%!%Gnew GUI_ctxt()%>
    me GUI_item: GUI_frame(me string: label) <- <%!%Gnew LinearLayout(%1)%>
    me GUI_item: GUI_menuItemWithLabel(me string: label) <- <%!%Gnew MenuItem(%1)%>
    me GUI_item: GUI_menuWithLabel(me string: label) <- <%!%Gnew Menu(%1)%>
    me void: setWidgetSize(me GUI_item: widget, me uint32: width, me uint32: height) <- <%!%G%1.setLayoutParams(new LayoutParams(%2, %3))%>
    me void: addToContainer(me GUI_container: container, me GUI_item: widget) <- <%!%G%1.addView(%2)%>
    me void: addToViewport(me GUI_container: container, me GUI_item: widget) <- <%!%G%1.addView(%2)%>
    me void: addItemToMenu(me GUI_menu: ParentMenu, me GUI_menuItem: menuitem) <- <%!%G%1.add(%2)%>
    me void: addMenuBar(me Menu: menubar) <- <%!%G%1.setJMenuBar(%2)%>
    me void: create_MenuItem()<- <%!gui.create_MenuItem(%1, %2)%>
    me SubMenu: create_TopSubMenu()<- <%!%G%1.addSubMenu(%2)%>
    me void: create_SubMenu()<- <%!%G%1.addSubMenu(%2)%>
    me void: setCallback() <- <%!%G %>
    me void: createAppMenu(me GUI_frame: frame) <- <%!me bool: onCreateOptionsMenu(Menu menubar)%>
}

struct GUI_ctxt: implMode="inherit:Canvas"{
    me Paint: paint
    me Path: GPath
    me double: cur_x
    me double: cur_y

    me none: GUI_ctxt () <- {
        Allocate(paint)
        Allocate(GPath)
    }
}

struct GUI_ctxt: ctxTag="Swing" Platform='Java' Lang='Java' LibReq="swing" implMode="inherit:Canvas" {
//    me void: reset() <- <%!GPath = new Path()%>
    me void: setRGBA(me double: red, me double: green, me double: blue, me double: alpha) <- <%!paint.setColor(Color.argb(%4, %1, %2, %3))%>
    me void: setRGB (me double: red, me double: green, me double: blue) <- <%!paint.setColor(Color.rgb(%1, %2, %3))%>
    me void: setLineWidth(me double: width) <- <%!paint.setStrokeWidth(%1)%>
    me void: moveTo(me double: x, me double: y) <- <%!%0.cur_x=%1; %0.cur_y=%2; %0.GPath.moveTo((float)(%1), (float)(%2))%>
    me void: lineTo(me double: x, me double: y) <- <%!%0.cur_x=%1; %0.cur_y=%2; %0.GPath.lineTo((float)(%1), (float)(%2))%>
    me void: moveRel(me double: dx, me double: dy) <- <%!GPath.moveTo((float)(cr.cur_x+%1), (float)(cr.cur_y+%2))%>
    me void: lineRel(me double: dx, me double: dy) <- <%!GPath.lineTo((float)(cr.cur_x+%1), (float)(cr.cur_y+%2))%>

//    me void: curveTo(me double: x1, me double: y1, me double: x2, me double: y2, me double: x3, me double: y3) <- <%!GPath.curve_to(cr, %1, %2, %3, %4, %5, %6)%>
//    me void: curveRel(me double: dx1, me double: dy1, me double: dx2, me double: dy2, me double: dx3, me double: dy3) <- <%!rel_curve_to(cr, %1, %2, %3, %4, %5, %6)%>
//    me void: paintNow() <- <%!gr.fill(cr.GPath)%>
    me void: strokeNow() <- <%!drawPath(cr.GPath, cr.paint)%>
    me void: fillNow() <- <%!drawPath(cr.GPath, cr.paint)%>
//    me void: renderFrame() <- <%!repaint()%>
}
    """

    codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )
