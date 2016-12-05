#/////////////////  Add GUI-Toolkit features using Java Swing

import progSpec
import codeDogParser

def use(objects, buildSpec, tags, platform):
    CODE="""
model draw2D{
    me void: setRGBA(me double: red, me double: green, me double: blue, me double: alpha)
    me void: setRGB (me double: red, me double: green, me double: blue)
    me void: setLineWidth(me double: width)
    me void: moveTo(me double: x, me double: y)
    me void: lineTo(me double: x, me double: y)
    me void: moveRel(me double: dx, me double: dy)
    me void: lineRel(me double: dx, me double: dy)
    me void: curveTo(me double: x1, me double: y1, me double: x2, me double: y2, me double: x3, me double: y3)
    me void: curveRel(me double: dx1, me double: dy1, me double: dx2, me double: dy2, me double: dx3, me double: dy3)
    me void: paintNow()
    me void: strokeNow()
}
struct JavaGUI_ctxt: ctxTag="Swing" Platform='Java' Lang='Java' LibReq="swing" implMode="inherit:JPanel" {
    their Graphics2D: gr
    me GeneralPath: GPath
    me double: cur_x
    me double: cur_y


    me void: paintComponent(me Graphics: g) <- <%    {
        super.paintComponent(g);
        gr=(Graphics2D)(g);
        GLOBAL.static_Global.drawAppArea_cb(this, this);
    }%>
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
        frame.setSize(500, 700);
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
struct GLOBAL{

    me thisApp: appFuncs
    me void: close_window() <- {
         // gtk_main_quit()
    }
}

struct GUI{
    me void: fetchAreaToBeDrawn(me GUI_rect: area) <- <%!;%>
    me void: showWidget(me GUI_item: widget) <-  <%!%1.setVisible(true)%>
    me void: markDirtyArea(me GUI_item: widget, me int32: x, me int32: y, me int32: width, me int32: height) <- <%!%G %>
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
    me void: moveTo(me double: x, me double: y) <- <%!GPath.moveTo(%1, %2)%>
    me void: lineTo(me double: x, me double: y) <- <%!GPath.lineTo(%1, %2)%>
    me void: moveRel(me double: dx, me double: dy) <- <%!GPath.moveTo(cr.cur_x+%1, cr.cur_y+%2)%>
    me void: lineRel(me double: dx, me double: dy) <- <%!GPath.lineTo(cr.cur_x+%1, cr.cur_y+%2)%>
    me void: curveTo(me double: x1, me double: y1, me double: x2, me double: y2, me double: x3, me double: y3) <- <%!GPath.curve_to(cr, %1, %2, %3, %4, %5, %6)%>
    me void: curveRel(me double: dx1, me double: dy1, me double: dx2, me double: dy2, me double: dx3, me double: dy3) <- <%!rel_curve_to(cr, %1, %2, %3, %4, %5, %6)%>
    me void: paintNow() <- <%!gr.fill(cr.GPath)%>
    me void: strokeNow() <- <%!gr.draw(cr.GPath)%>
}
    """

    codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )
