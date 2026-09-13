#!/usr/bin/python3
"""Restore this tablet's existing calibration into RAM; never write EFS."""
import os
from pathlib import Path
import re
import subprocess

assert os.getuid() == 0
assert 'PARTNAME=sec_efs\n' in Path('/sys/class/block/sda9/uevent').read_text()
assert subprocess.check_output(['/usr/sbin/blkid', '-p', '-s', 'TYPE', '-o', 'value', '/dev/sda9'], text=True).strip() == 'ext4'
for side in ('Left', 'Right'):
    state = subprocess.check_output(['amixer', '-c0', 'cget', f'name={side} AMP Enable Switch'], text=True)
    assert ': values=off' in state
point = Path('/run/t630-calibration-import')
point.mkdir(mode=0o700, exist_ok=True)
subprocess.run(['mount', '-t', 'ext4', '-o', 'ro,noload,nodev,nosuid,noexec', '/dev/sda9', str(point)], check=True)
values = {}
try:
    for name in ('temp_cal', 'rdc_cal', 'rdc_cal_r', 'vsc_cal', 'vsc_cal_r', 'isc_cal', 'isc_cal_r'):
        file = point / 'cirrus' / name
        assert not file.is_symlink()
        data = file.read_bytes()
        assert len(data) == 12
        text = data.rstrip(b'\0').decode('ascii')
        assert re.fullmatch(r'[0-9]+', text)
        value = int(text)
        if name.startswith('temp'):
            assert 0 < value < 100
        elif name.startswith('rdc'):
            assert 0 < value < 65536
        else:
            assert 0 < value < 2**24
        values[name] = value
finally:
    subprocess.run(['umount', str(point)], check=True)
# Stock module disassembly confirms decimal kstrtoint for these cache setters.
# These are cached factory values, not a request to run calibration.
mapping = {'temp': 'temp_cal', 'temp_r': 'temp_cal', 'rdc': 'rdc_cal',
           'rdc_r': 'rdc_cal_r', 'vsc': 'vsc_cal', 'vsc_r': 'vsc_cal_r',
           'isc': 'isc_cal', 'isc_r': 'isc_cal_r'}
for attr, filename in mapping.items():
    target = Path('/sys/class/cirrus/cirrus_cal') / attr
    target.write_text(str(values[filename]) + '\n')
    assert int(target.read_text()) == values[filename]
print('Factory speaker calibration cached and read-back verified. EFS stayed read-only.')
