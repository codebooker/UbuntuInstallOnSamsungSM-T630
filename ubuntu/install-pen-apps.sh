#!/bin/sh
# Optional physical evaluation, not yet part of the accepted release package set.
set -eu
if [ "$(id -u)" -ne 0 ] || [ ! -x /usr/local/bin/t630-gnome-run ]; then
    echo 'Run as root inside the configured tablet Ubuntu installation.' >&2
    exit 2
fi
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export DEBIAN_FRONTEND=noninteractive
apt-get install -y --no-install-recommends at-spi2-core xournalpp mypaint mypaint-data-extras
install -m 0755 "$script_dir/t630-pen-app.py" /usr/local/bin/t630-pen-app
install -d -m 0755 /usr/local/share/applications
install -m 0644 "$script_dir/t630-xournalpp.desktop" \
    /usr/local/share/applications/com.github.xournalpp.xournalpp.desktop
install -m 0644 "$script_dir/t630-mypaint.desktop" \
    /usr/local/share/applications/mypaint.desktop
update-desktop-database /usr/local/share/applications
# Do not auto-pin: GNOME 46 excludes favorites from its application drawer.
