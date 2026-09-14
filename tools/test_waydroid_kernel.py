#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import subprocess
import unittest

source = Path(__file__).with_name('check_waydroid_kernel.py')
spec = importlib.util.spec_from_file_location('waydroid_kernel', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WaydroidKernelTests(unittest.TestCase):
    def test_complete_config_passes(self):
        text = '\n'.join(f'{key}=y' for key in module.REQUIRED)
        self.assertEqual(module.check(text), [])

    def test_disabled_and_missing_features_fail(self):
        available = module.REQUIRED - {'CONFIG_PID_NS', 'CONFIG_IPC_NS'}
        text = '\n'.join(f'{key}=y' for key in available)
        text += '\n# CONFIG_PID_NS is not set\n'
        self.assertEqual(module.check(text), ['CONFIG_IPC_NS', 'CONFIG_PID_NS'])

    def test_module_is_accepted(self):
        text = '\n'.join(f'{key}=m' for key in module.REQUIRED)
        self.assertEqual(module.check(text), [])

    def test_v9_writer_pins_source_target_and_protected_partitions(self):
        writer = source.with_name('write_waydroid_kernel_boot_v9.sh')
        subprocess.run(['sh', '-n', writer], check=True)
        text = writer.read_text()
        self.assertIn('old_hash=2bfa801e391476fb9e4f597d31846fc2113b8c0c761130caa4a7fef4dec1876a', text)
        self.assertIn('new_hash=57b5d0c8a1ef76f46ea0c6c039d30a2f13e7b3743c5c7d1a72eb5f4eb10a993b', text)
        for partition in ('/dev/sda20', '/dev/sda21', '/dev/sda22', '/dev/sde19'):
            self.assertIn(partition, text)

    def test_builder_produces_matching_kernel_and_modules(self):
        builder = source.with_name('build_waydroid_kernel.sh')
        subprocess.run(['bash', '-n', builder], check=True)
        text = builder.read_text()
        self.assertIn('Image modules', text)
        self.assertIn('-Wno-error=incompatible-pointer-types', text)
        self.assertIn('-Wno-error)', text)
        self.assertIn("-name '*.ko'", text)
        self.assertIn('case-sensitive Linux filesystem', text)
        self.assertIn('xt_MARK.h', text)
        self.assertIn('xt_mark.h', text)

    def test_module_stager_is_guarded_and_keeps_rollback(self):
        stager = source.with_name('stage_waydroid_kernel_modules.sh')
        subprocess.run(['bash', '-n', stager], check=True)
        text = stager.read_text()
        self.assertIn('test "$current" = /opt/t630/vendor/lib/modules', text)
        self.assertIn('test "$(uname -r)" = "$release"', text)
        self.assertIn('modinfo -F vermagic', text)
        self.assertIn('modules-v8', text)
        self.assertIn('mode=${3:-check}', text)


if __name__ == '__main__':
    unittest.main()
