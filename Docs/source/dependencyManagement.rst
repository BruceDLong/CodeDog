Dependency Management Design
============================

This page describes the intended design for native library and package
management in CodeDog. It is a design reference, not a description of the
current implementation.

Goals
-----

CodeDog libraries should be able to describe the native libraries they need
without making each application manually copy dependency folders from an older
build. The dependency system should make fresh clones reproducible, keep
platform builds isolated from each other, and produce explicit build facts for
the generated build system.

The design must support build files that request more than one platform in a
single run. Dependencies for one build target must never be installed into a
repo-root ``include`` or ``lib`` directory. They must be staged under the folder
for the build target that requested them.

Vocabulary
----------

``feature``
    A CodeDog-level capability requested by an application or library, such as
    ``Quic``, ``Unicode``, or ``GUI_ToolKit``.

``implementation``
    A selected ``.Lib.dog`` layer that implements a feature for a matching set
    of build tags. For example, a C++ Linux QUIC implementation or a Windows
    temporary QUIC stub.

``native capability``
    A lower-level native build capability required by an implementation, such
    as ``quic_transport``, ``tls_boringssl``, ``event_loop_libev``, or
    ``unicode_icu``.

``native package``
    An external dependency that can provide one or more native capabilities.
    It may come from a system package manager, a git repository, an archive, a
    prebuilt SDK, a local path, or a source build.

``variant``
    A platform-specific way to obtain and build a native package. The same
    package may have different variants for Linux, Windows, MacOS, CPU
    families, compilers, or static versus dynamic linkage.

``stage``
    The build-local install prefix where a resolved package exports files for a
    single target. The stage is owned by CodeDog and is safe to delete and
    rebuild.

``manifest``
    A machine-readable record of what a resolved package exports. The generated
    build system consumes manifests instead of guessing include paths and link
    paths from copied folders.

Hard Invariants
---------------

* Dependency artifacts are staged under the active build folder, never under a
  repo-root ``include`` or ``lib`` directory.
* Dependencies are isolated by target key. Linux, Windows, MacOS, compiler, CPU,
  runtime, and linkage differences must not share the same stage directory.
* A package is not considered resolved merely because a folder exists. The
  resolver must verify declared headers, libraries, runtime files, and the
  source revision or archive hash when available.
* Git references, archive checksums, and update policies must be honored.
  Declaring ``@commit=...`` or an equivalent field must produce that exact
  source state.
* Stale or partial installs should fail with a dependency-resolution error or
  be rebuilt. They should not silently satisfy a build.
* Generated build files should consume explicit exports: include directories,
  library directories, libraries, defines, compiler flags, linker flags, and
  runtime files.

Target Keys
-----------

Each dependency resolution is keyed by the actual target being built. A target
key should include the information that can affect ABI, output filenames, or
build options:

* Platform
* CPU
* language and compiler family
* compiler version when known
* runtime model when relevant
* debug or release configuration
* static or dynamic linkage

Example target keys::

    Linux-amd64-CPP-GNU-release-static
    Windows-amd64-CPP-MSVC-release-dynamic
    MacOS-arm64-CPP-Clang-release-static

Build-Local Layout
------------------

Each build target owns its dependency area:

.. code-block:: text

    <buildName>/
      .codedog/
        deps/
          <targetKey>/
            <packageName>/
              src/
              build/
              stage/
                include/
                lib/
                bin/
              manifest.json
        lock.json

``src`` holds downloaded or checked-out source. ``build`` holds generated build
files and intermediate output. ``stage`` is the only area exported to generated
application builds.

Package Sources
---------------

The resolver should support several source adapters:

``system``
    Use a platform package manager such as apt, dnf, pacman, Homebrew, or a
    Windows package manager. Exports may come from known package metadata,
    ``pkg-config``, CMake package files, or explicit recipe data.

``pkgConfig``
    Query ``pkg-config`` for flags without downloading or staging source.

``cmakePackage``
    Use an existing CMake package configuration.

``archive``
    Download and extract a ``.zip`` or tar archive. Archive recipes should
    include a checksum when possible.

``git``
    Clone a repository at an exact branch, tag, or commit. Submodule handling
    must be explicit.

``prebuilt``
    Download a platform-specific SDK or binary package.

``sourceBuild``
    Build from source with CMake, Meson, Autotools, Make, MSBuild, Ninja, or
    another declared build system.

``local``
    Use a user-provided or checked-in path.

``manual``
    Stop with a clear message explaining the required headers, libraries, and
    tools when automation is not available.

Package Variants
----------------

A native package can have many variants. The resolver selects the first usable
variant whose ``when`` clause matches the target and whose required tools are
available.

Example shape:

.. code-block:: codeDog

    nativePackage = {
        id = 'boringssl'
        provides = [tls_boringssl]
        variants = [
            {
                when = { Platform = Linux Lang = CPP }
                source = {
                    type = git
                    url = 'https://github.com/google/boringssl'
                    ref = '251b516'
                    submodules = false
                }
                build = {
                    system = cmake
                    args = ['-DCMAKE_BUILD_TYPE=Release']
                }
                install = {
                    include = ['include']
                    libs = ['ssl/libssl.a', 'crypto/libcrypto.a']
                }
                exports = {
                    includeDirs = ['$stage/include']
                    libDirs = ['$stage/lib']
                    libs = [ssl, crypto]
                }
            }
        ]
    }

Manifest Exports
----------------

After resolution, each package writes a manifest with the facts needed by the
generated build system:

.. code-block:: json

    {
      "package": "boringssl",
      "targetKey": "Linux-amd64-CPP-GNU-release-static",
      "sourceRef": "251b516",
      "stage": "LinuxBuild/.codedog/deps/Linux-amd64-CPP-GNU-release-static/boringssl/stage",
      "includeDirs": [".../stage/include"],
      "libDirs": [".../stage/lib"],
      "libs": ["ssl", "crypto"],
      "defines": [],
      "cflags": [],
      "linkFlags": [],
      "runtimeFiles": []
    }

The SCons generator should combine manifests for the active build target only.
It should not add a package directory to both include and library search paths
unless the manifest explicitly exports those paths.

Compatibility With Current Library Syntax
-----------------------------------------

The first resolver implementation should accept the existing
``interface.packages`` shape so current libraries keep working. Compatibility
rules should be explicit:

* ``packageName`` becomes the native package id.
* ``fetchMethod`` maps to a source adapter.
* ``innerPkgName`` maps to the source root when an archive extracts a nested
  directory.
* ``buildCmds.<Platform>.buildCmd`` maps to a temporary shell build step.
* ``buildCmds.<Platform>.installFiles`` maps to staged files that must be
  verified.
* Existing ``interface.libFiles`` and ``interface.headers`` remain available,
  but new manifests should be preferred for generated build flags.

Compatibility mode should still use target-key staging and validation. It
should not preserve silent stale reuse.

Stub Semantics
--------------

Stubs are useful during bring-up, but they must be visible to the resolver.
There are three distinct states:

``real``
    The implementation provides the real feature behavior.

``stub``
    The implementation builds and links but intentionally omits behavior.

``missing``
    No implementation or native package provider exists for the target.

A stub should either provide a weaker capability or require an explicit build
tag such as ``AllowStubs = true``. This allows a platform build to proceed
during transition without hiding the absence of the real provider.

QUIC Example
------------

The QUIC wrapper is the motivating case. ``Quic.Lib.dog`` should define the
CodeDog-facing API. A real C++ implementation should require native
capabilities such as ``quic_transport``, ``tls_boringssl``, and
``event_loop_libev``. Native package variants then decide how to obtain lsquic,
BoringSSL, and libev on Linux, Windows, and MacOS.

During transition, a Windows stub can remain available so Slipstream can build
on Windows. Once the Windows lsquic provider is expressed and verified, the
real provider should be selected by default.

Incremental Plan
----------------

1. Add a compatibility resolver that stages current ``interface.packages`` under
   ``<buildName>/.codedog/deps/<targetKey>/``.
2. Honor exact git refs, archive checksums, and update policies.
3. Verify staged headers, libraries, and runtime files before declaring a
   package resolved.
4. Generate manifests and make SCons consume explicit exports.
5. Add platform variants for low-risk packages such as ICU, MPIR, and SDL.
6. Migrate QUIC to real Linux, Windows, and MacOS lsquic variants.
7. Add dependency diagnostics such as status, clean, and rebuild commands.
