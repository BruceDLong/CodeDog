#/////////////////  Add GUI-Toolkit features using GTK3

import progSpec
import codeDogParser

def createUtilityFunctions():
    S="""
/* Surface to store current scribbles */
their cairo_surface_t: surface <- 0


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
    print "USING GTK3"

    CODE="""
    struct GUI_item{their GtkWidget: GUI_item}
    struct GUI_menuBar{their GtkWidget: GUI_menuBar}
    struct GUI_menu{their GtkWidget: GUI_menu}
    struct GUI_menuItem{their GtkWidget: GUI_menuItem}

    struct GUI_canvas{their GtkWidget: GUI_canvas}

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


    GLOBAL_CODE="""
    struct GLOBAL{
        me GUI_TK: gui_tk
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

    codeDogParser.AddToObjectFromText(objects[0], objects[1], GLOBAL_CODE )
