#!/usr/bin/env python3
"""Reproducible local-only SM-T630 stock-kernel diagnostic image builder.

Never connects to a tablet. Outputs are experimental, NOT flash-approved.
Retains the exact stock kernel, v3 header metadata and gzip ramdisk format.
Leaves vendor_boot, DTB, dtbo and recovery unchanged on the device.
"""
import gzip
import hashlib
import json
from pathlib import Path
import stat
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output'
TOOLS = ROOT / 'tools'
STOCK = ROOT / 'stock'
PARTITION_SIZE = 100663296
BUSYBOX_DEB_SHA256 = 'd96535e0402c011e0ee43449799df2f4504d44b842e4f2b3a6cbc845508eaafc'
S9_REFERENCE_COMMIT = 'bb55ceb87b61db7629c0820101ce7884ff8d987b'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def run(*args):
    return subprocess.check_output([str(a) for a in args], text=True)

def align(data, size=4):
    return data + bytes((-len(data)) % size)

def newc(entries):
    """Write Linux newc directly: no host UID/mode/device-node dependence."""
    out = bytearray()
    entries = entries + [('TRAILER!!!', 0, b'', 0, 0)]
    for ino, (name, mode, data, major, minor) in enumerate(entries, 1):
        name = name.encode() + b'\0'
        fields = [ino, mode, 0, 0, 2 if stat.S_ISDIR(mode) else 1,
                  0, len(data), 0, 0, major, minor, len(name), 0]
        header = b'070701' + ''.join(f'{n:08x}' for n in fields).encode()
        assert len(header) == 110
        out.extend(align(header + name))
        out.extend(align(data))
    return align(bytes(out), 512)

def main():
    OUT.mkdir(exist_ok=True)
    stock_boot = (STOCK / 'boot.img').read_bytes()
    assert stock_boot[:8] == b'ANDROID!'
    assert struct.unpack_from('<I', stock_boot, 40)[0] == 3
    assert len(stock_boot) == PARTITION_SIZE
    package = STOCK / 'busybox-static_1.36.1-6ubuntu3.1_arm64.deb'
    assert sha(package.read_bytes()) == BUSYBOX_DEB_SHA256
    busybox = (STOCK / 'busybox-package/usr/bin/busybox').read_bytes()
    assert busybox[:6] == b'\x7fELF\x02\x01'
    assert struct.unpack_from('<H', busybox, 18)[0] == 183  # AArch64
    phoff = struct.unpack_from('<Q', busybox, 32)[0]
    phsize, phcount = struct.unpack_from('<HH', busybox, 54)
    assert all(struct.unpack_from('<I', busybox, phoff + i * phsize)[0] != 3
               for i in range(phcount)), 'BusyBox must not need an interpreter'

    dirs = ['bin', 'sbin', 'dev', 'proc', 'sys', 'config', 'run', 'root', 'tmp', 'etc']
    entries = [(d, stat.S_IFDIR | (0o1777 if d == 'tmp' else 0o755), b'', 0, 0) for d in dirs]
    entries.extend([
        ('dev/console', stat.S_IFCHR | 0o600, b'', 5, 1),
        ('dev/null', stat.S_IFCHR | 0o666, b'', 1, 3),
        ('bin/busybox', stat.S_IFREG | 0o755, busybox, 0, 0),
        ('init', stat.S_IFREG | 0o755, (ROOT / 'initramfs/init').read_bytes(), 0, 0),
        ('bin/usb-shell', stat.S_IFREG | 0o755, (ROOT / 'initramfs/usb-shell').read_bytes(), 0, 0),
        ('etc/passwd', stat.S_IFREG | 0o644, b'root:x:0:0:root:/root:/bin/sh\n', 0, 0),
        ('etc/group', stat.S_IFREG | 0o644, b'root:x:0:\n', 0, 0),
    ])
    cpio = newc(entries)
    (OUT / 'initramfs.cpio').write_bytes(cpio)
    ramdisk = OUT / 'initramfs.cpio.gz'
    ramdisk.write_bytes(gzip.compress(cpio, compresslevel=9, mtime=0))

    sys.path.insert(0, str(TOOLS / 'aosp-mkbootimg'))
    from unpack_bootimg import unpack_bootimg
    info = unpack_bootimg(str(STOCK / 'boot.img'), str(STOCK / 'boot-unpacked'))
    args = info.format_mkbootimg_argument()
    args[args.index('--ramdisk') + 1] = str(ramdisk)
    # Explicit /init is not needed: Linux's default ramdisk entrypoint is /init.
    # Keep the stock command line and vendor ramdisk/DTB unchanged for milestone 1.
    image = OUT / 'boot-test.img'
    run(sys.executable, TOOLS / 'aosp-mkbootimg/mkbootimg.py', *args, '--output', image)
    with image.open('ab') as f:
        f.write(b'SEANDROIDENFORCE')  # Standard 16-byte marker after aligned payload.
    payload_hash = sha(image.read_bytes())
    assert image.stat().st_size < PARTITION_SIZE - 65536
    avbtool = TOOLS / 'aosp-avb/avbtool.py'
    run(sys.executable, avbtool, 'add_hash_footer', '--image', image,
        '--partition_name', 'boot', '--partition_size', PARTITION_SIZE,
        '--algorithm', 'NONE', '--salt', payload_hash)

    parsed = unpack_bootimg(str(image), str(OUT / 'verified-unpacked'))
    assert parsed.header_version == info.header_version
    assert parsed.cmdline == info.cmdline
    assert parsed.os_version == info.os_version
    assert parsed.os_patch_level == info.os_patch_level
    assert (OUT / 'verified-unpacked/kernel').read_bytes() == (STOCK / 'boot-unpacked/kernel').read_bytes()
    assert (OUT / 'verified-unpacked/ramdisk').read_bytes() == ramdisk.read_bytes()
    assert gzip.decompress(ramdisk.read_bytes()) == cpio
    assert image.stat().st_size == PARTITION_SIZE
    # avbtool resolves the descriptor's partition name as sibling boot.img.
    verify_link = OUT / 'verified-unpacked/boot.img'
    if not verify_link.is_symlink():
        assert not verify_link.exists()
        verify_link.symlink_to('../boot-test.img')
    assert verify_link.readlink() == Path('../boot-test.img')
    avb_result = run(sys.executable, avbtool, 'verify_image', '--image', verify_link)
    print(avb_result)
    vbmeta_test = OUT / 'vbmeta-test.img'
    run(sys.executable, avbtool, 'make_vbmeta_image', '--output', vbmeta_test,
        '--flags', '2', '--padding_size', 65536)
    vb = vbmeta_test.read_bytes()
    assert len(vb) == 65536 and vb[:4] == b'AVB0'
    assert struct.unpack_from('>I', vb, 120)[0] == 2
    assert struct.unpack_from('>QQ', vb, 12) == (0, 0)
    print(run(sys.executable, avbtool, 'verify_image', '--image', vbmeta_test))
    (ROOT / 'reports/boot-test-avb.txt').write_text(run(sys.executable, avbtool, 'info_image', '--image', image))
    report = {
        'status': 'OFFLINE_VALIDATED_ONLY_NOT_FLASH_APPROVED',
        'model': 'SM-T630', 'stock_build': 'T630XXSBDZE3',
        'kernel': 'Unmodified stock Samsung 5.4.274; not a mainline port',
        'userspace': 'Ubuntu-packaged BusyBox diagnostic initramfs, not Ubuntu desktop',
        'boot_header': 3, 'ramdisk_compression': 'gzip',
        'partition_bytes': PARTITION_SIZE,
        'busybox_deb_sha256': BUSYBOX_DEB_SHA256,
        'busybox_verification': 'Matched HTTPS Ubuntu Packages index SHA256; GPG chain not checked',
        's9_reference_commit': S9_REFERENCE_COMMIT,
        'mkbootimg_commit': run('git', '-C', TOOLS / 'aosp-mkbootimg', 'rev-parse', 'HEAD').strip(),
        'avbtool_commit': run('git', '-C', TOOLS / 'aosp-avb', 'rev-parse', 'HEAD').strip(),
        'files': {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
                  for p in [image, vbmeta_test, ramdisk, STOCK / 'boot.img', STOCK / 'vendor_boot.img', STOCK / 'dtbo.img', STOCK / 'vbmeta.img']},
        'not_performed_by_this_command': [
            'Any device connection, partition write, or flash',
            'Cold-boot and runtime hardware validation of this local build',
        ],
        'device_mutations': 'None; this builder never opens a device',
    }
    (ROOT / 'reports/boot-test-manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
