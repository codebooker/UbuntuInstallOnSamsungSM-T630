#!/usr/bin/env python3
"""Build a private SM-T630 package from an owner's matching stock assets.

The output contains Samsung/Qualcomm files and must not be redistributed.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import stat
import tarfile
import tempfile

from build_first_boot_deb import ROOT, ar_member, tar_bytes


PACKAGE = "t630-stock-assets"
VERSION = "1.0.1+dze3"
BASELINE = "SM-T630 T630XXSBDZE3"

# Static, locally extracted inputs only. Mutable SSC registry/socinfo state,
# EFS speaker calibration, Bluetooth address, accounts and credentials are not
# selected by this map.
TREE_MAP = {
    "opt/t630/vendor/lib/modules": "opt/t630/vendor/lib/modules",
    "opt/t630/vendor/firmware": "opt/t630/vendor/firmware",
    "opt/t630/vendor/etc/acdbdata": "opt/t630/vendor/etc/acdbdata",
    "opt/t630/vendor/etc/audconf": "opt/t630/vendor/etc/audconf",
    "opt/t630/vendor/etc/sensors/config":
        "usr/local/share/t630/sensor-hexagonfs/sensors/config",
    "opt/t630/audio-firmware": "opt/t630/audio-firmware",
    "opt/t630/video-firmware": "opt/t630/video-firmware",
    "opt/t630/ipa-firmware": "opt/t630/ipa-firmware",
    "opt/t630/camera-firmware": "opt/t630/camera-firmware",
    "usr/local/lib/firmware/t630-bluetooth":
        "usr/local/lib/firmware/t630-bluetooth",
    "usr/local/share/t630/sensor-hexagonfs/dsp":
        "usr/local/share/t630/sensor-hexagonfs/dsp",
    "usr/local/share/t630/sensor-hexagonfs/acdb":
        "usr/local/share/t630/sensor-hexagonfs/acdb",
}
FILE_MAP = {
    "opt/t630/vendor/etc/mixer_paths.xml": "opt/t630/vendor/etc/mixer_paths.xml",
    "opt/t630/vendor/etc/sensors/sns_reg_config":
        "usr/local/share/t630/sensor-hexagonfs/sensors/sns_reg.conf",
}
EMPTY_DIRECTORIES = (
    "usr/local/share/t630/sensor-hexagonfs/sensors/registry",
    "usr/local/share/t630/sensor-hexagonfs/socinfo",
)
EXCLUDED_SOURCE_PATHS = frozenset({
    # These stock links resolve into mutable Android data/persist state rather
    # than the static vendor image. Wi-Fi works without copying either link.
    "opt/t630/vendor/firmware/wlanmdsp.otaupdate",
    "opt/t630/vendor/firmware/wlan/qca_cld/wlan_mac.bin",
})
CRITICAL_HASHES = {
    "opt/t630/vendor/lib/modules/modules.dep":
        "805b7b93de8ca2f01fb79376d809cf637a786aeed9edc170e5fb3b118fab8344",
    "opt/t630/vendor/lib/modules/qca_cld3_wlan.ko":
        "d4dc61be338e62612d5b492630894f1f1f9382c1650a7b7273f80277d88a611a",
    "opt/t630/vendor/lib/modules/machine_dlkm.ko":
        "7d8d5cb5a8e9bed57f6e7ec12e71eb03b986b7510c974d388a221fdbc4334157",
    "opt/t630/vendor/etc/mixer_paths.xml":
        "09839638d739497b077a74ef93edfce0fbfa75beb9d83cb53863b420f9be455e",
    "opt/t630/vendor/firmware/qca6490/amss.bin":
        "067dfed204498f62bc13805af7b411ce618c5991e507f979ca88f19d9717439f",
    "opt/t630/vendor/firmware/tsp_stm/fst1ba90a_gtact4pro.bin":
        "a16e5aa1165ad2f3545fd30626bec074e62a660c8e5403008ba8acbb52bb5e3a",
    "opt/t630/vendor/firmware/w9019_gtact4pro.bin":
        "59ade6b1e61ca64d73015206df0c8e189d72967e154e1456b7dd3073a51b965f",
    "usr/local/lib/firmware/t630-bluetooth/hpbtfw10.tlv":
        "602205a499b421f5f3230713795ae606b0b101f8307c1ae9ef9bc6c0b03fe9ed",
    "usr/local/lib/firmware/t630-bluetooth/hpnv10.bin":
        "84cd0fa7742fa65e788134ceda5b41d490f0bf8c9c92c7e9b301ea2f80522dd1",
    "opt/t630/audio-firmware/adsp.mdt":
        "7fb85199c8ab6a36f1f71e7b0dff89b5788db7f7fd3c0dcbde5a904739b384b6",
    "opt/t630/video-firmware/vpu20_1v.mdt":
        "f4384e0ccf227b9c9ec6ae09497b30bd16bc841390775f4a31551838ce930fd2",
    "opt/t630/ipa-firmware/yupik_ipa_fws.mdt":
        "f92680638f8702f45e7d2a183abe818a3a7f80b6ffbbe3f8563414589f30ae86",
    "opt/t630/vendor/etc/sensors/config/kodiak_default_sensors.json":
        "1efa9239b261359c4b0c32dba832af4dca7ee533e0549ba8dc12be021bd67426",
    "usr/local/share/t630/sensor-hexagonfs/dsp/adsp/libsns_device_mode_skel.so":
        "7b1c3b4ab766bc420e1a8a2bd9c86f8e27a093981c1beee26b21175ec3205b76",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def validate_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe package path: {value}")
    return path


def validate_critical(source_root: Path,
                      expected: dict[str, str] = CRITICAL_HASHES) -> None:
    for relative, wanted in expected.items():
        path = source_root / relative
        if not path.is_file() or path.is_symlink() or digest(path) != wanted:
            raise ValueError(f"wrong {BASELINE} stock input: {relative}")


def collect(source_root: Path,
            tree_map: dict[str, str] = TREE_MAP,
            file_map: dict[str, str] = FILE_MAP,
            excluded=frozenset(EXCLUDED_SOURCE_PATHS)):
    if source_root.is_symlink():
        raise ValueError("source root must be a real directory")
    source_root = source_root.resolve(strict=True)
    if not source_root.is_dir():
        raise ValueError("source root must be a real directory")
    entries: dict[str, tuple[str, Path | str, int]] = {}

    def add_file(source: Path, destination: str) -> None:
        validate_relative(destination)
        if destination in entries:
            raise ValueError(f"duplicate package path: {destination}")
        info = source.lstat()
        if stat.S_ISREG(info.st_mode):
            entries[destination] = ("file", source, stat.S_IMODE(info.st_mode))
        elif stat.S_ISLNK(info.st_mode):
            target = os.readlink(source)
            if os.path.isabs(target):
                raise ValueError(f"absolute stock symlink: {source}")
            resolved = (source.parent / target).resolve(strict=False)
            try:
                resolved.relative_to(source_root)
            except ValueError as exc:
                raise ValueError(f"escaping stock symlink: {source}") from exc
            entries[destination] = ("symlink", target, 0o777)
        else:
            raise ValueError(f"unsupported stock entry: {source}")

    for source_name, destination_name in tree_map.items():
        source = source_root / validate_relative(source_name)
        if not source.is_dir() or source.is_symlink():
            raise ValueError(f"missing or unsafe stock directory: {source_name}")
        for base, directories, files in os.walk(source, followlinks=False):
            directories.sort()
            files.sort()
            base_path = Path(base)
            relative_base = base_path.relative_to(source)
            for name in list(directories):
                child = base_path / name
                if child.is_symlink():
                    relative_source = child.relative_to(source_root).as_posix()
                    if relative_source not in excluded:
                        add_file(child, str(PurePosixPath(destination_name) /
                                            relative_base.as_posix() / name))
                    directories.remove(name)
            for name in files:
                child = base_path / name
                if child.relative_to(source_root).as_posix() not in excluded:
                    add_file(child, str(PurePosixPath(destination_name) /
                                 relative_base.as_posix() / name))
    for source_name, destination_name in file_map.items():
        add_file(source_root / validate_relative(source_name), destination_name)
    return entries


def source_manifest(entries) -> bytes:
    files = []
    for destination, (kind, source, mode) in sorted(entries.items()):
        item = {"path": destination, "kind": kind, "mode": f"{mode:04o}"}
        if kind == "file":
            item.update(bytes=source.stat().st_size, sha256=digest(source))
        else:
            item["target"] = source
        files.append(item)
    return (json.dumps({"baseline": BASELINE, "files": files},
                       sort_keys=True, indent=2) + "\n").encode()


def data_archive(entries, manifest: bytes, destination: Path, epoch: int) -> None:
    files = dict(entries)
    files["usr/share/doc/t630-stock-assets/source-manifest.json"] = (
        "bytes", manifest, 0o644)
    files["usr/share/doc/t630-stock-assets/copyright-warning"] = (
        "bytes",
        b"Locally extracted proprietary stock assets. Do not redistribute.\n",
        0o644,
    )
    directories = set(EMPTY_DIRECTORIES)
    for name in files:
        current = PurePosixPath(name).parent
        while str(current) != ".":
            directories.add(str(current))
            current = current.parent
    with tarfile.open(destination, "w:xz", format=tarfile.GNU_FORMAT,
                      preset=6) as archive:
        for name in sorted(directories):
            info = tarfile.TarInfo(f"./{name}/")
            info.type = tarfile.DIRTYPE
            info.mode = 0o755
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            info.mtime = epoch
            archive.addfile(info)
        for name, (kind, source, mode) in sorted(files.items()):
            info = tarfile.TarInfo(f"./{name}")
            info.mode = mode
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            info.mtime = epoch
            if kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = source
                archive.addfile(info)
            elif kind == "bytes":
                info.size = len(source)
                archive.addfile(info, io.BytesIO(source))
            else:
                info.size = source.stat().st_size
                with source.open("rb") as stream:
                    archive.addfile(info, stream)


def append_ar_member(output, name: str, size: int, epoch: int, stream) -> None:
    encoded = f"{name}/"
    header = (
        f"{encoded:<16}{epoch:<12}{0:<6}{0:<6}{'100644':<8}{size:<10}`\n"
    ).encode("ascii")
    output.write(header)
    while chunk := stream.read(1024 * 1024):
        output.write(chunk)
    if size % 2:
        output.write(b"\n")


def build(source_root: Path, output: Path, epoch: int,
          critical_hashes: dict[str, str] = CRITICAL_HASHES,
          tree_map: dict[str, str] = TREE_MAP,
          file_map: dict[str, str] = FILE_MAP,
          excluded=frozenset(EXCLUDED_SOURCE_PATHS)) -> str:
    if epoch < 0:
        raise ValueError("SOURCE_DATE_EPOCH must be non-negative")
    if source_root.is_symlink():
        raise ValueError("source root must be a real directory")
    source_root = source_root.resolve(strict=True)
    validate_critical(source_root, critical_hashes)
    entries = collect(source_root, tree_map, file_map, excluded)
    manifest = source_manifest(entries)
    control = f"""Package: {PACKAGE}
Version: {VERSION}
Architecture: arm64
Maintainer: local SM-T630 owner
Depends: t630-hardware-runtime (= 0.1.2)
Section: non-free/admin
Priority: optional
Description: private exact-stock assets for Samsung SM-T630 DZE3
 Locally generated package for the owner's tablet. It must not be published,
 shared, uploaded, or committed to the source repository.
""".encode()
    md5sums = "".join(
        f"{hashlib.md5(source.read_bytes(), usedforsecurity=False).hexdigest()}  {name}\n"
        for name, (kind, source, _mode) in sorted(entries.items())
        if kind == "file"
    ).encode()
    control_data = tar_bytes(
        {"control": (control, 0o644), "md5sums": (md5sums, 0o644)}, epoch)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        data_path = Path(temporary) / "data.tar.xz"
        data_archive(entries, manifest, data_path, epoch)
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as package:
            package.write(b"!<arch>\n")
            for name, contents in (("debian-binary", b"2.0\n"),
                                   ("control.tar.xz", control_data)):
                package.write(ar_member(name, contents, epoch))
            with data_path.open("rb") as stream:
                append_ar_member(package, "data.tar.xz", data_path.stat().st_size,
                                 epoch, stream)
            temporary_path = Path(package.name)
    temporary_path.chmod(0o600)
    temporary_path.replace(output)
    return digest(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path,
                        help="prepared exact-DZE3 source tree; use / only on the lab tablet")
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "output/private" / f"{PACKAGE}_{VERSION}_arm64.deb")
    parser.add_argument(
        "--source-date-epoch", type=int,
        default=int(os.environ.get("SOURCE_DATE_EPOCH", "0")))
    args = parser.parse_args()
    value = build(args.source_root, args.output.resolve(), args.source_date_epoch)
    print(f"{args.output}: SHA256 {value}")
    print("PRIVATE STOCK PACKAGE: do not redistribute or commit")


if __name__ == "__main__":
    main()
