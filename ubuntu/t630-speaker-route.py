#!/usr/bin/python3
"""Enable/disable the validated stock, calibrated speaker path."""
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

assert os.getuid() == 0
assert sys.argv[1:] in (['on'], ['off'], ['prepare'])
def get(name):
    return subprocess.check_output(['amixer', '-c0', 'cget', 'name=' + name], text=True)
def put(name, value):
    subprocess.run(['amixer', '-c0', 'cset', 'name=' + name, value], check=True,
                   stdout=subprocess.DEVNULL)
def stop():
    failures = []
    for side in ('Left', 'Right'):
        for suffix, value in [('AMP Enable Switch', '0'), ('DSP1 Enable Switch', '0'), ('Amplifier Mode', 'None')]:
            try: put(side + ' ' + suffix, value)
            except subprocess.CalledProcessError: failures.append(side + ' ' + suffix)
    try: put('QUIN_TDM_RX_0 Audio Mixer MultiMedia1', '0')
    except subprocess.CalledProcessError: failures.append('PCM route')
    assert not failures, failures
if sys.argv[1] == 'off':
    stop()
    sys.exit(0)
root = ET.parse('/opt/t630/vendor/etc/mixer_paths.xml').getroot()
defaults = {c.attrib['name']: c.attrib['value'] for c in root.findall('ctl')}
speaker = next(p for p in root.findall('path') if p.attrib['name'] == 'spk')
spk = {c.attrib['name']: c.attrib['value'] for c in speaker.findall('ctl')}
for side, expected in [('Left', 9156), ('Right', 9108)]:
    assert ': values=off' in get(side + ' AMP Enable Switch')
    raw = get(side + ' DSP1 Protection cd CAL_R').split(': values=')[1].strip()
    assert int.from_bytes(bytes(int(b, 16) for b in raw.split(',')), 'big') == expected
    assert ': values=9' in get(side + ' DSP1 Firmware')
    assert ': values=0' in get(side + ' Fast Use Case Delta File')
try:
    for name in ['QUIN_TDM_RX_0 Channels', 'QUIN_TDM_RX_0 Format']:
        put(name, defaults[name])
    for side in ('Left', 'Right'):
        for suffix in ['BBPE Enable Switch', 'SYNC Enable Switch', 'DACPCM Source',
                       'ASPRX1 Slot Position', 'ASPRX2 Slot Position', 'DSP_RX1 Source',
                       'DSP_RX2 Source', 'DSP_RX5 Source', 'DSP_RX6 Source', 'DSP_RX7 Source']:
            name = side + ' ' + suffix
            put(name, defaults[name])
        for suffix in ('DSP1 Enable Switch', 'Amplifier Mode', 'DACPCM Source', 'AMP Enable Switch'):
            name = side + ' ' + suffix
            if sys.argv[1] == 'prepare' and suffix == 'AMP Enable Switch':
                continue  # Route/configure PCM with both physical amps still off.
            put(name, spk[name])
    put('QUIN_TDM_RX_0 Audio Mixer MultiMedia1', '1')
except Exception:
    stop()
    raise
if sys.argv[1] == 'prepare':
    print('Calibrated PCM route prepared; speaker amplifiers remain off.')
else:
    print('Calibrated stock speaker route enabled; volume belongs to the user audio server.')
