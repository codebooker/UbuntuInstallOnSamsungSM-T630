#!/bin/sh
# Arm exactly one boot of the preserved identity-clean rehearsal root.
set -eu

root=/opt/t630/rehearsal/release-root
selector=/.t630-next-root

test "$(id -u)" = 0
test "$(cat /etc/t630-install-id)" = SM-T630-T630XXSBDZE3-Ubuntu-v1
test -d "$root"
test ! -L "$root"
test "$(stat -c %d /)" = "$(stat -c %d "$root")"
test -f "$root/.t630-offline-root"
test ! -L "$root/.t630-offline-root"
test "$(cat "$root/.t630-offline-root")" = 'SM-T630 OFFLINE RELEASE ROOT'
test "$(cat "$root/etc/t630-install-id")" = SM-T630-T630XXSBDZE3-Ubuntu-v1
test ! -e "$root/etc/t630/owner"
test ! -e "$selector"
test ! -L "$selector"
test -z "$(find "$root/home" -mindepth 1 -maxdepth 1 -print -quit)"
test ! -s "$root/etc/machine-id"
chroot "$root" /usr/bin/dpkg --audit

umask 077
printf '%s\n' opt/t630/rehearsal/release-root >"$selector"
sync
echo T630_CLEAN_ROOT_ONE_SHOT_ARMED
