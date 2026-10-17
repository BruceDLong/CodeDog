"""Check the native exception boundary of ordinary CodeDog error calls."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StandardErrorTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('g++'), 'C++ compiler required')
    def test_types_messages_and_lock_unwinding(self):
        source = '''
LocalBuild: Platform='Local';
FileName = "standardErrors"
ProgramOrLibrary = "program"
featuresNeeded = [Threads]
struct ErrorProbe {
    me Mutex: guard
    void: badArgument() <- {
        protect(guard){throwInvalidArgument("bad input")}
    }
    void: overflow() <- {
        protect(guard){throwOverflowError("capacity exhausted")}
    }
}
'''
        # CodeDog has no catch syntax. Observe its generated methods from the
        # native caller boundary without adding native CodeDog assertion bodies.
        driver = r'''
#define main generatedMain
#include "LocalBuild/standardErrors.cpp"
#undef main
bool released(ErrorProbe& probe) {
    bool free = false;
    std::thread worker([&]{
        free = probe.guard.try_lock();
        if(free) probe.guard.unlock();
    });
    worker.join(); return free;
}
int main() {
    ErrorProbe probe;
    try {probe.badArgument(); std::cout << "missing invalid error\n";}
    catch(const std::invalid_argument& error) {
        std::cout << "invalid:" << error.what() << ':' << released(probe) << '\n';
    }
    try {probe.overflow(); std::cout << "missing overflow error\n";}
    catch(const std::overflow_error& error) {
        std::cout << "overflow:" << error.what() << ':' << released(probe) << '\n';
    }
}
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'Probe.dog').write_text(source)
            commands = [[sys.executable, str(ROOT/'codeDog'), 'Probe.dog'],
                        ['g++', '-std=c++17', '-pthread', 'driver.cpp', '-o', 'driver']]
            (root/'driver.cpp').write_text(driver)
            for command in commands:
                result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                if command == commands[0]:
                    self.assertIn('Marker: Build Successful', result.stdout)
            run = subprocess.run([str(root/'driver')], cwd=root, capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
            self.assertEqual(run.stdout, 'invalid:bad input:1\noverflow:capacity exhausted:1\n')


if __name__ == '__main__':
    unittest.main()
