#!/bin/sh
# Write only the verified CNSS filesystem-ready SM-T630 boot candidate.
set -eu

mode=${1:---check}
image=/var/tmp/t630-release-boot-v7.img
old_hash=ca7caa12d1228969b264815bf69f34dbbee5ced9e3a86d1134c590bff8c895dc
new_hash=83a3eb1ea8a63df4989bb893d14f525b60c43bbf4b1d7ae2574e641d6811f1cd

case "$mode" in
    --check|--write) ;;
    *) echo "usage: $0 [--check|--write]" >&2; exit 2 ;;
esac

test "$(id -u)" = 0
test "$(uname -r)" = 5.4.274-qgki-31225846-abT630XXSBDZE3
grep -q 'androidboot.em.model=SM-T630' /proc/cmdline
test "$(cat /etc/t630-install-id)" = SM-T630-T630XXSBDZE3-Ubuntu-v1
grep -qx 'PARTNAME=boot' /sys/class/block/sda19/uevent
test "$(cat /sys/class/block/sda19/size)" = 196608
test -b /dev/sda19
boot_dev=$(cat /sys/class/block/sda19/dev)
awk -v dev="$boot_dev" '$3 == dev { found=1 } END { exit found ? 1 : 0 }' \
    /proc/self/mountinfo
test "$(cat /sys/class/power_supply/battery/capacity)" -ge 30
battery_status=$(cat /sys/class/power_supply/battery/status)
case "$battery_status" in
    Charging) ;;
    Full)
        test "$(cat /sys/class/power_supply/ac/online)" = 1 ||
            test "$(cat /sys/class/power_supply/usb/online)" = 1
        ;;
    *) echo "battery is not charging: $battery_status" >&2; exit 1 ;;
esac
test "$(stat -c %s "$image")" = 100663296
printf '%s  %s\n' "$new_hash" "$image" | sha256sum -c -
printf '%s  %s\n' "$old_hash" /dev/sda19 | sha256sum -c -

if [ "$mode" = --check ]; then
    echo RELEASE_BOOT_V7_WRITE_READY
    exit 0
fi

dd if="$image" of=/dev/sda19 bs=4M conv=fsync status=none
sync
printf '%s  %s\n' "$new_hash" /dev/sda19 | sha256sum -c -
printf '%s  %s\n' 2b6901f8341de3b76fbcabc69bf0229683d503f233eafd580b4d602392ff74f5 /dev/sda20 | sha256sum -c -
printf '%s  %s\n' fbebd763c17c05bc162776a6e9abd86fc386aa0ef58ccfdaa6cb9b13a6a0c72f /dev/sda21 | sha256sum -c -
printf '%s  %s\n' f9111b7a566b0a7342ec4d8f14cee53dc465a272d42596f774c0519d6e89fc57 /dev/sda22 | sha256sum -c -
printf '%s  %s\n' a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225 /dev/sde19 | sha256sum -c -
echo RELEASE_BOOT_V7_WRITTEN_READBACK_VERIFIED_PROTECTED_PARTITIONS_UNCHANGED
