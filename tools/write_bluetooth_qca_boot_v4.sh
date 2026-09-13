#!/bin/sh
# Write only the verified SM-T630 kernel with Qualcomm IBS Bluetooth support.
set -eu

mode=${1:---check}
image=/var/tmp/t630-bluetooth-qca-v4.img
old_hash=464e4900a841dc59c1ac82380812b9e7feff78843735a7216b1afe9bde466bd4
new_hash=9dd1ef688b578e574c148daacddf0d2f57e7c0408ac8ca024fb5eb0c0f21eaea

case "$mode" in
    --check|--write) ;;
    *) echo "usage: $0 [--check|--write]" >&2; exit 2 ;;
esac

test "$(id -u)" = 0
test "$(uname -r)" = 5.4.274-qgki-31225846-abT630XXSBDZE3
grep -q 'androidboot.em.model=SM-T630' /proc/cmdline
test "$(cat /etc/t630-install-id)" = SM-T630-T630XXSBDZE3-Ubuntu-v1
grep -qx 'PARTNAME=boot' /sys/class/block/sda19/uevent
test "$(cat /sys/class/block/sda19/dev)" = 259:3
test "$(cat /sys/class/block/sda19/size)" = 196608
test -b /dev/sda19
awk '$3 == "259:3" { found=1 } END { exit found ? 1 : 0 }' /proc/self/mountinfo
test "$(cat /sys/class/power_supply/battery/capacity)" -ge 30
test "$(cat /sys/class/power_supply/battery/status)" = Charging
test "$(stat -c %s "$image")" = 100663296
printf '%s  %s\n' "$new_hash" "$image" | sha256sum -c -
printf '%s  %s\n' "$old_hash" /dev/sda19 | sha256sum -c -

if [ "$mode" = --check ]; then
    echo BLUETOOTH_QCA_BOOT_WRITE_READY
    exit 0
fi

dd if="$image" of=/dev/sda19 bs=4M conv=fsync status=none
sync
printf '%s  %s\n' "$new_hash" /dev/sda19 | sha256sum -c -
printf '%s  %s\n' 2b6901f8341de3b76fbcabc69bf0229683d503f233eafd580b4d602392ff74f5 /dev/sda20 | sha256sum -c -
printf '%s  %s\n' fbebd763c17c05bc162776a6e9abd86fc386aa0ef58ccfdaa6cb9b13a6a0c72f /dev/sda21 | sha256sum -c -
printf '%s  %s\n' f9111b7a566b0a7342ec4d8f14cee53dc465a272d42596f774c0519d6e89fc57 /dev/sda22 | sha256sum -c -
printf '%s  %s\n' a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225 /dev/sde19 | sha256sum -c -
echo BLUETOOTH_QCA_BOOT_WRITTEN_READBACK_VERIFIED_PROTECTED_PARTITIONS_UNCHANGED
