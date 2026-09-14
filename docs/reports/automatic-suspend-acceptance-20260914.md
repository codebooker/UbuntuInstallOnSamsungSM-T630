# Automatic suspend acceptance and ADSP wake fix

## Failure found by the unattended test

The tablet was physically unplugged and reported battery `Discharging`, AC and
USB both offline, and the USB controller `not attached`. The normal GNOME idle
path locked the session and blanked the panel, then attempted guarded shallow
suspend. Four consecutive attempts entered freeze but resumed after about half
a second with IRQ 386, `glink-native-adsp`.

No PipeWire sink input was active. The remaining ADSP client was the SSC sensor
stack: `iio-sensor-proxy` plus `hexagonrpcd` holding the downstream FastRPC
sensor domain. Stopping those two exact processes and removing only the sensor
ready marker allowed the next automatic retry to remain asleep. A short Power
press woke it through IRQ 212, `pon_kpdpwr_status`, without rebooting.

## Installed fix

`t630-suspend` now performs sensor quiescence only after every existing power,
USB, IPA, password-lock, panel, audio, Wi-Fi, and RTC guard has passed. It:

1. Matches only the exact known `iio-sensor-proxy` and SM-T630 `hexagonrpcd`
   command lines.
2. Sends TERM and waits at most five seconds for both to exit.
3. Allows five seconds for final SSC/ADSP messages to drain.
4. Enters the existing guarded `freeze` cycle.
5. Relaunches the normal sensor startup helper after every return or exception,
   in addition to removing the temporary Wi-Fi wake pattern and RTC alarm.

No driver is unbound or unloaded, and no firmware, mixer, amplifier, password,
or network state is changed. The prior helper is backed up on the tablet at
`/usr/local/share/t630/backups/suspend-sensor-quiesce-20260914/t630-suspend`.

## Physical acceptance

With the fix deployed and both sensor processes running, an automatic idle
cycle entered suspend at `2026-09-14 15:19:53.938 UTC`. The tablet remained
unreachable over Wi-Fi until a physical short Power press and resumed at
`15:22:20.416 UTC`, about 146 seconds later. The kernel recorded IRQ 212,
`pon_kpdpwr_status`; boot ID remained
`79940f92-cb0d-461f-9234-261fd0549b8f`.

After wake, Wi-Fi/SSH returned, the GNOME password lock remained in force, the
speaker sink was `t630_speakers`, the sensor ready marker returned, SensorProxy
reported an accelerometer, and no current-boot kernel panic, null dereference,
or KGSL fault marker was present. The temporary two-minute validation idle
setting was restored to the normal five minutes.

A second unattended cycle used that normal 300-second policy. It entered
suspend at `15:27:45.233 UTC` and remained asleep until the five-minute safety
alarm, resuming at `15:32:46.668 UTC` after about 301 seconds on IRQ 216,
`pm8xxx_rtc_alarm`. The same boot ID and service recovery checks passed. This
cycle proves the full default idle interval and RTC recovery; the immediately
preceding cycle proves physical Power wake with the deployed sensor fix.

The first post-RTC automatic re-sleep attempt raced the newly restarted sensor
service and aborted safely with `One or more tasks refusing to freeze`. The
monitor now waits 60 seconds, rather than 15, after an RTC wake before another
attempt. User activity during that interval still restores the locked display
and cancels the retry normally.

Fifteen isolated suspend-guard/cleanup tests pass, including sensor restart on
the success path and cleanup after failed, timed-out, and alarm-cleanup paths.
