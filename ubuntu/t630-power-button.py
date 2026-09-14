#!/usr/bin/python3
"""SM-T630 short Power: verified GNOME lock then backlight off; wake never unlocks.

Reads only qpnp_pon, never grabs input, never reads touchscreen/keyboard events.
No network listener, password handling or shutdown operation. Opt-in suspend
is delegated to a separate guarded helper only after a manual Power blank.
"""
import argparse
import ctypes
import fcntl
import json
import os
from pathlib import Path
import select
import re
import signal
import struct
import subprocess
import sys
import time

sys.path.insert(0, '/usr/local/lib/t630')
from t630_display import DisplaySettings, ControlSocket, FlashlightSettings
sys.path.insert(0, '/usr/local/share/t630')
from t630_account import resolve_owner

RUN = '/usr/local/bin/t630-gnome-run'
LIGHT = Path('/sys/class/backlight/panel0-backlight')
STATE = Path('/run/t630-display-off-brightness')
TORCH = Path('/sys/class/leds/led:torch_0')
TORCH_SWITCH = Path('/sys/class/leds/led:switch_0')
EVENT = struct.Struct('@llHHi')


def command(args):
    return subprocess.check_output(args, text=True, timeout=8,
                                   stderr=subprocess.DEVNULL).strip()


def screen(method):
    return command([RUN, 'gdbus', 'call', '--session', '--dest',
                    'org.gnome.ScreenSaver', '--object-path',
                    '/org/gnome/ScreenSaver', '--method',
                    'org.gnome.ScreenSaver.' + method])


def locked_hint():
    # The normal-user helper joins the shell's real session cgroup, so self
    # resolves to that exact elogind session, not this root input monitor.
    return command([RUN, 'gdbus', 'call', '--system', '--dest',
                    'org.freedesktop.login1', '--object-path',
                    '/org/freedesktop/login1/session/self', '--method',
                    'org.freedesktop.DBus.Properties.Get',
                    'org.freedesktop.login1.Session', 'LockedHint']) == '(<true>,)'


def restore():
    if not STATE.exists():
        return
    value = int(STATE.read_text().strip())
    maximum = int((LIGHT / 'max_brightness').read_text())
    if not 0 < value <= maximum:
        raise RuntimeError('Invalid saved brightness; refusing arbitrary value')
    (LIGHT / 'brightness').write_text(str(value))
    STATE.unlink()
    print('Display backlight restored; authentication unchanged.', flush=True)


def lock_and_blank():
    if screen('GetActive') != '(true,)':
        screen('Lock')
    if screen('GetActive') != '(true,)' or not locked_hint():
        raise RuntimeError('Password lock not verified; leaving display on')
    value = int((LIGHT / 'brightness').read_text())
    if value <= 0:
        raise RuntimeError('Display already dark without our state; leaving unchanged')
    fd = os.open(STATE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as saved:
        saved.write(str(value))
    (LIGHT / 'brightness').write_text('0')
    print('Password lock verified; display backlight off.', flush=True)


def idle_time():
    result = command([RUN, 'gdbus', 'call', '--session', '--dest',
                      'org.gnome.Mutter.IdleMonitor', '--object-path',
                      '/org/gnome/Mutter/IdleMonitor/Core', '--method',
                      'org.gnome.Mutter.IdleMonitor.GetIdletime'])
    match = re.fullmatch(r'\(uint64 ([0-9]+),\)', result)
    if not match:
        raise ValueError('Unknown idle response')
    return int(match.group(1))


def audio_playing():
    # Inspect only stream state, never log application/media metadata.
    streams = json.loads(command([RUN, 'pactl', '-f', 'json', 'list', 'sink-inputs']))
    return any(stream.get('corked') is False for stream in streams)


def suspend_result():
    helper = Path('/usr/local/sbin/t630-suspend')
    if not helper.exists() or not Path('/etc/t630/suspend.enabled').exists():
        return {'slept': False, 'reason': 'policy disabled'}
    result = json.loads(subprocess.check_output([str(helper)], text=True, timeout=350))
    print('Suspend: ' + json.dumps(result), flush=True)
    return result


def manual_suspend():
    result = suspend_result()
    return result.get('slept') is True and result.get('power_wake') is True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--test-cycle', action='store_true')
    args = parser.parse_args()
    assert os.getuid() == 0
    assert Path('/etc/t630-install-id').read_text().strip() == 'SM-T630-T630XXSBDZE3-Ubuntu-v1'
    owner = resolve_owner()
    candidates = [p for p in Path('/sys/class/input').glob('event*')
                  if (p / 'device/name').read_text().strip() == 'qpnp_pon']
    assert len(candidates) == 1
    assert int((LIGHT / 'max_brightness').read_text()) == 306
    if args.check:
        print('Validated tablet, qpnp_pon input, and panel0 backlight; no changes.')
        return
    ctypes.CDLL(None).prctl(15, b't630-power-key', 0, 0, 0)
    with open('/run/t630-power-button.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        restore()  # Repair a previous abnormal monitor exit while blanked.
        try:
            flashlight = FlashlightSettings(TORCH, TORCH_SWITCH)
        except (OSError, ValueError) as exc:
            flashlight = None
            print(f'Flashlight unavailable: {type(exc).__name__}', flush=True)
        settings = DisplaySettings(LIGHT, STATE, '/var/lib/t630/display-settings.json',
                                   flashlight)
        def stop(_signal, _frame):
            raise SystemExit(0)
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        try:
            if args.test_cycle:
                lock_and_blank()
                time.sleep(3)
                return
            fd = os.open('/dev/input/' + candidates[0].name, os.O_RDONLY | os.O_NONBLOCK)
            control = ControlSocket(settings, owner.uid, owner.gid)
            pressed_at = None
            last_action = -1.0
            next_idle_check = time.monotonic() + 60
            previous_idle = None
            auto_suspend_at = None
            print('Power-key monitor ready; long presses and repeats ignored.', flush=True)
            try:
                while True:
                    ready = select.select([fd, control.sock], [], [], 1)[0]
                    if control.sock in ready:
                        control.handle()
                    settings.tick()
                    settings.flush()
                    now = time.monotonic()
                    if not settings.auto_suspend or not STATE.exists():
                        auto_suspend_at = None
                    elif auto_suspend_at is None:
                        # Let the lock animation, initiating input, and any last
                        # application work settle before entering system sleep.
                        auto_suspend_at = now + 15
                    elif now >= auto_suspend_at:
                        try:
                            result = suspend_result()
                            if result.get('slept') is True and result.get('power_wake') is True:
                                restore()
                                command([RUN, 'env', 'DISPLAY=:3', 'xdotool',
                                         'key', 'Shift_L'])
                                # Power events queue while rtcwake owns this
                                # thread. Consume the handled press and release.
                                for _ in range(32):
                                    try:
                                        if not os.read(fd, EVENT.size * 32):
                                            break
                                    except BlockingIOError:
                                        break
                                pressed_at = None
                                last_action = time.monotonic()
                                previous_idle = None
                                next_idle_check = last_action + 3
                                auto_suspend_at = None
                            elif result.get('slept') is True:
                                # The lab RTC safety alarm woke a still-idle,
                                # locked tablet. Return to sleep after settling.
                                auto_suspend_at = time.monotonic() + 15
                            else:
                                # Charging, USB, audio, or another temporary
                                # readiness guard: retry quietly after a minute.
                                auto_suspend_at = time.monotonic() + 60
                        except Exception as exc:
                            print(f'Automatic suspend not completed: {type(exc).__name__}',
                                  flush=True)
                            auto_suspend_at = time.monotonic() + 60
                    if now >= next_idle_check:
                        next_idle_check = now + (2 if STATE.exists() else 5)
                        try:
                            current_idle = idle_time()
                            if STATE.exists():
                                if previous_idle is not None and current_idle + 500 < previous_idle:
                                    restore()  # Activity wakes the light, never unlocks.
                                    auto_suspend_at = None
                            elif (settings.idle_seconds and
                                  current_idle >= settings.idle_seconds * 1000 and
                                  now >= settings.inhibit_until and not audio_playing()):
                                lock_and_blank()
                                if settings.auto_suspend:
                                    auto_suspend_at = time.monotonic() + 15
                                current_idle = None  # Lock animation is not a user wake event.
                            previous_idle = current_idle
                        except Exception:
                            # Missing/unresponsive session/audio info must not blank the screen.
                            previous_idle = None
                    if fd not in ready:
                        continue
                    data = os.read(fd, EVENT.size * 32)
                    if not data:
                        raise RuntimeError('Power input disconnected')
                    for offset in range(0, len(data), EVENT.size):
                        _, _, kind, code, value = EVENT.unpack_from(data, offset)
                        if kind != 1 or code != 116:
                            continue
                        now = time.monotonic()
                        if value == 1:
                            pressed_at = now
                        elif value == 0 and pressed_at is not None:
                            duration = now - pressed_at
                            pressed_at = None
                            if duration > 1.5 or now - last_action < .5:
                                continue
                            last_action = now
                            previous_idle = None
                            next_idle_check = now + 3
                            try:
                                if STATE.exists():
                                    # A modifier-only event also wakes any GNOME
                                    # idle shade, without submitting/typing text.
                                    restore()
                                    auto_suspend_at = None
                                    command([RUN, 'env', 'DISPLAY=:3', 'xdotool',
                                             'key', 'Shift_L'])
                                else:
                                    lock_and_blank()
                                    if manual_suspend():
                                        # The wake press is already accounted for;
                                        # do not interpret its queued release as
                                        # another request to blank/suspend again.
                                        restore()
                                        command([RUN, 'env', 'DISPLAY=:3', 'xdotool',
                                                 'key', 'Shift_L'])
                                        for _ in range(32):
                                            try:
                                                if not os.read(fd, EVENT.size * 32):
                                                    break
                                            except BlockingIOError:
                                                break
                                        pressed_at = None
                                        last_action = time.monotonic()
                                        previous_idle = None
                                        next_idle_check = last_action + 3
                                        auto_suspend_at = None
                                    elif settings.auto_suspend and STATE.exists():
                                        auto_suspend_at = time.monotonic() + 15
                            except Exception as exc:
                                restore()
                                print(f'Power action not completed: {type(exc).__name__}', flush=True)
            finally:
                settings.flush(force=True)
                try:
                    settings.close()
                finally:
                    control.close()
                os.close(fd)
        finally:
            restore()


if __name__ == '__main__':
    main()
