import unittest

import codeDogParser
from pyparsing import ParseBaseException


class TestParserRanges(unittest.TestCase):
    def _contains_token(self, node, token):
        if isinstance(node, str):
            return node == token
        try:
            return any(self._contains_token(child, token) for child in node)
        except TypeError:
            return False

    def _extract_with_each(self, src):
        parsed = codeDogParser.withEachAction.parse_string(src, parse_all=True)[0]
        return codeDogParser.extractActItem("testFunc", parsed)

    def test_num_range_end_expr_keeps_plus_at_plus_level(self):
        act = self._extract_with_each(
            "withEach idx in range numDefsBefore .. numDefsBefore+numAdded{ }"
        )

        self.assertEqual(act["kind"], "withEach")
        self.assertEqual(act["source"]["kind"], "numRange")

        rs = act["source"]["rangeSpec"]
        self.assertEqual(len(rs["rangeStart"]), 1)
        self.assertEqual(len(rs["rangeEnd"]), 1)

        end_expr = rs["rangeEnd"][0]
        self.assertTrue(self._contains_token(end_expr, "+"))

    def test_traversal_keys_range_end_expr_keeps_plus(self):
        act = self._extract_with_each(
            "withEach (k,v) in wordToModel keys: a .. b+delta{ }"
        )

        self.assertEqual(act["kind"], "withEach")
        self.assertEqual(act["source"]["kind"], "traversal")
        self.assertIsNotNone(act["source"]["rangeClause"])
        self.assertEqual(act["source"]["rangeClause"]["mode"], "keys")

        rs = act["source"]["rangeClause"]["range"]
        self.assertEqual(len(rs["rangeStart"]), 1)
        self.assertEqual(len(rs["rangeEnd"]), 1)

        end_expr = rs["rangeEnd"][0]
        self.assertTrue(self._contains_token(end_expr, "+"))

    def test_num_range_inclusive_operator_is_preserved(self):
        act = self._extract_with_each("withEach idx in range 1 ..= 10{ }")
        rs = act["source"]["rangeSpec"]
        self.assertTrue(bool(getattr(rs, "inclusiveOp", False)))

    def test_num_range_colon_form_rejected(self):
        with self.assertRaises(ParseBaseException):
            codeDogParser.withEachAction.parse_string(
                "withEach idx in range: 1 .. 10{ }", parse_all=True
            )


if __name__ == "__main__":
    unittest.main()
