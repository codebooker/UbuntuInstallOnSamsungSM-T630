# MyPaint chooser-popup input freeze — 2026-09-15

The owner reported glitching and loss of touch/S Pen responsiveness after the
single-worker drawing workaround. SSH still answered; GNOME's lock was initially
inactive and the display was unblanked. The MyPaint process remained alive rather
than crashing. Its local log contained:

> already mapped at time of grabbing

The full diagnostic warned about `gdk_seat_grab()` and window mapping. The
[upstream Wayland popup issue](https://github.com/mypaint/mypaint/issues/1161)
reports the same warning and chooser-related freezes. This is evidence for an
app grab fault, not proof of a new touchscreen hardware/driver failure.

## Bounded recovery

Checked the exact process command and normal-owner UID before targeting it.
Copied its approximately 1 MiB autosave cache into the unique directory
`/home/user/Documents/MyPaint-recovery-jgmzhx_x/autosave-cache`, then sent SIGTERM
to only that MyPaint process. Originals were neither removed nor overwritten.
No private artwork/core was uploaded or committed, and no tablet restart or
other application closure was required. These cached files have not yet been
accepted as a successfully reopened drawing.

## Experimental app-local UI adapter

`ubuntu/t630-mypaint.py` runs the normal `/usr/bin/mypaint` entrypoint, with its
single-worker setting and native Wayland retained. Only inside that process,
`ChooserPopup.popup` is replaced with a function revealing existing workspace
tools:

- Brush chooser: `MyPaintBrushGroupTool` with the selected group.
- Color chooser: `MyPaintHSVWheelTool`.

This avoids the quick chooser's popup/grab path; it does not synthesize input,
disable session security, patch installed MyPaint library files, or reset owner
preferences. Unknown chooser types fail closed. The adapter requires normal-owner
execution, `t630-gnome-0`, and exact native package `2.0.1-10build2`. Other MyPaint
dialogs are unchanged: this is not a claim that every possible grab is fixed.

The optional pen-app installer now installs the adapter and its drawing launcher
uses it. The live selected clean root was updated and one adapted MyPaint copy
started successfully, with the adaptation notice and normal GTK device inventory
in its local log. No kernel, boot image, release-package version, or global
environment change was made.

All 254 discovered tests completed (250 passes, four skips), including panel
mapping, refusal guards, normal entrypoint execution, and app-only environment
tests. These mocks and startup checks do not exercise physical picker clicks.

## Acceptance outstanding

The owner must confirm restored input, continuous drawing, and both quick
selectors opening usable side panels without freezing touch/pen. Pressure,
palm rejection, rotation, and drawing save/reopen remain separate gates.
During the later screen check, the preview was black because display status
reported `blanked: true` and GNOME ScreenSaver reported active. That observation
is consistent with normal idle lock, not by itself a desktop hang. Authentication
was not bypassed or the idle policy overwritten.
