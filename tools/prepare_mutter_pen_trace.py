#!/usr/bin/env python3
"""Emit a reviewed Ubuntu Mutter source trace patch; never install or edit files.

Diagnostic only: no event mutation, proximity synthesis, pressure scaling,
coordinates, handwriting, passwords, input grabs, or startup changes.
"""
import argparse
import difflib
import hashlib
from pathlib import Path
import sys


SOURCE_SHA = {
    'src/backends/x11/meta-seat-x11.c':
        '0263d16c0d100531158da98986beb8574741c7068c938c0b1c2217438a148ae0',
    'src/wayland/meta-wayland-tablet-seat.c':
        '08549daaf2b33777b75d8a90615594c8913cb12a624084cdb09cbd3644313ec7',
    'src/wayland/meta-wayland-tablet-tool.c':
        '669cf5a9b57d5252c89a78afd229028aa142ddcda2cec92a3e1e2eb6fdf0729f',
}

HELPER = '''/* Source-only T630 lab trace. Each call site logs at most eight events. */
static gboolean
t630_pen_trace_enabled (ClutterInputDevice *device)
{
  const char *name;

  if (g_strcmp0 (g_getenv ("T630_MUTTER_PEN_TRACE"), "1") != 0 || !device)
    return FALSE;

  name = clutter_input_device_get_device_name (device);
  return name && (g_str_has_prefix (name, "xwayland-tablet stylus:") ||
                  g_str_has_prefix (name, "xwayland-tablet eraser:"));
}

'''

MOTION_ANCHOR = '''        axes = translate_axes (device, x, y, &xev->valuators);
        event = clutter_event_motion_new'''
MOTION_TRACE = '''        if (t630_pen_trace_enabled (source_device))
          {
            static unsigned trace_count;
            if (trace_count++ < 8)
              g_message ("T630 pen trace XI motion: tool=%d source_equals_master=%d source_axes=%u master_axes=%u mode=%d",
                         tool != NULL, source_device == device,
                         meta_input_device_x11_get_n_axes (source_device),
                         meta_input_device_x11_get_n_axes (device),
                         clutter_input_device_get_device_mode (source_device));
          }

'''
SEAT_ANCHOR = '''      if (device && device_tool)
        tool = meta_wayland_tablet_seat_ensure_tool'''
SEAT_TRACE = '''      if (t630_pen_trace_enabled (device))
        {
          static unsigned trace_count;
          if (trace_count++ < 8)
            g_message ("T630 pen trace tablet seat: event=%d tool=%d tablet=%d capabilities=%u mode=%d",
                       clutter_event_type (event), device_tool != NULL,
                       g_hash_table_contains (tablet_seat->tablets, device),
                       (unsigned) clutter_input_device_get_capabilities (device),
                       clutter_input_device_get_device_mode (device));
        }

'''
REPICK_ANCHOR = '''  if (META_IS_SURFACE_ACTOR_WAYLAND (actor))
    surface = meta_surface_actor_wayland_get_surface'''
REPICK_TRACE = '''  if (t630_pen_trace_enabled (clutter_event_get_source_device (for_event)))
    {
      static unsigned trace_count;
      if (trace_count++ < 8)
        g_message ("T630 pen trace repick: tablet=%d actor=%s wayland_surface=%d",
                   tool->current_tablet != NULL,
                   actor ? G_OBJECT_TYPE_NAME (actor) : "none",
                   actor && META_IS_SURFACE_ACTOR_WAYLAND (actor));
    }

'''
HANDLE_ANCHOR = '''  if (!tool->focus_surface)
    return CLUTTER_EVENT_PROPAGATE;

  switch (clutter_event_type (event))'''
HANDLE_TRACE = '''  if (t630_pen_trace_enabled (clutter_event_get_source_device (event)))
    {
      static unsigned trace_count;
      if (trace_count++ < 8)
        g_message ("T630 pen trace dispatch: event=%d tablet=%d focus=%d",
                   clutter_event_type (event), tool->current_tablet != NULL,
                   tool->focus_surface != NULL);
    }

'''


def insert_once(text, anchor, fragment):
    if text.count(anchor) != 1:
        raise ValueError('Unknown or ambiguous diagnostic insertion point.')
    return text.replace(anchor, fragment + anchor)


def instrument(relative, text):
    if relative == 'src/backends/x11/meta-seat-x11.c':
        text = insert_once(text, 'static double *\ntranslate_axes (', HELPER)
        return insert_once(text, MOTION_ANCHOR, MOTION_TRACE)
    if relative == 'src/wayland/meta-wayland-tablet-seat.c':
        text = insert_once(text, 'static gboolean\nis_tablet_device (', HELPER)
        return insert_once(text, SEAT_ANCHOR, SEAT_TRACE)
    if relative == 'src/wayland/meta-wayland-tablet-tool.c':
        text = insert_once(text, 'static void\nrepick_for_event (', HELPER)
        text = insert_once(text, REPICK_ANCHOR, REPICK_TRACE)
        return insert_once(text, HANDLE_ANCHOR, HANDLE_TRACE)
    raise ValueError('Unreviewed source path.')


def build_patch(source):
    # Validate every input before emitting any patch; exact Ubuntu .16 sources.
    originals = {}
    for relative, expected in SOURCE_SHA.items():
        data = (source / relative).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Source differs from reviewed Ubuntu Mutter .16: ' + relative)
        originals[relative] = data.decode()
    patches = []
    for relative, text in originals.items():
        modified = instrument(relative, text)
        patches.extend(difflib.unified_diff(
            text.splitlines(keepends=True), modified.splitlines(keepends=True),
            fromfile='a/' + relative, tofile='b/' + relative))
    return ''.join(patches)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    sys.stdout.write(build_patch(args.source))


if __name__ == '__main__':
    main()
