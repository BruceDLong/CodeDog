"""Parse, generate, compile and execute the same exception flow on each backend."""
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from pyparsing import ParseBaseException

import codeDogParser
from codeGenerator import CodeGenerator
from xlator_CPP import Xlator_CPP
from xlator_Java import Xlator_Java
from xlator_Kotlin import Xlator_Kotlin
from xlator_Swift import Xlator_Swift


ROOT = Path(__file__).resolve().parents[1]
TRANSLATORS = {'CPP': Xlator_CPP, 'Java': Xlator_Java,
               'Kotlin': Xlator_Kotlin, 'Swift': Xlator_Swift}


def generate(source, language):
    with redirect_stdout(io.StringIO()):
        _, _, classes, _ = codeDogParser.parseCodeDogString(source, {}, [], {}, 'try/catch regression')
        generator = CodeGenerator()
        generator.clearBuild()
        generator.xlator = TRANSLATORS[language]()
        generator.xlator.codeGen = generator
        generator.classStore = classes
        generator.tagStore = {}
        generator.buildTags = {}
        generator.modeStringsAcc = ''
        globals_code = ''
        if 'GLOBAL' in classes[0]:
            if generator.xlator.doesLangHaveGlobals:
                generator.currentObjName = 'GLOBAL'
                globals_code = ''.join(generator.codeStructFields('GLOBAL', [{}, {}], ''))
            else:
                record = generator.codeOneStruct([{}, {}], '', 'GLOBAL')
                # GLOBAL's generated fields reference this runtime container.
                globals_code = generator.codeModeStringsStruct() + record[2] + record[3]
        record = generator.codeOneStruct([{}, {}], '', 'Probe')
    return globals_code + record[2] + record[3], generator


def portable_probe(language):
    # Exercise the actual GLOBAL library implementations while avoiding
    # pulling platform GUI/logger dependencies into a compiler regression.
    library = (ROOT / f'LIBS/CodeDog.{language}.Lib.dog').read_text()
    helpers = '\n'.join(re.findall(
        r'    void: throw(?:InvalidArgument|OverflowError)\([^\n]+?<- <%.*?%>',
        library, re.DOTALL))
    if len(re.findall(r'void: throw', helpers)) != 2:
        raise AssertionError('Missing standard error helpers for ' + language)
    native = {
        'CPP': 'throw std::runtime_error("native");',
        'Java': 'throw new java.io.IOException("native");',
        'Kotlin': 'throw java.io.IOException("native")',
        'Swift': 'throw NSError(domain: "Probe", code: 1, userInfo: [NSLocalizedDescriptionKey: "native"])',
    }[language]
    converter = 'Native.value()' if language == 'Java' else 'nativeValue()'
    source = '''struct GLOBAL {
''' + helpers + '''
}
struct Probe {
    me string: nativeFailure(): throws=true <- <%{''' + native + '''}%>
    me bool: nativeBool(): throws=true <- <%{''' + native + '''}%>
    me string: nativeConverted(): throws=true <- <%!%G''' + converter + '''%>
    me string: propagate(): throws=true <- {return(nativeFailure())}
    me string: echo(me string: text) <- {return(text)}
    me string: successfulReturn() <- {
        try {return("ok")} catch(error) {return(error)}
    }
    me string: failedReturn() <- {
        try {return(nativeFailure())} catch(error) {return(error)}
    }
    me string: run() <- {
        me string: trace <- ""
        me string: error <- "outer"
        me string: cdCaughtException <- "collision"
        me string: cdCatchMessage <- "collision"
        try {trace <+- successfulReturn()} catch(error) {trace <+- "WRONG"}
        try {throwInvalidArgument("invalid")} catch(error) {trace <+- error}
        try {throwOverflowError("overflow")} catch(error) {trace <+- error}
        try {nativeFailure(); trace <+- "WRONG"} catch(error) {trace <+- error}
        try {propagate()} catch(error) {trace <+- error}
        try {me string: value <- nativeConverted(); trace <+- "WRONG"} catch(error) {trace <+- error}
        try {trace <+- echo(nativeConverted())} catch(error) {trace <+- error}
        try {trace <+- nativeConverted().size()} catch(error) {trace <+- error}
        me Probe: other
        try {other.propagate()} catch(error) {trace <+- error}
        try {
            if(false and nativeBool()) {trace <+- "WRONG"}
            trace <+- "short"
            if(true and nativeBool()) {trace <+- "WRONG"}
        } catch(error) {trace <+- error}
        try {
            if(true or nativeBool()) {trace <+- "short"}
            if(false or nativeBool()) {trace <+- "WRONG"}
        } catch(error) {trace <+- error}
        try {
            try {throwInvalidArgument("inner")} catch(error) {
                trace <+- error
                try {throwOverflowError("nested")} catch(error) {trace <+- error}
                trace <+- error
                throwOverflowError("outerCatch")
            }
        } catch(error) {trace <+- error}
        try {throwInvalidArgument("ignored")} catch {trace <+- "bare"}
        me int: count <- 0
        while(count < 3) {
            ++count
            try {nativeFailure()} catch {continue()}
            trace <+- "WRONG"
        }
        while(true) {try {nativeFailure()} catch {break()}}
        trace <+- error
        trace <+- failedReturn()
        return(trace)
    }
}'''
    return source


class TryCatchParserTests(unittest.TestCase):
    def test_nested_and_bare_handlers(self):
        parsed = codeDogParser.tryAction.parse_string(
            'try {try {work()} catch(inner) {print(inner)}} catch {}', parse_all=True)[0]
        action = codeDogParser.extractActItem('probe', parsed)
        self.assertEqual(action['typeOfAction'], 'try')
        self.assertIsNone(action['errorName'])
        self.assertEqual(action['tryBody'][0]['errorName'], 'inner')

    def test_incomplete_and_multiple_handlers_rejected(self):
        for text in ('try {}', 'catch {}', 'try {} catch()',
                     'try {} catch(error)', 'try {} catch(42) {}',
                     'try {} catch {} catch {}'):
            with self.subTest(text=text), self.assertRaises(ParseBaseException):
                codeDogParser.actionSeq.parse_string('{' + text + '}', parse_all=True)

    def test_catch_variable_does_not_escape(self):
        source = 'struct Probe {void: run() <- {try {} catch(error) {print(error)}}}'
        for language in TRANSLATORS:
            with self.subTest(language=language):
                _, generator = generate(source, language)
                self.assertEqual(generator.CheckFunctionsLocalVarArgList('error'), 0)

    def test_throwing_declaration_and_invalid_tags(self):
        _, _, classes, _ = codeDogParser.parseCodeDogString(
            'struct Probe {void: external(): throws=true}', {}, [], {}, 'throwing declaration')
        self.assertTrue(classes[0]['Probe']['fields'][0]['typeSpec']['throws'])
        for text in ('void: run(): throws=maybe <- {}', 'me int: value: throws=true'):
            with self.subTest(text=text), redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                codeDogParser.parseCodeDogString('struct Probe {' + text + '}', {}, [], {}, 'bad throws tag')

    def test_generated_backends_and_throwing_calls(self):
        for language in TRANSLATORS:
            with self.subTest(language=language):
                code, _ = generate(portable_probe(language), language)
                self.assertIn('catch', code)
                if language == 'Swift':
                    self.assertIn('throws -> String', code)
                    self.assertIn('(try nativeFailure())', code)
                    self.assertIn('(try nativeValue())', code)
                elif language == 'Java':
                    self.assertIn('throws Exception', code)


class TryCatchRuntimeTests(unittest.TestCase):
    expected = ('okinvalidoverflownativenativeconvertedconvertedconvertednative'
                'shortnativeshortnativeinnernestedinnerouterCatchbareouternative')

    def run_command(self, command, root):
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    @unittest.skipUnless(shutil.which('g++'), 'C++ compiler required')
    def test_cpp(self):
        code, _ = generate(portable_probe('CPP'), 'CPP')
        source = '''#include <string>
#include <stdexcept>
#include <iostream>
using namespace std;
string nativeValue(){throw runtime_error("converted");}
''' + code + '\nint main(){Probe p; cout << p.run();}\n'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'probe.cpp').write_text(source)
            self.run_command(['g++', '-std=c++17', 'probe.cpp', '-o', 'probe'], root)
            self.assertEqual(self.run_command([str(root/'probe')], root), self.expected)

    @unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'JDK required')
    def test_java(self):
        code, _ = generate(portable_probe('Java'), 'Java')
        source = code + '''
class Native {static String value() throws java.io.IOException {throw new java.io.IOException("converted");}}
class Main {public static void main(String[] args){System.out.print(new Probe().run());}}
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'Main.java').write_text(source)
            self.run_command(['javac', 'Main.java'], root)
            self.assertEqual(self.run_command(['java', '-cp', str(root), 'Main'], root), self.expected)

    def test_kotlin(self):
        compiler = os.environ.get('KOTLINC') or shutil.which('kotlinc')
        if not compiler or not shutil.which('java'):
            self.skipTest('Kotlin compiler and Java required; KOTLINC may name its script')
        code, _ = generate(portable_probe('Kotlin'), 'Kotlin')
        source = '''fun nativeValue(): String {throw java.io.IOException("converted")}
''' + code + '\nfun main(){print(Probe().run())}\n'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'Probe.kt').write_text(source)
            command = [compiler] if os.access(compiler, os.X_OK) else ['bash', compiler]
            self.run_command(command + ['Probe.kt', '-include-runtime', '-d', 'probe.jar'], root)
            self.assertEqual(self.run_command(['java', '-jar', 'probe.jar'], root), self.expected)

    def test_swift(self):
        compiler = os.environ.get('SWIFTC') or shutil.which('swiftc')
        if not compiler:
            self.skipTest('Swift compiler required')
        code, _ = generate(portable_probe('Swift'), 'Swift')
        source = '''import Foundation
func nativeValue() throws -> String {throw NSError(domain: "Probe", code: 1, userInfo: [NSLocalizedDescriptionKey: "converted"])}
''' + code + '\nprint(Probe().run(), terminator: "")\n'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'probe.swift').write_text(source)
            self.run_command([compiler, '-module-cache-path', str(root/'cache'), 'probe.swift', '-o', 'probe'], root)
            self.assertEqual(self.run_command([str(root/'probe')], root), self.expected)

    @unittest.skipUnless(shutil.which('g++'), 'C++ compiler required')
    def test_cpp_full_build_native_nonstandard_exception_and_lock_cleanup(self):
        source = r'''
LocalBuild: Platform='Local';
FileName = "tryCatch"
ProgramOrLibrary = "program"
featuresNeeded = [Threads]
runCode = `me Probe: probe; probe.run()`
struct Probe {
    me Mutex: guard
    void: nonstandard() <- <%{throw 42;}%>
    void: checkUnlocked() <- <%{
        bool unlocked = false;
        std::thread worker([&]{unlocked = guard.try_lock(); if(unlocked) guard.unlock();});
        worker.join();
        if(!unlocked) std::abort();
    }%>
    void: run() <- {
        try {protect(guard) {throwInvalidArgument("locked")}}
        catch(error) {checkUnlocked(); print(error, "\n")}
        try {nonstandard()} catch(error) {print(error, "\n")}
        try {nonstandard()} catch {print("bare\n")}
    }
}
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'Probe.dog').write_text(source)
            output = self.run_command([sys.executable, str(ROOT/'codeDog'), 'Probe.dog'], root)
            self.assertIn('Marker: Build Successful', output)
            self.assertEqual(self.run_command([str(root/'LocalBuild/tryCatch')], root),
                             'locked\nUnknown native exception\nbare\n')


if __name__ == '__main__':
    unittest.main()
