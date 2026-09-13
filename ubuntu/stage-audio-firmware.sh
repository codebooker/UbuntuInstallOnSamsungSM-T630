#!/bin/sh
# Copy only stock audio firmware from the validated, read-only APNHLOS volume.
set -eu
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH
test "$(id -u)" = 0
test "$(sed -n 's/^PARTNAME=//p' /sys/class/block/sda23/uevent)" = apnhlos
test "$(blkid -p -s TYPE -o value /dev/sda23)" = vfat
mountpoint=/run/t630-audio-firmware-source
install -d -m 700 "$mountpoint"
mount -t vfat -o ro,nodev,nosuid,noexec /dev/sda23 "$mountpoint"
trap 'umount "$mountpoint"' EXIT
destination=/opt/t630/audio-firmware
install -d -m 755 "$destination"
for source in "$mountpoint"/image/adsp.* "$mountpoint"/image/adsp*.jsn \
              /opt/t630/vendor/firmware/cs35l45*; do
    [ -f "$source" ] || continue
    target="$destination/${source##*/}"
    if [ -e "$target" ]; then
        cmp -s "$source" "$target"
    else
        install -m 644 "$source" "$target"
        cmp -s "$source" "$target"
    fi
done
test -s "$destination/adsp.mdt"
# Cover both caller roots, preserving the established touchscreen/Wi-Fi path.
test "$(cat /sys/module/firmware_class/parameters/path)" = /run/input-firmware
install -d -m 755 /run/input-firmware
for source in "$destination"/*; do
    user_target="/run/input-firmware/${source##*/}"
    if [ -L "$user_target" ]; then
        test "$(readlink "$user_target")" = "$source"
    else
        test ! -e "$user_target"
        ln -s "$source" "$user_target"
    fi
    target="/proc/1/root/run/input-firmware/${source##*/}"
    link="/run/ubuntu$source"
    if [ -L "$target" ]; then
        test "$(readlink "$target")" = "$link"
    else
        test ! -e "$target"
        ln -s "$link" "$target"
    fi
done
sha256sum "$destination"/*
