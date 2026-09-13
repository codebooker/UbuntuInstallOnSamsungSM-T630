#!/usr/bin/python3
"""Bounded invisible GNOME render test; private X server, bus and profile.

Runs as tablet, never replaces or unlocks the physical desktop. GPU tests still
share kernel hardware, so a driver fault is not guaranteed to be isolated.
"""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import hashlib

assert os.getuid() == 1000
assert Path('/etc/t630-install-id').read_text().strip() == 'SM-T630-T630XXSBDZE3-Ubuntu-v1'
modes = ('software', 'gpu', 'gpu-sysmem', 'gpu-x11', 'gpu-x11-sysmem')
assert (len(sys.argv) == 2 and sys.argv[1] in modes
        or len(sys.argv) == 3 and sys.argv[1] == '--inside' and sys.argv[2] in modes)

if sys.argv[1] == '--inside':
    mode = sys.argv[2]
    # The separate session bus and empty profile prevent activation/configuration
    # from reaching the real GNOME instance or enabling its tablet extensions.
    subprocess.run(['gsettings', 'set', 'org.gnome.desktop.interface', 'enable-animations', 'false'], check=True)
    subprocess.run(['gsettings', 'set', 'org.gnome.desktop.session', 'idle-delay', '0'], check=True)
    subprocess.run(['gsettings', 'set', 'org.gnome.shell', 'disable-user-extensions', 'true'], check=True)
    loader = importlib.machinery.SourceFileLoader('watch', '/usr/local/libexec/t630-gpu-session-watch')
    spec = importlib.util.spec_from_loader(loader.name, loader)
    watch = importlib.util.module_from_spec(spec)
    loader.exec_module(watch)
    first_ready = None
    checks = 0
    observed_gpu = False
    completed = False
    frames = set()

    def probe(pid):
        global first_ready, checks, observed_gpu, completed
        ready = watch.desktop_ready(pid)
        if ready:
            checks += 1
            if first_ready is None:
                first_ready = time.monotonic()
                observed_gpu = 'mesa-25.2.8-kgsl' in Path(f'/proc/{pid}/maps').read_text()
                print(json.dumps({'ready': True, 'mode': mode, 'pid': pid,
                                  'gpu_library': observed_gpu}), flush=True)
            from PIL import ImageGrab
            if checks >= 3:
                frame = ImageGrab.grab(xdisplay=os.environ['DISPLAY'])
                # Exclude the clock: a clock update alone is not a UI redraw.
                frames.add(hashlib.sha256(frame.crop((100, 100, 1820, 1100)).tobytes()).hexdigest())
            # The public ShowApplications bus method may reject this caller.
            # Use input on the private X server and verify visible image changes.
            subprocess.run(['xdotool', 'key', '--clearmodifiers',
                            'Escape' if checks % 2 else 'super+a'], check=True, timeout=3)
            if time.monotonic() - first_ready >= 30:
                with tempfile.NamedTemporaryFile(prefix='t630-isolated-' + mode + '-',
                                                 suffix='.png', delete=False) as image_file:
                    # Explicit private Xvfb display, never the physical screen.
                    frame = ImageGrab.grab(xdisplay=os.environ['DISPLAY'])
                    frame.save(image_file, format='PNG')
                    print(json.dumps({'private_screen': image_file.name,
                                      'size': frame.size}), flush=True)
                completed = True
                os.kill(os.getpid(), signal.SIGTERM)
        return ready

    command = ['/usr/bin/gnome-shell', '--nested', '--wayland',
               '--wayland-display=t630-render-test']
    if mode not in ('gpu-x11', 'gpu-x11-sysmem'):
        command.append('--no-x11')
    os.environ['LD_PRELOAD'] = '/usr/local/lib/t630-cogl-sync.so'
    if mode != 'software':
        command.insert(0, '/usr/local/bin/t630-gpu-env')
    if mode in ('gpu-sysmem', 'gpu-x11-sysmem'):
        os.environ['TU_DEBUG'] = 'sysmem'
    result = watch.supervise(command, ready=probe, startup_timeout=40, health_interval=3)
    passed = completed and checks >= 5 and observed_gpu == (mode != 'software')
    print(json.dumps({'mode': mode, 'healthy_checks': checks, 'completed': completed,
                      'gpu_library': observed_gpu, 'supervisor_exit': result,
                      'responsiveness_pass': passed,
                      'distinct_frames': len(frames), 'redraw_pass': len(frames) >= 2,
                      'requires_kernel_and_image_review': True}), flush=True)
    raise SystemExit(0 if passed and len(frames) >= 2 else 1)

mode = sys.argv[1]
with tempfile.TemporaryDirectory(prefix='t630-render-test-') as directory:
    root = Path(directory)
    runtime = root / 'runtime'
    runtime.mkdir(mode=0o700)
    env = dict(PATH='/usr/local/bin:/usr/bin:/bin', LANG='C.UTF-8',
               HOME=str(root), USER='tablet', LOGNAME='tablet',
               XDG_RUNTIME_DIR=str(runtime), XDG_CONFIG_HOME=str(root / 'config'),
               XDG_DATA_HOME=str(root / 'data'), XDG_CACHE_HOME=str(root / 'cache'),
               XDG_CURRENT_DESKTOP='GNOME', XDG_SESSION_TYPE='wayland',
               LIBGL_ALWAYS_SOFTWARE='1', GALLIUM_DRIVER='llvmpipe',
               MESA_LOADER_DRIVER_OVERRIDE='swrast', GSK_RENDERER='cairo',
               MUTTER_DEBUG_DUMMY_MODE_SPECS='1920x1200', NO_AT_BRIDGE='1',
               XWAYLAND_NO_GLAMOR='1')
    # xvfb-run allocates its own display and authentication cookie, disables TCP,
    # and cleans up only the server it launched. The normal display is untouched.
    child = subprocess.Popen([
        'xvfb-run', '--auto-servernum', '--server-num=17',
        '--server-args=-screen 0 1920x1200x24 -nolisten tcp -extension MIT-SHM',
        'dbus-run-session', '--', sys.executable, str(Path(__file__).resolve()), '--inside', mode],
        env=env, start_new_session=True)
    try:
        result = child.wait(timeout=100)
    except subprocess.TimeoutExpired:
        result = 124
    finally:
        # Private session/process group includes only this test's server, bus,
        # GNOME and bus-activated test helpers. Never signal the live session.
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=3)
    raise SystemExit(result)
