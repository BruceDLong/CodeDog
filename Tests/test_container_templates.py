import copy
import unittest

import progSpec


class TestContainerTemplateDetection(unittest.TestCase):
    def setUp(self):
        self._impl_options_backup = copy.deepcopy(progSpec.classImplementationOptions)

    def tearDown(self):
        progSpec.classImplementationOptions.clear()
        progSpec.classImplementationOptions.update(self._impl_options_backup)

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


if __name__ == '__main__':
    unittest.main()
