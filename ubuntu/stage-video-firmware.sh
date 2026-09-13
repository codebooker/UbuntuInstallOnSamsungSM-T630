#!/bin/sh
# Exact-device stock firmware only; no partition writes or desktop changes.
set -eu
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH
test "$(id -u)" = 0
test "$(sed -n 's/^PARTNAME=//p' /sys/class/block/sda23/uevent)" = apnhlos
test "$(blkid -p -s TYPE -o value /dev/sda23)" = vfat
source_mount=/run/t630-video-firmware-source
destination=/opt/t630/video-firmware
install -d -m 700 "$source_mount"
mount -t vfat -o ro,nodev,nosuid,noexec /dev/sda23 "$source_mount"
trap 'umount "$source_mount"' EXIT
install -d -m 755 "$destination"
for source in "$source_mount"/image/vpu20_1v.* "$source_mount"/image/a660_zap.* \
    /opt/t630/vendor/firmware/a660_gmu.bin \
    /opt/t630/vendor/firmware/a660_sqe.fw; do
    test -f "$source"
    target="$destination/${source##*/}"
    if [ -e "$target" ]; then
        cmp -s "$source" "$target"
    else
        install -m 644 "$source" "$target"
        cmp -s "$source" "$target"
    fi
done
test -s "$destination/vpu20_1v.mdt"
test "$(cat /sys/module/firmware_class/parameters/path)" = /run/input-firmware
install -d -m 755 /run/input-firmware
for source in "$destination"/*; do
    # Synchronous firmware requests can run with the Ubuntu caller's root.
    user_target="/run/input-firmware/${source##*/}"
    if [ -L "$user_target" ]; then
        existing=$(readlink "$user_target")
        case "$existing" in
            "$source") ;;
            "/opt/t630/camera-firmware/${source##*/}")
                # Camera bring-up may publish these same two signed Adreno
                # files first. Share that validated byte-identical copy rather
                # than making camera and desktop startup fight over a symlink.
                test -f "$existing"
                cmp -s "$source" "$existing"
                ;;
            *) exit 1 ;;
        esac
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
