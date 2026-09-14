#!/usr/bin/env python3

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SOURCE = Path(__file__).with_name("audit_release_root.py")
SPEC = importlib.util.spec_from_file_location("audit_release_root", SOURCE)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


class ReleaseRootAuditTests(unittest.TestCase):
    def root(self):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        (root / "etc").mkdir()
        (root / "home").mkdir()
        (root / "etc/passwd").write_text(
            "root:x:0:0:root:/root:/bin/bash\n"
            "system:x:999:999:system:/nonexistent:/usr/sbin/nologin\n",
            encoding="utf-8",
        )
        (root / "etc/machine-id").write_text("", encoding="ascii")
        return directory, root

    def test_fresh_generic_root_passes(self):
        directory, root = self.root()
        try:
            self.assertEqual(audit.audit(root), [])
        finally:
            directory.cleanup()

    def test_human_account_and_home_are_rejected_without_disclosure(self):
        directory, root = self.root()
        try:
            (root / "etc/passwd").write_text(
                "root:x:0:0:root:/root:/bin/bash\nprivate-name:x:1000:1000::/home/private-name:/bin/bash\n"
            )
            (root / "home/private-name").mkdir()
            failures = audit.audit(root)
            self.assertTrue(any("human account" in item for item in failures))
            self.assertTrue(any("home directory" in item for item in failures))
            self.assertNotIn("private-name", repr(failures))
        finally:
            directory.cleanup()

    def test_network_owner_machine_and_ssh_state_are_rejected(self):
        directory, root = self.root()
        try:
            for relative in (
                "etc/t630/owner",
                "etc/NetworkManager/system-connections/private.nmconnection",
                "etc/netplan/private.yaml",
                "etc/ssh/ssh_host_ed25519_key",
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("secret", encoding="utf-8")
            (root / "etc/machine-id").write_text("device-id\n", encoding="ascii")
            failures = audit.audit(root)
            self.assertGreaterEqual(len(failures), 5)
            self.assertFalse(any("private.nmconnection" in item for item in failures))
            self.assertFalse(any("private.yaml" in item for item in failures))
        finally:
            directory.cleanup()

    def test_symlinked_secret_directory_is_rejected(self):
        directory, root = self.root()
        outside = Path(directory.name).parent / "release-audit-outside"
        outside.mkdir(exist_ok=True)
        try:
            target = root / "root/.ssh"
            target.parent.mkdir()
            target.symlink_to(outside, target_is_directory=True)
            self.assertTrue(any("credential directory" in item for item in audit.audit(root)))
        finally:
            target.unlink(missing_ok=True)
            outside.rmdir()
            directory.cleanup()


if __name__ == "__main__":
    unittest.main()
