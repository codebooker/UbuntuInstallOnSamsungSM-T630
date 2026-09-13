#!/bin/sh
# Ubuntu desktop packages only; no display-manager/startup replacement.
set -u
export DEBIAN_FRONTEND=noninteractive
/usr/bin/apt-get install -y --no-install-recommends gnome-shell gnome-session gnome-control-center dbus-x11 ibus gjs xauth x11-utils libdecor-0-plugin-1-gtk at-spi2-core gnome-backgrounds > /run/t630-gnome-install.log 2>&1
result=$?
printf '%s\n' "$result" > /run/t630-gnome-install.exit
exit "$result"
