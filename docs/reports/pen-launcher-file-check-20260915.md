# Pen launcher and native file check — 2026-09-15

After confirming touch/S Pen recovery and long strokes/brush/color controls, the
owner again reported MyPaint missing from the launcher. In the normal selected
GNOME session, Gio enumerated `mypaint.desktop` as `MyPaint Drawing`, with
`should_show=True` and the guarded pen-app helper executable. It was not in
favorites; `app-picker-layout` still contained its page-zero position-zero entry.
Only the empty flat-layout sentinel remained in the folder list. Those checks do
not prove Shell's current rendered tile is visible.

The desktop override used `Icon=mypaint`, but the native package installs
`org.mypaint.MyPaint.svg`. Corrected the tracked and live entry to
`Icon=org.mypaint.MyPaint` and refreshed the desktop database. Owner-session GTK3
confirmed the corrected icon resolves. No personal favorites, folder order,
application layout, or running drawing was reset. The view-only screenshot still
showed the canvas, not the app grid; requested that the owner open the grid.
Visible placement and a launch from the tile remain pending. The missing icon is
a demonstrated defect, not yet a demonstrated explanation for the missing tile.

## Native OpenRaster persistence probe

Added `tools/probe_mypaint_roundtrip.py`, using the installed native MyPaint
document engine as the normal owner with one OpenMP worker, core dumps disabled,
and CPU/wall-clock bounds. It creates a unique diagnostic directory and renders
256 generated points on an isolated `painting_only` document. It neither reads
user artwork nor touches the live canvas, preferences, input, or autosaves.

Initial strict checks exposed two distinctions:

- Allocated empty tiles were trimmed on loading: internal data bounds changed
  from 320×256 to 320×192. The final probe instead sets and verifies an explicit
  saved 320×256 canvas frame, then compares that same region's pixels.
- Rendered pixels were not byte-identical. The probe reports fidelity metrics
  independently, rather than silently accepting equality or tuning a tolerance
  to produce a pass.

Final live result:

```text
OPENRASTER_LOAD_PASS: generated_points=256 bbox=320x256
PIXEL_COMPARISON: identical=False max_byte_error=3 mean_byte_error=0.163541 changed_bytes=47918
```

Archive CRC/mimetype, document setting, saved frame, and pixel geometry checks
passed. The generated diagnostic file remains at
`/home/user/Documents/MyPaint-file-check-ldmv_462/generated-strokes.ora`.
Earlier generated diagnostic folders were also retained; no artwork was uploaded
or committed. No exact-fidelity, GUI save/reopen, or restart-persistence pass is
claimed. The small pixel differences have not been assigned a verified cause.

Idle GTK enumeration still showed X/Y-only pen axes. That is inconclusive because
tool axes may be populated at proximity-in; no physical pressure samples were
collected in this check. No pressure driver/metadata changes were made.

All 255 discovered tests completed successfully (251 passes, four skips),
including the launcher icon/guarded-entry regression test. The native file probe
was run separately on the tablet. No image/kernel build or boot change occurred.
