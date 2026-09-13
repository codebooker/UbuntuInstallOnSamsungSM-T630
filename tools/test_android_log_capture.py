import importlib.util
import io
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ubuntu" / "t630-android-log-capture.py"
SPEC = importlib.util.spec_from_file_location("t630_android_log_capture", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class AndroidLogCaptureTests(unittest.TestCase):
    def test_binary_prefix_is_removed(self):
        record = MODULE.encode_record(b"\x00\x01CameraService\x00opened camera 0", 12.5)
        self.assertEqual(record, b"12.500 CameraService | opened camera 0\n")

    def test_empty_packet_is_ignored(self):
        self.assertEqual(MODULE.encode_record(b"\x00\x01\x02", 1.0), b"")

    def test_file_is_truncated_before_limit_is_exceeded(self):
        output = io.BytesIO(b"12345678")
        MODULE.write_bounded(output, b"abc\n", limit=10)
        self.assertEqual(output.getvalue(), b"abc\n")

    def test_file_appends_below_limit(self):
        output = io.BytesIO(b"1234")
        MODULE.write_bounded(output, b"abc\n", limit=10)
        self.assertEqual(output.getvalue(), b"1234abc\n")


if __name__ == "__main__":
    unittest.main()
