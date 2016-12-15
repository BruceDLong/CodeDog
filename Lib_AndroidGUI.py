#/////////////////  Add GUI-Toolkit features using Java Swing

import progSpec
import codeDogParser

def use(objects, buildSpec, tags, platform):
    CODE="""
struct CanvasView: ctxTag="Swing" Platform='Java' Lang='Java' LibReq="swing" implMode="inherit:View" {
    me Path: GPath
    me double: cur_x
    me double: cur_y


    me void: onDraw(me Canvas: canvas) <- <%    {
        GLOBAL.static_Global.drawAppArea_cb(canvas);
    }%>
}
struct GUI_ctxt{their CanvasView:GUI_ctxt}
struct GUI_rect{me double: x1 me double: y1 me double: x2 me double: y2}
struct GUI_offset{their GtkAdjustment:GUI_offset}
struct GUI_item{me Object: GUI_item}
struct GUI_menuBar{me Menu: GUI_menuBar}
struct GUI_menu{me Menu: GUI_menu}
struct GUI_menuItem{me MenuItem: GUI_menuItem}
struct GUI_canvas{me CanvasView: GUI_canvas}
struct GUI_container{me LinearLayout:GUI_container}
struct GUI_frame{me LinearLayout:GUI_frame}
struct GUI_ScrollingWindow{me JScrollPane: GUI_ScrollingWindow}
struct GUI_callback{me GCallback: GUI_callback}
struct GUI_MotionEvent{their GdkEventMotion: GUI_MotionEvent}
struct GUI {
    me uint32: GUI_Init() <- <%{return(0);}%>

    me void: GUI_PopulateAndExec() <- <% {
        LinearLayout frame = new LinearLayout(title);
        frame.setSize(500, 700);
        frame.setDefaultCloseOperation(LinearLayout.EXIT_ON_CLOSE);
//        GLOBAL.static_Global.appFuncs.createAppMenu(frame);
        GLOBAL.static_Global.appFuncs.createAppArea(frame);
        frame.setVisible(true);
    } %>

    me uint32: GUI_Run() <- <% {
        int status=0;
//        javax.swing.SwingUtilities.invokeLater(new Runnable() {
//            public void run() {
//                GUI_PopulateAndExec();
//            }
//        });

        return(status);
    } %>
    me void: GUI_Deinit() <- {

    }

    me GUI_menuItem: create_MenuItem(me GUI_menu: ParentMenu, me string: label) <- {
        me MenuItem:  menuitem <- parentMenu.add(label)
//        me GUI_menuItem: menuitem
//        menuitem <- GUI_menuItemWithLabel(label)
//        addItemToMenu(ParentMenu, menuitem)
        showWidget(menuitem)

        return(menuitem)
    }

//    me GUI_menu: create_SubMenu(me GUI_menu: ParentMenu, me string: label) <- {
//        me GUI_menu: SubMenu
//        SubMenu <- GUI_menuWithLabel(label)
//        addItemToMenu(ParentMenu, SubMenu)
//        return(SubMenu)
//    }

//    me GUI_menu: create_TopSubMenu(me GUI_menuBar: ParentMenu, me string: label) <- {
//        me GUI_menu: SubMenu
//        SubMenu <- GUI_menuWithLabel(label)
//        addItemToMenu(ParentMenu, SubMenu)
//        return(SubMenu)
//    }
}
struct GLOBAL{

    me thisApp: appFuncs
    me void: close_window() <- {
         // gtk_main_quit()
    }
    me void: markDirtyArea(me GUI_item: widget, me int32: x, me int32: y, me int32: width, me int32: height) <- <%!%G%1.invalidate(%2, %3, %4, %5)%>
    me long: ticksPerSec() <- <%!%G1000%>
    me bool: drawAppArea_cb (me GUI_item: widget, me GUI_ctxt: cr) <- <%drawAppArea_cb(Canvas canvas)%>
}

struct GUI{
//    me void: fetchAreaToBeDrawn(me GUI_rect: area) <- <%!;%>
    me void: showWidget(me GUI_item: widget) <-  <%!%1.setVisible(true)%>
    me GUI_item: newCanvas() <- <%!%Gnew CanvasView()%>
    me GUI_item: GUI_frame(me string: label) <- <%!%Gnew LinearLayout(%1)%>
    me GUI_item: GUI_menuItemWithLabel(me string: label) <- <%!%Gnew MenuItem(%1)%>
    me GUI_item: GUI_menuWithLabel(me string: label) <- <%!%Gnew Menu(%1)%>
    me void: setWidgetSize(me GUI_item: widget, me uint32: width, me uint32: height) <- <%!%G%1.setPreferredSize(new Dimension(%2, %3))%>
//    me GUI_offset: newGUI_offset(me double: value, me double: upper, me double: lower, me double: step_increment, me double: page_increment, me double: page_size) <- <%!gtk_adjustment_new(%1, %2, %3, %4, %5, %6)%>
    me GUI_item: newScrollingWindow() <- <%!%Gnew JScrollPane()%>
//    me GUI_item: newViewport(me GUI_offset: H_Offset, me GUI_offset: V_Offset) <- <%!gtk_viewport_new(%1, %2)%>
    me void: addToContainer(me GUI_container: container, me GUI_item: widget) <- <%!%G%1.add(%2)%>
    me void: addToViewport(me GUI_container: container, me GUI_item: widget) <- <%!%G%1.setViewportView(%2)%>
    me void: addItemToMenu(me GUI_menu: ParentMenu, me GUI_menuItem: menuitem) <- <%!%G%1.add(%2)%>
//    me void: addMenuBar(me GUI_menuBar: menubar) <- <%!%G%1.setJMenuBar(%2)%>
    me void: create_MenuItem()<- <%!gui.create_MenuItem(%1, %2)%>
    me void: create_TopSubMenu()<- <%!%1.addSubMenu(%2)%>
    me void: create_SubMenu()<- <%!%%G1.addSubMenu(%2)%>
    me void: setCallback() <- <%!%G %>
//    me void: createAppMenu(me GUI_frame: frame) <- <%!me bool: createAppMenu(Menu menu)%>
}

struct android_ctx: implMode="inherit:View"{
    me Canvas: canvas
    me Paint: paint
    me Path: path
}

struct GUI_ctxt: ctxTag="Swing" Platform='Java' Lang='Java' LibReq="swing" implMode="inherit:View" {
//    me void: reset() <- <%!GPath = new Path()%>
    me void: setRGBA(me double: red, me double: green, me double: blue, me double: alpha) <- <%!paint.setColor(Color.rgba(%1, %2, %3, %4))%>
    me void: setRGB (me double: red, me double: green, me double: blue) <- <%!paint.setColor(Color.rgb(%1, %2, %3))%>
    me void: setLineWidth(me double: width) <- <%!paint.setStrokeWidth(%1)%>
    me void: moveTo(me double: x, me double: y) <- <%!GPath.moveTo(%1, %2)%>
    me void: lineTo(me double: x, me double: y) <- <%!Gpath.Path.lineTo(%1, %2)%>
//    me void: moveRel(me double: dx, me double: dy) <- <%!GPath.moveTo(cr.cur_x+%1, cr.cur_y+%2)%>
//    me void: lineRel(me double: dx, me double: dy) <- <%!GPath.lineTo(cr.cur_x+%1, cr.cur_y+%2)%>
//    me void: curveTo(me double: x1, me double: y1, me double: x2, me double: y2, me double: x3, me double: y3) <- <%!GPath.curve_to(cr, %1, %2, %3, %4, %5, %6)%>
//    me void: curveRel(me double: dx1, me double: dy1, me double: dx2, me double: dy2, me double: dx3, me double: dy3) <- <%!rel_curve_to(cr, %1, %2, %3, %4, %5, %6)%>
//    me void: paintNow() <- <%!gr.fill(cr.GPath)%>
    me void: strokeNow() <- <%!drawPath(Gpath, cr.paint)%>
//    me void: renderFrame() <- <%!repaint()%>
}


    """

    codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )
