"""Extract/decompress the exact stock super image locally, never touch the tablet."""
from pathlib import Path
import shutil
import subprocess
import tarfile
import zipfile
import argparse

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description='Extract the stock super image locally')
parser.add_argument('archive', type=Path)
parser.add_argument('--lz4', default=shutil.which('lz4') or 'lz4')
args = parser.parse_args()
source = args.archive.expanduser().resolve()
if not source.is_file():
    parser.error(f'archive not found: {source}')
target = root / 'stock/super.img'
target.parent.mkdir(exist_ok=True)
assert not target.exists()
with zipfile.ZipFile(source) as z:
    ap, = [n for n in z.namelist() if n.startswith('AP_')]
    with z.open(ap) as stream, tarfile.open(fileobj=stream, mode='r|') as t:
        for m in t:
            if m.name == 'super.img.lz4':
                print(f'Decompressing stock super: {m.size} compressed bytes', flush=True)
                with target.open('xb') as out:
                    p = subprocess.Popen([args.lz4, '-d', '-c'], stdin=subprocess.PIPE, stdout=out)
                    shutil.copyfileobj(t.extractfile(m), p.stdin, length=1024*1024)
                    p.stdin.close()
                    assert p.wait() == 0
                print(f'Extracted {target.stat().st_size} bytes locally', flush=True)
                break
        else:
            raise RuntimeError('No super image found')
