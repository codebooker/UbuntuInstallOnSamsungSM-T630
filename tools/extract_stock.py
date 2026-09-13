#!/usr/bin/env python3
"""Extract only bring-up/restore images from the user's AP archive; no device I/O."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import zipfile
import argparse

ROOT = Path(__file__).resolve().parents[1]
WANTED = {'boot.img.lz4', 'vendor_boot.img.lz4', 'recovery.img.lz4',
          'dtbo.img.lz4', 'vbmeta.img.lz4', 'vbmeta_system.img.lz4'}

def main():
    parser = argparse.ArgumentParser(
        description='Extract the SM-T630 AP images needed for build/recovery')
    parser.add_argument('archive', type=Path,
                        help='complete matching Samsung factory firmware ZIP')
    parser.add_argument('--lz4', default=shutil.which('lz4') or 'lz4',
                        help='path to the lz4 executable')
    args = parser.parse_args()
    archive = args.archive.expanduser().resolve()
    if not archive.is_file():
        parser.error(f'archive not found: {archive}')
    stock = ROOT / 'stock'
    reports = ROOT / 'reports'
    stock.mkdir(exist_ok=True)
    reports.mkdir(exist_ok=True)
    manifest = []
    with zipfile.ZipFile(archive) as z:
        ap, = [n for n in z.namelist() if n.startswith('AP_')]
        with z.open(ap) as stream, tarfile.open(fileobj=stream, mode='r|') as t:
            for member in t:
                print(f'{member.name}: {member.size} bytes', flush=True)
                if member.name not in WANTED:
                    continue
                assert member.isfile()
                target = stock / member.name
                with t.extractfile(member) as src, target.open('xb') as dst:
                    shutil.copyfileobj(src, dst)
                image = target.with_suffix('')
                subprocess.run([args.lz4, '-d', str(target), str(image)], check=True)
                manifest.append({'name': member.name, 'bytes': target.stat().st_size,
                                 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                                 'image': image.name,
                                 'image_bytes': image.stat().st_size,
                                 'image_sha256': hashlib.sha256(image.read_bytes()).hexdigest()})
    (reports / 'stock-extraction.json').write_text(json.dumps({
        'archive_name': archive.name, 'ap_member': ap, 'images': manifest}, indent=2) + '\n')
    missing = WANTED - {m['name'] for m in manifest}
    if missing:
        raise SystemExit(f'Missing expected files: {missing}')

if __name__ == '__main__':
    main()
