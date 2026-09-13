# SM-T630 microphone bring-up — 2026-09-13

## Result

The built-in main microphone is now exposed to the normal GNOME session as
`Tablet_Microphone`. It is the default PipeWire/PulseAudio-compatible source,
is unmuted at 100%, and uses Samsung's stock high-gain voice-recognition path.
The capture hardware is opened only while an application is recording.

## Board route

`t630-microphone-route.py` parses the exact DZE3 stock
`mixer_paths.xml`, verifies the expected main-microphone, voice-recognition and
audio-record values, and then applies that route. The selected codec gain is
Samsung's own `vr-main-mic` profile (`TX_DEC0=101`, `ADC1=10`), not an invented
gain. Its direct five-second probe peaked near -20 dBFS without clipping; the
ordinary record profile was about 31 dB quieter.

PipeWire 1.0.5's ALSA compatibility source stalled on the downstream Qualcomm
MultiMedia1 capture PCM. Direct ALSA capture remained continuous, so the
installed `t630-microphone-bridge` feeds that proven stream through a private
FIFO to `module-pipe-source`. The bridge watches the source state every 200 ms:
it starts `arecord` when an application changes the source to RUNNING and stops
it again at idle. The FIFO and PID file are private to UID 1000's runtime
directory; no audio device permissions were widened.

## Verification

- An eight-second GNOME-session capture produced 294,912 samples with peak
  3047 and no clipping. The shorter file duration reflects `parec`'s unflushed
  client buffer when killed by the test timeout, not a source stall.
- A physical acoustic loopback played an 880 Hz tone through the tablet
  speakers and recorded it through the built-in microphone. The detected
  880 Hz component was about 39 dB above nearby 700 Hz and 1000 Hz bins.
- When the test client exited, the PipeWire source returned to IDLE/SUSPENDED
  and no `arecord` process remained.
- Clean boot `939f9aa6-4303-4cd9-8eda-245e33b80022` restored GNOME, the speaker
  sink, `Tablet_Microphone`, the default source selection and the demand-driven
  bridge. A post-boot recording peaked at 3094 with no clipping, then released
  the hardware at idle.

## Installed pieces

- `/usr/local/share/t630/t630-microphone-route.py`
- `/usr/local/bin/t630-microphone-bridge`
- microphone setup inside `/usr/local/sbin/t630-audio-start`

The working speaker route remains independent and returned at its guarded 30%
startup volume during the same reboot.
