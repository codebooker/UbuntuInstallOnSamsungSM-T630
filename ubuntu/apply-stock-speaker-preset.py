#!/usr/bin/python3
"""Apply the stock startup DSP preset, with speakers disabled."""
import subprocess
import xml.etree.ElementTree as ET
defaults = {c.attrib['name']: c.attrib['value'] for c in ET.parse('/opt/t630/vendor/etc/mixer_paths.xml').getroot().findall('ctl')}
for side in ('Left', 'Right'):
    result = subprocess.check_output(['amixer', '-c0', 'cget', f'name={side} AMP Enable Switch'], text=True)
    assert ': values=off' in result
for side in ('Left', 'Right'):
    name = side + ' Fast Use Case Delta File'
    assert defaults[name] == 'cs35l45-default.bin'
    subprocess.run(['amixer', '-c0', 'cset', 'name=' + name, defaults[name]], check=True)
