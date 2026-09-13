"""Verify Ubuntu's detached signature against its documented full fingerprint."""
import hashlib
from pathlib import Path
import pgpy

root = Path(__file__).resolve().parents[1] / 'ubuntu'
key, _ = pgpy.PGPKey.from_file(str(root / 'ubuntu-cdimage-key.asc'))
assert str(key.fingerprint) == '843938DF228D22F7B3742BC0D94AA3F0EFE21092'
signature = pgpy.PGPSignature.from_file(str(root / 'SHA256SUMS.gpg'))
checksums = (root / 'SHA256SUMS').read_bytes()
assert key.verify(checksums, signature), 'Ubuntu checksum signature invalid'
name = 'ubuntu-base-24.04.5-base-arm64.tar.gz'
expected, = [line.split()[0] for line in checksums.decode().splitlines()
             if line.split()[1].lstrip('*') == name]
actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
assert actual == expected
print(f'Valid Ubuntu CD Image signature, key {key.fingerprint}')
print(f'{name}: SHA256 verified {actual}')
