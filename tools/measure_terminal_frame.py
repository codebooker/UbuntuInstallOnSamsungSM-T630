"""Measure white window decorations in a known one-terminal scanout capture."""
import json
from pathlib import Path
with Path('/tmp/t630-scanout.ppm').open('rb') as f:
    magic = f.readline()
    assert magic == b'P6\n'
    w, h = map(int, f.readline().split())
    maximum = f.readline()
    assert maximum == b'255\n'
    pixels = f.read()
assert (w,h) == (1200,1920)
points = []
# Exclude the panel/launcher at native x<50. The sole window has white borders.
for y in range(50,h-50):
    for x in range(50,w-50):
        rgb = pixels[(y*w+x)*3:(y*w+x+1)*3]
        if min(rgb) > 190:
            points.append((h-1-y,x))
assert points
bounds = [min(x for x,y in points), min(y for x,y in points),
          max(x for x,y in points), max(y for x,y in points)]
print(json.dumps({'logical_white_window_bounds':bounds, 'white_pixels':len(points)}))
assert 400 < bounds[2]-bounds[0] < 1500 and 200 < bounds[3]-bounds[1] < 900
