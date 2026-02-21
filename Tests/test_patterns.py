import unittest

import codeDogParser


class TestPatternExtraction(unittest.TestCase):
    def test_do_pattern_name_is_unwrapped(self):
        prog_spec = {}
        obj_names = []

        codeDogParser.parseCodeDogString(
            "do GeneratePtrSymbols(T)\n",
            prog_spec,
            obj_names,
            {},
            "pattern extraction test",
        )

        self.assertIn("GeneratePtrSymbols.0", prog_spec)
        self.assertEqual(prog_spec["GeneratePtrSymbols.0"]["name"], "GeneratePtrSymbols")


if __name__ == "__main__":
    unittest.main()
