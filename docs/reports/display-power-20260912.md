# Brightness, idle screen-off, and sleep investigation

## Installed display controls

- Existing root Power monitor remains the sole owner of blank/wake handling.
  Added `/usr/local/lib/t630/t630_display.py` and normal-user
  `/usr/local/bin/t630-display` client. Existing hardware Power behavior retained.
- Root-owned `/run/t630-display.sock`, group tablet, mode0660; AF_UNIX only,
  no network listener. SO_PEERCRED restricts requests to UID1000/root.
  Fixed commands only: STATUS, BRIGHTNESS5..100, IDLE0/120/300/600/1800,
  and a40-second INHIBIT lease. No file paths, shell execution, unlock, suspend,
  shutdown, credentials or arbitrary-device API exposed.
- Brightness addresses only the validated panel0 backlight max306. A5% floor
  prevents the brightness slider itself from making the display completely dark.
  While blanked, brightness changes only the saved restore value, not the panel.
- Brightness and idle preferences are stored atomically, root-only, in
  `/var/lib/t630/display-settings.json`, with2-second write coalescing.
  Saved default after tests: brightness83%, idle300seconds.
- Idle timing uses GNOME Mutter's idle counter, not raw touch/keyboard data.
  After five minutes idle, the monitor verifies the normal password lock and
  LockedHint before blanking. A falling idle counter wakes the backlight without
  unlocking; Power remains an immediate wake path. Wake polling is2seconds.
  Missing/unresponsive idle or audio state conservatively prevents blanking.
- Active uncorked audio streams inhibit automatic blanking. GNOME extension
  requests a renewable40-second lease for a focused full-screen app, checked
  every15seconds. Keep Awake sets idle0 for reading or other manual exceptions.
  These are scoped prototype controls, not a complete SessionManager inhibitor
  implementation. Application-specific media behavior still needs user testing.
- Tablet Controls extension version3 retains the existing keyboard/red-button
  behavior and adds a standard Quick Settings brightness slider and Keep Awake
  toggle. No password-screen behavior or keyboard overlay changes.

## Verification before reboot

- Five isolated module tests passed: blanked brightness updates do not light
  panel, saved preferences reload, invalid requests rejected, Keep Awake/lease
  handling, wrong backlight rejected. Python compilation and JS syntax passed.
- Actual normal-user brightness50 set raw153, then brightness83 restored raw254.
  BRIGHTNESS0 rejected and left raw254 unchanged. UID65534 was denied socket
  access. Device-node permissions did not change.
- Automatic idle blanking with temporary timeout120 succeeded: raw brightness0,
  saved brightness255/254, password lock active. While blanked, requesting50%
  changed saved value153 but raw stayed0. Restored preference83, injected only
  Shift to create a harmless input event, and the monitor restored backlight
  while ScreenSaver GetActive stayedtrue. Default timeout restored300 afterward.
- Prior monitor PID715 became a zombie after orderly stop; pgrep matched it,
  so the initial guarded manual restart did not launch the new monitor. Confirmed
  zombie state then launched replacement; flock still prevents a second live
  monitor. No unrelated process was signaled. Cold boot clears that zombie.
- Backup of prior monitor and extension:
  `/usr/local/share/t630/backups/display-controls.3Ychfc` on tablet.
- Clean reboot dispatched to load the updated extension and verify preferences.

## Suspend investigation

Kernel advertises freeze/mem and s2idle/deep. Its lpm_levels.sleep_disabled=Y
setting is unchanged. CONFIG_PM_DEBUG's staged `/sys/power/pm_test` interface
is absent. RTC and Power input advertise wakeup enabled.

RTC alarm-only test with rtcwake-mno fired: pm8xxx_rtc_alarm interrupt count
increased0->1 and alarm disabled itself. RTC hardware clock is a raw1970 epoch;
relative rtcwake programming handled its offset from current system time.
No RTC clock, firmware, boot arguments or deep-power settings were changed.

After verifying lock and syncing filesystems, one15-second shallow freeze test
used a timed RTC wake alarm. It returned immediately with rtcwake exit1, not a
successful suspend. Kernel suspend_stats: failed_suspend1, last_failed_dev
`a600000.ssusb`, errno-16 (EBUSY), success0. Alarm was explicitly disarmed.
Wi-Fi/SSH, desktop and display controls remained responsive afterward.

Asked owner to unplug USB for the next test. Automatic suspend remains disabled;
no claim of battery-saving sleep or measured unplugged endurance. Screen-off is
working separately and is not mislabeled as suspend.

References: [Linux staged suspend tests](https://cdn.kernel.org/doc/html/latest/power/basic-pm-debugging.html),
[GNOME Quick Settings extension API](https://gjs.guide/extensions/topics/quick-settings.html).

## Reboot and further verification

Boot `1aa10ea2-983f-4f83-968e-fa2b831d01c7` returned GNOME password lock,
Wi-Fi/SSH, audio services and the Power monitor. Preferences reloaded as83% and
300seconds; raw brightness254. Extension metadata reports Tablet Controls v3,
enabled, INACTIVE while password-locked (expected). No matching extension JS
errors appeared during startup. On-screen slider/toggle use awaits user unlock.
Automatic blanking occurred again after five idle minutes on this boot.

A normal-user silent paplay stream was correctly recognized by the audio-active
predicate; it was stopped afterward without mixer/amplifier changes. Added a
sixth isolated test: invalid preference JSON must not disable the Power monitor.
All six tests passed. That defensive preference-loading update is installed for
next monitor start; the current monitor has valid preferences and keeps running.

Two reversible USB-data-only experiments ran over established Wi-Fi SSH.
Both validated the exact controller and serial-only gadget first. Soft disconnect
left it configured/active. Temporary serial-gadget unbinding made it not-attached
but still runtime-active. Neither met the prerequisite for another freeze
attempt, so no additional suspend was attempted. Both restored the connection
in finally; gadget UDC and configured state were verified afterward. No
persistent USB setup changed. See `ubuntu/test-t630-usb-idle.py` and tablet logs
`/var/log/t630-usb-idle-test.log` / `/var/log/t630-usb-unbind-test.log`.
The [kernel UDC interface](https://www.kernel.org/doc/html/latest/admin-guide/abi-stable.html)
documents logical disconnect. Physical cable removal remains the next sleep-test
requirement; unplugged battery measurements also remain pending.

## Unplugged follow-up and actual UI checks

The owner confirmed Power screen-off/wake while unplugged. This is display
blanking, not proof of system suspend. Physical removal produced USB state
`not attached` and controller runtime state `suspended`; battery Discharging.

Quick Settings was exercised through pointer injection on the actual GNOME
screen: brightness slider set50%, Keep Awake set idle0, a second click restored
idle300. Brightness was restored83 afterward. Screenshot:
`power-controls-menu-20260912.png`. These are UI/backend checks, not a physical
finger-drag confirmation. The normal password lock was activated before sleep.

The first unplugged `/run/test-t630-freeze.sh` test succeeded at23:26UTC:
kernel success0->1, fail0, timekeeping suspended2.578seconds. Wi-Fi and locked
GNOME recovered. The intended15-second RTC alarm did not cause this wake:
kernel reported WLAN PATTERN_MATCH_FOUND, IPv4 UDP destination port9999.
The kernel's deep-power-disable setting remainedY. No automatic suspend enabled.
Tablet log: `/var/log/t630-freeze-unplugged.log`.

WoWLAN initially reported magic-packet-only despite the broadcast wake.
`test-t630-freeze-no-wow.py` temporarily disabled it, with restoration in finally.
The first invocation stopped at an exact-output guard before any change; a
subsequent invocation stopped at the password-lock guard before any suspend.
After locking normally, the no-WoWLAN test disconnected WLAN during suspend,
aborted with EBUSY, and then automatically reconnected. Original magic-packet
configuration was restored and read back. No network credentials were touched.
Log: `/var/log/t630-freeze-no-wow.log`.

Related Qualcomm [PMO source](https://android.googlesource.com/kernel/msm-modules/qcacld/+/refs/heads/android-msm-barbet-4.19-android12/components/pmo/core/src/wlan_pmo_wow.c)
deletes default patterns when adding user patterns; this is a lead, not proof
of identical behavior in this Samsung binary driver. The selective test adds
an Ethernet WoL pattern addressed to this tablet plus magic-packet wake, then
restores the original setting. Its first attempt aborted EBUSY after bus suspend
and panel-off; no completed sleep interval. Log:
`/var/log/t630-freeze-selective.log`. A repeat allows configuration to settle
and records per-source wake event deltas for diagnosis.

An unbounded diagnostic read of `/sys/power/wakeup_count` blocked because active
wakeup sources exist. Only that exact owned cat process was terminated. Future
reads must be bounded. `/sys/class/wakeup` is available without mounting debugfs.

## Further comparisons and final restored state

Two additional selective-pattern attempts aborted EBUSY. Per-source event
deltas included `qrtr_ws` and sometimes `qcom_rx_wakelock`, plus battery events
during resume. They are correlations, not proof of the exact abort source.
The driver continues an existing missing-IPA-firmware retry every approximately
512ms. Do not expose arbitrary firmware or live-unload audio to suppress it.

A temporary root-only tracefs mount and isolated `t630-sleep-test` instance
recorded only power events. No input, packet payloads, global trace options, or
other tracing instances were changed. The baseline magic-packet-only comparison
at23:39:35UTC completed freeze (success1->2) and timekeeping reported4.399seconds
asleep. It again woke on WLAN PATTERN_MATCH_FOUND, before the15-second alarm.
Trace identifies `qcom_rx_wakelock` activation in Wi-Fi `dp_rx_thread_0` and
periodic `qrtr_ws` activity. Logs copied to this reports directory:
`t630-freeze-traced.log`, `t630-freeze-power.trace`.

A selective-policy comparison allowed at most3 retries, only after a newly
recorded kernel EBUSY (never a failed prerequisite). Attempt1 aborted; attempt2
returned0 and success2->3 but returned within approximately0.465seconds of
suspend entry and again logged PATTERN_MATCH_FOUND. Its timekeeping message
repeated the prior4.399seconds despite the wall-time mismatch and absence of a
new GIC resume line. Do not count this as a verified4.399-second sleep or RTC
wake. Explicit patterns therefore did not establish a fix. Original WoWLAN
policy restored after every test. Log: `t630-freeze-selective-bounded.log`.

At final check: battery56%, Discharging; normal Wi-Fi SSH working; GNOME and
Power handler alive; default PipeWire speaker sink present and idle; display
preferences83%/300seconds. RTC alarm empty, lpm sleep_disabledY, no persistent
sleep-policy or firmware change. The private tracing instance was removed and
the temporary tracefs unmounted; saved diagnostic logs remain. Six display
module tests passed again and both new diagnostic scripts compile.

Next development gate is a full timer-length sleep with a trustworthy wake
reason and repeated recovery, then physical Power wake from actual suspend.
That requires resolving the vendor Wi-Fi wake behavior and suspend-entry races;
automatic sleep and deep-power changes remain disabled pending that evidence.
