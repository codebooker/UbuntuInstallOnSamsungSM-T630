# GNOME desktop work — 2026-09-12

## Milestone

GNOME Shell 46 / Mutter 46.2 renders the full 1920x1200 display as the normal
`tablet` user. The owner confirmed: "keyboard comes up and works with touch
and pen". App launching, GNOME Settings and Terminal/htop are also visible.
It is still nested inside private rootful Xwayland on Weston, not a replacement
for the physical compositor. No boot image, partition, calibration or boot
default changed. Weston/Maliit remains the recovery fallback.

GNOME's own Wayland socket is `t630-gnome-0`; Mousepad's process environment
was checked. Settings authorization, audio, suspend and session management
remain incomplete: outer PID 1 is BusyBox, without logind. The user password,
SSH keys and Wi-Fi configuration were not changed.

## Rendering fault and actual fix

The preview clipped all drawing below row 480. Mesa 25.2.8's
`src/egl/drivers/dri2/platform_x11.c`, `swrastPutImage2`, clamps transmitted
height to cached `_EGLSurface.Height`. That value retained the initial 480
pixels after the X window and Cogl framebuffer resized.

`eglQuerySurface` updates cached dimensions from the X drawable. The scoped
`t630-cogl-sync.so` queries width/height immediately before
`cogl_onscreen_swap_buffers`. This fixed 1600x1000 windowed and 1920x1200
full-screen output. It does not read pixels, log screen contents or change
input. Source: `tools/t630_cogl_sync.c`; deployed source in
`/usr/local/share/t630/`, library in `/usr/local/lib/`.

An early XPutImage chunking test appeared successful because the diagnostic
probe also called eglQuerySurface. Chunking alone, glFinish alone and pixel
readback alone did NOT fix the fault. Chunking/probe sources are retained as
diagnostics only and are NOT used by the normal launcher. llvmpipe/softpipe,
X11/nested Wayland, clipping flags, resizes and disabling MIT-SHM were tested.
The active fix is the EGL size refresh, not the transfer-size hypothesis.

## Packages and launchers

Ubuntu apt packages were installed with policy-rc.d preventing unsolicited
service startup. GDM is not installed/enabled. Package baseline lives in
`ubuntu/install-gnome-preview.sh`. Diagnostic extras: mesa-utils and xdotool.
at-spi2-core and gnome-backgrounds were added.

Root launch over existing key-only SSH:

```
nohup env T630_GNOME_FULLSCREEN=1 /usr/local/bin/t630-gnome-preview \
  </dev/null >/run/t630-gnome-preview.log 2>&1 &
```

The wrapper drops to UID 1000 before starting the desktop. Settings/data/cache
use isolated `t630-gnome-preview` directories. Xwayland :3 uses a generated
0600 authorization file and `-nolisten tcp`; no network port opens. The wrapper
owns and cleans up only its GNOME/Xwayland children.

To return to Weston, inspect `pgrep -a gnome-shell` and send the specific GNOME
PID SIGTERM. Do not kill Weston. One unmapped, black startup did not honor
SIGTERM; after confirming it had no user apps, that failed process was stopped
with SIGKILL. Never forcibly close a working session with unsaved documents.

## Remaining work

- Explicit US keyboard input source replaces the previous empty source list.
- The visible `Keyboard` top-bar toggle is installed, enabled and ACTIVE.
  Both open and hide actions were verified in live frames; it is a normal GNOME 46
  extension, scoped to the preview data directory. It does not change physical
  calibration or bypass access controls. Source: `ubuntu/gnome-tablet-tools/`.
- Basic desktop setup controls now include a `GNOME desktop` launch button.
  This is a manual entry point; boot defaults remain unchanged.
- An image-background startup stalled; flat purple is used at startup. Setting
  an image after startup worked, but that is not yet the startup default.
- Synthetic XTEST input triggered drag-state errors and became unreliable.
  The owner's direct touch/pen keyboard confirmation is the input evidence.
- Screen capture briefly caches frames; immediate captures can be stale.
- Battery rose from 17% to 19% and remained charging; brightness unchanged.
- No GNOME boot default or direct DRM session has been enabled yet.

The S9 Ultra project informed userspace choices; no hardware scripts were run.
Mesa code was inspected at mesa-25.2.8 and GNOME Shell code at 46.0.

## Reproducibility

The working EGL refresh library was compiled on the tablet using:

```
gcc -shared -fPIC -O2 -Wall -Wextra -Werror \
  /usr/local/share/t630/t630_cogl_sync.c -ldl \
  -o /usr/local/lib/t630-cogl-sync.so
```

Do not overwrite an in-use mapped library; build to a new filename and rename
it between preview sessions. A matching local binary is in
`output/t630-cogl-sync.so`.

- Library SHA256: `7f4b3906acdad986823ad141ad533facd415af051df5982e4c5363315016ffed`
- Source SHA256: `5cba815c7fddc3ecc995b49c9625b7c5919b83342f978501dfd03c54c2d35624`
- Package audit clean; shell syntax checks passed for both launchers and app
  dispatcher. The final session restarted successfully after extension install.
- Settings (Sound) and Terminal/htop were reopened after the reload. The final
  desktop stayed fully rendered with the keyboard hidden. Audio devices remain
  absent in Settings and are not claimed working.
