# Isolated GNOME acceleration and recovery tests

## Recovery changes

The GPU GNOME supervisor previously checked startup readiness only. It now
continues checking the exact owned child's bus identity and ScreenSaver response
every five seconds. Three consecutive failures trigger bounded TERM/KILL of
that child and return failure to the existing software-fallback launcher.
Transient failures reset on a healthy response. No unrelated processes, unlock
calls, kernel resets, or authentication changes are involved. Six tests passed
on both Mac and tablet, including post-startup hangs and transient failures.

The process-scoped GPU wrapper now sets MESA_VK_ABORT_ON_DEVICE_LOSS=1. A known
lost Vulkan device should exit instead of leaving the desktop waiting forever.
This cannot detect every fault: a kernel-recovered rendering fault may not be
reported to Vulkan and GNOME may remain responsive. The kernel test below proves
why bus responsiveness alone must not be considered a graphics pass.

Backups: `/usr/local/share/t630/backups/gpu-runtime-watch.lKCPRv` contains the
previous supervisor and GPU wrapper. Software rendering is still the default;
`/etc/t630/gpu.disabled` is unchanged.

The non-secret `/etc/t630-install-id` marker was root:root0600, so the normal-user
GPU supervisor would fail its exact-device check with PermissionError. After
verifying a regular non-symlink file with the exact expected marker, changed it
to root:root0644. It is still writable only by root. No credentials were read or
permissioned differently.

## Invisible test setup

Installed only Ubuntu's xvfb package, version2:21.1.12-1ubuntu1.6; no upgrades or
removals. `ubuntu/test-t630-isolated-gnome.py` creates a private1920x1200 Xvfb
display with an authentication cookie and no TCP listener, a private D-Bus
session, temporary HOME/config/data/cache/runtime, and a second GNOME as UID1000.
It never replaces or unlocks the physical GNOME desktop. No private user apps
or documents are opened. Test-process cleanup is scoped to its own process group.
The shared kernel GPU is not fault-isolated: kernel faults remain possible.

Tests use the same isolated25.2.8 KGSL Turnip and packaged25.2.8 Zink, CPU-copy
presentation, and the existing Cogl size-refresh preload. GNOME extensions are
disabled in the empty test profile. First tests omit nested Xwayland; the final
variant includes it, with XWAYLAND_NO_GLAMOR=1 as in the real session.

For each successful startup, hold for30seconds and make11 bus checks. The updated
test alternates Escape/Super+A only on the private X server, hashes central image
pixels excluding the clock, and saves one private-display screenshot. A render
test requires multiple distinct images as well as bus responses and expected
GPU library mappings. Kernel review is separately required. The initial test
incorrectly used “passed” for responsiveness alone; the revised output explicitly
separates responsiveness_pass, redraw_pass, and requires_kernel_and_image_review.

## Warm-boot comparisons

Boot `01bf77c3-1d54-4f93-bfb8-6c7bfbe9834c`; real GNOME PID1100 stayed software
rendered and password-locked throughout. GPU firmware was staged with the
existing exact-stock helper; APNHLOS was mounted read-only and unmounted again.

| Test | Evidence |
| --- | --- |
| Software control, PID3203 | 11 responsive checks, clean owned-child shutdown |
| First GPU, PID4051 | Null-address GPU write translation fault in UCHE; hang/context skip recorded. GNOME nevertheless kept responding and produced a recognizable overview image. **Not a graphics pass.** |
| GPU sysmem, PID4830 | 11 responsive checks, no additional page fault in kernel log |
| GPU default redraw repeat, PID5634 | 11 responsive checks,2 distinct frames, no additional page fault |
| GPU sysmem redraw, PID6234 | 11 responsive checks,2 distinct frames, no additional page fault |
| GPU sysmem with Xwayland, PID6824 | 11 responsive checks,2 distinct frames, no additional page fault |

The initial fault appeared at boot618.032693seconds: addr0, pid4051,
`context=gfx3d_user`, `write translation fault`, `UCHE: Not HLSQ`. Its image was
not wholly blank, illustrating that screenshots alone also miss faults. Kernel
evidence: `isolated-gpu-kernel-20260912.log`. Images:
`isolated-gnome-gpu-baseline-20260912.png` and
`isolated-gnome-sysmem-redraw-20260912.png`.

The later default test also passed, so the sysmem result does NOT yet establish
a fix. The reset_count sysfs value increments around ordinary context/power
lifecycle and is not treated as a count of proven fault resets.

## Cold-start test

A clean unmount-first reboot was dispatched at21:17:18EDT, retaining software
desktop startup. The next GPU workload will use sysmem immediately after fresh
firmware staging. Its result is pending.

Cold boot `31eb9aff-56d1-4367-9da7-f122a4bd0c7c` returned to software GNOME1102.
Networking took longer than the usual window; the owner reconnected USB, and
both SSH and serial were then verified. GPU reset_count was0 before any test.
First GPU workload on this boot used sysmem with Xwayland, PID2263:11 responsive
checks,2 distinct central-image hashes, correct GPU library mapping, no GPU page
fault in the kernel log. This establishes one clean first-GPU-use sysmem trial,
not broad stability across arbitrary workloads.

## Full-screen live test and verified fallback

Added root-owned `/etc/t630/gpu-sysmem.enabled`. The scoped GPU wrapper appends
sysmem only for GPU-opted-in processes; software apps and the physical host
compositor remain unchanged. This is GPU rendering into system memory plus
the already-required CPU-copy presentation, not switching rendering to the CPU.

Stopped only the validated ordinary GNOME session launcher, allowing its cleanup
to release X3. `ubuntu/test-t630-fullscreen-gpu.sh` started managed full-screen
GPU GNOME3175 with the normal password lock, wrapping it with a software-launch
fallback. The first image was an idle black shade; a harmless Shift on its host
X3 restored a correctly rendered purple clock/swipe lock screen, without unlock.
Screenshot: `gnome-sysmem-fullscreen-wake-20260912.png`. Its maps confirmed the
isolated Turnip driver. No GPU page fault was recorded during the live trial.

`ubuntu/test-t630-gpu-fallback.py` subsequently SIGSTOPped that exact validated
locked GPU process using a pidfd, with a45-second SIGCONT safety net. The runtime
watchdog detected the failed responses, stopped its owned child, and the wrapper
started software GNOME6969. This was an intentional test pause, not a spontaneous
GPU hang. Password lock was verified, Turnip mappings were absent, the boot ID
was unchanged, and sound automatically returned after the repairs below.
Thus the real fallback path—not only its mocks—was exercised successfully.

## Audio session-restart repairs

Replacing GNOME exposed stale user audio daemons with sockets removed during
elogind runtime-directory recreation. The `/run/t630-audio-ready` marker was not
proof of a reachable audio server. A second bug held the audio startup flock
forever: firmware pd-mapper1080 inherited FD9 from the initial startup script.
PipeWire daemons also inherited it. The pd-mapper was never stopped or reloaded.
After verifying its sole inherited FD and the original launcher730 was gone,
renamed the old RAM lock inode285 to `t630-audio-start.lock.inherited-285`, allowing
new invocations to serialize on a fresh inode. Reboot clears the old RAM lock.

Permanent changes:

- Close FD9 in the cold-order child script and spawned audio-server processes;
  the root parent continues holding it until startup finishes.
- Recheck the actual named speaker sink, not only the readiness marker.
- After a verified stale session, terminate only UID1000 PipeWire/WirePlumber
  executables whose selected profile/runtime fields match the real tablet
  desktop. Signal via pidfd, wait at most5seconds, and refuse duplicate startup
  if an old server does not stop. No module unloading or blanket process kill.
- Launch the serialized audio companion on each managed GNOME session start,
  so GPU-to-software fallback also reconnects sound. Healthy audio is left alone.
- Prepare the calibrated stock PCM route with both physical speaker amps off
  before the new ALSA sink negotiates its format. Only enable the amps after the
  sink exists, is muted, and is set to30%. Existing factory calibration checks,
  gains and protection limits are retained. An initial repair hit the prior
  amp-off assertion, then a concurrent format-negotiation failure; those failed
  attempts are not claimed as sound passes. The ordered preparation fixed them.

Backup: `/usr/local/share/t630/backups/audio-session-repair.THc22J`.
Five cleanup-selector tests and four mocked routing tests passed on Mac/tablet.
Routing tests verify prepare never enables either amp or changes gain/calibration,
and bad calibration refuses writes. Actual fallback restored the unmuted speaker
sink, normal-user silent playback succeeded, and the startup flock was available
after the helper exited. No credentials were read, stored, or altered.

## Full GPU boot trial

At21:33:16EDT, dispatched a clean one-boot full GPU startup trial with sysmem.
`gpu.disabled` was moved to the root-only `gpu-trial-restore-software` marker.
The root GNOME launcher restores that exact file to `gpu.disabled` before any
GPU initialization, retaining GPU selection only for this already-selected boot.
Thus subsequent boots return to software even if the trial fails. The normal
GPU supervisor/software fallback remains present on this boot. Result pending.

**Passed:** boot `ec72c69d-aa28-4b8c-abf3-79d995a9d6e6` automatically launched
GPU GNOME1184. Its mapped library is the isolated KGSL Turnip, with
TU_DEBUG=sysmem and MESA_VK_ABORT_ON_DEVICE_LOSS=1. The startup watchdog passed,
password lock was verified, the physical clock/swipe screen rendered correctly,
and no GPU page-fault/hang line appeared in the kernel log. SSH returned over
[redacted Wi-Fi network]; USB serial also worked. IPA ONLINE, brightness83%, idle300seconds.

The new audio startup passed from boot: calibrated PCM preparation with amps
off, named speaker sink present,30% volume, unmuted, normal-user silent playback
accepted. The audio startup flock was released, confirming the inheritance fix
also works through the firmware/cold-start branch. The one-boot marker restored
gpu.disabled and removed itself before launch; next boot is software by design.

Current live session is accelerated, but this remains a trial rather than proof
of long-term stability. The owner's post-change physical touch/pen/window test
has not been received. Hardware video decoding is still not implemented, and
the previously observed GLES precision-validation failures remain unresolved.
All44 local regression tests passed; the new audio-selector/routing tests also
passed on the tablet. No boot image, kernel/module binary, driver reset policy,
speaker gain, protection limits, or authentication rules were changed.

## Repeated sysmem trials — 2026-09-13

On clean boot `84251a48-c3c6-44cf-81bf-5d9f046fb4f8`, three consecutive private
`gpu-x11-sysmem` GNOME trials completed. Each held for 30 seconds, passed 11 bus
health checks, loaded the isolated Turnip library and produced two distinct
central image hashes while toggling Overview. The first and third final frames
were visually inspected and rendered the GNOME overview correctly. No KGSL
translation-fault, GPU-hang, kernel oops or panic line appeared, the real
password-locked software GNOME process remained running, and no private test
process remained afterward.

This strengthens the case for sysmem mode and the bounded fallback, but does not
erase the earlier reproduced UCHE translation fault or the GLES precision
failures. Software GNOME therefore remains the default rather than promoting a
three-run test into a broad GPU-stability claim.

Evidence: `gnome-sysmem-coldboot-20260912.log/.png`,
`gnome-sysmem-fallback-20260912.log`, `audio-session-repair-20260912.log`.

Primary diagnostic references:

- https://docs.mesa3d.org/drivers/freedreno.html (sysmem and other process-only
  controls for narrowing hangs; kernel recovery limitations).
- Local Mesa25.2.8 `src/vulkan/runtime/vk_device.c` recognizes
  MESA_VK_ABORT_ON_DEVICE_LOSS; no driver binary replacement was needed.
- https://docs.mesa3d.org/relnotes/26.2.2.html identifies a newer upstream driver
  release, but it has not been downloaded, built or substituted during these tests.
