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

    def test_container_info_for_set_exposes_value_spec(self):
        req_tags = self._req_tags('string')
        t_spec = self._make_tspec('AnySet', req_tags, fromImplemented='Set')

        info = progSpec.getContainerInfo(None, t_spec)

        self.assertTrue(info['isContainer'])
        self.assertEqual(info['category'], 'Set')
        self.assertFalse(info['isAssociative'])
        self.assertFalse(info['isOrdered'])
        self.assertEqual(info['entryShape'], 'value')
        self.assertEqual(info['valueTypeSpec']['fieldType'], 'string')
        self.assertIsNone(info['indexTypeSpec'])

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

    def test_cpp_map_selection_can_request_hash_or_tree(self):
        req_tags = self._req_tags('string', 'int')
        class_store = (
            {
                'CPP_HashMap': {
                    'name': 'CPP_HashMap',
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
                'CPP_Map': {
                    'name': 'CPP_Map',
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
            ['CPP_HashMap', 'CPP_Map'],
        )
        progSpec.classImplementationOptions.clear()
        progSpec.classImplementationOptions.update({
            'Map': ['CPP_HashMap', 'CPP_Map'],
        })
        progSpec.templatesDefined['CPP_HashMap'] = ['keyType', 'valueType']
        progSpec.templatesDefined['CPP_Map'] = ['keyType', 'valueType']

        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.classStore = class_store

        plain_tspec = self._make_tspec('Map', req_tags)
        hash_tspec = self._make_tspec(
            'Map',
            req_tags,
            reqTags={'insert': 'constant', 'find': 'constant', 'at': 'constant', 'rangeIteration': 'dontUse'},
        )
        ranged_tspec = self._make_tspec(
            'Map',
            req_tags,
            reqTags={'rangeIteration': 'logarithmic'},
        )

        self.assertEqual(
            code_gen.chooseStructImplementationToUse(plain_tspec, 'Holder', 'plain')[0],
            'CPP_HashMap',
        )
        self.assertEqual(
            code_gen.chooseStructImplementationToUse(hash_tspec, 'Holder', 'lookup')[0],
            'CPP_HashMap',
        )
        self.assertEqual(
            code_gen.chooseStructImplementationToUse(ranged_tspec, 'Holder', 'ranked')[0],
            'CPP_Map',
        )

    def test_set_implementation_selection_uses_hash_provider(self):
        req_tags = self._req_tags('string')
        class_store = (
            {
                'CPP_HashSet': {
                    'name': 'CPP_HashSet',
                    'stateType': 'struct',
                    'tags': {
                        'native': 'lang',
                        'specs': {
                            'insert': 'constant',
                            'find': 'constant',
                            'contains': 'constant',
                            'rangeIteration': 'dontUse',
                        },
                    },
                    'fields': [],
                },
            },
            ['CPP_HashSet'],
        )
        progSpec.classImplementationOptions.clear()
        progSpec.classImplementationOptions.update({
            'Set': ['CPP_HashSet'],
        })
        progSpec.templatesDefined['CPP_HashSet'] = ['nodeType']

        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.classStore = class_store

        plain_tspec = self._make_tspec('Set', req_tags)
        hash_tspec = self._make_tspec(
            'Set',
            req_tags,
            reqTags={'insert': 'constant', 'find': 'constant', 'contains': 'constant', 'rangeIteration': 'dontUse'},
        )

        self.assertEqual(
            code_gen.chooseStructImplementationToUse(plain_tspec, 'Holder', 'plain')[0],
            'CPP_HashSet',
        )
        self.assertEqual(
            code_gen.chooseStructImplementationToUse(hash_tspec, 'Holder', 'lookup')[0],
            'CPP_HashSet',
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
                'Kotlin_ArrayList': {
                    'name': 'Kotlin_ArrayList',
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
            ['Kotlin_ArrayList', 'Kotlin_LinkedList'],
        )
        progSpec.classImplementationOptions.clear()
        progSpec.classImplementationOptions.update({
            'List': ['Kotlin_ArrayList', 'Kotlin_LinkedList'],
        })
        progSpec.templatesDefined['Kotlin_ArrayList'] = ['nodeType']
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
            'Kotlin_ArrayList',
        )
        self.assertEqual(
            code_gen.chooseStructImplementationToUse(prepend_tspec, 'Holder', 'queue')[0],
            'Kotlin_LinkedList',
        )

    def test_cpp_list_selection_can_request_vector_or_deque(self):
        req_tags = self._req_tags('int')
        class_store = (
            {
                'CPP_ArrayList': {
                    'name': 'CPP_ArrayList',
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
                'CPP_Deque': {
                    'name': 'CPP_Deque',
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
            ['CPP_ArrayList', 'CPP_Deque'],
        )
        progSpec.classImplementationOptions.clear()
        progSpec.classImplementationOptions.update({
            'List': ['CPP_ArrayList', 'CPP_Deque'],
        })
        progSpec.templatesDefined['CPP_ArrayList'] = ['nodeType']
        progSpec.templatesDefined['CPP_Deque'] = ['nodeType']

        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.classStore = class_store

        plain_tspec = self._make_tspec('List', req_tags)
        at_tspec = self._make_tspec(
            'List',
            req_tags,
            reqTags={'at': 'constant'},
        )
        prepend_tspec = self._make_tspec(
            'List',
            req_tags,
            reqTags={'prepend': 'constant'},
        )

        self.assertEqual(
            code_gen.chooseStructImplementationToUse(plain_tspec, 'Holder', 'plain')[0],
            'CPP_ArrayList',
        )
        self.assertEqual(
            code_gen.chooseStructImplementationToUse(at_tspec, 'Holder', 'indexed')[0],
            'CPP_ArrayList',
        )
        self.assertEqual(
            code_gen.chooseStructImplementationToUse(prepend_tspec, 'Holder', 'queue')[0],
            'CPP_Deque',
        )

    def test_swift_list_selection_can_request_constant_prepend(self):
        req_tags = self._req_tags('int')
        class_store = (
            {
                'Swift_ArrayList': {
                    'name': 'Swift_ArrayList',
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
                'Swift_Deque': {
                    'name': 'Swift_Deque',
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
            ['Swift_ArrayList', 'Swift_Deque'],
        )
        progSpec.classImplementationOptions.clear()
        progSpec.classImplementationOptions.update({
            'List': ['Swift_ArrayList', 'Swift_Deque'],
        })
        progSpec.templatesDefined['Swift_ArrayList'] = ['nodeType']
        progSpec.templatesDefined['Swift_Deque'] = ['nodeType']

        code_gen = CodeGenerator()
        code_gen.clearBuild()
        code_gen.classStore = class_store

        plain_tspec = self._make_tspec('List', req_tags)
        at_tspec = self._make_tspec(
            'List',
            req_tags,
            reqTags={'at': 'constant'},
        )
        prepend_tspec = self._make_tspec(
            'List',
            req_tags,
            reqTags={'prepend': 'constant'},
        )

        self.assertEqual(
            code_gen.chooseStructImplementationToUse(plain_tspec, 'Holder', 'plain')[0],
            'Swift_ArrayList',
        )
        self.assertEqual(
            code_gen.chooseStructImplementationToUse(at_tspec, 'Holder', 'indexed')[0],
            'Swift_ArrayList',
        )
        self.assertEqual(
            code_gen.chooseStructImplementationToUse(prepend_tspec, 'Holder', 'queue')[0],
            'Swift_Deque',
        )

    def test_swift_map_selection_honors_range_iteration_requirement(self):
        req_tags = self._req_tags('string', 'int')
        class_store = (
            {
                'Swift_HashMap': {
                    'name': 'Swift_HashMap',
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
                'Swift_TreeMap': {
                    'name': 'Swift_TreeMap',
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
            ['Swift_HashMap', 'Swift_TreeMap'],
        )
        progSpec.classImplementationOptions.clear()
        progSpec.classImplementationOptions.update({
            'Map': ['Swift_HashMap', 'Swift_TreeMap'],
        })
        progSpec.templatesDefined['Swift_HashMap'] = ['keyType', 'valueType']
        progSpec.templatesDefined['Swift_TreeMap'] = ['keyType', 'valueType']

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
            'Swift_HashMap',
        )
        self.assertEqual(
            code_gen.chooseStructImplementationToUse(ranged_tspec, 'Holder', 'ranked')[0],
            'Swift_TreeMap',
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
