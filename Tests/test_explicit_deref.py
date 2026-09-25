import io
import os
import unittest
from contextlib import redirect_stdout

import codeDogParser
from codeGenerator import CodeGenerator
from xlator_CPP import Xlator_CPP
from xlator_Java import Xlator_Java
from xlator_Kotlin import Xlator_Kotlin


class TestExplicitDeref(unittest.TestCase):
    def _parse_var_ref(self, src):
        return codeDogParser.varRef.parse_string(src, parse_all=True)[0]

    def _cpp_generator(self, class_store=None):
        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.xlator = Xlator_CPP()
        code_gen.xlator.codeGen = code_gen
        code_gen.classStore = class_store or [{}, []]
        code_gen.currentObjName = "GLOBAL"
        return code_gen

    def _generator(self, xlator, class_store=None):
        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.xlator = xlator
        code_gen.xlator.codeGen = code_gen
        code_gen.classStore = class_store or [{}, []]
        code_gen.currentObjName = "GLOBAL"
        return code_gen

    def _code_ref(self, code_gen, src):
        return code_gen.codeItemRef(self._parse_var_ref(src), "RVAL", None, "RVAL", {})

    def _code_action(self, code_gen, src):
        parsed = codeDogParser.action.parse_string(src, parse_all=True)[0]
        action = codeDogParser.extractActItem("testFunc", parsed)
        return code_gen.codeAction(action, "    ", None, {})

    def _enable_deref_warnings(self, code_gen):
        code_gen.tagStore = {"ExplicitDeref": "warn"}
        code_gen.buildTags = {}

    def _captured_stdout(self, func):
        output = io.StringIO()
        with redirect_stdout(output):
            func()
        return output.getvalue()

    def test_parser_accepts_postfix_deref_segments(self):
        self.assertEqual(self._parse_var_ref("p!").as_list(), [["p"], ["!"]])
        self.assertEqual(self._parse_var_ref("p!.field").as_list(), [["p"], ["!"], ["field"]])
        self.assertEqual(self._parse_var_ref("p[n]!").as_list()[-1], ["!"])

    def test_postfix_deref_does_not_steal_equality_operators(self):
        for src, op in (("p!=NULL", "!="), ("p!==q", "!==")):
            parsed = codeDogParser.expr.parse_string(src, parse_all=True)
            self.assertIn(op, parsed.dump())
            self.assertNotIn("deref", parsed.dump())

    def test_postfix_deref_can_precede_spaced_comparison(self):
        parsed = codeDogParser.expr.parse_string("p! == 1", parse_all=True)
        self.assertIn("deref", parsed.dump())
        self.assertIn("==", parsed.dump())

    def test_cpp_explicit_deref_lowers_to_referent(self):
        code_gen = self._cpp_generator()
        code_gen.localVarsAllocated = [
            ["p", {"owner": "their", "fieldType": "string", "arraySpec": None, "paramList": None}],
            ["sp", {"owner": "our", "fieldType": "string", "arraySpec": None, "paramList": None}],
            ["n", {"owner": "me", "fieldType": "int", "arraySpec": None, "paramList": None}],
        ]

        p_expr, p_type, _parent, _alt = self._code_ref(code_gen, "p!")
        self.assertEqual(p_expr, "(*p)")
        self.assertEqual(p_type["owner"], "me")

        sp_expr, sp_type, _parent, _alt = self._code_ref(code_gen, "sp!")
        self.assertEqual(sp_expr, "(*sp)")
        self.assertEqual(sp_type["owner"], "me")

        idx_expr, idx_type, _parent, _alt = self._code_ref(code_gen, "p![n]")
        self.assertEqual(idx_expr, "(*p)[n]")
        self.assertEqual(idx_type["fieldType"], "char")

    def test_cpp_explicit_deref_composes_with_field_access(self):
        src = """
struct Widget{
    me int: value
}
"""
        prog_spec = {}
        obj_names = []
        _tags, _build_specs, classes, _new_classes = codeDogParser.parseCodeDogString(
            src, prog_spec, obj_names, {}, "explicit deref test"
        )
        code_gen = self._cpp_generator(classes)
        code_gen.localVarsAllocated = [
            ["p", {"owner": "their", "fieldType": ["Widget"], "arraySpec": None, "paramList": None}],
        ]

        expr, t_spec, _parent, _alt = self._code_ref(code_gen, "p!.value")
        self.assertEqual(expr, "p->value")
        self.assertEqual(t_spec["owner"], "me")
        self.assertEqual(t_spec["fieldType"], "int")

    def test_explicit_deref_rejects_managed_my_owner(self):
        code_gen = self._cpp_generator()
        code_gen.localVarsAllocated = [
            ["owned", {"owner": "my", "fieldType": "string", "arraySpec": None, "paramList": None}],
            ["value", {"owner": "me", "fieldType": "string", "arraySpec": None, "paramList": None}],
        ]

        with self.assertRaises(SystemExit):
            self._code_ref(code_gen, "owned!")
        with self.assertRaises(SystemExit):
            self._code_ref(code_gen, "value!")

    def test_java_kotlin_reject_bare_explicit_deref_assignment(self):
        for xlator in (Xlator_Java(), Xlator_Kotlin()):
            with self.subTest(language=xlator.LanguageName):
                code_gen = self._generator(xlator)
                code_gen.localVarsAllocated = [
                    ["p", {"owner": "their", "fieldType": "int", "arraySpec": None, "paramList": None}],
                ]

                with self.assertRaises(SystemExit):
                    self._code_action(code_gen, "p! <- 1")

    def test_java_kotlin_explicit_deref_read_lowering(self):
        src = """
struct Widget{
    me int: value
}
"""
        prog_spec = {}
        obj_names = []
        _tags, _build_specs, classes, _new_classes = codeDogParser.parseCodeDogString(
            src, prog_spec, obj_names, {}, "explicit deref JVM read test"
        )

        cases = (
            (
                Xlator_Java(),
                {"p!": "p", "p!.value": "p.value", "p.value": "p.value", "s![n]": "s.charAt(n)"},
            ),
            (
                Xlator_Kotlin(),
                {"p!": "p!!", "p!.value": "p!!.value", "p.value": "p!!.value", "s![n]": "s!![n]"},
            ),
        )
        for xlator, expectations in cases:
            with self.subTest(language=xlator.LanguageName):
                code_gen = self._generator(xlator, classes)
                code_gen.localVarsAllocated = [
                    ["p", {"owner": "their", "fieldType": ["Widget"], "arraySpec": None, "paramList": None}],
                    ["s", {"owner": "their", "fieldType": "string", "arraySpec": None, "paramList": None}],
                    ["n", {"owner": "me", "fieldType": "int", "arraySpec": None, "paramList": None}],
                ]
                for src_ref, expected in expectations.items():
                    with self.subTest(ref=src_ref):
                        self.assertEqual(self._code_ref(code_gen, src_ref)[0], expected)

    def test_kotlin_explicit_deref_value_contexts(self):
        code_gen = self._generator(Xlator_Kotlin())
        code_gen.localVarsAllocated = [
            ["pi", {"owner": "their", "fieldType": "int", "arraySpec": None, "paramList": None}],
            ["mi", {"owner": "me", "fieldType": "int", "arraySpec": None, "paramList": None}],
            ["pb", {"owner": "their", "fieldType": "bool", "arraySpec": None, "paramList": None}],
        ]

        plus_expr = codeDogParser.expr.parse_string("pi! + 1", parse_all=True)[0]
        bool_expr = codeDogParser.expr.parse_string("pb! and true", parse_all=True)[0]

        self.assertEqual(code_gen.codeExpr(plus_expr, None, None, "RVAL", {})[0], "pi!! + 1")
        self.assertEqual(code_gen.codeExpr(bool_expr, None, None, "RVAL", {})[0], "pb!! && true")
        self.assertEqual(self._code_action(code_gen, "mi <- pi!").strip(), "mi = pi!!;")

    def test_java_kotlin_allow_explicit_deref_member_assignment(self):
        src = """
struct Widget{
    me int: value
}
"""
        prog_spec = {}
        obj_names = []
        _tags, _build_specs, classes, _new_classes = codeDogParser.parseCodeDogString(
            src, prog_spec, obj_names, {}, "explicit deref JVM assignment test"
        )

        cases = (
            (Xlator_Java(), "p.value = 1;"),
            (Xlator_Kotlin(), "p!!.value = 1;"),
        )
        for xlator, expected in cases:
            with self.subTest(language=xlator.LanguageName):
                code_gen = self._generator(xlator, classes)
                code_gen.localVarsAllocated = [
                    ["p", {"owner": "their", "fieldType": ["Widget"], "arraySpec": None, "paramList": None}],
                ]

                self.assertEqual(self._code_action(code_gen, "p!.value <- 1").strip(), expected)

    def test_warning_mode_allows_unambiguous_value_assignment(self):
        code_gen = self._generator(Xlator_Kotlin())
        self._enable_deref_warnings(code_gen)
        code_gen.localVarsAllocated = [
            ["pi", {"owner": "their", "fieldType": "int", "arraySpec": None, "paramList": None}],
            ["mi", {"owner": "me", "fieldType": "int", "arraySpec": None, "paramList": None}],
        ]

        implicit_expr = codeDogParser.expr.parse_string("pi + 1", parse_all=True)[0]
        explicit_expr = codeDogParser.expr.parse_string("pi! + 1", parse_all=True)[0]

        explicit_warnings = self._captured_stdout(lambda: code_gen.codeExpr(explicit_expr, None, None, "RVAL", {}))
        assign_warnings = self._captured_stdout(lambda: self._code_action(code_gen, "mi <- pi"))
        explicit_assign_warnings = self._captured_stdout(lambda: self._code_action(code_gen, "mi <- pi!"))

        with self.assertRaises(SystemExit):
            code_gen.codeExpr(implicit_expr, None, None, "RVAL", {})
        self.assertEqual(explicit_warnings, "")
        self.assertEqual(assign_warnings, "")
        self.assertEqual(explicit_assign_warnings, "")
        self.assertEqual(self._code_action(code_gen, "mi <- pi").strip(), "mi = (pi!!);")
        self.assertEqual(self._code_action(code_gen, "mi <- pi!").strip(), "mi = pi!!;")

    def test_cpp_auto_derefs_unambiguous_value_assignment(self):
        code_gen = self._cpp_generator()
        self._enable_deref_warnings(code_gen)
        code_gen.localVarsAllocated = [
            ["pi", {"owner": "their", "fieldType": "int", "arraySpec": None, "paramList": None}],
            ["mi", {"owner": "me", "fieldType": "int", "arraySpec": None, "paramList": None}],
        ]

        assign_warnings = self._captured_stdout(lambda: self._code_action(code_gen, "mi <- pi"))

        self.assertEqual(assign_warnings, "")
        self.assertEqual(self._code_action(code_gen, "mi <- pi").strip(), "mi = (*pi);")

    def test_strict_mode_rejects_ambiguous_implicit_derefs(self):
        src = """
struct Widget{
    me int: value
}
"""
        prog_spec = {}
        obj_names = []
        _tags, _build_specs, classes, _new_classes = codeDogParser.parseCodeDogString(
            src, prog_spec, obj_names, {}, "strict deref test"
        )
        code_gen = self._cpp_generator(classes)
        code_gen.tagStore = {"ExplicitDeref": "strict"}
        code_gen.buildTags = {}
        code_gen.localVarsAllocated = [
            ["p", {"owner": "their", "fieldType": ["Widget"], "arraySpec": None, "paramList": None}],
            ["pi", {"owner": "their", "fieldType": "int", "arraySpec": None, "paramList": None}],
            ["mi", {"owner": "me", "fieldType": "int", "arraySpec": None, "paramList": None}],
        ]

        self.assertEqual(self._code_action(code_gen, "mi <- pi").strip(), "mi = (*pi);")
        self.assertEqual(self._code_ref(code_gen, "p.value")[0], "p->value")
        with self.assertRaises(SystemExit):
            self._code_action(code_gen, "pi <- mi")

    def test_warning_mode_allows_member_access_and_rejects_index_access(self):
        src = """
struct Widget{
    me int: value
}
"""
        prog_spec = {}
        obj_names = []
        _tags, _build_specs, classes, _new_classes = codeDogParser.parseCodeDogString(
            src, prog_spec, obj_names, {}, "explicit deref warning member test"
        )
        code_gen = self._cpp_generator(classes)
        self._enable_deref_warnings(code_gen)
        code_gen.localVarsAllocated = [
            ["p", {"owner": "their", "fieldType": ["Widget"], "arraySpec": None, "paramList": None}],
            ["s", {"owner": "their", "fieldType": "string", "arraySpec": None, "paramList": None}],
            ["n", {"owner": "me", "fieldType": "int", "arraySpec": None, "paramList": None}],
        ]

        member_warnings = self._captured_stdout(lambda: self._code_ref(code_gen, "p.value"))
        explicit_member_warnings = self._captured_stdout(lambda: self._code_ref(code_gen, "p!.value"))
        explicit_index_warnings = self._captured_stdout(lambda: self._code_ref(code_gen, "s![n]"))

        self.assertEqual(self._code_ref(code_gen, "p.value")[0], "p->value")
        self.assertEqual(member_warnings, "")
        self.assertEqual(explicit_member_warnings, "")
        with self.assertRaises(SystemExit):
            self._code_ref(code_gen, "s[n]")
        self.assertEqual(explicit_index_warnings, "")

    def test_warning_mode_reports_deprecated_deep_assignment(self):
        code_gen = self._cpp_generator()
        self._enable_deref_warnings(code_gen)
        code_gen.localVarsAllocated = [
            ["A", {"owner": "their", "fieldType": "int", "arraySpec": None, "paramList": None}],
            ["B", {"owner": "their", "fieldType": "int", "arraySpec": None, "paramList": None}],
        ]

        warnings = self._captured_stdout(lambda: self._code_action(code_gen, "B <deep- A"))

        self.assertIn("deprecated '<deep-' assignment", warnings)
        self.assertIn("B! <- A!", warnings)

    def test_warning_mode_skips_code_converter_member_calls(self):
        src = """
struct Widget{
    me void: draw() <- <%!drawWidget(%0)%>
}
"""
        prog_spec = {}
        obj_names = []
        _tags, _build_specs, classes, _new_classes = codeDogParser.parseCodeDogString(
            src, prog_spec, obj_names, {}, "explicit deref warning converter test"
        )
        code_gen = self._cpp_generator(classes)
        self._enable_deref_warnings(code_gen)
        code_gen.localVarsAllocated = [
            ["p", {"owner": "their", "fieldType": ["Widget"], "arraySpec": None, "paramList": None}],
        ]

        warnings = self._captured_stdout(lambda: self._code_ref(code_gen, "p.draw()"))

        self.assertEqual(warnings, "")

    def test_cpp_explicit_deref_mode_field_uses_referent_flags(self):
        src = """
struct Widget{
    mode[owning, other]: owner
}
"""
        prog_spec = {}
        obj_names = []
        _tags, _build_specs, classes, _new_classes = codeDogParser.parseCodeDogString(
            src, prog_spec, obj_names, {}, "explicit deref mode field test"
        )
        code_gen = self._cpp_generator(classes)
        code_gen.localVarsAllocated = [
            ["p", {"owner": "our", "fieldType": ["Widget"], "arraySpec": None, "paramList": None}],
        ]

        expr, _t_spec, _parent, _alt = self._code_ref(code_gen, "p!.owner")

        self.assertIn("p->flags", expr)
        self.assertIn(", owner)", expr)
        self.assertNotIn("p->o.flags", expr)

    def test_warning_mode_keeps_null_handle_checks_quiet(self):
        code_gen = self._cpp_generator()
        self._enable_deref_warnings(code_gen)
        code_gen.localVarsAllocated = [
            ["p", {"owner": "their", "fieldType": "int", "arraySpec": None, "paramList": None}],
        ]

        null_check = codeDogParser.expr.parse_string("p != NULL", parse_all=True)[0]
        value_check = codeDogParser.expr.parse_string("p == 1", parse_all=True)[0]

        null_warnings = self._captured_stdout(lambda: code_gen.codeExpr(null_check, None, None, "RVAL", {}))

        self.assertEqual(null_warnings, "")
        with self.assertRaises(SystemExit):
            code_gen.codeExpr(value_check, None, None, "RVAL", {})

    def test_null_literal_detection_is_codedog_null_only(self):
        code_gen = self._cpp_generator()

        self.assertTrue(code_gen.isNullLiteralExpr("NULL", {"owner": "their", "fieldType": "int"}))
        self.assertTrue(code_gen.isNullLiteralExpr("nullptr", {"owner": "PTR"}))
        self.assertFalse(code_gen.isNullLiteralExpr("null", {"owner": "their", "fieldType": "int"}))
        self.assertFalse(code_gen.isNullLiteralExpr("nil", {"owner": "their", "fieldType": "int"}))

    def test_warning_mode_allows_pointer_bool_contexts(self):
        code_gen = self._cpp_generator()
        self._enable_deref_warnings(code_gen)
        code_gen.localVarsAllocated = [
            ["p", {"owner": "their", "fieldType": "bool", "arraySpec": None, "paramList": None}],
            ["q", {"owner": "their", "fieldType": "bool", "arraySpec": None, "paramList": None}],
        ]
        if_parsed = codeDogParser.conditionalAction.parse_string("if(p){}", parse_all=True)[0]
        if_action = codeDogParser.extractActItem("testFunc", if_parsed)
        while_parsed = codeDogParser.whileAction.parse_string("while(p){}", parse_all=True)[0]
        while_action = codeDogParser.extractActItem("testFunc", while_parsed)
        logical_expr = codeDogParser.expr.parse_string("p and q", parse_all=True)[0]
        not_expr = codeDogParser.expr.parse_string("!p", parse_all=True)[0]

        if_warnings = self._captured_stdout(lambda: code_gen.codeAction(if_action, "    ", None, {}))
        while_warnings = self._captured_stdout(lambda: code_gen.codeAction(while_action, "    ", None, {}))
        logical_warnings = self._captured_stdout(lambda: code_gen.codeExpr(logical_expr, None, None, "RVAL", {}))
        not_warnings = self._captured_stdout(lambda: code_gen.codeExpr(not_expr, None, None, "RVAL", {}))

        self.assertEqual(if_warnings, "")
        self.assertEqual(while_warnings, "")
        self.assertEqual(logical_warnings, "")
        self.assertEqual(not_warnings, "")
        self.assertEqual(code_gen.codeExpr(logical_expr, None, None, "RVAL", {})[0], "p && q")
        self.assertEqual(code_gen.codeExpr(not_expr, None, None, "RVAL", {})[0], "!p")

    def test_jvm_pointer_bool_contexts_use_null_checks(self):
        cases = (
            (Xlator_Java(), "p != null && q != null", "(p == null)"),
            (Xlator_Kotlin(), "(p != null) && (q != null)", "(p == null)"),
        )
        logical_expr = codeDogParser.expr.parse_string("p and q", parse_all=True)[0]
        not_expr = codeDogParser.expr.parse_string("!p", parse_all=True)[0]
        for xlator, expected_logical, expected_not in cases:
            with self.subTest(language=xlator.LanguageName):
                code_gen = self._generator(xlator)
                self._enable_deref_warnings(code_gen)
                code_gen.localVarsAllocated = [
                    ["p", {"owner": "their", "fieldType": "bool", "arraySpec": None, "paramList": None}],
                    ["q", {"owner": "their", "fieldType": "bool", "arraySpec": None, "paramList": None}],
                ]

                self.assertEqual(code_gen.codeExpr(logical_expr, None, None, "RVAL", {})[0], expected_logical)
                self.assertEqual(code_gen.codeExpr(not_expr, None, None, "RVAL", {})[0], expected_not)

    def test_warning_mode_can_be_enabled_by_environment(self):
        code_gen = self._cpp_generator()
        code_gen.localVarsAllocated = [
            ["p", {"owner": "their", "fieldType": "int", "arraySpec": None, "paramList": None}],
        ]
        expr = codeDogParser.expr.parse_string("p + 1", parse_all=True)[0]
        old_value = os.environ.get("CODEDOG_EXPLICIT_DEREF")
        os.environ["CODEDOG_EXPLICIT_DEREF"] = "warn"
        try:
            with self.assertRaises(SystemExit):
                code_gen.codeExpr(expr, None, None, "RVAL", {})
        finally:
            if old_value == None:
                del os.environ["CODEDOG_EXPLICIT_DEREF"]
            else:
                os.environ["CODEDOG_EXPLICIT_DEREF"] = old_value


if __name__ == "__main__":
    unittest.main()
