#!/usr/bin/env python3
"""Emit an opt-in pen handoff trial against the exact trace-instrumented source.

Lab only, not a released driver: physical hover-out lifecycle remains pending.
No event injection, synthetic strokes, grabs, authentication or startup changes.
Inputs are validated together before any diff is emitted; inputs are not edited.
"""
import argparse
import difflib
import hashlib
from pathlib import Path


SOURCE_SHA = {
    'src/backends/x11/meta-seat-x11.c':
        '2b51ed69a040f7049fe1c7eab95b078cafc2069d34d027053012a1a308c4ba01',
    'src/wayland/meta-wayland-tablet-tool.c':
        '27a6041408eac076a0d4d70fa6db49587b78bdc1044aea92084659f8155f6e91',
}
NAME_HELPER = '''/* Explicit manual T630 trial; never match a master pointer or cursor. */
static gboolean
t630_x11_pen_fix_name (const char *name)
{
  const char *suffix;

  if (g_strcmp0 (g_getenv ("T630_X11_PEN_FIX"), "1") != 0 || !name)
    return FALSE;

  if (g_str_has_prefix (name, "xwayland-tablet stylus:"))
    suffix = name + sizeof ("xwayland-tablet stylus:") - 1;
  else if (g_str_has_prefix (name, "xwayland-tablet eraser:"))
    suffix = name + sizeof ("xwayland-tablet eraser:") - 1;
  else
    return FALSE;

  if (!*suffix)
    return FALSE;
  for (; *suffix; suffix++)
    if (!g_ascii_isdigit (*suffix))
      return FALSE;
  return TRUE;
}

'''
MODE_ANCHOR = '''  if (info->use != XIMasterKeyboard &&
      info->use != XIMasterPointer)'''
MODE_TRIAL = '''  if (mode == CLUTTER_INPUT_MODE_PHYSICAL &&
      (source == CLUTTER_PEN_DEVICE || source == CLUTTER_ERASER_DEVICE) &&
      (capabilities & CLUTTER_INPUT_CAPABILITY_TABLET_TOOL) &&
      t630_x11_pen_fix_name (info->name))
    mode = CLUTTER_INPUT_MODE_FLOATING;

'''
AXIS_ANCHOR = '''      if (!meta_input_device_x11_get_axis (device, i, &axis))
        continue;

      val = *values++;'''
AXIS_TRIAL = '''      if (!meta_input_device_x11_get_axis (device, i, &axis))
        {
          /* XI packs one value for every set bit, even an unknown axis. */
          if (t630_x11_pen_fix_name (clutter_input_device_get_device_name (device)))
            values++;
          continue;
        }

      val = *values++;'''
UPDATE_ANCHOR = '''meta_wayland_tablet_tool_update (MetaWaylandTabletTool *tool,
                                 const ClutterEvent    *event)
{
  switch (clutter_event_type (event))'''
UPDATE_TRIAL = '''meta_wayland_tablet_tool_update (MetaWaylandTabletTool *tool,
                                 const ClutterEvent    *event)
{
  ClutterInputDevice *source = clutter_event_get_source_device (event);
  ClutterEventType type = clutter_event_type (event);

  /* Nested X11 has no proximity-in events. Initialize from a REAL event,
   * preserving its coordinates instead of picking at fabricated (0, 0).
   * Hover-out is not yet covered: this is deliberately a manual lab trial.
   */
  if (!tool->current_tablet && tool->device_tool && source &&
      clutter_input_device_tool_get_serial (tool->device_tool) == 630 &&
      t630_x11_pen_fix_name (clutter_input_device_get_device_name (source)) &&
      (type == CLUTTER_MOTION || type == CLUTTER_BUTTON_PRESS ||
       type == CLUTTER_BUTTON_RELEASE))
    {
      MetaCursorRenderer *renderer;

      tool->current_tablet =
        meta_wayland_tablet_seat_lookup_tablet (tool->seat, source);
      if (tool->current_tablet)
        {
          renderer = meta_backend_get_cursor_renderer_for_device (backend_from_tool (tool),
                                                                  source);
          g_set_object (&tool->cursor_renderer, renderer);
          /* Direct tip-down needs focus before pressed-button accounting. */
          repick_for_event (tool, event);
        }
    }

  switch (clutter_event_type (event))'''


def replace_once(text, anchor, replacement):
    if text.count(anchor) != 1:
        raise ValueError('Unknown or ambiguous pen trial insertion point.')
    return text.replace(anchor, replacement)


def modify(relative, text):
    if relative == 'src/backends/x11/meta-seat-x11.c':
        text = replace_once(text, 'static ClutterInputDevice *\ncreate_device (',
                            NAME_HELPER + 'static ClutterInputDevice *\ncreate_device (')
        text = replace_once(text, MODE_ANCHOR, MODE_TRIAL + MODE_ANCHOR)
        text = replace_once(text, AXIS_ANCHOR, AXIS_TRIAL)
        anchor = 'axes = translate_axes (device, x, y, &xev->valuators);'
        if text.count(anchor) != 2:
            raise ValueError('Expected the exact XI button and motion axis decoders.')
        return text.replace(anchor, '''axes = translate_axes (t630_x11_pen_fix_name (clutter_input_device_get_device_name (source_device)) ?
                                   source_device : device,
                                   x, y, &xev->valuators);''')
    if relative == 'src/wayland/meta-wayland-tablet-tool.c':
        text = replace_once(text, 'void\n' + UPDATE_ANCHOR,
                            NAME_HELPER + 'void\n' + UPDATE_TRIAL)
        return text
    raise ValueError('Unreviewed pen trial source path.')


def build_patch(root):
    originals = {}
    for relative, expected in SOURCE_SHA.items():
        data = (root / relative).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Source differs from the reviewed diagnostic build: ' + relative)
        originals[relative] = data.decode()
    patches = []
    for relative, original in originals.items():
        patches.extend(difflib.unified_diff(
            original.splitlines(keepends=True),
            modify(relative, original).splitlines(keepends=True),
            fromfile='a/' + relative, tofile='b/' + relative))
    return ''.join(patches)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    print(build_patch(args.source), end='')


if __name__ == '__main__':
    main()
