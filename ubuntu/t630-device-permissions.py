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
known_sources = {base, source_text}
for optional_rule in ('fuse 0:0 666\n', 'video3[23] 0:994 660\n',
                      '(dri/)?renderD128 0:994 660\n'):
    known_sources.update(text.replace(optional_rule, '')
                         for text in tuple(known_sources))
assert target.read_text() in known_sources, 'Unknown mdev configuration; preserving it.'
subprocess.run(['install', '-m', '644', str(source), str(target)], check=True)
conventional_nodes = {
    'null': (1, 3),
    'zero': (1, 5),
    'full': (1, 7),
    'random': (1, 8),
    'urandom': (1, 9),
    'tty': (5, 0),
    'ptmx': (5, 2),
    'fuse': (10, 229),
}
for name, device_number in conventional_nodes.items():
    node = Path('/dev') / name
    info = node.stat(follow_symlinks=False)
    assert stat.S_ISCHR(info.st_mode) and not node.is_symlink()
    assert (os.major(info.st_rdev), os.minor(info.st_rdev)) == device_number
    os.chown(node, 0, 0)
    os.chmod(node, 0o666)
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
render = Path('/dev/dri/renderD128')
render_stat = render.stat(follow_symlinks=False)
assert stat.S_ISCHR(render_stat.st_mode) and not render.is_symlink()
assert (os.major(render_stat.st_rdev), os.minor(render_stat.st_rdev)) == (226, 128)
assert (Path('/sys/class/drm/renderD128/device/driver').resolve() ==
        Path('/sys/bus/platform/drivers/msm_drm'))
os.chown(render, 0, 994)
os.chmod(render, 0o660)

# A later mdev scan also resets the already-created ALSA nodes. Repair only
# kernel-advertised major-116 devices; this is the same invariant enforced by
# t630-sound-nodes.py, but must happen immediately after arbitrary rescans.
sound_class = Path('/sys/class/sound')
if sound_class.is_dir():
    for entry in sound_class.iterdir():
        dev = entry / 'dev'
        if not dev.is_file():
            continue
        major, minor = map(int, dev.read_text().strip().split(':'))
        assert major == 116
        node = Path('/dev/snd') / entry.name
        number = os.makedev(major, minor)
        if node.exists() or node.is_symlink():
            info = node.lstat()
            assert stat.S_ISCHR(info.st_mode) and info.st_rdev == number
        else:
            os.mknod(node, stat.S_IFCHR | 0o660, number)
        os.chown(node, 0, 29)
        os.chmod(node, 0o660)
print('Validated mdev audio/render permission rules installed.')
