#!/bin/sh
# Read-only, filename-only inventory of speaker calibration; no EFS contents.
set -eu
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH
test "$(id -u)" = 0
for spec in sda6:efs sda9:sec_efs; do
    block=${spec%:*}
    label=${spec#*:}
    test "$(sed -n 's/^PARTNAME=//p' /sys/class/block/$block/uevent)" = "$label"
    test "$(blkid -p -s TYPE -o value /dev/$block)" = ext4
    point="/run/t630-$label-audio-inspect"
    install -d -m 700 "$point"
    mount -t ext4 -o ro,noload,nodev,nosuid,noexec "/dev/$block" "$point"
    trap 'umount "$point"' EXIT
    echo "Partition: $label"
    find "$point" -maxdepth 5 -type f \( -iname '*cirrus*' -o -iname '*speaker*' -o -iname '*rdc*' -o -iname '*vimon*' -o -iname '*cs35*' \) -printf '%P\n'
    if [ -d "$point/cirrus" ]; then
        find "$point/cirrus" -maxdepth 1 -type f -printf '%f (%s bytes)\n'
        for name in rdc_cal rdc_cal_r; do
            if [ -f "$point/cirrus/$name" ]; then
                echo "$name calibration bytes:"
                od -An -tx1 -N32 "$point/cirrus/$name"
            fi
        done
    fi
    umount "$point"
    trap - EXIT
done
