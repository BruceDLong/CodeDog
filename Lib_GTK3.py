#/////////////////  Add GUI-Toolkit features using GTK3

import progSpec
import codeDogParser

def createUtilityFunctions():
    S="""


    // LOGGING INTERFACE:
    me void: logMesg(me string: s) <- <%!g_message(%1)%>
    me void: logInfo(me string: s) <- <%!g_info(%1)%>
    me void: logCriticalIssue(me string: s) <- <%!g_critical(%1)%>
    me void: logFatalError(me string: s) <- <%!g_error(%1)%>
    me void: logWarning(me string: s) <- <%!g_warning(%1)%>
    me void: logDebug(me string: s) <- <%!g_debug(%1)%>
    //me void: assert(condition) <- {}


// GUI INTERFACE:

/* Surface to store current scribbles */
their cairo_surface_t: surface <- 0

me void: close_window() <- {
  if (surface){
    cairo_surface_destroy(surface)
  }

  gtk_main_quit()
}

me GUI_menuItem: create_MenuItem(me GUI_menu: ParentMenu, me string: label) <- <%{
    GtkWidget *menuitem;

    menuitem = gtk_menu_item_new_with_label (label.data());
    //gtk_menu_item_set_submenu (GTK_MENU_ITEM (menuitem), SubMenu);
    gtk_menu_shell_append (GTK_MENU_SHELL (ParentMenu), menuitem);
    gtk_widget_show (menuitem);

  return menuitem;
} %>

me GUI_menu: create_SubMenu(me GUI_menu: ParentMenu, me string: label) <- <%{
    GtkWidget *SubMenu = gtk_menu_new ();
    GtkWidget *menuitem;

    menuitem = gtk_menu_item_new_with_label (label.data());
    gtk_menu_item_set_submenu (GTK_MENU_ITEM (menuitem), SubMenu);
    gtk_menu_shell_append (GTK_MENU_SHELL (ParentMenu), menuitem);
    gtk_widget_show (menuitem);

  return SubMenu;
} %>


me void: setRGBA(me double: red, me double: green, me double: blue, me double: alpha) <- <%!cairo_set_source_rgba(cr, %1, %2, %3, %4)%>
me void: setRGB (me double: red, me double: green, me double: blue) <- <%!cairo_set_source_rgb(cr, %1, %2, %3)%>
me void: setLineWidth(me double: width) <- <%!cairo_set_line_width(cr, %1)%>
me void: moveTo(me double: x, me double: y) <- <%!cairo_move_to(cr, %1, %2)%>
me void: lineTo(me double: x, me double: y) <- <%!cairo_line_to(cr, %1, %2)%>
me void: moveRel(me double: dx, me double: dy) <- <%!cairo_rel_move_to(cr, %1, %2)%>
me void: lineRel(me double: dx, me double: dy) <- <%!cairo_rel_line_to(cr, %1, %2)%>
me void: curveTo(me double: x1, me double: y1, me double: x2, me double: y2, me double: x3, me double: y3) <- <%!cairo_curve_to(cr, %1, %2, %3, %4, %5, %6)%>
me void: curveRel(me double: dx1, me double: dy1, me double: dx2, me double: dy2, me double: dx3, me double: dy3) <- <%!cairo_rel_curve_to(cr, %1, %2, %3, %4, %5, %6)%>
me void: paintNow() <- <%!cairo_paint(cr)%>
me void: strokeNow() <- <%!cairo_stroke(cr)%>

me void: fetchAreaToBeDrawn(me GUI_rect: area) <- <%!cairo_clip_extents(cr, &%1.x1, &%1.y1, &%1.x2, &%1.y2)%>
me void: showWidget(me GUI_item: widget) <-  <%!gtk_widget_show(%1)%>
me void: markDirtyArea(me GUI_item: widget, me int32: x, me int32: y, me int32: width, me int32: height) <- <%!gtk_widget_queue_draw_area(%1, %2, %3, %4, %5)%>
me GUI_item: newCanvas() <- <%!gtk_drawing_area_new()%>
me void: setWidgetSize(me GUI_item: widget, me uint32: width, me uint32: height) <- <%!gtk_widget_set_size_request(%1, %2, %3)%>
me GUI_offset: newGUI_offset(me double: value, me double: upper, me double: lower, me double: step_increment, me double: page_increment, me double: page_size) <- <%!gtk_adjustment_new(%1, %2, %3, %4, %5, %6)%>
me GUI_item: newScrollingWindow() <- <%!gtk_scrolled_window_new(0, 0)%>
me GUI_item: newViewport(me GUI_offset: H_Offset, me GUI_offset: V_Offset) <- <%!gtk_viewport_new(%1, %2)%>
me void: addToContainer(me GUI_container: container, me GUI_item: widget) <- <%!gtk_container_add(GTK_CONTAINER (%1), %2)%>

me void: setCallback(me GUI_item: widget, me string: eventID, me GUI_callback: callback) <- <% {
    g_signal_connect(widget, eventID.data(), G_CALLBACK (callback), NULL);
    if(eventID=="button-press-event"){
        gtk_widget_set_events(widget, gtk_widget_get_events(widget) | GDK_BUTTON_PRESS_MASK);
    }
    if(eventID=="motion-notify-event"){
        gtk_widget_set_events(widget, gtk_widget_get_events(widget) | GDK_POINTER_MOTION_MASK);
    }
} %>

"""
    return S


def createMenubar():
    S="""
      GtkWidget *boxForMenubar;
      GtkWidget *menubar;


      boxForMenubar = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 0);
      gtk_container_add (GTK_CONTAINER (topBox), boxForMenubar);
      gtk_widget_show (boxForMenubar);

      menubar = gtk_menu_bar_new ();
      gtk_box_pack_start (GTK_BOX (boxForMenubar), menubar, TRUE, TRUE, 0);
      gtk_widget_show (menubar);

      appFuncs.createAppMenu(menubar);
      """
    return S


def createMainAppArea():
    S="""
      GtkWidget *frame;
      GtkWidget *appArea;

      frame = gtk_frame_new (NULL);
      gtk_frame_set_shadow_type (GTK_FRAME (frame), GTK_SHADOW_IN);
      gtk_box_pack_start (GTK_BOX (topBox), frame, TRUE, TRUE, 0);

      appFuncs.createAppArea(frame);
     // gtk_container_add (GTK_CONTAINER (frame), appArea);

"""
    return S


def createStatusBar():
    S="""
    // Status bar code here
"""
    return S


def use(objects, buildSpec, tags, platform):
    print "USING GTK3"

    CODE="""
    struct GUI_ctxt{their cairo_t:GUI_ctxt}
    struct GUI_rect{me double: x1 me double: y1 me double: x2 me double: y2}
    struct GUI_offset{their GtkAdjustment:GUI_offset}


    struct GUI_item{their GtkWidget: GUI_item}
    struct GUI_menuBar{their GtkWidget: GUI_menuBar}
    struct GUI_menu{their GtkWidget: GUI_menu}
    struct GUI_menuItem{their GtkWidget: GUI_menuItem}
    struct GUI_canvas{their GtkWidget: GUI_canvas}
    struct GUI_container{their GtkContainer:GUI_container}
    struct GUI_frame{their GtkWidget:GUI_frame}
    struct GUI_ScrollingWindow{their GtkWidget: GUI_ScrollingWindow}

    struct GUI_callback{me GCallback: GUI_callback}

    struct GUI_MotionEvent{their GdkEventMotion: GUI_MotionEvent}

    struct GUI{
        their GtkApplication: app
        their GtkWidget: window

        me uint32: GUI_Init() <- {
            app <- gtk_application_new ("org.gtk.example", G_APPLICATION_FLAGS_NONE)
            g_signal_connect (app, "activate", G_CALLBACK(activate), NULL)
            return(0)
        }
        me uint32: GUI_Run() <- <% {
            uint32_t status;
            status = g_application_run( G_APPLICATION(app), 0, 0);
            return(status);
        } %>
        me void: GUI_Deinit() <- {
            g_object_unref(app)
        }

    }

    """

    codeDogParser.AddToObjectFromText(objects[0], objects[1], CODE )

    APP_UTILITY_CODE = createUtilityFunctions()
    MENU_BAR_CODE = createMenubar()
    MAIN_APP_CODE = createMainAppArea()
    STATUS_BAR_CODE=createStatusBar()


    GLOBAL_CODE="""
    struct GLOBAL{
        //me GUI: static_gui_tk
        me thisApp: appFuncs
        %s
        me void: activate(their GtkApplication: app, me gpointer: user_data) <- <%%{
          GtkWidget *window;
          GtkWidget *topBox;

          window = gtk_application_window_new (app);
          gtk_window_set_title (GTK_WINDOW (window), "Window");
          gtk_window_set_default_size (GTK_WINDOW (window), 500, 700);
          g_signal_connect (window, "destroy", G_CALLBACK (close_window), NULL);
          gtk_container_set_border_width (GTK_CONTAINER (window), 0);

          topBox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 0);
          gtk_container_add (GTK_CONTAINER (window), topBox);
          gtk_widget_show (topBox);
          ////////////////////  A d d  A p p l i c a t i o n   M e n u
          %s

          ////////////////////  A d d   A p p l i c a t i o n   I t e m s
          %s

          ////////////////////  A d d  S t a t u s   A r e a
          %s


          gtk_widget_show_all (window);
        }%%>
    }
""" % (APP_UTILITY_CODE, MENU_BAR_CODE, MAIN_APP_CODE, STATUS_BAR_CODE)
    print "##################################################\n", GLOBAL_CODE, "\n\n\n"
    codeDogParser.AddToObjectFromText(objects[0], objects[1], GLOBAL_CODE )
