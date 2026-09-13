# Hardware and integration status

Last updated: 2026-09-13. Unless stated otherwise, results are from one physical
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
| Display | Working | Internal 1920×1200 panel through DRM/MSM; full-screen nested GNOME |
| Touch | Working | Finger coordinates and click/drag corrected |
| S Pen | Working | Position and clicking corrected; GNOME keyboard accepts pen input |
| Keyboard | Working | Maliit/GNOME on-screen keyboard with Shift, Enter, Backspace, and Hide |
| Physical keys | Working | Volume, Power, Home, Back, Recents, and red Active button mapped |
| Wi-Fi / remote access | Working | Reconnect survives interface renaming; SSH and the single-instance loopback screen service work over the LAN |
| Bluetooth | Working | WCN6850 startup retry, firmware handoff, idle wake, BlueZ discovery, synchronized teardown, and supervised recovery physically tested; WirePlumber Bluetooth audio policy is enabled, pending a paired-headset playback test |
| Speakers | Working | Stock calibration and guarded amplifier sequencing; GNOME volume control works |
| Microphone | Working | Built-in microphone exposed as the normal PipeWire source through a demand-driven bridge |
| Sensors | Mostly working | Accelerometer, light, proximity, magnetometer, compass, and automatic brightness tested; physical rotation and suspend/resume remain to validate |
| Charging | Working | Charger detection and charge state are exposed through UPower to GNOME; 100% fully charged was verified after a cold boot |
| Display sleep | Working | Power-key blank/lock/wake works |
| System suspend | Experimental | Guarded manual shallow suspend and wake passed; automatic idle suspend remains disabled |
| GPU | Experimental | Turnip/Zink can render GNOME, but a KGSL fault was reproduced; software fallback is retained |
| Video | Mostly working | FFmpeg and GStreamer H.264/VP9 use the stock decoder. A real WebKit process selected it, but no accelerated browser launcher is shipped because this kernel cannot provide WebKit's normal user-namespace sandbox |
| Camera | Partial | Separate front and rear launchers publish one 640x480 camera at a time to GNOME Camera. A volatile eight-frame validator confirms delivery and cleans up both sensors; the rear lens-down result is nearly uniform, so a well-lit image and orientation validation remain |
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
- Automatic idle system suspend is disabled while power behavior is still being
  characterized.
- Camera support still depends on proprietary files extracted from the owner's
  matching stock firmware; those files cannot be redistributed here. The front
  and rear cameras are integrated with GNOME as exclusive sources; final rear
  image-quality validation remains.
  See [CAMERA.md](CAMERA.md).

For the complete test history, see the dated files in `docs/reports/`, including
the [GStreamer and WebKit video report](reports/gstreamer-video-20260913.md).
