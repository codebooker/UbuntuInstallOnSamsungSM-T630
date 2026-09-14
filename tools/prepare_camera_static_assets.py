#!/usr/bin/env python3
"""Reconstruct static private camera assets from exact mounted DZE3 stock."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile


APEXES = {
    "runtime/apex_payload.img": (
        "apex/com.android.runtime.apex",
        "60dcde8e281759b388f54c94619b735801b09488aba2f6516aabcde145bdbba9",
        "933852072eda61c000f1e0f34570c92f420e02ad765735685645c73bab561f9a"),
    "i18n/apex_payload.img": (
        "apex/com.android.i18n.apex",
        "9a2cd2855249acb6cbdd49e818c38ad7b6f927bdb9536c6c578918e06eaa96ed",
        "1a81d87cf37e8767ab1cc996d2e955f4f2657261ac7ffabc52df8c3bbac53c61"),
    "vndk30/apex_payload.img": (
        "system_ext/apex/com.android.vndk.v30.apex",
        "189ea2aab862412c0a19e1af811542d8d4051980560cd0c53c6733bcf39e79f5",
        "cbf2391730c65de571ec48b6e30bba2099d6f09576613628cc4359453a0ce36b"),
}
VENDOR_APEXES = {
    "camera/apex_payload.img": (
        "apex/com.samsung.android.camera.unihal.signed.apex",
        "5e49f94d2fa4bc81ec63ae1bc3561bc0bde57772b3b3b27e8b8a4c8cb1baf80e",
        "ccc35ded4ac562dcd2b4dbfe0d3aadad36feb25660d1977ae6b53d8be9fb124f"),
}
PATCHES = {
    "system/cameraserver": (
        "bin/cameraserver",
        "834766618646efa697b67c3ba14c9170f0c946c51a8e796017ac2bd30681671e",
        "5429480613566f22182d5ba99ea3af35d3b586fa290a88e5c895dcf6eee70202",
        ((885840, 0xA0, 0xED), (885841, 0x1D, 0x00), (885843, 0x36, 0x14),
         (1242908, 0x20, 0x1F), (1242909, 0x0F, 0x20),
         (1242910, 0x00, 0x03), (1242911, 0x36, 0xD5))),
}
VENDOR_PATCHES = {
    "vendor/com.qti.chi.override.so": (
        "lib64/hw/com.qti.chi.override.so",
        "00d4da91710edda0794848c1937fcf2051078765a7eb8aecf744de400f616c57",
        "cdcb884968c7522bc9005615bee732d4b0265bde70f2828b0b7f31c35097b524",
        ((212494, 0x2F, 0x32), (2659828, 0x57, 0x1F),
         (2659829, 0x7C, 0x20), (2659830, 0x0A, 0x03),
         (2659831, 0x94, 0xD5))),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_file(root: Path, relative: str, wanted: str) -> bytes:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or unsafe stock input: {relative}")
    data = path.read_bytes()
    if sha(data) != wanted:
        raise ValueError(f"wrong DZE3 stock input: {relative}")
    return data


def patched(data: bytes, changes, wanted: str) -> bytes:
    result = bytearray(data)
    for offset, before, after in changes:
        if offset >= len(result) or result[offset] != before:
            raise ValueError(f"patch preimage mismatch at {offset}")
        result[offset] = after
    output = bytes(result)
    if sha(output) != wanted:
        raise ValueError("patched output checksum mismatch")
    return output


def prepare(system: Path, vendor: Path, output: Path) -> dict:
    if system.is_symlink() or vendor.is_symlink():
        raise ValueError("stock roots must be real directories")
    system = system.resolve(strict=True)
    vendor = vendor.resolve(strict=True)
    if not system.is_dir() or not vendor.is_dir():
        raise ValueError("stock roots must be real directories")
    if output.exists() or output.is_symlink():
        raise ValueError("output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    records = []
    try:
        for mapping, root in ((APEXES, system), (VENDOR_APEXES, vendor)):
            for destination, (source, source_hash, payload_hash) in mapping.items():
                archive_data = checked_file(root, source, source_hash)
                with zipfile.ZipFile(io.BytesIO(archive_data)) as archive:
                    payload = archive.read("apex_payload.img")
                if sha(payload) != payload_hash:
                    raise ValueError(f"wrong APEX payload: {source}")
                target = temporary / destination
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                target.chmod(0o600)
                records.append({"path": destination, "sha256": payload_hash,
                                "bytes": len(payload)})
        for mapping, root in ((PATCHES, system), (VENDOR_PATCHES, vendor)):
            for destination, (source, source_hash, output_hash, changes) in mapping.items():
                data = patched(checked_file(root, source, source_hash), changes, output_hash)
                target = temporary / destination
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                target.chmod(0o700)
                records.append({"path": destination, "sha256": output_hash,
                                "bytes": len(data), "changed_bytes": len(changes)})
        manifest = {"baseline": "SM-T630 T630XXSBDZE3", "files": records}
        (temporary / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (temporary / "manifest.json").chmod(0o600)
        os.replace(temporary, output)
        return manifest
    except Exception:
        shutil.rmtree(temporary)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("system_root", type=Path)
    parser.add_argument("vendor_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = prepare(args.system_root, args.vendor_root, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
