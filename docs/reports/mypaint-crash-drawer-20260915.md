# MyPaint first-stroke crash and drawer visibility — 2026-09-15

The owner reported MyPaint disappeared when touched and was absent from the app
drawer. The previous dock pin caused the visibility regression: GNOME 46's
[AppDisplay filter](https://github.com/GNOME/gnome-shell/blob/46.0/js/ui/appDisplay.js#L1414)
excludes favorites. Removed only `mypaint.desktop` from the live favorite list;
the normal installed MyPaint Drawing desktop entry remains visible through Gio.
The optional installer no longer auto-pins it. Personal favorites and folders
otherwise remain untouched.

## Crash reproduction

Reopened MyPaint detached from SSH with a dedicated local log and core dumps
disabled. It subsequently disappeared with `Segmentation fault` and
`MYPAINT_EXIT=139`. This is a real app crash, not evidence of a tablet reboot.
The pre-existing `/home/user/core` was identified as an older internal Xwayland
crash, not MyPaint; it was neither uploaded nor deleted.

A bounded headless probe renders 12 rows / 384 generated points into a private
in-memory tiled surface, without GUI input or user files:

- Four OpenMP workers: segmentation fault, exit 139.
- One worker: exit 0, `HEADLESS_RENDER_PASS`, nonempty 384×320 bounding box.

The [upstream issue](https://github.com/mypaint/mypaint/issues/1253) and
[Debian aarch64 report](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=1079663)
describe this package crash and the one-worker workaround. The
[upstream fix](https://github.com/mypaint/mypaint/commit/356716e7bacfcbb1f3ab80171fea405fdd10b2b9)
acquires Python's GIL around tiled-surface callbacks and yields it during native
render calls. Our results are consistent with that known fault; no local native
backtrace was collected or private core uploaded.

## Scoped workaround

The optional tracked pen-app launcher now overrides `OMP_NUM_THREADS=1` for
MyPaint only, retaining native Wayland, dark controls, file arguments, and the
normal owner. Notes and the desktop do not get this override. The installed
launcher was updated and MyPaint reopened after the uncorrected copy crashed.
The sole reopened MyPaint process was checked without printing its environment:
`OMP_NUM_THREADS=1` was present. The live overview showed its canvas thumbnail.
Corrected physical strokes remain to verify; the headless pass alone does not
prove touch, pressure, palm rejection, save/reopen, or full GUI reliability.

No kernel/image/package-version change or system-wide OpenMP environment change
was required. The proper patched native package is preferable long term; the
single-worker workaround deliberately trades parallel performance for a bounded
fix using the currently installed native package.

All 251 discovered tests completed successfully (247 passes, four skips),
including the launcher test that requires the drawing-only OpenMP override and
leaves the notes launch environment unchanged.
