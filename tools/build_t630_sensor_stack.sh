#!/bin/sh
set -eu

# Build the Qualcomm SSC userspace bridge natively on Ubuntu ARM64. Source
# archives and the reference patch set are pinned and hash-checked before use.
# Build products live below T630_SENSOR_BUILD_ROOT and T630_SENSOR_OUTPUT; the
# script never installs its results into the running system.

repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build=${T630_SENSOR_BUILD_ROOT:-/tmp/t630-sensor-stack-build}
out=${T630_SENSOR_OUTPUT:-$repo/output/sensors}
epoch=${SOURCE_DATE_EPOCH:-1700000000}

case "$build" in
  /|/tmp|/var/tmp|"$repo")
    echo "Refusing unsafe T630_SENSOR_BUILD_ROOT: $build" >&2
    exit 2
    ;;
esac
case "$epoch" in
  ''|*[!0-9]*)
    echo "SOURCE_DATE_EPOCH must be a non-negative integer" >&2
    exit 2
    ;;
esac
if [ "$(uname -m)" != aarch64 ]; then
  echo "This builder must run on Ubuntu ARM64" >&2
  exit 2
fi

export LC_ALL=C
export TZ=UTC
export SOURCE_DATE_EPOCH=$epoch
export DEBIAN_FRONTEND=noninteractive

if [ "${T630_SKIP_BUILD_DEPS:-0}" != 1 ]; then
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends \
    build-essential ninja-build pkg-config ca-certificates curl git patch \
    python3-dev python3-gi python3-protobuf python3-pip python3-venv \
    libglib2.0-dev libgudev-1.0-dev libudev-dev systemd-dev libqmi-glib-dev \
    libmbim-glib-dev libqrtr-glib-dev libprotobuf-c-dev \
    protobuf-c-compiler protobuf-compiler libpolkit-gobject-1-dev \
    dpkg-dev >/dev/null
fi

for command in python3 ninja pkg-config curl git sha256sum patch tar dpkg-deb; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Missing build command: $command" >&2
    exit 2
  fi
done

fetch_verified() {
  url=$1 digest=$2 destination=$3
  curl -fL --retry 3 --output "$destination" "$url"
  actual=$(sha256sum "$destination" | cut -d ' ' -f 1)
  if [ "$actual" != "$digest" ]; then
    echo "Source archive checksum mismatch: $destination" >&2
    exit 1
  fi
}

rm -rf -- "$build"
mkdir -p "$build/downloads" "$build/src" "$build/stage-libssc" \
  "$build/stage-hexagonrpcd" "$build/stage-iio-sensor-proxy" "$out"
rm -f -- "$out"/libssc_0.4.4-t6303_arm64.deb \
  "$out"/hexagonrpcd_0.4.0-t6303_arm64.deb \
  "$out"/iio-sensor-proxy_3.9-t6303_arm64.deb

if [ -n "${T630_MESON:-}" ]; then
  meson=$T630_MESON
else
  python3 -m venv "$build/tooling"
  printf '%s\n' \
    'meson==1.7.2 --hash=sha256:82c6818dc81743c96de3a458f06175776ebfde4081195ea31ea6971838f25e38' \
    > "$build/meson-requirements.txt"
  "$build/tooling/bin/pip" install --disable-pip-version-check --no-deps \
    --require-hashes -r "$build/meson-requirements.txt" >/dev/null
  meson="$build/tooling/bin/meson"
fi
if ! command -v "$meson" >/dev/null 2>&1; then
  echo "Missing Meson command: $meson" >&2
  exit 2
fi
meson_version=$("$meson" --version)
meson_major=${meson_version%%.*}
meson_remainder=${meson_version#*.}
meson_minor=${meson_remainder%%.*}
if [ "$meson_major" -lt 1 ] || \
   { [ "$meson_major" -eq 1 ] && [ "$meson_minor" -lt 4 ]; }; then
  echo "Meson 1.4 or newer is required; found $meson_version" >&2
  exit 2
fi

fetch_verified \
  https://codeberg.org/DylanVanAssche/libssc/archive/v0.4.4.tar.gz \
  716d6bd6b34d2d753060c6b54c9a87e34fae75b724c763bf9ef487efa3621587 \
  "$build/downloads/libssc.tar.gz"
fetch_verified \
  https://github.com/linux-msm/hexagonrpc/archive/refs/tags/v0.4.0.tar.gz \
  fe742549a2672902d59a90dafd741a9a0acbeca059e07ff5130e2b525a66574f \
  "$build/downloads/hexagonrpc.tar.gz"
fetch_verified \
  https://gitlab.freedesktop.org/hadess/iio-sensor-proxy/-/archive/3.9/iio-sensor-proxy-3.9.tar.gz \
  af5edd307dcfa52dc3a242d13b7cc756e90a71640caf332efbad960e21649ae4 \
  "$build/downloads/iio-sensor-proxy.tar.gz"
fetch_verified \
  https://github.com/agcarbajo/ubuntu-galaxy-tab-s9-ultra/archive/bb55ceb87b61db7629c0820101ce7884ff8d987b.tar.gz \
  c9adf372693d7c0c1345d50bfedb6a48fa87d32c4cdadc734a575ad9c80299c9 \
  "$build/downloads/reference-s9-ultra.tar.gz"

tar -C "$build/src" -xf "$build/downloads/libssc.tar.gz"
tar -C "$build/src" -xf "$build/downloads/hexagonrpc.tar.gz"
tar -C "$build/src" -xf "$build/downloads/iio-sensor-proxy.tar.gz"
tar -C "$build/src" -xf "$build/downloads/reference-s9-ultra.tar.gz"

reference="$build/src/ubuntu-galaxy-tab-s9-ultra-bb55ceb87b61db7629c0820101ce7884ff8d987b/packaging/sensors"

cd "$build/src/libssc"
patch -p1 < "$reference/fix-ssc-sync-wait-busy-loop.patch"
patch -p1 < "$repo/patches/use-t630-auto-brightness.patch"
"$meson" setup output --prefix=/usr --libdir=lib/aarch64-linux-gnu \
  --buildtype=release
"$meson" compile -C output
DESTDIR="$build/stage-libssc" "$meson" install --no-rebuild -C output

cd "$build/src/hexagonrpc-0.4.0"
for name in support-samsung-sensor-registry-writes.patch \
            fix-fwrite-arity.patch add-apps-std-rename.patch \
            raise-listener-inbuf-limit.patch; do
  patch -p1 < "$reference/$name"
done
git apply --recount "$repo/patches/hexagonrpcd-downstream-fastrpc.patch"
"$meson" setup output --prefix=/usr --buildtype=release
"$meson" compile -C output
DESTDIR="$build/stage-hexagonrpcd" "$meson" install --no-rebuild -C output

# Point only libssc at its staged prefix. Its transitive dependencies still use
# the host's normal pkg-config metadata, so no blanket sysroot is applied.
mkdir -p "$build/pkgconfig"
sed "s|^prefix=/usr$|prefix=$build/stage-libssc/usr|" \
  "$build/stage-libssc/usr/lib/aarch64-linux-gnu/pkgconfig/libssc.pc" \
  > "$build/pkgconfig/libssc.pc"
export PKG_CONFIG_PATH="$build/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
export LD_LIBRARY_PATH="$build/stage-libssc/usr/lib/aarch64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

cd "$build/src/iio-sensor-proxy-3.9"
patch -p1 < "$reference/fix-early-ssc-claim-race.patch"
patch -p1 < "$repo/patches/iio-sensor-proxy-downstream-fastrpc-subsystem.patch"
"$meson" setup output --prefix=/usr --buildtype=release -Dssc-support=enabled \
  -Dsystemdsystemunitdir=/usr/lib/systemd/system
"$meson" compile -C output
DESTDIR="$build/stage-iio-sensor-proxy" "$meson" install --no-rebuild -C output

find "$build" -type d -name __pycache__ -prune -exec rm -rf -- {} +

package() {
  stage=$1 name=$2 version=$3 depends=$4 description=$5
  pkg="$build/pkg-$name"
  rm -rf -- "$pkg"
  mkdir -p "$pkg/DEBIAN"
  cp -a "$stage/." "$pkg/"
  printf '%s\n' \
    "Package: $name" \
    "Version: $version" \
    'Section: misc' \
    'Priority: optional' \
    'Architecture: arm64' \
    'Maintainer: SM-T630 Ubuntu Port contributors' \
    "Depends: $depends" \
    "Description: $description" > "$pkg/DEBIAN/control"
  case "$name" in
    libssc|hexagonrpcd)
      printf '%s\n' '#!/bin/sh' 'set -e' 'ldconfig' > "$pkg/DEBIAN/postinst"
      printf '%s\n' '#!/bin/sh' 'set -e' 'ldconfig' > "$pkg/DEBIAN/postrm"
      chmod 755 "$pkg/DEBIAN/postinst" "$pkg/DEBIAN/postrm"
      ;;
  esac
  (
    cd "$pkg"
    find . -type f ! -path './DEBIAN/*' -print0 | sort -z | \
      xargs -0 md5sum > DEBIAN/md5sums
  )
  find "$pkg" -exec touch -h -d "@$epoch" {} +
  dpkg-deb --root-owner-group --build "$pkg" \
    "$out/${name}_${version}_arm64.deb" >/dev/null
}

package "$build/stage-libssc" libssc 0.4.4-t6303 \
  'libc6, libglib2.0-0t64, libqmi-glib5, libqrtr-glib0, libprotobuf-c1' \
  'Qualcomm Sensor Core client library for the Samsung SM-T630'
package "$build/stage-hexagonrpcd" hexagonrpcd 0.4.0-t6303 \
  'libc6' 'Qualcomm FastRPC filesystem daemon for the Samsung SM-T630'
package "$build/stage-iio-sensor-proxy" iio-sensor-proxy 3.9-t6303 \
  'libc6, dbus, libglib2.0-0t64, libgudev-1.0-0, libssc (>= 0.4.4-t6303)' \
  'IIO sensor proxy with Qualcomm SSC support for the Samsung SM-T630'

sha256sum "$out"/*.deb
