#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


SOURCE = Path(__file__).with_name("build_recovery_bcb.py")
SPEC = importlib.util.spec_from_file_location("build_recovery_bcb", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RecoveryBcbTest(unittest.TestCase):
    def test_preflight_message_is_standard_2048_byte_layout(self):
        message = MODULE.build_preflight_message()
        self.assertEqual(len(message), 2048)
        self.assertEqual(message[:32].split(b"\0", 1)[0], b"boot-recovery")
        recovery = message[64:832].split(b"\0", 1)[0]
        self.assertEqual(
            recovery,
            b"recovery\n--reason=t630_dualboot_recovery_preflight\n--locale=en-US\n",
        )
        self.assertEqual(message[832:], bytes(1216))

    def test_preflight_message_cannot_wipe(self):
        message = MODULE.build_preflight_message().lower()
        self.assertNotIn(b"wipe", message)
        self.assertNotIn(b"format", message)

    def test_wipe_data_message_is_explicit_and_standard(self):
        message = MODULE.build_wipe_data_message()
        self.assertEqual(len(message), 2048)
        self.assertEqual(message[:32].split(b"\0", 1)[0], b"boot-recovery")
        recovery = message[64:832].split(b"\0", 1)[0]
        self.assertEqual(
            recovery,
            b"recovery\n"
            b"--wipe_data\n"
            b"--reason=t630_dualboot_native_android_initialization\n"
            b"--locale=en-US\n",
        )
        self.assertEqual(recovery.count(b"--wipe_data\n"), 1)
        self.assertEqual(message[832:], bytes(1216))

    def test_field_rejects_overflow_and_nul(self):
        with self.assertRaises(ValueError):
            MODULE.field("x" * 32, 32)
        with self.assertRaises(ValueError):
            MODULE.field("bad\0value", 32)

    def test_cli_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bcb.bin"
            output.write_bytes(b"keep")
            old_argv = sys.argv
            sys.argv = [str(SOURCE), "--output", str(output)]
            try:
                with self.assertRaises(SystemExit):
                    MODULE.main()
            finally:
                sys.argv = old_argv
            self.assertEqual(output.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()
