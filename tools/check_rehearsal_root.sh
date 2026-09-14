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
    t630-hardware-runtime t630-boot-runtime t630-native-userspace t630-pd-mapper \
    libssc hexagonrpcd iio-sensor-proxy t630-stock-assets

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
echo "native_linkage: valid"

if findmnt -rn -o TARGET | grep -q "^$root\(/\|$\)"; then
    echo "rehearsal root still contains mounted host filesystems" >&2
    exit 1
fi
echo "mount_leaks: none"
du -sh "$root" | awk '{print "root_size: " $1}'
