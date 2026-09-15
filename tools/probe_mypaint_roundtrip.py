#!/usr/bin/python3
"""Bounded native OpenRaster round trip of generated strokes, not user artwork.

Creates a unique diagnostic folder in Documents. Does not touch the running
canvas, input devices, preferences, autosaves, or any existing drawing.
This verifies file-engine persistence, not GUI save/reopen or physical pressure.
"""
import hashlib
import os
from pathlib import Path
import resource
import signal
import sys
import tempfile
import zipfile


def main():
    if os.getuid() == 0:
        raise SystemExit('Run as the normal desktop owner.')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    signal.alarm(45)
    os.environ['OMP_NUM_THREADS'] = '1'
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    sys.path.insert(0, '/usr/lib/mypaint')
    from lib.document import Document

    documents = Path.home() / 'Documents'
    if not documents.is_dir():
        raise SystemExit('Documents directory is absent; no files created.')
    output = Path(tempfile.mkdtemp(prefix='MyPaint-file-check-', dir=documents))
    original = Document(painting_only=True)
    reopened = Document(painting_only=True)
    original.brush.brushinfo.set_base_value('radius_logarithmic', 3.0)
    original.brush.brushinfo.set_base_value('opaque', 1.0)
    original.settings['t630-generated-file-check'] = True
    for row in range(8):
        original.brush.reset()
        for point in range(32):
            original.layer_stack.current.stroke_to(
                original.brush, 32.0 + point * 8, 32.0 + row * 20,
                0.25 + point / 48.0, 0.0, 0.0, 0.02, 1.0, 0.0, 0.0)
    bbox = original.get_bbox()
    if bbox.w <= 0 or bbox.h <= 0:
        raise SystemExit('No rendered pixels; test inconclusive.')
    original.set_frame(tuple(bbox))
    original.set_frame_enabled(True)
    archive = output / 'generated-strokes.ora'
    original.save(str(archive))
    with zipfile.ZipFile(archive) as saved:
        if saved.testzip() is not None or saved.read('mimetype') != b'image/openraster':
            raise SystemExit('OpenRaster archive validation failed.')
    reopened.load(str(archive))
    if reopened.settings.get('t630-generated-file-check') is not True:
        raise SystemExit('Document settings did not survive save/load.')
    # Empty allocated tiles can be trimmed when loading. Compare the explicit
    # saved canvas frame and all rendered pixels, not internal tile allocation.
    if not reopened.frame_enabled or tuple(reopened.get_frame()) != tuple(bbox):
        raise SystemExit('Saved canvas frame changed after save/load.')
    def pixels(document):
        root = document.layer_stack
        pixbuf = root.render_layer_as_pixbuf(root, bbox=bbox)
        return (pixbuf.get_width(), pixbuf.get_height(), pixbuf.get_n_channels(),
                pixbuf.get_rowstride(), bytes(pixbuf.get_pixels()))
    before, after = pixels(original), pixels(reopened)
    if before[:-1] != after[:-1] or len(before[-1]) != len(after[-1]):
        raise SystemExit('Rendered pixel geometry changed after save/load.')
    errors = [abs(a-b) for a, b in zip(before[-1], after[-1])]
    # Report measured fidelity separately: successful parsing/frame/settings
    # persistence must not be advertised as a bit-exact artwork round trip.
    print('OPENRASTER_LOAD_PASS: generated_points=256 '
          f'bbox={bbox.w}x{bbox.h} pixel_sha256={hashlib.sha256(before[-1]).hexdigest()}')
    print(f'PIXEL_COMPARISON: identical={before == after} max_byte_error={max(errors)} '
          f'mean_byte_error={sum(errors)/len(errors):.6f} '
          f'changed_bytes={sum(error != 0 for error in errors)}')
    print(f'GENERATED_TEST_FILE: {archive}')
    original.cleanup()
    reopened.cleanup()


if __name__ == '__main__':
    main()
