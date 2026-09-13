# Hardware and integration status

Last updated: 2026-09-13. Unless stated otherwise, results are from one physical
SM-T630 on the exact `T630XXSBDZE3` baseline.

| Area | State | Notes |
| --- | --- | --- |
| Boot | Working | Stock downstream kernel with a replacement Ubuntu initramfs; Ubuntu root on userdata |
| Display | Working | Internal 1920×1200 panel through DRM/MSM; full-screen nested GNOME |
| Touch | Working | Finger coordinates and click/drag corrected |
| S Pen | Working | Position and clicking corrected; GNOME keyboard accepts pen input |
| Keyboard | Working | Maliit/GNOME on-screen keyboard with Shift, Enter, Backspace, and Hide |
| Physical keys | Working | Volume, Power, Home, Back, Recents, and red Active button mapped |
| Wi-Fi | Working | Reconnect survives interface renaming; SSH works over the LAN |
| Bluetooth | Working | WCN6850 UART initialization, firmware handoff, idle wake, and BlueZ discovery tested |
| Speakers | Working | Stock calibration and guarded amplifier sequencing; GNOME volume control works |
| Microphone | Working | Built-in microphone exposed as the normal PipeWire source through a demand-driven bridge |
| Sensors | Mostly working | Accelerometer, light, proximity, magnetometer, compass, and automatic brightness tested; physical rotation and suspend/resume remain to validate |
| Charging | Working | Charger detection and charge state observed |
| Display sleep | Working | Power-key blank/lock/wake works |
| System suspend | Experimental | Guarded manual shallow suspend and wake passed; automatic idle suspend remains disabled |
| GPU | Experimental | Turnip/Zink can render GNOME, but a KGSL fault was reproduced; software fallback is retained |
| Video | Partial | Stock decoder adapter passed tested H.264 and VP9 playback; browser integration is absent |
| Camera | In progress | Stock camera kernel module, Android provider, CameraService, calibration, and stream configuration run; first output-frame plumbing is still being completed |
| Security | Lab configuration | GNOME password lock works, but the retained recovery compositor and USB root console mean this is not a hardened full-device login boundary |

## Known limitations

- The public repository does not yet ship a ready-to-flash Ubuntu image.
- The first device uses an unlocked bootloader and reports orange verified-boot
  state. Knox warranty state is permanently tripped.
- Recovery to stock was prepared but has not been exercised end-to-end on the
  development tablet.
- GPU acceleration is opt-in; software rendering is the safe fallback.
- Automatic idle system suspend is disabled while power behavior is still being
  characterized.
- Camera support is a source-level experiment and currently depends on
  proprietary files extracted from the owner's matching stock firmware. Those
  files cannot be redistributed here.

For the complete test history, see the dated files in `docs/reports/`.
