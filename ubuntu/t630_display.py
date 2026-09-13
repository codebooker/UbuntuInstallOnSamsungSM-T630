"""Narrow local display controls shared by the Power monitor, not a shell API."""
import json
import os
from pathlib import Path
import socket
import stat
import struct
import time

SOCKET = '/run/t630-display.sock'
IDLE_CHOICES = (0, 120, 300, 600, 1800)


class DisplaySettings:
    def __init__(self, light, off_state, preferences):
        self.light, self.off_state, self.preferences = map(Path, (light, off_state, preferences))
        self.maximum = int((self.light / 'max_brightness').read_text())
        if self.maximum != 306:
            raise ValueError('Unexpected backlight')
        self.idle_seconds = 300
        self.inhibit_until = 0
        self.dirty_at = None
        if self.preferences.exists():
            try:
                data = json.loads(self.preferences.read_text())
                percent, idle = data['brightness'], data['idle_seconds']
                self.validate(percent, idle)
            except (ValueError, OSError, KeyError, TypeError):
                print('Invalid display preferences ignored; current brightness retained.', flush=True)
            else:
                self.idle_seconds = idle
                self.set_brightness(percent, persist=False)

    @staticmethod
    def validate(percent, idle):
        if type(percent) is not int or not 5 <= percent <= 100:
            raise ValueError('Brightness must be 5..100')
        if type(idle) is not int or idle not in IDLE_CHOICES:
            raise ValueError('Unsupported idle timeout')

    def status(self):
        source = self.off_state if self.off_state.exists() else self.light / 'brightness'
        raw = int(source.read_text())
        return dict(brightness=max(5, min(100, round(raw * 100 / self.maximum))),
                    idle_seconds=self.idle_seconds, blanked=self.off_state.exists())

    def set_brightness(self, percent, persist=True):
        self.validate(percent, self.idle_seconds)
        raw = round(self.maximum * percent / 100)
        # While blanked, change the restore value without lighting the panel.
        target = self.off_state if self.off_state.exists() else self.light / 'brightness'
        target.write_text(str(raw))
        if persist:
            self.dirty_at = time.monotonic()

    def request(self, text):
        parts = text.strip().split()
        if parts == ['STATUS']:
            pass
        elif len(parts) == 2 and parts[0] == 'BRIGHTNESS':
            self.set_brightness(int(parts[1]))
        elif len(parts) == 2 and parts[0] == 'IDLE':
            idle = int(parts[1])
            self.validate(self.status()['brightness'], idle)
            self.idle_seconds = idle
            self.dirty_at = time.monotonic()
        elif parts == ['INHIBIT']:
            # Short lease for an active full-screen app; never survives a crash.
            self.inhibit_until = time.monotonic() + 40
        else:
            raise ValueError('Unsupported display request')
        return self.status()

    def flush(self, force=False):
        if self.dirty_at is None or (not force and time.monotonic() - self.dirty_at < 2):
            return
        data = self.status()
        data.pop('blanked')
        temporary = self.preferences.with_suffix('.new')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.preferences)
        self.dirty_at = None


class ControlSocket:
    def __init__(self, settings):
        self.settings = settings
        if os.path.lexists(SOCKET):
            info = os.lstat(SOCKET)
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != 0:
                raise ValueError('Unexpected control socket path')
            # Caller holds the existing single-monitor flock before this cleanup.
            os.unlink(SOCKET)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(SOCKET)
        os.chown(SOCKET, 0, 1000)
        os.chmod(SOCKET, 0o660)
        self.sock.listen(4)
        self.sock.setblocking(False)

    def handle(self):
        conn, _ = self.sock.accept()
        with conn:
            conn.settimeout(.2)
            try:
                _, uid, _ = struct.unpack('3i', conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                if uid not in (0, 1000):
                    raise ValueError('Unauthorized local user')
                data = bytearray()
                while not data.endswith(b'\n') and len(data) <= 64:
                    chunk = conn.recv(65 - len(data))
                    if not chunk:
                        raise ValueError('Incomplete request')
                    data.extend(chunk)
                if len(data) > 64:
                    raise ValueError('Request too long')
                result = self.settings.request(data.decode('ascii'))
                conn.sendall((json.dumps(result) + '\n').encode())
            except (ValueError, OSError, UnicodeError):
                try:
                    conn.sendall(b'{"error":"Display request rejected"}\n')
                except OSError:
                    pass

    def close(self):
        self.sock.close()
        os.unlink(SOCKET)
