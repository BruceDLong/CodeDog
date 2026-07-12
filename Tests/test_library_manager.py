import unittest

import libraryMngr


class TestLibraryManager(unittest.TestCase):
    def test_child_libraries_require_dot_separator(self):
        old_lib_paths = libraryMngr.libPaths[:]
        try:
            libraryMngr.libPaths = [
                "/libs/ReactGUI.Lib.dog",
                "/libs/ReactGUI.CPP.Lib.dog",
                "/libs/ReactGUI.CPP.GNU.Lib.dog",
                "/libs/ReactGUI_Render3D.Lib.dog",
            ]

            self.assertEqual(
                libraryMngr.findLibraryChildren("ReactGUI"),
                ["/libs/ReactGUI.CPP.Lib.dog"],
            )
        finally:
            libraryMngr.libPaths = old_lib_paths


if __name__ == "__main__":
    unittest.main()
