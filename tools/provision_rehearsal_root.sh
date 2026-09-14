#!/bin/sh
# Install the public Ubuntu dependencies into a marked, offline rehearsal root.
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: $0 OFFLINE_ROOT" >&2
    exit 2
fi

root=$1
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
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
    rm -f -- "$root/tmp/packages.mozilla.org.asc"
    rm -rf -- "$root/tmp/t630-gpg-home"
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
    ca-certificates curl gpg sudo dmsetup

# Ubuntu's firefox package transitions to Snap, whose namespace assumptions do
# not work on the stock Samsung kernel. Use Mozilla's signed native ARM64 DEB
# repository and fail closed if its independently documented key changes.
chroot "$root" curl -fsSL --retry 3 \
    https://packages.mozilla.org/apt/repo-signing-key.gpg \
    -o /tmp/packages.mozilla.org.asc
echo "3ecc63922b7795eb23fdc449ff9396f9114cb3cf186d6f5b53ad4cc3ebfbb11f  $root/tmp/packages.mozilla.org.asc" |
    sha256sum -c -
install -d -m 0700 "$root/tmp/t630-gpg-home"
fingerprint=$(chroot "$root" gpg --batch --homedir /tmp/t630-gpg-home \
    --show-keys --with-colons \
    /tmp/packages.mozilla.org.asc | awk -F: '$1 == "fpr" {print $10; exit}')
if [ "$fingerprint" != 35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3 ]; then
    echo "Mozilla signing-key fingerprint mismatch" >&2
    exit 1
fi
install -d -m 0755 "$root/etc/apt/keyrings" "$root/etc/apt/preferences.d"
install -m 0644 "$root/tmp/packages.mozilla.org.asc" \
    "$root/etc/apt/keyrings/packages.mozilla.org.asc"
install -m 0644 "$repo_dir/ubuntu/mozilla.sources" \
    "$root/etc/apt/sources.list.d/mozilla.sources"
install -m 0644 "$repo_dir/ubuntu/mozilla-firefox.pref" \
    "$root/etc/apt/preferences.d/mozilla-firefox"
rm -f -- "$root/tmp/packages.mozilla.org.asc"
chroot "$root" /usr/bin/env \
    DEBIAN_FRONTEND=noninteractive LC_ALL=C \
    apt-get update
chroot "$root" /usr/bin/env \
    DEBIAN_FRONTEND=noninteractive LC_ALL=C \
    apt-get install -y --no-install-recommends \
    alsa-utils bluez breeze-icon-theme chrony dbus file librsvg2-common \
    gir1.2-gtk-3.0 gdm3 gnome-shell \
    iio-sensor-proxy libdrm2 libglib2.0-0t64 libglib2.0-bin \
    libgtk-3-0t64 libgudev-1.0-0 liblzma5 libprotobuf-c1 libqt5svg5 \
    libqmi-glib5 libqrtr-glib0 libwayland-client0 libweston-13-0 \
    libxcb1 locales maliit-framework maliit-keyboard network-manager passwd \
    pipewire pipewire-pulse python3 python3-gi qtwayland5 seatd util-linux \
    weston wireplumber x11-utils xauth xdotool xwayland sudo dmsetup \
    desktop-file-utils eog evince evolution-data-server file-roller firefox \
    fonts-crosextra-caladea fonts-crosextra-carlito fonts-noto-color-emoji \
    gnome-calculator gnome-calendar gnome-characters gnome-clocks \
    gnome-contacts gnome-disk-utility gnome-font-viewer gnome-snapshot \
    gnome-software gnome-system-monitor gnome-terminal gnome-text-editor \
    gstreamer1.0-libav gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-base-apps gstreamer1.0-plugins-good \
    gstreamer1.0-tools gvfs-backends gvfs-fuse hunspell-en-us \
    libreoffice-calc libreoffice-gtk3 libreoffice-impress libreoffice-writer \
    nautilus packagekit totem xdg-user-dirs xdg-utils

cleanup
trap - EXIT HUP INT TERM
# Do not carry build downloads or GnuPG state created only to inspect Mozilla's
# public key into the release image. APT indexes and AppStream metadata stay so
# GNOME Software has a catalog on first boot.
chroot "$root" apt-get clean
rm -rf -- "$root/root/.gnupg"
rmdir "$root/root/.cache" 2>/dev/null || true
# systemd and DBus legitimately create these while their packages configure.
# A distributable image must generate fresh identities on its first real boot.
truncate -s 0 "$root/etc/machine-id"
rm -f -- "$root/var/lib/dbus/machine-id" "$root/var/lib/systemd/random-seed"
python3 "$script_dir/audit_release_root.py" "$root"
