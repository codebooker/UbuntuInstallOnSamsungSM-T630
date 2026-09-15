# S Pen pressure-path investigation — September 15, 2026

Status: hardware and parent X11 pressure confirmed; native GNOME pen delivery
remains unresolved. This is a lab report, not an installer step or a working
pressure fix.

## Physical evidence

- Read-only polling of the exact, previously identified `sec_e-pen` event7
  pressure axis collected 598 samples. The range was 0–2550, against the
  reported hardware maximum of 4095; 50 samples were nonzero.
- The corrected GTK3 probe in the parent X11 session collected 472 pen samples
  spanning normalized pressure 0–0.7684901197833219. The owner confirmed that
  its visible pressure number changed during strokes.
- The native GTK3 test inside nested GNOME received finger events, but the
  owner reported no pen identity or changing pressure readout. This does not
  establish a failure of the pen sensor or kernel driver.

The probe originally assumed that PyGObject returned a `(success, value)` pair
from `get_axis()`. This installation returns a number or `None`. The corrected
normalizer supports both forms, rejects invalid values, and preserves zero.
Earlier failed readouts affected by that bug are not pressure evidence.

## Unaccepted experiments

Manual X11 Wacom metadata was published before/after GNOME startup to examine
tool classification. An ABI- and hash-gated preload then attempted to supply
missing tablet proximity transitions; a later variant constructed the private
stylus/eraser as independent devices. The bridge observed a stylus motion with
tool serial 630, but that observation did not translate into an accepted pen
event in the native test app.

The owner also reported that pen hover took the app out of fullscreen. GNOME's
Activities hot corner was enabled, so it was temporarily disabled as a
diagnostic hypothesis. That hypothesis was not physically verified. The trial
was abandoned rather than treating synthetic proximity as a released fix, and
the original hot-corner preference was restored.

The normal managed GNOME session was restored without either trial flag. Its
installed session script matches the pre-trial SHA-256
`6e121b1647f5c19e4941b836eb86b8104497c1ff15d0b06722bde3d8c624f912`.
Startup password locking and SSH connectivity were verified after replacement.
The boot ID remained unchanged: only the desktop session was replaced.

## Scope and next investigation

The source-only tools are deliberately outside released package startup:
`observe_pen_pressure.py`, `probe_gdk_pen.py`,
`prepare_pen_session_trial.py`, and `t630_pen_proximity_trial.c`. The generator
requires the reviewed base script, and its bridge branch checks the exact
Mutter, Clutter, and bridge binaries. Do not use these as installation advice.

No physical device grab, handwriting-coordinate recording, kernel change,
partition flashing, authentication bypass, or global permission widening was
used. The physical-axis observer validates the installation marker and the
exact event7 name before reading current pressure values.

Next: inspect the matching Ubuntu Mutter source
`46.2-1ubuntu0.24.04.16` and follow device/tool/focus delivery through the nested
X11 backend into Wayland tablet events. Source acquisition and any subsequent
build belong on the tablet, not the Mac's nearly filled development disk.
The exact source was acquired through Ubuntu's existing signed source index.
A diagnostic-only build is in progress in an isolated tablet build directory;
15 development dependencies were added to the original build root, with no
package upgrades or removals. The selected clean desktop root was not changed.
No new compositor build has been installed or accepted.

`tools/prepare_mutter_pen_trace.py` validates all three exact Ubuntu source
hashes before emitting a patch. Its four trace sites log at most eight events
each and do not alter the input events. They observe X11 tool/axis identity,
Wayland tablet-seat registration, actor selection, and client focus. The
suspected master-pointer axis decoding has **not** been changed in this build;
the trace is intended to establish the failure before choosing a fix.

Reference implementations:

- [Mutter 46.2 X11 seat](https://github.com/GNOME/mutter/blob/46.2/src/backends/x11/meta-seat-x11.c)
- [Mutter 46.2 Wayland tablet tool](https://github.com/GNOME/mutter/blob/46.2/src/wayland/meta-wayland-tablet-tool.c)
- [GTK3 Wayland input devices](https://github.com/GNOME/gtk/blob/3.24.41/gdk/wayland/gdkdevice-wayland.c)
