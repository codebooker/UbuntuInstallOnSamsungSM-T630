#!/bin/sh
# Read-only SM-T630 health summary using only known-safe kernel interfaces.
set -u

PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH

printf 'boot_id: '
cat /proc/sys/kernel/random/boot_id
printf 'uptime_seconds: '
cut -d' ' -f1 /proc/uptime

printf 'weston: '
pgrep -x weston >/dev/null && echo running || echo stopped
printf 'gnome_shell: '
pgrep -x gnome-shell >/dev/null && echo running || echo stopped

printf 'wifi: '
nmcli -t -f GENERAL.STATE,GENERAL.CONNECTION device show wlan0 2>/dev/null |
    tr '\n' ' '
echo

printf 'bluetooth: '
if [ -d /sys/class/bluetooth/hci0 ]; then
    timeout 5 bluetoothctl show 2>/dev/null |
        sed -n 's/^[[:space:]]*Powered:[[:space:]]*/powered=/p' |
        head -1
else
    echo unavailable
fi

printf 'audio: '
timeout 5 runuser -u tablet -- env XDG_RUNTIME_DIR=/run/user/1000 \
    PULSE_SERVER=unix:/run/user/1000/pulse/native \
    pactl get-sink-volume @DEFAULT_SINK@ 2>/dev/null |
    head -1 || echo unavailable

printf 'accelerometer: '
timeout 5 busctl get-property net.hadess.SensorProxy /net/hadess/SensorProxy \
    net.hadess.SensorProxy HasAccelerometer 2>/dev/null || echo unavailable

printf 'runtime_filesystem: '
df -h /run | tail -1
