#!/usr/bin/python3
"""Attended MyPaint timing probe: aggregate timings, never handwriting.

Wraps only this process's handlers, preserving arguments/results/exceptions.
Starts on the first painting event. After 90 seconds restores the handlers
without closing or saving the app; waiting times out after five minutes.
No package edits, input injection, or pressure adjustment. An explicit queue
trial temporarily changes only this app's idle scheduling, then restores it.
The separate high-idle-only trial keeps it active until this process closes;
it never changes the normal launcher or installed package.
"""
import os
import argparse
import cProfile
import runpy
import resource
import statistics
import math
import subprocess
import sys
import time
import weakref
from collections import deque
from functools import wraps
from gdk_event_latency import event_age_ms


def describe(values):
    if not values:
        return 'samples=0 (inconclusive)'
    ordered = sorted(values)
    return (f'samples={len(ordered)} median={statistics.median(ordered):.3f} '
            f'p95={ordered[math.ceil(len(ordered)*.95)-1]:.3f} max={ordered[-1]:.3f}')


def reschedule_queues(modes, glib, priority):
    """Retain every queued stroke; replace only owned idle callback sources."""
    changed = 0
    for mode in list(modes):
        for tdw, state in list(mode._drawing_state.items()):
            old = state.motion_processing_cbid
            if old is None:
                continue
            if isinstance(old, bool) or not isinstance(old, int) or old <= 0:
                raise RuntimeError('Unexpected owned motion callback ID.')
            if not glib.source_remove(old):
                raise RuntimeError('Owned motion callback missing; refusing duplicate scheduling.')
            state.motion_processing_cbid = glib.idle_add(
                mode._motion_queue_idle_cb, tdw, priority=priority)
            changed += 1
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile-strokes', action='store_true',
                        help='Also profile the first 1000 stroke callbacks; changes timing overhead')
    parser.add_argument('--queue-priority-trial', action='store_true',
                        help='35s baseline, then high-idle queue scheduling until 90s; restores afterward')
    parser.add_argument('--high-idle-only', action='store_true',
                        help='Keep high-idle scheduling in this process until it closes; no normal-launcher change')
    parser.add_argument('--default-priority-only', action='store_true',
                        help='Keep GLib default-priority scheduling in this process until it closes; diagnostic only')
    args = parser.parse_args()
    if sum((args.profile_strokes, args.queue_priority_trial, args.high_idle_only,
            args.default_priority_only)) > 1:
        parser.error('Run profiling and each scheduling trial separately.')
    if os.getuid() == 0 or os.environ.get('WAYLAND_DISPLAY') != 't630-gnome-0':
        raise SystemExit('Use the normal-owner tablet GNOME launcher.')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    version = subprocess.check_output(['/usr/bin/dpkg-query', '-W',
        '-f=${Version}', 'mypaint'], text=True).strip()
    if version != '2.0.1-10build2':
        raise SystemExit('This handler probe requires MyPaint 2.0.1-10build2.')
    os.environ['OMP_NUM_THREADS'] = '1'
    # If the ordinary adapter later adopts responsive scheduling, this
    # diagnostic alone owns its scheduling so a baseline stays a baseline.
    os.environ['T630_MYPAINT_QUEUE_DIAGNOSTIC'] = '1'
    sys.path.insert(0, '/usr/lib/mypaint')
    from gui.freehand import FreehandMode
    from gui.tileddrawwidget import CanvasRenderer
    from lib.gibindings import GLib
    original_priority = FreehandMode.MOTION_QUEUE_PRIORITY
    if (args.queue_priority_trial or args.high_idle_only or
            args.default_priority_only) and original_priority != GLib.PRIORITY_DEFAULT_IDLE:
        raise SystemExit('Unexpected queue priority; comparison refused.')
    if args.high_idle_only:
        FreehandMode.MOTION_QUEUE_PRIORITY = GLib.PRIORITY_HIGH_IDLE
        print(f'QUEUE_PRIORITY_HIGH_IDLE_ONLY: priority={GLib.PRIORITY_HIGH_IDLE}; '
              'active until this test process closes, normal launcher unchanged.', flush=True)
    elif args.default_priority_only:
        if (GLib.PRIORITY_DEFAULT, GLib.PRIORITY_HIGH_IDLE,
                GLib.PRIORITY_DEFAULT_IDLE) != (0, 100, 200):
            raise SystemExit('Unexpected GLib priorities; comparison refused.')
        FreehandMode.MOTION_QUEUE_PRIORITY = GLib.PRIORITY_DEFAULT
        print(f'QUEUE_PRIORITY_DEFAULT_ONLY: priority={GLib.PRIORITY_DEFAULT}; '
              'active until this test process closes, normal launcher unchanged.', flush=True)

    metrics = {key: deque(maxlen=20000) for key in
               ('pen_delivery_age_ms', 'queued_stroke_age_ms',
                'stroke_callback_ms', 'canvas_draw_callback_ms')}
    deadline = None
    originals = []
    profile = cProfile.Profile() if args.profile_strokes else None
    profile_calls = 0
    modes = weakref.WeakSet()
    phase = 'waiting-for-canvas-stroke'

    def active():
        return deadline is None or time.monotonic() < deadline

    def wrap(cls, name, before=None, duration=None):
        original = getattr(cls, name)
        @wraps(original)
        def measured(self, *args, **kwargs):
            nonlocal profile_calls
            collect = active()
            if not collect:
                return original(self, *args, **kwargs)
            if name == 'motion_notify_cb':
                modes.add(self)
            if collect and before:
                before(args)
            start = time.monotonic()
            profiling = profile is not None and deadline is not None and duration == 'stroke_callback_ms' and profile_calls < 1000
            if profiling:
                profile_calls += 1
                profile.enable()
            try:
                return original(self, *args, **kwargs)
            finally:
                if profiling:
                    profile.disable()
                if collect and duration:
                    metrics[duration].append((time.monotonic()-start)*1000)
        originals.append((cls, name, original))
        setattr(cls, name, measured)

    def delivery(args):
        event = args[1]
        device = event.get_source_device()
        if device is not None and device.get_source().value_nick in ('pen', 'eraser'):
            age = event_age_ms(event.get_time(), time.monotonic()*1000)
            if age is not None:
                metrics['pen_delivery_age_ms'].append(age)

    def queued(args):
        data = args[1]
        # Ignore nonpainting hover; never retain pressure, position, or timestamps.
        if data[3] > 0:
            stamp = data[0]
            if isinstance(stamp, (int, float)) and stamp > 0:
                age = event_age_ms(int(stamp), time.monotonic()*1000)
                if age is not None:
                    if deadline is None:
                        begin_window()
                    metrics['queued_stroke_age_ms'].append(age)

    wrap(FreehandMode, 'motion_notify_cb', before=delivery)
    wrap(FreehandMode, '_process_queued_event', before=queued,
         duration='stroke_callback_ms')
    wrap(CanvasRenderer, '_draw_cb', duration='canvas_draw_callback_ms')

    def report(final=False):
        nonlocal deadline
        print('MYPAINT_TIMING ' + ('FINAL' if final else 'LIVE') + f' phase={phase}', flush=True)
        for name, values in metrics.items():
            print(f'{name}: {describe(values)}', flush=True)
        print('Callback/event ages only; not measured pen-to-pixel latency.', flush=True)
        from gui.application import get_app
        app = get_app()
        if app is not None:
            keys = ('radius_logarithmic', 'opaque', 'slow_tracking',
                    'dabs_per_actual_radius', 'dabs_per_basic_radius', 'dabs_per_second')
            print('BRUSH_BASE_VALUES: ' + ' '.join(
                f'{key}={app.brush.get_base_value(key):.6f}' for key in keys), flush=True)
        if final:
            deadline = 0
            if args.queue_priority_trial:
                FreehandMode.MOTION_QUEUE_PRIORITY = original_priority
                count = reschedule_queues(modes, GLib, original_priority)
                print(f'QUEUE_PRIORITY_RESTORED: priority={original_priority} pending_sources={count}', flush=True)
            elif args.high_idle_only or args.default_priority_only:
                print(f'QUEUE_PRIORITY_TEST_STILL_ACTIVE: priority={FreehandMode.MOTION_QUEUE_PRIORITY}; '
                      'normal launcher unchanged.', flush=True)
            for cls, name, original in originals:
                setattr(cls, name, original)
            if profile is not None:
                import pstats
                stats = pstats.Stats(profile).stats
                print(f'STROKE_PROFILE: callbacks={profile_calls}; profiling overhead present', flush=True)
                for (filename, line, function), (primitive, calls, own, cumulative, _callers) in sorted(
                        stats.items(), key=lambda item: item[1][3], reverse=True)[:15]:
                    print(f'{os.path.basename(filename)}:{line} {function} calls={calls} '
                          f'own_seconds={own:.6f} cumulative_seconds={cumulative:.6f}', flush=True)
            return False
        return True

    def trial_phase():
        nonlocal phase
        report()
        FreehandMode.MOTION_QUEUE_PRIORITY = GLib.PRIORITY_HIGH_IDLE
        count = reschedule_queues(modes, GLib, GLib.PRIORITY_HIGH_IDLE)
        for values in metrics.values():
            values.clear()
        phase = 'high-idle-trial'
        print(f'QUEUE_PRIORITY_TRIAL: priority={GLib.PRIORITY_HIGH_IDLE} pending_sources={count}; '
              'stroke data retained, input priority unchanged', flush=True)
        return False

    def begin_window():
        nonlocal deadline, phase
        deadline = time.monotonic() + 90
        if args.high_idle_only:
            phase = 'high-idle-only'
        elif args.default_priority_only:
            phase = 'default-priority-only'
        else:
            phase = 'baseline-default-idle'
        for values in metrics.values():
            values.clear()
        GLib.timeout_add_seconds(15, lambda: report() if active() else False)
        GLib.timeout_add_seconds(90, lambda: report(final=True))
        if args.queue_priority_trial:
            GLib.timeout_add_seconds(35, trial_phase)
        print('MEASUREMENT_STARTED: first painting event; 90-second window.', flush=True)

    def waiting_timeout():
        if deadline is None:
            print('WAITING_TIMEOUT: no painting event; comparison inconclusive.', flush=True)
            report(final=True)
        return False

    GLib.timeout_add_seconds(300, waiting_timeout)
    print('T630 attended MyPaint timing: waiting for first stroke, then 90 seconds; '
          'app stays open afterward.', flush=True)
    # Do not pass this probe's diagnostic arguments to the normal app.
    sys.argv = ['/usr/local/libexec/t630-mypaint']
    runpy.run_path('/usr/local/libexec/t630-mypaint', run_name='__main__')


if __name__ == '__main__':
    main()
