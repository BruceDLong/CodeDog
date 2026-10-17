Known backend issues
====================

These open issues were identified while validating try/catch support on
2026-10-17. The full-build failures below also reproduce at commit ``c3a71f2``,
before the try/catch changes, with a program that uses no exception handling.
The synchronization gaps were confirmed by inspecting the existing sources;
their runtime behavior has not yet been validated across all backends.

Validation boundary
-------------------

The Python regression suite passed all 107 tests with C++, Java, Kotlin and
Swift compiler tests enabled. The try/catch tests compile and execute generated
code on all four backends, including the actual standard error helper bindings.
A complete C++ application build also passes. Complete Java, Kotlin and Swift
application builds remain blocked by the issues below, so the focused tests do
not establish that their entire standard libraries work.

To reproduce the first full-build failures, save this as ``Probe.dog`` in a
scratch directory and run ``/path/to/CodeDog/codeDog Probe.dog``::

    Build: Platform="Swing" Lang="Java";
    FileName="baseline"
    ProgramOrLibrary="program"
    runCode=`print("baseline")`

For Kotlin, use ``Platform="Kotlin" Lang="Kotlin"``. For Swift, use
``Platform="Swift" Lang="Swift"``. Use a separate directory for each backend.
Fixing the first failure may expose further standard-library problems.

JVM exit declaration
--------------------

**Status:** Open; observed during Java and Kotlin generation.

``Logger.Lib.dog`` calls ``exit(-1)`` from ``logFatalError``. Java and Kotlin
define ``GLOBAL::exit(int)`` in their implementation libraries, but
``LIBS/CodeDog.Lib.dog`` does not declare it in the shared public API. The
generator correctly rejects this as access to an implementation-only member.

**Proposed fix:** Declare ``void: exit(me int: status)`` in the shared API and
provide matching native bindings on every backend. Preserve the implementation
visibility checks. Audit the other shared declarations against backend
implementations as subsequent failures appear.

**Acceptance:** The minimal Java and Kotlin programs generate past
``logFatalError``; full builds and subprocess tests verify native exit status
without introducing an unimplemented stub or recursive binding on C++ or Swift.

Swift numeric string conversion
-------------------------------

**Status:** Open; observed during Swift compilation.

The shared API declares ``toString(number_type)``, but
``LIBS/CodeDog.Swift.Lib.dog`` supplies only the ``long`` and ``int`` numeric
overloads. Generated Swift contains an undefined ``number_type`` parameter and
numeric calls that cannot resolve to the available Boolean overload.

**Proposed fix:** Supply the numeric wildcard converter using Swift's
``String(value)``, following the existing C++ wildcard binding. Keep Boolean
conversion separate and verify numeric overload selection across the backends.
``number_type`` is a compiler matching type and must not appear as a native
Swift parameter type.

**Acceptance:** Compile and run conversions of signed and unsigned integers,
64-bit values, floating-point values and Booleans; compile the complete logger
and ``dblToString`` paths.

Swift threads and synchronization
---------------------------------

**Status:** Open; callback and missing ``wait`` errors observed during
compilation, additional ownership and locking gaps confirmed in source.

In ``LIBS/Threads.Swift.Lib.dog``:

* ``__threadedFunction`` takes a nonoptional pointer, while the tested Linux
  ``pthread_create`` binding expects an optional raw pointer callback argument.
* The callback context allocation lacks a complete initialization and cleanup
  lifecycle. Thread-handle storage and joining also need review.
* ``__SyncLock`` is empty, although generated code calls its ``wait`` method.
* ``__MutexMngr`` copies the native mutex value instead of owning a reference
  to the shared mutex storage.

Separately, ``xlator_Swift.py::codeProtectBlock`` returns the protected body
without generating any lock acquisition or release.

**Proposed fix:** Match the native callback signature on supported platforms,
give the callback context explicit ownership and cleanup on both successful
start and failure, and join only successfully started threads. Implement
initialized, shared mutex storage and condition-variable wait, signal and
broadcast operations. Waiting must release and reacquire the same mutex.
Generate lexical locking for ``protect`` with ``defer`` to unlock on normal
completion, early return and thrown errors.

**Acceptance:** Full Swift builds plus bounded runtime tests for start/join,
mutual exclusion, wait/reacquisition, single and broadcast notification, and
lock release during exception propagation and early returns. Check both Linux
and Darwin native bindings; Linux compilation alone is insufficient.

Kotlin synchronization
----------------------

**Status:** Open; confirmed in source, independent of the first build failure.

``LIBS/Threads.Kotlin.Lib.dog`` has empty ``SyncLock.wait`` and ``notifyOne``
bodies and no implementation of the shared ``notifyAll`` operation.
``Xlator_Kotlin`` also inherits Java's ``codeProtectBlock``, which emits Java
local-variable and constructor syntax.

**Proposed fix:** Implement the shared condition-variable contract with real
waiting and notifications, preserving the supplied mutex relationship. Add a
Kotlin-specific ``protect`` generator using exception-safe ``try/finally``
locking and Kotlin syntax.

**Acceptance:** Compile actual ``protect`` blocks and run the same bounded
locking, notification and exception-unwinding checks used for Swift. Empty
method bodies must not count as successful synchronization support.

Kotlin compiler selection
-------------------------

**Status:** Open; toolchain incompatibility observed independently of the
library generation failure.

``buildDog.py::kotlinCompilerCommand`` prefers the compiler under
``.tools/kotlin-apt`` whenever it exists, ahead of ``PATH``. That older compiler
failed with JDK 21 using ``Unsupported class file major version 65``. The
installed Kotlin 1.9.24 compiler passed the focused runtime tests with that JDK.

**Proposed fix:** Add an explicit ``CODEDOG_KOTLINC`` selection override,
analogous to ``CODEDOG_SWIFTC``, and support a compatible compiler/JDK pair
without changing the user's system-wide toolchain. This override is proposed,
not implemented. The tests' ``KOTLINC`` variable currently selects a compiler
only for those tests; it does not override the application builder.

**Acceptance:** Verify compiler-selection precedence and complete a Kotlin CLI
build with the selected compiler after resolving the library blockers.
