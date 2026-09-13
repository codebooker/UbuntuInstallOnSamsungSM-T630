#!/bin/sh
# One manual shallow-suspend experiment; no persistent sleep policy changes.
set -eu
seconds=${1:-15}
case "$seconds" in 15|45) ;; *) exit 2 ;; esac
test "$(id -u)" = 0
test "$(cat /etc/t630-install-id)" = SM-T630-T630XXSBDZE3-Ubuntu-v1
test "$(cat /sys/module/lpm_levels/parameters/sleep_disabled)" = Y
test "$(cat /sys/class/rtc/rtc0/device/power/wakeup)" = enabled
grep -qw freeze /sys/power/state
/usr/local/bin/t630-gnome-run gdbus call --session --dest org.gnome.ScreenSaver \
    --object-path /org/gnome/ScreenSaver --method org.gnome.ScreenSaver.GetActive | grep -qx '(true,)'
test -z "$(cat /sys/class/rtc/rtc0/wakealarm)"
date -u
grep -H . /sys/power/suspend_stats/* || true
sync
set +e
timeout -k 3 "$((seconds + 30))" rtcwake -m freeze -d /dev/rtc0 -s "$seconds"
result=$?
set -e
printf 'rtcwake exit=%s\n' "$result"
date -u
grep -H . /sys/power/suspend_stats/* || true
rtcwake -m disable -d /dev/rtc0
exit "$result"
