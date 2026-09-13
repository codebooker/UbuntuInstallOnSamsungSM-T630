#!/bin/sh
# Build the redistributable pieces of the camera compatibility stack.
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
output_dir=${1:-"$repo_dir/build/camera"}
: "${ANDROID_NDK_ROOT:?Set ANDROID_NDK_ROOT to Android NDK r27 or newer}"

case $(uname -s) in
    Darwin) host_tag=darwin-x86_64 ;;
    Linux) host_tag=linux-x86_64 ;;
    *) echo "Unsupported build host: $(uname -s)" >&2; exit 1 ;;
esac

toolchain="$ANDROID_NDK_ROOT/toolchains/llvm/prebuilt/$host_tag/bin"
cc="$toolchain/aarch64-linux-android30-clang"
cxx="$toolchain/aarch64-linux-android30-clang++"
test -x "$cc"
test -x "$cxx"
mkdir -p "$output_dir"

"$cc" -shared -fPIC -Wall -Wextra -Werror -nostdlib \
    "$repo_dir/ubuntu/t630-android-property-seed.c" \
    -o "$output_dir/t630-android-property-seed.so"
"$cxx" -std=c++17 -Wall -Wextra -Werror -fPIE -pie \
    "$repo_dir/camera/t630-sensorservice-hidl.cpp" -ldl \
    -o "$output_dir/t630-sensorservice-hidl"
"$cc" -std=c11 -Wall -Wextra -Werror -O2 \
    "$repo_dir/camera/t630-camera-capture.c" \
    -lcamera2ndk -lmediandk -landroid -llog -ldl \
    -o "$output_dir/t630-camera-capture"

echo "Built camera compatibility components in $output_dir"
