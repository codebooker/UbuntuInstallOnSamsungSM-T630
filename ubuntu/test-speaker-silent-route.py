#!/usr/bin/python3
"""Exercise the stock playback route with digital silence and speaker amps off."""
import re
import subprocess
import xml.etree.ElementTree as ET

root = ET.parse('/opt/t630/vendor/etc/mixer_paths.xml').getroot()
defaults = {c.attrib['name']: c.attrib['value'] for c in root.findall('ctl')}
def get(name):
    return subprocess.check_output(['amixer', '-c0', 'cget', 'name=' + name], text=True)
def set_control(name, value):
    subprocess.run(['amixer', '-c0', 'cset', 'name=' + name, value], check=True)
for side, expected in [('Left', 9156), ('Right', 9108)]:
    assert ': values=off' in get(side + ' AMP Enable Switch')
    raw = get(side + ' DSP1 Protection cd CAL_R').split(': values=')[1].strip()
    assert int.from_bytes(bytes(int(b, 16) for b in raw.split(',')), 'big') == expected
for name in ['QUIN_TDM_RX_0 Channels', 'QUIN_TDM_RX_0 Format']:
    set_control(name, defaults[name])
for side in ('Left', 'Right'):
    for suffix in ['BBPE Enable Switch', 'SYNC Enable Switch', 'DACPCM Source',
                   'ASPRX1 Slot Position', 'ASPRX2 Slot Position', 'DSP_RX1 Source',
                   'DSP_RX2 Source', 'DSP_RX5 Source', 'DSP_RX6 Source', 'DSP_RX7 Source']:
        name = side + ' ' + suffix
        set_control(name, defaults[name])
route = 'QUIN_TDM_RX_0 Audio Mixer MultiMedia1'
assert ': values=off' in get(route) or ': values=0' in get(route)
set_control(route, '1')
try:
    subprocess.run(['timeout', '10', 'aplay', '-D', 'hw:0,0', '-t', 'raw', '-f', 'S24_LE',
                    '-r', '48000', '-c', '2', '-d', '1', '/dev/zero'], check=True)
finally:
    set_control(route, '0')
print('One-second digital-silence PCM test passed with speaker amps disabled.')
