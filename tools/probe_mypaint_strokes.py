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

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--threads', type=int, choices=(1, 4), required=True)
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
info.set_base_value('radius_logarithmic', 3.5)
info.set_base_value('opaque', 1.0)
brush = Brush(info)
print(f'Headless MyPaint test: threads={args.threads}', flush=True)
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
print(f'HEADLESS_RENDER_PASS: rows=12 points=384 bbox={bbox.w}x{bbox.h}', flush=True)
