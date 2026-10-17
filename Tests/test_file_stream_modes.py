"""Exercise standard file modes through a generated CodeDog program."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODES = ['r', 'rb', 'r+', 'r+b', 'rb+', 'w', 'wb', 'w+', 'w+b', 'wb+',
         'a', 'ab', 'a+', 'a+b', 'ab+']


class FileStreamModeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('g++'), 'C++ compiler required')
    def test_standard_modes_and_legacy_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy(ROOT/'Tests/fileStreamModes.dog', root/'Probe.dog')
            for mode in MODES:
                (root/f'existing-{mode}.txt').write_bytes(b'base\n')
            for name in ['legacy', 'old-new', 'old-append', 'invalid', 'once']:
                (root/f'{name}.txt').write_bytes(b'base\n')
            readonly = root/'readonly.txt'
            readonly.write_bytes(b'readonly\n')
            readonly.chmod(0o444)
            build = subprocess.run([sys.executable, str(ROOT/'codeDog'), 'Probe.dog'],
                                   cwd=root, capture_output=True, text=True, timeout=60)
            self.assertEqual(build.returncode, 0, build.stdout+build.stderr)
            self.assertIn('Marker: Build Successful', build.stdout)
            run = subprocess.run([str(root/'LocalBuild/fileStreamModes')], cwd=root,
                                 capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
            self.assertEqual(run.stdout.strip(), 'PASS: file stream modes')
            for mode in MODES:
                with self.subTest(mode=mode):
                    expected = b'base\n' if mode in ['r', 'rb'] else b'new!\n'
                    if mode.startswith('a'):
                        expected = b'base\nnew!\n'
                    self.assertEqual((root/f'existing-{mode}.txt').read_bytes(), expected)
                    missing = root/f'missing-{mode}.txt'
                    if mode.startswith('r'):
                        self.assertFalse(missing.exists())
                    else:
                        self.assertEqual(missing.read_bytes(), b'created\n')
            self.assertEqual(readonly.read_bytes(), b'readonly\n')
            self.assertEqual((root/'invalid.txt').read_bytes(), b'base\n')
            self.assertEqual((root/'legacy.txt').read_bytes(), b'base\ntail\n')
            self.assertFalse((root/'legacy-missing.txt').exists())
            self.assertEqual((root/'old-new.txt').read_bytes(), b'new\n')
            self.assertEqual((root/'old-append.txt').read_bytes(), b'base\ntail\n')


if __name__ == '__main__':
    unittest.main()
