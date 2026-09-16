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

The next investigation uses the matching Ubuntu Mutter source
`46.2-1ubuntu0.24.04.16` and follow device/tool/focus delivery through the nested
X11 backend into Wayland tablet events. Source acquisition and any subsequent
build belong on the tablet, not the Mac's nearly filled development disk.
The exact source was acquired through Ubuntu's existing signed source index.
A diagnostic-only build completed in an isolated tablet build directory;
16 development dependencies were added to the original build root, with no
package upgrades or removals. The selected clean desktop's installed packages
were not changed. Private libraries and typelibs are staged in its RAM-backed
`/run`; the installed session script is swapped atomically for a manual start
and restored immediately afterward. No new compositor is a default or an
accepted pressure fix.

`tools/prepare_mutter_pen_trace.py` validates all three exact Ubuntu source
hashes before emitting a patch. Its four trace sites log at most eight events
each and do not alter the input events. They observe X11 tool/axis identity,
Wayland tablet-seat registration, actor selection, and client focus. The
suspected master-pointer axis decoding has **not** been changed in this build;
the trace is intended to establish the failure before choosing a fix.

The nested-only configuration initially failed to compile because an `else`
was left before a conditionally excluded native-backend branch. The separately
hash-gated `--nested-configuration-fix` removes only that redundant `else`:
the preceding nested branch returns, so backend selection is preserved. The
syncobj backport also included unused native renderer headers, which pulled in
GBM/GUdev prerequisites despite disabling the native backend. The separately
hash-gated `--syncobj-configuration-fix` replaces those three unused includes
with the actual Wayland DRM timeline and libdrm headers, without changing executable
logic. GBM headers were added while diagnosing that include chain; native
libinput runtime packages were deliberately not upgraded. These are build
prerequisites, not S Pen fixes.

`tools/prepare_mutter_trace_session.py` prepares a separately hash-gated manual
session using five libraries and six matching typelibs in one fixed RAM
directory. It requires both
explicit diagnostic flags, retains the existing startup password lock and
software-rendering synchronization hook, and does not load the failed
proximity preload. It never installs or launches the generated session.

## Private build loading and startup checks

GNOME Shell prepends its distribution-private introspection directory even
when `GI_TYPELIB_PATH` is set. Two early launches consequently loaded private
and distribution Cogl libraries together and stalled on duplicate GObject
type registration. The startup authentication guard refused to complete;
only the validated trial processes were stopped, and the ordinary desktop
was restored. Neither attempt is input or pressure evidence.

`tools/relocate_mutter_trace_gir.py` pins only each reviewed GIR's
`shared-library` attribute to an absolute private RAM path; namespaces and API
declarations remain unchanged. Matching typelibs are recompiled, not copied
over system typelibs. `tools/t630_mutter_trace_namespace.sh` requires root,
the installation marker, explicit trace/metadata flags, software rendering,
a private mount namespace, and a non-shared mount tree. A read-only bind makes
the private library/typelib directory visible to this GNOME launch alone.
Inode checks dereference typelib symlinks. The ordinary desktop namespace's
distribution files retain their original hashes.

With this isolated loading path, the diagnostic GNOME session started and
passed its startup password-lock check. No physical pen events were collected
before that session was restored. A waiting app launcher expired while the
session remained locked: that is **not** a failed pressure test. Helpers
outside the private namespace cannot reliably discover this diagnostic GNOME;
administrative app checks must enter its mount namespace, and normal session
restoration remains mandatory before finishing an unattended trial.

## Unaccepted real-event source trial

`tools/prepare_mutter_pen_source_trial.py` validates both exact
trace-instrumented source hashes before emitting a supplemental diff. The
new trial compiled successfully against the isolated source build. It is
disabled unless `T630_X11_PEN_FIX=1`, and it matches only digit-suffixed private
Xwayland stylus/eraser names, not the master mouse, finger device, or cursor.

The inspected source has three relevant boundaries:

- XI button/motion axes are decoded against the master input device; the trial
  uses the actual matching pen source instead, preserving real coordinates.
- Packed XI valuator values need to advance even for an unknown axis. That
  correction is limited to the explicitly matched trial pen.
- Wayland tablet focus depends on `current_tablet`, normally initialized by a
  proximity-in event. The nested X11 backend does not emit that event. The
  trial initializes the tablet on its first **real** motion/button event and
  selects focus before direct tip-down button accounting. Its matching private
  pen is represented as independent, as native tablet tools are.

No Clutter proximity/motion events, handwriting, or clicks are synthesized.
This is a lead, not a complete driver: physical hover-out lifecycle is not yet
implemented, and pressure delivery, ordinary touch, pen clicks/strokes,
rotation, lock-screen behavior, and drawing-app stability still require
acceptance. `--source-trial` on the session generator adds a third fail-closed
flag requirement while retaining the normal startup password lock. None of
these source-build helpers is invoked by the installer or released startup.

The real-event trial also started successfully with its password lock verified.
The installed ordinary session script was already restored before physical
testing. Its private Mutter library SHA-256 is
`7687e311ec1e23723bc1f7a5a590a91bf2783fe213ddbe1baa0624cde15dd060`;
the distribution library outside the namespace remains
`94d5c4d40ff84a90ad2533adc69671c182ac2e11799c15f3a9dcbcc5b61b0af6`.
The emitted name guard compiled independently under `-Wall -Wextra -Werror`
and passed valid/invalid-name and unset/disabled-flag cases on the tablet build
root. Compilation and successful startup do not establish native pen pressure.
The two-minute GTK test window closed with zero tools, zero samples, and no
input events while GNOME remained locked. No physical acceptance or rejection
can be inferred from that run. The normal managed desktop was restored after
the bounded trial; the prepared RAM bundle remains available for an attended
test. The kernel and boot ID were unchanged.

Reference implementations:

- [Mutter 46.2 X11 seat](https://github.com/GNOME/mutter/blob/46.2/src/backends/x11/meta-seat-x11.c)
- [Mutter 46.2 Wayland tablet tool](https://github.com/GNOME/mutter/blob/46.2/src/wayland/meta-wayland-tablet-tool.c)
- [GTK3 Wayland input devices](https://github.com/GNOME/gtk/blob/3.24.41/gdk/wayland/gdkdevice-wayland.c)
