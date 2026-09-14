# Hardware and integration status

Last updated: 2026-09-14. Unless stated otherwise, results are from one physical
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
| Keyboard | Working | Maliit/GNOME on-screen keyboard with Shift, Enter, Backspace, and Hide |
| Physical keys | Working | Volume, Power, Home, Back, Recents, and red Active button mapped |
| Wi-Fi / remote access | Working | Reconnect survives interface renaming; SSH and the single-instance loopback screen service work over the LAN |
| Bluetooth | Working | WCN6850 startup retry, firmware handoff, idle wake, BlueZ discovery, synchronized teardown, and supervised recovery physically tested; WirePlumber Bluetooth audio policy is enabled, pending a paired-headset playback test |
| Speakers | Working | Stock calibration and guarded amplifier sequencing; GNOME volume control works |
| Microphone | Working | Built-in microphone exposed as the normal PipeWire source through a demand-driven bridge |
| Sensors | Working | Accelerometer, light, proximity, magnetometer, compass, automatic brightness, and debounced panel/GNOME rotation tested in adjacent positions; four-edge and suspend/resume rotation passes remain |
| Charging | Working | Charger detection and charge state are exposed through UPower to GNOME; 100% fully charged was verified after a cold boot |
| Display sleep | Working | Power-key blank/lock/wake works |
| System suspend | Working | Guarded shallow suspend, automatic idle entry, Power wake, RTC recovery, and post-wake sensor restoration work while unplugged; the sensor bridge is quiesced around freeze to prevent an ADSP wake interrupt |
| GPU | Experimental | Turnip/Zink can render GNOME, but a KGSL fault was reproduced; software fallback is retained |
| Video | Mostly working | FFmpeg and GStreamer H.264/VP9 use the stock decoder. A real WebKit process selected it, but no accelerated browser launcher is shipped because this kernel cannot provide WebKit's normal user-namespace sandbox |
| Camera | Partial | Both GNOME previews run at 720×480. Rear ID 0 uses 30 ms / ISO 800, gamma 2.5, working continuous autofocus, and a live color slider. The HAL supports HD, but Snapshot crashes above the current preview size |
| Flashlight | Working | Rear LED current and PMIC switch mapped; GNOME Quick Settings provides a brightness slider and a leased toggle that fails off after 15 seconds if its controller disappears |
| Optional I/O | Characterized | Kernel support exists for microSD, USB host/role switch, Samsung NFC, GNSS framework, and USB-C DisplayPort. The exact NFC I2C path and the proprietary NFC/GNSS service boundaries are documented; physical accessory and bounded-service tests remain |
| User setup | In progress | Desktop/session integration resolves the installer-selected owner rather than assuming `tablet`/UID 1000; deterministic first-boot and desktop-runtime packages pass native arm64 extraction, and the non-writing first-boot preview fills the physical display; fresh-root execution remains |
| Release packaging | In progress | First-boot, desktop, hardware, sensor, native-userspace, and private DZE3 stock-assets packages build reproducibly and pass native extraction; factory-archive preparation, remaining compiled components, root assembly, and recovery rehearsal remain |
| Security | Lab configuration | GNOME password lock works, but the retained recovery compositor and USB root console mean this is not a hardened full-device login boundary |

## Known limitations

- The public repository does not yet ship a ready-to-flash Ubuntu image.
- The first device uses an unlocked bootloader and reports orange verified-boot
  state. Knox warranty state is permanently tripped.
- Recovery to stock was prepared but has not been exercised end-to-end on the
  development tablet.
- GPU acceleration is opt-in; software rendering is the safe fallback.
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
The source-built compatibility binary boundary is recorded in the
[native userspace package report](reports/native-userspace-package-20260914.md).
The redistributable hardware-service boundary is recorded in the
[hardware runtime package report](reports/hardware-runtime-package-20260914.md).
The pinned, reproducible Qualcomm sensor build is recorded in the
[sensor stack package report](reports/sensor-stack-package-20260914.md).
The local-only proprietary asset boundary is recorded in the
[stock assets package report](reports/stock-assets-package-20260914.md).
