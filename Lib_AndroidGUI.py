#/////////////////  Add GUI-Toolkit features using Java Swing

import progSpec
import codeDogParser

def use(objects, buildSpec, tags, platform):
    CODE="""
struct CanvasView: ctxTag="Swing" Platform='Java' Lang='Java' LibReq="swing" implMode="inherit:View" {
    me double: cur_x
    me double: cur_y
    me GUI_ctxt: xCanvas
    
    me none: CanvasView(me Context: context ) <- <%{
        super(context);
    }%>
    
    me none: CanvasView() <- <%{
        super(GLOBAL.static_Global);
    }%>

    me void: onDraw(me Canvas: canvas) <- <%{
        xCanvas = new GUI_ctxt(canvas);
        //GLOBAL.drawAppArea_cb(xCanvas);
    }%>
}

struct thisApp {
    me none: thisApp() <- <%{}%>
    
    //me void: createAppArea(me LinearLayout: frame) <- <%{
        //ScrollView scroller = GLOBAL.static_Global.appFuncs.gui.vScroller;
    //}%>
}

//struct GUI_rect{me double: x1 me double: y1 me double: x2 me double: y2}
//struct GUI_offset{their GtkAdjustment:GUI_offset}
struct GUI_item{me Object: GUI_item}
//struct GUI_menuBar{me Menu: GUI_menuBar}
//struct GUI_menu{me Menu: GUI_subMenu}
//struct GUI_menuItem{me MenuItem: GUI_menuItem}
struct GUI_canvas{me CanvasView: GUI_canvas}
struct GUI_container{me LinearLayout:GUI_container}
struct GUI_frame{me LinearLayout:GUI_frame}
struct GUI_ScrollingWindow{me ScrollView: GUI_ScrollingWindow}
struct GUI_callback{me GCallback: GUI_callback}
struct GUI_MotionEvent{their GdkEventMotion: GUI_MotionEvent}
struct GUI: {
    me LinearLayout: drawingArea
    me ScrollView: vScroller
    me HorizontalScrollView: hScroller
    
    me uint32: GUI_Init() <- <%{return(0);}%>
    me ScrollView: newScrollingWindow(me Context: cr) <- <%{
        ScrollView vScroller = new ScrollView(cr);
        HorizontalScrollView hScroller = new HorizontalScrollView(cr);
        vScroller.addView(hScroller);
        LinearLayout layoutArea = new LinearLayout(cr);
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
struct GLOBAL{

    me thisApp: appFuncs <- Allocate(thisApp)
    me void: close_window() <- {
         // gtk_main_quit()
    }
    me void: markDirtyArea(me GUI_item: widget, me int32: x, me int32: y, me int32: width, me int32: height) <- <%!%G%1.invalidate(%2, %3, %4, %5)%>
    me long: ticksPerSec() <- <%!%G1000%>
    
    //me bool: drawAppArea_cb (me GUI_item: widget, me GUI_ctxt: cr) <- <%!drawAppArea_cb(me GUI_ctxt: cr)%>
}

struct GUI{
//    me void: fetchAreaToBeDrawn(me GUI_rect: area) <- <%!;%>
    me void: showWidget(me GUI_item: widget) <-  <%!%1.setVisible(true)%>
    me GUI_item: newCanvas() <- <%!%Gnew CanvasView(GLOBAL.static_Global)%>
    me GUI_item: GUI_frame(me string: label) <- <%!%Gnew LinearLayout(%1)%>
    me GUI_item: GUI_menuItemWithLabel(me string: label) <- <%!%Gnew MenuItem(%1)%>
    me GUI_item: GUI_menuWithLabel(me string: label) <- <%!%Gnew Menu(%1)%>
    me void: setWidgetSize(me GUI_item: widget, me uint32: width, me uint32: height) <- <%!%G%1.setLayoutParams(new LayoutParams(%2, %3))%>
//    me GUI_offset: newGUI_offset(me double: value, me double: upper, me double: lower, me double: step_increment, me double: page_increment, me double: page_size) <- <%!gtk_adjustment_new(%1, %2, %3, %4, %5, %6)%>
//    me GUI_item: newScrollingWindow() <- <%!%newScrollingWindow(GLOBAL.static_Global)%>
//    me GUI_item: newViewport(me GUI_offset: H_Offset, me GUI_offset: V_Offset) <- <%!gtk_viewport_new(%1, %2)%>
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
    me Canvas: Gcanvas
    me Paint: paint
    me Path: GPath
    
    me none: GUI_ctxt () <- {}
    
    me none: GUI_ctxt (me Canvas: canvas) <- {
        Gcanvas <- canvas
        Allocate(paint)
        Allocate(GPath) 
    }
}

struct GUI_ctxt: ctxTag="Swing" Platform='Java' Lang='Java' LibReq="swing" implMode="inherit:Canvas" {
//    me void: reset() <- <%!GPath = new Path()%>
    me void: setRGBA(me double: red, me double: green, me double: blue, me double: alpha) <- <%!paint.setColor(Color.rgba(%1, %2, %3, %4))%>
    me void: setRGB (me double: red, me double: green, me double: blue) <- <%!paint.setColor(Color.rgb(%1, %2, %3))%>
    me void: setLineWidth(me double: width) <- <%!paint.setStrokeWidth(%1)%>
    me void: moveTo(me double: x, me double: y) <- <%!GPath.moveTo(%1, %2)%>
    me void: lineTo(me double: x, me double: y) <- <%!GPath.lineTo((float)(%1), (float)(%2))%>
//    me void: moveRel(me double: dx, me double: dy) <- <%!GPath.moveTo(cr.cur_x+%1, cr.cur_y+%2)%>
//    me void: lineRel(me double: dx, me double: dy) <- <%!GPath.lineTo(cr.cur_x+%1, cr.cur_y+%2)%>
//    me void: curveTo(me double: x1, me double: y1, me double: x2, me double: y2, me double: x3, me double: y3) <- <%!GPath.curve_to(cr, %1, %2, %3, %4, %5, %6)%>
//    me void: curveRel(me double: dx1, me double: dy1, me double: dx2, me double: dy2, me double: dx3, me double: dy3) <- <%!rel_curve_to(cr, %1, %2, %3, %4, %5, %6)%>
//    me void: paintNow() <- <%!gr.fill(cr.GPath)%>
    me void: strokeNow() <- <%!Gcanvas.drawPath(cr.GPath, cr.paint)%>
//    me void: renderFrame() <- <%!repaint()%>
}
    """

    codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )
