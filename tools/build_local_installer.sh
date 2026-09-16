#!/bin/sh
# Build the complete private installer input set. Performs no device I/O.
set -eu

if [ "$#" -ne 4 ]; then
    echo "usage: sudo $0 UBUNTU_BASE PACKAGE_DIR ACCEPTED_KERNEL NEW_WORK_DIR" >&2
    exit 2
fi

base=$1
packages=$2
kernel=$3
work=$4
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)

test "$(id -u)" = 0 || { echo "root is required" >&2; exit 1; }
test "$(uname -s)" = Linux || { echo "build must run on Linux" >&2; exit 1; }
case "$(uname -m)" in
    aarch64|arm64) ;;
    *) echo "build must run on ARM64" >&2; exit 1 ;;
esac
test -f "$base"
test -d "$packages"
test -f "$kernel"
case "$work" in /|"") echo "refusing broad or empty work directory" >&2; exit 2 ;; esac
test ! -e "$work" || { echo "work directory must not exist" >&2; exit 2; }
parent=$(dirname -- "$work")
test -d "$parent"
work=$(cd -- "$parent" && pwd -P)/$(basename -- "$work")
mkdir -m 0700 "$work"

root=$work/root
python3 "$script_dir/prepare_rehearsal_root.py" "$base" "$root"
"$script_dir/provision_rehearsal_root.sh" "$root"
python3 "$script_dir/assemble_release_root.py" "$packages" --root "$root" --apply
"$script_dir/check_rehearsal_root.sh" "$root"
python3 "$script_dir/build_installer_runtime.py" \
    "$root" "$work/t630-installer-runtime.tar.gz"
python3 "$script_dir/build_release_archive.py" \
    "$root" "$work/t630-release-rootfs.tar.gz"
python3 "$script_dir/build_boot_persistent.py" \
    --kernel "$kernel" --output "$work/boot"
python3 "$script_dir/audit_release_root.py" "$root"
python3 "$script_dir/finalize_installer_bundle.py" "$work"
chmod 0600 "$work/t630-release-rootfs.tar.gz" \
    "$work/t630-release-rootfs.tar.gz.manifest.json" \
    "$work/t630-installer-runtime.tar.gz" \
    "$work/t630-installer-runtime.tar.gz.manifest.json" \
    "$work/boot/boot.img" "$work/boot/manifest.json" \
    "$work/installer-bundle.json" "$work/SHA256SUMS"

echo "LOCAL_INSTALLER_BUILD_COMPLETE"
echo "rootfs=$work/t630-release-rootfs.tar.gz"
echo "boot=$work/boot/boot.img"
echo "checksums=$work/SHA256SUMS"
echo "No device was opened or written."
