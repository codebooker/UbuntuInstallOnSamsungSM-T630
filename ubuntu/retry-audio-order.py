#!/usr/bin/python3
"""Manual no-card-only audio retry. Never force-unload or touch desktop modules."""
import os
from pathlib import Path
import signal
import subprocess

raise SystemExit('DISABLED: live stock audio-module unloading caused a kernel restart. Use cold-boot investigation instead.')

assert os.getuid() == 0
assert Path('/proc/asound/cards').read_text().strip() == '--- no soundcards ---'
loader = '/usr/local/share/t630/t630-audio-modules.py'
names = subprocess.check_output(['python3', loader], text=True).splitlines()
normalized = {name.replace('-', '_') for name in names}
for line in Path('/proc/modules').read_text().splitlines():
    fields = line.split()
    if fields[0] in normalized:
        users = set(fields[3].strip(',').split(',')) - {'-'}
        assert users <= normalized, f'Unexpected module users: {fields[0]} {users}'
pid = int(subprocess.check_output(['pgrep', '-x', 't630-pd-mapper'], text=True))
# Pause only the userspace lookup service. Already-running DSP services stay up.
# Resume even if a normal (non-forced) unload refuses or a reload fails.
os.kill(pid, signal.SIGSTOP)
try:
    for name in reversed(names):
        if Path('/sys/module', name.replace('-', '_')).exists():
            print('Unloading ' + name, flush=True)
            subprocess.run(['rmmod', name], check=True, timeout=5)
    subprocess.run(['python3', loader, '--load'], check=True, timeout=20)
finally:
    os.kill(pid, signal.SIGCONT)
print('Audio modules registered before locator responses resumed.', flush=True)
