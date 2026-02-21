import unittest

import codeDogParser
import progSpec
from codeGenerator import CodeGenerator
from pyparsing import ParseResults


class TestNestedClassExtraction(unittest.TestCase):
    def _parse_classes(self, src):
        prog_spec = {}
        obj_names = []
        _tags, _build_specs, classes, new_classes = codeDogParser.parseCodeDogString(
            src, prog_spec, obj_names, {}, "nested class extraction test"
        )
        return classes, new_classes

    def test_recursive_nested_extraction_tracks_full_path(self):
        src = """
struct Outer{
    const struct: Inner() <- {
        me int: marker
        const struct: Leaf() <- {
            me int: value
        }
    }
}
"""
        classes, new_classes = self._parse_classes(src)

        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.extractNestedClasses(classes, new_classes)

        self.assertIn("Inner", classes[0])
        self.assertIn("Leaf", classes[0])

        self.assertEqual(classes[0]["Inner"]["fromNested"], "Outer")
        self.assertEqual(classes[0]["Leaf"]["fromNested"], "Inner")

        self.assertEqual(classes[0]["Inner"]["nestedPath"], "Outer::Inner")
        self.assertEqual(classes[0]["Leaf"]["nestedPath"], "Outer::Inner::Leaf")

        self.assertEqual(code_gen.nestedClasses["Inner"], "Outer")
        self.assertEqual(code_gen.nestedClasses["Leaf"], "Inner")

        self.assertEqual(code_gen.nestedClassQualifiedNames["Inner"], "Outer::Inner")
        self.assertEqual(code_gen.nestedClassQualifiedNames["Leaf"], "Outer::Inner::Leaf")

    def test_parser_accepts_dotted_type_reference(self):
        parsed = codeDogParser.fieldDef.parse_string("me Outer.Inner: item", parse_all=True)
        self.assertTrue(bool(parsed))

    def test_nested_class_angle_bracket_type_args(self):
        src = """
struct OuterAngle{
    const struct: InnerAngle<T> <- {
        me T: value
    }
}
"""
        classes, new_classes = self._parse_classes(src)

        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.extractNestedClasses(classes, new_classes)

        self.assertIn("InnerAngle", classes[0])
        self.assertEqual(progSpec.getTypeArgList("InnerAngle"), ["T"])

    def test_nested_class_legacy_paren_type_args_still_supported(self):
        src = """
struct OuterLegacy{
    const struct: InnerLegacy(typeArg: argName) <- {
        me int: value
    }
}
"""
        classes, new_classes = self._parse_classes(src)

        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.extractNestedClasses(classes, new_classes)

        self.assertIn("InnerLegacy", classes[0])
        self.assertEqual(progSpec.getTypeArgList("InnerLegacy"), ["typeArg"])

    def test_resolve_dotted_type_from_class_and_var(self):
        src = """
struct Outer{
    const struct: Inner() <- {
        const struct: Leaf() <- {
            me int: value
        }
    }
}
struct GLOBAL{
    void: run() <- {
        me Outer: out
    }
}
"""
        classes, new_classes = self._parse_classes(src)

        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.classStore = classes
        code_gen.extractNestedClasses(classes, new_classes)
        code_gen.currentObjName = "GLOBAL"
        code_gen.localVarsAllocated.append(["out", {"owner": "me", "fieldType": ["Outer"]}])

        self.assertEqual(code_gen.resolveDottedTypeKW("Outer.Inner", None), "Inner")
        self.assertEqual(code_gen.resolveDottedTypeKW("Outer.Inner.Leaf", None), "Leaf")
        self.assertEqual(code_gen.resolveDottedTypeKW("out.Inner", None), "Inner")
        self.assertEqual(code_gen.resolveDottedTypeKW("out.Inner.Leaf", None), "Leaf")

    def test_resolve_dotted_iterator_shorthand(self):
        src = """
struct Bag{
    const struct: iterator_Bag() <- {
        me int: value
    }
}
struct GLOBAL{
    void: run() <- {
        me Bag: bag
    }
}
"""
        classes, new_classes = self._parse_classes(src)

        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.classStore = classes
        code_gen.extractNestedClasses(classes, new_classes)
        code_gen.currentObjName = "GLOBAL"
        code_gen.localVarsAllocated.append(["bag", {"owner": "me", "fieldType": ["Bag"]}])

        self.assertEqual(code_gen.resolveDottedTypeKW("Bag.iterator", None), "iterator_Bag")
        self.assertEqual(code_gen.resolveDottedTypeKW("bag.iterator", None), "iterator_Bag")

    def test_rewrite_dotted_iterator_to_itr_owner(self):
        src = """
struct Bag{
    const struct: iterator_Bag() <- {
        me int: value
    }
}
struct GLOBAL{
    void: run() <- {
        me Bag: bag
    }
}
"""
        classes, new_classes = self._parse_classes(src)

        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.classStore = classes
        code_gen.extractNestedClasses(classes, new_classes)
        code_gen.currentObjName = "GLOBAL"
        code_gen.localVarsAllocated.append(["bag", {"owner": "me", "fieldType": ["Bag"]}])

        t_spec = {"owner": "me", "fieldType": ["bag.iterator"]}
        rewritten = code_gen.rewriteDottedIteratorTypeSpec(t_spec, None)
        self.assertEqual(rewritten, "Bag")
        self.assertEqual(t_spec["owner"], "itr")
        self.assertEqual(t_spec["fieldType"][0], "Bag")

    def test_rewrite_dotted_iterator_copies_container_req_tags(self):
        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.classStore = [{}, []]
        code_gen.currentObjName = "GLOBAL"

        req_tags = [{"tArgOwner": "me", "tArgType": "int"}]
        code_gen.localVarsAllocated.append(
            [
                "data",
                {
                    "owner": "me",
                    "fieldType": ["CPP_Deque", req_tags],
                    "arraySpec": None,
                    "reqTagList": req_tags,
                    "paramList": None,
                    "fromImplemented": "List",
                    "containerCategory": "List",
                    "implTypeArgs": ["nodeType"],
                },
            ]
        )

        t_spec = {"owner": "me", "fieldType": ["data.iterator"], "paramList": None}
        rewritten = code_gen.rewriteDottedIteratorTypeSpec(t_spec, None)

        self.assertEqual(rewritten, "CPP_Deque")
        self.assertEqual(t_spec["owner"], "itr")
        self.assertEqual(t_spec["fieldType"][0], "CPP_Deque")
        self.assertEqual(t_spec["reqTagList"][0]["tArgType"], "int")
        self.assertEqual(t_spec["fieldType"][1][0]["tArgType"], "int")
        self.assertEqual(t_spec["fromImplemented"], "List")
        self.assertEqual(t_spec["containerCategory"], "List")

    def test_find_spec_accepts_wrapped_class_name_key(self):
        obj_map = {"Outer": {"name": "Outer"}}
        self.assertIsNotNone(progSpec.findSpecOf(obj_map, ParseResults(["Outer"]), "struct"))


if __name__ == "__main__":
    unittest.main()
