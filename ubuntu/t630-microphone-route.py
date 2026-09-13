#!/usr/bin/python3
"""Enable or disable the SM-T630's stock high-gain main microphone path."""
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

assert os.getuid() == 0
assert sys.argv[1:] in (['on'], ['off'])
assert Path('/etc/t630-install-id').read_text().strip() == 'SM-T630-T630XXSBDZE3-Ubuntu-v1'


def get(name):
    return subprocess.check_output(['amixer', '-c0', 'cget', 'name=' + name], text=True)


def put(name, value):
    subprocess.run(['amixer', '-q', '-c0', 'cset', 'name=' + name, value], check=True)


def stop():
    # Disconnect the PCM first, then the codec capture stages.
    put('MultiMedia1 Mixer TX_CDC_DMA_TX_3', '0')
    put('TX_AIF1_CAP Mixer DEC0', '0')
    put('ADC1_MIXER Switch', '0')


if sys.argv[1] == 'off':
    stop()
    raise SystemExit

root = ET.parse('/opt/t630/vendor/etc/mixer_paths.xml').getroot()
defaults = {c.attrib['name']: c.attrib['value'] for c in root.findall('ctl')}
paths = {p.attrib['name']: p for p in root.findall('path')}
main = {c.attrib['name']: c.attrib['value'] for c in paths['main-mic'].findall('ctl')}
voice = {c.attrib['name']: c.attrib['value'] for c in paths['vr-main-mic'].findall('ctl')}
record = {c.attrib['name']: c.attrib['value'] for c in paths['audio-record'].findall('ctl')}

# These values come verbatim from Samsung's DZE3 mixer file. The ordinary
# record profile expects Android DSP gain that is absent on Ubuntu; Samsung's
# own voice-recognition profile supplies usable codec/decoder gain instead.
expected = {
    'TX DEC0 MUX': 'SWR_MIC',
    'TX SMIC MUX0': 'SWR_MIC0',
    'ADC1 ChMap': 'SWRM_TX1_CH1',
    'TX_DEC0 Volume': '101',
    'ADC1 Volume': '10',
    'MultiMedia1 Mixer TX_CDC_DMA_TX_3': '1',
}
for name, value in expected.items():
    source = main | voice | record
    assert source[name] == value, (name, source.get(name))
    get(name)  # Refuse partial application if this exact control is absent.

try:
    stop()
    for name in ('TX_CDC_DMA_TX_3 Channels', 'TX_CDC_DMA_TX_3 Format'):
        put(name, defaults[name])
    for name, value in main.items():
        put(name, value)
    for name, value in voice.items():
        put(name, value)
    for name, value in record.items():
        put(name, value)
except Exception:
    stop()
    raise

print('Stock high-gain main microphone route enabled.')
