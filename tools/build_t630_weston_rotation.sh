#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
out="$root/output/t630-weston-rotation.so"
mkdir -p "$root/output"

${CC:-cc} -std=c11 -Wall -Wextra -Werror -fPIC -shared \
    $(pkg-config --cflags libweston-13) \
    "$root/ubuntu/t630-weston-rotation.c" \
    -o "$out" \
    $(pkg-config --libs libweston-13)
sha256sum "$out"
