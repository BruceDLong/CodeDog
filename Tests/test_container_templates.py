import copy
import unittest

import codeDogParser
import progSpec
from codeGenerator import CodeGenerator
from xlator_CPP import Xlator_CPP


class TestContainerTemplateDetection(unittest.TestCase):
    def setUp(self):
        self._impl_options_backup = copy.deepcopy(progSpec.classImplementationOptions)
        self._templates_backup = copy.deepcopy(progSpec.templatesDefined)

    def tearDown(self):
        progSpec.classImplementationOptions.clear()
        progSpec.classImplementationOptions.update(self._impl_options_backup)
        progSpec.templatesDefined.clear()
        progSpec.templatesDefined.update(self._templates_backup)

    def _req_tags(self, *types):
        return [{'tArgOwner': 'me', 'tArgType': t} for t in types]

    def _make_tspec(self, field_type_kw, req_tags=None, **extras):
        t_spec = {
            'owner': 'me',
            'fieldType': [field_type_kw, req_tags] if req_tags else [field_type_kw],
            'arraySpec': None,
            'reqTagList': req_tags,
            'paramList': None,
        }
        t_spec.update(extras)
        return t_spec

    def test_non_container_generic_is_not_treated_as_container(self):
        req_tags = self._req_tags('int', 'string')
        t_spec = self._make_tspec('MapNode', req_tags)

        self.assertFalse(progSpec.isContainerTemplateTempFunc(t_spec))
        self.assertFalse(progSpec.isNewContainerTempFunc(t_spec))
        self.assertIsNone(progSpec.getNewContainerFirstElementTypeTempFunc(t_spec))

    def test_container_category_tag_marks_container_template(self):
        req_tags = self._req_tags('int')
        t_spec = self._make_tspec('CustomSeq', req_tags, containerCategory='List')

        self.assertTrue(progSpec.isContainerTemplateTempFunc(t_spec))
        self.assertTrue(progSpec.isNewContainerTempFunc(t_spec))
        self.assertEqual(progSpec.getNewContainerFirstElementTypeTempFunc(t_spec), 'int')
        self.assertEqual(progSpec.containerCategoryForTypeSpec(t_spec), 'List')

    def test_from_implemented_marks_container_template(self):
        req_tags = self._req_tags('string', 'int')
        t_spec = self._make_tspec('AnyImplMap', req_tags, fromImplemented='Map')

        self.assertTrue(progSpec.isContainerTemplateTempFunc(t_spec))
        self.assertEqual(progSpec.containerCategoryForTypeSpec(t_spec), 'Map')

    def test_container_info_for_map_exposes_key_and_value_specs(self):
        req_tags = self._req_tags('string', 'int')
        t_spec = self._make_tspec('AnyImplMap', req_tags, fromImplemented='Map')

        info = progSpec.getContainerInfo(None, t_spec)

        self.assertTrue(info['isContainer'])
        self.assertEqual(info['category'], 'Map')
        self.assertTrue(info['isAssociative'])
        self.assertEqual(info['entryShape'], 'entry')
        self.assertEqual(info['keyTypeSpec']['fieldType'], 'string')
        self.assertEqual(info['valueTypeSpec']['fieldType'], 'int')

    def test_container_info_for_list_exposes_value_spec(self):
        req_tags = self._req_tags('int')
        t_spec = self._make_tspec('CustomSeq', req_tags, containerCategory='List')

        info = progSpec.getContainerInfo(None, t_spec)

        self.assertTrue(info['isContainer'])
        self.assertEqual(info['category'], 'List')
        self.assertFalse(info['isAssociative'])
        self.assertEqual(info['entryShape'], 'value')
        self.assertEqual(info['valueTypeSpec']['fieldType'], 'int')

    def test_codegen_container_value_type_uses_value_spec(self):
        req_tags = self._req_tags('string', 'int')
        t_spec = self._make_tspec('AnyImplMap', req_tags, fromImplemented='Map')

        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.classStore = [{}, []]

        self.assertEqual(code_gen.getContainerValueOwnerAndType(t_spec), ['me', 'int'])

    def test_type_argument_requirement_tags_are_preserved(self):
        src = """
struct Holder{
    me Map<me int, me string: rangeIteration=logarithmic>: ranked
}
"""
        prog_spec = {}
        obj_names = []
        _tags, _build_specs, classes, _new_classes = codeDogParser.parseCodeDogString(
            src, prog_spec, obj_names, {}, "container req tag test"
        )

        type_spec = classes[0]["Holder"]["fields"][0]["typeSpec"]

        self.assertEqual(type_spec["reqTagList"][0]["tArgType"], "int")
        self.assertEqual(type_spec["reqTagList"][1]["tArgType"], "string")
        self.assertEqual(type_spec["reqTags"], {"rangeIteration": "logarithmic"})
        self.assertEqual(progSpec.getReqTags(type_spec), {"rangeIteration": "logarithmic"})

    def test_map_implementation_selection_can_request_range_iteration(self):
        req_tags = self._req_tags('int', 'string')
        class_store = (
            {
                'Kotlin_HashMap': {
                    'name': 'Kotlin_HashMap',
                    'stateType': 'struct',
                    'tags': {
                        'native': 'lang',
                        'specs': {
                            'insert': 'constant',
                            'find': 'constant',
                            'at': 'constant',
                            'rangeIteration': 'dontUse',
                        },
                    },
                    'fields': [],
                },
                'Kotlin_TreeMap': {
                    'name': 'Kotlin_TreeMap',
                    'stateType': 'struct',
                    'tags': {
                        'native': 'lang',
                        'specs': {
                            'insert': 'logarithmic',
                            'find': 'logarithmic',
                            'at': 'logarithmic',
                            'rangeIteration': 'logarithmic',
                        },
                    },
                    'fields': [],
                },
            },
            ['Kotlin_HashMap', 'Kotlin_TreeMap'],
        )
        progSpec.classImplementationOptions.clear()
        progSpec.classImplementationOptions.update({
            'Map': ['Kotlin_HashMap', 'Kotlin_TreeMap'],
        })
        progSpec.templatesDefined['Kotlin_HashMap'] = ['keyType', 'valueType']
        progSpec.templatesDefined['Kotlin_TreeMap'] = ['keyType', 'valueType']

        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.classStore = class_store

        plain_tspec = self._make_tspec('Map', req_tags)
        ranged_tspec = self._make_tspec(
            'Map',
            req_tags,
            reqTags={'rangeIteration': 'logarithmic'},
        )

        self.assertEqual(
            code_gen.chooseStructImplementationToUse(plain_tspec, 'Holder', 'plain')[0],
            'Kotlin_HashMap',
        )
        self.assertEqual(
            code_gen.chooseStructImplementationToUse(ranged_tspec, 'Holder', 'ranked')[0],
            'Kotlin_TreeMap',
        )

    def test_implementation_selection_skips_options_missing_requested_specs(self):
        req_tags = self._req_tags('int', 'string')
        class_store = (
            {
                'MinimalHashMap': {
                    'name': 'MinimalHashMap',
                    'stateType': 'struct',
                    'tags': {
                        'native': 'lang',
                        'specs': {
                            'insert': 'constant',
                            'find': 'constant',
                            'at': 'constant',
                        },
                    },
                    'fields': [],
                },
                'Kotlin_TreeMap': {
                    'name': 'Kotlin_TreeMap',
                    'stateType': 'struct',
                    'tags': {
                        'native': 'lang',
                        'specs': {
                            'insert': 'logarithmic',
                            'find': 'logarithmic',
                            'at': 'logarithmic',
                            'rangeIteration': 'logarithmic',
                        },
                    },
                    'fields': [],
                },
            },
            ['MinimalHashMap', 'Kotlin_TreeMap'],
        )
        progSpec.classImplementationOptions.clear()
        progSpec.classImplementationOptions.update({
            'Map': ['MinimalHashMap', 'Kotlin_TreeMap'],
        })
        progSpec.templatesDefined['MinimalHashMap'] = ['keyType', 'valueType']
        progSpec.templatesDefined['Kotlin_TreeMap'] = ['keyType', 'valueType']

        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.classStore = class_store
        ranged_tspec = self._make_tspec(
            'Map',
            req_tags,
            reqTags={'rangeIteration': 'logarithmic'},
        )

        self.assertEqual(
            code_gen.chooseStructImplementationToUse(ranged_tspec, 'Holder', 'ranked')[0],
            'Kotlin_TreeMap',
        )

    def test_container_capabilities_respect_unordered_implementation_specs(self):
        req_tags = self._req_tags('int', 'string')
        class_store = (
            {
                'Kotlin_HashMap': {
                    'name': 'Kotlin_HashMap',
                    'stateType': 'struct',
                    'tags': {
                        'implements': 'Map',
                        'native': 'lang',
                        'specs': {
                            'insert': 'constant',
                            'find': 'constant',
                            'at': 'constant',
                            'rangeIteration': 'dontUse',
                        },
                    },
                    'fields': [],
                },
            },
            ['Kotlin_HashMap'],
        )
        t_spec = self._make_tspec('Kotlin_HashMap', req_tags, fromImplemented='Map')

        caps = progSpec.getContainerCapabilities(class_store, t_spec)

        self.assertFalse(caps['isOrdered'])
        self.assertNotIn('ordered_keys', caps['tags'])

    def test_list_implementation_selection_can_request_constant_prepend(self):
        req_tags = self._req_tags('int')
        class_store = (
            {
                'Java_ArrayList': {
                    'name': 'Java_ArrayList',
                    'stateType': 'struct',
                    'tags': {
                        'native': 'lang',
                        'specs': {
                            'insert': 'linear',
                            'append': 'constant',
                            'prepend': 'linear',
                            'at': 'constant',
                            'rangeIteration': 'constant',
                        },
                    },
                    'fields': [],
                },
                'Kotlin_LinkedList': {
                    'name': 'Kotlin_LinkedList',
                    'stateType': 'struct',
                    'tags': {
                        'native': 'lang',
                        'specs': {
                            'insert': 'linear',
                            'append': 'constant',
                            'prepend': 'constant',
                            'at': 'linear',
                            'rangeIteration': 'constant',
                        },
                    },
                    'fields': [],
                },
            },
            ['Java_ArrayList', 'Kotlin_LinkedList'],
        )
        progSpec.classImplementationOptions.clear()
        progSpec.classImplementationOptions.update({
            'List': ['Java_ArrayList', 'Kotlin_LinkedList'],
        })
        progSpec.templatesDefined['Java_ArrayList'] = ['nodeType']
        progSpec.templatesDefined['Kotlin_LinkedList'] = ['nodeType']

        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.classStore = class_store

        plain_tspec = self._make_tspec('List', req_tags)
        prepend_tspec = self._make_tspec(
            'List',
            req_tags,
            reqTags={'prepend': 'constant'},
        )

        self.assertEqual(
            code_gen.chooseStructImplementationToUse(plain_tspec, 'Holder', 'plain')[0],
            'Java_ArrayList',
        )
        self.assertEqual(
            code_gen.chooseStructImplementationToUse(prepend_tspec, 'Holder', 'queue')[0],
            'Kotlin_LinkedList',
        )

    def test_registered_implementation_marks_container_template(self):
        progSpec.classImplementationOptions.clear()
        progSpec.classImplementationOptions.update({
            'List': ['UltraList'],
            'Map': [],
            'Multimap': [],
        })
        req_tags = self._req_tags('int')
        t_spec = self._make_tspec('UltraList', req_tags)

        self.assertTrue(progSpec.isContainerTemplateTempFunc(t_spec))
        self.assertTrue(progSpec.isNewContainerTempFunc(t_spec))
        self.assertEqual(progSpec.containerCategoryForTypeSpec(t_spec), 'List')

    def test_container_category_resolves_from_model_implements_tag(self):
        class_store = (
            {
                'List': {
                    'name': 'List',
                    'stateType': 'model',
                    'tags': {'implements': 'List'},
                    'fields': [],
                }
            },
            ['List'],
        )
        req_tags = self._req_tags('int')
        t_spec = self._make_tspec('List', req_tags)

        self.assertEqual(progSpec.getContaineCategory(class_store, t_spec), 'List')

    def test_wrapped_map_value_type_is_unwrapped_for_cpp(self):
        src = """
struct INK_Image: wraps = cairo_surface_t ownerMe = their{}
struct Holder{
    me Map<string, INK_Image>: inkImg
}
"""
        prog_spec = {}
        obj_names = []
        _tags, _build_specs, classes, _new_classes = codeDogParser.parseCodeDogString(
            src, prog_spec, obj_names, {}, "wrapped map type test"
        )

        field = classes[0]["Holder"]["fields"][0]

        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.classStore = classes
        code_gen.currentObjName = "Holder"
        code_gen.xlator = Xlator_CPP()
        code_gen.xlator.codeGen = code_gen

        cvrt_type = code_gen.convertType(field["typeSpec"], "var", {})
        self.assertIn("cairo_surface_t", cvrt_type)
        self.assertNotIn("INK_Image", cvrt_type)


if __name__ == '__main__':
    unittest.main()
