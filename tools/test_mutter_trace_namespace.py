from pathlib import Path
import subprocess
import unittest


class MutterTraceNamespaceTests(unittest.TestCase):
    def test_namespace_and_shared_mount_checks_precede_bind(self):
        source = Path(__file__).with_name('t630_mutter_trace_namespace.sh').read_text()
        bind = source.index('/usr/bin/mount --bind')
        for guard in ('/proc/self/ns/mnt', '/proc/1/ns/mnt', ' shared:',
                      '/etc/t630-install-id', 'T630_GPU_RENDERER',
                      'T630_MUTTER_PEN_TRACE', 'T630_PEN_METADATA_TRIAL'):
            self.assertLess(source.index(guard), bind)
        self.assertIn('/usr/bin/mount -o remount,bind,ro', source)
        self.assertIn('exec /usr/local/bin/t630-gnome-preview', source)
        self.assertNotIn('chmod', source)
        self.assertNotIn('umount', source)
        self.assertNotIn('eval ', source)
        subprocess.run(['sh', '-n'], input=source, text=True, check=True,
                       capture_output=True, timeout=5)
