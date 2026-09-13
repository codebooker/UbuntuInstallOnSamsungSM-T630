# Timed shallow suspend after the IPA firmware fix

Device boot: `fd8bcf77-e2ef-4405-993b-0b7928404b79`.
Owner unplugged; battery Discharging, USB not attached, IPA ONLINE.
Stock kernel and `lpm_levels.sleep_disabled=Y` unchanged.

## Comparisons

1. Vendor unicast-MAC wake rule: first attempt aborted during process freeze
   (EBUSY, no named stuck task, 0.003seconds). A subsequent attempt completed
   suspend for0.923seconds, then a UDP discovery packet from port1900 to2021
   triggered WLAN PATTERN_MATCH_FOUND. Unicast-only filtering is therefore not
   sufficient on this network.
2. Temporary nonmatching packet rule `06:01:000000000000:3f`: successful sleep
   for16.060seconds. RTC interrupt increased1 and wake reason explicitly named
   IRQ216 `pm8xxx_rtc_alarm`. Total elapsed16.761seconds.
3. Repeat of the same timer test: successful sleep16.556seconds; RTC interrupt
   increased1, same RTC wake reason. Total elapsed17.220seconds.

The15-second relative alarm has coarse RTC/offset rounding; both tests ran to
their alarm rather than waking early. Suspended duration is measured from the
change in CLOCK_BOOTTIME minus CLOCK_MONOTONIC, not just dmesg text. Test2's
kernel timekeeping duration agreed. Firmware pattern changes were removed in
finally after every test, with successful exact-string deletion reported.

After timer wake: Wi-Fi SSH/[redacted Wi-Fi network] connected, GNOME ScreenSaver still active,
normal speaker sink present, IPA ONLINE, display preference83/300 unchanged,
RTC alarm empty. No auto-suspend policy enabled. This is shallow system sleep,
not validated deepest-SoC sleep or a battery-endurance measurement.

## Physical Power wake test

Added a45-second backup-alarm variant. It reuses the existing lock-and-blank
function and state file so the normal Power monitor will restore light after
the wake button, without unlocking. Owner was asked to press Power after five
seconds dark. Result to be recorded after the test.

The physical test passed: one initial EBUSY during device suspend, then the
second bounded attempt slept33.709seconds. Wake reason was IRQ212
`pon_kpdpwr_status`, RTC IRQ delta0. The owner confirmed the lock screen returned.
The Power monitor restored brightness and the backup alarm was cleared.

## Normal Power integration

Installed `/usr/local/sbin/t630-suspend` and enabled the scoped policy flag
`/etc/t630/suspend.enabled`. Opt-out is `/etc/t630/suspend.disabled` or removing
the enable flag. Prior Power monitor backup:
`/usr/local/share/t630/backups/manual-suspend.0hjkoa`.

Only a **manual Power blank** invokes the helper. Idle timeout still locks and
blanks the screen without system suspend. Helper requires the exact install and
kernel, lpm sleep_disabledY, IPA ONLINE, battery Discharging, detached USB, both
GNOME lock and elogind LockedHint, a tracked blank display, readable/inactive
audio streams, enabled RTC wake and no existing alarm. Other states fall back
to screen-off. It creates no privileged network or user-accessible control API.

During sleep the temporary nonmatching Wi-Fi packet rule prevents incoming
network traffic from waking the tablet; SSH is unavailable until wake. The
original wake patterns are restored afterward, including on errors. A300-second
RTC safety net remains during lab validation. A timer wake does not deliberately
unlock or restore the display. No automatic return-to-sleep loop is installed.

On a verified Power wake, the monitor restores brightness, sends only a harmless
modifier to dismiss the idle shade, and discards the already-handled Power
events from its own input reader to avoid treating wake as another sleep request.
No input grab or raw touchscreen/password capture.

Seven guard tests passed on Mac and tablet; six display regression tests passed.
Normal-user silent playback was accepted after resume and correctly inhibited
idle blanking. Source compilation passed. The root helper refused an ineligible
live check without sleeping. Old monitor PID720 was validated by exact command
name and stopped normally; new PID10008 is running with the updated code.
Physical normal-button cycle and persistence verification remain in progress.
The installed helper's live `--check` subsequently returned `ready; check only`
with the display locked/blanked. RTC alarm remained empty and IPA ONLINE. No
physical normal-button cycle had been reported by the owner at that check.
The existing desktop startup `--check` passed; modified files and policy flag
are persisted, but a reboot of this new Power integration has not yet run.

## Integrated-handler reboot and timer recovery

The clean unmount-first restart completed. At 20:59:19 EDT, new boot
`01bf77c3-1d54-4f93-bfb8-6c7bfbe9834c` had the Power monitor running as PID720,
IPA ONLINE, Wi-Fi SSH restored, GNOME ScreenSaver active, speaker sink present,
and the saved 83% brightness / 300-second idle setting. The tablet was still
Discharging with USB not attached. The monitor's old ambiguous “No suspend”
log suffix was removed; the following structured helper result now describes
whether a manual action actually suspended.

Installed Power monitor SHA256:
`ced0c2a7df616d232b39ac3f50fa77a1fa4447022bcba1899cf526b08a08170a`.
Installed suspend helper SHA256:
`facc45742f44577ef7e603f7e894f25a6fdd3429f5171e0f47b37d21de5bf4b6`.
Both match the local source files.

`ubuntu/test-t630-power-event.py` sends exactly one 100 ms KEY_POWER press and
release through the unique qpnp_pon evdev node. It checks the exact install and
kernel, requires an already locked GNOME session, and accepts only a lit-screen
sleep test or a blank-screen wake-display test. It does not capture input or
simulate a hardware wake IRQ. Linux's evdev write path dispatches through
input_inject_event; reference:
https://github.com/torvalds/linux/blob/master/drivers/input/evdev.c

The synthetic short press was delivered through the installed handler after
reboot. SSH became unreachable, as expected while asleep. The full 300-second
backup-alarm recovery result remains to be recorded below. This is an automated
input-path test, not owner confirmation of the new normal two-press sequence.

**Completed:** the installed helper reported `slept=true`, `seconds=301.3`,
`exit=0`, `power_wake=false`, wake reason `216 pm8xxx_rtc_alarm`. The kernel's
current-boot suspend counters were success1/fail0. The boot ID was unchanged.
SSH returned without USB or a restart. IPA was ONLINE, [redacted Wi-Fi network] connected,
ScreenSaver active, and the display remained tracked/blanked at 83% preference.
The RTC alarm was empty. No failed guard, driver reload or retry was involved.

A second synthetic short Power press exercised the ordinary display-wake path:
brightness returned to254/306, the saved blank state was removed, and the
password lock stayed active. The real Power monitor remained PID720. Normal-user
silent playback passed after resume and was detected as an idle-blank inhibitor.
The first invocation of that audio test was correctly refused because it ran as
root; it was then rerun through t630-gnome-run as UID1000 and passed. No audio
gain or authentication settings changed. Seven isolated Power/lock tests also
passed on the tablet. The view-only localhost screen tunnel was restored.

The five-minute alarm remains a lab safety net. This test establishes a complete
timer recovery through the installed handler; it does not substitute for the
owner's normal physical two-press test. The earlier physical Power IRQ wake is
separately verified above. Automatic idle system sleep remains disabled, and
`lpm_levels.sleep_disabled=Y` is unchanged. Battery61% is only a spot reading,
not evidence of a measured battery-life improvement.

Persistent handler log copied to
`reports/t630-power-button-integrated-20260912.log`.

All 33 local tests passed (display, IPA, GPU startup-watch, Power/lock, and
suspend). The expanded 12 suspend tests also passed on the tablet. Added tests
cover RTC-vs-Power wake handling, unsuccessful suspend, timeout cleanup,
Wi-Fi-rule cleanup even when alarm cleanup raises, refusal to blank without
both lock confirmations, saved-brightness bounds, and restoration without any
unlock request. Mocked timeout tests are not hardware fault-injection tests.

Scripts: `ubuntu/test-t630-driver-wake-pattern.py`,
`ubuntu/test-t630-freeze.sh` (only15/45seconds accepted).
New bounded retries apply only to newly recorded kernel EBUSY, never a failed
safety prerequisite. Device/install/kernel/IPA/USB/battery/password-lock checks
remain in place. No driver unloads, partition writes or auth bypasses.

## Interface-rename guard — 2026-09-13

The guarded suspend helper no longer assumes that the primary radio is named
`wlan0`. It selects exactly one connected interface that exposes this vendor
driver's add/delete wake-pattern attributes and a valid six-byte MAC address.
Zero or multiple matches are refused rather than guessed. Tests cover a
connected `wlp1s0`, an inactive Samsung virtual interface, and an ambiguous
two-interface failure. The current plugged-in tablet correctly returned
`external power or USB connected` without attempting suspend.

The read-only runtime-health helper now discovers the connected Wi-Fi interface
the same way through NetworkManager and prints only its interface/state, not the
saved connection or network name. On boot
`84251a48-c3c6-44cf-81bf-5d9f046fb4f8` it reported GNOME, Weston, Wi-Fi,
Bluetooth, 30% speaker volume and the accelerometer healthy.
