import unittest
import os
import tempfile
from contextlib import contextmanager
import ConfigParser
import io
from cStringIO import StringIO
import json
import getopt

import configman.config_manager as config_manager
from configman.dotdict import DotDict
import configman.datetime_util as dtu
from configman.config_exceptions import NotAnOptionError


class TestCase(unittest.TestCase):

    def test_empty_ConfigurationManager_constructor(self):
        # because the default option argument defaults to using sys.argv we
        # have to mock that
        c = config_manager.ConfigurationManager(
          manager_controls=False,
          #use_config_files=False,
          use_auto_help=False,
          argv_source=[]
        )
        self.assertEqual(c.option_definitions, config_manager.Namespace())

    def test_get_config_1(self):
        n = config_manager.Namespace()
        n.add_option('a', 1, 'the a')
        n.add_option('b', 17)
        c = config_manager.ConfigurationManager(
          [n],
          manager_controls=False,
          #use_config_files=False,
          use_auto_help=False,
          argv_source=[]
        )
        d = c.get_config()
        e = DotDict()
        e.a = 1
        e.b = 17
        self.assertEqual(d, e)

    def test_get_config_2(self):
        n = config_manager.Namespace()
        n.add_option('a', 1, 'the a')
        n.b = 17
        n.c = c = config_manager.Namespace()
        c.x = 'fred'
        c.y = 3.14159
        c.add_option('z', 99, 'the 99')
        c = config_manager.ConfigurationManager(
          [n],
          manager_controls=False,
          #use_config_files=False,
          use_auto_help=False,
          argv_source=[]
        )
        d = c.get_config()
        e = DotDict()
        e.a = 1
        e.b = 17
        e.c = DotDict()
        e.c.x = 'fred'
        e.c.y = 3.14159
        e.c.z = 99
        self.assertEqual(d, e)

    def test_walk_config(self):
        """step through them all"""
        n = config_manager.Namespace(doc='top')
        n.add_option('aaa', False, 'the a', short_form='a')
        n.c = config_manager.Namespace(doc='c space')
        n.c.add_option('fred', doc='husband from Flintstones')
        n.c.add_option('wilma', doc='wife from Flintstones')
        n.d = config_manager.Namespace(doc='d space')
        n.d.add_option('fred', doc='male neighbor from I Love Lucy')
        n.d.add_option('ethel', doc='female neighbor from I Love Lucy')
        n.d.x = config_manager.Namespace(doc='x space')
        n.d.x.add_option('size', 100, 'how big in tons', short_form='s')
        n.d.x.add_option('password', 'secrets', 'the password')
        c = config_manager.ConfigurationManager(
          [n],
          manager_controls=False,
          #use_config_files=False,
          use_auto_help=False,
          argv_source=[]
        )
        e = [('aaa', 'aaa', n.aaa.name),
             ('c', 'c', n.c._doc),
             ('c.wilma', 'wilma', n.c.wilma.name),
             ('c.fred', 'fred', n.c.fred.name),
             ('d', 'd', n.d._doc),
             ('d.ethel', 'ethel', n.d.ethel.name),
             ('d.fred', 'fred', n.d.fred.name),
             ('d.x', 'x', n.d.x._doc),
             ('d.x.size', 'size', n.d.x.size.name),
             ('d.x.password', 'password', n.d.x.password.name),
            ]
        e.sort()
        r = [(q, k, v.name if isinstance(v, config_manager.Option) else v._doc)
              for q, k, v in c.walk_config()]
        r.sort()
        for expected, received in zip(e, r):
            self.assertEqual(received, expected)

    def _some_namespaces(self):
        """set up some namespaces"""
        n = config_manager.Namespace(doc='top')
        n.add_option('aaa', '2011-05-04T15:10:00','the a',
          short_form='a',
          from_string_converter=dtu.datetime_from_ISO_string
        )
        n.c = config_manager.Namespace(doc='c space')
        n.c.add_option('fred', 'stupid', 'husband from Flintstones')
        n.c.add_option('wilma', 'waspish', 'wife from Flintstones')
        n.d = config_manager.Namespace(doc='d space')
        n.d.add_option('fred', 'crabby', 'male neighbor from I Love Lucy')
        n.d.add_option('ethel', 'silly', 'female neighbor from I Love Lucy')
        n.x = config_manager.Namespace(doc='x space')
        n.x.add_option('size', 100, 'how big in tons', short_form='s')
        n.x.add_option('password', 'secret', 'the password')
        return n

    def test_overlay_config_1(self):
        n = config_manager.Namespace()
        n.add_option('a')
        n.a.default = 1
        n.a.doc = 'the a'
        n.b = 17
        n.c = c = config_manager.Namespace()
        c.x = 'fred'
        c.y = 3.14159
        c.add_option('z')
        c.z.default = 99
        c.z.doc = 'the 99'
        c = config_manager.ConfigurationManager([n],
                                    manager_controls=False,
                                    #use_config_files=False,
                                    use_auto_help=False,
                                    argv_source=[])
        o = {"a": 2, "c.z": 22, "c.x": 'noob', "c.y": "2.89"}
        c.overlay_config_recurse(o)
        d = c.get_config()
        e = DotDict()
        e.a = 2
        e.b = 17
        e.c = DotDict()
        e.c.x = 'noob'
        e.c.y = 2.89
        e.c.z = 22
        self.assertEqual(d, e)

    def test_overlay_config_2(self):
        n = config_manager.Namespace()
        n.add_option('a')
        n.a.default = 1
        n.a.doc = 'the a'
        n.b = 17
        n.c = c = config_manager.Namespace()
        c.x = 'fred'
        c.y = 3.14159
        c.add_option('z')
        c.z.default = 99
        c.z.doc = 'the 99'
        c = config_manager.ConfigurationManager([n],
                                    manager_controls=False,
                                    #use_config_files=False,
                                    use_auto_help=False,
                                    argv_source=[])
        o = {"a": 2, "c.z": 22, "c.x": 'noob', "c.y": "2.89", "n": "not here"}
        c.overlay_config_recurse(o, ignore_mismatches=True)
        d = c.get_config()
        e = DotDict()
        e.a = 2
        e.b = 17
        e.c = DotDict()
        e.c.x = 'noob'
        e.c.y = 2.89
        e.c.z = 22
        self.assertEqual(d, e)

    def test_overlay_config_3(self):
        n = config_manager.Namespace()
        n.add_option('a')
        n.a.default = 1
        n.a.doc = 'the a'
        n.b = 17
        n.c = c = config_manager.Namespace()
        c.x = 'fred'
        c.y = 3.14159
        c.add_option('z')
        c.z.default = 99
        c.z.doc = 'the 99'
        c = config_manager.ConfigurationManager([n],
                                    manager_controls=False,
                                    #use_config_files=False,
                                    use_auto_help=False,
                                    argv_source=[])
        output = {
          "a": 2,
          "c.z": 22,
          "c.x": 'noob',
          "c.y": "2.89",
          "c.n": "not here"
        }
        self.assertRaises(NotAnOptionError,
                          c.overlay_config_recurse, output,
                          ignore_mismatches=False)

    def test_overlay_config_4(self):
        """test overlay dict w/flat source dict"""
        n = config_manager.Namespace()
        n.add_option('a', doc='the a', default=1)
        n.b = 17
        n.c = config_manager.Namespace()
        n.c.add_option('extra', doc='the x', default=3.14159)
        g = {'a': 2, 'c.extra': 2.89}
        c = config_manager.ConfigurationManager([n], [g],
                                    manager_controls=False,
                                    #use_config_files=False,
                                    use_auto_help=False,
                                    argv_source=[])
        self.assertEqual(c.option_definitions.a, n.a)
        self.assertTrue(isinstance(c.option_definitions.b,
                                   config_manager.Option))
        self.assertEqual(c.option_definitions.a.value, 2)
        self.assertEqual(c.option_definitions.b.value, 17)
        self.assertEqual(c.option_definitions.b.default, 17)
        self.assertEqual(c.option_definitions.b.name, 'b')
        self.assertEqual(c.option_definitions.c.extra.name, 'extra')
        self.assertEqual(c.option_definitions.c.extra.doc, 'the x')
        self.assertEqual(c.option_definitions.c.extra.default, 3.14159)
        self.assertEqual(c.option_definitions.c.extra.value, 2.89)

    def test_overlay_config_4a(self):
        """test overlay dict w/deep source dict"""
        n = config_manager.Namespace()
        n.add_option('a', 1, doc='the a')
        n.b = 17
        n.c = config_manager.Namespace()
        n.c.add_option('extra', doc='the x', default=3.14159)
        g = {'a': 2, 'c': {'extra': 2.89}}
        c = config_manager.ConfigurationManager([n], [g],
                                    manager_controls=False,
                                    #use_config_files=False,
                                    use_auto_help=False,
                                    argv_source=[])
        self.assertEqual(c.option_definitions.a, n.a)
        self.assertTrue(isinstance(c.option_definitions.b,
                                   config_manager.Option))
        self.assertEqual(c.option_definitions.a.value, 2)
        self.assertEqual(c.option_definitions.b.value, 17)
        self.assertEqual(c.option_definitions.b.default, 17)
        self.assertEqual(c.option_definitions.b.name, 'b')
        self.assertEqual(c.option_definitions.c.extra.name, 'extra')
        self.assertEqual(c.option_definitions.c.extra.doc, 'the x')
        self.assertEqual(c.option_definitions.c.extra.default, 3.14159)
        self.assertEqual(c.option_definitions.c.extra.value, 2.89)

    def test_overlay_config_5(self):
        """test namespace definition w/getopt"""
        n = config_manager.Namespace()
        n.add_option('a', doc='the a', default=1)
        n.b = 17
        n.add_option('c', doc='the c', default=False)
        c = config_manager.ConfigurationManager([n], [getopt],
                                    manager_controls=False,
                                    #use_config_files=False,
                                    use_auto_help=False,
                                    argv_source=['--a', '2', '--c'])
        self.assertEqual(c.option_definitions.a, n.a)
        self.assertTrue(isinstance(c.option_definitions.b,
                                   config_manager.Option))
        self.assertEqual(c.option_definitions.a.value, 2)
        self.assertEqual(c.option_definitions.b.value, 17)
        self.assertEqual(c.option_definitions.b.default, 17)
        self.assertEqual(c.option_definitions.b.name, 'b')
        self.assertEqual(c.option_definitions.c.name, 'c')
        self.assertEqual(c.option_definitions.c.value, True)

    def test_overlay_config_6(self):
        """test namespace definition w/getopt"""
        n = config_manager.Namespace()
        n.add_option('a', doc='the a', default=1)
        n.b = 17
        n.c = config_manager.Namespace()
        n.c.add_option('extra', short_form='e', doc='the x', default=3.14159)
        c = config_manager.ConfigurationManager([n], [getopt],
                                    manager_controls=False,
                                    #use_config_files=False,
                                    use_auto_help=False,
                                    argv_source=['--a', '2', '--c.extra',
                                                 '11.0'])
        self.assertEqual(c.option_definitions.a, n.a)
        self.assertEqual(type(c.option_definitions.b), config_manager.Option)
        self.assertEqual(c.option_definitions.a.value, 2)
        self.assertEqual(c.option_definitions.b.value, 17)
        self.assertEqual(c.option_definitions.b.default, 17)
        self.assertEqual(c.option_definitions.b.name, 'b')
        self.assertEqual(c.option_definitions.c.extra.name, 'extra')
        self.assertEqual(c.option_definitions.c.extra.doc, 'the x')
        self.assertEqual(c.option_definitions.c.extra.default, 3.14159)
        self.assertEqual(c.option_definitions.c.extra.value, 11.0)

    def test_overlay_config_6a(self):
        """test namespace w/getopt w/short form"""
        n = config_manager.Namespace()
        n.add_option('a', doc='the a', default=1)
        n.b = 17
        n.c = config_manager.Namespace()
        n.c.add_option('extra', 3.14159, 'the x', short_form='e')
        c = config_manager.ConfigurationManager([n], [getopt],
                                    manager_controls=False,
                                    #use_config_files=False,
                                    use_auto_help=False,
                                    argv_source=['--a', '2', '-e', '11.0'])
        self.assertEqual(c.option_definitions.a, n.a)
        self.assertEqual(type(c.option_definitions.b), config_manager.Option)
        self.assertEqual(c.option_definitions.a.value, 2)
        self.assertEqual(c.option_definitions.b.value, 17)
        self.assertEqual(c.option_definitions.b.default, 17)
        self.assertEqual(c.option_definitions.b.name, 'b')
        self.assertEqual(c.option_definitions.c.extra.name, 'extra')
        self.assertEqual(c.option_definitions.c.extra.doc, 'the x')
        self.assertEqual(c.option_definitions.c.extra.default, 3.14159)
        self.assertEqual(c.option_definitions.c.extra.value, 11.0)

    def test_overlay_config_7(self):
        """test namespace definition flat file"""
        n = config_manager.Namespace()
        n.add_option('a', doc='the a', default=1)
        n.b = 17
        n.c = config_manager.Namespace()
        n.c.add_option('extra', 3.14159, 'the x')
        n.c.add_option('string', 'fred', doc='str')

        @contextmanager
        def dummy_open():
            yield ['# comment line to be ignored\n',
                   '\n',  # blank line to be ignored
                   'a=22\n',
                   'b = 33\n',
                   'c.extra = 2.0\n',
                   'c.string =   wilma\n'
                  ]
        #g = config_manager.ConfValueSource('dummy-filename', dummy_open)
        c = config_manager.ConfigurationManager([n], [dummy_open],
                                    manager_controls=False,
                                    #use_config_files=False,
                                    use_auto_help=False)
        self.assertEqual(c.option_definitions.a, n.a)
        self.assertEqual(type(c.option_definitions.b), config_manager.Option)
        self.assertEqual(c.option_definitions.a.value, 22)
        self.assertEqual(c.option_definitions.b.value, 33)
        self.assertEqual(c.option_definitions.b.default, 17)
        self.assertEqual(c.option_definitions.b.name, 'b')
        self.assertEqual(c.option_definitions.c.extra.name, 'extra')
        self.assertEqual(c.option_definitions.c.extra.doc, 'the x')
        self.assertEqual(c.option_definitions.c.extra.default, 3.14159)
        self.assertEqual(c.option_definitions.c.extra.value, 2.0)
        self.assertEqual(c.option_definitions.c.string.name, 'string')
        self.assertEqual(c.option_definitions.c.string.doc, 'str')
        self.assertEqual(c.option_definitions.c.string.default, 'fred')
        self.assertEqual(c.option_definitions.c.string.value, 'wilma')

    def test_overlay_config_8(self):
        """test namespace definition ini file"""
        n = config_manager.Namespace()
        n.other = config_manager.Namespace()
        n.other.add_option('t', 'tee', 'the t')
        n.d = config_manager.Namespace()
        n.d.add_option('a', 1, doc='the a')
        n.d.b = 17
        n.c = config_manager.Namespace()
        n.c.add_option('extra', 3.14159, 'the x')
        n.c.add_option('string', 'fred', doc='str')
        ini_data = """
[other]
t=tea
[d]
# blank line to be ignored
a=22
b = 33
[c]
extra = 2.0
string =   wilma
"""
        config = ConfigParser.RawConfigParser()
        config.readfp(io.BytesIO(ini_data))
        c = config_manager.ConfigurationManager([n], [config],
                                    manager_controls=False,
                                    use_auto_help=False)
        self.assertEqual(c.option_definitions.other.t.name, 't')
        self.assertEqual(c.option_definitions.other.t.value, 'tea')
        self.assertEqual(c.option_definitions.d.a, n.d.a)
        self.assertEqual(type(c.option_definitions.d.b), config_manager.Option)
        self.assertEqual(c.option_definitions.d.a.value, 22)
        self.assertEqual(c.option_definitions.d.b.value, 33)
        self.assertEqual(c.option_definitions.d.b.default, 17)
        self.assertEqual(c.option_definitions.d.b.name, 'b')
        self.assertEqual(c.option_definitions.c.extra.name, 'extra')
        self.assertEqual(c.option_definitions.c.extra.doc, 'the x')
        self.assertEqual(c.option_definitions.c.extra.default, 3.14159)
        self.assertEqual(c.option_definitions.c.extra.value, 2.0)
        self.assertEqual(c.option_definitions.c.string.name, 'string')
        self.assertEqual(c.option_definitions.c.string.doc, 'str')
        self.assertEqual(c.option_definitions.c.string.default, 'fred')
        self.assertEqual(c.option_definitions.c.string.value, 'wilma')

    def test_overlay_config_9(self):
        """test namespace definition ini file"""
        n = config_manager.Namespace()
        n.other = config_manager.Namespace()
        n.other.add_option('t', 'tee', 'the t')
        n.d = config_manager.Namespace()
        n.d.add_option('a', 1, doc='the a')
        n.d.b = 17
        n.c = config_manager.Namespace()
        n.c.add_option('extra', 3.14159, 'the x')
        n.c.add_option('string', 'fred', 'str')
        ini_data = """
[other]
t=tea
[d]
# blank line to be ignored
a=22
[c]
extra = 2.0
string =   from ini
"""
        config = ConfigParser.RawConfigParser()
        config.readfp(io.BytesIO(ini_data))
        e = DotDict()
        e.fred = DotDict()  # should be ignored
        e.fred.t = 'T'  # should be ignored
        e.d = DotDict()
        e.d.a = 16
        e.c = DotDict()
        e.c.extra = 18.6
        e.c.string = 'from environment'

        #fake_os_module = DotDict()
        #fake_os_module.environ = e
        #import configman.value_sources.for_mapping as fm
        #saved_os = fm.os
        #fm.os = fake_os_module
        saved_environ = os.environ
        os.environ = e
        try:
            c = config_manager.ConfigurationManager([n], [e, config, getopt],
                                        manager_controls=False,
                                        use_auto_help=False,
                                        argv_source=['--other.t', 'TTT',
                                                     '--c.extra', '11.0'])
        finally:
            os.environ = saved_environ
        #fm.os = saved_os
        self.assertEqual(c.option_definitions.other.t.name, 't')
        self.assertEqual(c.option_definitions.other.t.value, 'TTT')
        self.assertEqual(c.option_definitions.d.a, n.d.a)
        self.assertEqual(type(c.option_definitions.d.b), config_manager.Option)
        self.assertEqual(c.option_definitions.d.a.value, 22)
        self.assertEqual(c.option_definitions.d.b.value, 17)
        self.assertEqual(c.option_definitions.d.b.default, 17)
        self.assertEqual(c.option_definitions.d.b.name, 'b')
        self.assertEqual(c.option_definitions.c.extra.name, 'extra')
        self.assertEqual(c.option_definitions.c.extra.doc, 'the x')
        self.assertEqual(c.option_definitions.c.extra.default, 3.14159)
        self.assertEqual(c.option_definitions.c.extra.value, 11.0)
        self.assertEqual(c.option_definitions.c.string.name, 'string')
        self.assertEqual(c.option_definitions.c.string.doc, 'str')
        self.assertEqual(c.option_definitions.c.string.default, 'fred')
        self.assertEqual(c.option_definitions.c.string.value, 'from ini')

    def test_overlay_config_10(self):
        """test namespace definition ini file"""
        n = config_manager.Namespace()
        n.add_option('t', 'tee', 'the t')
        n.d = config_manager.Namespace()
        n.d.add_option('a', 1, 'the a')
        n.d.b = 17
        n.c = config_manager.Namespace()
        n.c.add_option('extra', 3.14159, 'the x')
        n.c.add_option('string', 'fred', doc='str')
        ini_data = """
[top_level]
t=tea
[d]
# blank line to be ignored
a=22
[c]
extra = 2.0
string =   from ini
"""
        config = ConfigParser.RawConfigParser()
        config.readfp(io.BytesIO(ini_data))
        #g = config_manager.IniValueSource(config)
        e = DotDict()
        e.t = 'T'
        e.d = DotDict()
        e.d.a = 16
        e.c = DotDict()
        e.c.extra = 18.6
        e.c.string = 'from environment'
        #v = config_manager.GetoptValueSource(
          #argv_source=['--c.extra', '11.0']
        #)
        c = config_manager.ConfigurationManager([n], [e, config, getopt],
                                    manager_controls=False,
                                    argv_source=['--c.extra', '11.0'],
                                    #use_config_files=False,
                                    use_auto_help=False)
        self.assertEqual(c.option_definitions.t.name, 't')
        self.assertEqual(c.option_definitions.t.value, 'tea')
        self.assertEqual(c.option_definitions.d.a, n.d.a)
        self.assertEqual(type(c.option_definitions.d.b), config_manager.Option)
        self.assertEqual(c.option_definitions.d.a.value, 22)
        self.assertEqual(c.option_definitions.d.b.value, 17)
        self.assertEqual(c.option_definitions.d.b.default, 17)
        self.assertEqual(c.option_definitions.d.b.name, 'b')
        self.assertEqual(c.option_definitions.c.extra.name, 'extra')
        self.assertEqual(c.option_definitions.c.extra.doc, 'the x')
        self.assertEqual(c.option_definitions.c.extra.default, 3.14159)
        self.assertEqual(c.option_definitions.c.extra.value, 11.0)
        self.assertEqual(c.option_definitions.c.string.name, 'string')
        self.assertEqual(c.option_definitions.c.string.doc, 'str')
        self.assertEqual(c.option_definitions.c.string.default, 'fred')
        self.assertEqual(c.option_definitions.c.string.value, 'from ini')

    def test_get_option_names(self):
        n = config_manager.Namespace()
        n.add_option('a', 1, 'the a')
        n.b = 17
        n.c = config_manager.Namespace()
        n.c.add_option('fred')
        n.c.add_option('wilma')
        n.d = config_manager.Namespace()
        n.d.add_option('fred')
        n.d.add_option('wilma')
        n.d.x = config_manager.Namespace()
        n.d.x.add_option('size')
        c = config_manager.ConfigurationManager([n],
                                    manager_controls=False,
                                    #use_config_files=False,
                                    use_auto_help=False,
                                    argv_source=[])
        names = c.get_option_names()
        names.sort()
        e = ['a', 'b', 'c.fred', 'c.wilma', 'd.fred', 'd.wilma', 'd.x.size']
        e.sort()
        self.assertEqual(names, e)

    def test_get_option_by_name(self):
        n = config_manager.Namespace()
        n.add_option('a', 1, 'the a')
        n.b = 17
        n.c = config_manager.Namespace()
        n.c.add_option('fred')
        n.c.add_option('wilma')
        n.d = config_manager.Namespace()
        n.d.add_option('fred')
        n.d.add_option('wilma')
        n.d.x = config_manager.Namespace()
        n.d.x.add_option('size')
        c = config_manager.ConfigurationManager([n],
                                    manager_controls=False,
                                    #use_config_files=False,
                                    use_auto_help=False,
                                    argv_source=[])
        self.assertEqual(c.get_option_by_name('a'), n.a)
        self.assertEqual(c.get_option_by_name('b').name, 'b')
        self.assertEqual(c.get_option_by_name('c.fred'), n.c.fred)
        self.assertEqual(c.get_option_by_name('c.wilma'), n.c.wilma)
        self.assertEqual(c.get_option_by_name('d.fred'), n.d.fred)
        self.assertEqual(c.get_option_by_name('d.wilma'), n.d.wilma)
        self.assertEqual(c.get_option_by_name('d.wilma'), n.d.wilma)
        self.assertEqual(c.get_option_by_name('d.x.size'), n.d.x.size)

    def test_output_summary(self):
        """test_output_summary: the output from help"""
        n = config_manager.Namespace()
        n.add_option('aaa', False, 'the a', short_form='a')
        n.b = 17
        n.c = config_manager.Namespace()
        n.c.add_option('fred', doc='husband from Flintstones')
        n.d = config_manager.Namespace()
        n.d.add_option('fred', doc='male neighbor from I Love Lucy')
        n.d.x = config_manager.Namespace()
        n.d.x.add_option('size', 100, 'how big in tons', short_form='s')
        n.d.x.add_option('password', 'secrets', 'the password')
        c = config_manager.ConfigurationManager([n],
                                    manager_controls=False,
                                    #use_config_files=False,
                                    use_auto_help=False,
                                    argv_source=[])
        s = StringIO()
        c.output_summary(output_stream=s)
        r = s.getvalue()
        s.close()
        expect = [
          '\t-a, --aaa',
          '\t\tthe a',
          '\t    --b',
          '\t\tno documentation available (default: 17)',
          '\t    --c.fred',
          '\t\thusband from Flintstones (default: None)',
          '\t    --d.fred',
          '\t\tmale neighbor from I Love Lucy (default: None)',
          '\t    --d.x.password',
          '\t\tthe password (default: ********)',
          '\t-s, --d.x.size',
          '\t\thow big in tons (default: 100)',
        ]
        expect = '\n'.join(expect)
        self.assertEqual(r.rstrip(), expect.rstrip())

    def test_config_manager_output_summary(self):
        """Test that ConfigurationManager().output_summary() works"""
        n = config_manager.Namespace()
        n.add_option('aaa', False, 'the a', short_form='a')
        n.b = 17
        n.c = config_manager.Namespace()
        n.c.add_option('fred', doc='the doc',
                              default="[ ('version', 'fred', 100), "
                                     "('product', 'sally', 100)]",
                             from_string_converter=eval)
        n.c.add_option('wilma', doc='wife from Flintstones')
        c = config_manager.ConfigurationManager([n],
                                    manager_controls=False,
                                    #use_config_files=False,
                                    use_auto_help=False,
                                    argv_source=[])
        s = StringIO()
        c.output_summary(output_stream=s)
        received = s.getvalue()
        s.close()
        expected = r"""	-a, --aaa
		the a
	    --b
		no documentation available (default: 17)
	    --c.fred
		the doc (default: [('version', 'fred', 100), ('product', 'sally', 100)])
	    --c.wilma
		wife from Flintstones (default: None)
        """
        self.assertEqual(received.strip(), expected.strip())

    def test_eval_as_converter(self):
        """does eval work as a to string converter on an Option object?"""
        n = config_manager.Namespace()
        n.add_option('aaa', doc='the a', default='', short_form='a')
        self.assertEqual(n.aaa.value, '')

    def test_RequiredConfig_get_required_config(self):

        class Foo:
            required_config = {'foo': True}

        class Bar:
            required_config = {'bar': False}

        class Poo:
            pass

        class Combined(config_manager.RequiredConfig, Foo, Poo, Bar):
            pass

        result = Combined.get_required_config()
        self.assertEqual(result, {'foo': True, 'bar': False})

    #def test_create_ConfigurationManager_with_use_config_files(self):
        ## XXX incomplete! (peter, 15 Aug)
        #c = config_manager.ConfigurationManager([],
                                                #manager_controls=False,
                                                ##use_config_files=True,
                                                #use_auto_help=False,
                                                #argv_source=[])
        #self.assertTrue(c.ini_source is None)
        #self.assertTrue(c.conf_source is None)
        #self.assertTrue(c.json_source is None)