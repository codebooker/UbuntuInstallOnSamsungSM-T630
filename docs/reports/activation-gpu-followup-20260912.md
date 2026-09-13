# Application activation, Back, and GPU follow-up

## Application-launch bug fixed

DBus-activated Nautilus inherited `WAYLAND_DISPLAY=/run/user/0/wayland-0`
from the parent session bus. It opened on the outer Weston recovery desktop,
not inside GNOME. This was confirmed using its selected display environment,
the visible outer panel, and failure of host-X3 navigation keys to reach Files.
The same bug could affect other DBus-activated GTK applications.

The GNOME session launcher now waits for its nested Wayland socket, then updates
only `WAYLAND_DISPLAY=t630-gnome-0` and `GDK_BACKEND=wayland` on its private
session bus using the standard dbus-update-activation-environment utility.
No global bus, authentication policy, or credentials are changed. Compatibility
preloads/resource overlays are excluded from that utility invocation.

Applied live as well. Closed only the test Files instance and reactivated it
through its normal Application interface. New Nautilus PID4443 had the correct
nested display; its process-scoped polkit helper also attached. Screenshot
`back-inside-gnome-20260912.png` confirms it is inside GNOME.

The existing Back key mapping is already correct: gpio_keys158 -> XKB166 ->
XF86Back. No remap was needed. After opening `/usr/share/applications` from
Home, an injected XF86Back through the normal host X3 input path returned Files
to `file:///home/tablet`, verified using FileManager1 OpenLocations. This is
an automated event-path test, not yet a physical Back-button confirmation.

## GPU diagnostics

Installed Ubuntu glmark2-data, glmark2-es2-x11, glmark2-es2-wayland and
glmark2-x11 (2023.01+dfsg-1build2). No existing packages upgraded/removed.
Staged exact-stock GPU firmware using the existing guarded, read-only-partition
firmware helper. Software boots do not stage it automatically; the first test
failed initialization solely because a660_sqe.fw was not staged yet.

All rendering tests run as tablet UID1000, off-screen, through private X3,
with existing scoped Zink/Turnip wrapper. Desktop renderer defaults unchanged.

| Test | Result |
| --- | --- |
| Software GLES image validation | 27 success, 0 failure, 6 unknown |
| GPU GLES image validation | 21 success, 6 failure, 6 unknown |
| GPU desktop OpenGL image validation | 27 success, 0 failure, 6 unknown |
| GPU GLES1920x1200 stress, 2s per scene | All33 scenes completed, exit0, score660 |

Unknown means the benchmark has no validating result for that scene. Exit0
alone does NOT mean pixel validation passed. The GPU renderer identifies as
Zink over Adreno 7c+ Gen3/MESA_TURNIP, not llvmpipe; kernel calls it642Lv1.
Score660 is off-screen throughput, not physical display FPS or video decoding.
No new KGSL translation-fault/hang message matched in the kernel log. The
driver's reset_count changed during tests; its semantics have not been
established, so do not claim zero hardware resets.

GLES failures are in repeated conditionals/function/loop calculations; one
expected0xff252525 but got0xff1b1b1b. They do not occur in desktop GL or llvmpipe.
This suggests a precision-path difference, but is not proven to be a driver
bug or the cause of the earlier GNOME startup fault. Neither IR3_SHADER_DEBUG
nofp16 nor glmark's fragment-precision option changed the result. Debug output
still showed mediump under the latter option; the highp-named report is NOT
evidence that a genuinely high-precision shader was tested. No such overrides
were installed persistently. Original logs are alongside this report.

References used for diagnostic design:
[Mesa Freedreno/Turnip](https://docs.mesa3d.org/drivers/freedreno.html),
[glmark2 upstream](https://github.com/glmark2/glmark2).

## Bounded GPU startup supervision

Added normal-user `/usr/local/libexec/t630-gpu-session-watch`, used only when
the launcher selects GPU GNOME. It owns the exact GNOME child via Popen, waits
up to45s for that child's org.gnome.Shell bus ownership and a responsive standard
ScreenSaver query, then waits for normal process exit. A startup timeout fails
the attempt so the existing parent can retry software GNOME. Cleanup sends TERM
to its own child, waits5s, then KILL if necessary, with a bounded final wait.
No PID search/signaling of unrelated apps, kernel reset, or unlock call.
Readiness is NOT proof of rendering correctness; later hangs remain possible.

Four tests passed on the Mac and as the normal tablet user: normal child exit,
exit before readiness, unresponsive child ignoring TERM, unrelated child left
alone. The actual bus readiness probe also returned true for the running GNOME.
The GPU startup integration still needs an actual selected-GPU boot test;
software rendering remains selected by `/etc/t630/gpu.disabled`.

Original session launcher backup on tablet:
`/usr/local/share/t630/backups/gpu-startup-watch.GCLLMa`.
One clean software reboot dispatched to verify persistent activation correction.

## Clean reboot result

Boot `ad7c5d7e-a622-4809-9e1c-4f1de0a16210` passed. GNOME's startup log
confirmed password lock, and GetActive remained true before and after launching
a new Files service through DBus. That newly service-activated Nautilus reported
`WAYLAND_DISPLAY=t630-gnome-0`, proving the correction survived reboot.
Wi-Fi/SSH returned, the Power monitor started, speakers were unmuted, charging
was reported, and chrony corrected the clock to EDT once networking returned.
No password was entered remotely and no lock-deactivation call was used.

## Power observation

During this turn the existing monitor received actual Power off/on events,
logged verified password lock/backlight-off followed by restoration, and later
GNOME was unlocked. No remote unlock was issued. Physical darkness and the
owner's authentication experience have not yet been explicitly confirmed.
