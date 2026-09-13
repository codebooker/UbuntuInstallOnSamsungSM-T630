# Rear camera exposure, color, and lifecycle follow-up

Date: 2026-09-13. Device: one physical SM-T630 on the exact
`T630XXSBDZE3` baseline. No frame, proprietary binary, calibration data, device
identifier, or raw kernel log is retained in this repository.

## Physical exposure correction

The first usable rear profile used ID 0, `TEMPLATE_STILL_CAPTURE`, AE off,
60,000,000 ns, ISO 1600, and rear-only gamma 2.5. In a brighter real scene its
published PipeWire output measured mean luma 206.37 (median 215, minimum 37),
and physical inspection found it slightly overexposed and too yellow.

The deployed sensor baseline is now 30,000,000 ns at ISO 800. Capture result
metadata exactly echoed both values with `ae_state=0`. Before color tuning, an
eight-frame volatile sample measured mean luma 162.26 and 1.39% near-white
pixels. After color tuning, a later sample measured mean 160.35 and no
near-white pixels. The sample tool deleted each raw I420 stream immediately.

## White-balance finding

With required manual rear AE, Samsung's AUTO white balance stays inactive:
`awb_state=0`, despite reporting applied gains of
`1.391,1.000,1.000,2.469`. Camera characteristics advertise AWB modes
`0` through `8`. Selecting the advertised incandescent preset made the session
active but delivered no frames, so the preset was removed rather than risking
more HAL state changes.

The known-good AUTO request now feeds a small Ubuntu-native I420 filter before
GStreamer. The first physical trial at 0.92× red and 1.25× blue was reported as
much improved but still slightly yellow, so the current profile applies 0.90×
red and 1.32× blue in BT.601 space only to the rear. Physical inspection then
accepted the result as okay and not too blue; slight warmth remains.
A deterministic 2×2 yellow test moved U/V from 90/150 to 98/144 while
keeping its four luma values within two levels. Live aggregate chroma also moved
away from yellow.

A touch/S Pen-friendly **Rear Camera Color** app now gives the user a live
warmer/cooler range around the accepted profile. It persists one integer from
−100 through +100 using an atomic replacement. The root-owned filter treats
missing, malformed, and out-of-range values as zero, reloads the value every 15
frames, and maps the full range to bounded red gains 1.00×–0.80× and blue gains
1.02×–1.62×. No camera restart or privileged UI action is required. Live UI
validation drove the filter through both endpoints and back to +34 cooler while
the same camera process and stream remained active.

## Stock driver panic and safer teardown

Rapid queued front/rear transitions reproduced a warm-reset kernel panic in
the stock `camera.ko`. `/proc/last_kmsg` identified
`cdm_write_genirq+0x64/0x90`, called through the camera CDM/IFE submission path
by Samsung's provider process. The raw log was inspected locally and was not
committed.

The control plane now:

- rejects a new switch while another transition holds the lock;
- terminates the downstream GStreamer consumer first;
- lets the capture client treat EPIPE as a normal condition and close its
  ACamera session and device;
- waits five seconds for hardware quiescence between clients; and
- retains a bounded, exact-process-group TERM/KILL fallback.

A live rear close after these changes ended with `session closed` and preserved
the boot ID. After final color acceptance, another close also removed the
capture client, color filter, GStreamer process, and PipeWire node while
preserving the boot. An initial implementation used Bash process substitution,
but this rootfs has no `/dev/fd`; the deployed version uses a portable
`ps | while read` pipeline.

## Clean-boot findings

A clean boot changed the block minor for the fixed `super` partition symlink.
The camera mount helper now validates `sda26` by partition name and size, then
reads its current major/minor from `/sys/class/block/sda26/dev` instead of
hard-coding `259:10`.

The normal stop helper also exposed a PATH ambiguity: after unmounting Ubuntu,
an SSH-originated environment could still resolve `reboot` to Ubuntu's systemd
wrapper. The helper now calls `/bin/busybox reboot -f` explicitly. Boot
`ba2d8c70-99c8-4bae-8e26-b106c3a3a091` restored GNOME, Wi-Fi on the saved
network, SSH, the corrected mounts, and the 30 ms / ISO 800 rear stream.
