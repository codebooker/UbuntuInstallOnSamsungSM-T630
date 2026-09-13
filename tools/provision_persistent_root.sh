#!/bin/busybox sh
# ONE-TIME DESTRUCTIVE INSTALL, explicitly authorized by the owner.
# Exact target only; never execute this as part of boot.
set -eu
umask 022
test "$(uname -r)" = '5.4.274-qgki-31225846-abT630XXSBDZE3'
grep -q 'androidboot.em.model=SM-T630' /proc/cmdline
grep -qx 'PARTNAME=userdata' /sys/class/block/sda34/uevent
grep -qx 'PARTN=34' /sys/class/block/sda34/uevent
test "$(cat /sys/class/block/sda34/dev)" = 259:18
test "$(cat /sys/class/block/sda34/size)" = 226918360
test -b /dev/sda34
test ! -e /run/t630-install
test ! -e /run/t630-format-started
awk '$3 == "259:18" { found=1 } END { exit found ? 1 : 0 }' /proc/self/mountinfo
test "$(cat /sys/class/power_supply/battery/capacity)" -ge 30
test "$(cat /sys/class/power_supply/battery/status)" = Charging
chroot /run/ubuntu /usr/bin/dpkg --audit
touch /run/t630-format-started
chroot /run/ubuntu /usr/sbin/mkfs.ext4 -F -L ubuntu-t630 -U 64de8544-53ea-4fdc-8946-d6b07e238630 -m 1 -i 65536 -O ^orphan_file,^metadata_csum_seed -E nodiscard,lazy_itable_init=0,lazy_journal_init=0 /dev/sda34
mkdir -p /run/t630-install /run/ubuntu/mnt/t630-install
mount -t ext4 -o noatime,errors=remount-ro /dev/sda34 /run/t630-install
mount --bind /run/t630-install /run/ubuntu/mnt/t630-install
# Retain the owner's Wi-Fi profile only on their own tablet. Never export it.
chroot /run/ubuntu /bin/bash -o pipefail -c '
tar --one-file-system --xattrs --xattrs-include="*" --acls -cpf - \
 --exclude=./dev --exclude=./proc --exclude=./sys --exclude=./run \
 --exclude=./tmp --exclude=./mnt --exclude=./var/log \
 --exclude=./var/cache/apt/archives --exclude=./var/lib/apt/lists \
 --exclude=./root/.bash_history -C / . \
 | tar --xattrs --xattrs-include="*" --acls -xpf - -C /mnt/t630-install'
mkdir -p /run/t630-install/dev /run/t630-install/proc /run/t630-install/sys /run/t630-install/run /run/t630-install/tmp /run/t630-install/mnt /run/t630-install/var/log/chrony /run/t630-install/var/cache/apt/archives/partial /run/t630-install/var/lib/apt/lists/partial
chmod 755 /run/t630-install /run/t630-install/run
chmod 1777 /run/t630-install/tmp
chmod 755 /run/t630-install/var/lib/apt/lists /run/t630-install/var/cache/apt/archives /run/t630-install/var/log /run/t630-install/mnt
chroot /run/t630-install /usr/bin/chown _apt:root /var/lib/apt/lists/partial /var/cache/apt/archives/partial
chmod 700 /run/t630-install/var/lib/apt/lists/partial /run/t630-install/var/cache/apt/archives/partial
sync
echo 'ROOT_COPY_COMPLETE (configuration and verification still required)'
