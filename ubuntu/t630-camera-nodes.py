#!/usr/bin/python3
"""Create only kernel-advertised SM-T630 camera and media device nodes."""
import os
from pathlib import Path
import re
import stat


assert os.getuid() == 0
assert Path('/etc/t630-install-id').read_text().strip() == 'SM-T630-T630XXSBDZE3-Ubuntu-v1'
assert os.uname().release == '5.4.274-qgki-31225846-abT630XXSBDZE3'

expected_video = {'video0', 'video1'}
expected_subdev = {f'v4l-subdev{index}' for index in range(17)}
expected_media = {'media0', 'media1'}


def ensure_node(name, major, minor):
    assert name in expected_video | expected_subdev | expected_media
    node = Path('/dev') / name
    number = os.makedev(major, minor)
    if node.exists() or node.is_symlink():
        info = node.lstat()
        assert stat.S_ISCHR(info.st_mode) and info.st_rdev == number
    else:
        os.mknod(node, stat.S_IFCHR | 0o660, number)
    os.chown(node, 0, 0)
    os.chmod(node, 0o660)


found_video = set()
found_subdev = set()
for entry in Path('/sys/class/video4linux').iterdir():
    name = entry.name
    if name in ('video32', 'video33'):
        continue  # Hardware codec ownership belongs to the render policy.
    assert re.fullmatch(r'(?:video|v4l-subdev)[0-9]+', name)
    major, minor = map(int, (entry / 'dev').read_text().strip().split(':'))
    assert major == 81
    ensure_node(name, major, minor)
    (found_video if name.startswith('video') else found_subdev).add(name)

found_media = set()
for entry in Path('/sys/dev/char').glob('245:*'):
    values = dict(line.split('=', 1) for line in (entry / 'uevent').read_text().splitlines()
                  if '=' in line)
    name = values.get('DEVNAME', '')
    assert name in expected_media
    major, minor = map(int, entry.name.split(':'))
    ensure_node(name, major, minor)
    found_media.add(name)

assert found_video == expected_video
assert found_subdev == expected_subdev
assert found_media == expected_media
print('Kernel-advertised SM-T630 camera/media nodes ready; root access only.')
