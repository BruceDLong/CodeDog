CodeDog Libraries
=================

* Default CodeDog Library

* GUI Toolkit
  * CodeDog Widgets
  * Dashboard
  * DataDashes
  * DataManager

* Game Toolkit

* Logger

* Math

* Networking

* WebSockets

* Terminal

* Threads

* Unicode

* IOBuffer

Checked unsigned parsing
------------------------

The default CodeDog library provides ``UInt64Parser`` for strict decimal input:

.. code-block:: codeDog

    me UInt64Parser: parsed
    if(parsed.parse(text)){
        me uint64: value <- parsed.value
    }

``parse`` accepts ASCII digits over the full range 0 through
18446744073709551615, including leading zeroes. It returns ``false`` for empty
input, signs, whitespace, non-digits, or overflow, and leaves ``value`` unchanged
on failure. C++, Java, Kotlin, and Swift use their respective library backends.
Java and Kotlin represent ``uint64`` with a signed ``long``/``Long``; values above
9223372036854775807 retain their unsigned bit pattern and require unsigned-aware
formatting or comparisons on those targets.


File stream open modes
----------------------

The C++ ``FileStream`` backend accepts a mode string:

.. code-block:: codeDog

    me FileStream: input
    input.open("data.txt", "r")
    if(!input.failure()){print(input.getLine()); input.close()}

The supported modes follow the familiar C file-mode conventions:

* ``r``: read an existing file without requiring write permission.
* ``r+``: read and write an existing file without truncating it.
* ``w``: write, creating the file or truncating its existing contents.
* ``w+``: read and write, creating or truncating the file.
* ``a``: write at the end, creating the file if necessary.
* ``a+``: read and append, creating the file if necessary.

Add ``b`` for binary I/O, for example ``rb``, ``w+b`` or ``ab+``. The ``+``
and ``b`` modifiers may appear in either order, once each. Invalid modes set
``failure()`` without opening or truncating a file. Opening failures also use
``failure()``. An already open stream must be closed before reopening it.

The one-argument ``open(path)`` retains its existing read/write behavior on C++.
``openNew(path)`` and ``openAppend(path)`` also retain their existing behavior.
The new mode overload is currently supplied by the C++ backend; the other
backends' existing file-stream operations are unchanged. Calling the new overload
on a backend without an implementation reports a fatal unsupported-operation
error before performing any file I/O.

Standard error bindings
-----------------------

On the C++ backend, ``throwInvalidArgument(message)`` and
``throwOverflowError(message)`` raise ``std::invalid_argument`` and
``std::overflow_error`` respectively. They preserve the supplied message and
normal stack unwinding, including release of locks held by ``protect``.
These runtime bindings do not introduce CodeDog try/catch syntax.
