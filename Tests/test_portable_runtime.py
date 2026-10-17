"""Compile generated runtime helpers, including unsigned bounds and lock release."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import codeDogParser
from codeGenerator import CodeGenerator
from xlator_CPP import Xlator_CPP
from xlator_Java import Xlator_Java
from xlator_Swift import Xlator_Swift
from xlator_Kotlin import Xlator_Kotlin

ROOT = Path(__file__).resolve().parents[1]


def parser_source(language, translator):
    common = (ROOT / 'LIBS/CodeDog.Lib.dog').read_text().split('struct UInt64Parser{', 1)[1].split('\nstruct _atomic_uint64', 1)[0]
    native = (ROOT / f'LIBS/CodeDog.{language}.Lib.dog').read_text().split('struct UInt64Parser{', 1)[1]
    _, _, classes, _ = codeDogParser.parseCodeDogString(
        'struct UInt64Parser{' + common + '\nstruct UInt64Parser{' + native,
        {}, [], {}, 'checked unsigned parser')
    generator = CodeGenerator()
    generator.clearBuild()
    generator.xlator = translator()
    generator.xlator.codeGen = generator
    generator.classStore = classes
    generator.tagStore = {}
    generator.buildTags = {}
    record = generator.codeOneStruct([{}, {}], '', 'UInt64Parser')
    return record[2] + record[3]


class PortableRuntimeTests(unittest.TestCase):
    def run_command(self, args, root):
        result = subprocess.run(args, cwd=root, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which('g++'), 'C++ compiler required')
    def test_cpp_unsigned_parser(self):
        source = '#include <string>\n#include <cstdint>\n#include <stdexcept>\n#include <cassert>\nusing namespace std;\n'
        source += parser_source('CPP', Xlator_CPP)
        source += '''
int main(){
    UInt64Parser p;
    assert(p.parse("0") && p.value == 0);
    assert(p.parse("00042") && p.value == 42);
    assert(p.parse("9223372036854775808") && p.value == (uint64_t(1)<<63));
    assert(p.parse("18446744073709551615") && p.value == UINT64_MAX);
    for(const string s: {"", "-1", "+1", " 1", "1 ", "1x", "1.0", "18446744073709551616", "99999999999999999999999", "１２"}) {
        assert(!p.parse(s)); assert(p.value == UINT64_MAX);
    }
    assert(p.parse("7") && p.value == 7);
}
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'probe.cpp').write_text(source)
            self.run_command(['g++', '-std=c++14', 'probe.cpp', '-o', 'probe'], root)
            self.run_command([str(root/'probe')], root)

    @unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'JDK required')
    def test_java_unsigned_parser(self):
        source = parser_source('Java', Xlator_Java) + '''
class Probe {
    static void check(boolean ok){if(!ok) throw new AssertionError();}
    public static void main(String[] args){
        UInt64Parser p = new UInt64Parser();
        check(p.parse("0") && p.value == 0);
        check(p.parse("00042") && p.value == 42);
        check(p.parse("9223372036854775808") && p.value == Long.MIN_VALUE);
        check(p.parse("18446744073709551615") && p.value == -1L);
        for(String s: new String[]{"", "-1", "+1", " 1", "1 ", "1x", "1.0", "18446744073709551616", "99999999999999999999999", "１２"}){
            check(!p.parse(s)); check(p.value == -1L);
        }
        check(p.parse("7") && p.value == 7);
    }
}
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'Probe.java').write_text(source)
            self.run_command(['javac', 'Probe.java'], root)
            self.run_command(['java', '-cp', str(root), 'Probe'], root)

    @unittest.skipUnless(shutil.which('swiftc'), 'Swift compiler required')
    def test_swift_unsigned_parser(self):
        source = 'import Foundation\n' + parser_source('Swift', Xlator_Swift) + '''
let p = UInt64Parser()
precondition(p.parse("0") && p.value == 0)
precondition(p.parse("00042") && p.value == 42)
precondition(p.parse("9223372036854775808") && p.value == (UInt64(1)<<63))
precondition(p.parse("18446744073709551615") && p.value == UInt64.max)
for s in ["", "-1", "+1", " 1", "1 ", "1x", "1.0", "18446744073709551616", "99999999999999999999999", "１２"] {
    precondition(!p.parse(s)); precondition(p.value == UInt64.max)
}
precondition(p.parse("7") && p.value == 7)
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'probe.swift').write_text(source)
            self.run_command(['swiftc', '-module-cache-path', str(root/'cache'), 'probe.swift', '-o', 'probe'], root)
            self.run_command([str(root/'probe')], root)

    @unittest.skipUnless(shutil.which('kotlinc') and shutil.which('java'), 'Kotlin compiler required')
    def test_kotlin_unsigned_parser(self):
        source = parser_source('Kotlin', Xlator_Kotlin) + '''
fun main(){
    val p = UInt64Parser()
    check(p.parse("0") && p.value == 0L)
    check(p.parse("00042") && p.value == 42L)
    check(p.parse("9223372036854775808") && p.value == Long.MIN_VALUE)
    check(p.parse("18446744073709551615") && p.value == -1L)
    for(s in listOf("", "-1", "+1", " 1", "1 ", "1x", "1.0", "18446744073709551616", "99999999999999999999999", "１２")) {
        check(!p.parse(s)); check(p.value == -1L)
    }
    check(p.parse("7") && p.value == 7L)
}
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'Probe.kt').write_text(source)
            self.run_command(['kotlinc', 'Probe.kt', '-include-runtime', '-d', 'probe.jar'], root)
            self.run_command(['java', '-jar', 'probe.jar'], root)

    @unittest.skipUnless(shutil.which('g++'), 'C++ compiler required')
    def test_pre_deinit_stops_application_before_library_teardown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'Teardown.Lib.dog').write_text(r'''
featuresNeeded = [CodeDog]
deinitCode = `print("library-close\n")`
struct Teardown{}
''')
            source = r'''
LocalBuild: Platform='Local';
FileName = "teardownProbe"
ProgramOrLibrary = "program"
featuresNeeded = [Teardown]
preDeinitCode = `print("application-stop\n")`
deinitCode = `print("application-close\n")`
'''
            for with_hook in (True, False):
                with self.subTest(with_hook=with_hook):
                    text = source if with_hook else source.replace('preDeinitCode = `print("application-stop\\n")`', '')
                    (root/'Probe.dog').write_text(text)
                    self.run_command([sys.executable, str(ROOT/'codeDog'), 'Probe.dog'], root)
                    result = subprocess.run([str(root/'LocalBuild/teardownProbe')], cwd=root,
                                            capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    expected = 'library-close\napplication-close\n'
                    if with_hook:
                        expected = 'application-stop\n' + expected
                    self.assertEqual(result.stdout, expected)

    @unittest.skipUnless(shutil.which('g++'), 'C++ compiler required')
    def test_file_stream_accepts_literal_and_evaluates_expression_once(self):
        source = r'''
LocalBuild: Platform='Local';
FileName = "streamProbe"
ProgramOrLibrary = "program"
featuresNeeded = [CodeDog]
runCode = `
    me FileStream: output
    output.openNew("output.txt")
    output.write("header\n")
    output.write(nextRow()+"\n")
    output.flush()
    output.close()
    print(toString(calls))
`
struct GLOBAL{
    me int: calls
    me string: nextRow() <- {calls <+- 1; return("row")}
}
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'Probe.dog').write_text(source)
            self.run_command([sys.executable, str(ROOT/'codeDog'), 'Probe.dog'], root)
            self.assertTrue((root/'LocalBuild/streamProbe').is_file())
            result = subprocess.run([str(root/'LocalBuild/streamProbe')], cwd=root,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, '1')
            self.assertEqual((root/'output.txt').read_bytes(), b'header\nrow\n')

    @unittest.skipUnless(shutil.which('g++'), 'C++ compiler required')
    def test_rearmed_timer_emits_one_wrapper_and_keeps_target(self):
        src = '''struct TimerProbe{
            me int: ticks
            void: poll() <- {ticks <+- 1; if(ticks<3){callOnce("TimerProbe", self, "poll", 50)}}
            void: start() <- {callOnce("TimerProbe", self, "poll", 50)}
        }'''
        _, _, classes, _ = codeDogParser.parseCodeDogString(src, {}, [], {}, 'timer regression')
        generator = CodeGenerator()
        generator.clearBuild()
        generator.xlator = Xlator_CPP()
        generator.xlator.codeGen = generator
        generator.classStore = classes
        generator.tagStore = {}
        generator.buildTags = {}
        record = generator.codeOneStruct([{}, {}], '', 'TimerProbe')
        source = '''
#include <cassert>
#include <deque>
struct Callback {int (*call)(void*); void* target;};
std::deque<Callback> callbacks;
void CodeDogCallPeriodically(int millis, int (*call)(void*), void* target){
    assert(millis==50); callbacks.push_back({call, target});
}
''' + record[1] + generator.funcDeclAcc + record[2] + generator.funcDefnAcc + record[3] + '''
int main(){
    TimerProbe first, second; first.start(); second.start();
    int count = 0;
    while(!callbacks.empty()){
        auto next = callbacks.front(); callbacks.pop_front();
        assert(next.call(next.target)==false); assert(++count<=6);
    }
    assert(count==6 && first.ticks==3 && second.ticks==3);
}
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'probe.cpp').write_text(source)
            self.run_command(['g++', '-std=c++14', 'probe.cpp', '-o', 'probe'], root)
            self.run_command([str(root/'probe')], root)
        generator.clearBuild()
        generator.codeOneStruct([{}, {}], '', 'TimerProbe')
        self.assertIn('cb_once_TimerProbe_poll', generator.funcDefnAcc)

    @unittest.skipUnless(shutil.which('g++'), 'C++ compiler required')
    def test_protect_accepts_recursive_mutexes_and_releases_on_exit(self):
        translator = Xlator_CPP()
        ordinary = translator.codeProtectBlock('mutex', '        return;\n', '    ')
        nested = translator.codeProtectBlock('(*pointer)', '            throw 42;\n', '        ')
        recursive = translator.codeProtectBlock('mutex', nested, '    ')
        source = '''
#include <mutex>
#include <type_traits>
#include <thread>
#include <cassert>
void ordinary(std::mutex& mutex){
''' + ordinary + '''}
void recursive(std::recursive_mutex& mutex){
    auto* pointer = &mutex;
''' + recursive + '''}
template<class Mutex> void checkReleased(Mutex& mutex){
    bool released = false;
    std::thread other([&]{released = mutex.try_lock(); if(released) mutex.unlock();});
    other.join(); assert(released);
}
int main(){
    std::mutex mutex; ordinary(mutex); checkReleased(mutex);
    std::recursive_mutex nested;
    try{recursive(nested); assert(false);}catch(int value){assert(value==42);}
    checkReleased(nested);
}
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'probe.cpp').write_text(source)
            self.run_command(['g++', '-std=c++14', '-pthread', 'probe.cpp', '-o', 'probe'], root)
            self.run_command([str(root/'probe')], root)

    @unittest.skipUnless(shutil.which('g++'), 'C++ compiler required')
    def test_input_wait_lock_order_nested_scopes_and_exceptions(self):
        # Test the native synchronization boundary directly; language integration
        # is exercised by the generated IOBuffer and Proteus tests.
        source = '''
#include <mutex>
#include <condition_variable>
#include <thread>
#include <chrono>
#include <vector>
#include <future>
#include <cassert>
''' + (ROOT/'LIBS/Threads.InputWait.inc').read_text() + r'''
bool available(std::recursive_mutex& mutex) {
    return std::async(std::launch::async, [&]{
        if(!mutex.try_lock()) return false;
        mutex.unlock(); return true;
    }).get();
}
struct OrderedWake {
    std::recursive_mutex& model;
    std::mutex& buffer;
    std::thread contender;
    void wait(std::unique_lock<std::mutex>& lock) {
        std::promise<void> modelHeld, wakeReturned;
        auto held = modelHeld.get_future();
        auto waking = wakeReturned.get_future();
        lock.unlock();
        contender = std::thread([&, waking = std::move(waking)]() mutable {
            std::lock_guard<std::recursive_mutex> outer(model);
            modelHeld.set_value();
            waking.wait();
            std::lock_guard<std::mutex> inner(buffer);
        });
        held.wait();
        lock.lock();
        wakeReturned.set_value();
    }
};
struct ThrowingWait {
    void wait(std::unique_lock<std::mutex>&) { throw 42; }
};
int main() {
    std::recursive_mutex model, other;
    std::mutex buffer;
    {
        CodeDogInputLock first(&model), nested(&model), second(&other);
        assert(!available(model) && !available(other));
        {
            CodeDogInputPause pause;
            assert(available(model) && available(other));
            { CodeDogInputLock callback(&model); assert(!available(model)); }
            assert(available(model));
        }
        assert(!available(model) && !available(other));
        std::unique_lock<std::mutex> inner(buffer);
        OrderedWake wake{model, buffer, {}};
        codeDogWaitForInput(wake, inner);
        wake.contender.join();
        assert(inner.owns_lock() && !available(model) && !available(other));
        ThrowingWait throws;
        try { codeDogWaitForInput(throws, inner); assert(false); }
        catch(int value) { assert(value == 42); }
        assert(!inner.owns_lock() && !available(model) && !available(other));
        try { CodeDogInputPause pause; throw 7; } catch(int) {}
        assert(!available(model) && !available(other));
    }
    assert(available(model) && available(other));
    // Ordinary users need no model lock or registration.
    {
        std::condition_variable cv;
        std::unique_lock<std::mutex> inner(buffer);
        bool ready = false;
        std::thread producer([&]{
            std::lock_guard<std::mutex> held(buffer);
            ready = true; cv.notify_one();
        });
        while(!ready) codeDogWaitForInput(cv, inner);
        inner.unlock(); producer.join();
    }
}
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'probe.cpp').write_text(source)
            self.run_command(['g++', '-std=c++14', '-pthread', 'probe.cpp', '-o', 'probe'], root)
            self.run_command([str(root/'probe')], root)


    @unittest.skipUnless(shutil.which('g++'), 'C++ compiler required')
    def test_generated_buffer_wait_releases_input_lock(self):
        source = r'''
LocalBuild: Platform='Local';
FileName = "inputWaitProbe"
ProgramOrLibrary = "program"
featuresNeeded = [IOBuffer]
runCode = `
    me ProbeMutex: mutex
    me strBuf: buffer; buffer.init("input-wait")
    me InputProducer: producer
    producer.mutex <- mutex; producer.buffer <- buffer
    if(true){
        me InputLock: outer{mutex}
        me InputLock: inner{mutex}
        producer.start()
        print(buffer.scrapeCID(0))
    }
    producer.waitForExit()
`
struct ProbeMutex: wraps=recursive_mutex{}
struct InputProducer: inherits=Threads {
    their ProbeMutex: mutex
    their strBuf: buffer
    void: run() <- {
        protect(mutex!){
            buffer!.putStr("hello")
            buffer!.close()
        }
    }
}
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'Probe.dog').write_text(source)
            self.run_command([sys.executable, str(ROOT/'codeDog'), 'Probe.dog'], root)
            result = subprocess.run([str(root/'LocalBuild/inputWaitProbe')], cwd=root,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, '5')


    @unittest.skipUnless(shutil.which('g++'), 'C++ compiler required')
    def test_generated_decimal_input(self):
        source = r'''
LocalBuild: Platform='Local';
FileName = "decimalInputProbe"
ProgramOrLibrary = "program"
featuresNeeded = [BigNumbers, IOBuffer]
runCode = `
    me FlexNum: number
    me List<string>: inputs <- ["08", "010", "08/09", "0.25", "-001.25", "+008", "184467440737095516160"]
    me List<string>: expected <- ["8", "10", "8/9", "0.25", "-1.25", "8", "184467440737095516160"]
    withEach idx in range 0 .. inputs.size(){
        if(!number.parseDecimal(inputs[idx]) or toString(number)!=expected[idx]){
            print("bad conversion: "+inputs[idx]+" -> "+toString(number)+"\n")
        }
    }
    number.parseDecimal("0.25")
    me List<string>: invalid <- ["", "+", "-", "1/", "1.", ".5", "1/0", "0/0", "1/00", "1.2.3", "1.2/3", "1/-2", "0x10", " 1", "1 ", "1 2", "1a", "１２"]
    withEach input in invalid{
        if(number.parseDecimal(input)){print("accepted: "+input+"\n")}
        if(toString(number)!="0.25" or number.decPlaces!=3){print("failed conversion changed value\n")}
    }
    number.parseDecimal("7")
    if(number.decPlaces!=-1 or toString(number)!="7"){print("integer retained decimal precision\n")}
    me List<string>: prefixes <- ["1/", "1/\n", "1.", "1. ", "08/09", "08/09 ", "1.25", "1.25 ", "123", "123 "]
    me List<int>: lengths <- [1, 1, 1, 1, 5, 5, 4, 4, 3, 3]
    withEach idx in range 0 .. prefixes.size(){
        me strBuf: buffer; buffer.init("decimal-prefix")
        buffer.putStr(prefixes[idx]); buffer.close()
        if(buffer.scrapeFlexNum(0)!=lengths[idx]){print("wrong prefix: "+prefixes[idx]+"\n")}
    }
    print("Decimal input passed")
`
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'Probe.dog').write_text(source)
            self.run_command([sys.executable, str(ROOT/'codeDog'), 'Probe.dog'], root)
            result = subprocess.run([str(root/'LocalBuild/decimalInputProbe')], cwd=root,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, 'Decimal input passed')



if __name__ == '__main__':
    unittest.main()
