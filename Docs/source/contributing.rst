Contributing
============

Thank you for your interest in contributing to the CodeDog project!

Here you will find resources that will be useful in some way.

CodeDog Style Guide
-------------------

The following are some general guidelines so that we all produce code that looks similar.

1. Use 4 spaces to indent. Do not use tab characters. You can set your editor to do this automatically.

.. note::

    If you use a file compare tool such as Meld, be sure to set it to use 4 spaces and no tabs.
    We have found that we get commits with terrible white space changes otherwise.

2. Line up curly braces like this:

.. code-block:: codeDog

        if(…){
            // code here
        } else {
            // code here
        }

3. If it seems appropriate, lines of code can be made to line up with each other like this:

.. code-block:: codeDog

        sizeDiff            <- 0
        LHS.value.format    <- fLiteral
        LHS.value.str       <- RHS.value.str
        LHS.value.sizeMode  <- fromGiven

4. Use camelCase for identifiers. Class names can be capitalized while other identifiers start lower case.

5. Only put more than one command on a single line when it adds to the clarity of the code or makes trivial things take less space. Separate the items with semicolons:

.. code-block:: codeDog

           void: clear()<-{path<-NULL; flags<-0;}


Our Code Review Checklist
-------------------------

Tiffany's Workflow
------------------


A Tour of How CodeDog Builds Programs
-------------------------------------

The codeDog file
^^^^^^^^^^^^^^^^

codeDogParser.py
^^^^^^^^^^^^^^^^

progSpec.py
^^^^^^^^^^^

codeGenerator.py
^^^^^^^^^^^^^^^^

buildDog.py
^^^^^^^^^^^
