#!/bin/sh
# Runs inside installed Ubuntu; no credentials or transient state in backup.
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
