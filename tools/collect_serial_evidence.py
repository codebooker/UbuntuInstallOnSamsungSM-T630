"""Copy finite read-only evidence from the diagnostic root shell to this Mac."""
import base64
import re
import time
from pathlib import Path
import serial

ROOT = Path(__file__).resolve().parents[1]
jobs = {
    'native-boot-summary.txt': (
        'uname -a; id; echo CMDLINE; cat /proc/cmdline; '
        'echo PID1; tr "\\000" " " </proc/1/cmdline; echo; '
        'echo PARTITIONS; cat /proc/partitions; '
        'echo DISPLAY; ls -l /sys/class/graphics /sys/class/drm; '
        'echo INPUT; cat /proc/bus/input/devices; '
        'echo BOOTLOG; cat /run/bringup.log; echo UPTIME; cat /proc/uptime'
    ),
    'native-boot-dmesg.txt': 'dmesg',
    'native-boot-fdt.dtb': 'cat /sys/firmware/fdt',
}

with serial.Serial('/dev/cu.usbmodemT630BRINGUP0011', 115200,
                   timeout=0.2, write_timeout=3) as s:
    time.sleep(0.5)
    s.reset_input_buffer()
    for index, (filename, command) in enumerate(jobs.items()):
        begin, end = f'T630_B64_BEGIN_{index}', f'T630_B64_END_{index}'
        line = f'echo {begin}; ( {command} ) 2>&1 | base64; echo {end}\n'
        s.write(line.encode())
        s.flush()
        received = bytearray()
        start = time.monotonic()
        complete = None
        while time.monotonic() - start < 45:
            received.extend(s.read(65536))
            # Require stand-alone markers; ignore the terminal's command echo.
            complete = re.search(rb'(?:\r?\n)' + begin.encode() +
                                 rb'\r?\n(.*?)\r?\n' + end.encode() + rb'\r?\n',
                                 received, re.S)
            if complete:
                break
        if not complete:
            raise RuntimeError(f'Timed out collecting {filename}; no file written')
        payload = re.sub(rb'\s', b'', complete.group(1))
        try:
            data = base64.b64decode(payload, validate=True)
        except ValueError:
            (ROOT / 'reports' / (filename + '.serial.txt')).write_bytes(received)
            print('Unexpected lines:', [line for line in complete.group(1).splitlines()
                  if not re.fullmatch(rb'[A-Za-z0-9+/=]*', line)])
            raise
        target = ROOT / 'reports' / filename
        target.write_bytes(data)
        print(f'{filename}: {len(data)} bytes', flush=True)
