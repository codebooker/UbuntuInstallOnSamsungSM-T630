#!/bin/bash
# Build the exact public Qualcomm WLAN release against a completed Waydroid kernel build.
set -euo pipefail

release=5.4.274-qgki-31225846-abT630XXSBDZE3
qcacld_commit=4e15799e1f443577a9a102bc0c9564259e502b03
host_cmn_commit=0904701ee8ae065bbc920c7d5a2a11c0c645ebaa
fw_api_commit=2b58351f875928929af63aa548fa0b84f3050587
base=https://git.codelinaro.org/clo/la/platform/vendor/qcom-opensource/wlan

if [ "$#" -ne 4 ]; then
    echo "usage: $0 KERNEL_SOURCE KERNEL_BUILD EMPTY_WLAN_WORKSPACE OUTPUT_MODULE" >&2
    exit 2
fi

source_tree=$(realpath "$1")
kernel_build=$(realpath "$2")
workspace=$3
output=$4
repo=$(cd "$(dirname "$0")/.." && pwd)

for tool in git make modinfo python3 realpath sha256sum stat; do
    command -v "$tool" >/dev/null || {
        echo "Missing build tool: $tool" >&2
        exit 1
    }
done
command -v "${CC:-clang}" >/dev/null || {
    echo "Missing compiler: ${CC:-clang}" >&2
    exit 1
}
command -v "${LD:-ld.lld}" >/dev/null || {
    echo "Missing linker: ${LD:-ld.lld}" >&2
    exit 1
}

test -f "$source_tree/Makefile"
test -f "$kernel_build/.config"
test -s "$kernel_build/Module.symvers"
test ! -e "$workspace"
test ! -e "$output"
test "${output##*/}" = qca_cld3_wlan.ko || {
    echo 'Output module must be named qca_cld3_wlan.ko.' >&2
    exit 2
}
case "$workspace:$output" in
    /*:/*) ;;
    *) echo 'Workspace and output paths must be absolute.' >&2; exit 2 ;;
esac

python3 "$repo/tools/check_waydroid_kernel.py" "$kernel_build/.config"
actual_release=$(make -s -C "$source_tree" O="$kernel_build" ARCH=arm64 kernelrelease)
test "$actual_release" = "$release" || {
    echo "Wrong kernel release: $actual_release" >&2
    exit 1
}

mkdir "$workspace"
clone_pinned() {
    name=$1
    commit=$2
    directory="$workspace/$name"
    git init -q "$directory"
    git -C "$directory" remote add origin "$base/$name.git"
    git -C "$directory" fetch -q --depth=2 origin "$commit"
    git -C "$directory" checkout -q --detach FETCH_HEAD
    test "$(git -C "$directory" rev-parse HEAD)" = "$commit"
}
clone_pinned qcacld-3.0 "$qcacld_commit"
clone_pinned qca-wifi-host-cmn "$host_cmn_commit"
clone_pinned fw-api "$fw_api_commit"

build=(make -C "$source_tree" O="$kernel_build" ARCH=arm64
       CC="${CC:-clang}" LD="${LD:-ld.lld}"
       CLANG_TRIPLE="${CLANG_TRIPLE:-aarch64-linux-gnu-}"
       CROSS_COMPILE="${CROSS_COMPILE:-aarch64-linux-android-}"
       CROSS_COMPILE_ARM32="${CROSS_COMPILE_ARM32:-arm-linux-androideabi-}"
       M="$workspace/qcacld-3.0"
       WLAN_ROOT="$workspace/qcacld-3.0"
       WLAN_COMMON_ROOT=../qca-wifi-host-cmn
       WLAN_FW_API="$workspace/fw-api"
       CONFIG_QCA_WIFI_ISOC=0 CONFIG_QCA_WIFI_2_0=1
       CONFIG_QCA_CLD_WLAN=m MODNAME=wlan
       KCFLAGS=-Wno-error=frame-larger-than=)

"${build[@]}" clean

# This Android 5.4 build reads both Module.symvers and a build-directory
# vmlinux. A stale vmlinux silently overrides otherwise-correct CRCs. Hide it
# for the external build so Module.symvers is the single ABI authority.
hidden_vmlinux=
restore_vmlinux() {
    if [ -n "$hidden_vmlinux" ] && [ -e "$hidden_vmlinux" ]; then
        mv "$hidden_vmlinux" "$kernel_build/vmlinux"
    fi
}
trap restore_vmlinux EXIT
if [ -e "$kernel_build/vmlinux" ]; then
    hidden_vmlinux="$kernel_build/.t630-wlan-vmlinux.$$"
    test ! -e "$hidden_vmlinux"
    mv "$kernel_build/vmlinux" "$hidden_vmlinux"
fi

jobs=$(nproc)
if [ "$jobs" -gt 4 ]; then jobs=4; fi
"${build[@]}" -j"$jobs" modules
restore_vmlinux
hidden_vmlinux=
trap - EXIT

built="$workspace/qcacld-3.0/wlan.ko"
test -s "$built"
test "$(modinfo -F vermagic "$built")" = \
    "$release SMP preempt mod_unload modversions aarch64"
test "$(modinfo -F depends "$built")" = \
    cnss2,cnss_prealloc,cnss_nl,cnss_utils

temporary="$output.unstripped.$$"
cp "$built" "$temporary"
cleanup() { rm -f "$temporary"; }
trap cleanup EXIT
if command -v llvm-strip >/dev/null; then
    llvm-strip --strip-debug -o "$output" "$temporary"
elif command -v "${CROSS_COMPILE:-aarch64-linux-android-}strip" >/dev/null; then
    "${CROSS_COMPILE:-aarch64-linux-android-}strip" --strip-debug \
        -o "$output" "$temporary"
else
    echo 'Missing llvm-strip or target strip tool.' >&2
    exit 1
fi

python3 "$repo/tools/audit_kernel_module_abi.py" \
    "$output" "$kernel_build/Module.symvers" \
    --expected-vermagic-prefix "$release"
sha256sum "$output"
printf 'qcacld-3.0=%s\nqca-wifi-host-cmn=%s\nfw-api=%s\n' \
    "$qcacld_commit" "$host_cmn_commit" "$fw_api_commit"
