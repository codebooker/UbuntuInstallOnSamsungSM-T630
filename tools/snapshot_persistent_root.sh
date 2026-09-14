#!/bin/sh
# LAB BACKUP ONLY. This retains the installed human account and must never be
# published or used as the base of a release installer. A release root must be
# built from generic Ubuntu packages and pass audit_release_root.py.
set -eu
umask 077
test ! -e /tmp/desktop-snapshot.tar.gz
tar --one-file-system -czf /tmp/desktop-snapshot.tar.gz \
 --exclude=./dev --exclude=./proc --exclude=./sys --exclude=./run \
 --exclude=./tmp --exclude=./mnt --exclude=./var/log \
 --exclude=./var/cache/apt/archives --exclude=./var/lib/apt/lists \
 --exclude=./etc/netplan --exclude=./etc/NetworkManager/system-connections \
 --exclude=./var/lib/NetworkManager --exclude=./var/lib/chrony \
 --exclude=./root/.bash_history -C / .
tar -tzf /tmp/desktop-snapshot.tar.gz >/dev/null
sha256sum /tmp/desktop-snapshot.tar.gz
