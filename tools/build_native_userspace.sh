#!/bin/sh
# Reproducibly build the small redistributable ARM64 compatibility layer.
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
output=${1:?usage: build_native_userspace.sh NEW_OUTPUT_DIRECTORY}
test "$(uname -m)" = aarch64
test ! -e "$output"
mkdir -p "$output"

export LC_ALL=C
export TZ=UTC
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-1700000000}
common="-O2 -Wall -Wextra -Werror -ffile-prefix-map=$root=. -fdebug-prefix-map=$root=."
shared="$common -shared -fPIC -Wl,--build-id=none"

gcc $shared "$root/tools/t630_cogl_sync.c" -ldl -o "$output/t630-cogl-sync.so"
gcc $shared "$root/tools/t630_drm_compat.c" \
    $(pkg-config --cflags --libs libdrm) -ldl -o "$output/t630-drm-compat.so"
gcc $shared "$root/tools/t630_xput_image.c" \
    $(pkg-config --cflags --libs xcb) -ldl -o "$output/t630-xput-image.so"
gcc $common -fPIE -pie -Wl,--build-id=none "$root/tools/capture_scanout.c" \
    $(pkg-config --cflags --libs libdrm) -o "$output/t630-capture"
gcc $shared "$root/ubuntu/t630-weston-rotation.c" \
    $(pkg-config --cflags --libs libweston-13) -o "$output/t630-rotation.so"

protocol=/usr/share/wayland-protocols/unstable/text-input/text-input-unstable-v1.xml
wayland-scanner client-header "$protocol" "$output/text-input-v1-client.h"
wayland-scanner private-code "$protocol" "$output/text-input-v1-protocol.c"
gcc $shared -I"$output" "$root/tools/t630_gtk_im.c" \
    "$output/text-input-v1-protocol.c" \
    $(pkg-config --cflags --libs gtk+-3.0 wayland-client) \
    -o "$output/im-t630-wayland.so"
rm "$output/text-input-v1-client.h" "$output/text-input-v1-protocol.c"

for file in "$output"/*; do
    readelf -h "$file" | grep -q 'Class:.*ELF64'
    readelf -h "$file" | grep -q 'Machine:.*AArch64'
    chmod 0755 "$file"
done
sha256sum "$output"/*
