#!/usr/bin/env python3

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import t630_installer as subject


class T630InstallerTest(unittest.TestCase):
    def test_verify_only_uses_seal_verifier_and_never_connects(self):
        with tempfile.TemporaryDirectory() as temporary, \
                mock.patch.object(subject, "run_tool") as run:
            bundle = Path(temporary)
            subject.workflow(
                host_bundle=bundle, tablet_bundle=None, verify_only=True,
                staged=False,
                prepare=False, install=False,
                acknowledge_stock_recovery=False)
        run.assert_called_once_with(
            "finalize_installer_bundle.py", ("--verify", str(bundle)))

    def test_tablet_local_prepare_orders_stage_then_read_only_gate(self):
        with mock.patch.object(subject, "run_tool") as run:
            subject.workflow(
                host_bundle=None, tablet_bundle="/run/ubuntu/opt/t630/bundle",
                staged=False,
                verify_only=False, prepare=True, install=False,
                acknowledge_stock_recovery=False)
        self.assertEqual(run.call_args_list, [
            mock.call("stage_installer_bundle_local.py",
                      ("/run/ubuntu/opt/t630/bundle",)),
            mock.call("prepare_staged_install.py"),
        ])

    def test_install_reuses_existing_authorizer_last(self):
        with mock.patch.object(subject, "run_tool") as run:
            subject.workflow(
                host_bundle=None, tablet_bundle="/run/ubuntu/opt/t630/bundle",
                staged=False,
                verify_only=False, prepare=False, install=True,
                acknowledge_stock_recovery=True)
        self.assertEqual(run.call_args_list[-1], mock.call(
            "authorize_staged_install.py", ("--acknowledge-stock-recovery",)))
        self.assertEqual(run.call_args_list[:2], [
            mock.call("stage_installer_bundle_local.py",
                      ("/run/ubuntu/opt/t630/bundle",)),
            mock.call("prepare_staged_install.py"),
        ])

    def test_install_requires_recovery_acknowledgement(self):
        with self.assertRaisesRegex(ValueError, "requires --acknowledge"):
            subject.workflow(
                host_bundle=None, tablet_bundle="/run/ubuntu/opt/t630/bundle",
                staged=False,
                verify_only=False, prepare=False, install=True,
                acknowledge_stock_recovery=False)

    def test_host_staging_cannot_use_local_prepare_path(self):
        with self.assertRaisesRegex(ValueError, "host staging already requires"):
            subject.workflow(
                host_bundle=Path("bundle"), tablet_bundle=None,
                staged=False,
                verify_only=False, prepare=True, install=False,
                acknowledge_stock_recovery=False)

    def test_staged_continuation_can_prepare_without_recopying(self):
        with mock.patch.object(subject, "run_tool") as run:
            subject.workflow(
                host_bundle=None, tablet_bundle=None, staged=True,
                verify_only=False, prepare=True, install=False,
                acknowledge_stock_recovery=False)
        run.assert_called_once_with("prepare_staged_install.py")

    def test_source_contains_no_partition_or_format_logic(self):
        text = Path(subject.__file__).read_text()
        for forbidden in ("/dev/sda", "mkfs", "dd if=", "--apply"):
            self.assertNotIn(forbidden, text)
        self.assertIn("authorize_staged_install.py", text)

    def test_python_syntax(self):
        subprocess.run(["python3", "-m", "py_compile", subject.__file__], check=True)


if __name__ == "__main__":
    unittest.main()
