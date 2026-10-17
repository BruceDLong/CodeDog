"""Shared-owner inspection must not itself add an owner."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import codeDogParser
from codeGenerator import CodeGenerator
from xlator_CPP import Xlator_CPP
from xlator_Java import Xlator_Java
from xlator_Kotlin import Xlator_Kotlin
from xlator_Swift import Xlator_Swift


ROOT = Path(__file__).resolve().parents[1]


class SharedOwnershipTests(unittest.TestCase):
    def generator(self, translator=Xlator_CPP):
        generator = CodeGenerator()
        generator.clearBuild()
        generator.xlator = translator()
        generator.xlator.codeGen = generator
        generator.classStore = [{}, []]
        generator.currentObjName = 'GLOBAL'
        generator.localVarsAllocated = [
            [name, {'owner': owner, 'fieldType': ['Widget'], 'arraySpec': None, 'paramList': None}]
            for name, owner in [('shared', 'our'), ('borrowed', 'their'), ('owned', 'my'), ('value', 'me')]]
        return generator

    def code_ref(self, generator, source):
        ref = codeDogParser.varRef.parse_string(source, parse_all=True)[0]
        return generator.codeItemRef(ref, 'RVAL', None, 'RVAL', {})

    def assert_rejected(self, generator, source, message):
        with patch('codeGenerator.cdErr', side_effect=SystemExit) as error:
            with self.assertRaises(SystemExit):
                self.code_ref(generator, source)
        error.assert_called_once()
        self.assertIn(message, error.call_args.args[0])

    def test_count_has_integer_value_type(self):
        code, type_spec, _, _ = self.code_ref(self.generator(), 'sharedUseCount(shared)')
        self.assertEqual(code, '(shared).use_count()')
        self.assertEqual(type_spec['owner'], 'me')
        self.assertEqual(type_spec['fieldType'], 'int64')

    def test_rejects_incorrect_argument_count(self):
        for source in ['sharedUseCount()', 'sharedUseCount(shared, shared)']:
            with self.subTest(source=source):
                self.assert_rejected(self.generator(), source, 'requires exactly one')

    def test_rejects_nonshared_values(self):
        for value in ['borrowed', 'owned', 'value', 'shared!', 'NULL', '1']:
            with self.subTest(value=value):
                self.assert_rejected(self.generator(), f'sharedUseCount({value})', "requires an 'our' value")

    def test_rejects_backends_without_shared_owner_counts(self):
        for translator in [Xlator_Java, Xlator_Kotlin, Xlator_Swift]:
            with self.subTest(translator=translator):
                self.assert_rejected(self.generator(translator), 'sharedUseCount(shared)', 'is not supported by')

    @unittest.skipUnless(shutil.which('g++'), 'C++ compiler required')
    def test_generated_ownership_lifetimes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy(ROOT / 'Tests/sharedOwnership.dog', root / 'Probe.dog')
            build = subprocess.run(
                [sys.executable, str(ROOT / 'codeDog'), 'Probe.dog'], cwd=root,
                capture_output=True, text=True, timeout=60)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            self.assertIn('Marker: Build Successful', build.stdout)
            run = subprocess.run([str(root / 'LocalBuild/sharedOwnership')], cwd=root,
                                 capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(run.stdout.strip(), 'PASS: shared ownership')


if __name__ == '__main__':
    unittest.main()
