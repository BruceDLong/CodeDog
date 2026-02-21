import unittest

import codeDogParser


class TestIncDecActions(unittest.TestCase):
    def _extract_action(self, src):
        parsed = codeDogParser.action.parse_string(src, parse_all=True)[0]
        return codeDogParser.extractActItem("testFunc", parsed)

    def _target_name(self, target):
        # target is parseResultsToListOfParseResults(varRef)
        # first segment -> first token should be identifier
        first_seg = target[0]
        if isinstance(first_seg, str):
            return first_seg
        token0 = first_seg[0]
        if isinstance(token0, str):
            return token0
        return token0[0]

    def test_prefix_increment_action(self):
        act = self._extract_action("++idx")
        self.assertEqual(act["typeOfAction"], "incDec")
        self.assertEqual(act["op"], "++")
        self.assertEqual(act["position"], "prefix")
        self.assertEqual(self._target_name(act["target"]), "idx")

    def test_postfix_increment_action(self):
        act = self._extract_action("idx++")
        self.assertEqual(act["typeOfAction"], "incDec")
        self.assertEqual(act["op"], "++")
        self.assertEqual(act["position"], "postfix")
        self.assertEqual(self._target_name(act["target"]), "idx")

    def test_prefix_decrement_action(self):
        act = self._extract_action("--idx")
        self.assertEqual(act["typeOfAction"], "incDec")
        self.assertEqual(act["op"], "--")
        self.assertEqual(act["position"], "prefix")
        self.assertEqual(self._target_name(act["target"]), "idx")

    def test_postfix_decrement_action(self):
        act = self._extract_action("idx--")
        self.assertEqual(act["typeOfAction"], "incDec")
        self.assertEqual(act["op"], "--")
        self.assertEqual(act["position"], "postfix")
        self.assertEqual(self._target_name(act["target"]), "idx")

    def test_action_seq_accepts_incdec_statements(self):
        parsed = codeDogParser.actionSeq.parse_string("{ ++a; b++; --c; d--; }", parse_all=True)
        self.assertTrue(bool(parsed))

    def test_expr_parses_pre_and_post_forms(self):
        for expr_src in ("++x", "x++", "--x", "x--", "a + x++", "++x + 1"):
            parsed = codeDogParser.expr.parse_string(expr_src, parse_all=True)
            self.assertTrue(bool(parsed), msg=expr_src)

    def test_expr_uses_incdec_rule_for_prefix_decrement(self):
        parsed = codeDogParser.expr.parse_string("--x", parse_all=True)
        self.assertIn("incDecPrefixExpr", parsed.dump())

    def test_assignment_rvalue_accepts_postfix_inc_expr(self):
        parsed = codeDogParser.action.parse_string("x <- y++", parse_all=True)
        self.assertTrue(bool(parsed))


if __name__ == "__main__":
    unittest.main()
