#!/bin/bash
# Build an exact-source SM-T630 kernel with the existing fixes plus Waydroid prerequisites.
set -euo pipefail

for tool in bc cpio make patch python3 realpath sha256sum stat; do
    command -v "$tool" >/dev/null || {
        echo "Missing build tool: $tool" >&2
        exit 1
    }
done
test -f /usr/include/openssl/bio.h || {
    echo 'Missing OpenSSL development headers (Ubuntu package: libssl-dev).' >&2
    exit 1
}

if [ "$#" -ne 2 ]; then
    echo "usage: $0 FRESH_SAMSUNG_KERNEL_SOURCE EMPTY_OUTPUT_DIRECTORY" >&2
    exit 2
fi
source_tree=$(realpath "$1")
output=$2
case "$output" in
    /*) ;;
    *) echo 'Output directory must be absolute.' >&2; exit 2 ;;
esac
test ! -e "$output"
repo=$(cd "$(dirname "$0")/.." && pwd)
defconfig=arch/arm64/configs/vendor/gtact4prowifi_eur_open_defconfig

test -f "$source_tree/$defconfig"
test -f "$source_tree/drivers/bluetooth/hci_qca.c"
test -f "$source_tree/net/bluetooth/hci_sock.c"
# Samsung ships both names. A case-insensitive extraction silently merges them
# and later fails in xt_mark.c with incomplete structures.
test "$(stat -c '%d:%i' "$source_tree/include/uapi/linux/netfilter/xt_MARK.h")" != \
     "$(stat -c '%d:%i' "$source_tree/include/uapi/linux/netfilter/xt_mark.h")" || {
    echo 'Kernel source must be extracted on a case-sensitive Linux filesystem.' >&2
    exit 1
}
printf '%s  %s\n' \
    44d64f3796044b89ecc223b4025e818581dda5ea3e4ffc04d7b711f179b3739e \
    "$source_tree/$defconfig" | sha256sum -c -
printf '%s  %s\n' \
    09ada7b24c0396f40cc8139a0d152ef3211714045b042d7ce1681d99574b78e7 \
    "$source_tree/Makefile" | sha256sum -c -
printf '%s  %s\n' \
    277dbc439aba407a753be0cd1c6f8fb2ca636c08990ab2cb5dc2ac791fba67a5 \
    "$source_tree/drivers/bluetooth/hci_qca.c" | sha256sum -c -
printf '%s  %s\n' \
    42478547962e073015231d621289b61841d4f6f1b2ba0618afdbe1870b6fc1e4 \
    "$source_tree/net/bluetooth/hci_sock.c" | sha256sum -c -
printf '%s  %s\n' \
    e0662377a6c673e8f2e6f3c7539417924902950a2e4a753a73940cc871789bdc \
    "$source_tree/include/uapi/linux/netfilter/xt_MARK.h" | sha256sum -c -
printf '%s  %s\n' \
    eaac1d30d0f595a9cc160a8555d7b8ec7c9d3dc376eb8e6d29ecc3271ac029a2 \
    "$source_tree/include/uapi/linux/netfilter/xt_mark.h" | sha256sum -c -

for patch in "$repo"/patches/00{01,02,03,04,05,06,07,08,09,10,11,12,13,14,15,16,17,18,19}-*.patch; do
    test -f "$patch"
    patch -d "$source_tree" -p1 --forward --batch --dry-run < "$patch"
    patch -d "$source_tree" -p1 --forward --batch < "$patch"
done

mkdir "$output"
jobs=$(nproc)
if [ "$jobs" -gt 4 ]; then jobs=4; fi
build=(make -C "$source_tree" O="$output" ARCH=arm64
       CROSS_COMPILE=aarch64-linux-gnu- DISABLE_WRAPPER=1
       CONFIG_SECTION_MISMATCH_WARN_ONLY=y
       KCFLAGS=-Wno-error=incompatible-pointer-types\ -Wno-error=format\ -Wno-error=implicit-fallthrough\ -Wno-error=strict-prototypes\ -Wno-error)
"${build[@]}" vendor/gtact4prowifi_eur_open_defconfig
"${build[@]}" olddefconfig
python3 "$repo/tools/check_waydroid_kernel.py" "$output/.config"
"${build[@]}" -j"$jobs" Image modules

image="$output/arch/arm64/boot/Image"
test -s "$image"
test "$(stat -c %s "$image")" -gt 10000000
sha256sum "$image"
module_count=$(find "$output" -type f -name '*.ko' | wc -l)
test "$module_count" -gt 50
printf 'Built %s external hardware modules.\n' "$module_count"
