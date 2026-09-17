"""Framed command output on the already-running, owner-approved diagnostic shell."""
import base64
import glob
import re
import time
import uuid
import serial
import hashlib
import shlex
from pathlib import Path

class Link:
    def __enter__(self):
        candidates = []
        for pattern in ('/dev/cu.usbmodemT630MAINT001*',
                        '/dev/cu.usbmodemT630BRINGUP001*'):
            candidates.extend(glob.glob(pattern))
        if len(candidates) != 1:
            raise RuntimeError(f'Expected one SM-T630 serial console, found {len(candidates)}')
        self.s = serial.Serial(candidates[0], 115200,
                               timeout=0.1, write_timeout=10)
        time.sleep(0.25)
        self.s.reset_input_buffer()
        return self

    def __exit__(self, *args):
        self.s.close()

    def run(self, script, timeout=30):
        # BusyBox's interactive line editor has a smaller buffer than Linux's
        # canonical tty limit. Transfer long scripts as files instead of lines.
        if len(base64.b64encode(script.encode())) > 700:
            remote = f'/run/serial-script-{uuid.uuid4().hex[:12]}.sh'
            self.upload_ram(script.encode(), remote)
            return self.run(f'sh {shlex.quote(remote)}', timeout=timeout)
        token = uuid.uuid4().hex[:12]
        begin, end = f'BEGIN_{token}', f'END_{token}'
        encoded = base64.b64encode(script.encode()).decode()
        command = (f'echo {begin}; ( echo {encoded} | base64 -d | sh; '
                   "printf '\\nREMOTE_EXIT=%s\\n' $? ) 2>&1 | base64; "
                   f'echo {end}\n')
        if len(command) >= 1000:
            raise ValueError('Command exceeds conservative terminal input limit')
        self.s.write(command.encode())
        self.s.flush()
        buf = bytearray()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            buf.extend(self.s.read(65536))
            m = re.search(rb'\r?\n' + begin.encode() + rb'\r?\n(.*?)\r?\n' +
                          end.encode() + rb'\r?\n', buf, re.S)
            if m:
                return base64.b64decode(re.sub(rb'\s', b'', m.group(1)), validate=True).decode(errors='replace')
        raise TimeoutError(f'Serial command incomplete; last bytes: {bytes(buf[-500:])!r}')

    def upload_ram(self, data, remote):
        if not remote.startswith('/run/') or '..' in remote.split('/'):
            raise ValueError('RAM uploads must target /run without traversal')
        quoted = shlex.quote(remote)
        check = self.run(f'test ! -e {quoted}')
        if 'REMOTE_EXIT=0' not in check:
            raise ValueError(f'Refusing to overwrite {remote}')
        token = uuid.uuid4().hex[:12]
        ready, done = f'UPLOAD_READY_{token}', f'UPLOAD_DONE_{token}'
        command = (f"stty raw -echo; printf '\\n{ready}\\n'; "
                   f'timeout 90 head -c {len(data)} > {quoted}; result=$?; '
                   f"stty sane; echo UPLOAD_RC=$result; sha256sum {quoted}; "
                   f'echo {done}\n')
        self.s.write(command.encode())
        self.s.flush()
        buf = bytearray()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            buf.extend(self.s.read(65536))
            if b'\n' + ready.encode() + b'\n' in buf:
                break
        else:
            raise TimeoutError('Receiver not ready; sent no binary payload')
        start = time.monotonic()
        received = bytearray()
        for offset in range(0, len(data), 65536):
            if time.monotonic() - start > 70:
                raise TimeoutError('Upload too slow; remote receiver will time out and restore terminal')
            self.s.write(data[offset:offset + 65536])
            if self.s.in_waiting:
                received.extend(self.s.read(self.s.in_waiting))
                if done.encode() in received:
                    raise RuntimeError('Remote receiver stopped early; upload aborted')
            if offset and offset % (4 * 1024 * 1024) == 0:
                print(f'Uploaded {offset // (1024*1024)} MiB', flush=True)
        self.s.flush()
        deadline = start + 100
        while time.monotonic() < deadline:
            received.extend(self.s.read(65536))
            if b'\n' + done.encode() + b'\r\n' in received:
                break
        else:
            raise TimeoutError('No transfer completion marker')
        response = received.decode(errors='replace')
        expected = hashlib.sha256(data).hexdigest()
        if 'UPLOAD_RC=0' not in response or expected not in response:
            raise RuntimeError(f'Upload verification failed: {response}')
        print(f'{len(data)} bytes uploaded and SHA256 verified in {time.monotonic()-start:.1f}s', flush=True)
        return response

    def upload_file_ram(self, source, remote):
        """Stream one regular host file into /run without loading it into RAM."""
        source = Path(source)
        if source.is_symlink() or not source.is_file():
            raise ValueError('Host upload source must be a regular file')
        size = source.stat().st_size
        if size <= 0 or size > 4 * 1024 * 1024 * 1024:
            raise ValueError('Host upload source size is outside the 4 GiB staging limit')
        if not remote.startswith('/run/') or '..' in remote.split('/'):
            raise ValueError('RAM uploads must target /run without traversal')
        quoted = shlex.quote(remote)
        check = self.run(f'test ! -e {quoted}')
        if 'REMOTE_EXIT=0' not in check:
            raise ValueError(f'Refusing to overwrite {remote}')
        digest = hashlib.sha256()
        with source.open('rb') as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        expected = digest.hexdigest()
        timeout_seconds = min(1800, max(120, size // (1024 * 1024) * 3 + 120))
        token = uuid.uuid4().hex[:12]
        ready, done = f'UPLOAD_READY_{token}', f'UPLOAD_DONE_{token}'
        command = (f"stty raw -echo; printf '\n{ready}\n'; "
                   f'timeout {timeout_seconds} head -c {size} > {quoted}; result=$?; '
                   f"stty sane; echo UPLOAD_RC=$result; sha256sum {quoted}; "
                   f'echo {done}\n')
        self.s.write(command.encode())
        self.s.flush()
        received = bytearray()
        deadline = time.monotonic() + 10
        marker = b'\n' + ready.encode() + b'\n'
        while time.monotonic() < deadline:
            received.extend(self.s.read(65536))
            if marker in received:
                break
        else:
            raise TimeoutError('Receiver not ready; sent no file payload')
        start = time.monotonic()
        sent = 0
        next_report = 64 * 1024 * 1024
        with source.open('rb') as stream:
            while chunk := stream.read(65536):
                if time.monotonic() - start > timeout_seconds - 20:
                    raise TimeoutError('File upload too slow; receiver timeout is near')
                self.s.write(chunk)
                sent += len(chunk)
                if self.s.in_waiting:
                    received.extend(self.s.read(self.s.in_waiting))
                    if done.encode() in received:
                        raise RuntimeError('Remote receiver stopped early; upload aborted')
                if sent >= next_report:
                    print(f'Uploaded {sent // (1024*1024)} MiB', flush=True)
                    next_report += 64 * 1024 * 1024
        self.s.flush()
        deadline = start + timeout_seconds
        while time.monotonic() < deadline:
            received.extend(self.s.read(65536))
            if b'\n' + done.encode() + b'\r\n' in received:
                break
        else:
            raise TimeoutError('No file-transfer completion marker')
        response = received.decode(errors='replace')
        if sent != size or 'UPLOAD_RC=0' not in response or expected not in response:
            raise RuntimeError(f'File upload verification failed: {response}')
        print(f'{sent} bytes uploaded and SHA256 verified in '
              f'{time.monotonic()-start:.1f}s', flush=True)
        return response

    def download_ram(self, remote, target):
        """Copy an existing RAM artifact without text encoding or secret logging."""
        from pathlib import Path
        target = Path(target)
        if not remote.startswith('/run/') or '..' in remote.split('/') or target.exists():
            raise ValueError('Use an existing RAM source and a new local target')
        quoted = shlex.quote(remote)
        info = self.run(f'stat -c %s {quoted}; sha256sum {quoted}')
        lines = info.strip().splitlines()
        size, expected = int(lines[0]), lines[1].split()[0]
        token = uuid.uuid4().hex[:12]
        ready, done = f'DOWNLOAD_READY_{token}', f'DOWNLOAD_DONE_{token}'
        command = f"stty raw -echo; printf '\\n{ready}\\n'; cat {quoted}; stty sane; echo {done}\n"
        self.s.write(command.encode()); self.s.flush()
        buffer = bytearray()
        marker = b'\n' + ready.encode() + b'\n'
        deadline = time.monotonic()+10
        while marker not in buffer and time.monotonic() < deadline:
            buffer.extend(self.s.read(65536))
        if marker not in buffer: raise TimeoutError('No download start marker')
        pending = bytes(buffer).split(marker, 1)[1]
        digest = hashlib.sha256()
        received = 0
        start = time.monotonic()
        next_report = 16*1024*1024
        with target.open('xb') as out:
            while received < size:
                if time.monotonic()-start > 300: raise TimeoutError('RAM download timed out')
                chunk = pending or self.s.read(min(65536, size-received))
                pending = b''
                if len(chunk) > size-received:
                    pending = chunk[size-received:]; chunk = chunk[:size-received]
                out.write(chunk); digest.update(chunk); received += len(chunk)
                if received >= next_report:
                    print(f'Downloaded {received//(1024*1024)} MiB', flush=True)
                    next_report += 16*1024*1024
        trailer = bytearray(pending)
        deadline = time.monotonic()+5
        while done.encode() not in trailer and time.monotonic() < deadline:
            trailer.extend(self.s.read(65536))
        assert done.encode() in trailer, 'No download completion marker'
        assert digest.hexdigest() == expected, 'Downloaded SHA256 differs'
        print(f'{received} bytes downloaded and SHA256 verified in {time.monotonic()-start:.1f}s', flush=True)
        return expected

if __name__ == '__main__':
    import argparse
    from pathlib import Path
    p = argparse.ArgumentParser()
    p.add_argument('script', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--timeout', type=int, default=30)
    a = p.parse_args()
    with Link() as link:
        result = link.run(a.script.read_text(), timeout=a.timeout)
    if a.output:
        a.output.write_text(result)
    print(result)
