#!/bin/sh
# Manual first-load experiment only; live module unloading is unsafe on stock.
set -eu
test "$(id -u)" = 0
test ! -d /sys/module/q6_pdr_dlkm
test ! -d /sys/module/snd_soc_cs35l45_i2c
if pgrep -x t630-pd-mapper >/dev/null; then
    echo 'Mapper already running; refusing to change live startup order.' >&2
    exit 1
fi
sh /usr/local/share/t630/stage-audio-firmware.sh >/run/t630-audio-firmware.sha256
# Register the notifier before publishing the one-shot location response.
python3 /usr/local/share/t630/t630-audio-modules.py --load
nohup /usr/local/sbin/t630-pd-mapper --directory /opt/t630/audio-firmware \
    </dev/null >/run/t630-pd-mapper.log 2>&1 &
chroot /proc/1/root /bin/busybox sh -c \
    'test -s /run/input-firmware/adsp.mdt && printf 1 > /sys/kernel/boot_adsp/boot'
attempt=0
until grep -q lahaina-yupikidp-snd-card /proc/asound/cards; do
    attempt=$((attempt + 1))
    test "$attempt" -lt 30
    sleep 1
done
python3 /usr/local/share/t630/t630-sound-nodes.py
# Factory calibration must be cached before the speaker protection DSP boots.
python3 /usr/local/share/t630/load-stock-speaker-calibration.py
python3 /usr/local/share/t630/test-speaker-protection.py
echo 'Cold-order test completed. Speaker amps remain disabled; no modules unloaded.'
