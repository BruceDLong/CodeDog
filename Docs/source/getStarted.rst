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

Python, Pip & Pyparsing Installs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#. Python3 is required for CodeDog to run. To install open terminal and enter the following commands::

    $ sudo apt install python3
    $ sudo apt install python3-pip

#. Check Python version is 3 or higher::

    $ python3 --version

Clone Git Repos
^^^^^^^^^^^^^^^
#. Install Git::

    $ sudo apt install git

#. Make a new folder for development then change directories into that folder::

    $ mkdir devl
    $ cd devl

#. Clone the git repo::

    $ git clone https://github.com/BruceDLong/CodeDog.git

#. Run any CodeDog example to set up the environment::

    $ ./codeDog ./Examples/minimalGame.dog

Android Studio
^^^^^^^^^^^^^^
If you are going to be developing for Android you will need to install Android Studio.  Follow the instructions provided in the Android official documentation.

Instructions: `<https://developer.android.com/studio/install#linux>`__

Download: `<https://developer.android.com/studio/index.html>`_

Installing VSCode or VSCode-Server (Integrated Development Environment "IDE")
^^^^^^^^^^^^^^^^^^^^^^^^

#. Install VSCode::

    $ sudo apt install wget gpg
    $ wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
    $ sudo install -D -o root -g root -m 644 packages.microsoft.gpg /etc/apt/keyrings/packages.microsoft.gpg
    $ sudo sh -c 'echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'
    $ rm -f packages.microsoft.gpg
    $ sudo apt install apt-transport-https
    $ sudo apt update
    $ sudo apt install code

#. Copy the VSCode extension for CodeDog syntax::

    $ cp -r ~/devl/CodeDog/Docs/syntax-highlight-extensions/vscpde-codeDog-syntax-extension ~/.vscode/extensions/

#. (Optional) Install VSCode-Server (to allow remote VSCode sessions on the host)::

    .. note:: At the time of publishing, VSCode does not expose an option to specify which port is used to listen for remote sessions. There's an open-source project that acts as a wrapper, allowing finer control over both ports and user access: https://coder.com/docs/code-server/latest/guide

    $ curl -fsSL https://code-server.dev/install.sh | sh

    .. note:: The installation script will guide you through the rest of the setup process

#. (Optional) Copy and install the VSCode extension for CodeDog syntax::

    $ cp -r ~/devl/CodeDog/Docs/syntax-highlight-extensions/vscpde-codeDog-syntax-extension ~/.vscode-server/extensions/

Installing Geany (Text Editor / IDE)
^^^^^^^^^^^^^^^^^^^^^^^^
 `Geany <https://www.geany.org/>`_ is another open source text editor. We have already made a configuration file for Geany that provides syntax highlighting.

#. Install Geany:

    $ sudo apt install geany geany-plugins

#. Copy the CodeDog config file from the CodeDog repo into Geany:

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
