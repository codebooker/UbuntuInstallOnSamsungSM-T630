#!/bin/sh
set -eu

# Build the private-prefix elogind/GDM authentication stack from pinned public
# sources and package it without installing over the running tablet.
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build=${T630_LOGIN_BUILD_ROOT:-/tmp/t630-login-runtime-build}
out=${T630_LOGIN_OUTPUT:-$repo/output/t630-login-runtime_0.1.0_arm64.deb}
epoch=${SOURCE_DATE_EPOCH:-1700000000}

elogind_url=https://github.com/elogind/elogind/archive/refs/tags/v255.27.tar.gz
elogind_sha=1ef0dffaad77e8d8ded047895fc5e60b7ab5cf7137d356cebd821cc5a0d566c9
gdm_base=https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/gdm3/46.2-1ubuntu1~24.04.9
gdm_orig=gdm3_46.2.orig.tar.xz
gdm_debian=gdm3_46.2-1ubuntu1~24.04.9.debian.tar.xz
gdm_orig_sha=4ee345422a16537150cd842450cda52b2ca86984bc51ee20cdc025dcf4bd268b
gdm_debian_sha=0a4bfa56afc053f257f56a7918c679fe3edce1048817811de359f80ef0fff653

case "$build" in
  /|/tmp|/var/tmp|"$repo")
    echo "Refusing unsafe T630_LOGIN_BUILD_ROOT: $build" >&2
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

export LC_ALL=C TZ=UTC SOURCE_DATE_EPOCH=$epoch DEBIAN_FRONTEND=noninteractive
if [ "${T630_SKIP_BUILD_DEPS:-0}" != 1 ]; then
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends \
    build-essential ca-certificates curl gettext gperf itstool meson ninja-build \
    patch pkg-config python3-jinja2 \
    libaccountsservice-dev libacl1-dev libaudit-dev libcanberra-gtk3-dev \
    libcap-dev libdbus-1-dev libglib2.0-dev libgtk-3-dev libgudev-1.0-dev \
    libjson-glib-dev libkeyutils-dev libmount-dev libpam0g-dev \
    libpolkit-gobject-1-dev libselinux1-dev libsystemd-dev libudev-dev \
    libx11-dev libxau-dev libxcb1-dev gobject-introspection \
    libgirepository1.0-dev >/dev/null
fi
for command in cc curl dpkg-deb meson ninja patch pkg-config sha256sum tar; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Missing build command: $command" >&2
    exit 2
  }
done

rm -rf -- "$build"
mkdir -p "$build/downloads" "$build/src" "$build/stage" "$(dirname -- "$out")"
curl -fL --retry 3 "$elogind_url" -o "$build/downloads/elogind.tar.gz"
curl -fL --retry 3 "$gdm_base/$gdm_orig" -o "$build/downloads/$gdm_orig"
curl -fL --retry 3 "$gdm_base/$gdm_debian" -o "$build/downloads/$gdm_debian"
echo "$elogind_sha  $build/downloads/elogind.tar.gz" | sha256sum -c -
echo "$gdm_orig_sha  $build/downloads/$gdm_orig" | sha256sum -c -
echo "$gdm_debian_sha  $build/downloads/$gdm_debian" | sha256sum -c -

tar -C "$build/src" -xf "$build/downloads/elogind.tar.gz"
elogind=$build/src/elogind-255.27
meson setup "$elogind/build-t630" "$elogind" \
  --prefix=/opt/t630/elogind-255.27 --libdir=lib \
  --sysconfdir=/opt/t630/elogind-255.27/etc --localstatedir=/var \
  --buildtype=release -Dmode=release -Dtests=false -Dman=disabled \
  -Dhtml=disabled -Dtranslations=false -Dpam=enabled \
  -Dpamlibdir=/opt/t630/elogind-255.27/lib/security -Dpamconfdir=no \
  -Ddbuspolicydir=/opt/t630/elogind-255.27/share/dbus-1/system.d \
  -Ddbussystemservicedir=/opt/t630/elogind-255.27/share/dbus-1/system-services \
  -Dudevrulesdir=/opt/t630/elogind-255.27/lib/udev/rules.d \
  -Ddefault-hierarchy=legacy -Dcgroup-controller=elogind \
  -Ddefault-kill-user-processes=false -Dpolkit=enabled -Dgroup-render-mode=0660
ninja -C "$elogind/build-t630" -j2
DESTDIR="$build/stage" meson install -C "$elogind/build-t630" --no-rebuild
install -m 644 "$repo/ubuntu/t630-elogind-lab.conf" \
  "$build/stage/opt/t630/elogind-255.27/etc/elogind/logind.conf"
install -m 644 "$repo/ubuntu/t630-elogind-sleep.conf" \
  "$build/stage/opt/t630/elogind-255.27/etc/elogind/sleep.conf"

tar -C "$build/src" -xf "$build/downloads/$gdm_orig"
gdm=$build/src/gdm-46.2
tar -C "$gdm" -xf "$build/downloads/$gdm_debian"
while IFS= read -r name; do
  case "$name" in ''|'#'*) continue ;; esac
  patch -d "$gdm" -p1 < "$gdm/debian/patches/$name"
done < "$gdm/debian/patches/series"
patch -d "$gdm" -p1 < "$repo/ubuntu/gdm-auth-only-greeter.patch"

export PKG_CONFIG_PATH="$build/stage/opt/t630/elogind-255.27/lib/pkgconfig"
export LD_LIBRARY_PATH="$build/stage/opt/t630/elogind-255.27/lib"
meson setup "$gdm/build-t630" "$gdm" \
  --prefix=/opt/t630/gdm-46.2-auth --libdir=lib --sysconfdir=/etc/t630 \
  --localstatedir=/var --buildtype=release \
  -Dlogind-provider=elogind -Dxdmcp=disabled -Dplymouth=disabled \
  -Dsystemd-journal=false -Ddefault-pam-config=none -Ddistro=debian \
  -Dsysconfsubdir=gdm-auth -Dcustom-conf=/etc/t630/gdm-auth/custom.conf \
  -Dworking-dir=/var/lib/gdm3 -Dxauth-dir=/run/t630-gdm \
  -Drun-dir=/run/t630-gdm -Dpid-file=/run/t630-gdm.pid \
  -Dlog-dir=/var/log/t630-gdm -Druntime-conf=/run/t630-gdm/custom.conf \
  -Dsystemdsystemunitdir=no -Dsystemduserunitdir=no \
  -Dc_link_args=-Wl,-rpath,/opt/t630/elogind-255.27/lib
ninja -C "$gdm/build-t630" -j2
DESTDIR="$build/stage" meson install -C "$gdm/build-t630" --no-rebuild

pkg=$build/package
mkdir -p "$pkg/DEBIAN" "$pkg/etc/pam.d" "$pkg/etc/t630/gdm-auth" \
  "$pkg/usr/share/doc/t630-login-runtime"
cp -a "$build/stage/opt" "$pkg/"
install -m 644 "$repo/ubuntu/t630-gdm-auth-only.conf" \
  "$pkg/etc/t630/gdm-auth/custom.conf"
install -m 644 "$repo/ubuntu/t630-common-session" "$pkg/etc/pam.d/common-session"
: > "$pkg/etc/t630/login.enabled"
: > "$pkg/etc/t630/lock-on-start"
install -m 644 "$elogind/LICENSE.GPL2" \
  "$pkg/usr/share/doc/t630-login-runtime/elogind-LICENSE.GPL2"
install -m 644 "$elogind/LICENSE.LGPL2.1" \
  "$pkg/usr/share/doc/t630-login-runtime/elogind-LICENSE.LGPL2.1"
install -m 644 "$gdm/COPYING" \
  "$pkg/usr/share/doc/t630-login-runtime/gdm-COPYING"
printf '%s\n' \
  'Package: t630-login-runtime' \
  'Version: 0.1.0' \
  'Architecture: arm64' \
  'Maintainer: SM-T630 Ubuntu Port contributors' \
  'Depends: t630-desktop-runtime (= 0.1.1), gdm3 (= 46.2-1ubuntu1~24.04.9), libpam-systemd, libpam0g, libglib2.0-0t64, libgudev-1.0-0, libgtk-3-0t64, libjson-glib-1.0-0, libcanberra-gtk3-0t64, libaccountsservice0, libaudit1, libcap2, libdbus-1-3, libmount1, libpolkit-gobject-1-0, libselinux1, libudev1, libx11-6, libxau6, libxcb1' \
  'Section: admin' \
  'Priority: optional' \
  'Description: isolated GDM authentication runtime for Samsung SM-T630 Ubuntu' \
  ' Provides standard password lock and login accounting for the nested GNOME' \
  ' desktop without starting a second compositor or enabling remote GDM login.' \
  > "$pkg/DEBIAN/control"
printf '%s\n' \
  '#!/bin/sh' \
  'set -e' \
  'path=/etc/pam.d/common-session' \
  'dpkg-divert --package t630-login-runtime --add --rename \' \
  '  --divert "$path.t630-stock" "$path"' \
  > "$pkg/DEBIAN/preinst"
printf '%s\n' \
  '#!/bin/sh' \
  'set -e' \
  'if [ "$1" = remove ] || [ "$1" = purge ]; then' \
  '  path=/etc/pam.d/common-session' \
  '  dpkg-divert --package t630-login-runtime --remove --rename \' \
  '    --divert "$path.t630-stock" "$path"' \
  'fi' \
  > "$pkg/DEBIAN/postrm"
chmod 755 "$pkg/DEBIAN/preinst" "$pkg/DEBIAN/postrm"
(
  cd "$pkg"
  find etc opt usr -type f -print0 | sort -z | xargs -0 md5sum > DEBIAN/md5sums
)
find "$pkg" -exec touch -h -d "@$epoch" {} +
dpkg-deb --root-owner-group -Zxz --build "$pkg" "$out" >/dev/null
sha256sum "$out"
