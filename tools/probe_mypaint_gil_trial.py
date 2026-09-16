#!/usr/bin/python3
"""Load only the reviewed RAM GIL-fix extension for a bounded headless probe.

Lab artifact hashes, not an installer/default or general binary loader.
No installed package replacement, live-app changes, GUI/input, or documents.
"""
import argparse
import hashlib
import os
from pathlib import Path
import runpy
import resource
import signal
import stat
import subprocess
import sys

EXPECTED = {
    '_mypaintlib.cpython-312-aarch64-linux-gnu.so':
        '969627187a15ae4f9128944b24f55a730ca95e2d914e2ece604676bb3d5482c4',
    'mypaintlib.py': 'd154b514ccf4ef84becff8676bb73f47888b2533feb083078651f454d3046be7',
}


def validate(directory):
    if directory.is_symlink() or directory.parent != Path('/run') or not directory.name.startswith('t630-mypaint-gil-trial-'):
        raise ValueError('Use the explicitly staged root-owned RAM trial directory.')
    info = directory.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError('Unexpected trial directory ownership/mode.')
    for name, expected in EXPECTED.items():
        path = directory / name
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022 or info.st_size > 32*2**20:
            raise ValueError('Unexpected trial artifact ownership/mode/size.')
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Unreviewed trial artifact hash.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library-dir', type=Path, required=True)
    parser.add_argument('--threads', choices=(1, 4), type=int, required=True)
    args = parser.parse_args()
    if os.getuid() == 0:
        raise SystemExit('Run through the normal-owner helper; never a root application.')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    signal.alarm(25)
    version = subprocess.check_output(['/usr/bin/dpkg-query', '-W', '-f=${Version}',
                                       'mypaint'], text=True).strip()
    if version != '2.0.1-10build2':
        raise SystemExit('The trial requires the exact matching installed MyPaint package.')
    validate(args.library_dir)
    os.environ['OMP_NUM_THREADS'] = str(args.threads)
    sys.path.insert(0, '/usr/lib/mypaint')
    import lib
    lib.__path__.insert(0, str(args.library_dir))
    from lib import mypaintlib
    if Path(mypaintlib.__file__).parent != args.library_dir:
        raise SystemExit('Trial Python binding did not load; no render test performed.')
    from lib import _mypaintlib
    if Path(_mypaintlib.__file__).parent != args.library_dir:
        raise SystemExit('Trial extension did not load; no render test performed.')
    print('Reviewed private MyPaint GIL-fix extension loaded; installed files unchanged.', flush=True)
    probe = Path(__file__).with_name('probe_mypaint_strokes.py')
    sys.argv = [str(probe), '--threads', str(args.threads), '--brush',
                'classic/impressionism', '--full-canvas']
    runpy.run_path(str(probe), run_name='__main__')


if __name__ == '__main__':
    main()
