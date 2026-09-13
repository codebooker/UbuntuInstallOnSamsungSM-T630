#!/bin/sh
# Build the process-scoped SM-T630 V4L2 compatibility adapter.
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
output_dir=${1:-"$repo_dir/build/video"}
cc=${CC:-cc}

command -v "$cc" >/dev/null
test -r /usr/include/linux/videodev2.h
mkdir -p "$output_dir"
temporary=$(mktemp "$output_dir/.t630-v4l2-compat.XXXXXX")
trap 'rm -f -- "$temporary"' EXIT HUP INT TERM

"$cc" -shared -fPIC -O2 -Wall -Wextra -Werror \
    -o "$temporary" "$repo_dir/tools/t630_v4l2_probe.c" -ldl -pthread
chmod 0755 "$temporary"
mv -f -- "$temporary" "$output_dir/t630-v4l2-compat.so"
trap - EXIT HUP INT TERM
sha256sum "$output_dir/t630-v4l2-compat.so"
