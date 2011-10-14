import unittest
import datetime
import functools

import configman.config_manager as config_manager
import configman.datetime_util as dtu


class TestCase(unittest.TestCase):

    def test_Namespace_basics(self):
        namespace = config_manager.Namespace('doc string')
        namespace.alpha = 1
        my_birthday = datetime.datetime(1960, 5, 4, 15, 10)
        namespace.beta = my_birthday
        self.assertEqual(namespace.alpha.name, 'alpha')
        self.assertEqual(namespace.alpha.doc, None)
        self.assertEqual(namespace.alpha.default, 1)
        self.assertEqual(namespace.alpha.from_string_converter, int)
        self.assertEqual(namespace.alpha.value, 1)
        self.assertEqual(namespace.beta.name, 'beta')
        self.assertEqual(namespace.beta.doc, None)
        self.assertEqual(namespace.beta.default, my_birthday)
        self.assertEqual(namespace.beta.from_string_converter,
                         dtu.datetime_from_ISO_string)
        self.assertEqual(namespace.beta.value, my_birthday)

    def test_configuration_with_namespace(self):
        namespace = config_manager.Namespace()
        namespace.add_option('a')
        namespace.a.default = 1
        namespace.a.doc = 'the a'
        namespace.b = 17
        config = config_manager.ConfigurationManager(
          [namespace],
          use_config_files=False,
          argv_source=[]
        )
        self.assertEqual(config.option_definitions.a, namespace.a)
        self.assertTrue(isinstance(config.option_definitions.b,
                                   config_manager.Option))
        self.assertEqual(config.option_definitions.b.value, 17)
        self.assertEqual(config.option_definitions.b.default, 17)
        self.assertEqual(config.option_definitions.b.name, 'b')

    def test_namespace_constructor_3(self):
        """test json definition"""

        j = '{ "a": {"name": "a", "default": 1, "doc": "the a"}, "b": 17}'
        config = config_manager.ConfigurationManager(
          [j],
          use_config_files=False,
          argv_source=[]
        )
        self.assertTrue(isinstance(config.option_definitions.a,
                                   config_manager.Option))
        self.assertEqual(config.option_definitions.a.value, 1)
        self.assertEqual(config.option_definitions.a.default, 1)
        self.assertEqual(config.option_definitions.a.name, 'a')
        self.assertTrue(isinstance(config.option_definitions.b,
                                   config_manager.Option))
        self.assertEqual(config.option_definitions.b.value, 17)
        self.assertEqual(config.option_definitions.b.default, 17)
        self.assertEqual(config.option_definitions.b.name, 'b')

    def test_walk_expanding_class_options(self):
        class A(config_manager.RequiredConfig):
            required_config = {
              'a': config_manager.Option('a', 1, 'the a'),
              'b': 17,
            }
        n = config_manager.Namespace()
        n.source = config_manager.Namespace()
        n.source.add_option('c', A, 'the A class')
        assert n.source.c.doc == 'the A class'

        n.dest = config_manager.Namespace()
        n.dest.add_option('c', A, doc='the A class')
        assert n.dest.c.doc == 'the A class'
        c = config_manager.ConfigurationManager([n],
                                    manager_controls=False,
                                    use_config_files=False,
                                    auto_help=False,
                                    argv_source=[])
        e = config_manager.Namespace()
        e.s = config_manager.Namespace()
        e.s.add_option('c', A, doc='the A class')
        e.s.add_option('a', 1, 'the a')
        e.s.add_option('b', default=17)
        e.d = config_manager.Namespace()
        e.d.add_option('c', A, doc='the A class')
        e.d.add_option('a', 1, 'the a')
        e.d.add_option('b', default=17)

        def namespace_test(val):
            self.assertEqual(type(val), config_manager.Namespace)

        def option_test(val, expected=None):
            self.assertEqual(val.name, expected.name)
            self.assertEqual(val.default, expected.default)
            self.assertEqual(val.doc, expected.doc)

        e = [
          ('dest', 'dest', namespace_test),
          ('dest.a', 'a', functools.partial(option_test, expected=e.d.a)),
          ('dest.b', 'b', functools.partial(option_test, expected=e.d.b)),
          ('dest.c', 'c', functools.partial(option_test, expected=e.d.c)),
          ('source', 'source', namespace_test),
          ('source.a', 'a', functools.partial(option_test, expected=e.s.a)),
          ('source.b', 'b', functools.partial(option_test, expected=e.s.b)),
          ('source.c', 'c', functools.partial(option_test, expected=e.s.c)),
        ]

        c_contents = [(qkey, key, val) for qkey, key, val in c.walk_config()]
        c_contents.sort()
        e.sort()
        for c_tuple, e_tuple in zip(c_contents, e):
            qkey, key, val = c_tuple
            e_qkey, e_key, e_fn = e_tuple
            self.assertEqual(qkey, e_qkey)
            self.assertEqual(key, e_key)
            e_fn(val)

    def test_setting_nested_namespaces(self):
        n = config_manager.Namespace()
        n.namespace('sub')
        sub_n = n.sub
        sub_n.add_option('name')
        self.assertTrue(n.sub)
        self.assertTrue(isinstance(n.sub.name, config_manager.Option))

    def test_editing_values_on_namespace(self):
        n = config_manager.Namespace()
        self.assertRaises(KeyError, n.set_value, 'name', 'Peter')
        n.add_option('name', 'Lars')
        n.set_value('name', 'Peter')
        self.assertTrue(n.name)
        self.assertEqual(n.name.value, 'Peter')
        n.namespace('user')
        n.user.add_option('age', 100)
        n.set_value('user.age', 200)
        self.assertTrue(n.user.age)
        self.assertEqual(n.user.age.value, 200)

        # let's not be strict once
        n.set_value('user.gender', u'male', strict=False)
        self.assertEqual(n.user.gender.value, u'male')

    def test_comparing_namespace_instances(self):
        n = config_manager.Namespace()
        n2 = config_manager.Namespace()
        self.assertEqual(n, n2)

        n3 = config_manager.Namespace()
        n3.add_option('name', 'Peter')
        self.assertNotEqual(n, n3)

        n2.add_option('name', 'Peter', 'Name of a person')
        self.assertNotEqual(n, n2)
        self.assertNotEqual(n2, n3)

        n4 = config_manager.Namespace()
        n4.add_option('name', 'Peter')
        self.assertEqual(n4, n3)
