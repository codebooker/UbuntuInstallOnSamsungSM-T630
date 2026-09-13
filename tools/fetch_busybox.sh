#!/bin/sh
# Download and unpack the exact Ubuntu arm64 BusyBox used by the diagnostic image.
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
stock="$root/stock"
name=busybox-static_1.36.1-6ubuntu3.1_arm64.deb
url="https://ports.ubuntu.com/ubuntu-ports/pool/main/b/busybox/$name"
expected=d96535e0402c011e0ee43449799df2f4504d44b842e4f2b3a6cbc845508eaafc

command -v curl >/dev/null
command -v ar >/dev/null
command -v zstd >/dev/null
command -v tar >/dev/null
mkdir -p "$stock"

if [ -f "$stock/$name" ] && [ -x "$stock/busybox-package/usr/bin/busybox" ]; then
    if command -v sha256sum >/dev/null; then
        actual=$(sha256sum "$stock/$name" | awk '{print $1}')
    else
        actual=$(shasum -a 256 "$stock/$name" | awk '{print $1}')
    fi
    test "$actual" = "$expected"
    echo "Pinned BusyBox is already ready."
    exit 0
fi

test ! -e "$stock/$name"
test ! -e "$stock/busybox-package"
temporary=$(mktemp -d "$stock/.busybox.XXXXXX")
trap 'rm -rf "$temporary"' EXIT HUP INT TERM

curl --fail --location --proto '=https' --tlsv1.2 "$url" --output "$temporary/$name"
if command -v sha256sum >/dev/null; then
    actual=$(sha256sum "$temporary/$name" | awk '{print $1}')
else
    actual=$(shasum -a 256 "$temporary/$name" | awk '{print $1}')
fi
test "$actual" = "$expected"

ar p "$temporary/$name" data.tar.zst >"$temporary/data.tar.zst"
zstd --decompress "$temporary/data.tar.zst" --output-dir-flat "$temporary"
mkdir "$temporary/package"
tar -xf "$temporary/data.tar" -C "$temporary/package"
test -x "$temporary/package/usr/bin/busybox"

mv "$temporary/$name" "$stock/$name"
mv "$temporary/package" "$stock/busybox-package"
echo "Pinned Ubuntu arm64 BusyBox is ready."
