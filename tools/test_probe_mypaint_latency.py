import unittest
from unittest.mock import patch
import probe_mypaint_latency as probe
from types import SimpleNamespace
from probe_mypaint_latency import describe


class MyPaintLatencySummaryTests(unittest.TestCase):
    def test_high_idle_only_remains_after_collection_without_package_write(self):
        from unittest.mock import Mock
        class Freehand:
            MOTION_QUEUE_PRIORITY = 200
            def motion_notify_cb(self, *args):
                pass
            def _process_queued_event(self, *args):
                pass
        class Canvas:
            def _draw_cb(self, *args):
                pass
        original = Freehand._process_queued_event
        glib = SimpleNamespace(PRIORITY_DEFAULT_IDLE=200, PRIORITY_HIGH_IDLE=100,
                               timeout_add_seconds=Mock(return_value=1))
        def entrypoint(*args, **kwargs):
            self.assertEqual(Freehand.MOTION_QUEUE_PRIORITY, 100)
            Freehand()._process_queued_event(object(), (10, 0, 0, .5, 0, 0, 1, 0, 0))
            calls = glib.timeout_add_seconds.call_args_list
            self.assertEqual([call.args[0] for call in calls], [300, 15, 90])
            calls[-1].args[1]()
            self.assertIs(Freehand._process_queued_event, original)
            self.assertEqual(Freehand.MOTION_QUEUE_PRIORITY, 100)
        modules = {'gui': SimpleNamespace(__path__=[]), 'lib': SimpleNamespace(__path__=[]),
                   'gui.freehand': SimpleNamespace(FreehandMode=Freehand),
                   'gui.tileddrawwidget': SimpleNamespace(CanvasRenderer=Canvas),
                   'gui.application': SimpleNamespace(get_app=lambda: None),
                   'lib.gibindings': SimpleNamespace(GLib=glib)}
        with patch.object(probe.sys, 'argv', ['probe', '--high-idle-only']), \
             patch.object(probe.os, 'getuid', return_value=1000), \
             patch.dict(probe.os.environ, {'WAYLAND_DISPLAY': 't630-gnome-0'}), \
             patch.object(probe.resource, 'setrlimit'), \
             patch.object(probe.subprocess, 'check_output', return_value='2.0.1-10build2'), \
             patch.dict(probe.sys.modules, modules), \
             patch.object(probe.sys, 'path', []), \
             patch.object(probe, 'event_age_ms', return_value=5), \
             patch.object(probe.runpy, 'run_path', side_effect=entrypoint):
            probe.main()

    def test_measurement_timers_wait_for_first_painting_event(self):
        from unittest.mock import Mock
        class Freehand:
            MOTION_QUEUE_PRIORITY = 200
            def motion_notify_cb(self, *args):
                pass
            def _process_queued_event(self, *args):
                pass
        class Canvas:
            def _draw_cb(self, *args):
                pass
        glib = SimpleNamespace(PRIORITY_DEFAULT_IDLE=200, PRIORITY_HIGH_IDLE=100,
                               timeout_add_seconds=Mock(return_value=1))
        def entrypoint(*args, **kwargs):
            self.assertEqual([call.args[0] for call in glib.timeout_add_seconds.call_args_list], [300])
            mode = Freehand()
            mode._process_queued_event(object(), (10, 0, 0, 0, 0, 0, 1, 0, 0))
            self.assertEqual(glib.timeout_add_seconds.call_count, 1)
            mode._process_queued_event(object(), (10, 0, 0, .5, 0, 0, 1, 0, 0))
            self.assertEqual([call.args[0] for call in glib.timeout_add_seconds.call_args_list], [300, 15, 90, 35])
            mode._process_queued_event(object(), (20, 0, 0, .5, 0, 0, 1, 0, 0))
            self.assertEqual(glib.timeout_add_seconds.call_count, 4)
        modules = {'gui': SimpleNamespace(__path__=[]), 'lib': SimpleNamespace(__path__=[]),
                   'gui.freehand': SimpleNamespace(FreehandMode=Freehand),
                   'gui.tileddrawwidget': SimpleNamespace(CanvasRenderer=Canvas),
                   'lib.gibindings': SimpleNamespace(GLib=glib)}
        with patch.object(probe.sys, 'argv', ['probe', '--queue-priority-trial']), \
             patch.object(probe.os, 'getuid', return_value=1000), \
             patch.dict(probe.os.environ, {'WAYLAND_DISPLAY': 't630-gnome-0'}), \
             patch.object(probe.resource, 'setrlimit'), \
             patch.object(probe.subprocess, 'check_output', return_value='2.0.1-10build2'), \
             patch.dict(probe.sys.modules, modules), \
             patch.object(probe.sys, 'path', []), \
             patch.object(probe, 'event_age_ms', return_value=5), \
             patch.object(probe.runpy, 'run_path', side_effect=entrypoint):
            probe.main()

    def test_rescheduling_keeps_queue_and_replaces_only_its_source(self):
        from collections import deque
        from unittest.mock import Mock
        queue = deque(['fixture-event'])
        state = SimpleNamespace(motion_processing_cbid=12, motion_queue=queue)
        tdw = object()
        callback = Mock()
        mode = SimpleNamespace(_drawing_state={tdw: state}, _motion_queue_idle_cb=callback)
        glib = SimpleNamespace(source_remove=Mock(return_value=True), idle_add=Mock(return_value=23))
        self.assertEqual(probe.reschedule_queues([mode], glib, 100), 1)
        glib.source_remove.assert_called_once_with(12)
        glib.idle_add.assert_called_once_with(callback, tdw, priority=100)
        self.assertEqual(state.motion_processing_cbid, 23)
        self.assertIs(state.motion_queue, queue)
        self.assertEqual(list(queue), ['fixture-event'])

    def test_missing_source_cannot_duplicate_callback(self):
        from unittest.mock import Mock
        state = SimpleNamespace(motion_processing_cbid=12)
        mode = SimpleNamespace(_drawing_state={object(): state})
        glib = SimpleNamespace(source_remove=Mock(return_value=False), idle_add=Mock())
        with self.assertRaises(RuntimeError):
            probe.reschedule_queues([mode], glib, 100)
        glib.idle_add.assert_not_called()

    def test_empty_is_not_acceptance(self):
        self.assertIn('inconclusive', describe([]))

    def test_aggregates_only_and_no_mutation(self):
        values = [9, 1, 5]
        self.assertEqual(describe(values), 'samples=3 median=5.000 p95=9.000 max=9.000')
        self.assertEqual(values, [9, 1, 5])

    def test_root_and_wrong_display_refuse_before_gui_import(self):
        for uid, display in ((0, 't630-gnome-0'), (1000, 'other-display')):
            with patch.object(probe.sys, 'argv', ['probe']), \
                 patch.object(probe.os, 'getuid', return_value=uid), \
                 patch.dict(probe.os.environ, {'WAYLAND_DISPLAY': display}), \
                 patch.object(probe.subprocess, 'check_output') as query:
                with self.assertRaises(SystemExit):
                    probe.main()
                query.assert_not_called()

    def test_unsupported_app_version_refuses_before_gui_import(self):
        with patch.object(probe.sys, 'argv', ['probe']), \
             patch.object(probe.os, 'getuid', return_value=1000), \
             patch.object(probe.resource, 'setrlimit'), \
             patch.dict(probe.os.environ, {'WAYLAND_DISPLAY': 't630-gnome-0'}), \
             patch.object(probe.subprocess, 'check_output', return_value='unsupported'):
            with self.assertRaises(SystemExit):
                probe.main()
