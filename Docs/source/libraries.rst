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
