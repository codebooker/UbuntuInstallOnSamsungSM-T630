#!/bin/sh
# Install the public Ubuntu dependencies into a marked, offline rehearsal root.
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: $0 OFFLINE_ROOT" >&2
    exit 2
fi

root=$1
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
case "$root" in
    /|"") echo "refusing live or empty root" >&2; exit 2 ;;
esac
if [ -L "$root" ] || [ ! -d "$root" ]; then
    echo "offline root must be a real directory" >&2
    exit 2
fi
root=$(cd -- "$root" && pwd -P)
if [ "$(cat "$root/.t630-offline-root" 2>/dev/null || true)" != "SM-T630 OFFLINE RELEASE ROOT" ]; then
    echo "offline root marker is absent or invalid" >&2
    exit 2
fi
if ! grep -qx 'ID=ubuntu' "$root/etc/os-release" ||
   ! grep -qx 'VERSION_ID="24.04"' "$root/etc/os-release"; then
    echo "offline root is not Ubuntu 24.04" >&2
    exit 2
fi

mounted_dev=0
mounted_proc=0
mounted_sys=0
mounted_dns=0
cleanup() {
    rm -f -- "$root/usr/sbin/policy-rc.d"
    if [ "$mounted_dns" -eq 1 ]; then umount "$root/etc/resolv.conf" || true; fi
    if [ "$mounted_sys" -eq 1 ]; then umount "$root/sys" || true; fi
    if [ "$mounted_proc" -eq 1 ]; then umount "$root/proc" || true; fi
    if [ "$mounted_dev" -eq 1 ]; then umount -R "$root/dev" || true; fi
}
trap cleanup EXIT HUP INT TERM

install -m 0755 "$script_dir/rehearsal-policy-rc.d" "$root/usr/sbin/policy-rc.d"
mount --rbind /dev "$root/dev"
mount --make-rslave "$root/dev"
mounted_dev=1
mount -t proc proc "$root/proc"
mounted_proc=1
mount -t sysfs sysfs "$root/sys"
mounted_sys=1
mount --bind /etc/resolv.conf "$root/etc/resolv.conf"
mounted_dns=1

chroot "$root" /usr/bin/env \
    DEBIAN_FRONTEND=noninteractive LC_ALL=C \
    apt-get update
chroot "$root" /usr/bin/env \
    DEBIAN_FRONTEND=noninteractive LC_ALL=C \
    apt-get install -y --no-install-recommends \
    alsa-utils bluez dbus gir1.2-gtk-3.0 gnome-shell \
    iio-sensor-proxy libdrm2 libglib2.0-0t64 libglib2.0-bin \
    libgtk-3-0t64 libgudev-1.0-0 liblzma5 libprotobuf-c1 \
    libqmi-glib5 libqrtr-glib0 libwayland-client0 libweston-13-0 \
    libxcb1 locales network-manager passwd pipewire pipewire-pulse \
    python3 python3-gi util-linux wireplumber x11-utils xauth xdotool \
    xwayland

cleanup
trap - EXIT HUP INT TERM
# systemd and DBus legitimately create these while their packages configure.
# A distributable image must generate fresh identities on its first real boot.
truncate -s 0 "$root/etc/machine-id"
rm -f -- "$root/var/lib/dbus/machine-id" "$root/var/lib/systemd/random-seed"
python3 "$script_dir/audit_release_root.py" "$root"
