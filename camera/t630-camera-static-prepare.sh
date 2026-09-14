#!/bin/bash
# Reconstruct private camera files from the tablet's read-only stock super.
set -euo pipefail

test "$(id -u)" = 0
test "$(cat /etc/t630-install-id)" = SM-T630-T630XXSBDZE3-Ubuntu-v1
test "$(uname -r)" = 5.4.274-qgki-31225846-abT630XXSBDZE3
test "$(grep '^PARTNAME=' /sys/class/block/sda26/uevent)" = PARTNAME=super
test "$(cat /sys/class/block/sda26/size)" = 18432000
test "$#" -le 1
output=${1:-/var/lib/t630-camera/static}
case "$output" in
    /var/lib/t630-camera/static|/opt/t630/rehearsal/camera-static-*) ;;
    *) echo 'output must be the final private path or a dedicated rehearsal path' >&2
       exit 2 ;;
esac
test ! -e "$output"
test ! -L "$output"

for mapping in t630-prepare-system t630-prepare-vendor \
        t630-stock-system t630-stock-vendor; do
    if dmsetup info "$mapping" >/dev/null 2>&1; then
        echo "camera mapping is already active: $mapping" >&2
        exit 1
    fi
done

work=$(mktemp -d /run/t630-camera-prepare.XXXXXX)
system_mount=$work/system
vendor_mount=$work/vendor
mkdir "$system_mount" "$vendor_mount"

cleanup() {
    set +e
    mountpoint -q "$vendor_mount" && umount "$vendor_mount"
    mountpoint -q "$system_mount" && umount "$system_mount"
    dmsetup remove t630-prepare-vendor >/dev/null 2>&1
    dmsetup remove t630-prepare-system >/dev/null 2>&1
    rm -f "$work/system.json" "$work/vendor.json" \
        "$work/system.table" "$work/vendor.table"
    rmdir "$vendor_mount" "$system_mount" "$work" 2>/dev/null
}
trap cleanup EXIT INT TERM

super_device=$(cat /sys/class/block/sda26/dev)
[[ "$super_device" =~ ^[0-9]+:[0-9]+$ ]]
for partition in system vendor; do
    python3 /usr/local/share/t630/extract-dynamic-partition.py /dev/sda26 \
        --partition "$partition" --device "$super_device" >"$work/$partition.json"
    python3 - "$work/$partition.json" >"$work/$partition.table" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    records = json.load(stream)
if len(records) != 1 or not records[0].get("dm_table"):
    raise SystemExit("missing verified device-mapper table")
print("\n".join(records[0]["dm_table"]))
PY
    dmsetup create "t630-prepare-$partition" --readonly <"$work/$partition.table"
done

mapper_node() {
    local name=$1 number major minor node
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

system_device=$(mapper_node t630-prepare-system)
vendor_device=$(mapper_node t630-prepare-vendor)
mount -t f2fs -o ro "$system_device" "$system_mount"
mount -t f2fs -o ro "$vendor_device" "$vendor_mount"
python3 /usr/local/share/t630/prepare-camera-static-assets.py \
    "$system_mount/system" "$vendor_mount" "$output"
test -f "$output/manifest.json"
echo "Private camera runtime reconstructed at $output"
