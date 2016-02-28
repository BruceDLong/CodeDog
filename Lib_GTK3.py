#/////////////////  Add GUI-Toolkit features using GTK3

import progSpec
import codeDogParser

def createUtilityFunctions():
    S="""
/* Surface to store current scribbles */
their cairo_surface_t: surface <- 0

me void: clear_surface() <- {
  their cairo_t: cr

  cr <- cairo_create(surface)

  cairo_set_source_rgb(cr, 1, 1, 1)
  cairo_paint(cr)

  cairo_destroy(cr)
}

/* Create a new surface of the appropriate size to store our scribbles */
me gboolean: configure_event_cb (their GtkWidget: widget, their GdkEventConfigure: event, me gpointer: data) <- <% {
  if (surface)
    cairo_surface_destroy (surface);

  surface = gdk_window_create_similar_surface (gtk_widget_get_window (widget),
                                               CAIRO_CONTENT_COLOR,
                                               gtk_widget_get_allocated_width (widget),
                                               gtk_widget_get_allocated_height (widget));

  /* Initialize the surface to white */
  clear_surface ();

  /* We've handled the configure event, no need for further processing. */
  return TRUE;
} %>

/* Redraw the screen from the surface. Note that the ::draw
 * signal receives a ready-to-be-used cairo_t that is already
 * clipped to only draw the exposed areas of the widget
 */
me gboolean: draw_cb (their GtkWidget: widget,
         their cairo_t:   cr,
         me gpointer:   data)  <- <% {
  cairo_set_source_surface (cr, surface, 0, 0);
  cairo_paint (cr);

  return FALSE;
}  %>

/* Draw a rectangle on the surface at the given position */
me void: draw_brush (their GtkWidget: widget,
            me gdouble:    x,
            me gdouble:    y) <- <%{
  cairo_t *cr;

  /* Paint to the surface, where we store our state */
  cr = cairo_create (surface);

  cairo_rectangle (cr, x - 3, y - 3, 6, 6);
  cairo_fill (cr);

  cairo_destroy (cr);

  /* Now invalidate the affected region of the drawing area. */
  gtk_widget_queue_draw_area (widget, x - 3, y - 3, 6, 6);
} %>

/* Handle button press events by either drawing a rectangle
 * or clearing the surface, depending on which button was pressed.
 * The ::button-press signal handler receives a GdkEventButton
 * struct which contains this information.
 */
me gboolean: button_press_event_cb (their GtkWidget: widget,
                       their GdkEventButton: event,
                       me gpointer:        data) <- <%{
  /* paranoia check, in case we haven't gotten a configure event */
  if (surface == NULL)
    return FALSE;

  if (event->button == GDK_BUTTON_PRIMARY)
    {
      draw_brush (widget, event->x, event->y);
    }
  else if (event->button == GDK_BUTTON_SECONDARY)
    {
      clear_surface ();
      gtk_widget_queue_draw (widget);
    }

  /* We've handled the event, stop processing */
  return TRUE;
} %>

/* Handle motion events by continuing to draw if button 1 is
 * still held down. The ::motion-notify signal handler receives
 * a GdkEventMotion struct which contains this information.
 */
me gboolean: motion_notify_event_cb (their GtkWidget: widget,
                        their GdkEventMotion: event,
                        me gpointer: data) <- <% {
  /* paranoia check, in case we haven't gotten a configure event */
  if (surface == NULL)
    return FALSE;

  if (event->state & GDK_BUTTON1_MASK)
    draw_brush (widget, event->x, event->y);

  /* We've handled it, stop processing */
  return TRUE;
} %>

me void: close_window() <- {
  if (surface)
    cairo_surface_destroy(surface)

  gtk_main_quit()
}

their GtkWidget: create_MenuItem(their GtkWidget: ParentMenu, me string: label) <- <%{
  GtkWidget *menuitem;

      menuitem = gtk_menu_item_new_with_label (label.data());
      //gtk_menu_item_set_submenu (GTK_MENU_ITEM (menuitem), SubMenu);
      gtk_menu_shell_append (GTK_MENU_SHELL (ParentMenu), menuitem);
      gtk_widget_show (menuitem);

  return menuitem;
} %>

their GtkWidget: create_SubMenu(their GtkWidget: ParentMenu, me string: label) <- <%{
  GtkWidget *SubMenu = gtk_menu_new ();
  GtkWidget *menuitem;

      menuitem = gtk_menu_item_new_with_label (label.data());
      gtk_menu_item_set_submenu (GTK_MENU_ITEM (menuitem), SubMenu);
      gtk_menu_shell_append (GTK_MENU_SHELL (ParentMenu), menuitem);
      gtk_widget_show (menuitem);

  return SubMenu;
} %>

their GtkWidget: create_menu(me gint: depth) <- <%{
  GtkWidget *menu;
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

  return menu;
}
%>
"""
    return S


def createMenubar():
    S="""
      GtkWidget *box;
      GtkWidget *boxForMenubar;
      GtkWidget *menubar;
      GtkWidget *menu;
      GtkWidget *menuitem;
      box = gtk_box_new (GTK_ORIENTATION_VERTICAL, 0);
      gtk_container_add (GTK_CONTAINER (window), box);
      gtk_widget_show (box);

      boxForMenubar = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 0);
      gtk_container_add (GTK_CONTAINER (box), boxForMenubar);
      gtk_widget_show (boxForMenubar);

      menubar = gtk_menu_bar_new ();
      gtk_box_pack_start (GTK_BOX (boxForMenubar), menubar, TRUE, TRUE, 0);
      gtk_widget_show (menubar);


      """
    return S


def createMainAppArea():
    S="""
      GtkWidget *frame;
      GtkWidget *drawing_area;

      frame = gtk_frame_new (NULL);
      gtk_frame_set_shadow_type (GTK_FRAME (frame), GTK_SHADOW_IN);
      gtk_box_pack_start (GTK_BOX (box), frame, TRUE, TRUE, 0);

      drawing_area = gtk_drawing_area_new ();

      gtk_widget_set_size_request (drawing_area, 100, 100);

      gtk_container_add (GTK_CONTAINER (frame), drawing_area);

      g_signal_connect (drawing_area, "draw", G_CALLBACK (draw_cb), NULL);
      g_signal_connect (drawing_area,"configure-event", G_CALLBACK (configure_event_cb), NULL);


      g_signal_connect (drawing_area, "motion-notify-event",  G_CALLBACK (motion_notify_event_cb), NULL);
      g_signal_connect (drawing_area, "button-press-event", G_CALLBACK (button_press_event_cb), NULL);


      gtk_widget_set_events (drawing_area, gtk_widget_get_events (drawing_area) | GDK_BUTTON_PRESS_MASK | GDK_POINTER_MOTION_MASK);
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
    struct GUI_TK{
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


    MAIN_CODE="""
    struct MAIN{
        me GUI_TK: gui_tk
        %s
        me void: activate(their GtkApplication: app, me gpointer: user_data) <- <%%{
          GtkWidget *window;

          window = gtk_application_window_new (app);
          gtk_window_set_title (GTK_WINDOW (window), "Window");
          gtk_window_set_default_size (GTK_WINDOW (window), 500, 700);
          g_signal_connect (window, "destroy", G_CALLBACK (close_window), NULL);
          gtk_container_set_border_width (GTK_CONTAINER (window), 0);

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

    codeDogParser.AddToObjectFromText(objects[0], objects[1], MAIN_CODE )
