import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import hashlib

import prepare_mutter_pen_trace as trace


class MutterPenTraceTests(unittest.TestCase):
    def test_syncobj_build_fix_changes_only_includes(self):
        with tempfile.TemporaryDirectory(prefix='t630-mutter-syncobj-test-') as directory:
            root = Path(directory)
            path = root / 'src/wayland/meta-wayland-linux-drm-syncobj.c'
            path.parent.mkdir(parents=True)
            path.write_text(trace.SYNCOBJ_ANCHOR)
            with self.assertRaises(ValueError):
                trace.build_syncobj_configuration_patch(root)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            with patch.object(trace, 'SYNCOBJ_SHA', digest):
                result = trace.build_syncobj_configuration_patch(root)
            changes = [line[1:] for line in result.splitlines()
                       if line[:1] in ('+', '-') and line[:3] not in ('+++', '---')]
            self.assertEqual(len(changes), 5)
            self.assertTrue(all(line.startswith('#include ') for line in changes))
            self.assertEqual(path.read_text(), trace.SYNCOBJ_ANCHOR)

    def test_nested_build_fix_only_removes_redundant_else(self):
        with tempfile.TemporaryDirectory(prefix='t630-mutter-context-test-') as directory:
            root = Path(directory)
            path = root / 'src/core/meta-context-main.c'
            path.parent.mkdir(parents=True)
            path.write_text(trace.CONTEXT_ANCHOR + '\n')
            with self.assertRaises(ValueError):
                trace.build_nested_configuration_patch(root)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            with patch.object(trace, 'CONTEXT_SHA', digest):
                result = trace.build_nested_configuration_patch(root)
            removed = [line for line in result.splitlines()
                       if line.startswith('-') and not line.startswith('---')]
            added = [line for line in result.splitlines()
                     if line.startswith('+') and not line.startswith('+++')]
            self.assertEqual(removed, ['-      else'])
            self.assertEqual(added, [])
            self.assertEqual(path.read_text(), trace.CONTEXT_ANCHOR + '\n')

    def test_instrumentation_is_bounded_and_does_not_replace_events(self):
        fixtures = {
            'src/backends/x11/meta-seat-x11.c':
                'static double *\ntranslate_axes (\n' + trace.MOTION_ANCHOR,
            'src/wayland/meta-wayland-tablet-seat.c':
                'static gboolean\nis_tablet_device (\n' + trace.SEAT_ANCHOR,
            'src/wayland/meta-wayland-tablet-tool.c':
                'static void\nrepick_for_event (\n' + trace.REPICK_ANCHOR + trace.HANDLE_ANCHOR,
        }
        for relative, original in fixtures.items():
            modified = trace.instrument(relative, original)
            self.assertIn(trace.HELPER, modified)
            self.assertIn('trace_count++ < 8', modified)
            self.assertNotIn('clutter_event_put', modified)
            self.assertNotIn('clutter_event_proximity_new', modified)
            self.assertNotIn('translate_axes (source_device', modified)
        self.assertIn(trace.MOTION_ANCHOR,
                      trace.instrument(next(iter(fixtures)), next(iter(fixtures.values()))))

    def test_ambiguous_or_unknown_sources_fail_closed(self):
        with self.assertRaises(ValueError):
            trace.instrument('unknown.c', '')
        with self.assertRaises(ValueError):
            trace.insert_once('xx', 'x', 'trace')
        with self.assertRaises(ValueError):
            trace.insert_once('known', 'missing', 'trace')

    def test_changed_source_emits_no_patch_and_changes_no_files(self):
        with tempfile.TemporaryDirectory(prefix='t630-mutter-source-test-') as directory:
            root = Path(directory)
            relative = next(iter(trace.SOURCE_SHA))
            path = root / relative
            path.parent.mkdir(parents=True)
            path.write_text('unreviewed source')
            with self.assertRaises(ValueError):
                trace.build_patch(root)
            self.assertEqual(path.read_text(), 'unreviewed source')
