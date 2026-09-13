# GNOME startup and audio investigation — 2026-09-12

## Automatic desktop startup

`ubuntu/t630-desktop-autostart` is installed as
`/usr/local/sbin/t630-desktop-autostart`. Weston's existing configuration now
has an `[autolaunch]` section pointing to it, with `watch=false`. Failure leaves
Weston running. This uses Weston's documented autolaunch mechanism; the boot
image, kernel, partition table and input calibration were not changed.

The wrapper checks the install marker and required files, waits for the existing
Wayland/system bus sockets, clears the root compositor's environment, then calls
the normal-user GNOME launcher in fullscreen mode. GNOME's existing singleton
lock prevents a duplicate desktop. A later three-second delay lets the initramfs
recovery terminal map first, preventing it from covering the fullscreen host.

Recovery: create `/etc/t630/desktop-autostart.disabled` to skip automatic GNOME,
or restore `/root/.config/weston.ini.before-gnome-autostart`. Manual GNOME launch
remains available from Weston. This is automatic entry into the existing tablet
account, not a new login manager, lock screen or hardened session architecture.

The owner approved restart after being asked to save open documents. The first
attempt stopped safely on a busy `/run/ubuntu/dev` mount. All normal applications
had received SIGTERM, but the old helper allowed only three seconds before
unmounting. A later ordinary unmount succeeded; no force/lazy unmount or power
cut was used. The initial inspection did not establish the holder. A second
attempt showed that even 30 seconds of waiting did not release the mount. The
actual holder was the restart helper itself: its SSH-side `/dev/null` redirect
had been opened through Ubuntu's bind mount before chrooting into the outer
root. Reopening stdin in the outer root changed its verified fdinfo mount ID
from 24 (Ubuntu bind) to 19 (outer /dev). The final helper now does
`cd /; exec </dev/null` before stopping services. Longer waits remain but were
not the root-cause fix.

`ubuntu/stop-ubuntu-remote` now waits up to 30 seconds for processes rooted in
the Ubuntu mount to exit, tolerates already-unmounted targets, and retries each
ordinary unmount for up to 30 seconds. It still aborts rather than force an
unclean restart. The too-long process-name pkill entry was removed; the exact
chroot-root process sweep already covers that process. Updated helper SHA256:
`9ea0f7c85c2f4e990c83654c29dd3a275468a5acc8f3c96441be9bd91c4aeccd`.
It is persisted at `/usr/local/share/t630/stop-ubuntu` and copied into the outer
RAM filesystem by the existing remote-start helper, with its hash checks intact.

After resuming cleanup from USB, reboot completed. First new boot ID:
`c23d7fcf-6f0c-46f5-b34d-d365dadfdc33`, replacing
`27d8eb8f-61f3-4013-a32b-726c1f75d3af`.
GNOME and its authentication supervisor started automatically as tablet. The
keyboard extension was ACTIVE, keyboard setting true, favorites preserved.
Wi-Fi, key-only SSH and screen service returned around 90 seconds after boot.
The Mac's loopback-only SSH screen tunnel was re-established. The filesystem
mounted normally without a journal-recovery/error line in the checked boot log.
The store rendered again and its process-scoped agent started automatically.

The recovery terminal briefly covered GNOME on this first boot; closing only
that identified boot terminal restored the fullscreen view. The startup delay
was then added. A second full-session restart is being used to validate both
the delay and the improved shutdown helper; record its result below when done.

## Audio: exact-device prerequisites, not working playback yet

ALSA originally reported no sound cards. None of the stock audio modules were
loaded, and the corresponding platform devices had no drivers. The module
sequence comes from this tablet's `init.gtact4prowifi.rc`, not from the S9 Ultra.
`ubuntu/t630-audio-modules.py` resolves the stock `modules.dep`, checks every
selected module's exact kernel vermagic/ARM64 architecture, and defaults to a
read-only plan. `--load` is an explicit temporary runtime test.

The two enabled amplifier devices are I2C 18-0030/18-0031. Their stock CS35L45
driver attached and identified CS35L46 silicon, as logged by that driver. No
mixer gains, calibration values, protection bypasses, or playback signals were
written during this investigation.

Read-only inventories identified:

- `/dev/sda17`, PARTNAME=dsp, ext4: DSP shared libraries. Mounted with `ro,noload`.
- `/dev/sda18`, PARTNAME=modem, FAT: modem firmware, not the ADSP boot payload.
- `/dev/sda23`, PARTNAME=apnhlos, FAT: the actual stock ADSP payload and maps.

Probe mounts were unmounted after use. `ubuntu/stage-audio-firmware.sh` copied
43 existing ADSP/map/amplifier firmware files (about 24 MiB) into
`/opt/t630/audio-firmware`, checked source/destination equality, and exposed them
through new entries in the existing outer `/run/input-firmware` directory.
The touchscreen/Wi-Fi firmware search path and entries were not changed.
Manifest: `reports/audio-firmware.sha256`. Proprietary firmware was not copied
to a public/local distribution artifact or flashed to another partition.

The sound module set loaded successfully. Issuing the stock init sequence's
`/sys/kernel/boot_adsp/boot` request from the outer namespace booted ADSP:
subsystem state ONLINE, reset released, error-ready/clock-ready handshake,
FastRPC and APR audio channel established. No ALSA card appeared yet.

Kernel messages showed the service locator was missing. The S9 Ultra userspace
notes identify the same general dependency, but its mainline device setup was
not copied. Upstream source: https://github.com/linux-msm/pd-mapper at commit
`5ecd2fe926aca7abfe40724177f63b942cff3947`.

The downstream kernel has `msm_subsys` instead of remoteproc firmware metadata.
The retained source in `ubuntu/pd-mapper-source/` adds an explicit `--directory`
option to load this tablet's stock .jsn maps. It does not fabricate remoteproc
nodes or change the maps. Built with Ubuntu libqrtr-dev/liblzma-dev; executable
`/usr/local/sbin/t630-pd-mapper`. Build recipe:
`ubuntu/build-pd-mapper.sh`. The upstream JSON reader emits a size-analysis
compiler warning; input is restricted operationally to the root-owned stock
map directory, not untrusted network-supplied JSON.

The mapper advertised QRTR service 64 and the kernel established the service
locator connection. However, the audio drivers had already timed out before
it started, and no card appeared. The next controlled test starts the mapper
before the modules. Audio module loading, ADSP boot, mapper and firmware links
are NOT enabled at boot; restarting returns to the prior working desktop.

## Final verification and remaining work

The stdin-reference fix was verified directly (mount IDs 24 -> 19), and cleanup
then completed with stdin deliberately opened through the Ubuntu device mount.
New boot ID: `56ecdaf5-5215-4ad5-8da4-53191435e469`. GNOME started automatically
with the three-second ordering adjustment: the recovery terminal no longer
covered it. The owner opened Firefox/YouTube; the live frame showed the normal
desktop and full on-screen keyboard. No documents were restored, modified or
submitted by the assistant. Updated autostart SHA256:
`2d9c4f9ba5148881bcfb99d8f1886a1b7f28e365f6fe458e66727f3745fd898b`.

The owner reported no Wi-Fi during this restart. At 97.97 seconds uptime,
NetworkManager reported wlan0 connected to [redacted Wi-Fi network] at TABLET_IP, and native HTTPS
to ubuntu.com returned HTTP/2 200. Firefox subsequently displayed YouTube.
The second virtual Wi-Fi interface wlp1s0 remains disconnected; this does not
mean the active wlan0 connection is down. Kernel logs identify a 70000 ms CNSS
calibration timeout at 74.719990 seconds, followed by driver initialization and
BDF downloads around 76 seconds. There is also an initial regulatory.db firmware
fallback timeout. Neither calibration nor regulatory protections were bypassed.
This startup latency remains to investigate separately; connectivity itself
is verified. The saved network profile was not changed.

The corrected-order audio test is `/usr/local/share/t630/test-audio-start.sh`.
Starting the stock-map locator before the modules succeeded: service locator
initialization, FastRPC audio/sensor PDR registration, and both ADSP domains
reported UP. The amplifier drivers attached and ADSP stayed ONLINE. However,
`/proc/asound/cards` still reports no cards. The APR parent is bound to audio_apr,
but its q6core-audio/codec/machine child platform devices have not appeared.
This is the next driver-side investigation, not a working sound claim. No test
tones or speaker gain/calibration writes were made. All audio activation remains
manual/runtime-only, and PipeWire session startup is not yet integrated.

The adapted mapper binary SHA256 is
`a0acf3140cdb14cc421f715c6e418628b9101ad52260e4722ce8b45d0eb48849`.
At the final check the battery was Charging at 26%, Wi-Fi was connected, and
`dpkg --audit` was clean. Script syntax and Python compilation checks passed.
The screen tunnel was restored at 127.0.0.1:18765 without exposing a VNC/HTTP
listener to the LAN. No further restart was performed while the owner browsed.
