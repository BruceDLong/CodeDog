# Linux C++ shared interfaces

A standalone library target can set `ExportInterface='true'` in its build
specification with `ProgramOrLibrary = "sharedlibrary"`. CodeDog emits a `.hpp`,
one implementation `.cpp`, and a `.interface.json` beside the `.so`.

A client build sets `LinkedInterface='path/to/name.interface.json'` and continues
to request the same CodeDog features. The language declarations remain available
for type checking. Imported C++ classes, globals, and implementation embeds are
supplied by the shared library. Client-generated declarations must match those
in the manifest. Library initialization/deinitialization runs through exported
lifecycle functions, avoiding duplicate shared state.

Only one linked interface is currently supported. Build the library first, in a
separate CodeDog invocation from the client. The link uses an absolute development
RUNPATH. A generated ABI symbol plus eager binding rejects stale generated
interfaces. Native headers used by the public header are not structurally
fingerprinted: changes to their public layouts or inline code require rebuilding
the client, as with ordinary C++ libraries.

For base classes intended for client-side inheritance, declare extension hooks:

```text
struct Service: virtualMethods=[reply] {
    void: reply(me string: text) <- {print(text)}
}
```

This keeps virtual dispatch independent of whether subclasses are visible during
library generation. Unlisted methods retain CodeDog's existing inheritance rules.
See `Tests/test_shared_library.py` for a complete executable replacement test.
