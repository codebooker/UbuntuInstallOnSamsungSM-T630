#!/bin/sh
set -eu

image=${1:-/workspace/port/stock/vendor.img}
mountpoint=/mnt/t630-vendor

mkdir -p "$mountpoint"
mount -t f2fs -o loop,ro "$image" "$mountpoint"
trap 'umount "$mountpoint"' EXIT

echo '=== Bluetooth firmware ==='
find "$mountpoint/firmware" -maxdepth 2 \( -type f -o -type l \) \
  \( -iname '*bt*' -o -iname '*nvm*' -o -iname 'hp*' -o -iname 'ms*' \) \
  -exec ls -l {} \;

echo '=== NVM loading configuration ==='
sed -n '1,240p' "$mountpoint/firmware/bt_nvm_loading.xml"

echo '=== Bluetooth service configuration ==='
sed -n '1,200p' \
  "$mountpoint/etc/init/android.hardware.bluetooth@1.0-service-qti.rc"

echo '=== Loader strings ==='
strings "$mountpoint/lib64/hw/android.hardware.bluetooth@1.0-impl-qti.so" |
  grep -Ei 'hpbt|hpnv|msbt|msnv|ttyHS|baud|firmware|nvm|qca|wcn' |
  head -240
