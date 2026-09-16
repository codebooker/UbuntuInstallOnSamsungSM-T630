#!/usr/bin/python3
"""Bounded headless MyPaint render test; no GUI input or user documents.

Run each thread setting in a separate process. Never use this as proof of
physical pen pressure or palm rejection. Core dumps are disabled for this probe.
"""
import argparse
import os
import resource
import signal
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--threads', type=int, choices=(1, 4), required=True)
parser.add_argument('--brush', help='Installed stock preset name, e.g. classic/impressionism')
parser.add_argument('--full-canvas', action='store_true',
                    help='Also time eight in-memory 1920x1200 layer composites (not display presentation)')
args = parser.parse_args()
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
signal.alarm(25)
os.environ['OMP_NUM_THREADS'] = str(args.threads)
os.environ['OPENBLAS_NUM_THREADS'] = '1'
sys.path.insert(0, '/usr/lib/mypaint')
from lib.brush import Brush, BrushInfo
from lib.tiledsurface import Surface

surface = Surface()
info = BrushInfo()
if args.brush:
    root = Path('/usr/share/mypaint-data/2.0/brushes').resolve()
    preset = (root / (args.brush + '.myb')).resolve()
    if not preset.is_relative_to(root) or not preset.is_file() or preset.stat().st_size > 2**20:
        raise SystemExit('Use a small installed stock MyPaint preset, not a user document.')
    info.load_from_string(preset.read_text())
else:
    info.set_base_value('radius_logarithmic', 3.5)
    info.set_base_value('opaque', 1.0)
brush = Brush(info)
print(f'Headless MyPaint test: threads={args.threads} brush={args.brush or "simple-control"}', flush=True)
render_start = time.monotonic()
cpu_start = time.process_time()
for row in range(12):
    brush.reset()
    surface.begin_atomic()
    for point in range(32):
        brush.stroke_to(surface.backend, point * 8.0, row * 16.0,
                        0.25 + point / 48.0, 0.0, 0.0, 0.02, 1.0, 0.0, 0.0)
    surface.end_atomic()
bbox = surface.get_bbox()
if bbox.w <= 0 or bbox.h <= 0:
    raise SystemExit('No pixels rendered; test inconclusive.')
print(f'HEADLESS_RENDER_PASS: rows=12 points=384 bbox={bbox.w}x{bbox.h} '
      f'render_seconds={time.monotonic() - render_start:.6f} '
      f'cpu_seconds={time.process_time() - cpu_start:.6f}', flush=True)
if args.full_canvas:
    composite_start = time.monotonic()
    for _ in range(8):
        pixbuf = surface.render_as_pixbuf(0, 0, 1920, 1200)
        if pixbuf.get_width() != 1920 or pixbuf.get_height() != 1200:
            raise SystemExit('Unexpected composite dimensions; test inconclusive.')
    print(f'HEADLESS_COMPOSITE_PASS: frames=8 size=1920x1200 '
          f'total_seconds={time.monotonic() - composite_start:.6f}; '
          'one layer, not GUI/display latency', flush=True)
