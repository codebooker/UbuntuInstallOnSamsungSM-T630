#!/bin/sh
# Read-only stock audio inventory. Does not load modules or change mixer gains.
set -eu
uname -r
cat /proc/asound/cards
for name in machine_dlkm adsp_loader_dlkm q6_dlkm apr_dlkm bolero_cdc_dlkm \
            wcd938x_dlkm snd-soc-cs35l45 snd-soc-cs35l45-i2c; do
    file="/opt/t630/vendor/lib/modules/$name.ko"
    [ -r "$file" ] || continue
    echo "MODULE: $name"
    modinfo -F vermagic "$file"
    modinfo -F depends "$file"
    modinfo -F firmware "$file"
done
echo 'AUDIO PLATFORM BINDINGS'
for device in /sys/bus/platform/devices/*; do
    case "${device##*/}" in
        *sound*|*audio*|*adsp*|*bolero*|*q6*|*swr*)
            printf '%s: ' "${device##*/}"
            readlink "$device/driver" || true
            ;;
    esac
done
echo 'FIRMWARE SEARCH PATH'
cat /sys/module/firmware_class/parameters/path
echo 'FIRMWARE MOUNT CANDIDATES'
ls -l /dev/block/by-name/modem /dev/block/by-name/dsp 2>/dev/null || true
echo 'AUDIO KERNEL LOG'
dmesg | grep -iE 'snd|asoc|adsp|sound|audio|wcd|lpass' | tail -n 40 || true
