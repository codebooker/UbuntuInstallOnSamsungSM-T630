# S Pen notes and drawing

Physical evaluation on the personalized Ubuntu 24.04 clean root, 2026-09-15:

- Xournal++ `1.2.2-2build3`: opens in nested GNOME; the physical test page contains
  continuous handwriting. Notes, PDF annotation, and pressure options are
  described in the [official guide](https://xournalpp.github.io/guide/).
- MyPaint `2.0.1-10build2`, labeled **MyPaint Drawing** in the launcher: opens maximized with dark GTK controls, a native
  canvas, and its brush/background assets. It is designed for drawing tablets;
  see the [upstream project](https://github.com/mypaint/mypaint).
- Krita `5.2.2`: not an accepted app on this desktop yet. Its upstream
  [startup code](https://github.com/KDE/krita/blob/v5.2.2/krita/main.cc#L492)
  explicitly refuses native Wayland. A bounded app-specific platform experiment
  reached that rejection dialog; the experiment was removed without a kernel
  restart. Do not advertise a working Krita launcher or bypass the rejection.

## Optional install

From this repository, **inside the configured tablet Ubuntu installation**:

```sh
sudo sh ubuntu/install-pen-apps.sh
```

The recipe installs native Ubuntu ARM64 packages and two account-neutral desktop
overrides. `t630-gnome-run` joins the existing owner's GNOME session and drops
administrator privileges before the app starts. `t630-pen-app` selects native
Wayland and dark GTK controls; it does not reset preferences or documents. The
Xournal++ paper itself retains the person's chosen paper/background settings.
MyPaint Drawing is kept in the app drawer by default. GNOME 46 removes pinned
favorites from that drawer, so the installer no longer auto-pins it. Desktop
runtime 0.1.3 preserves the owner's favorites instead of resetting them.
This optional evaluation recipe is not yet in the exact-version release set.
The launcher now uses the installed upstream `org.mypaint.MyPaint` icon; the old
`mypaint` icon name did not resolve on the clean root. After a renewed report
that the app was absent, owner-session registration, non-favorite state, and the
corrected icon were checked. After the owner pressed Home, the live screenshot
confirmed **MyPaint Drawing at the upper-left of the first app-grid page**.
Launching it by tapping that tile remains separate from visibility acceptance.

## Ubuntu 24.04 first-stroke crash workaround

The installed MyPaint 2.0.1 extension has a known OpenMP/Python-locking crash.
See the [upstream report](https://github.com/mypaint/mypaint/issues/1253) and
[proper upstream fix](https://github.com/mypaint/mypaint/commit/356716e7bacfcbb1f3ab80171fea405fdd10b2b9).
This tablet reproduced a segmentation fault both in the GUI and in a bounded
headless render test with four workers; the same 384-point test passed with one.
`t630-pen-app drawing` now sets **only MyPaint's** `OMP_NUM_THREADS=1` before
launch. This serializes rendering and may reduce performance; no system-wide
thread setting, driver change, or library bypass is used. Close/reopen any
already running copy to pick up the workaround. Physical drawing acceptance
of continuous strokes/pickers passed, but responsive pressure drawing remains pending.

A later isolated exact-version source build with the upstream GIL fix passed
both one- and four-worker headless tests. It was loaded only in private
normal-owner test processes with pinned RAM-artifact hashes, not installed over
the distro app. The small workload did not establish a performance improvement;
physical GUI acceptance and safe packaging remain pending. The ordinary
launcher still uses one worker. See the [measured follow-up](reports/pen-pressure-path-20260915.md).

`tools/probe_mypaint_strokes.py --threads 1` tests the native drawing engine on
an in-memory surface, not the display or physical pen. Its four-worker comparison
is expected to crash on this unpatched build; the probe disables core dumps and
has CPU/time bounds. It writes no document or GUI/input event.

## Experimental chooser-popup input workaround

The single-worker workaround does not fix MyPaint's separate
[Wayland chooser-popup freeze](https://github.com/mypaint/mypaint/issues/1161).
The live app logged the matching GDK grab warning when the owner reported touch
and pen becoming unresponsive. Its autosave cache was copied into a unique
`Documents/MyPaint-recovery-*` directory before only that app was terminated.

The optional launcher now uses `t630-mypaint`, a version-guarded, app-local UI
adapter. Brush and color quick selectors reveal MyPaint's existing dockable
brush-group and HSV-wheel panels instead of popup windows with input grabs.
It leaves installed package files, documents, preferences, the desktop, and
Xournal++ unchanged. It refuses root, the wrong Wayland display, unsupported
chooser types, and MyPaint versions other than `2.0.1-10build2`; review/update
the adapter before upgrading that package. Normal file arguments are retained.
Startup and unit tests pass, and the owner confirms physical touch and S Pen
respond again. The owner then confirmed the requested long-stroke and brush/color
control check works. This accepts that bounded drawing/picker check, not extended
session reliability, pressure, palm rejection, or save/reopen. See the
[input-freeze investigation](reports/mypaint-popup-input-20260915.md).

## Pressure investigation

The private rootful Xwayland host advertises six stylus valuators, including
`Abs Pressure` with range 0–65535. The nested GNOME GTK inventory initially showed
only X/Y tablet axes and did not expose the actual stylus device. Mutter 46's
[device classifier](https://github.com/GNOME/mutter/blob/46.2/src/backends/x11/meta-seat-x11.c#L583)
recognizes `pen`/`wacom`, but not the host name `xwayland-tablet stylus:14`, unless
the explicit Wacom tool-type property exists. Its tool tracking also expects
serial metadata.

`ubuntu/t630-pen-x11-metadata.py` is an **experimental, nonpersistent diagnostic**.
It identifies only the complete private stylus/eraser/cursor set and checks
pressure capabilities before assigning explicit tool-type and software serial
metadata. A live `--refresh` refuses a physical pen in proximity and re-enumerates
only those software tablet devices, always re-enabling them. Serial metadata is
published **after** re-enumeration so Mutter updates the replacement device's
current tool rather than a device it is about to remove. It needs the USB
administrator for the read-only physical-pen idle check; do not widen input-device
permissions to run it as the normal owner. No device grabs or synthetic strokes
are used. It made the stylus visible to inner GTK, but pressure axes were still
unconfirmed before the next physical stroke. It is not a startup hook.

`tools/probe_gdk_pen.py`, launched through `t630-gnome-run`, inventories device
names, sources, and axis capabilities without recording handwriting. Neither
the inventory nor continuous constant-width handwriting proves pressure works.
GTK3 [clones tool axes on proximity-in](https://github.com/GNOME/gtk/blob/3.24.41/gdk/wayland/gdkdevice-wayland.c),
so an idle client's X/Y-only inventory does not prove that pressure was lost.
Use `--window` for a bounded 30-second physical proximity/pressure check; it
records only tool capabilities and aggregate pressure, not handwriting or
coordinates. The corrected September 15 probe confirmed varying pressure in
the parent X11 session, but the native GNOME test still received no usable pen
samples even though finger events arrived. A subsequent opt-in Mutter source
handoff trial received **310 physical native-GNOME pen samples**, normalized
pressure **0–0.800534**, and **147 finger events**. This confirms pressure in
the native GTK test, not a safe
persistent driver. The older proximity preloads remain removed, and no pressure
experiment is enabled at normal startup. See the
[pressure-path report](reports/pen-pressure-path-20260915.md) for the measured
boundary and rejected trials.

In that attended source trial the owner also confirmed MyPaint responds to
pressure, but required excessive force and had multi-second drawing lag.
A 2×, capped app-local pressure curve was verified mathematically, but the
owner reported needing **more** force. After normal app closure, its original
identity curve was restored with an exact preferences backup. Do not recommend
that failed sensitivity trial or press harder to compensate. Drawing latency
must be resolved before further comfort tuning; neither trial makes the
experimental GNOME handoff persistent.

For optional sensitivity adjustment after pressure delivery works, close
MyPaint normally first, then run as the existing desktop owner:

```sh
t630-gnome-run python3 tools/configure_mypaint_pressure.py --full-pressure 1.0
```

Use an absolute path to the tool if the repository is not in the owner's
home directory. Smaller thresholds mathematically amplify pressure, but the
0.5 trial worsened the owner's experience on this desktop. `1.0` restores the
identity pressure curve. The helper supports 0.2–1.0, keeps other preferences,
backs up the old settings alongside `settings.json`, and refuses live app
changes. You can also adjust MyPaint's normal pressure curve in Preferences.
This tool is not an installer default and does not configure Xournal++ or
alter the physical pressure axis. Do not compensate by pressing unusually hard.

The event-age extension to `tools/probe_gdk_pen.py` received 695 physical pen
events with median delivery age 4 ms, p95 42 ms, and maximum 58 ms. This is
event delivery to a simple GTK client, **not pen-to-pixel latency in MyPaint**.
The headless engine rendered 384 points with the selected stock
`classic/impressionism` brush in 0.155 seconds; eight 1920×1200 single-layer
composites took 0.096 seconds total. These small generated workloads do not
measure the live document, GUI stroke queue, or nested desktop presentation.
`tools/probe_mypaint_latency.py` is an attended, version-guarded app-local
diagnostic of delivery age, queued stroke age, and callback durations. It
stores only bounded numeric aggregates, restores its wrappers after 90 seconds,
and leaves the app open. It changes no scheduling priority, pressure curve,
package, input event, or document **by default**. Empty samples are inconclusive.
Its optional `--profile-strokes` captures function-call aggregates for the
first 1,000 stroke callbacks (with added profiling overhead), not call arguments
or handwriting. The probe also reports only selected numeric brush base values
to separate the live brush configuration from the stock-preset benchmark.
The explicit `--queue-priority-trial` instead tests unchanged scheduling for
35 seconds, then temporarily gives only MyPaint's stroke idle callbacks priority
100 rather than 200. It reschedules owned callbacks without dropping queue
data, compares phase-specific metrics, and restores at 90 seconds. Do not use
it together with profiling or treat this pending comparison as an installer
default. A follow-up caught 5.572 seconds of queued stroke delay despite fresh
pen delivery and short individual callbacks; scheduling is a hypothesis, not
yet an accepted fix.

The first timed comparison did not receive strokes in its high-idle phase and
was discarded. A corrected first-stroke-triggered control run then measured
**7,405 ms median / 11,404 ms p95** queued-stroke age over 5,253 samples under
MyPaint's default-idle priority 200. A separate steady high-idle process used
the same reported brush bases and measured **41 ms median / 81 ms p95** over
4,724 samples. Pen delivery stayed fresh (58 ms p95), stroke callbacks were
short (2.035 ms p95), and 204 canvas draw callbacks completed during that run.

The exact-package adapter now sets only `FreehandMode.MOTION_QUEUE_PRIORITY`
to GLib high-idle 100 before the application starts. GTK documents its resize
and redraw work at 110 and 120, so this drains stroke work before redraws without
changing normal input priority. The adapter verifies all three expected values
and refuses changed contracts. Diagnostics set a private process flag so they
retain explicit control over their own baselines. The previous adapter is kept
beside the installed helper as an exact rollback copy; neither MyPaint package
files nor preferences were replaced. The attended test kept the accepted
priority active after metrics stopped; it has since been closed, and future
normal launches receive the setting from the adapter. Subjective feel and
longer-session acceptance remain pending.

Standard owner folders are now initialized with `xdg-user-dirs-update` without
replacing chosen paths. Before the restart, the existing Xournal++ autosave was
preserved as `Documents/T630-pen-test-before-restart.xopp`; its compressed data
verified and the file survived restart. Opening it again in Xournal++ and the
`.ora` drawing save/reopen test still require acceptance.

`tools/probe_mypaint_roundtrip.py` performs a bounded, normal-owner native file
test without changing the live canvas. It creates a unique
`Documents/MyPaint-file-check-*` folder with generated strokes, checks the
OpenRaster archive, reloads it, and verifies canvas-frame/settings persistence.
The live 256-point test passed those checks. Rendered pixels were **not**
bit-identical: maximum byte difference 3/255, mean 0.163541/255. The probe reports
this separately and does not accept exact fidelity, GUI save/reopen, physical
pressure, or post-restart persistence. Internal empty tile allocation can change
on loading and is not treated as the document's saved canvas frame.

## Acceptance still required

1. Light-to-firm strokes change thickness when pressure is enabled.
2. Long strokes remain continuous with pen-tip drag and normal palm contact.
3. Pen-button tool changes work without leaving a pressed/grabbed state.
4. All orientations retain correct coordinates and usable controls.
5. Save a `.xopp` note and `.ora` drawing; reopen after an orderly restart.
6. Verify the accepted settings survive suspend/resume and startup before
   adding the apps or metadata integration to the release recipe.
