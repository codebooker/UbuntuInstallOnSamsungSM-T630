#!/usr/bin/python3
"""Preserve validated audio/render permissions across the late Wi-Fi mdev scan."""
import grp
import fcntl
import os
from pathlib import Path
import subprocess
import stat

assert os.getuid() == 0
lock = open('/run/t630-device-permissions.lock', 'a')
fcntl.flock(lock, fcntl.LOCK_EX)
assert grp.getgrnam('audio').gr_gid == 29
assert grp.getgrnam('render').gr_gid == 994
base = ''.join(name + ' 0:0 666\n' for name in ['null', 'zero', 'full', 'random', 'urandom', 'tty', 'ptmx'])
source = Path('/usr/local/share/t630/mdev.conf')
target = Path('/proc/1/root/etc/mdev.conf')
assert not target.is_symlink()
source_text = source.read_text()
previous_source = source_text.replace('video3[23] 0:994 660\n', '')
assert target.read_text() in (base, previous_source, source_text), 'Unknown mdev configuration; preserving it.'
subprocess.run(['install', '-m', '644', str(source), str(target)], check=True)
for name in ('kgsl-3d0', 'ion'):
    node = Path('/dev') / name
    assert node.is_char_device() and not node.is_symlink()
    os.chown(node, 0, 994)
    os.chmod(node, 0o660)
video_nodes = {
    'video32': (81, 0),
    'video33': (81, 1),
}
for name, device_number in video_nodes.items():
    node = Path('/dev') / name
    device_stat = node.stat(follow_symlinks=False)
    assert stat.S_ISCHR(device_stat.st_mode) and not node.is_symlink()
    assert (os.major(device_stat.st_rdev), os.minor(device_stat.st_rdev)) == device_number
    driver = (Path('/sys/class/video4linux') / name / 'device/driver').resolve()
    assert driver == Path('/sys/bus/platform/drivers/msm_vidc_v4l2')
    os.chown(node, 0, 994)
    os.chmod(node, 0o660)
print('Validated mdev audio/render permission rules installed.')
