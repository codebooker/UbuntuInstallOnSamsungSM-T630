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
When an owner GNOME session is running, the updated installer also pins MyPaint
Drawing to the dock without replacing existing favorites. Desktop runtime
0.1.3 preserves those favorites on later startup instead of resetting them.
This optional evaluation recipe is not yet in the exact-version release set.

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
coordinates. The current live tests received no usable pen samples and are
**inconclusive**, not pressure failures or passes. Metadata remains experimental
and is deliberately absent after restart.

Standard owner folders are now initialized with `xdg-user-dirs-update` without
replacing chosen paths. Before the restart, the existing Xournal++ autosave was
preserved as `Documents/T630-pen-test-before-restart.xopp`; its compressed data
verified and the file survived restart. Opening it again in Xournal++ and the
`.ora` drawing save/reopen test still require acceptance.

## Acceptance still required

1. Light-to-firm strokes change thickness when pressure is enabled.
2. Long strokes remain continuous with pen-tip drag and normal palm contact.
3. Pen-button tool changes work without leaving a pressed/grabbed state.
4. All orientations retain correct coordinates and usable controls.
5. Save a `.xopp` note and `.ora` drawing; reopen after an orderly restart.
6. Verify the accepted settings survive suspend/resume and startup before
   adding the apps or metadata integration to the release recipe.
