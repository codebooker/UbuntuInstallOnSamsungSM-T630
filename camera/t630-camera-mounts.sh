#!/bin/bash
# Build the isolated, read-only Android camera runtime inside Ubuntu.
set -euo pipefail

test "$(cat /etc/t630-install-id)" = SM-T630-T630XXSBDZE3-Ubuntu-v1
test "$(uname -r)" = 5.4.274-qgki-31225846-abT630XXSBDZE3
test "$(grep '^PARTNAME=' /sys/class/block/sda26/uevent)" = PARTNAME=super
test "$(cat /sys/class/block/sda26/size)" = 18432000

system_table='0 12036096 linear 259:10 2048
12036096 16248 linear 259:10 17401856'
if ! dmsetup info t630-stock-system >/dev/null 2>&1; then
    printf '%s\n' "$system_table" | dmsetup create t630-stock-system --readonly
fi
test "$(dmsetup table t630-stock-system)" = "$system_table"
if [[ ! -b /dev/dm-0 ]]; then
    mknod /dev/dm-0 b 253 0
fi
test "$(cat /sys/class/block/dm-0/dm/name)" = t630-stock-system

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
    mount -t f2fs -o ro /dev/dm-0 /mnt/t630-stock-system
fi
mount_bind_ro /mnt/t630-stock-system/system /system
mount_image /home/tablet/stock-vendor-full.img /mnt/stock-vendor-full
mount_image /home/tablet/t630-vndk30-apex/apex_payload.img /mnt/t630-vndk30
mount_image /home/tablet/t630-apex/runtime/apex_payload.img /mnt/t630-runtime
mount_image /home/tablet/t630-apex/i18n/apex_payload.img /mnt/t630-i18n
mount_image /home/tablet/t630-camera-apex/apex_payload.img /mnt/t630-camera

mount_bind_ro /home/tablet/t630-vendor-view /vendor
mount_bind_ro /home/tablet/t630-linkerconfig /linkerconfig
mkdir -p /data
if ! mountpoint -q /data; then
    mount --bind /home/tablet/t630-android-data /data
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
    mount --bind /home/tablet/t630-system-overrides/cameraserver /system/bin/cameraserver
fi
chi=/mnt/stock-vendor-full/lib64/hw/com.qti.chi.override.so
if ! mountpoint -q "$chi"; then
    mount --bind /home/tablet/t630-vendor-overrides/com.qti.chi.override.so "$chi"
fi

ln -sf /usr/local/lib/t630-android-property-seed.so /dev/t630-android-property-seed.so
for firmware in /opt/t630/camera-firmware/*; do
    ln -sf "$firmware" "/run/input-firmware/${firmware##*/}"
done
if [[ ! -d /sys/module/camera ]]; then
    insmod /opt/t630/vendor/lib/modules/camera.ko
fi
/proc/1/root/bin/busybox mdev -s

test -c /dev/media0
test -c /dev/video0
test -x /system/bin/cameraserver
test -x /vendor/bin/hw/vendor.samsung.hardware.camera.provider@4.0-service_64
echo 'Camera lab runtime mounted; no Android writable partition was mounted.'
