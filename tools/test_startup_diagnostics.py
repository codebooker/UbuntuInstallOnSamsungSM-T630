from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StartupDiagnosticsTests(unittest.TestCase):
    def test_mount_reference_boundary_excludes_sibling_log(self):
        script = ROOT / 'tools/show_ubuntu_mount_refs.sh'
        subprocess.run(['sh', '-n', script], check=True)
        text = script.read_text()
        self.assertIn('/run/ubuntu|/run/ubuntu/*)', text)
        self.assertNotIn('/run/ubuntu*)', text)
        self.assertNotIn('/sys/', text)
        self.assertNotIn('cat "$reference"', text)
        awk = '$2 == "/run/ubuntu" || index($2,"/run/ubuntu/") == 1 {print $2}'
        result = subprocess.run(['awk', awk], input=(
            'none /run/ubuntu ext4\nnone /run/ubuntu/run tmpfs\n'
            'none /run/ubuntu-start.log none\n'), text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.splitlines(), ['/run/ubuntu', '/run/ubuntu/run'])

    def test_wifi_probe_is_read_only_by_default_and_refuses_live_wlan(self):
        script = ROOT / 'tools/signal_wifi_filesystem_ready.sh'
        subprocess.run(['sh', '-n', script], check=True)
        text = script.read_text()
        self.assertIn('mode=${1:---check}', text)
        write = text.index('printf \'1\\n\' >"$device/fs_ready"')
        self.assertLess(text.index('if [ -d /sys/module/wlan ]'), write)
        self.assertLess(text.index('if [ "$mode" = --check ]'), write)
        self.assertIn('qcom,wlan-cbc-enabled', text)
        self.assertNotIn('> /sys/wifi/mac_addr', text)
        self.assertNotIn('/dev/sda', text)


if __name__ == '__main__':
    unittest.main()
