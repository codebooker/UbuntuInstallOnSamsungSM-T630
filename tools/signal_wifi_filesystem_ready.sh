#!/bin/sh
# Experimental outer-recovery cold-start probe, not a live-Wi-Fi repair.
# Default is read-only. Use only between loading cnss2 and loading wlan.
set -eu
mode=${1:---check}
case "$mode" in
    --check|--signal-ready) ;;
    *) echo "usage: $0 [--check|--signal-ready]" >&2; exit 2 ;;
esac
test "$(id -u)" = 0
test "$(uname -r)" = 5.4.274-qgki-31225846-abT630XXSBDZE3
grep -q 'androidboot.em.model=SM-T630' /proc/cmdline
test -f /run/t630-selected-root
root=$(cat /run/t630-selected-root)
case "$root" in
    /run/ubuntu|/run/ubuntu/opt/t630/rehearsal/release-root) ;;
    *) echo 'Unexpected selected root; refusing.' >&2; exit 1 ;;
esac
test "$(cat "$root/etc/t630-install-id")" = SM-T630-T630XXSBDZE3-Ubuntu-v1
test -d /sys/module/cnss2
if [ -d /sys/module/wlan ]; then
    echo 'wlan is already loading/running; refusing out-of-order calibration.' >&2
    exit 1
fi
device=/sys/bus/platform/devices/b0000000.qcom,cnss-qca6490
test -e "$device/of_node/qcom,wlan-cbc-enabled"
test -w "$device/fs_ready"
test "$(cat /sys/module/firmware_class/parameters/path)" = /run/input-firmware
for file in amss.bin regdb.bin bdwlan.e3f; do
    test -s "/run/input-firmware/qca6490/$file"
done
test -s /run/input-firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini
if [ "$mode" = --check ]; then
    echo 'WIFI_FILESYSTEM_READY_PROBE_READY; no signal sent.'
    exit 0
fi
# This is the driver's normal fs_ready event, NOT a calibration-done override.
# It neither supplies an invented MAC nor changes quirks/regulatory limits.
printf '1\n' >"$device/fs_ready"
echo 'WIFI_FILESYSTEM_READY_SIGNALED; calibration outcome still needs observation.'
