import unittest
from relocate_mutter_trace_gir import DIRECTORY, LIBRARIES, relocate


class MutterGirRelocationTests(unittest.TestCase):
    def fixture(self, name, library, version='14'):
        return (f'<repository xmlns="http://www.gtk.org/introspection/core/1.0">'
                f'<namespace name="{name}" version="{version}" shared-library="{library}">'
                '<function name="preserved" /></namespace></repository>')

    def test_only_exact_shared_library_attribute_changes(self):
        for name, library in LIBRARIES.items():
            original = self.fixture(name, library)
            modified = relocate(original)
            self.assertEqual(modified.replace(DIRECTORY + '/', ''), original)

    def test_arbitrary_paths_names_versions_are_rejected(self):
        for name, library, version in (
                ('Cogl', '/unexpected/lib.so', '14'),
                ('GLib', 'libmutter-cogl-14.so.0', '14'),
                ('Cogl', 'libmutter-cogl-14.so.0', '15')):
            with self.assertRaises(ValueError):
                relocate(self.fixture(name, library, version))

    def test_duplicate_namespaces_are_rejected(self):
        with self.assertRaises(ValueError):
            relocate('<repository xmlns="http://www.gtk.org/introspection/core/1.0">'
                     '<namespace name="Cogl" /><namespace name="Meta" /></repository>')
