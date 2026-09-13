#!/usr/bin/env python3
"""Mock mixer tests: no tablet access, no actual audio controls."""
from pathlib import Path
import runpy
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

source = Path(__file__).resolve().parents[1] / 'ubuntu/t630-speaker-route.py'
if not source.exists():
    source = Path('/usr/local/share/t630/t630-speaker-route.py')


class RouteTests(unittest.TestCase):
    def execute(self, mode, bad_calibration=False):
        root = ET.Element('mixer')
        names = ['QUIN_TDM_RX_0 Channels', 'QUIN_TDM_RX_0 Format']
        suffixes = ['BBPE Enable Switch', 'SYNC Enable Switch', 'DACPCM Source',
                    'ASPRX1 Slot Position', 'ASPRX2 Slot Position', 'DSP_RX1 Source',
                    'DSP_RX2 Source', 'DSP_RX5 Source', 'DSP_RX6 Source', 'DSP_RX7 Source']
        names += [side + ' ' + suffix for side in ('Left', 'Right') for suffix in suffixes]
        for name in names:
            ET.SubElement(root, 'ctl', name=name, value='stock-value')
        speaker = ET.SubElement(root, 'path', name='spk')
        for side in ('Left', 'Right'):
            for suffix in ('DSP1 Enable Switch', 'Amplifier Mode', 'DACPCM Source', 'AMP Enable Switch'):
                ET.SubElement(speaker, 'ctl', name=side + ' ' + suffix, value='1')
        self.writes = []

        def read(args, **kwargs):
            name = args[-1].removeprefix('name=')
            if name.endswith('AMP Enable Switch'):
                return ': values=off'
            if name.endswith('Protection cd CAL_R'):
                value = 0 if bad_calibration else 9156 if name.startswith('Left') else 9108
                return ': values=' + ','.join(hex(b) for b in value.to_bytes(4, 'big'))
            if name.endswith('DSP1 Firmware'):
                return ': values=9'
            return ': values=0'

        def write(args, **kwargs):
            self.writes.append((args[-2].removeprefix('name='), args[-1]))

        with mock.patch('os.getuid', return_value=0), \
                mock.patch('sys.argv', ['route', mode]), \
                mock.patch('subprocess.check_output', side_effect=read), \
                mock.patch('subprocess.run', side_effect=write), \
                mock.patch('xml.etree.ElementTree.parse', return_value=ET.ElementTree(root)):
            runpy.run_path(str(source))

    def test_prepare_never_enables_amplifiers(self):
        self.execute('prepare')
        self.assertFalse(any(name.endswith('AMP Enable Switch') for name, value in self.writes))
        self.assertIn(('QUIN_TDM_RX_0 Audio Mixer MultiMedia1', '1'), self.writes)

    def test_on_retains_existing_amp_enable(self):
        self.execute('on')
        for side in ('Left', 'Right'):
            self.assertIn((side + ' AMP Enable Switch', '1'), self.writes)

    def test_bad_calibration_refuses_all_writes(self):
        with self.assertRaises(AssertionError):
            self.execute('prepare', bad_calibration=True)
        self.assertEqual(self.writes, [])

    def test_prepare_never_changes_gain_or_calibration(self):
        self.execute('prepare')
        self.assertFalse(any('Gain' in name or 'CAL_' in name or 'Protection' in name
                             for name, value in self.writes))


if __name__ == '__main__':
    unittest.main()
