#!/usr/bin/python3
"""Cycle only the idle speaker DSP boot controls to apply cached calibration."""
import subprocess
for side in ('Left', 'Right'):
    for name in ('AMP Enable Switch', 'DSP1 Enable Switch'):
        assert ': values=off' in subprocess.check_output(['amixer', '-c0', 'cget', f'name={side} {name}'], text=True)
for side in ('Left', 'Right'):
    for name, value in [('DSP1 Boot Switch', '0'), ('DSP1 Preload Switch', '0'),
                        ('DSP1 Preload Switch', '1'), ('DSP1 Boot Switch', '1')]:
        subprocess.run(['amixer', '-c0', 'cset', f'name={side} {name}', value], check=True)
