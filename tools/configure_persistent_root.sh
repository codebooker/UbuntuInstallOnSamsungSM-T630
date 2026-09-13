#!/bin/busybox sh
set -eu
umask 022
root=/run/t630-install
grep -q '^/dev/sda34 /run/t630-install ext4 ' /proc/mounts
test "$(cat /run/persistent-root-install.exit)" = 0
test -x "$root/usr/bin/weston"
mkdir -p "$root/etc/chrony" "$root/etc/NetworkManager/conf.d" "$root/etc/udev/rules.d" "$root/root/.config" "$root/usr/local/lib" "$root/opt/t630"
cp /run/ubuntu/tmp/t630-drm-compat-v4.so "$root/usr/local/lib/t630-drm-compat.so"
cp /run/ubuntu/tmp/t630-drm-compat-v4.c "$root/opt/t630/t630-drm-compat.c"
cp /run/ubuntu/tmp/t630-weston-input.ini "$root/root/.config/weston.ini"
cp /run/ubuntu/etc/udev/rules.d/99-t630-input.rules "$root/etc/udev/rules.d/99-t630-input.rules"
cp /run/ubuntu/etc/NetworkManager/conf.d/90-t630-network.conf "$root/etc/NetworkManager/conf.d/90-t630-network.conf"
cp /run/ubuntu/tmp/chrony-ram.conf "$root/etc/chrony/t630.conf"
chmod 755 "$root/usr/local/lib/t630-drm-compat.so"
chmod 644 "$root/opt/t630/t630-drm-compat.c" "$root/root/.config/weston.ini"
printf '%s\n' ubuntablet >"$root/etc/hostname"
printf '%s\n' '127.0.0.1 localhost' '127.0.1.1 ubuntablet' '::1 localhost ip6-localhost ip6-loopback' >"$root/etc/hosts"
printf '%s\n' 'SM-T630-T630XXSBDZE3-Ubuntu-v1' >"$root/etc/t630-install-id"
printf '%s\n' '# Mounted by SM-T630 prototype initramfs; not a systemd boot.' >"$root/etc/fstab"
chroot "$root" /usr/bin/dpkg --audit
chroot "$root" /usr/bin/ldd /usr/bin/weston
chroot "$root" /usr/bin/ldd /usr/local/lib/t630-drm-compat.so
sha256sum "$root/usr/local/lib/t630-drm-compat.so"
test "$(dd if=/dev/sda34 bs=1 skip=1080 count=2 2>/dev/null | od -An -tx1 | tr -d ' \n')" = 53ef
test "$(dd if=/dev/sda34 bs=1 skip=1128 count=16 2>/dev/null | od -An -tx1 | tr -d ' \n')" = 64de854453ea4fdc8946d6b07e238630
sync
echo PERSISTENT_ROOT_CONFIGURED
