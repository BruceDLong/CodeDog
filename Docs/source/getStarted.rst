============================
Getting Started With CodeDog
============================

In this chapter lets get CodeDog installed and configured on your computer. We'll test it out by writing a "Hello World" program. After that we will get you going by building an example GUI program and a skeleton of a game.

Setting up CodeDog
===============================

Setting up CodeDog on Linux
---------------------------
.. note::
    The green sections below indicate either text or commands to enter: those beginning with $ are terminal commands.  To open a terminal go to the start menu and type "terminal" in the search box then enter.
    Now you should have a terminal window open, copy the commands below, omitting the $ prompt then enter.

Clone Git Repos
^^^^^^^^^^^^^^^
#. Install Git::

    $ sudo apt install git

#. Make a new folder for development then change directories into that folder::

    $ mkdir devl
    $ cd devl

#. Clone the git repo::

    $ git clone https://github.com/BruceDLong/CodeDog.git

Python, Pip & Pyparsing Installs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#. Python and Pyparsing are required for CodeDog to run.  To install open terminal and enter the following commands::

    $ wget https://bootstrap.pypa.io/get-pip.py
    $ sudo apt install python3
    $ sudo apt install python3-pip
    $ sudo pip3 install pyparsing

#. Check Python version is 3 or higher::

    $ python3 --version

#. Check Pyparsing version is 2.4.6 or higher::

    $ pip3 show pyparsing

Install C++, GTK & Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If you are going to be developing for Linux you will need to install the following::

    $ sudo apt install build-essential libgtk-3-dev libcurl4-gnutls-dev libsdl2-dev libsdl2-mixer-dev libicu-dev libgmp-dev libncurses5-dev libwebsockets-dev

Android Studio
^^^^^^^^^^^^^^
If you are going to be developing for Android you will need to install Android Studio.  Follow the instructions provided in the Android official documentation.

Instructions: `<https://developer.android.com/studio/install#linux>`__

Download: `<https://developer.android.com/studio/index.html>`_

Add CodeDog to your System Path
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#. Edit your .bashrc file adding the following line toward the bottom of the file.::

    PATH="$PATH:$HOME/devl/CodeDog"

#. Verify CodeDog command::

    $ codeDog --version

Installing a Text Editor
^^^^^^^^^^^^^^^^^^^^^^^^
You will need a text editor, our recommendation is `Geany <https://www.geany.org/>`_.   We have already made a configuration file for Geany that provides syntax highlighting.

#. Install Geany::

    $ sudo apt install geany geany-plugins

#. Copy the CodeDog config file from the CodeDog repo into Geany
    $ cp ~/devl/CodeDog/filetypes.dog.conf  ~/.config/geany/filedefs

#. Open Geany/ Tools menu/ Configuration files/ filetype extensions.conf.  Add the following line::

    ‘dog=*.dog;’

#. Now open Geany/ Tools menu/ Reload Configuration or close and reopen Geany.


Setting up CodeDog on Windows
-----------------------------


Setting up CodeDog on MacOS
---------------------------



"Hello World!"
==============


Minimal GUI
===========

Minimal Game
============
