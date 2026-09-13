#!/bin/sh
set -eu

# Build the Qualcomm SSC userspace bridge as native arm64 Ubuntu packages in
# an ephemeral container. Nothing is compiled on the tablet.

work=/work
patches="$work/reference-s9-ultra/packaging/sensors"
out="$work/output/sensors"
build=/build

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
  build-essential ninja-build pkg-config git ca-certificates curl patch \
  python3-pip python3-setuptools python3-dev python3-gi python3-protobuf \
  libglib2.0-dev libgudev-1.0-dev libudev-dev systemd-dev libqmi-glib-dev \
  libmbim-glib-dev libqrtr-glib-dev libprotobuf-c-dev \
  protobuf-c-compiler protobuf-compiler libpolkit-gobject-1-dev \
  dpkg-dev >/dev/null
pip3 install --break-system-packages --quiet 'meson>=1.4,<2'

rm -rf "$build"
mkdir -p "$build" "$out"
rm -f "$out"/*.deb

git clone --quiet --depth 1 --branch v0.4.4 \
  https://codeberg.org/DylanVanAssche/libssc.git "$build/libssc"
cd "$build/libssc"
patch -p1 < "$patches/fix-ssc-sync-wait-busy-loop.patch"
meson setup output --prefix=/usr --libdir=lib/aarch64-linux-gnu
meson compile -C output
DESTDIR="$build/stage-libssc" meson install --no-rebuild -C output
cp -a "$build/stage-libssc/." /
ldconfig

git clone --quiet --depth 1 --branch v0.4.0 \
  https://github.com/linux-msm/hexagonrpc.git "$build/hexagonrpc"
cd "$build/hexagonrpc"
for p in support-samsung-sensor-registry-writes.patch \
         fix-fwrite-arity.patch add-apps-std-rename.patch \
         raise-listener-inbuf-limit.patch; do
  patch -p1 < "$patches/$p"
done
git apply --recount "$work/patches/hexagonrpcd-downstream-fastrpc.patch"
meson setup output --prefix=/usr
meson compile -C output
DESTDIR="$build/stage-hexagonrpcd" meson install --no-rebuild -C output

curl -fsSL -o "$build/iio-sensor-proxy.tar.gz" \
  https://gitlab.freedesktop.org/hadess/iio-sensor-proxy/-/archive/3.9/iio-sensor-proxy-3.9.tar.gz
tar -C "$build" -xf "$build/iio-sensor-proxy.tar.gz"
cd "$build/iio-sensor-proxy-3.9"
patch -p1 < "$patches/fix-early-ssc-claim-race.patch"
patch -p1 < "$work/patches/iio-sensor-proxy-downstream-fastrpc-subsystem.patch"
meson setup output --prefix=/usr -Dssc-support=enabled \
  -Dsystemdsystemunitdir=/usr/lib/systemd/system
meson compile -C output
DESTDIR="$build/stage-iio-sensor-proxy" meson install --no-rebuild -C output

package() {
  stage=$1 name=$2 version=$3 depends=$4 description=$5
  pkg="$build/pkg-$name"
  rm -rf "$pkg"
  mkdir -p "$pkg/DEBIAN"
  cp -a "$stage/." "$pkg/"
  printf '%s\n' \
    "Package: $name" \
    "Version: $version" \
    'Section: misc' \
    'Priority: optional' \
    'Architecture: arm64' \
    'Maintainer: SM-T630 Ubuntu port <noreply@example.invalid>' \
    "Depends: $depends" \
    "Description: $description" > "$pkg/DEBIAN/control"
  find "$pkg" -exec touch -h -d '@0' {} +
  dpkg-deb --root-owner-group --build "$pkg" "$out/${name}_${version}_arm64.deb" >/dev/null
}

package "$build/stage-libssc" libssc 0.4.4-t6302 \
  'libc6, libglib2.0-0t64, libqmi-glib5, libqrtr-glib0, libprotobuf-c1' \
  'Qualcomm Sensor Core client library for the SM-T630'
package "$build/stage-hexagonrpcd" hexagonrpcd 0.4.0-t6302 \
  'libc6' 'Qualcomm FastRPC Hexagon filesystem daemon for the SM-T630'
package "$build/stage-iio-sensor-proxy" iio-sensor-proxy 3.9-t6302 \
  'libc6, dbus, libglib2.0-0t64, libgudev-1.0-0, libssc (>= 0.4.4-t6302)' \
  'IIO sensor proxy with Qualcomm SSC support for the SM-T630'

sha256sum "$out"/*.deb
