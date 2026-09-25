import copy
import unittest

import codeDogParser
import progSpec
from codeGenerator import CodeGenerator
from xlator_CPP import Xlator_CPP


class TestImplementationVisibility(unittest.TestCase):
    def _function_field(self, class_name, field_name, lib_level, lib_name="Impl.Lib.dog", value=None, param_types=None):
        if value is None:
            value = [[], ""]
        if param_types is None:
            param_types = []
        param_list = [
            {
                "fieldName": "arg{}".format(idx),
                "typeSpec": {
                    "owner": "me",
                    "fieldType": param_type,
                    "arraySpec": None,
                    "reqTagList": None,
                    "paramList": None,
                },
                "value": None,
            }
            for idx, param_type in enumerate(param_types)
        ]
        field_id = "{}::{}".format(class_name, field_name)
        if param_types:
            field_id += "({})".format(",".join(param_types))
        return {
            "fieldName": field_name,
            "fieldID": field_id,
            "typeSpec": {
                "owner": "me",
                "fieldType": "void",
                "arraySpec": None,
                "reqTagList": None,
                "paramList": param_list,
            },
            "value": value,
            "isAllocated": False,
            "libLevel": lib_level,
            "libName": lib_name,
        }

    def _class_def(self, class_name, lib_level, fields=None, tags=None, state_type="struct"):
        return {
            "name": class_name,
            "attrList": [],
            "attr": {},
            "fields": fields or [],
            "vFields": None,
            "stateType": state_type,
            "configType": "SEQ",
            "tags": tags or {},
            "libLevel": lib_level,
            "libName": "{}.Lib.dog".format(class_name),
        }

    def _code_gen(self, class_store):
        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.classStore = class_store
        code_gen.xlator = Xlator_CPP()
        code_gen.xlator.codeGen = code_gen
        code_gen.currentDefinitionLibLevel = 1
        return code_gen

    def test_parser_marks_child_library_fields_as_implementation_level(self):
        old_lib_levels = copy.copy(progSpec.libLevels)
        try:
            progSpec.setLibLevels(["Impl.Lib.dog"])
            prog_spec = {}
            obj_names = []

            codeDogParser.parseCodeDogString(
                "struct Api{ void: declared() }",
                prog_spec,
                obj_names,
                {},
                "Api.Lib.dog",
            )
            codeDogParser.parseCodeDogString(
                "struct Api{ void: declared() <- {} void: hidden() <- {} }",
                prog_spec,
                obj_names,
                {},
                "Impl.Lib.dog",
            )

            levels = {
                field["fieldID"]: field["libLevel"]
                for field in prog_spec["Api"]["fields"]
            }
            self.assertEqual(levels["Api::declared"], 2)
            self.assertEqual(levels["Api::hidden"], 2)
        finally:
            progSpec.setLibLevels(old_lib_levels)

    def test_late_top_level_declaration_is_kept_after_implementation_body(self):
        old_lib_levels = copy.copy(progSpec.libLevels)
        try:
            progSpec.setLibLevels(["Impl.Lib.dog"])
            prog_spec = {}
            obj_names = []

            codeDogParser.parseCodeDogString(
                "struct Api{}",
                prog_spec,
                obj_names,
                {},
                "Api.Lib.dog",
            )
            codeDogParser.parseCodeDogString(
                "struct Api{ void: late() <- {} }",
                prog_spec,
                obj_names,
                {},
                "Impl.Lib.dog",
            )
            codeDogParser.parseCodeDogString(
                "struct Api{ void: late() }",
                prog_spec,
                obj_names,
                {},
                "Api.Lib.dog",
            )

            matching_levels = [
                field["libLevel"]
                for field in prog_spec["Api"]["fields"]
                if field["fieldID"] == "Api::late"
            ]
            self.assertEqual(matching_levels, [2, 1])

            callable_fields = []
            progSpec.populateCallableStructFields(callable_fields, (prog_spec, obj_names), "Api")
            callable_late = [
                field["libLevel"]
                for field in callable_fields
                if field["fieldID"] == "Api::late"
            ]
            self.assertEqual(callable_late, [2])
        finally:
            progSpec.setLibLevels(old_lib_levels)

    def test_top_level_constant_declaration_is_filled_by_implementation_value(self):
        old_lib_levels = copy.copy(progSpec.libLevels)
        try:
            progSpec.setLibLevels(["Impl.Lib.dog"])
            prog_spec = {}
            obj_names = []

            codeDogParser.parseCodeDogString(
                "struct GLOBAL{ const int: EVENT_CODE }",
                prog_spec,
                obj_names,
                {},
                "Api.Lib.dog",
            )
            codeDogParser.parseCodeDogString(
                "struct GLOBAL{ const int: EVENT_CODE <- 12 }",
                prog_spec,
                obj_names,
                {},
                "Impl.Lib.dog",
            )

            callable_fields = []
            progSpec.populateCallableStructFields(callable_fields, (prog_spec, obj_names), "GLOBAL")
            event_fields = [
                field
                for field in callable_fields
                if field["fieldID"] == "GLOBAL::EVENT_CODE"
            ]
            self.assertEqual(len(event_fields), 1)
            self.assertEqual(event_fields[0]["libLevel"], 2)
            self.assertIsNotNone(event_fields[0].get("value"))
        finally:
            progSpec.setLibLevels(old_lib_levels)

    def test_explicit_implementation_only_type_is_rejected(self):
        class_store = (
            {
                "ImplOnly": self._class_def("ImplOnly", 2),
            },
            ["ImplOnly"],
        )
        code_gen = self._code_gen(class_store)
        t_spec = {
            "owner": "me",
            "fieldType": "ImplOnly",
            "arraySpec": None,
            "reqTagList": None,
            "paramList": None,
        }

        with self.assertRaises(SystemExit):
            code_gen.convertType(t_spec, "var", {})

    def test_generated_provider_type_is_allowed_when_marked_from_implemented(self):
        class_store = (
            {
                "ImplOnly": self._class_def("ImplOnly", 2),
            },
            ["ImplOnly"],
        )
        code_gen = self._code_gen(class_store)
        t_spec = {
            "owner": "me",
            "fieldType": "ImplOnly",
            "arraySpec": None,
            "reqTagList": None,
            "paramList": None,
            "fromImplemented": "PublicApi",
        }

        self.assertEqual(code_gen.convertType(t_spec, "var", {}), "ImplOnly")

    def test_explicit_implementation_only_member_is_rejected(self):
        impl_field = self._function_field("ImplOnly", "hidden", 2)
        class_store = (
            {
                "ImplOnly": self._class_def("ImplOnly", 2, [impl_field]),
            },
            ["ImplOnly"],
        )
        code_gen = self._code_gen(class_store)

        with self.assertRaises(SystemExit):
            code_gen.CheckObjectVars("ImplOnly", "hidden", "")

    def test_provider_member_declared_on_top_level_surface_is_allowed(self):
        public_field = self._function_field("PublicApi", "declared", 1, "PublicApi.Lib.dog", value=None)
        impl_field = self._function_field("ImplOnly", "declared", 2)
        class_store = (
            {
                "%PublicApi": self._class_def("PublicApi", 1, [public_field], state_type="model"),
                "ImplOnly": self._class_def("ImplOnly", 2, [impl_field], tags={"implements": "PublicApi"}),
            },
            ["%PublicApi", "ImplOnly"],
        )
        code_gen = self._code_gen(class_store)
        receiver_tspec = {
            "owner": "me",
            "fieldType": ["ImplOnly"],
            "fromImplemented": "PublicApi",
        }

        self.assertIs(
            code_gen.CheckObjectVars("ImplOnly", "declared", "", receiver_tspec),
            impl_field,
        )

    def test_top_level_name_without_matching_signature_does_not_expose_impl_overload(self):
        public_field = self._function_field("PublicApi", "declared", 1, "PublicApi.Lib.dog", value=None)
        impl_field = self._function_field("ImplOnly", "declared", 2, param_types=["int"])
        class_store = (
            {
                "%PublicApi": self._class_def("PublicApi", 1, [public_field], state_type="model"),
                "ImplOnly": self._class_def("ImplOnly", 2, [impl_field], tags={"implements": "PublicApi"}),
            },
            ["%PublicApi", "ImplOnly"],
        )
        code_gen = self._code_gen(class_store)

        self.assertFalse(code_gen.fieldVisibleFromCurrentContext("ImplOnly", impl_field))

    def test_member_declared_on_implemented_surface_is_allowed(self):
        public_field = self._function_field("PublicApi.PublicItr", "val", 1, "PublicApi.Lib.dog", value=None)
        impl_field = self._function_field("ImplItr", "val", 2)
        class_store = (
            {
                "%PublicApi.PublicItr": self._class_def("PublicApi.PublicItr", 1, [public_field], state_type="model"),
                "ImplItr": self._class_def("ImplItr", 2, [impl_field], tags={"implements": "PublicItr"}),
            },
            ["%PublicApi.PublicItr", "ImplItr"],
        )
        code_gen = self._code_gen(class_store)

        self.assertIs(code_gen.CheckObjectVars("ImplItr", "val", ""), impl_field)

    def test_member_declared_on_inherited_top_level_surface_is_allowed(self):
        public_field = self._function_field("BaseApi", "declared", 1, "BaseApi.Lib.dog", value=None)
        impl_field = self._function_field("BaseApi", "declared", 2)
        class_store = (
            {
                "BaseApi": self._class_def("BaseApi", 2, [impl_field, public_field]),
                "ChildApi": self._class_def("ChildApi", 1, tags={"inherits": "BaseApi"}),
            },
            ["BaseApi", "ChildApi"],
        )
        code_gen = self._code_gen(class_store)

        self.assertTrue(code_gen.fieldVisibleFromCurrentContext("ChildApi", impl_field))

    def test_implementation_code_can_use_implementation_helpers(self):
        impl_field = self._function_field("ImplOnly", "hidden", 2)
        class_store = (
            {
                "ImplOnly": self._class_def("ImplOnly", 2, [impl_field]),
            },
            ["ImplOnly"],
        )
        code_gen = self._code_gen(class_store)
        code_gen.currentDefinitionLibLevel = 2

        self.assertIs(code_gen.CheckObjectVars("ImplOnly", "hidden", ""), impl_field)


if __name__ == "__main__":
    unittest.main()
