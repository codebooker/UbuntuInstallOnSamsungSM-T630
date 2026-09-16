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
CONTEXT_SHA = 'a559e0b970c23f9f04fce303d1077f2ec9d20196d685b61c2aae0830a6b4d2d7'
SYNCOBJ_SHA = 'e1860178a9e0720377a0a67de9391935fd4d182669c610dec22af5c61bb64181'
SYNCOBJ_ANCHOR = '''#include "backends/native/meta-backend-native-types.h"
#include "backends/native/meta-device-pool.h"
#include "backends/native/meta-renderer-native.h"
'''
CONTEXT_ANCHOR = '''      if (context_main->options.nested)
        return create_nested_backend (context, error);
      else
#endif
#ifdef HAVE_NATIVE_BACKEND'''

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


def build_nested_configuration_patch(source):
    # Ubuntu .16 leaves an orphan "else" when native_backend=false. The
    # preceding branch returns, so removing else preserves backend selection.
    relative = 'src/core/meta-context-main.c'
    data = (source / relative).read_bytes()
    if hashlib.sha256(data).hexdigest() != CONTEXT_SHA:
        raise ValueError('Unreviewed backend configuration source.')
    text = data.decode()
    if text.count(CONTEXT_ANCHOR) != 1:
        raise ValueError('Ambiguous backend configuration branch.')
    modified = text.replace(CONTEXT_ANCHOR,
                            CONTEXT_ANCHOR.replace('      else\n', ''))
    return ''.join(difflib.unified_diff(
        text.splitlines(keepends=True), modified.splitlines(keepends=True),
        fromfile='a/' + relative, tofile='b/' + relative))


def build_syncobj_configuration_patch(source):
    # The backport uses MetaDrmTimeline, not native renderer/device-pool APIs.
    # Include the actual Wayland timeline declaration without native headers.
    relative = 'src/wayland/meta-wayland-linux-drm-syncobj.c'
    data = (source / relative).read_bytes()
    if hashlib.sha256(data).hexdigest() != SYNCOBJ_SHA:
        raise ValueError('Unreviewed syncobj configuration source.')
    text = data.decode()
    if text.count(SYNCOBJ_ANCHOR) != 1:
        raise ValueError('Ambiguous syncobj includes.')
    modified = text.replace(SYNCOBJ_ANCHOR,
                            '#include <xf86drm.h>\n#include "wayland/meta-drm-timeline.h"\n')
    return ''.join(difflib.unified_diff(
        text.splitlines(keepends=True), modified.splitlines(keepends=True),
        fromfile='a/' + relative, tofile='b/' + relative))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--nested-configuration-fix', action='store_true',
                        help='Emit the separately hash-gated orphan-else build fix instead of tracing')
    mode.add_argument('--syncobj-configuration-fix', action='store_true',
                      help='Emit the separately hash-gated unused-native-header build fix')
    args = parser.parse_args()
    builder = (build_nested_configuration_patch if args.nested_configuration_fix
               else build_syncobj_configuration_patch if args.syncobj_configuration_fix
               else build_patch)
    sys.stdout.write(builder(args.source))


if __name__ == '__main__':
    main()
