#!/bin/bash
# Build the isolated, read-only Android camera runtime inside Ubuntu.
set -euo pipefail

test "$(cat /etc/t630-install-id)" = SM-T630-T630XXSBDZE3-Ubuntu-v1
test "$(uname -r)" = 5.4.274-qgki-31225846-abT630XXSBDZE3
test "$(grep '^PARTNAME=' /sys/class/block/sda26/uevent)" = PARTNAME=super
test "$(cat /sys/class/block/sda26/size)" = 18432000
super_device=$(cat /sys/class/block/sda26/dev)
[[ "$super_device" =~ ^[0-9]+:[0-9]+$ ]]
camera_static=/var/lib/t630-camera/static
camera_runtime=/run/t630-camera

test "$(sha256sum "$camera_static/runtime/apex_payload.img" | cut -d' ' -f1)" = \
    933852072eda61c000f1e0f34570c92f420e02ad765735685645c73bab561f9a
test "$(sha256sum "$camera_static/i18n/apex_payload.img" | cut -d' ' -f1)" = \
    1a81d87cf37e8767ab1cc996d2e955f4f2657261ac7ffabc52df8c3bbac53c61
test "$(sha256sum "$camera_static/vndk30/apex_payload.img" | cut -d' ' -f1)" = \
    cbf2391730c65de571ec48b6e30bba2099d6f09576613628cc4359453a0ce36b
test "$(sha256sum "$camera_static/camera/apex_payload.img" | cut -d' ' -f1)" = \
    ccc35ded4ac562dcd2b4dbfe0d3aadad36feb25660d1977ae6b53d8be9fb124f
test "$(sha256sum "$camera_static/system/cameraserver" | cut -d' ' -f1)" = \
    5429480613566f22182d5ba99ea3af35d3b586fa290a88e5c895dcf6eee70202
test "$(sha256sum "$camera_static/vendor/com.qti.chi.override.so" | cut -d' ' -f1)" = \
    cdcb884968c7522bc9005615bee732d4b0265bde70f2828b0b7f31c35097b524

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
mount_image "$camera_static/vndk30/apex_payload.img" /mnt/t630-vndk30
mount_image "$camera_static/runtime/apex_payload.img" /mnt/t630-runtime
mount_image "$camera_static/i18n/apex_payload.img" /mnt/t630-i18n
mount_image "$camera_static/camera/apex_payload.img" /mnt/t630-camera

install -d -o root -g root -m 0755 \
    "$camera_runtime/vendor-view" "$camera_runtime/linkerconfig"
for name in apex app bin bt_firmware build.prop default.prop dsp etc firmware \
        firmware-modem firmware_mnt gpu lib lib64 odm overlay recovery-from-boot.p \
        rfs saiv tima_measurement_info ueventd.rc vm-system; do
    ln -sfn "/mnt/stock-vendor-full/$name" "$camera_runtime/vendor-view/$name"
done
install -o root -g root -m 0644 \
    /usr/local/share/t630/camera-templates/vendor-manifest.xml \
    "$camera_runtime/vendor-view/manifest.xml"
install -o root -g root -m 0644 \
    /usr/local/share/t630/camera-templates/ld.config.txt \
    "$camera_runtime/linkerconfig/ld.config.txt"
mount_bind_ro "$camera_runtime/vendor-view" /vendor
mount_bind_ro "$camera_runtime/linkerconfig" /linkerconfig
# Camera HAL cache and warm-start state are machine data, not user data.  An
# empty directory is intentional: the exact DZE3 HAL recreates every required
# file on first camera use from the read-only stock image and hardware.
install -d -o root -g root -m 0771 \
    /var/lib/t630-camera /var/lib/t630-camera/android-data \
    /var/lib/t630-camera/android-data/vendor
install -d -o root -g root -m 0770 \
    /var/lib/t630-camera/android-data/vendor/camera
mkdir -p /data
if ! mountpoint -q /data; then
    mount --bind /var/lib/t630-camera/android-data /data
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
    mount --bind "$camera_static/system/cameraserver" /system/bin/cameraserver
fi
chi=/mnt/stock-vendor-full/lib64/hw/com.qti.chi.override.so
if ! mountpoint -q "$chi"; then
    mount --bind "$camera_static/vendor/com.qti.chi.override.so" "$chi"
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
