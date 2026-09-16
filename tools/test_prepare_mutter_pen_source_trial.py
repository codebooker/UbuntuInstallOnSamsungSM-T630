import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import shutil
import subprocess

import prepare_mutter_pen_source_trial as trial


class MutterPenSourceTrialTests(unittest.TestCase):
    def test_compiled_guard_rejects_nonprivate_names_and_unset_flag(self):
        compiler = shutil.which('cc')
        pkg_config = shutil.which('pkg-config')
        if not compiler or not pkg_config:
            self.skipTest('C compiler and GLib development files required.')
        flags = subprocess.run([pkg_config, '--cflags', '--libs', 'glib-2.0'],
                               capture_output=True, text=True, timeout=5)
        if flags.returncode:
            self.skipTest('GLib development files required.')
        import shlex
        program = '#include <glib.h>\n' + trial.NAME_HELPER + '''
int main (void)
{
  const char *valid[] = {"xwayland-tablet stylus:14", "xwayland-tablet eraser:1"};
  const char *invalid[] = {NULL, "", "Core Pointer", "xwayland-tablet cursor:14",
                          "xwayland-tablet stylus:", "xwayland-tablet stylus:14x",
                          "xwayland-tablet stylus:-1", "xwayland-tablet eraser:1 "};
  unsigned i;
  g_unsetenv ("T630_X11_PEN_FIX");
  for (i = 0; i < G_N_ELEMENTS (valid); i++)
    if (t630_x11_pen_fix_name (valid[i])) return 1;
  g_setenv ("T630_X11_PEN_FIX", "0", TRUE);
  if (t630_x11_pen_fix_name (valid[0])) return 2;
  g_setenv ("T630_X11_PEN_FIX", "1", TRUE);
  for (i = 0; i < G_N_ELEMENTS (valid); i++)
    if (!t630_x11_pen_fix_name (valid[i])) return 3;
  for (i = 0; i < G_N_ELEMENTS (invalid); i++)
    if (t630_x11_pen_fix_name (invalid[i])) return 4;
  return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix='t630-pen-guard-') as directory:
            binary = str(Path(directory) / 'guard')
            subprocess.run([compiler, '-Wall', '-Wextra', '-Werror', '-x', 'c', '-',
                            '-o', binary, *shlex.split(flags.stdout)], input=program,
                           capture_output=True, text=True, check=True, timeout=30)
            subprocess.run([binary], check=True, capture_output=True, timeout=5)

    def fixtures(self):
        return {
            'src/backends/x11/meta-seat-x11.c':
                'static ClutterInputDevice *\ncreate_device (\n' + trial.MODE_ANCHOR +
                trial.AXIS_ANCHOR +
                '\naxes = translate_axes (device, x, y, &xev->valuators);\n' * 2,
            'src/wayland/meta-wayland-tablet-tool.c': 'void\n' + trial.UPDATE_ANCHOR,
        }

    def test_private_device_gate_and_real_event_only(self):
        for relative, text in self.fixtures().items():
            result = trial.modify(relative, text)
            self.assertIn('g_getenv ("T630_X11_PEN_FIX")', result)
            self.assertIn('g_ascii_isdigit', result)
            self.assertNotIn('xwayland-tablet cursor:', result)
            for unsafe in ('clutter_event_put', 'clutter_event_proximity_new',
                           'clutter_event_motion_new', 'XIGrabDevice', 'XTestFake'):
                self.assertNotIn(unsafe, result)
        xi = trial.modify(next(iter(self.fixtures())), next(iter(self.fixtures().values())))
        self.assertIn('source_device : device', xi)
        self.assertIn('values++;', xi)
        self.assertIn('mode == CLUTTER_INPUT_MODE_PHYSICAL', xi)
        tool = trial.modify('src/wayland/meta-wayland-tablet-tool.c',
                            self.fixtures()['src/wayland/meta-wayland-tablet-tool.c'])
        self.assertIn('get_serial (tool->device_tool) == 630', tool)
        self.assertLess(tool.index('repick_for_event (tool, event)'),
                        tool.index('switch (clutter_event_type (event))'))
        self.assertIn('Hover-out is not yet covered', tool)

    def test_known_inputs_emit_diff_without_edits_and_changed_input_fails(self):
        with tempfile.TemporaryDirectory(prefix='t630-pen-source-trial-') as directory:
            root = Path(directory)
            hashes = {}
            for relative, original in self.fixtures().items():
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(original)
                hashes[relative] = hashlib.sha256(target.read_bytes()).hexdigest()
            with patch.object(trial, 'SOURCE_SHA', hashes):
                result = trial.build_patch(root)
                self.assertIn('--- a/src/backends/x11/meta-seat-x11.c', result)
                for relative, original in self.fixtures().items():
                    self.assertEqual((root / relative).read_text(), original)
                (root / 'src/wayland/meta-wayland-tablet-tool.c').write_text('changed')
                with self.assertRaises(ValueError):
                    trial.build_patch(root)

    def test_ambiguous_insertions_fail_closed(self):
        for text, anchor in (('xx', 'x'), ('known', 'missing')):
            with self.assertRaises(ValueError):
                trial.replace_once(text, anchor, 'replacement')
        with self.assertRaises(ValueError):
            trial.modify('unreviewed.c', '')
        fixtures = self.fixtures()
        with self.assertRaises(ValueError):
            trial.modify(next(iter(fixtures)), next(iter(fixtures.values())) +
                         '\naxes = translate_axes (device, x, y, &xev->valuators);')
