#!/bin/sh
# Rehearse the exact 4 KiB-sector split and GPT rollback on a sparse file only.
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
image=$root/output/t630-dualboot-rehearsal.img
bytes=127385206784

test ! -e "$image"
mkdir -p "$root/output"
truncate -s "$bytes" "$image"
test -f "$image"
test ! -L "$image"
test "$(stat -f %z "$image" 2>/dev/null || stat -c %s "$image")" = "$bytes"

docker run --rm --privileged -v "$image:/work/disk.img" ubuntu:24.04 bash -ceu '
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq gdisk e2fsprogs util-linux >/dev/null

loop=$(losetup --find --show --sector-size 4096 /work/disk.img)
part=
android=
cleanup() {
    umount /mnt/test 2>/dev/null || true
    [ -z "$android" ] || losetup -d "$android" 2>/dev/null || true
    [ -z "$part" ] || losetup -d "$part" 2>/dev/null || true
    losetup -d "$loop" 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM
test "$(blockdev --getss "$loop")" = 4096
test "$(blockdev --getsz "$loop")" = 248799232

sgdisk --clear \
    --new=34:2735104:31099898 \
    --typecode=34:A03A \
    --change-name=34:userdata "$loop" >/dev/null
part=$(losetup --find --show --offset $((2735104 * 4096)) \
    --sizelimit $((28364795 * 4096)) /work/disk.img)
test -b "$part"
test "$(blockdev --getsz "$part")" = 226918360

mke2fs -q -t ext4 -b 4096 -U 64de8544-53ea-4fdc-8946-d6b07e238630 \
    -E lazy_itable_init=1,lazy_journal_init=1 "$part"
mkdir -p /mnt/test
mount "$part" /mnt/test
printf "%s\n" SM-T630-DUALBOOT-REHEARSAL >/mnt/test/marker
sync
umount /mnt/test
e2fsck -fp "$part"

# Interruption before this point leaves the original GPT and filesystem.
resize2fs "$part" 16777216 >/dev/null
e2fsck -fp "$part"
test "$(dumpe2fs -h "$part" 2>/dev/null | sed -n "s/^Block count:[[:space:]]*//p")" = 16777216
# Interruption here is also recoverable: the filesystem is merely smaller than
# the still-original partition.

sgdisk --backup=/work/gpt-before-split.bin "$loop" >/dev/null
unique=$(sgdisk --info=34 "$loop" | sed -n "s/^Partition unique GUID: //p")
test -n "$unique"
sgdisk \
    --delete=34 \
    --new=34:2735104:19512319 \
    --typecode=34:8300 \
    --partition-guid=34:"$unique" \
    --change-name=34:linuxroot \
    --new=35:19512320:31099898 \
    --typecode=35:A03A \
    --change-name=35:userdata "$loop" >/dev/null
losetup -d "$part"
part=$(losetup --find --show --offset $((2735104 * 4096)) \
    --sizelimit $((16777216 * 4096)) /work/disk.img)
android=$(losetup --find --show --offset $((19512320 * 4096)) \
    --sizelimit $((11587579 * 4096)) /work/disk.img)
test "$(blockdev --getsz "$part")" = 134217728
test "$(blockdev --getsz "$android")" = 92700632
sgdisk --info=34 "$loop" | grep -q "Partition name: .linuxroot."
sgdisk --info=35 "$loop" | grep -q "Partition name: .userdata."
mount "$part" /mnt/test
grep -qx SM-T630-DUALBOOT-REHEARSAL /mnt/test/marker
umount /mnt/test

# Prove the saved GPT can roll the table back after the filesystem shrink.
sgdisk --load-backup=/work/gpt-before-split.bin "$loop" >/dev/null
sgdisk --info=34 "$loop" | grep -q "Partition name: .userdata."
if sgdisk --info=35 "$loop" 2>/dev/null | grep -q "Partition name:"; then
    echo "partition 35 survived GPT rollback" >&2
    exit 1
fi
losetup -d "$android"
android=
losetup -d "$part"
part=$(losetup --find --show --offset $((2735104 * 4096)) \
    --sizelimit $((28364795 * 4096)) /work/disk.img)
test "$(blockdev --getsz "$part")" = 226918360
mount "$part" /mnt/test
grep -qx SM-T630-DUALBOOT-REHEARSAL /mnt/test/marker
umount /mnt/test
e2fsck -fp "$part"
echo DUALBOOT_SPARSE_REHEARSAL_AND_GPT_ROLLBACK_PASSED
'

du -h "$image"
rm -f "$image"
test ! -e "$image"
