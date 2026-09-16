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

    def test_v9_writer_refuses_the_abi_incompatible_image(self):
        writer = source.with_name('write_waydroid_kernel_boot_v9.sh')
        subprocess.run(['sh', '-n', writer], check=True)
        text = writer.read_text()
        result = subprocess.run([writer, '--write'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('REFUSED', result.stderr)
        self.assertIn('module ABI', result.stderr)
        self.assertNotIn('/dev/sda19', text)
        self.assertNotIn('\ndd ', text)

    def test_wifi_safe_writer_pins_rollback_target_and_neighbors(self):
        writer = source.with_name('write_wifi_safe_checksum_boot_v10.sh')
        subprocess.run(['sh', '-n', writer], check=True)
        text = writer.read_text()
        self.assertIn('old_hash=57b5d0c8a1ef76f46ea0c6c039d30a2f13e7b3743c5c7d1a72eb5f4eb10a993b', text)
        self.assertIn('new_hash=5394a2347dd4ed660af02e7197c48a38b91c6912a6a0667b4cd002dc16c21b61', text)
        self.assertIn('PARTNAME=boot', text)
        self.assertIn('dd if="$image" of=/dev/sda19', text)
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
        self.assertIn(',19}-*.patch', text)

    def test_container_pivot_patch_preserves_initial_namespace_lock(self):
        patch = source.parents[1] / 'patches/0019-allow-pivot-root-in-isolated-mount-namespaces.patch'
        text = patch.read_text()
        self.assertIn('CONFIG_KDP_NS', text)
        self.assertIn('current->nsproxy->mnt_ns == init_task.nsproxy->mnt_ns', text)
        self.assertIn('MNT_LOCKED', text)

    def test_boot_builder_can_bind_a_coherent_module_manifest(self):
        builder = source.with_name('build_boot_with_kernel.py').read_text()
        self.assertIn('--module-manifest', builder)
        self.assertIn('module_payload_manifest_sha256', builder)
        self.assertIn('module_symvers_sha256', builder)
        self.assertIn('coherent_module_count', builder)
        self.assertIn('--source-boot', builder)
        self.assertIn('release-boot-v12-charger-guard/boot.img', builder)
        self.assertIn('a7bde8259ab09b8238e0a1c8871e94422c3a6eb29e95ff8218e2de1746cd2e28', builder)

    def test_module_stager_is_guarded_and_keeps_rollback(self):
        stager = source.with_name('stage_waydroid_kernel_modules.sh')
        subprocess.run(['bash', '-n', stager], check=True)
        text = stager.read_text()
        self.assertIn('test "$current" = /opt/t630/vendor/lib/modules', text)
        self.assertIn('test "$(uname -r)" = "$release"', text)
        self.assertIn('modinfo -F vermagic', text)
        self.assertIn('modules-v8', text)
        self.assertIn('mode=${3:-check}', text)

    def test_wlan_builder_pins_release_and_avoids_stale_vmlinux(self):
        builder = source.with_name('build_waydroid_wlan.sh')
        subprocess.run(['bash', '-n', builder], check=True)
        text = builder.read_text()
        self.assertIn('4e15799e1f443577a9a102bc0c9564259e502b03', text)
        self.assertIn('0904701ee8ae065bbc920c7d5a2a11c0c645ebaa', text)
        self.assertIn('2b58351f875928929af63aa548fa0b84f3050587', text)
        self.assertIn('git.codelinaro.org', text)
        self.assertIn('.t630-wlan-vmlinux', text)
        self.assertIn('audit_kernel_module_abi.py', text)
        self.assertIn('CONFIG_QCA_CLD_WLAN=m', text)
        self.assertIn('--strip-debug', text)
        self.assertIn('qca_cld3_wlan.ko', text)

    def test_v10_trial_stager_pairs_modules_and_boot_with_rollback(self):
        stager = source.with_name('stage_waydroid_kernel_trial_v10.sh')
        subprocess.run(['sh', '-n', stager], check=True)
        text = stager.read_text()
        self.assertIn('mode=${1:---check}', text)
        self.assertIn('modules-stock-v12', text)
        self.assertIn('boot-v12.rollback.img', text)
        self.assertIn('current_backed_up=0', text)
        self.assertIn('candidate_activated=0', text)
        self.assertIn('rollback()', text)
        self.assertIn('dd if="$rollback_image" of=/dev/sda19', text)
        self.assertIn('dd if="$image" of=/dev/sda19', text)
        self.assertIn('cmp "$candidate/manifest.json"', text)
        self.assertIn('WAYDROID_KERNEL_V10_TRIAL_READY_NO_CHANGES', text)

    def test_v13_trial_stager_changes_only_boot_and_keeps_v12_rollback(self):
        stager = source.with_name('stage_waydroid_kernel_trial_v13.sh')
        subprocess.run(['sh', '-n', stager], check=True)
        text = stager.read_text()
        self.assertIn('mode=${1:---check}', text)
        self.assertIn('boot-v12.transaction-rollback.img', text)
        self.assertIn('boot-v12.stable-rollback.img', text)
        self.assertIn('current_modules=/opt/t630/vendor/lib/modules', text)
        self.assertIn('d574e39844665e55a85549ea829ec20715ff29223786a4c4b8386b2486f24889', text)
        self.assertIn('dd if="$image" of=/dev/sda19', text)
        self.assertIn('dd if="$transaction_rollback" of=/dev/sda19', text)
        self.assertNotIn('mv "$current_modules"', text)
        self.assertIn('WAYDROID_KERNEL_V13_TRIAL_READY_NO_CHANGES', text)


if __name__ == '__main__':
    unittest.main()
