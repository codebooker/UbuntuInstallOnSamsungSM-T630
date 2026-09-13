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
nmcli -t -f DEVICE,TYPE,STATE device status 2>/dev/null |
    awk -F: '$2 == "wifi" && $3 == "connected" {
        print "interface=" $1 " state=" $3; found=1; exit
    } END {if (!found) print "unavailable"}'

printf 'bluetooth: '
if [ -d /sys/class/bluetooth/hci0 ]; then
    timeout 5 bluetoothctl show 2>/dev/null |
        awk '
            /^[[:space:]]*Powered:/ { powered=$2 }
            /UUID: Audio Source/ { source="yes" }
            /UUID: Audio Sink/ { sink="yes" }
            END {
                if (!powered) powered="unknown"
                if (!source) source="no"
                if (!sink) sink="no"
                print "powered=" powered " audio_source=" source " audio_sink=" sink
            }'
else
    echo unavailable
fi

printf 'audio: '
timeout 5 runuser -u tablet -- env XDG_RUNTIME_DIR=/run/user/1000 \
    PULSE_SERVER=unix:/run/user/1000/pulse/native \
    pactl get-sink-volume @DEFAULT_SINK@ 2>/dev/null |
    head -1 || echo unavailable

printf 'audio_defaults: '
sink=$(timeout 5 runuser -u tablet -- env XDG_RUNTIME_DIR=/run/user/1000 \
    PULSE_SERVER=unix:/run/user/1000/pulse/native \
    pactl get-default-sink 2>/dev/null || true)
source=$(timeout 5 runuser -u tablet -- env XDG_RUNTIME_DIR=/run/user/1000 \
    PULSE_SERVER=unix:/run/user/1000/pulse/native \
    pactl get-default-source 2>/dev/null || true)
if [ -n "$sink" ] && [ -n "$source" ]; then
    printf 'sink=%s source=%s\n' "$sink" "$source"
else
    echo unavailable
fi

printf 'device_permissions: '
if [ "$(stat -c '%U:%G:%a' /dev/fuse 2>/dev/null)" = root:root:666 ] && \
   [ "$(stat -c '%U:%G:%a' /dev/kgsl-3d0 2>/dev/null)" = root:render:660 ] && \
   [ "$(stat -c '%U:%G:%a' /dev/ion 2>/dev/null)" = root:render:660 ] && \
   [ "$(stat -c '%U:%G:%a' /dev/video32 2>/dev/null)" = root:render:660 ] && \
   [ "$(stat -c '%U:%G:%a' /dev/video33 2>/dev/null)" = root:render:660 ] && \
   [ "$(stat -c '%U:%G:%a' /dev/dri/renderD128 2>/dev/null)" = root:render:660 ] && \
   [ "$(stat -c '%U:%G:%a' /dev/snd/controlC0 2>/dev/null)" = root:audio:660 ]; then
    echo valid
else
    echo mismatch
fi

printf 'camera_stack: '
if [ -e /run/t630-camera-ready ] || pgrep -x cameraserver >/dev/null 2>&1 || \
   pgrep -f '^/usr/local/libexec/t630-camera-capture( |$)' >/dev/null 2>&1; then
    echo active
else
    echo stopped
fi

printf 'kernel_fault_markers: '
dmesg 2>/dev/null |
    grep -ciE 'kernel panic|internal error: oops|kgsl.*fault|watchdog.*lockup|h/w is overloaded|msm_vidc.*state.*error' || true

printf 'desktop_battery: '
timeout 5 upower -i /org/freedesktop/UPower/devices/DisplayDevice 2>/dev/null |
    awk '
        /^[[:space:]]*state:/ { state=$2 }
        /^[[:space:]]*percentage:/ { percentage=$2 }
        END {
            if (state && percentage)
                print "state=" state " percentage=" percentage
            else
                print "unavailable"
        }'

printf 'accelerometer: '
accelerometer=$(timeout 5 busctl get-property net.hadess.SensorProxy \
    /net/hadess/SensorProxy net.hadess.SensorProxy HasAccelerometer \
    2>/dev/null || true)
case "$accelerometer" in
    'b true') echo available=yes ;;
    'b false') echo available=no ;;
    *) echo unavailable ;;
esac

printf 'runtime_filesystem: '
df -h /run | tail -1
