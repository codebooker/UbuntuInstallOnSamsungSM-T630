#!/usr/bin/python3
"""Create only kernel-advertised ALSA nodes in this non-devtmpfs initramfs."""
import grp
import os
from pathlib import Path
import stat

assert os.getuid() == 0
assert Path('/etc/t630-install-id').read_text().strip() == 'SM-T630-T630XXSBDZE3-Ubuntu-v1'
gid = grp.getgrnam('audio').gr_gid
for entry in Path('/sys/class/sound').iterdir():
    if not (entry / 'dev').exists():
        continue
    major, minor = map(int, (entry / 'dev').read_text().strip().split(':'))
    assert major == 116
    node = Path('/dev/snd') / entry.name
    number = os.makedev(major, minor)
    if node.exists() or node.is_symlink():
        info = node.lstat()
        assert stat.S_ISCHR(info.st_mode) and info.st_rdev == number
    else:
        os.mknod(node, stat.S_IFCHR | 0o660, number)
    os.chown(node, 0, gid)
    os.chmod(node, 0o660)
print('Kernel-advertised ALSA nodes ready; root/audio access only.')
