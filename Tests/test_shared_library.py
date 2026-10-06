"""Exercise the exported C++ boundary with an unchanged consumer executable."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

CODEDOG = Path(__file__).resolve().parents[1] / "codeDog"


@unittest.skipUnless(sys.platform == "linux" and shutil.which("g++"), "Linux C++ linker test")
class SharedLibraryTests(unittest.TestCase):
    def test_replace_library_without_recompiling_client_and_reject_abi_change(self):
        with tempfile.TemporaryDirectory(prefix="codedog-shared-") as directory:
            root = Path(directory)
            library = root / "Counter.Lib.dog"
            original = """
featuresNeeded = [CodeDog]
initCode = `sharedCount <- 10; singleton.marker <- 42`
deinitCode = `print("library-close\\n")`
struct GLOBAL {
    our Counter:: singleton
    me int: sharedCount <- 0
    me int: sharedValue() <- {return(sharedCount)}
    me int: dispatch(their Counter: counter) <- {return(counter.next())}
}
struct Counter: virtualMethods=[next] {
    me int: marker <- 0
    me int: next() <- {sharedCount <+- 1; return(sharedCount)}
}
"""
            library.write_text(original)
            (root / "Library.dog").write_text("""
LibraryBuild: Platform='Local' ExportInterface='true';
FileName = "counter"
ProgramOrLibrary = "sharedlibrary"
featuresNeeded = [Counter]
""")
            (root / "Client.dog").write_text("""
ClientBuild: Platform='Local' LinkedInterface='LibraryBuild/counter.interface.json';
FileName = "client"
ProgramOrLibrary = "program"
featuresNeeded = [Counter]
runCode = `me Counter: counter; me Child: child; print(counter.next(), ":", sharedValue(), ":", singleton.marker, ":", dispatch(child), "\\n")`
deinitCode = `print("client-close\\n")`
struct Child: inherits=Counter {me int: next() <- {return(99)}}
""")

            def build(file):
                result = subprocess.run([sys.executable, str(CODEDOG), file], cwd=root,
                                        text=True, capture_output=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("Marker: Build Successful", result.stdout)

            def run():
                return subprocess.run([str(root / "ClientBuild/client")], cwd=root,
                                      text=True, capture_output=True, timeout=10)

            build("Library.dog")
            build("Client.dog")
            self.assertEqual(run().stdout.strip(), "11:11:42:99\nclient-close\nlibrary-close")
            client = root / "ClientBuild/client"
            before = hashlib.sha256(client.read_bytes()).hexdigest()
            interface = root / "LibraryBuild/counter.hpp"
            public = interface.read_bytes()
            library.write_text(original.replace("sharedCount <+- 1", "sharedCount <+- 2"))
            build("Library.dog")
            self.assertEqual(interface.read_bytes(), public)
            self.assertEqual(run().stdout.strip(), "12:12:42:99\nclient-close\nlibrary-close")
            self.assertEqual(hashlib.sha256(client.read_bytes()).hexdigest(), before)
            # A changed layout must not run against an executable compiled for
            # the old declarations, even when its method signatures match.
            library.write_text(original.replace("struct Counter: virtualMethods=[next] {", "struct Counter: virtualMethods=[next] { me int: added <- 0"))
            build("Library.dog")
            failed = run()
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("counter_abi_", failed.stderr)
            build("Client.dog")
            self.assertEqual(run().stdout.strip(), "11:11:42:99\nclient-close\nlibrary-close")


if __name__ == "__main__":
    unittest.main()
