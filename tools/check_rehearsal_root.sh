#!/bin/sh
# Verify a completed offline release-root rehearsal without booting it.
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

echo "identity_audit:"
python3 "$script_dir/audit_release_root.py" "$root"

echo "dpkg_audit:"
dpkg --root="$root" --audit

echo "release_packages:"
chroot "$root" dpkg-query -W \
    -f='${Package} ${Version} ${db:Status-Status}\n' \
    t630-release-base t630-first-boot t630-desktop-runtime \
    t630-hardware-runtime t630-boot-runtime t630-polkit-runtime \
    t630-login-runtime \
    t630-native-userspace t630-pd-mapper \
    libssc hexagonrpcd iio-sensor-proxy t630-stock-assets

echo "everyday_apps:"
chroot "$root" dpkg-query -W \
    -f='${Package} ${Version} ${db:Status-Status}\n' \
    firefox gnome-software packagekit nautilus gnome-text-editor \
    gnome-terminal libreoffice-writer libreoffice-calc libreoffice-impress \
    evince eog file-roller gnome-calculator gnome-calendar gnome-contacts \
    gnome-clocks gnome-snapshot gnome-system-monitor totem
firefox_version=$(chroot "$root" dpkg-query -W -f='${Version}' firefox)
case "$firefox_version" in
    1:1snap*) echo "Ubuntu Firefox Snap transition package installed" >&2; exit 1 ;;
esac
if [ "$(chroot "$root" dpkg-query -W -f='${db:Status-Status}' snapd 2>/dev/null || true)" = installed ]; then
    echo "snapd must not be present on the stock-kernel image" >&2
    exit 1
fi
echo "3ecc63922b7795eb23fdc449ff9396f9114cb3cf186d6f5b53ad4cc3ebfbb11f  $root/etc/apt/keyrings/packages.mozilla.org.asc" |
    sha256sum -c - >/dev/null
grep -qx 'URIs: https://packages.mozilla.org/apt' \
    "$root/etc/apt/sources.list.d/mozilla.sources"
grep -qx 'Pin-Priority: -1' "$root/etc/apt/preferences.d/mozilla-firefox"
echo "native_firefox: valid"

if [ "$(cat "$root/etc/t630-install-id")" != \
     "SM-T630-T630XXSBDZE3-Ubuntu-v1" ]; then
    echo "installed device marker mismatch" >&2
    exit 1
fi
echo "install_id: valid"

if chroot "$root" ldd /usr/local/libexec/t630-capture | grep -q 'not found'; then
    echo "t630-capture has unresolved libraries" >&2
    exit 1
fi
if chroot "$root" ldd /usr/lib/aarch64-linux-gnu/weston/t630-rotation.so |
        grep -q 'not found'; then
    echo "t630-rotation.so has unresolved libraries" >&2
    exit 1
fi
if chroot "$root" ldd /usr/bin/weston | grep -q 'not found'; then
    echo "weston has unresolved libraries" >&2
    exit 1
fi
if chroot "$root" ldd /usr/bin/maliit-keyboard | grep -q 'not found'; then
    echo "maliit-keyboard has unresolved libraries" >&2
    exit 1
fi
if chroot "$root" ldd /usr/local/libexec/t630-polkit-agent |
        grep -q 'not found'; then
    echo "t630-polkit-agent has unresolved libraries" >&2
    exit 1
fi
for binary in \
    /opt/t630/elogind-255.27/libexec/elogind \
    /opt/t630/elogind-255.27/lib/security/pam_elogind.so \
    /opt/t630/gdm-46.2-auth/sbin/gdm \
    /opt/t630/gdm-46.2-auth/libexec/gdm-session-worker; do
    if chroot "$root" ldd "$binary" | grep -q 'not found'; then
        echo "login runtime has unresolved libraries: $binary" >&2
        exit 1
    fi
done
if [ ! -f "$root/etc/t630/login.enabled" ] ||
   [ ! -f "$root/etc/t630/lock-on-start" ] ||
   [ ! -f "$root/etc/pam.d/common-session.t630-stock" ]; then
    echo "login runtime marker or PAM diversion is missing" >&2
    exit 1
fi
for path in \
    usr/libexec/weston-keyboard \
    usr/libexec/weston-keyboard.t630-stock \
    usr/lib/aarch64-linux-gnu/maliit/keyboard2/qml/Keyboard.qml \
    usr/lib/aarch64-linux-gnu/maliit/keyboard2/qml/Keyboard.qml.t630-stock \
    usr/local/share/t630/gnome-resource-overlay/keyboard.js \
    usr/local/share/t630/gnome-resource-overlay/unlockDialog.js \
    usr/local/share/t630/icons/controls.png \
    usr/local/share/t630/icons/files.png \
    usr/local/share/t630/icons/editor.png \
    usr/local/share/t630/weston.ini; do
    if [ ! -f "$root/$path" ]; then
        echo "boot runtime asset missing: /$path" >&2
        exit 1
    fi
done
if [ ! -f "$root/usr/share/dbus-1/system-services/"\
"org.freedesktop.PolicyKit1.service.t630-stock" ]; then
    echo "PolicyKit service diversion is missing" >&2
    exit 1
fi
echo "native_linkage: valid"

if findmnt -rn -o TARGET | grep -q "^$root\(/\|$\)"; then
    echo "rehearsal root still contains mounted host filesystems" >&2
    exit 1
fi
echo "mount_leaks: none"
du -sh "$root" | awk '{print "root_size: " $1}'
