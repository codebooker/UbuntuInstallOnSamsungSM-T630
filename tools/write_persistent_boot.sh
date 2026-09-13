#!/bin/busybox sh
# Authorized one-time BOOT update. Never formats/repartitions or writes VBMETA.
set -eu
test "$(uname -r)" = '5.4.274-qgki-31225846-abT630XXSBDZE3'
grep -q 'androidboot.em.model=SM-T630' /proc/cmdline
grep -qx 'PARTNAME=boot' /sys/class/block/sda19/uevent
test "$(cat /sys/class/block/sda19/dev)" = 259:3
test "$(cat /sys/class/block/sda19/size)" = 196608
test -b /dev/sda19
awk '$3 == "259:3" { found=1 } END { exit found ? 1 : 0 }' /proc/self/mountinfo
test "$(cat /sys/class/power_supply/battery/capacity)" -ge 30
test "$(cat /sys/class/power_supply/battery/status)" = Charging
test "$(cat /run/t630-install/etc/t630-install-id)" = 'SM-T630-T630XXSBDZE3-Ubuntu-v1'
test "$(cat /run/ubuntu/tmp/root-copy-check.exit)" = 0
test "$(stat -c %s /run/ubuntu/tmp/persistent-boot-v1.img)" = 100663296
echo '297cf31e5914ff6a17d1e1d6499d2af2a493022c56336978b76e61e14b9c910a  /run/ubuntu/tmp/persistent-boot-v1.img' | sha256sum -c -
echo '596292caf0365d3f790bc205bdfca3cfaca9d7033d472e863a83bb883b833ea7  /dev/sda19' | sha256sum -c -
chroot /run/ubuntu /usr/bin/dd if=/tmp/persistent-boot-v1.img of=/dev/sda19 bs=1M conv=fsync status=none
sync
echo '297cf31e5914ff6a17d1e1d6499d2af2a493022c56336978b76e61e14b9c910a  /dev/sda19' | sha256sum -c -
echo '2b6901f8341de3b76fbcabc69bf0229683d503f233eafd580b4d602392ff74f5  /dev/sda20' | sha256sum -c -
echo 'fbebd763c17c05bc162776a6e9abd86fc386aa0ef58ccfdaa6cb9b13a6a0c72f  /dev/sda21' | sha256sum -c -
echo 'f9111b7a566b0a7342ec4d8f14cee53dc465a272d42596f774c0519d6e89fc57  /dev/sda22' | sha256sum -c -
echo 'a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225  /dev/sde19' | sha256sum -c -
echo BOOT_WRITTEN_READBACK_VERIFIED_PROTECTED_PARTITIONS_UNCHANGED
