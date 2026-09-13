#!/usr/bin/env python3
"""Local tests use only child Python processes, never the tablet desktop."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest import mock
import importlib.machinery

source = Path(__file__).resolve().parents[1] / 'ubuntu/t630-gpu-session-watch.py'
if not source.exists():
    source = Path('/usr/local/libexec/t630-gpu-session-watch')
loader = importlib.machinery.SourceFileLoader('watch', str(source))
spec = importlib.util.spec_from_loader(loader.name, loader)
watch = importlib.util.module_from_spec(spec)
loader.exec_module(watch)


class WatchTests(unittest.TestCase):
    def test_ready_child_exit(self):
        result = watch.supervise([sys.executable, '-c', 'import time; time.sleep(.3)'],
                                 ready=lambda pid: True, startup_timeout=1)
        self.assertEqual(result, 0)

    def test_exit_before_ready_is_failure(self):
        result = watch.supervise([sys.executable, '-c', 'pass'],
                                 ready=lambda pid: False, startup_timeout=1)
        self.assertEqual(result, 1)

    def test_hung_startup_is_bounded(self):
        started = time.monotonic()
        result = watch.supervise(
            [sys.executable, '-c',
             'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)'],
            ready=lambda pid: False, startup_timeout=.5, stop_grace=.2)
        self.assertEqual(result, 1)
        self.assertLess(time.monotonic() - started, 3)

    def test_unrelated_child_is_untouched(self):
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            watch.supervise([sys.executable, '-c', 'import time; time.sleep(30)'],
                            ready=lambda pid: False, startup_timeout=.1, stop_grace=.2)
            self.assertIsNone(unrelated.poll())
        finally:
            unrelated.terminate()
            unrelated.wait(timeout=3)

    def test_later_hang_is_bounded(self):
        started = time.monotonic()
        ready = mock.Mock(side_effect=[True, False, False, False])
        result = watch.supervise(
            [sys.executable, '-c',
             'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)'],
            ready=ready, startup_timeout=1, stop_grace=.2,
            health_interval=.01, health_failures=3)
        self.assertEqual(result, 1)
        self.assertEqual(ready.call_count, 4)
        self.assertLess(time.monotonic() - started, 3)

    def test_transient_failure_does_not_restart_session(self):
        ready = mock.Mock(side_effect=[True, False, True, False, True, True, True, True])
        result = watch.supervise([sys.executable, '-c', 'import time; time.sleep(1.4)'],
                                 ready=ready, startup_timeout=1,
                                 health_interval=.01, health_failures=2)
        self.assertEqual(result, 0)
        self.assertGreaterEqual(ready.call_count, 5)


if __name__ == '__main__':
    unittest.main()
