# Hardware and integration status

Last updated: 2026-09-14. Unless stated otherwise, results are from one physical
SM-T630 on the exact `T630XXSBDZE3` baseline.

## Diagnostic safety

Do not recursively read arbitrary `name` attributes below `/sys` on the stock
DZE3 kernel. A read of a Qualcomm GLINK packet-device `name` attribute reached
`drivers/soc/qcom/glink_pkt.c:name_show()` with an invalid device object and
caused a kernel null-pointer panic. In particular, avoid commands equivalent to
`find /sys ... -name name -exec grep ...`. Runtime checks in this repository use
explicit, previously validated sysfs paths instead.

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
| System suspend | Experimental | Guarded shallow suspend, Power wake, RTC recovery, and automatic idle policy are implemented and enabled; one unattended unplugged idle-cycle acceptance remains |
| GPU | Experimental | Turnip/Zink can render GNOME, but a KGSL fault was reproduced; software fallback is retained |
| Video | Mostly working | FFmpeg and GStreamer H.264/VP9 use the stock decoder. A real WebKit process selected it, but no accelerated browser launcher is shipped because this kernel cannot provide WebKit's normal user-namespace sandbox |
| Camera | Partial | Both GNOME previews run at 720×480. Rear ID 0 uses 30 ms / ISO 800, gamma 2.5, working continuous autofocus, and a live color slider. The HAL supports HD, but Snapshot crashes above the current preview size |
| Flashlight | Working | Rear LED current and PMIC switch mapped; GNOME Quick Settings provides a brightness slider and a leased toggle that fails off after 15 seconds if its controller disappears |
| Optional I/O | Detected | Kernel support exists for microSD, USB host/role switch, Samsung NFC, GNSS framework, and USB-C DisplayPort; physical accessory and service tests remain |
| User setup | In progress | Desktop/session integration resolves the installer-selected owner rather than assuming `tablet`/UID 1000; the first-boot backend validates identity, locale, keyboard and timezone without storing the password |
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
  Wi-Fi and RTC guards. Its final release gate is an unattended five-minute
  cycle while physically unplugged.
- Camera support still depends on proprietary files extracted from the owner's
  matching stock firmware; those files cannot be redistributed here. Both
  cameras are integrated with GNOME. Rear exposure and color are physically
  accepted and user-adjustable, but exposure is not scene-aware and needs
  wider-lighting tests.
  See [CAMERA.md](CAMERA.md).

For the complete test history, see the dated files in `docs/reports/`, including
the [GStreamer and WebKit video report](reports/gstreamer-video-20260913.md).
