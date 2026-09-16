# S Pen pressure-path investigation — September 15, 2026

Status: hardware, parent X11, and native GNOME GTK pressure confirmed in the
manual real-event source trial. Drawing-app acceptance and a complete, safe
persistent driver remain unresolved. This is a lab report, not an installer
step or a released pressure fix.

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
- The attended, subsequent real-event Mutter source trial received 310 pen
  samples in native GNOME GTK, spanning normalized pressure
  0–0.8005340657663844. It also received 147 finger events. The live readout
  identified source/tool as `pen` and reported a pressure axis. This is the
  first measured native-GNOME pressure result, not evidence of a default fix.

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

## Attended native-GNOME result

The owner returned to the tablet for a new manual launch of the same hashed
source trial. Startup password locking passed, and the installed ordinary
session script was restored atomically before testing. The full-screen dark
GTK test was visibly open after normal password login.

```
LIVE SUMMARY: tools=2 samples=310 pressure_min=0.0
pressure_max=0.8005340657663844
event_counts={'pen': 310, 'touchscreen': 147}
```

The pen's live axes included pressure, tilt, and distance; only pressure was
physically measured here. No coordinates, handwriting, or passwords were
recorded. The bounded trace showed an independent pen source, a registered
tablet and tool, and client focus during dispatch. This establishes native
GTK pressure delivery for the combined opt-in trial; it does not isolate which
individual source change was necessary.

First motion selection passed through Shell actors/Activities before client
focus appeared. Whether that was the existing app-preview activation flow or
an unresolved first-hover regression is not accepted yet. MyPaint was launched
through the normal unprivileged, single-worker/dockable-picker adapter for the
next physical check. Its canvas showed continuous strokes, and the owner
confirmed that pressure changes the brush response, but reported needing too
much force. Physical hover-out and production startup remain pending.

## MyPaint sensitivity preference

After the owner closed MyPaint normally, `tools/configure_mypaint_pressure.py`
was run as the existing desktop owner. It changes only MyPaint's standard
`input.global_pressure_mapping`, backs up the exact existing preferences,
preserves other keys, and atomically replaces settings with owner-only mode.
It refuses root, the wrong owner/config directory, unsupported MyPaint
versions, live MyPaint processes, invalid JSON and symlinked targets.

The initial lighter curve reaches full response at normalized raw pressure
0.5: output is `min(1, 2 * raw_pressure)`. Zero remains zero, so hover is not
converted to painting. MyPaint stores the curve's graph Y inverted; the knots
are `[[0,1],[0.5,0],[1,0]]`. Its installed native `MappingWrapper` verified
outputs 0, 0.10, 0.20, 0.50, 1, 1 and 1 for inputs 0, 0.05, 0.1, 0.25, 0.5,
0.8 and 1, respectively, within floating-point precision. The live-app guard
also refused a second write after MyPaint reopened.

MyPaint was reopened through the unchanged normal-user single-worker adapter
and loaded its saved settings/scratchpad. This is a persistent **app preference**,
not a hardware pressure change, drawing-engine patch, synthetic input, or
default native-GNOME pressure driver. The owner rejected the trial: it required
**even more force**, and drawing appeared multiple seconds behind the pen.
After another normal app closure the helper restored the original identity
knots `[[0,1],[1,0]]`, retaining backups and unrelated settings. Do not treat
mathematical mapping verification as comfort acceptance or recommend this curve.

## Drawing latency investigation

With MyPaint closed and the original curve restored, the native GNOME GTK
probe received 695 physical pen events spanning normalized pressure 0–0.728786.
Validated event timestamps compared against the local monotonic clock yielded
delivery age median **4 ms**, p95 **42 ms**, maximum **58 ms**. The timestamp
helper handles 32-bit wrap and refuses unknown/incompatible/stale clocks.
This measures delivery into a simple GTK client, not live MyPaint or
pen-to-pixel presentation, and does not by itself accept a lag fix.

Bounded headless, single-worker MyPaint tests used generated in-memory strokes,
not the owner's document. A simple brush rendered 384 points in 0.103 seconds;
the actual saved stock preset `classic/impressionism` took 0.155 seconds.
Eight full 1920×1200 **single-layer** pixbuf composites took 0.096 seconds total.
These workloads do not reproduce full live canvas complexity or GUI/desktop
presentation. Do not attribute all lag to the one-worker crash workaround.

The installed MyPaint freehand implementation queues motion and renders it
through a default-idle callback. A new attended, app-local probe measures pen
delivery age, positive-pressure queued-event age, stroke callback duration,
and canvas draw callback duration without retaining coordinates, pressure,
handwriting, or raw timestamps. Collection is bounded to 90 seconds and 20,000
numeric values per metric; wrappers restore without closing the app. It retains
the normal single-worker/panel adapter and makes no priority or package changes.
Its live results remain separate from the headless engine measurements.

The attended 90-second live run collected:

| Measurement | Samples | Median | p95 | Maximum |
| --- | ---: | ---: | ---: | ---: |
| Pen delivery age | 11,794 | 24 ms | 56 ms | 2,118 ms |
| Positive-pressure queued stroke age | 9,748 | 63 ms | 2,552 ms | 3,524 ms |
| Stroke-processing callback | 11,793 | 0.337 ms | 3.990 ms | 2,106.703 ms |
| Canvas draw callback | 499 | 25.485 ms | 32.511 ms | 89.446 ms |

The app really accumulated seconds of stroke backlog; one measured
stroke-processing callback also blocked for over two seconds. This narrows
the investigation to live stroke processing/queue scheduling rather than
assuming constant physical-input or canvas redraw delay. The callback includes
brushwork/undo bookkeeping as well as native brush rendering, so these timings
do not isolate the expensive substep. They are not presentation timestamps.
The probe printed its final summary and disabled collection/restored class
handlers; MyPaint remained open with no preference change.

The exact Ubuntu MyPaint source was fetched from an isolated, signed official
Noble universe source index into the original tablet build root. The index
did not replace the root's ordinary APT lists. The official upstream GIL fix
`356716e7bacfcbb1f3ab80171fea405fdd10b2b9` applied with zero fuzz and offsets.
Eight new development/asset packages were installed only in that build root,
with no upgrades/removals; the personalized clean root's installed app and
libraries were not changed. The extension-only build completed. The compiler
emitted a brush-directory macro quote warning, but the build linked and the
binding imported successfully. Provenance hashes are in
[PROVENANCE](../PROVENANCE.md).

The new extension and its generated Python binding were copied into a unique,
root-owned, non-writable RAM directory. The normal-owner
`tools/probe_mypaint_gil_trial.py` refuses root, a mismatched package, unsafe
stage paths/modes/types, unreviewed hashes, or a binding/extension loaded from
any other directory. It prepends only this process's `lib` package search path;
installed package files and the open GUI app remain unchanged.

Both one- and four-worker headless tests passed with that extension; the old
four-worker segmentation fault did not recur in this bounded test. Concurrent
initial runs rendered in 0.163/0.189 seconds and composited eight frames in
0.103/0.106 seconds respectively. These were overlapping jobs, not a fair
performance comparison or physical GUI acceptance. Do not increase the
ordinary app's worker count or claim the multi-second lag fixed from them.
The ordinary adapter still uses one worker.

Six later **sequential**, alternating fresh-process runs also passed, three
per worker setting. Median render times were 0.163470 seconds (one worker)
and 0.170601 seconds (four); median eight-frame composite totals were
0.092833 and 0.094753 seconds. This small workload showed no speedup. It
supports a bounded crash-fix result, not promotion of four workers for the GUI.

An unmodified-app follow-up, with optional profiling of its first 1,000 stroke
callbacks, caught a larger queue delay: positive-pressure queued-event age
maximum **5,572 ms**, p95 **4,662 ms**, while pen-delivery age maximum was
**141 ms** and the largest stroke callback **122.295 ms**. The current live
brush base values differed from the earlier saved stock-preset benchmark:
radius logarithmic 2.5, opacity 0.78, slow tracking 2.0, actual-radius dabs
3.24, basic-radius and per-second dabs both zero. The first 1,000 profiled
callbacks totaled 0.571116 seconds; native end-atomic work and content-change
notifications dominated that short profile. This did not reproduce the earlier
two-second single callback and does not isolate its original cause.

The new backlog with fresh event delivery and much shorter individual callbacks
makes low-priority queue starvation a concrete hypothesis. MyPaint sets its
motion processor to default idle priority 200; GTK redraw work runs at 120,
according to [GLib's priority documentation](https://docs.gtk.org/glib/const.PRIORITY_HIGH_IDLE.html).
A prepared `--queue-priority-trial` compares 35 seconds of unchanged scheduling
with high-idle priority 100 until 90 seconds. It retains every queued event,
replaces only this process's owned idle callback sources, leaves ordinary input
priority unchanged, and restores scheduling afterward. Metrics are reset at
the phase boundary. This is not a normal-launcher change or an accepted fix;
physical comparison remains pending.

The initial timed comparison was inconclusive: the baseline received strokes,
but the owner paused before the high-idle phase, which received zero pen or
stroke samples. Its priority restored to 200 and no conclusion was drawn. The
harness was corrected to wait for the first positive-pressure painting event,
and the owner's preferences/autosaves were preserved before replacing only the
verified diagnostic client.

That corrected control run measured:

| Default-idle measurement | Samples | Median | p95 | Maximum |
| --- | ---: | ---: | ---: | ---: |
| Pen delivery age | 5,282 | 31 ms | 68 ms | 467 ms |
| Positive-pressure queued stroke age | 5,253 | 7,405 ms | 11,404 ms | 11,685 ms |
| Stroke callback | 5,289 | 1.248 ms | 12.342 ms | 102.344 ms |
| Canvas draw callback | 339 | 25.042 ms | 31.995 ms | 84.235 ms |

The next client held priority 100 for its entire process lifetime, removing the
timing-window problem. It reported identical selected brush base values and:

| High-idle measurement | Samples | Median | p95 | Maximum |
| --- | ---: | ---: | ---: | ---: |
| Pen delivery age | 5,399 | 26 ms | 58 ms | 160 ms |
| Positive-pressure queued stroke age | 4,724 | 41 ms | 81 ms | 180 ms |
| Stroke callback | 5,434 | 0.262 ms | 2.035 ms | 21.111 ms |
| Canvas draw callback | 204 | 23.949 ms | 28.577 ms | 92.208 ms |

This confirms that continuous GTK redraw work was starving MyPaint's
default-idle stroke processor on this desktop. `ubuntu/t630-mypaint.py` now
sets only the exact-version app's stroke class to GLib high-idle before startup.
It verifies the original value 200 and GLib values 200/100, changes no input
priority, and refuses an unexpected contract. Diagnostics opt out so control
runs remain controls. Unit/integration tests and the full 315-test suite pass.

The adapter was installed atomically with SHA-256
`5a5b1836b37e4e62ad24307347177b4641282c46f2043851507543ce84f4e13d`.
The original helper is retained beside it with SHA-256
`e1d09ee8d3fb3c2404b532479c4b27c12a50929c86ec4f8f0192a09bfb078f0c`.
MyPaint package files, the global GTK scheduler, the input stack, pressure
curve, documents and normal startup for other applications were unchanged.
The steady test exercised the same priority and has since been closed. A normal
relaunch gets the setting from the installed adapter. Subjective feel and an
extended session remain separate acceptance gates.

On the next normal launch the owner reported pressure was much better, with
only slight remaining lag. The recorded brush bases mapped exactly to the stock
`classic/short_grass` preset, including deliberate `slow_tracking=2.0`.
Therefore that observation cannot be treated as residual system latency. After
the app's own corner close button failed, its exact PID, UID and command line
were verified before sending `SIGTERM`. A one-shot owner process preserved the
complete settings file as `settings-before-responsive-brush-*.json`, changed
only `brushmanager.selected_brush` from `classic/short_grass` to stock
`deevad/ballpen`, and relaunched through the normal helper. The selected control
preset is pressure-aware and sets both slow-tracking values to zero. The stock
preset files, global pressure curve, queue fix and user documents were not
changed. Physical comparison of that control remains pending.

## Hover-out source boundary

The exact installed Ubuntu Xwayland source `2:23.2.6-1ubuntu0.8` was downloaded
through the existing signed source index into the tablet's original build
root. No Xwayland binary was built, installed, or substituted in this step.
Its `hw/xwayland/xwayland-input.c` SHA-256 is
`882cfce4b731e65f073a9277acfb0d37c2a6a0b0e215e36fdf072a4b8062e40e`.
The inspected `tablet_tool_proximity_out()` clears the Wayland focus and cached
pressure/tilt values, but publishes no XInput proximity event or tool-property
change to the nested compositor. The source trial's lazy real-event tablet
initialization alone cannot supply this missing out-of-range notification.

A complete solution must carry the **real** host proximity transition into
nested tablet focus cleanup. Do not infer pen departure from zero pressure
(normal hover has zero pressure) or a quiet motion stream (the pen can be held
still). The [Wayland tablet protocol](https://cgit.freedesktop.org/wayland/wayland-protocols/tree/unstable/tablet/tablet-unstable-v2.xml)
also distinguishes pen proximity from tip-down/up and surface focus changes.
Source acquisition and inspection here do not accept a new lifecycle bridge.

Reference implementations:

- [Mutter 46.2 X11 seat](https://github.com/GNOME/mutter/blob/46.2/src/backends/x11/meta-seat-x11.c)
- [Mutter 46.2 Wayland tablet tool](https://github.com/GNOME/mutter/blob/46.2/src/wayland/meta-wayland-tablet-tool.c)
- [GTK3 Wayland input devices](https://github.com/GNOME/gtk/blob/3.24.41/gdk/wayland/gdkdevice-wayland.c)
