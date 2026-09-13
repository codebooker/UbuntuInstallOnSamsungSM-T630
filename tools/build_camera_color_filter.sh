#!/bin/sh
# Build the small native Ubuntu-side rear-camera color correction filter.
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
output=${1:-"$repo_dir/build/camera/t630-yuv-tune"}
mkdir -p "$(dirname -- "$output")"
${CC:-cc} -std=c11 -O3 -Wall -Wextra -Werror \
    "$repo_dir/camera/t630-yuv-tune.c" -o "$output"
echo "Built camera color filter at $output"
