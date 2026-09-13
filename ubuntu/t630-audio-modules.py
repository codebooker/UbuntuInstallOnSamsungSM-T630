#!/usr/bin/python3
"""Resolve the exact SM-T630 stock audio module set; default is read-only."""
import os
from pathlib import Path
import subprocess
import sys

kernel = '5.4.274-qgki-31225846-abT630XXSBDZE3'
assert os.uname().release == kernel
assert sys.argv[1:] in ([], ['--load'])
directory = Path('/opt/t630/vendor/lib/modules')
dependencies = {}
for line in (directory / 'modules.dep').read_text().splitlines():
    module, values = line.split(':', 1)
    dependencies[Path(module).stem] = [Path(value).stem for value in values.split()]
# Audio entries in this device's init.gtact4prowifi.rc (not a different board).
roots = '''q6_pdr_dlkm q6_notifier_dlkm snd_event_dlkm apr_dlkm adsp_loader_dlkm
q6_dlkm native_dlkm pinctrl_wcd_dlkm pinctrl_lpi_dlkm platform_dlkm hdmi_dlkm
stub_dlkm wcd_core_dlkm bolero_cdc_dlkm va_macro_dlkm rx_macro_dlkm tx_macro_dlkm
machine_dlkm'''.split()
# The live I2C bus exposes the two enabled CS35L45 devices at 18-0030/18-0031.
for address in ('18-0030', '18-0031'):
    compatible = Path('/sys/bus/i2c/devices', address, 'of_node/compatible').read_bytes()
    assert b'cirrus,cs35l45' in compatible
roots.append('snd-soc-cs35l45-i2c')
# The exact live DT has WCD938x TX/RX SoundWire slave nodes. Their driver is
# separate from the parent codec and not a module-symbol dependency of it.
dt = Path('/sys/firmware/devicetree/base/soc/qcom,msm-audio-apr/qcom,q6core-audio/bolero-cdc')
assert any(b'qcom,wcd938x-slave' in p.read_bytes() for p in dt.rglob('compatible'))
roots.append('wcd938x_slave_dlkm')
# The stock sound card also requires its Bluetooth Slimbus codec even when
# testing built-in speakers. These drivers are in this firmware's modules.load.
slim = Path('/sys/firmware/devicetree/base/soc/slim@3ac0000')
assert b'qcom,slim-ngd' in (slim / 'compatible').read_bytes()
assert b'qcom,btfmslim_slave' in (slim / 'qca6490/compatible').read_bytes()
roots.extend(['slimbus-ngd', 'bt_fm_slim'])
ordered, active = [], set()
def visit(name):
    if name in ordered:
        return
    assert name not in active, f'Circular dependency: {name}'
    active.add(name)
    for dependency in dependencies[name]:
        visit(dependency)
    active.remove(name)
    ordered.append(name)
for root in roots:
    visit(root)
for name in ordered:
    path = directory / (name + '.ko')
    magic = subprocess.check_output(['modinfo', '-F', 'vermagic', str(path)], text=True)
    assert magic.startswith(kernel + ' ') and 'aarch64' in magic
    print(name, flush=True)
if sys.argv[1:] == ['--load']:
    assert os.getuid() == 0
    for name in ordered:
        if Path('/sys/module', name.replace('-', '_')).exists():
            continue
        print('Loading ' + name, flush=True)
        subprocess.run(['insmod', str(directory / (name + '.ko'))], check=True)
    print('Stock audio module loading completed; playback is not verified.', flush=True)
