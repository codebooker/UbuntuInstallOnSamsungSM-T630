#!/usr/bin/env python3
"""Local-only persistent candidate. Never overwrites the diagnostic image."""
import gzip
import hashlib
import json
from pathlib import Path
import stat
import struct
import sys
from build_boot_test import newc, run, sha, ROOT, STOCK, TOOLS, PARTITION_SIZE

out = ROOT / 'output/persistent-v1'
out.mkdir(exist_ok=False)
source = ROOT / 'persistent'
stock = STOCK / 'boot.img'
assert sha(stock.read_bytes()) == '79a9b1d56763cb6e3c113473eb783f6332fe79b054e3c67494c5094c6c382796'
busybox = (STOCK / 'busybox-package/usr/bin/busybox').read_bytes()
assert busybox[:6] == b'\x7fELF\x02\x01'
assert struct.unpack_from('<H', busybox, 18)[0] == 183
# Match the actual BusyBox payload already embedded in the verified test image.
assert busybox in (ROOT / 'output/initramfs.cpio').read_bytes()
entries = [(d, stat.S_IFDIR | (0o1777 if d == 'tmp' else 0o755), b'', 0, 0)
           for d in ['bin', 'sbin', 'dev', 'proc', 'sys', 'config', 'run', 'root', 'tmp', 'etc']]
entries += [('dev/console', stat.S_IFCHR | 0o600, b'', 5, 1),
            ('dev/null', stat.S_IFCHR | 0o666, b'', 1, 3),
            ('bin/busybox', stat.S_IFREG | 0o755, busybox, 0, 0)]
for name in ['init', 'usb-shell', 'start-ubuntu', 'stop-ubuntu']:
    target = name if name == 'init' else 'bin/' + name
    entries.append((target, stat.S_IFREG | 0o755, (source / name).read_bytes(), 0, 0))
entries += [('etc/mdev.conf', stat.S_IFREG | 0o644, (ROOT / 'ubuntu/mdev.conf').read_bytes(), 0, 0),
            ('etc/passwd', stat.S_IFREG | 0o644, b'root:x:0:0:root:/root:/bin/sh\n', 0, 0),
            ('etc/group', stat.S_IFREG | 0o644, b'root:x:0:\n', 0, 0)]
cpio = newc(entries)
(out / 'initramfs.cpio').write_bytes(cpio)
ramdisk = out / 'initramfs.cpio.gz'
ramdisk.write_bytes(gzip.compress(cpio, compresslevel=9, mtime=0))
sys.path.insert(0, str(TOOLS / 'aosp-mkbootimg'))
from unpack_bootimg import unpack_bootimg
info = unpack_bootimg(str(stock), str(out / 'stock-unpacked'))
args = info.format_mkbootimg_argument()
args[args.index('--ramdisk') + 1] = str(ramdisk)
image = out / 'boot.img'
run(sys.executable, TOOLS / 'aosp-mkbootimg/mkbootimg.py', *args, '--output', image)
with image.open('ab') as stream:
    stream.write(b'SEANDROIDENFORCE')
payload_hash = sha(image.read_bytes())
assert image.stat().st_size < PARTITION_SIZE - 65536
avb = TOOLS / 'aosp-avb/avbtool.py'
run(sys.executable, avb, 'add_hash_footer', '--image', image, '--partition_name', 'boot',
    '--partition_size', PARTITION_SIZE, '--algorithm', 'NONE', '--salt', payload_hash)
parsed = unpack_bootimg(str(image), str(out / 'verified-unpacked'))
assert parsed.header_version == info.header_version == 3
assert parsed.cmdline == info.cmdline
assert parsed.os_version == info.os_version
assert parsed.os_patch_level == info.os_patch_level
assert (out / 'verified-unpacked/kernel').read_bytes() == (out / 'stock-unpacked/kernel').read_bytes()
assert (out / 'verified-unpacked/ramdisk').read_bytes() == ramdisk.read_bytes()
assert image.stat().st_size == PARTITION_SIZE
verification = run(sys.executable, avb, 'verify_image', '--image', image)
manifest = {
    'status': 'OFFLINE_VALIDATED; physical boot not yet tested',
    'model': 'SM-T630', 'build': 'T630XXSBDZE3',
    'boot_sha256': sha(image.read_bytes()), 'boot_bytes': image.stat().st_size,
    'kernel_sha256': sha((out / 'verified-unpacked/kernel').read_bytes()),
    'root_uuid': '64de8544-53ea-4fdc-8946-d6b07e238630',
    'files': {name: sha((source / name).read_bytes()) for name in ['init', 'usb-shell', 'start-ubuntu', 'stop-ubuntu']},
    'verification': verification,
    'writes': 'Builder performs local artifact writes only; no device I/O.',
}
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
