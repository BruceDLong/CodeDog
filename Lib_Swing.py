#/////////////////  Add GUI-Toolkit features using Java Swing

import progSpec
import codeDogParser

def createUtilityFunctions():
    S="""

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
  GUI_menuItem menuitem;

//      menuitem = gtk_menu_item_new_with_label (label.data());
//      //gtk_menu_item_set_submenu (GTK_MENU_ITEM (menuitem), SubMenu);
//      gtk_menu_shell_append (GTK_MENU_SHELL (ParentMenu), menuitem);
//      gtk_widget_show (menuitem);

  return menuitem;
} %>

me GUI_menu: create_SubMenu(me GUI_menu: ParentMenu, me string: label) <- <%{
/*   GUI_menu SubMenu = gtk_menu_new ();
   GUI_menuItem menuitem;

      menuitem = gtk_menu_item_new_with_label (label.data());
      gtk_menu_item_set_submenu (GTK_MENU_ITEM (menuitem), SubMenu);
      gtk_menu_shell_append (GTK_MENU_SHELL (ParentMenu), menuitem);
      gtk_widget_show (menuitem);
*/
  return 0;//SubMenu;
} %>

me GUI_menu: create_menu(me gint: depth) <- <%{
/*  GtkWidget *menu;
  GtkWidget *menuitem;
  GSList *group;
  char buf[32];
  int i, j;

  if (depth < 1)
    return NULL;

  menu = gtk_menu_new ();
  group = NULL;

  for (i = 0, j = 1; i < 5; i++, j++)
    {
      sprintf (buf, "item %2d - %d", depth, j);
      menuitem = gtk_radio_menu_item_new_with_label (group, buf);
      group = gtk_radio_menu_item_get_group (GTK_RADIO_MENU_ITEM (menuitem));

      gtk_menu_shell_append (GTK_MENU_SHELL (menu), menuitem);
      gtk_widget_show (menuitem);
      if (i == 3)
        gtk_widget_set_sensitive (menuitem, FALSE);

      gtk_menu_item_set_submenu (GTK_MENU_ITEM (menuitem), create_menu (depth - 1));
    }
*/
  return 0;// menu;
}
%>

me void: setRGBA(me double: red, me double: green, me double: blue, me double: alpha) <- <%!setColor(color(%1, %2, %3, %4))%>
me void: setRGB (me double: red, me double: green, me double: blue) <- <%!setColor(color(%1, %2, %3))%>
me void: setLineWidth(me double: width) <- <%!cairo_set_line_width(%1)%>
me void: moveTo(me double: x, me double: y) <- <%!cr.moveTo(%1, %2)%>
me void: lineTo(me double: x, me double: y) <- <%!cr.lineTo(%1, %2)%>
me void: moveRel(me double: dx, me double: dy) <- <%!cr.rel_moveTo(%1, %2)%>
me void: lineRel(me double: dx, me double: dy) <- <%!cr.rel_lineTo(%1, %2)%>
me void: curveTo(me double: x1, me double: y1, me double: x2, me double: y2, me double: x3, me double: y3) <- <%!cr.curve_to(cr, %1, %2, %3, %4, %5, %6)%>
me void: curveRel(me double: dx1, me double: dy1, me double: dx2, me double: dy2, me double: dx3, me double: dy3) <- <%!cr.rel_curve_to(cr, %1, %2, %3, %4, %5, %6)%>
me void: paintNow() <- <%!cairo_paint(cr)%>
me void: strokeNow() <- <%!cairo_stroke(cr)%>

me void: fetchAreaToBeDrawn(me GUI_rect: area) <- <%!cairo_clip_extents(cr, %1.x1, %1.y1, %1.x2, %1.y2)%>
me void: showWidget(me GUI_item: widget) <-  <%!gtk_widget_show(%1)%>
me void: markDirtyArea(me GUI_item: widget, me int32: x, me int32: y, me int32: width, me int32: height) <- <%!gtk_widget_queue_draw_area(%1, %2, %3, %4, %5)%>
me GUI_item: newCanvas() <- <%!gtk_drawing_area_new()%>
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

      appArea = appFuncs.createAppArea();
      gtk_container_add (GTK_CONTAINER (frame), appArea);

"""
    return S


def createStatusBar():
    S="""
    // Status bar code here
"""
    return S


def use(objects, buildSpec, tags, platform):
    print "USING Java Swing for UI"

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

    struct GUI_callback{me GCallback: GUI_callback}

    struct GUI_MotionEvent{their GdkEventMotion: GUI_MotionEvent}

    struct GUI_TK{

        me uint32: GUI_Init() <- <%{return(0);}%>

        me void: createAndShowGUI() <- <% {
            //Create and set up the window.
            JFrame frame = new JFrame("HelloWorldSwing");
            frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);

            //Add the ubiquitous "Hello World" label.
            JLabel label = new JLabel("Hello World");
            frame.getContentPane().add(label);

            //Display the window.
            //frame.pack();
            frame.setSize(650, 250);
            frame.setVisible(true);
        } %>

        me uint32: GUI_Run() <- <% {
            long status=0;

            javax.swing.SwingUtilities.invokeLater(new Runnable() {
            public void run() {
                createAndShowGUI();
            }
            });

            return(status);
        } %>
        me void: GUI_Deinit() <- {

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
        me GUI_TK: gui_tk
        me thisApp: appFuncs
        %s
        me void: activate(their GtkApplication: app, me gpointer: user_data) <- <%%{
  /*        GtkWidget *window;
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
          */
        }%%>
    }
""" % (APP_UTILITY_CODE, MENU_BAR_CODE, MAIN_APP_CODE, STATUS_BAR_CODE)

    codeDogParser.AddToObjectFromText(objects[0], objects[1], GLOBAL_CODE )
