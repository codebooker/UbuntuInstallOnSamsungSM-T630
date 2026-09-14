#!/bin/bash
# Build the isolated, read-only Android camera runtime inside Ubuntu.
set -euo pipefail

test "$(cat /etc/t630-install-id)" = SM-T630-T630XXSBDZE3-Ubuntu-v1
test "$(uname -r)" = 5.4.274-qgki-31225846-abT630XXSBDZE3
test "$(grep '^PARTNAME=' /sys/class/block/sda26/uevent)" = PARTNAME=super
test "$(cat /sys/class/block/sda26/size)" = 18432000
super_device=$(cat /sys/class/block/sda26/dev)
[[ "$super_device" =~ ^[0-9]+:[0-9]+$ ]]
eval "$(/usr/bin/python3 /usr/local/share/t630/t630_account.py env)"

system_table="0 12036096 linear $super_device 2048
12036096 16248 linear $super_device 17401856"
vendor_table="0 2214168 linear $super_device 15142912"

create_mapping() {
    local name=$1 table=$2 number major minor node
    if ! dmsetup info "$name" >/dev/null 2>&1; then
        printf '%s\n' "$table" | dmsetup create "$name" --readonly
    fi
    test "$(dmsetup table "$name")" = "$table"
    number=$(dmsetup info -c --noheadings --separator : -o major,minor "$name" |
        tr -d ' ')
    [[ "$number" =~ ^[0-9]+:[0-9]+$ ]]
    major=${number%:*}
    minor=${number#*:}
    node=/dev/dm-$minor
    if [[ ! -b "$node" ]]; then
        mknod "$node" b "$major" "$minor"
    fi
    printf '%s\n' "$node"
}

system_device=$(create_mapping t630-stock-system "$system_table")
vendor_device=$(create_mapping t630-stock-vendor "$vendor_table")

mount_image() {
    local image=$1 target=$2
    mkdir -p "$target"
    if ! mountpoint -q "$target"; then
        mount -o loop,ro "$image" "$target"
    fi
}

mount_bind_ro() {
    local source=$1 target=$2
    mkdir -p "$target"
    if ! mountpoint -q "$target"; then
        mount --bind "$source" "$target"
        mount -o remount,bind,ro "$target"
    fi
}

mkdir -p /system /mnt/t630-stock-system /mnt/stock-vendor-full
if ! mountpoint -q /mnt/t630-stock-system; then
    mount -t f2fs -o ro "$system_device" /mnt/t630-stock-system
fi
if ! mountpoint -q /mnt/stock-vendor-full; then
    mount -t f2fs -o ro "$vendor_device" /mnt/stock-vendor-full
fi
mount_bind_ro /mnt/t630-stock-system/system /system
mount_image "$T630_OWNER_HOME/t630-vndk30-apex/apex_payload.img" /mnt/t630-vndk30
mount_image "$T630_OWNER_HOME/t630-apex/runtime/apex_payload.img" /mnt/t630-runtime
mount_image "$T630_OWNER_HOME/t630-apex/i18n/apex_payload.img" /mnt/t630-i18n
mount_image "$T630_OWNER_HOME/t630-camera-apex/apex_payload.img" /mnt/t630-camera

mount_bind_ro "$T630_OWNER_HOME/t630-vendor-view" /vendor
mount_bind_ro "$T630_OWNER_HOME/t630-linkerconfig" /linkerconfig
mkdir -p /data
if ! mountpoint -q /data; then
    mount --bind "$T630_OWNER_HOME/t630-android-data" /data
fi
mount_bind_ro /mnt/t630-runtime /apex/com.android.runtime
mount_bind_ro /mnt/t630-i18n /apex/com.android.i18n
mount_bind_ro /mnt/t630-camera /apex/com.samsung.android.camera.unihal
mount_bind_ro /mnt/t630-vndk30 /dev/t630-vndk30

mkdir -p /dev/binderfs
if ! mountpoint -q /dev/binderfs; then
    mount -t binder binder /dev/binderfs
fi
for name in binder hwbinder vndbinder; do
    test -c "/dev/binderfs/$name"
    [[ -e "/dev/$name" ]] || ln -s "binderfs/$name" "/dev/$name"
done

# These compatibility files are extracted locally from the matching stock
# build. Their hashes and purpose are documented, but the files are not
# redistributable and are deliberately excluded from this repository.
if ! mountpoint -q /system/bin/cameraserver; then
    mount --bind "$T630_OWNER_HOME/t630-system-overrides/cameraserver" /system/bin/cameraserver
fi
chi=/mnt/stock-vendor-full/lib64/hw/com.qti.chi.override.so
if ! mountpoint -q "$chi"; then
    mount --bind "$T630_OWNER_HOME/t630-vendor-overrides/com.qti.chi.override.so" "$chi"
fi

ln -sf /usr/local/lib/t630-android-property-seed.so /dev/t630-android-property-seed.so
for firmware in /opt/t630/camera-firmware/*; do
    ln -sf "$firmware" "/run/input-firmware/${firmware##*/}"
done
if [[ ! -d /sys/module/camera ]]; then
    insmod /opt/t630/vendor/lib/modules/camera.ko
fi
# Create only the camera/media nodes exposed by this exact kernel. A global
# mdev scan here would reset unrelated live desktop device permissions.
python3 /usr/local/share/t630/t630-camera-nodes.py
python3 /usr/local/share/t630/t630-device-permissions.py

test -c /dev/media0
test -c /dev/video0
test -x /system/bin/cameraserver
test -x /vendor/bin/hw/vendor.samsung.hardware.camera.provider@4.0-service_64
echo 'Camera lab runtime mounted; no Android writable partition was mounted.'
