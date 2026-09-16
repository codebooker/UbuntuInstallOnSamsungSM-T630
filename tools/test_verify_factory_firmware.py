import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

import verify_factory_firmware as subject


def member_name(role: str) -> str:
    names = {
        "BL": "BL_T630XXSBDZE3_T630XXSBDZE3_TEST.tar.md5",
        "AP": "AP_T630XXSBDZE3_T630XXSBDZE3_TEST.tar.md5",
        "HOME_CSC": "HOME_CSC_XAR_T630XARBDZE3_TEST.tar.md5",
        "CSC": "CSC_XAR_T630XARBDZE3_TEST.tar.md5",
    }
    return names[role]


def payload(name: str, good: bool = True) -> bytes:
    body = b"x" * (1024 * 1024 + 1)
    value = hashlib.md5(body, usedforsecurity=False).hexdigest()
    if not good:
        value = "0" * 32
    return body + value.encode() + b"  " + name.removesuffix(".md5").encode() + b"\n"


class FactoryFirmwareTests(unittest.TestCase):
    def make(self, root: Path, good: bool = True) -> Path:
        result = root / "factory.zip"
        with zipfile.ZipFile(result, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for role in subject.ROLES:
                name = member_name(role)
                archive.writestr(name, payload(name, good))
        return result

    def test_structure_and_deep_md5_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = self.make(Path(temporary))
            shallow = subject.validate(archive)
            self.assertEqual(shallow["status"], "RECOVERY_ARCHIVE_STRUCTURE_VALID_ONLY")
            deep = subject.validate(archive, deep=True)
            self.assertEqual(deep["status"], "RECOVERY_ARCHIVE_DEEP_VERIFIED")
            self.assertTrue(all(item["deep_verified"] for item in deep["members"]))

    def test_bad_appended_md5_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = self.make(Path(temporary), good=False)
            with self.assertRaisesRegex(ValueError, "payload MD5 mismatch"):
                subject.validate(archive, deep=True)

    def test_missing_role_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "factory.zip"
            with zipfile.ZipFile(archive, "w") as output:
                for role in subject.ROLES[:-1]:
                    name = member_name(role)
                    output.writestr(name, payload(name))
            with self.assertRaisesRegex(ValueError, "missing factory roles"):
                subject.validate(archive)

    def test_nested_member_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "factory.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("nested/" + member_name("BL"), payload(member_name("BL")))
            with self.assertRaisesRegex(ValueError, "unsafe or nested"):
                subject.validate(archive)


if __name__ == "__main__":
    unittest.main()
