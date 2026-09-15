#!/usr/bin/python3
"""Opt-in, owner-only SSH and authenticated loopback screen viewing.

Run on the personalized tablet as root with a public ED25519 key file. No
passwords/private keys are accepted or carried in the repository/release image.
"""
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, '/usr/local/share/t630')


def make_config(username):
    if not re.fullmatch(r'[a-z_][a-z0-9_-]{0,31}', username):
        raise ValueError('Invalid installed owner.')
    return f'''Port 22
ListenAddress 0.0.0.0
HostKey /etc/ssh/ssh_host_t630_ed25519_key
PidFile /run/t630-sshd.pid
AuthorizedKeysFile /etc/t630/remote_authorized_keys
AllowUsers {username}
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
UsePAM yes
StrictModes yes
AllowAgentForwarding no
X11Forwarding no
AllowTcpForwarding local
PermitOpen 127.0.0.1:8765
GatewayPorts no
PermitTunnel no
AllowStreamLocalForwarding no
MaxAuthTries 3
LoginGraceTime 30
Subsystem sftp internal-sftp
'''


def validate_public_key(text):
    # Exactly one ordinary ED25519 public key, no authorized_keys options.
    line = text.strip()
    if not re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/]+={0,2}(?: [^\r\n]*)?', line):
        raise ValueError('Expected one ED25519 public key, never a private key.')
    return line + '\n'


def main():
    from t630_account import resolve_owner
    if os.getuid() != 0 or len(sys.argv) != 2:
        raise SystemExit('Usage (tablet root): install-remote-access.py PUBLIC_KEY_FILE')
    if Path('/etc/t630-install-id').read_text().strip() != 'SM-T630-T630XXSBDZE3-Ubuntu-v1':
        raise SystemExit('Not the configured SM-T630 installation.')
    owner = resolve_owner()
    source = Path(__file__).resolve().parent
    key = Path(sys.argv[1])
    if key.is_symlink() or not key.is_file() or key.stat().st_size > 8192:
        raise SystemExit('Unsafe public key file.')
    public = validate_public_key(key.read_text())
    subprocess.run(['/usr/bin/ssh-keygen', '-lf', str(key)], check=True,
                   stdout=subprocess.DEVNULL)
    destinations = {
        '/etc/t630/remote_authorized_keys': (public.encode(), 0o644),
        '/etc/ssh/sshd_config_t630': (make_config(owner.username).encode(), 0o600),
        '/usr/local/libexec/t630-screen': ((source / 't630_screen.py').read_bytes(), 0o755),
        '/usr/local/sbin/t630-remote-start': ((source / 't630-remote-start').read_bytes(), 0o755),
        '/usr/local/share/t630/stop-ubuntu': ((source / 'stop-ubuntu-remote').read_bytes(), 0o755),
        '/etc/NetworkManager/dispatcher.d/90-t630-remote': ((source / '90-t630-remote').read_bytes(), 0o755),
    }
    # Refuse configuration replacement: opt-in must not silently change keys,
    # access policy, or another administrator's existing remote setup.
    for name in destinations:
        path = Path(name)
        if path.exists() or path.is_symlink():
            raise SystemExit('Remote destination already exists; inspect it before changing access.')
        if any(parent.is_symlink() for parent in path.parents):
            raise SystemExit('Refusing symlinked remote destination.')
    host_key = Path('/etc/ssh/ssh_host_t630_ed25519_key')
    if host_key.exists() or host_key.is_symlink() or Path(str(host_key) + '.pub').exists():
        raise SystemExit('Dedicated host key already exists; preserve and inspect it.')
    host_key.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['/usr/bin/ssh-keygen', '-q', '-t', 'ed25519', '-N', '',
                    '-f', str(host_key)], check=True)
    for name, (content, mode) in destinations.items():
        path = Path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
    subprocess.run(['/usr/local/sbin/t630-remote-start'], check=True)
    print('Owner-only SSH and loopback screen service enabled. Pin the new host key over USB before SSH.')


if __name__ == '__main__':
    main()
