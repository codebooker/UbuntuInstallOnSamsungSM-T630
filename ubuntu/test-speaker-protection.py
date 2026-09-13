#!/usr/bin/python3
"""Load exact stock protection DSP firmware with both speaker amps disabled."""
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

assert os.getuid() == 0
root = ET.parse('/opt/t630/vendor/etc/mixer_paths.xml').getroot()
defaults = {c.attrib['name']: c.attrib['value'] for c in root.findall('ctl')}
def get(name):
    return subprocess.check_output(['amixer', '-c0', 'cget', 'name=' + name], text=True)
for side in ('Left', 'Right'):
    assert ': values=off' in get(side + ' AMP Enable Switch')
    assert ': values=off' in get(side + ' DSP1 Enable Switch')
for side in ('Left', 'Right'):
    for suffix, value in [('DSP1 Firmware', 'Protection'), ('DSP1 Preload Switch', '1'), ('DSP1 Boot Switch', '1')]:
        name = side + ' ' + suffix
        assert defaults[name] == value
        subprocess.run(['amixer', '-c0', 'cset', 'name=' + name, value], check=True)
    name = side + ' Fast Use Case Delta File'
    assert defaults[name] == 'cs35l45-default.bin'
    subprocess.run(['amixer', '-c0', 'cset', 'name=' + name, defaults[name]], check=True)
for side in ('Left', 'Right'):
    assert ': values=off' in get(side + ' AMP Enable Switch')
print('Protection firmware requested. Amplifiers remain disabled; no playback.')
