#!/usr/bin/python3
"""Bounded, -40 dBFS stereo test through the stock protected speaker route."""
import math
from pathlib import Path
import struct
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

root = ET.parse('/opt/t630/vendor/etc/mixer_paths.xml').getroot()
assert sys.argv[1:] in ([], ['--s16'])
bits = 16 if sys.argv[1:] else 24
paths = {p.attrib['name']: p for p in root.findall('path')}
spk = {c.attrib['name']: c.attrib['value'] for c in paths['spk'].findall('ctl')}
def get(name):
    return subprocess.check_output(['amixer', '-c0', 'cget', 'name=' + name], text=True)
def put(name, value):
    subprocess.run(['amixer', '-c0', 'cset', 'name=' + name, value], check=True,
                   stdout=subprocess.DEVNULL)
for side, expected in [('Left', 9156), ('Right', 9108)]:
    assert ': values=off' in get(side + ' AMP Enable Switch')
    assert ': values=on' in get(side + ' BBPE Enable Switch')
    assert ': values=9' in get(side + ' DSP1 Firmware')
    raw = get(side + ' DSP1 Protection cd CAL_R').split(': values=')[1].strip()
    assert int.from_bytes(bytes(int(b, 16) for b in raw.split(',')), 'big') == expected
    # Keep the already-existing stock speaker gains unchanged.
    assert ': values=3' in get(side + ' AMP PCM Gain')
    assert ': values=817' in get(side + ' Digital PCM Volume')
tone = Path('/run/t630-quiet-speaker-test.raw')
old_stream_volume = get('Playback 0 Volume').split(': values=')[1].splitlines()[0].strip()
assert old_stream_volume.isdigit()
with tone.open('wb') as audio:
    for i in range(48000 * 6):
        t = i / 48000
        part = t % 3
        envelope = max(0, min(1, part / .05, (2.0 - part) / .05))
        sample = round((2**(bits - 1) - 1) * 10**(-40/20) * envelope * math.sin(2*math.pi*440*t))
        pair = (sample, 0) if t < 3 else (0, sample)
        audio.write(struct.pack('<hh' if bits == 16 else '<ii', *pair))
try:
    for side in ('Left', 'Right'):
        for suffix in ('DSP1 Enable Switch', 'Amplifier Mode', 'DACPCM Source', 'AMP Enable Switch'):
            name = side + ' ' + suffix
            put(name, spk[name])
    put('QUIN_TDM_RX_0 Audio Mixer MultiMedia1', '1')
    player = subprocess.Popen(['timeout', '10', 'aplay', '-D', 'hw:0,0', '-t', 'raw',
                               '-f', 'S16_LE' if bits == 16 else 'S24_LE',
                               '-r', '48000', '-c', '2', str(tone)])
    try:
        time.sleep(.6)
        print(get('Playback 0 Volume'), flush=True)
        # This control has a meaningful value only while the PCM stream is open.
        put('Playback 0 Volume', '8192')
        for name in ['Left DSP1 Protection cd CSPL_STATE', 'Left DSP1 Protection cd SPK_OUTPUT_POWER',
                     'Right DSP1 Protection cd SPK_OUTPUT_POWER']:
            print(get(name), flush=True)
        assert player.wait(timeout=12) == 0
    finally:
        if player.poll() is None:
            player.terminate()
            player.wait(timeout=3)
finally:
    # Attempt every cleanup even if one mixer command fails.
    for side in ('Left', 'Right'):
        for suffix, value in [('AMP Enable Switch', '0'), ('DSP1 Enable Switch', '0'), ('Amplifier Mode', 'None')]:
            subprocess.run(['amixer', '-c0', 'cset', f'name={side} {suffix}', value],
                           stdout=subprocess.DEVNULL)
    subprocess.run(['amixer', '-c0', 'cset', 'name=QUIN_TDM_RX_0 Audio Mixer MultiMedia1', '0'],
                   stdout=subprocess.DEVNULL)
    subprocess.run(['amixer', '-c0', 'cset', 'name=Playback 0 Volume', old_stream_volume],
                   stdout=subprocess.DEVNULL)
print('Quiet PCM test completed; amps and route disabled afterward. Audibility requires confirmation.')
