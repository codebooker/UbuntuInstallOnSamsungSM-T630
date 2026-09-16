# Xournal++ palm-rejection repair — 2026-09-16

## Trigger

The owner reported that finger drawing was disabled but moving a resting palm
still moved the page. That is not palm rejection and was not counted as an
accepted pen-app result.

## Cause

The installed Xournal++ version is `1.2.2-2build3`. In the matching upstream
`v1.2.2` source, `InputContext::handle()` sends touchscreen events to the normal
touch handler when touch drawing is off. The setting prevents ink, not page
pan/zoom.

Xournal++ has a separate `HandRecognition` path. With `disableTouch=true`, each
pen or eraser event blocks the app's touchscreen device. A timer re-enables it
after the configured quiet period. The internal `InputContext` block is called
on Wayland even when no X11-wide `TouchDisableX11` implementation is selected.

Upstream references:

- [`InputContext.cpp` at v1.2.2](https://github.com/xournalpp/xournalpp/blob/v1.2.2/src/core/gui/inputdevices/InputContext.cpp)
- [`HandRecognition.cpp` at v1.2.2](https://github.com/xournalpp/xournalpp/blob/v1.2.2/src/core/gui/inputdevices/HandRecognition.cpp)

## Live repair

The only running normal-owner Xournal++ process was closed with `SIGTERM` so it
could finish writing preferences. The profile then contained Xournal++'s empty
default `<data name="touch"/>`. Its exact settings file was backed up as:

```text
/home/user/.config/t630-gnome-preview/xournalpp/settings.xml.before-palm-rejection-20260916-000053
```

The replacement was XML-validated before Xournal++ was relaunched:

```xml
<data name="touch">
  <attribute name="disableTouch" type="boolean" value="true"/>
  <attribute name="method" type="string" value="auto"/>
  <attribute name="timeout" type="int" value="1000"/>
</data>
```

No system-wide touchscreen, compositor input mapping, or kernel input device was
disabled. Finger interaction outside Xournal++ remains unchanged.

## Reproducible default

`t630-xournalpp-defaults` now runs before the notes app. Once per account it:

1. refuses root and non-regular or foreign-owned settings files;
2. validates a bounded XML settings file;
3. enables internal hand recognition only if the setting has no value;
4. preserves an exact pre-edit backup;
5. atomically replaces the settings file; and
6. writes an owner-only state marker so later user choices are never forced.

An explicit existing `true` or `false` is preserved. A fresh account receives a
minimal valid settings file; Xournal++ supplies and later saves all other normal
defaults. Parse or safety failures preserve the file and do not prevent the app
from opening.

The live launcher and helper hashes matched the tracked files after installation.
The full repository suite passed: 319 tests, 5 skipped.

## First physical result: failed

With internal hand recognition loaded, the owner placed a palm on the display
and confirmed that it still moved the paper. App-level touch suppression is not
accepted as the solution.

Udev showed why the system-level arbitration path was incomplete:

```text
sec_touchscreen LIBINPUT_DEVICE_GROUP=18/0/0:sec_touchscreen
sec_e-pen      LIBINPUT_DEVICE_GROUP=18/0/0:sec_e-pen
```

[Libinput's tablet-touch arbitration](https://wayland.freedesktop.org/libinput/doc/1.25.0/tablet-support.html)
associates the integrated touchscreen and digitizer through their device group
and discards touch while a tool is in proximity. The tracked
`99-t630-input.rules` now assigns both exact device names:

```text
LIBINPUT_DEVICE_GROUP=t630-integrated-pen-touch
```

`udevadm test` resolved that value for `/sys/class/input/event5` and `event7`.
After an orderly restart, the live udev database reported the shared value for
both nodes; Weston, nested GNOME, and Xournal++ restarted normally. This changes
association metadata only: it does not grab, inject, or record input and does
not disable the touchscreen permanently.

## Remaining physical gate

Bring the pen into proximity first, then rest and move the palm while drawing;
the page must remain fixed. After moving the pen out of proximity, deliberate
finger scrolling must work again. This report does not mark that gate passed
until the owner confirms both.
