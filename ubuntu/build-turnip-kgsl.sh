#!/bin/sh
# Opt-in test ICD only. Does not replace Ubuntu Mesa or change desktop startup.
set -eu
test "$(uname -m)" = aarch64
source_dir=/usr/local/src/mesa-25.2.8
meson=/opt/t630/mesa-build-venv/bin/meson
test -x "$meson"
test -f "$source_dir/meson.build"
"$meson" setup "$source_dir/build-t630" "$source_dir" \
    --prefix=/opt/t630/mesa-25.2.8-kgsl --libdir=lib --buildtype=release \
    -Dgallium-drivers= -Dvulkan-drivers=freedreno -Dfreedreno-kmds=kgsl \
    -Dplatforms=x11,wayland -Dglx=disabled -Degl=disabled -Dgbm=disabled \
    -Dllvm=disabled -Dbuild-tests=false -Dvideo-codecs= \
    -Dvalgrind=disabled -Dlibunwind=disabled
nice -n 15 ninja -j 2 -C "$source_dir/build-t630"
"$meson" install -C "$source_dir/build-t630"
