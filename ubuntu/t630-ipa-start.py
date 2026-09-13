#!/usr/bin/env python3
"""Stage exact APNHLOS-signed IPA firmware; no partition writes or driver reloads."""
import fcntl
import hashlib
import os
from pathlib import Path
import time

HASHES = {
    'b00': '1e1e68a0273587326e85bda6be6f188c5f847e34e364010baadc7417b1ba9487',
    'b01': '47da62258942ebe5921c10cb7e2964f5730b1f68013738b50c15fc06ff85733e',
    'b02': '62c4d89ad07b00d02f71dfd4a786f44ccfb861c4956a9c6a43ef27b3f6bb1a4d',
    'b03': '14024088f436ebd24b097cb113b2177e12c939efdac0211d560c7cc498611507',
    'b04': 'c3f819a0e2a28dd74b519f9de15d182ed6e3e3f44c669f0845257f0a73c784fb',
    'mdt': 'f92680638f8702f45e7d2a183abe818a3a7f80b6ffbbe3f8563414589f30ae86',
}


def validate_files(directory):
    result = []
    for suffix, digest in HASHES.items():
        source = directory / ('yupik_ipa_fws.' + suffix)
        if source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f'Unexpected IPA firmware: {source.name}')
        result.append(source)
    return result


def main():
    if os.geteuid() != 0:
        raise RuntimeError('Root service only')
    if Path('/etc/t630-install-id').read_text().strip() != 'SM-T630-T630XXSBDZE3-Ubuntu-v1':
        raise RuntimeError('Unexpected tablet installation')
    if Path('/etc/t630/ipa.disabled').exists():
        return
    if os.uname().release != '5.4.274-qgki-31225846-abT630XXSBDZE3':
        raise RuntimeError('Unexpected kernel')
    with open('/run/t630-ipa-start.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if Path('/sys/module/firmware_class/parameters/path').read_text().strip() != '/run/input-firmware':
            raise RuntimeError('Unexpected firmware search path')
        sources = validate_files(Path('/opt/t630/ipa-firmware'))
        user_dir = Path('/run/input-firmware')
        user_dir.mkdir(mode=0o755, exist_ok=True)
        outer_dir = Path('/proc/1/root/run/input-firmware')
        if not outer_dir.is_dir():
            raise RuntimeError('Outer firmware directory unavailable')
        links = []
        for source in sources:  # Metadata last, in both caller roots.
            for directory, target in ((user_dir, str(source)),
                                      (outer_dir, '/run/ubuntu' + str(source))):
                link = directory / source.name
                if os.path.lexists(link):
                    if not link.is_symlink() or os.readlink(link) != target:
                        raise RuntimeError(f'Refusing to replace {link}')
                else:
                    links.append((link, target))
        for link, target in links:
            link.symlink_to(target)
        print('Validated APNHLOS-signed IPA firmware staged.', flush=True)
        state = Path('/sys/bus/platform/devices/soc:qcom,ipa_fws/subsys0/state')
        for _ in range(80):
            if state.read_text().strip() == 'ONLINE':
                print('IPA ONLINE; stock firmware accepted.', flush=True)
                return
            time.sleep(1)
        raise RuntimeError('IPA did not become ONLINE within 80 seconds')


if __name__ == '__main__':
    main()
