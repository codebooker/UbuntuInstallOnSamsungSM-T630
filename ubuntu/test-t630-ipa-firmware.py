#!/usr/bin/env python3
"""Expose only validated stock IPA files briefly; never unload or flash devices."""
import hashlib
import os
import pathlib
import struct
import subprocess
import sys
import time

assert os.geteuid() == 0
assert pathlib.Path('/etc/t630-install-id').read_text().strip() == 'SM-T630-T630XXSBDZE3-Ubuntu-v1'
assert subprocess.check_output(['uname', '-r'], text=True).strip() == '5.4.274-qgki-31225846-abT630XXSBDZE3'
assert pathlib.Path('/sys/module/firmware_class/parameters/path').read_text().strip() == '/run/input-firmware'
vendor = pathlib.Path('/opt/t630/vendor/firmware')
assert sys.argv[1:] in ([], ['--apnhlos'])
signed = sys.argv[1:] == ['--apnhlos']
src = pathlib.Path('/run/t630-apnhlos-stock/image') if signed else vendor
if signed:
    mounts = pathlib.Path('/proc/mounts').read_text().splitlines()
    assert any(line.split()[:3] == ['/dev/sda23', '/run/t630-apnhlos-stock', 'vfat']
               and 'ro' in line.split()[3].split(',') for line in mounts)
dest = pathlib.Path('/proc/1/root/run/input-firmware')
stem = 'yupik_ipa_fws'
blob = (vendor / (stem + '.elf')).read_bytes()
assert hashlib.sha256(blob).hexdigest() == '3f3833c2cfba37fc5276f2fbcbd70793f858237231d1117b368f77c3d85a6aa0'
mdt = (src / (stem + '.mdt')).read_bytes()
assert hashlib.sha256(mdt).hexdigest() == (
    'f92680638f8702f45e7d2a183abe818a3a7f80b6ffbbe3f8563414589f30ae86' if signed else
    '30b84e0259e3b893f8227cd24c334f63863b75ab628ef34d6b56aa9e852d9e53')
assert blob[:4] == b'\x7fELF' and blob[4:6] == b'\x01\x01'
assert struct.unpack_from('<I', blob, 28)[0] == 52
assert struct.unpack_from('<HH', blob, 42) == (32, 5)
for i in range(5):
    typ, off, virt, phys, fsz, msz, flags, align = struct.unpack_from('<8I', blob, 52 + i * 32)
    segment = (src / f'{stem}.b{i:02}').read_bytes()
    if signed and i == 1:
        assert hashlib.sha256(segment).hexdigest() == '47da62258942ebe5921c10cb7e2964f5730b1f68013738b50c15fc06ff85733e'
    else:
        assert segment == blob[off:off + fsz]
    if typ == 1:
        assert flags & (1 << 27) and phys + msz <= 0xa000
        assert fsz <= msz
assert mdt == (src / (stem + '.b00')).read_bytes() + (src / (stem + '.b01')).read_bytes()
node = pathlib.Path('/sys/bus/platform/devices/soc:qcom,ipa_fws/of_node')
assert (node / 'qcom,pas-id').read_bytes() == struct.pack('>I', 15)
assert (node / 'memory-region').read_bytes() == struct.pack('>I', 0xc8)
region = pathlib.Path('/sys/firmware/devicetree/base/reserved-memory/ipa_gsi@8b710000')
assert (region / 'reg').read_bytes() == struct.pack('>4I', 0, 0x8b710000, 0, 0xa000)
state = pathlib.Path('/sys/bus/platform/devices/soc:qcom,ipa_fws/subsys0/state')
original_state = state.read_text().strip()
assert original_state == 'OFFLINING'  # Observed state during repeated missing-file failures.
created = []
print('Stock file and reserved-memory checks passed.', flush=True)
try:
    # Metadata becomes visible last, after all the segment files are ready.
    for suffix in ['b00', 'b01', 'b02', 'b03', 'b04', 'mdt']:
        link = dest / (stem + '.' + suffix)
        target = '/run/ubuntu' + str(src / link.name)
        assert not os.path.lexists(link)
        link.symlink_to(target)
        created.append((link, target))
    for _ in range(40):
        status = state.read_text().strip()
        if status != original_state:
            print('Subsystem state:', status, flush=True)
            break
        time.sleep(0.1)
    print('Final subsystem state:', state.read_text().strip(), flush=True)
finally:
    for link, target in reversed(created):
        if link.is_symlink() and os.readlink(link) == target:
            link.unlink()
    print('Temporary firmware links removed; original files unchanged.', flush=True)
