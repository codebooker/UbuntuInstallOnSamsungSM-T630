# SM-T630 persistent installation — core goal verified

**Final result:** Ubuntu boots persistently, including a clean restart cycle.
Desktop, physical finger tap, physical S Pen click-and-drag, and Wi-Fi passed.
Recovery and partition geometry are unchanged; USB recovery shell remains live.
See the final audit at the end. Earlier sections retain the chronological tests
and temporary blockers, not the current completion state.

Owner explicitly directed continuation after the proposal to erase Android
userdata and update BOOT. A persistent-install goal is active. This report is
not proof of a successful reboot until the post-boot section says so.

## Actual writes

- `/dev/sda34`, verified PARTNAME=userdata, 226918360 sectors: formatted ext4,
  UUID `64de8544-53ea-4fdc-8946-d6b07e238630`, label ubuntu-t630. Android userdata
  has been erased. Existing GPT/partition sizes were not changed.
- Copied native Ubuntu from RAM; verified 27395 /usr and /opt entries including
  regular-file SHA256, ownership, modes and symlink targets, with zero differences
  excluding two intentionally replaced v4 compatibility files.
- Explicit read-only filesystem check after unmount completed all five passes.
  Filesystem clean, 30366 files, about 1.3GiB used of 107.2GiB usable.
- Kernel ext4 does not accept the Android `security.selinux` labels inherited
  from RAM: tar logged 30340 such warnings. No security.capability warnings.
  Copy exited 0; content/Unix permissions and filesystem checks passed. This is
  not a supported SELinux-labelled Android filesystem or hardened desktop.
- Wi-Fi profile originally generated under /run by Ubuntu's Netplan integration
  was explicitly copied to persistent NetworkManager storage, mode 0600.
  Its secret was never printed. Network reconnect after reboot remains to test.
- BOOT `/dev/sda19`, verified PARTNAME=boot and size 96MiB, updated directly
  through the existing root diagnostic shell, with old-image hash precondition,
  input hash check, fsync and complete partition readback SHA256 verification.
  Candidate: `output/persistent-v1/boot.img`, SHA256
  `297cf31e5914ff6a17d1e1d6499d2af2a493022c56336978b76e61e14b9c910a`.
- Recovery, vendor_boot, DTBO and the existing custom VBMETA were checked after
  this write and match their pre-write hashes. No writes to those partitions.
- BOOT retains exact Samsung kernel/header/command line; initramfs now starts
  the USB shell first, checks userdata size/UUID/install marker, mounts Ubuntu,
  loads exact stock input/Wi-Fi drivers and supervises Weston/network/time.
- Persistent session remains a root, Pixman-rendered prototype with BusyBox
  PID 1, no systemd boot and no GPU acceleration claim. USB is an unauthenticated
  physical root recovery shell; connect only to a trusted machine.

## Backup correction

The first snapshot omitted NetworkManager credential paths but accidentally
included the generated `/etc/netplan` Wi-Fi configuration. Earlier claims that
the snapshot contained no Wi-Fi credentials were incorrect.

A sanitized replacement excludes Netplan as well. All 29296 retained archive
entries were verified against the original (content hashes and metadata).
Current usable artifact: `output/ubuntu-desktop-ram-20260912-sanitized.tar.gz`,
460976403 bytes, SHA256
`953fa9fe4b1a03d910156fa1f86bd70093afa027582b43be202609bd9b1caaa6`.
The obsolete TLS original, corrupt serial copy and zero-byte failed copy were
deleted from the Mac. The sanitized backup retains their usable userspace, not
the generated Wi-Fi profile. Ordinary deletion is not a secure-erasure claim.
The snapshot script now excludes Netplan for future backups too.

## Reboot status

**First persistent reboot succeeded.** USB re-enumerated as SM-T630 Ubuntu
recovery console; `/dev/sda34` is mounted ext4 rw at `/run/ubuntu`. Weston,
desktop-shell, keyboard and terminal started automatically. About 5GB of RAM
was available after boot, compared with the RAM-hosted prototype's smaller pool.

Input modules loaded at cold boot; event5 has the confirmed finger calibration
matrix and DSI-1 association, and event7 has tablet classification/axis resolution.
The owner has been asked to confirm physical taps and pen dragging after reboot;
that confirmation is still pending. No claim of physically verified drag yet.

Wi-Fi initialized around 76 seconds into the boot and automatically connected
to [redacted Wi-Fi network] at TABLET_IP. Chrony synchronized to Ubuntu NTP and corrected the 2021
boot clock. Native HTTPS to ubuntu.com returned 200. No TCP/UDP listening sockets
were reported. Initial post-copy apt directories were 0700, producing a download
sandbox warning; corrected lists/archive parents to 0755 and partial dirs to
0700 _apt:root. Subsequent `apt-get update` completed without that warning and
without disabling signature verification. Provisioning scripts now set umask 022.

The 60-second firmware fallback timeout may contribute to slow Wi-Fi startup;
this is an inference, not an isolated cause or a change made to the kernel.
Kernel documentation says timeout=0 means effectively infinite, **not disabled**:
https://docs.kernel.org/driver-api/firmware/fallback-mechanisms.html .

An orderly USB-side restart helper is `/bin/stop-ubuntu reboot`. It prevents
service respawn, stops daemons and unmounts before restart; an unmount failure
prevents forced reboot. That helper still needs a physical restart-cycle test.
Do not treat a long-press power cut as a normal clean shutdown.

Evidence: `persistent-root-fsck.txt`, `persistent-boot-write.txt`,
`persistent-reboot-request.txt`, `desktop-snapshot-sanitized.json`.

## Installed-version backup

After the successful reboot and apt permission fix, a fresh installed-root
snapshot was transferred over the same peer-restricted one-shot TLS mechanism.
`output/ubuntu-persistent-v1-tls.tar.gz`: 473005700 bytes, SHA256
`8a3633f052b2b4c54952039bf702a3199f022ed9df68f2b4109cec4f6124c3e7`.
The full hash matched on tablet and Mac. It excludes Netplan, NetworkManager
profiles/state, runtime directories, logs, apt caches and shell history, and
contains the installed v4 workaround, input/network configuration and chrony.
Pair it with `output/persistent-v1/boot.img` for the current prototype version.
The transfer server has stopped; socket inventory again shows no TCP/UDP
listeners. This new backup has not itself been restored onto an erased tablet.

Still pending: owner post-reboot physical input/drag feedback. Suspend, GPU,
audio, cameras, S Pen pressure in creative apps and non-root daily-driver
security are not validated. The diagnostic wake lock keeps the tablet awake.

## Completion audit, follow-up pass

- Persistent BOOT partition was re-read and still matches the installed image.
- The native framebuffer was captured without a modeset or any pixel writes.
  Samsung's driver rejects GetFB2, but legacy GetFB exports its depth24/bpp32
  scanout. MAP_DUMB plus a PROT_READ mapping produced a complete 1200x1920 frame.
  PNG encoding preserved its pixel values, and the downloaded image's full
  SHA256 matched: `796d37a6b02907ca27ed1d10d851d257e55c9fcdf01e57832fc8c0f963d9464b`.
  `persistent-scanout.png` was visually inspected: purple desktop, top panel,
  correct date/time, terminal window and root prompt are actually rendered.
  Native raster orientation is portrait; the desktop content is landscape,
  consistent with the configured rotate-90 transform. No capture-side rotation.
- This verifies rendered desktop content, not the panel's emitted light or
  physical input. The unresolved gate remains the owner's post-reboot finger
  and S Pen test, including the previously reported dragging problem.
- Previous goal turn was **progress**: internal install, verified write and
  reboot, automatic network recovery, and backups. This pass adds direct visual
  scanout evidence; it does not redefine input verification as configuration
  inspection. Goal completion remains unproven pending physical input feedback.

## Awaiting hands-on verification

At 829 seconds uptime, the persistent ext4 root remained mounted read/write,
Weston retained PID 652, NetworkManager reported connected/full, and the battery
was charging at 34%. No restart or further flash was performed in this check.
The preceding goal pass made progress by directly verifying the rendered frame.
The same remaining physical-input gate has now persisted across three goal
turns without owner feedback. Safe software checks cannot establish physical
finger alignment, tip clicks or drag behavior. The goal is blocked on that
specific test, not marked complete; the tablet is left running and connected.

## Resumed work: synthetic input-path verification

The owner asked to continue. Additional bounded tests were run without treating
synthetic events as physical digitizer proof:

- A temporary fullscreen GTK test surface received only test-local input (no
  global keyboard capture). Controlled events were injected into the existing
  sec_e-pen evdev node, after refusing any already-held physical tip. The test
  releases synthesized contact/proximity state in a finally block.
- GTK received pen motion at approximately (960,600), button-1 press, held-tip
  motion to (1152,480), and release. This verifies the kernel input-to-libinput-
  Weston-GTK software path, including button state during drag.
- With the temporary surface closed, a separate synthetic pen drag targeted
  the observed terminal title bar. Read-only scanout measurements before/after
  showed its top-left moving from **(639,251) to (831,131)**: exactly +192/-120,
  matching the injected motion. The v4 Weston pen-list workaround activated.
  This is direct evidence that the window-drag software bug is addressed.
- A single-slot synthetic sec_touchscreen sequence produced GTK touch-begin
  (959,601), ten updates ending (1150,482), and touch-end. The touchscreen
  calibration/rotation path is functioning after the persistent reboot.
- The first GTK logger had an optional Cairo-converter issue, then a union
  field serialization issue for touch events. Both were corrected in the
  local test utility; the final v3 touch log is clean. These were test-tool
  faults, not evidence of broken tablet input.
- Evidence: `pen-path-software-test.txt`,
  `pen-window-drag-software-test.txt`, `touch-path-software-test-v3.txt`.
- Temporary test windows were closed. No input-device grabs, firmware writes,
  keyboard injection or calibration changes were performed.

A clean restart through `/bin/stop-ubuntu reboot` also **succeeded**. USB
disconnected and returned, uptime reset, ext4 mounted normally without journal
recovery messages, and desktop/terminal/Wi-Fi restarted automatically. Native
HTTPS returned 200 again. Evidence: `persistent-second-boot.txt`.

To remove the need for a typed chat reply, `ubuntu/verify_physical_input.py`
now displays a two-step physical test on the tablet: tap an asymmetric finger
target, then drag a pen tile into a separate drop zone. It filters for the
appropriate device source and requires pen movement plus release in the zone.
It records test ID, process ID, current kernel boot ID and pass flags in
`/run/t630-physical-input-result.json` inside Ubuntu, then closes on success.
No synthetic inputs are used while this physical test is running. Its state
must not be confused with the separate synthetic test logs. A fresh result
must match the active test process/boot; merely launching the panel is not a pass.

The panel was inspected through a read-only scanout capture. Its target-box
styling was corrected before any physical input was recorded. Current session
identity is in `physical-input-test-session.txt`. The owner can complete the
remaining hardware check directly on the tablet without typing a report.
Physical sensor alignment remains distinct from the successful software tests.

## Final physical result and completion audit

The owner completed the on-tablet test without a chat reply. Test ID
`31de47d5-f097-45b2-8c9d-83d94a7ab779`, process 915, kernel boot ID
`27d8eb8f-61f3-4013-a32b-726c1f75d3af` recorded all physical pass flags at
328.004 seconds monotonic uptime. Finger target tap, pen button-1 tip contact,
and pen drag into the separate target passed; recorded pen movement was 870.1
logical pixels. No synthetic input was injected during this physical test.
The test closed itself and returned to the desktop.

The final audit independently re-read the current boot ID and compared it with
the test result, preventing a stale prior-boot result from counting as proof.
It confirmed the persistent ext4 mount, running desktop/terminal, full network
connectivity, and BOOT/recovery/vendor_boot/DTBO/VBMETA partition hashes. All 99
block-device major/minor numbers and sizes match the pre-install baseline.
An initial audit parser accidentally included a four-word process command as
a partition row; restricting all three numeric columns corrected the verifier,
and the actual full geometry comparison passed.

| Goal requirement | Authoritative evidence |
| --- | --- |
| Persistent native Ubuntu on internal userdata | Two boots, fresh uptimes and ext4 `/dev/sda34` mount; matching boot-image readback |
| Preserve stock recovery and partition table | Full recovery SHA256 unchanged; all pre-install partition geometry unchanged; no table-writing command executed |
| Retain USB recovery shell | Root serial commands worked before and after both persistent boots |
| Verify desktop | Direct scanout image inspected; desktop/terminal running again after clean restart |
| Verify touch and pen after reboot | Current-boot physical test completed by touchscreen and pen device sources; pen drag/drop passed |
| Verify Wi-Fi after reboot | [redacted Wi-Fi network] reconnected automatically twice; connected/full and HTTPS 200 after restart |

Final evidence: `persistent-completion-audit.txt`,
`physical-input-test-session.txt`, `persistent-second-boot.txt` and the earlier
hashed backups. The scoped persistent-boot/input/network goal is achieved.
This is still the documented root, software-rendered prototype: GPU acceleration,
audio, cameras, suspend and hardened daily-driver operation are not claimed.
