"""Read-only first-boot checks on the observed diagnostic USB serial port."""
import time
from pathlib import Path
import serial

port = '/dev/cu.usbmodemT630BRINGUP0011'
out = Path(__file__).resolve().parents[1] / 'reports' / 'first-boot-console.txt'
commands = (
    "echo __T630_BEGIN__; uname -a; id; echo PID1; "
    "cat /proc/1/comm; echo MOUNTS; cat /proc/mounts; "
    "echo BOOTLOG; cat /run/bringup.log; echo __T630_END__\n"
)
chunks = []
with serial.Serial(port, 115200, timeout=0.2, write_timeout=3) as s:
    start = time.monotonic()
    while time.monotonic() - start < 2:
        chunks.append(s.read(65536))
    s.write(commands.encode())
    s.flush()
    start = time.monotonic()
    while time.monotonic() - start < 12:
        chunks.append(s.read(65536))
        if b'\r\n__T630_END__\r\n' in b''.join(chunks):
            break
data = b''.join(chunks).decode(errors='replace')
out.write_text(data)
print(data)
