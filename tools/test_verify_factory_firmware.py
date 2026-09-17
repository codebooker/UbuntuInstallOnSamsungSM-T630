import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
from typing import Optional
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


def inner_payload(
        role: str, *, omit: Optional[str] = None, symlink: Optional[str] = None
) -> bytes:
    name = member_name(role)
    output = io.BytesIO()
    regular = [item for item in sorted(subject.EXPECTED_INNER[role])
               if item != "meta-data"]
    large = regular[-1]
    with tarfile.open(fileobj=output, mode="w") as archive:
        for item in sorted(subject.EXPECTED_INNER[role]):
            if item == omit:
                continue
            info = tarfile.TarInfo(item)
            info.mtime = 0
            if item == "meta-data":
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                archive.addfile(info)
            elif item == symlink:
                info.type = tarfile.SYMTYPE
                info.linkname = "elsewhere"
                archive.addfile(info)
            else:
                body = b"x" * (1024 * 1024 + 1 if item == large else 1)
                info.size = len(body)
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(body))
    body = output.getvalue()
    value = hashlib.md5(body, usedforsecurity=False).hexdigest()
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

    def test_exact_inner_inventory_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "factory.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
                for role in subject.ROLES:
                    output.writestr(member_name(role), inner_payload(role))
            result = subject.validate(archive, deep=True, inventory=True)
            self.assertEqual(result["status"], "RECOVERY_ARCHIVE_CONTENTS_VERIFIED")
            for record in result["members"]:
                self.assertEqual(
                    {item["name"] for item in record["inner_members"]},
                    subject.EXPECTED_INNER[record["role"]],
                )

    def test_inventory_requires_deep_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = self.make(Path(temporary))
            with self.assertRaisesRegex(ValueError, "requires deep"):
                subject.validate(archive, inventory=True)

    def test_missing_inner_partition_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "factory.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
                for role in subject.ROLES:
                    omit = "boot.img.lz4" if role == "AP" else None
                    output.writestr(member_name(role), inner_payload(role, omit=omit))
            with self.assertRaisesRegex(ValueError, "missing inner AP members: boot.img.lz4"):
                subject.validate(archive, deep=True, inventory=True)

    def test_inner_symlink_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "factory.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
                for role in subject.ROLES:
                    symlink = "boot.img.lz4" if role == "AP" else None
                    output.writestr(member_name(role), inner_payload(role, symlink=symlink))
            with self.assertRaisesRegex(ValueError, "unsafe inner tar type in AP"):
                subject.validate(archive, deep=True, inventory=True)


if __name__ == "__main__":
    unittest.main()
