#!/usr/bin/python3
"""Verify audio-active detection with a short silent stream, never amplifier changes."""
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import time
import wave

assert os.getuid() == 1000
power = runpy.run_path('/usr/local/sbin/t630-power-button')
with tempfile.TemporaryDirectory(prefix='t630-idle-audio-', dir=os.environ['XDG_RUNTIME_DIR']) as folder:
    path = Path(folder) / 'silence.wav'
    with wave.open(str(path), 'wb') as wav:
        wav.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
        wav.writeframes(bytes(48000 * 4 * 8))
    child = subprocess.Popen(['paplay', str(path)])
    try:
        time.sleep(.5)
        assert child.poll() is None, 'Test stream exited early'
        assert power['audio_playing'](), 'Active audio was not detected'
        print('Silent playing stream correctly inhibits idle screen-off.')
    finally:
        if child.poll() is None:
            child.terminate()
        child.wait(timeout=3)
