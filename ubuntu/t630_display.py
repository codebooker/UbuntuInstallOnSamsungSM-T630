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


class FlashlightSettings:
    """Bounded, leased control of the rear torch and its PMIC switch."""

    LEASE_SECONDS = 15
    # The kernel advertises 500 mA. Keep ordinary torch operation at or below
    # the controller's conventional 300 mA operating point.
    SAFE_MAX = 300

    def __init__(self, torch, switch):
        self.torch, self.switch = map(Path, (torch, switch))
        if self.torch.name != 'led:torch_0' or self.switch.name != 'led:switch_0':
            raise ValueError('Unexpected flashlight nodes')
        if self.torch.resolve().parent != self.switch.resolve().parent:
            raise ValueError('Flashlight current and switch are from different controllers')
        if int((self.torch / 'max_brightness').read_text()) != 500:
            raise ValueError('Unexpected torch current limit')
        if int((self.switch / 'max_brightness').read_text()) != 255:
            raise ValueError('Unexpected torch switch')
        self.percent = 20
        self.enabled = False
        self.lease_until = 0
        self.off()

    def status(self):
        return dict(available=True, enabled=self.enabled, brightness=self.percent)

    def set_brightness(self, percent):
        if type(percent) is not int or not 5 <= percent <= 100:
            raise ValueError('Flashlight brightness must be 5..100')
        self.percent = percent
        if self.enabled:
            self._write_current()
            self.renew()

    def _write_current(self):
        raw = max(1, round(self.SAFE_MAX * self.percent / 100))
        (self.torch / 'brightness').write_text(str(raw))

    def on(self):
        # The PMIC driver requires current first and the separate switch last.
        self._write_current()
        (self.switch / 'brightness').write_text('1')
        self.enabled = True
        self.renew()

    def renew(self):
        if not self.enabled:
            raise ValueError('Flashlight is off')
        self.lease_until = time.monotonic() + self.LEASE_SECONDS

    def expire(self):
        if self.enabled and time.monotonic() >= self.lease_until:
            self.off()

    def off(self):
        # Clear both controls even if our in-memory state says it is already off.
        # This repairs a prior abnormal monitor exit during the next startup.
        (self.torch / 'brightness').write_text('0')
        (self.switch / 'brightness').write_text('0')
        self.enabled = False
        self.lease_until = 0


class DisplaySettings:
    def __init__(self, light, off_state, preferences, flashlight=None):
        self.light, self.off_state, self.preferences = map(Path, (light, off_state, preferences))
        self.flashlight = flashlight
        self.maximum = int((self.light / 'max_brightness').read_text())
        if self.maximum != 306:
            raise ValueError('Unexpected backlight')
        self.idle_seconds = 300
        self.auto_suspend = False
        self.inhibit_until = 0
        self.dirty_at = None
        if self.preferences.exists():
            try:
                data = json.loads(self.preferences.read_text())
                percent, idle = data['brightness'], data['idle_seconds']
                auto_suspend = data.get('auto_suspend', False)
                self.validate(percent, idle, auto_suspend)
            except (ValueError, OSError, KeyError, TypeError):
                print('Invalid display preferences ignored; current brightness retained.', flush=True)
            else:
                self.idle_seconds = idle
                self.auto_suspend = auto_suspend
                self.set_brightness(percent, persist=False)

    @staticmethod
    def validate(percent, idle, auto_suspend=False):
        if type(percent) is not int or not 5 <= percent <= 100:
            raise ValueError('Brightness must be 5..100')
        if type(idle) is not int or idle not in IDLE_CHOICES:
            raise ValueError('Unsupported idle timeout')
        if type(auto_suspend) is not bool:
            raise ValueError('Automatic suspend must be boolean')

    def status(self):
        source = self.off_state if self.off_state.exists() else self.light / 'brightness'
        raw = int(source.read_text())
        result = dict(brightness=max(5, min(100, round(raw * 100 / self.maximum))),
                      idle_seconds=self.idle_seconds, auto_suspend=self.auto_suspend,
                      blanked=self.off_state.exists())
        result['flashlight'] = (self.flashlight.status() if self.flashlight else
                                dict(available=False, enabled=False, brightness=20))
        return result

    def set_brightness(self, percent, persist=True):
        self.validate(percent, self.idle_seconds, self.auto_suspend)
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
            self.validate(self.status()['brightness'], idle, self.auto_suspend)
            self.idle_seconds = idle
            self.dirty_at = time.monotonic()
        elif len(parts) == 2 and parts[0] == 'AUTO_SUSPEND' and parts[1] in ('ON', 'OFF'):
            self.auto_suspend = parts[1] == 'ON'
            self.dirty_at = time.monotonic()
        elif parts == ['INHIBIT']:
            # Short lease for an active full-screen app; never survives a crash.
            self.inhibit_until = time.monotonic() + 40
        elif parts == ['FLASHLIGHT', 'ON'] and self.flashlight:
            self.flashlight.on()
        elif parts == ['FLASHLIGHT', 'OFF'] and self.flashlight:
            self.flashlight.off()
        elif parts == ['FLASHLIGHT', 'RENEW'] and self.flashlight:
            self.flashlight.renew()
        elif (len(parts) == 3 and parts[:2] == ['FLASHLIGHT', 'BRIGHTNESS'] and
              self.flashlight):
            self.flashlight.set_brightness(int(parts[2]))
        else:
            raise ValueError('Unsupported display request')
        return self.status()

    def tick(self):
        if self.flashlight:
            self.flashlight.expire()

    def close(self):
        if self.flashlight:
            self.flashlight.off()

    def flush(self, force=False):
        if self.dirty_at is None or (not force and time.monotonic() - self.dirty_at < 2):
            return
        status = self.status()
        data = dict(brightness=status['brightness'], idle_seconds=self.idle_seconds,
                    auto_suspend=self.auto_suspend)
        temporary = self.preferences.with_suffix('.new')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.preferences)
        self.dirty_at = None


class ControlSocket:
    def __init__(self, settings, owner_uid, owner_gid):
        self.settings = settings
        self.owner_uid = owner_uid
        if os.path.lexists(SOCKET):
            info = os.lstat(SOCKET)
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != 0:
                raise ValueError('Unexpected control socket path')
            # Caller holds the existing single-monitor flock before this cleanup.
            os.unlink(SOCKET)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(SOCKET)
        os.chown(SOCKET, 0, owner_gid)
        os.chmod(SOCKET, 0o660)
        self.sock.listen(4)
        self.sock.setblocking(False)

    def handle(self):
        conn, _ = self.sock.accept()
        with conn:
            conn.settimeout(.2)
            try:
                _, uid, _ = struct.unpack('3i', conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                if uid not in (0, self.owner_uid):
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
