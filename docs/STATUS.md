# Hardware and integration status

Last updated: 2026-09-16. Unless stated otherwise, results are from one physical
SM-T630 on the exact `T630XXSBDZE3` baseline.

## Diagnostic safety

Do not read arbitrary `name` attributes below `/sys` on the stock DZE3 kernel.
A recursive Qualcomm GLINK probe and, independently, a direct read of
`/sys/bus/spi/devices/spi0.0/name` both reached `name_show()` with an invalid
device object and caused a kernel null-pointer panic. Avoid commands equivalent
to `find /sys ... -name name -exec grep ...` and do not assume a narrower bus
glob is safe. Runtime checks in this repository use exact, previously validated
sysfs paths instead. See the [second reproduced panic report](reports/sysfs-name-panic-20260914.md).

| Area | State | Notes |
| --- | --- | --- |
| Boot | Working | Stock downstream kernel with a replacement Ubuntu initramfs; Ubuntu root on userdata |
| Display | Working | Internal DRM/MSM panel; GNOME fills both tested 1920×1200 landscape and 1200×1920 portrait positions without the recovery panel showing |
| Touch | Working | Finger coordinates and click/drag corrected |
| S Pen | Working | Position and clicking corrected; GNOME keyboard accepts pen input |
| S Pen pressure | Confirmed in manual source trial; not default | Native GNOME GTK received 310 physical pen samples spanning normalized pressure 0–0.800534, plus 147 finger events, with the opt-in real-event/source-axis Mutter handoff trial. The owner confirms pressure feels much better; the failed 2× app sensitivity trial remains reverted to identity. Failed proximity preloads remain removed. Physical hover-out lifecycle, responsive drawing, restart/rotation/lock regressions and safe packaging remain; normal startup has no pressure trial. See the [pressure-path report](reports/pen-pressure-path-20260915.md) |
| Pen apps | Evaluation | Native Xournal++ notes and MyPaint drawing launch in clean-root GNOME; continuous handwriting is visible. Xournal++ has no perceptible pen lag, isolating the remaining delay to MyPaint. Its default-idle stroke queue measured 7.405 s median/11.404 s p95; high-idle reduced this to 41/81 ms. With the actual per-device stylus clone changed from deliberately smoothed `classic/short_grass` to pressure-aware zero-tracking `deevad/ballpen`, it measured 28/49 ms at priority 100 and 26/43 ms at priority 0. The exact-version adapter now uses the latter, with both older helpers retained for rollback; the owner reports it feels better. Xournal++ touch drawing, internal hand recognition, and libinput's partial region did not fully reject this tablet's palm. A root guard now disables only the exact touchscreen for the S Pen's full proximity interval without grabbing or logging input; the owner confirms palm rejection works before and after restart. Extended sessions, rotation, and save/reopen remain; Krita's native-Wayland rejection is documented |
| Keyboard | Working | Maliit/GNOME on-screen keyboard with Shift, Enter, Backspace, and Hide |
| Everyday apps | Working | Clean-root provisioning installs GNOME Software/PackageKit, native Mozilla Firefox, Files, Terminal, Text Editor, LibreOffice, Contacts, media codecs, and the standard GNOME utilities; Snap remains absent because the stock kernel lacks its namespace requirements |
| Physical keys | Working | Volume, Power, Home, Back, Recents, and red Active button mapped |
| Desktop system controls | Working | Settings is packaged and available from the app grid, favorites, and Quick Settings; GNOME's standard Restart and Power Off confirmations reach the guarded orderly-shutdown path. The default Utilities folder is now flattened before Shell starts using an invisible empty-folder sentinel; the live grid passes, with new-fix restart acceptance pending |
| Wi-Fi / remote access | Working | The normal pre-wlan filesystem-ready event now starts stock CNSS cold-boot calibration at 3.77 seconds; calibration completed at 19.55 seconds, WLAN module loading returned at 20.83 seconds, association began around 25.6 seconds, and DHCP completed around 27.7 seconds with no 70-second timeout. Owner-only SSH, real HTTPS, and the loopback screen feed start automatically on the personalized clean root; host trust and same-boot isolation checks pass |
| Bluetooth | Working | WCN6850 startup retry, firmware handoff, idle wake, BlueZ discovery, synchronized teardown, and supervised recovery physically tested; WirePlumber Bluetooth audio policy is enabled, pending a paired-headset playback test |
| Speakers | Working | Stock calibration and guarded amplifier sequencing; GNOME volume control works |
| Microphone | Working | Built-in microphone exposed as the normal PipeWire source through a demand-driven bridge |
| Sensors | Working | Accelerometer, light, proximity, magnetometer, compass, automatic brightness, and debounced panel/GNOME rotation tested in adjacent positions; four-edge and suspend/resume rotation passes remain |
| Charging | Working | Charger detection and charge state are exposed through UPower to GNOME; 100% fully charged was verified after a cold boot |
| Display sleep | Working | Power-key blank/lock/wake works |
| Brightness / rotation lock | Working; responsiveness follow-up | Missing display-preferences directory could terminate the Power/display monitor; directory creation and nonfatal persistence retry are repaired. Tablet Controls 7 uses one hardware-backed brightness slider and a calibrated-service Rotation Lock. The owner confirms both work after restart; brightness's trailing debounce still feels laggy. See the [repair report](reports/brightness-rotation-lock-20260915.md) |
| App drawer / input stability | Recovered; intermittent cause open | Input failed after opening Activities/app menu despite working login and brightness controls. Another managed-session replacement with a bounded state-only observer produced a successful owner-confirmed replay. Observer is disabled; repeated ordinary drawer use with finger and S Pen also passed. Durable root cause, rotation, lock/unlock and fresh-start acceptance remain; see the [input report](reports/app-drawer-input-regression-20260915.md) |
| System suspend | Working | Guarded shallow suspend, automatic idle entry, Power wake, RTC recovery, and post-wake sensor restoration work while unplugged; the sensor bridge is quiesced around freeze to prevent an ADSP wake interrupt |
| GPU | Experimental | Turnip/Zink can render GNOME, but a KGSL fault was reproduced; software fallback is retained |
| Video | Mostly working | FFmpeg and GStreamer H.264/VP9 use the stock decoder. A real WebKit process selected it, but no accelerated browser launcher is shipped because this kernel cannot provide WebKit's normal user-namespace sandbox |
| Camera | Partial | Both GNOME previews run at 720×480. Rear ID 0 uses 30 ms / ISO 800, gamma 2.5, working continuous autofocus, and a live color slider. HAL state regenerates into account-neutral `/var/lib/t630-camera`; the HAL supports HD, but Snapshot crashes above the current preview size |
| Flashlight | Working | Rear LED current and PMIC switch mapped; GNOME Quick Settings provides a brightness slider and a leased toggle that fails off after 15 seconds if its controller disappears |
| Optional I/O | Characterized | Kernel support exists for microSD, USB host/role switch, Samsung NFC, GNSS framework, and USB-C DisplayPort. The exact NFC I2C path and the proprietary NFC/GNSS service boundaries are documented; physical accessory and bounded-service tests remain |
| User setup | Working | The physical ownerless-root walkthrough completed with the normal GNOME keyboard, Wi-Fi connection, user-selected account/password, unique post-install machine identity, owner-neutral asset migration, and transition to the new owner's GNOME password lock; the installer frontend now defaults to dark mode |
| Release packaging | In progress | The thirteen-component set is now dependency-consistent under `t630-release-base` 0.1.14. A package refresh repaired stale exact internal dependencies, the native login builder is byte-reproducible and survives the root's documentation-exclusion policy, and the installed tablet passes both `dpkg --audit` and `apt-get check` after a clean reboot. The identity-safe Ubuntu 24.04.5 ARM64 root completed first boot and repeated personalized cold boots. Boot v7 keeps that root selected after orderly system actions while preserving crash fallback; exact write/readback, protected-neighbor checks, managed GNOME startup, Wi-Fi filesystem-ready startup, and wallpaper persistence pass. Return-to-stock acceptance remains |
| Security | Lab configuration | GNOME password lock works and normal owner boots no longer expose the recovery terminal, but the retained parent compositor and USB root console mean this is not a hardened full-device login boundary |

## Known limitations

- The public repository does not yet ship a ready-to-flash Ubuntu image.
- The first device uses an unlocked bootloader and reports orange verified-boot
  state. Knox warranty state is permanently tripped.
- Recovery to stock was prepared but has not been exercised end-to-end on the
  development tablet.
- GPU acceleration is opt-in; software rendering is the safe fallback.
- The personalized clean root now passes an unattended orderly restart with
  automatic SSH/screen startup, preserved wallpaper and owner folders. Full
  Power Off acceptance remains separate; this restart does not prove shutdown
  on every path. See the [restart report](reports/clean-root-restart-folders-20260915.md).
- Wi-Fi cold-boot calibration now follows the stock driver's required ordering
  and physically passes. If any exact model/kernel/root/firmware/order gate
  refuses, startup deliberately falls back to the older slow path instead of
  leaving Wi-Fi unavailable.
- The stable nested GNOME path currently disables its internal Xwayland server;
  the packaged default applications are Wayland-native, but legacy X11-only
  applications will not run until the Qualcomm/Mesa crash path is resolved.
- The stock kernel has `CONFIG_USER_NS` disabled. Firefox remains the safe
  default browser; the verified WebKit hardware-video path is not exposed as a
  launcher because it currently requires disabling WebKit's normal sandbox.
- Automatic idle system suspend is enabled with power, USB, audio, lock, panel,
  Wi-Fi and RTC guards. The SSC sensor bridge is stopped only after those guards
  pass and is relaunched after every return from freeze; this prevents its open
  FastRPC channel from immediately waking the system through ADSP GLINK.
- Camera support still depends on proprietary files extracted from the owner's
  matching stock firmware; those files cannot be redistributed here. Both
  cameras are integrated with GNOME. Rear exposure and color are physically
  accepted and user-adjustable, but exposure is not scene-aware and needs
  wider-lighting tests.
  See [CAMERA.md](CAMERA.md).

For the complete test history, see the dated files in `docs/reports/`, including
the [GStreamer and WebKit video report](reports/gstreamer-video-20260913.md) and
the [NFC/GNSS prerequisite audit](reports/nfc-gnss-prerequisites-20260914.md).
Installer work is tracked in the
[first-boot package report](reports/first-boot-package-20260914.md).
Automatic suspend acceptance and the ADSP wake fix are recorded in the
[suspend acceptance report](reports/automatic-suspend-acceptance-20260914.md).
The standard Settings, navigation-key, Restart, and Power Off integration is
recorded in the [desktop system-controls report](reports/desktop-system-controls-20260914.md).
The source-built compatibility binary boundary is recorded in the
[native userspace package report](reports/native-userspace-package-20260914.md).
The redistributable hardware-service boundary is recorded in the
[hardware runtime package report](reports/hardware-runtime-package-20260914.md).
The pinned, reproducible Qualcomm sensor build is recorded in the
[sensor stack package report](reports/sensor-stack-package-20260914.md).
The local-only proprietary asset boundary is recorded in the
[stock assets package report](reports/stock-assets-package-20260914.md).
The pinned audio protection-domain service is recorded in the
[pd-mapper package report](reports/pd-mapper-package-20260914.md).
The exact-version dependency closure is recorded in the
[release package-set report](reports/release-package-set-20260914.md).
The live package dependency repair, reproducibility check, and clean-reboot
acceptance are recorded in the
[package consistency report](reports/package-dependency-repair-20260916.md).
The packaged host compositor boundary is recorded in the
[boot runtime report](reports/boot-runtime-package-20260914.md).
The source-built app-store authentication boundary is recorded in the
[PolicyKit runtime report](reports/polkit-runtime-package-20260914.md).
The reproducible password-login boundary is recorded in the
[login runtime report](reports/login-runtime-package-20260914.md).
The redistributable camera boundary and physical package-path test are recorded
in the [camera runtime report](reports/camera-runtime-package-20260914.md).
The hash-gated local reconstruction of the private static camera layer is in the
[camera static reconstruction report](reports/camera-static-reconstruction-20260914.md).
The empty-state regeneration and account-neutral writable camera path are in the
[camera state isolation report](reports/camera-state-isolation-20260914.md).
The fail-closed offline installation boundary is recorded in the
[release-root assembly report](reports/release-root-assembly-gate-20260914.md).
The reproducible AVB-verified persistent image and guarded write boundary are
recorded in the [release boot candidate report](reports/release-boot-candidate-20260914.md).
The successful package apply and first-boot backend exercise are recorded in the
[fresh-root rehearsal report](reports/fresh-root-rehearsal-20260914.md).
The physical GNOME keyboard and two-orientation installer preview are recorded
in the [GNOME first-boot host report](reports/first-boot-gnome-host-20260914.md).
