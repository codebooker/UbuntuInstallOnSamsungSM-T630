# SM-T630 Bluetooth bring-up — 2026-09-13

## Result

The Galaxy Tab Active4 Pro's WCN6850 Bluetooth controller now works under the
native Ubuntu installation through BlueZ and GNOME. The verified boot image is
`output/bluetooth-rxd-wakeup-v7/boot.img`, SHA256
`c9fd8a0025e2c8acc8c7781a077c2af71eb49c01688cf9ae010a4bc8c15118db`.
The boot partition readback matched and the guarded writer verified that
`sda20`, `sda21`, `sda22` and `sde19` were unchanged.

## Root causes and fixes

Samsung's stock kernel disabled HCI UART, while the controller requires a
Samsung/QTI firmware download, board NVM overrides and Qualcomm in-band sleep.
The exact DZE3 kernel was rebuilt with HCI UART/QCA support. The userspace loader
downloads the stock WCN6850 patch and board calibration at 3.2 Mbps, then hands
the live UART to the QCA line discipline.

The upstream QCA driver sent `IBS_WAKE_IND` directly. Samsung's exact QTI HAL
instead performs a receiver-wake pulse first: RTS low, 38400 baud without
hardware flow control, one zero byte, normal UART settings restored, RTS high,
then `IBS_WAKE_IND`. The board-scoped kernel patch reproduces that sequence.

The controller can still miss Linux's first `Write LE Host Supported` command
while settling after firmware handoff. HCI initialization recovers, and the
startup launcher now retries the standard command, verifies its exact successful
completion, and only then launches BlueZ. A redundant `btmgmt info` check was
removed because that utility remains attached as a monitor after printing its
answer. The launcher also handles a transient D-Bus-activated `bluetoothd`
without waiting forever on the UART owner.

A later panic-reboot exposed another bounded startup race: the WCN6850 once
returned a stray `0xff` byte and timed out while changing the UART to 3.2 Mbps.
The firmware loader already powers the controller off on any failed attempt;
the launcher now makes up to three clean attempts, with a settle delay between
them, before declaring Bluetooth unavailable. A manual second attempt on the
same boot completed normally and restored the powered BlueZ adapter.

Stopping that live UART owner then reproduced a kernel use-after-free in
`hci_ibs_wake_retrans_timeout()`: the downstream `qca_close()` used
non-synchronous timer deletion and freed its state while the callback was still
running. Patch 0008 backports the teardown guarantee used by current upstream
Linux. Because Linux 5.4 does not provide `timer_shutdown_sync()`, it uses
`del_timer_sync()` before and after draining the QCA workqueue so queued work
cannot leave a rearmed timer behind.

### Physical verification of synchronized teardown

The replacement LTO kernel and boot image were built from the exact saved
production config and release string. The kernel `Image` SHA-256 is
`bdee4acf92c0a27ae0158fb121e9fe2dce5c66ce868d19e8d4828b2ff59cb882`;
the AVB-padded boot image SHA-256 is
`2bfa801e391476fb9e4f597d31846fc2113b8c0c761130caa4a7fef4dec1876a`.
The guarded writer verified the old v7 boot hash, wrote only `sda19`, read the
new hash back, and verified `sda20`, `sda21`, `sda22`, and `sde19` unchanged.

Physical boot `056cf97f-4035-4b53-8809-8218437b3a82` reached GNOME with Wi-Fi,
the 30% speaker sink, sensors, and a powered Bluetooth adapter. On an earlier
boot, the revised launcher encountered the known transient high-speed UART
timeout and recovered on its next bounded attempt.

The panic reproduction was then repeated deliberately: terminating the live
Bluetooth launcher closed the QCA line discipline and UART owner. The boot ID
stayed unchanged, no kernel exception was logged, and a fresh launcher restored
the powered adapter on its first attempt. This physically verifies patch 0008
against the previously reproducible timer use-after-free.

### Runtime supervision and reaping

The desktop now starts Bluetooth through a single-instance supervisor rather
than leaving the one-shot launcher as an unsupervised shell child. If the UART
owner or BlueZ exits, the supervisor restarts the complete launcher after a
capped delay. Its stop path terminates and reaps the exact owned child.

On boot `056cf97f-4035-4b53-8809-8218437b3a82`, the live launcher was
deliberately terminated under the new supervisor. It logged status 1, waited two
seconds, started a new launcher, and restored a powered adapter without changing
the boot ID or disturbing the desktop, Wi-Fi, audio, or sensors. A subsequent
clean boot `4d826579-5c53-47e3-8edd-dc3d6ffd8d0b` started the supervisor and its
Bluetooth child automatically. The managed GNOME wrapper now reaps inherited
one-shot startup helpers; no zombie processes remained after startup.

## Physical verification

Clean boot `79fdbd99-b920-459c-bd1f-ee2886e431b0` established all of the
following:

- BlueZ, GNOME, Wi-Fi and SSH started automatically.
- The adapter reported powered, SSP, BR/EDR, LE and secure connections.
- Correct HCI replies arrived after 5, 10 and 30 seconds of controller idle.
- A direct management scan completed with 52 discovery events.
- Two sustained BlueZ scans completed normally; the first created 16 D-Bus
  device objects and the second raised the retained total to 20.
- No Bluetooth timeout was logged after the single recovered boot-time LE-host
  miss. No Bluetooth addresses are recorded here.

The remaining early timeout is visible but no longer functional: the verified
retry completes before BlueZ starts. Future work can move the retry into a
kernel delayed-init path if eliminating that benign log line becomes valuable.

## Bluetooth audio policy

The Ubuntu PipeWire installation includes WirePlumber's BlueZ monitor and its
SBC, AAC, aptX, LDAC, FastStream, LC3, and Opus codec plugins. An early
prototype override had kept the monitor disabled because the session did not
yet have logind or a working Bluetooth transport. Both dependencies now exist,
so `51-t630-bluetooth.lua` enables the stock WirePlumber Bluetooth audio policy
while leaving untested Bluetooth MIDI disabled.

Registration of the audio endpoints and preservation of the built-in speaker
and microphone are verified on the tablet. Actual A2DP playback still requires
pairing a headset or speaker and is not yet claimed as physically tested.

On physical boot `84251a48-c3c6-44cf-81bf-5d9f046fb4f8`, WirePlumber restarted
cleanly with the new override. BlueZ then advertised both Audio Source and Audio
Sink profiles. The 30% `Tablet_Speakers` sink and the `Tablet_Microphone` source
remained present and default; WirePlumber logged no BlueZ-monitor failure.
