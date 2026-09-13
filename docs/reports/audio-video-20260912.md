# Audio and acceleration investigation — 2026-09-12

## Audio

The earlier mapper-before-modules sequence lost the one-shot audio locator
notification. A cold first-load test registering the audio modules before
starting pd-mapper produced `audio_notifier_reg_service: service PDR_ADSP is
in use`, `apr_adsp_up: Q6 is Up`, and populated the APR/q6core/bolero/machine
devices. This is implemented in `ubuntu/test-audio-cold-order.sh`, manual only.

The exact live DT also requires `wcd938x_slave_dlkm`, separate from the parent
codec module and absent from its symbol dependencies. Added it to the verified
stock-module resolver. TX SoundWire slave binds; RX device
`wcd938x-slave.d01170224` cannot enumerate. Retrying only that unbound device
through `drivers_probe` confirms the same failure. The card remains deferred at
`TX_CDC_DMA_TX_5` with -517. No ALSA card or speaker playback yet. No speaker
gain, calibration, protection, or arbitrary GPIO/voltage changes were made.

**Do not live-unload the stock audio modules.** The attempted normal, non-forced
unload of `snd_soc_cs35l45_i2c` caused a NULL dereference at
`snd_soc_tplg_component_remove+0x34`, via `snd_soc_unregister_component` and
`devm_component_release`, at previous-boot uptime 952.211 seconds. The tablet
restarted. `retry-audio-order.py` is now explicitly disabled locally and on
the tablet. No audio experiment is enabled at startup.

Recovered boot ID: `7c4d15c9-3d2d-4069-bb5d-1a65c113f2ef`.
GNOME initially refused startup due to its stale X3 socket/lock after the crash.
Added `t630-x11-recovery.py`, which checks `/proc/net/unix`, verifies owner/type,
and quarantines only inactive X3 files into `/var/lib/t630/stale-x11`. No live
X server is stopped. Integrated it into the root GNOME launcher. Full-screen
GNOME and Firefox/YouTube were visually verified restored. Wi-Fi, SSH and the
loopback-only screen tunnel returned. `dpkg --audit` was clean.

## Video codec engine

Samsung V4L2 nodes: `/dev/video32` decoder, `/dev/video33` encoder, driver
`msm_vidc_driver`, kernel driver `msm_vidc_v4l2`. Opening them initially failed
with ENOMEM because `vpu20_1v.mdt` was missing from the caller's firmware path.

`stage-video-firmware.sh` validates the APNHLOS partition identity and FAT
filesystem, mounts it read-only/noexec/nodev/nosuid, copies exact stock VPU and
A660 ZAP firmware plus vendor A660 GMU/SQE files, compares copies, and unmounts.
Files remain private to the tablet under `/opt/t630/video-firmware`.
Links are supplied in both the outer initramfs and Ubuntu
`/run/input-firmware`: synchronous kernel requests can use the Ubuntu caller's
root. No firmware partition was written.

After staging, decoder QUERYCAP and format enumeration succeeds: compressed
MPEG-2, H.264, HEVC and VP9; capture NV12 and Qualcomm formats. The Samsung
driver omits VIDIOC_TRY_FMT and accepts USERPTR only, while Ubuntu FFmpeg's
generic V4L2 M2M path requires TRY_FMT and MMAP.

`t630-v4l2-compat.so` is an exact-device-guarded, process-scoped adapter for
`msm_vidc_driver` / `msm_vidc_vdec`. It emulates TRY_FMT through S_FMT, gives
FFmpeg MMAP-shaped buffers backed by ION system-heap allocations, then submits
them using Qualcomm's USERPTR convention: userspace address plus dma-buf fd in
the reserved plane field. It also hides the vendor extradata plane from FFmpeg
and moves NV12 chroma from Qualcomm's 512-scanline-aligned luma offset to the
ordinary contiguous offset expected by FFmpeg. It is loaded only by the Videos
launcher, never globally.

Working evidence:

- 30-frame 320×240 and 1280×720 H.264 hardware output matched software output
  exactly: infinite PSNR independently for Y, U and V.
- Five repeated H.264 runs, a 120-frame 720p run and a 60-frame VP9 run exited
  cleanly. The 720p null-output run was roughly 10.5 times real time.
- A normal UID 1000 process decoded H.264, and the touch-friendly mpv wrapper
  played the 720p clip through the live nested GNOME Wayland display and exited
  cleanly.
- HEVC and MPEG-2 vendor paths hung during bounded tests, so the launcher does
  not select those hardware decoders. mpv automatically tries its normal
  software decoders after the H.264/VP9 priority list.

Persistent pieces are `/usr/local/lib/t630/t630-v4l2-compat.so`,
`/usr/local/bin/t630-video-player`, the `Videos` desktop entry and default video
MIME associations. Video32/33 and ION are root:render 0660, with exact node,
device-number and sysfs-driver checks. VPU firmware staging runs before every
GNOME launch. Browser video acceleration remains unimplemented.

Later camera coexistence testing found that the camera module's `mdev -s` cold
scan reset unrelated live device permissions, including FUSE, ALSA, graphics
and codec nodes. The final camera helper therefore does not run a global scan:
it creates only the exact kernel-advertised video0/1, v4l-subdev0–16 and media0/1
nodes, then runs the exact-device permission verifier. A missing media1 node was
recreated from its sysfs device number as a live creation-path test. Afterward,
a cold camera start/capture/complete-stack stop followed by a normal-user
1280x720 H.264 hardware decode passed; FUSE and all audio/render nodes retained
their intended modes, and speaker audio remained unmuted. A generated 320x240
H.264 stream still stalls this vendor decoder, while generated 320x240 VP9 and
1280x720 H.264 complete, so the launcher retains software fallback for
unsupported/problematic streams.

## GPU rendering

KGSL reports Adreno642Lv1. Ubuntu Mesa 25.2.8's packaged Vulkan driver enumerates
DRM only; an explicit Turnip-only probe fails to find a GPU. The desktop remains
llvmpipe/Pixman. Installed Ubuntu's Vulkan and V4L2 tools plus FFmpeg and build
dependencies. No sandbox or privilege-authentication bypass was introduced.

Building upstream Mesa 25.2.8 with `freedreno-kmds=kgsl`, Turnip only, under
`/opt/t630/mesa-25.2.8-kgsl`; no replacement of Ubuntu Mesa or GNOME environment.
Source archive SHA256:
`097842f3e49d996868b38688db87b006f7d4541e93ce86d2f341d8b3e7be7c93`.
Build recipe `ubuntu/build-turnip-kgsl.sh`; Meson 1.7.2 in an isolated build venv.
Two low-priority build jobs preserve resources for the running desktop.

Primary references: [Mesa source releases](https://archive.mesa3d.org/),
[Mesa Freedreno documentation](https://docs.mesa3d.org/drivers/freedreno.html),
[Qualcomm audio notifier reference](https://android.googlesource.com/kernel/msm-extra/+/refs/heads/android-msm-redbull-4.19-android14/dsp/audio_notifier.c),
[Qualcomm APR reference](https://android.googlesource.com/kernel/msm-extra/+/refs/heads/android-msm-redbull-4.19-android14/ipc/apr.c).
Reference audio sources are not claimed to match Samsung's module binaries
exactly. Live DT, exact-stock modules and observed kernel output are authoritative.

### GPU verification and next boot

The isolated Turnip build finished. Binary SHA256:
`3647a83a3223bf29cb019950d3fd288977517f1a38aad7ffe2a449244c90098e`.
Vulkan enumerates an integrated Qualcomm GPU (`0x5143`, device `0x6030500`),
named Adreno 7c+ Gen 3 by Mesa's fallback chip mapping, not llvmpipe. Kernel KGSL
calls the same hardware Adreno642Lv1. Stock A660 ZAP firmware loads successfully.

Normal user `tablet` added to standard `render` group; only `/dev/kgsl-3d0` and
`/dev/ion` assigned root:render 0660 in RAM. ACLs are unsupported on these nodes.
No world-writable graphics devices or root desktop apps were introduced.

Native Vulkan cube: direct presentation gives SIGBUS, but
`MESA_VK_WSI_DEBUG=sw` works. This flag uses CPU-copy presentation, not CPU
rendering. A 120-frame test completed with exit 0; a longer test was visually
verified as a correctly rendered cube, then stopped by its timeout.
OpenGL contexts identify Zink over Turnip, GL 4.6 / GLES 3.2. Native Wayland
es2gears produces a black window; not considered working. GLX on private X3 with
`LIBGL_KOPPER_DRI2=1` renders correct gears, visually verified, around 185 FPS.
Disabling Kopper segfaults that test; do not set LIBGL_KOPPER_DISABLE.
`t630-gpu-env` is an opt-in test wrapper, not a global environment override.

Owner explicitly authorized a clean restart for revised sound startup and GPU
GNOME testing. Added one-shot `/etc/t630/gpu-next-boot` handling: autostart
consumes the marker, prepares exact GPU firmware/device permissions, and wraps
only GNOME (not its software host Xwayland) in the GPU environment. Subsequent
boots still default to llvmpipe. The clean, unmount-first restart was dispatched;
its result and accelerated GNOME still require verification below.

### Clean restart results and Wi-Fi recovery

Boot ID `33b5b8ea-2930-4872-9975-35d450477196`. GPU one-shot marker consumed,
but the initial GPU launch failed because the sanitized launcher PATH omitted
`/usr/sbin` (`blkid` unavailable in firmware staging). Started the same GPU
GNOME launcher manually with a complete PATH; fullscreen desktop visually
verified in `gnome-gpu-first-screen.png`. GNOME PID 881 maps the isolated Turnip
library and emits Zink diagnostics. Firefox also identifies Zink/Turnip.
Host Xwayland and Weston remain software-presented. This is not proof of video
decode acceleration. Subsequent boots still default to software GNOME.

Both firmware stagers now set their own complete system PATH; autostart PATH
also corrected. Video staging tested successfully under the previously failing
sanitized environment. Fix deployed, but automatic launch on another clean boot
has not yet been retested. Brief fallback-desktop visibility remains inherent
to the current nested architecture; the unusually long delay this time was
the failed launch followed by manual recovery.

udev renamed the primary Wi-Fi interface from wlan0 to wlp1s0; [redacted Wi-Fi network] was pinned
to wlan0. Saved profile now matches the primary radio MAC instead of its name,
preserving existing credentials. It auto-connected after the profile update.
The initial nmcli call lost its bus reply while NetworkManager was restarted;
the saved change was verified afterward and survived `nmcli connection reload`.
NetworkManager dispatcher now accepts real wireless interfaces regardless of
name. Legacy connection/status helpers were updated likewise. SSH and screen
tunnel restored; HTTPS request to YouTube returned HTTP 200. No Wi-Fi secrets
were printed. Persistence across another reboot remains to be verified.

### First complete ALSA sound-card registration

Cold-order module loading bound both WCD938x SoundWire slaves, advancing the
deferred sound-card link to SLIMBUS_7_RX. Exact stock `modules.load`, module
dependencies and live DT identify missing slimbus, slimbus-ngd, btpower and
bt_fm_slim drivers. Loaded those without unloading anything. Kernel registered
`lahaina-yupikidp-snd-card`, including both CS35L45 amplifiers and PCM endpoints.

The initramfs lacks automatic creation of these dynamic ALSA device nodes.
`t630-sound-nodes.py` creates only sysfs-advertised major-116 nodes with exact
minor numbers, root:audio 0660, rejecting conflicting existing nodes. Installed
ALSA utilities and PulseAudio client utilities; package audit is clean. No
desktop audio daemon or speaker playback has been enabled yet.

`test-speaker-protection.py` selects only stock XML Protection firmware,
preload and boot controls, while checking both AMP and DSP playback enables
are off. Both speaker DSPs loaded the exact stock protection firmware and
reported execution started. No gain, boost/protection limit, or amplifier-enable
changes were made. Driver initially applied its default RAM calibration because
Android's calibration-import step was missing.

Read-only/no-journal-replay inspection of verified EFS/sec_efs partitions found
this tablet's seven calibration files in sec_efs/cirrus. Only those calibration
files were read; no broad EFS dump or factory-partition write. Import helper
validates their fixed-size decimal format/range, unmounts the partition, then
caches existing values through the stock sysfs calibration setters and verifies
readback. RDC values are 9156/9108 and temperature 28 C. No recalibration ran.

The already-booted speaker firmware still holds the earlier default RDC 8580.
Its boot-control reset is rejected with EPERM; the diagnostic script stops at
that rejection. No security bypass or module unload was attempted. The manual
cold-order test now imports calibration before speaker DSP preload/boot, keeping
amplifiers disabled. A further owner-approved clean restart is required to test
that corrected order before any audible playback. Audio is NOT working yet.

### Second authorized clean restart and protected playback tests

Owner authorized another restart. Boot ID now
`73a757c9-5719-42b9-8cd1-84adddc86404`. GPU GNOME autostart succeeded without
manual recovery (PID 824, isolated Turnip mapped). Screenshot
`gnome-gpu-autostart-verified.png` shows the full GNOME overview. Wi-Fi returned
automatically as **wlan0** this time, confirming the MAC-matched connection works
under either interface name. SSH/screen service also started automatically.
Radio firmware startup still takes roughly 75–90 seconds; not fixed here.

Dispatched revised manual cold-order sound test over USB after boot. Sound card
registered; factory calibration loaded before protection firmware. Kernel
confirmed RDC 9156/9108, temperature 28, VIMON status 2 with saved VSC/ISC values.
Both DSPs start successfully, amplifiers remain off until the bounded test.

Silent 48kHz stereo S24_LE PCM test through stock QUIN_TDM_RX_0/MultiMedia1 passed.
Stock source/slot/protection controls selected from this firmware's mixer XML.
No amplifier gain or protection limit changes. A -50 dBFS 3-second stereo test,
then a -40 dBFS 6-second test, both completed, with amplifiers/routes disabled in
finally blocks. Owner heard neither. PLL locks during playback; amp/DSP power
events occur. Overtemperature, overexcursion and abnormal mute counters are 0.
No claim of audible sound success.

Found separate `Playback 0 Volume` at 0 (range 0..8192). Current bounded test
sets stream gain to 8192 (Qualcomm unity scale), preserves the -40 dBFS source,
then restores the old stream volume and disables amplifiers/routes. User
audibility confirmation is pending. Desktop sound server remains unconfigured.

### Audible sound and normal desktop audio achieved

Owner reported silence after the stream-volume test too. A subsequent S16_LE
probe set Playback 0 Volume while the PCM stream was actually open (the setter
silently ignores writes with no substream runtime). This distinguishes the
closed-stream zero reading from a proven active mute; the earlier inference
that zero alone explained the silence was not established.

Both `Fast Use Case Delta File` controls were unselected (4294967295). Applied
`cs35l45-default.bin` exactly as specified in the stock XML, with amplifiers off.
The next S16_LE / -40 dBFS stereo test was audible: owner said “I heard it that
time. It was very, very quiet.” The cold-order protection helper now also applies
this stock preset. Multiple variables changed across tests, so the preset is
the last correlated correction, not proof it was the sole cause.

Started PipeWire 1.0.5, pipewire-pulse and WirePlumber 0.4.17 as normal UID 1000;
tablet added to standard audio group. No TCP audio listener. Explicit
`module-alsa-sink` uses hw:0,0, S16_LE, stereo 48kHz, mmap=false, tsched=false.
GNOME sees Tablet_Speakers, with ordinary software volume/mute controls. Initial
volume 30%; user increased it via normal controls. Owner confirmed normal app
sound: **“it works.”** Sink observed RUNNING. Normal paplay also completed.

Automatic ALSA profiling is disabled in this prototype's isolated WirePlumber
config because this Android card has no Ubuntu UCM and exposes thousands of
nonstandard controls. Bluetooth monitor disabled: Bluetooth audio isn't brought
up and there is no logind. No microphone/capture route was enabled. USB/Bluetooth
audio auto-discovery is therefore not claimed working.

Important late-startup bug: outer Wi-Fi loader calls `mdev -s`, resetting sound
and KGSL/ION permissions to root:root. Added narrowly matched ALSA root:audio and
KGSL/ION root:render 0660 mdev rules. Guarded helper preserves unknown configs,
serializes changes, and reapplies the known rules before desktop/audio startup.
Repeated the actual outer `mdev -s`: permissions stayed correct. No device made
world-writable. This also fixes new GPU apps losing access after Wi-Fi startup.

Persistent configuration installed:
- `/etc/t630/gpu.enabled` selects GPU GNOME by default. `gpu.disabled` opts out.
  A failing GPU session retries software GNOME; physical Weston fallback remains.
- `/usr/local/sbin/t630-audio-start` is dispatched in the background by desktop
  autostart, never blocks GNOME/network startup. It performs the guarded first
  load, factory calibration, stock protection/preset, ALSA nodes, waits for the
  GNOME session and PipeWire core, creates the explicit sink, initializes it at
  30% muted, enables the calibrated route, then unmutes. Failure after sink
  setup mutes and disables the route. `/etc/t630/audio.disabled` opts out.
- `/run/t630-audio-ready` prevents duplicate initialization during one boot.

Syntax, Python compilation, non-mutating startup checks and current-running
audio-core checks passed. Wi-Fi/GPU automatic startup was verified on the second
restart, but this FINAL integrated audio-autostart hook and GPU persistent flag
have not had another cold-boot test. Do not claim sound reboot persistence as
fully verified yet. Current tablet remains playing normal app audio on Wi-Fi.
At this checkpoint video hardware decoding was still unimplemented; the later
hardware-video section above supersedes that state. Graphics rendering
acceleration remains separate and works through Zink/Turnip plus CPU-copy
presentation.

### Physical volume buttons

User requested physical volume buttons next. Kernel exposes volume-down via
qpnp_pon/event0 and volume-up via gpio_keys/event4; Weston recognizes both as
keyboards. GNOME's static XF86AudioLowerVolume/RaiseVolume bindings were already
configured, but gsd-media-keys was not running in this custom session.

Started `/usr/libexec/gsd-media-keys` as tablet through the existing session
launcher. Owner confirmed both volume adjustment and the GNOME volume indicator
work. No raw-key remapping, input grab, root key-control daemon, or kernel/driver
change was needed. A bounded read-only observer logs only volume presses, not
other keys; it does not become a background service.

`t630-gnome-session` now starts the normal-user media-key service once its nested
display socket exists and cleans it up with the session. Installed and syntax
checked; this final startup addition has not yet had another reboot test.

### Red Active button — installed, awaiting GNOME restart and physical test

Owner chose the keyboard for the red button. Other non-volume buttons have
not been assigned new actions. The existing top-bar keyboard control remains.

Verified gpio_keys EVIOCGKEYCODE_V2 entries by index: 0=115 (volume up),
1=254 (recents), 2=158 (back), 3=172 (home), 4=252 (Active).
`t630-red-button.py`, installed as `/usr/local/sbin/t630-red-button`, guards
the installation ID, DT hot_key code, unique gpio_keys device and full expected
keymap, then maps only index 4 to KEY_F14=184. The actual running XKB map
translates this to XF86Launch5; no existing GSettings binding used that symbol.
F13 was deliberately not used: it maps to XF86Tools, already used by Settings.
No input grab, persistent raw-key reader, device-permission widening or kernel
rebuild. Apply/readback/restore passed; **live keycode was restored to stock252**
while the current GNOME session still has the old extension in memory.

Tablet Keyboard extension version2 and compiled settings schema are installed.
The XF86Launch5 binding shares the top-bar show/hide action, ignores autorepeat,
and applies only in NORMAL/OVERVIEW, not on a lock screen. Existing touchscreen
keyboard settings are unchanged. Desktop autostart applies the guarded keymap
before launching GNOME, with failure leaving desktop startup operational.

Python compilation, JavaScript syntax, strict schema compilation, settings
readback, shell syntax and autostart --check passed. Running GNOME still reports
extension version1: GNOME46 explicitly deprecates live ReloadExtension, so a
desktop restart is required. No restart performed and **physical red-button
show/hide has not yet been verified**. Before a desktop-only restart, save user
work. Apply t630-red-button manually if bypassing desktop-autostart. Preserve
audio processes/session integration when planning that restart.

Previous extension and autostart backups:
`/usr/local/share/t630/backups/red-button.e7EoLN/` on the tablet.
Runtime keymap rollback: `/usr/local/sbin/t630-red-button --restore`.

### Active-key activation and integrated reboot test

Owner clarified the tablet is lab equipment with no ongoing work to preserve;
routine setup/test restarts do not need repeated save-work approval. This does
not authorize unrelated destructive changes or protection bypasses.

Clean reboot to boot ID `4005a669-d2d0-4fea-8ace-3e15ea30ec36` passed:
- Full-screen accelerated GNOME returned; its process maps contained the
  isolated Turnip library and Cogl compatibility preload.
- Wi-Fi connected automatically as wlan0; HTTPS YouTube returned200, SSH and
  the loopback-only screen service came back. The Mac tunnel was reopened.
- Audio first-load, factory calibration, stock protection/preset, PipeWire
  sink and route completed automatically, with `/run/t630-audio-ready` present.
  Sink was unmuted at the intended30%; media-key service started automatically.
- Late mdev scan preserved root:audio/render0660 on relevant device nodes.
- Tablet Keyboard extension version2 loaded ACTIVE without extension errors;
  Active-key mapping read back184. Battery17%, reported Charging.

First physical Active-key test failed despite the bounded observer receiving
two complete code184 press/release pairs. An injected XF86Launch5 into the
host Xwayland successfully opened the keyboard, isolating the issue below the
GNOME binding. Weston had already opened gpio_keys before autolaunch remapped
its supported key. A targeted udev remove/add refreshed only gpio_keys, after
which the owner confirmed **"works now"** for keyboard show/hide.

Added `/etc/udev/rules.d/71-t630-active-key.rules` to run the guarded mapping on
the gpio_keys event-device add, before the outer startup's udev-settle/Weston
launch. Rule verification and udev-test RUN selection passed. No input grab
or persistent reader; the45-second observer exited. Autolaunch mapping remains
as an idempotent fallback. A second clean restart was dispatched to verify
the new early mapping order.

### Hardware-video application and cold-boot verification

The final adapter binary SHA256 is
`3cf4fc687dd19a2dc46c6e6d6b7b2d46a9f6255a39f7723e6450fe7838a8fe7c`.
Its source, launcher, desktop entry, firmware hook, guarded permissions and MIME
associations were installed before an ordinary unmount-first restart.

Fresh boot `1fccce7c-1b50-4db0-ab22-0c5b59b1285f` verified:

- [redacted Wi-Fi network] reconnected as wlan0; GNOME deliberately used the software fallback
  selected by `/etc/t630/gpu.disabled`.
- The Tablet_Speakers PipeWire sink returned at 30%, and audio startup reported
  ready.
- VPU firmware was staged from the preserved stock copy. Video32/33, ION and
  KGSL permissions remained root:render 0660 after the late device scan.
- The installed adapter hash matched; MP4, WebM and Matroska all resolved to
  `t630-hardware-video.desktop` in the isolated GNOME profile.
- As UID1000, 60 H.264 frames opened `msm_vidc_driver` / `msm_vidc_vdec` and
  decoded at about 13.6 times real time. A 60-frame VP9 run also passed.
- Launching the installed desktop entry through GIO opened mpv on the live
  GNOME Wayland socket, presented 1280×720 NV12 through wlshm, played to EOF
  and left no decoder/player process behind.
- `dpkg --audit` was clean. All 47 host regression tests passed.

The adapter behavior follows Qualcomm's downstream
[msm_vidc buffer handling](https://android.googlesource.com/kernel/msm/+/c580026d9a771c26cffa2253a8dd7187405c3c7a/drivers/media/platform/msm/vidc_3x/msm_vidc.c)
and documented
[Venus NV12 alignment](https://android.googlesource.com/kernel/msm.git/+/6d464a5c1b01f89743d1a320b7247574495cfb9d/include/uapi/media/msm_media_info.h).
Unsupported decoders fall through according to the
[mpv decoder-selection rules](https://mpv.io/manual/stable/).

### Next hardware gap: Bluetooth transport

Installed Ubuntu BlueZ 5.72, its OBEX service and GNOME Bluetooth Send-To.
Package audit remains clean; these daemons are not falsely advertised as a
working adapter.

Exact live evidence identifies the missing kernel layer:

- The QCA6490 power device is bound to `bt_power`, and rfkill exposes
  `bt_power` soft-blocked. Stock `btpower` and `bt_fm_slim` modules are loaded.
- Android's preserved vendor init configuration assigns `/dev/ttyHS0` to its
  Bluetooth service, and the live serial node is provided by msm_geni_serial.
- The exact running kernel config has Bluetooth core, BR/EDR, LE and HCI SDIO,
  but explicitly has `CONFIG_BT_HCIUART` disabled. No HCI device exists and no
  matching external HCI-UART module is present. Starting BlueZ alone cannot
  bridge the UART.
- Samsung's official source catalog lists
  `SM-T630_15_Opensource_T630XXSBDZE2_..._T630XXSBDZE3.zip` for this exact build.
  Download is gated by Samsung's hCaptcha and must be completed by the owner.

The next implementation is to build and validate the QCA HCI-UART transport
against Samsung's exact source/config, initially as a reversible test. Do not
power-cycle the radio or flash a speculative kernel built from a neighboring
model. The Android-common 5.4 QCA driver documents the transport architecture,
but it is not a substitute for Samsung's exact source and module ABI.
