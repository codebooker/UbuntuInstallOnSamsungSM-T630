# Cold-boot subsystem coexistence — 2026-09-13

Physical boot `e3fdbec7-82e2-483a-b60e-41673728ffa5` followed a clean,
unmount-first restart through the recovery-side shutdown helper. The following
sequence was then tested on the persistent Ubuntu root:

1. Wi-Fi, SSH, Weston, nested GNOME, PipeWire, WirePlumber, the built-in
   speaker/microphone routes, BlueZ, and the WCN6850 supervisor returned
   automatically.
2. WirePlumber loaded `51-t630-bluetooth.lua`; BlueZ advertised both Audio
   Source and Audio Sink profiles without manual intervention.
3. The front-camera validator cold-started the isolated Android camera stack,
   captured eight 640x480 I420 frames with measurable luma contrast, deleted
   the temporary stream, and stopped the whole compatibility stack.
4. A normal UID 1000 process generated and decoded 60 frames of 1280x720 H.264
   through `/dev/video32`. FFmpeg selected `h264_v4l2m2m`, identified
   `msm_vidc_driver` / `msm_vidc_vdec`, completed at 13.2 times real time, and
   exited cleanly.
5. FUSE, KGSL, ION, video32/33, DRM render, and ALSA control permissions still
   matched their expected owner, group, and mode. The speaker remained unmuted
   at 30%, the tablet microphone remained default, Bluetooth remained powered,
   and both audio profiles remained registered.
6. No camera compatibility process remained and the current boot log contained
   no panic, oops, KGSL fault, or watchdog-lockup marker.

This verifies the prior camera-scan permission fix across a real cold boot and
demonstrates camera, hardware decode, local audio, graphics-device access, and
Bluetooth-audio policy coexisting in one session. It does not replace the
still-pending physical A2DP playback test with an external device.

