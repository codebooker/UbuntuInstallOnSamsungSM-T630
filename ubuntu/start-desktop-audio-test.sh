#!/bin/sh
# Manual user-session audio test; no new TCP listener or system service.
set -eu
test "$(id -u)" = 0
eval "$(python3 /usr/local/share/t630/t630_account.py env)"
usermod -aG audio "$T630_OWNER"
for process in pipewire pipewire-pulse wireplumber; do
    if pgrep -u "$T630_OWNER_UID" -x "$process" >/dev/null; then
        echo "$process already running; refusing duplicate launch."
        exit 1
    fi
done
for process in pipewire pipewire-pulse wireplumber; do
    nohup /usr/local/bin/t630-gnome-run "$process" </dev/null >"/var/log/t630-$process.log" 2>&1 &
done
attempt=0
until /usr/local/bin/t630-gnome-run pactl info >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    test "$attempt" -lt 20
    sleep 1
done
/usr/local/bin/t630-gnome-run pactl load-module module-alsa-sink \
    sink_name=t630_speakers device=hw:0,0 format=s16le rate=48000 channels=2 \
    channel_map=front-left,front-right mmap=false tsched=false \
    sink_properties=device.description=Tablet_Speakers
/usr/local/bin/t630-gnome-run pactl set-sink-mute t630_speakers 1
/usr/local/bin/t630-gnome-run pactl set-sink-volume t630_speakers 10%
/usr/local/bin/t630-gnome-run pactl set-default-sink t630_speakers
/usr/local/bin/t630-gnome-run pactl list short sinks
