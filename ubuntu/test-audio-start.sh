#!/bin/sh
# Manual prototype test only. Not registered for automatic startup.
set -eu
test "$(id -u)" = 0
sh /usr/local/share/t630/stage-audio-firmware.sh >/run/t630-audio-firmware.sha256
if ! pgrep -x t630-pd-mapper >/dev/null; then
    nohup /usr/local/sbin/t630-pd-mapper --directory /opt/t630/audio-firmware \
        </dev/null >/run/t630-pd-mapper.log 2>&1 &
fi
attempt=0
until qrtr-lookup | grep -qE '^[[:space:]]*64[[:space:]]'; do
    attempt=$((attempt + 1))
    test "$attempt" -lt 10
    sleep 1
done
python3 /usr/local/share/t630/t630-audio-modules.py --load
# Match the stock boot request, with the firmware path resolved in init's root.
chroot /proc/1/root /bin/busybox sh -c \
    'test -s /run/input-firmware/adsp.mdt && printf 1 > /sys/kernel/boot_adsp/boot'
echo 'Audio prerequisites started; card enumeration and playback need verification.'
