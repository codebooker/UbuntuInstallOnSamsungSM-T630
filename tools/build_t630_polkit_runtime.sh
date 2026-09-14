#!/bin/sh
set -eu

# Build the process-scoped PolicyKit agent from Ubuntu's exact source package
# and package it without installing anything over the running tablet.
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build=${T630_POLKIT_BUILD_ROOT:-/tmp/t630-polkit-runtime-build}
out=${T630_POLKIT_OUTPUT:-$repo/output/t630-polkit-runtime_0.1.0_arm64.deb}
epoch=${SOURCE_DATE_EPOCH:-1700000000}
orig_url=https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/policykit-1-gnome/0.105-7ubuntu5/policykit-1-gnome_0.105.orig.tar.xz
debian_url=https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/policykit-1-gnome/0.105-7ubuntu5/policykit-1-gnome_0.105-7ubuntu5.debian.tar.xz
orig_sha=1784494963b8bf9a00eedc6cd3a2868fb123b8a5e516e66c5eda48df17ab9369
debian_sha=957ebefe04c896fc621ef8c578f6e77f04e72cd2092c6500b47e578ae91d1cf1

case "$build" in
  /|/tmp|/var/tmp|"$repo")
    echo "Refusing unsafe T630_POLKIT_BUILD_ROOT: $build" >&2
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
    build-essential ca-certificates curl dpkg-dev patch \
    pkg-config libgtk-3-dev libpolkit-agent-1-dev \
    libpolkit-gobject-1-dev >/dev/null
fi
for command in cc curl dpkg-deb patch pkg-config sha256sum tar; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Missing build command: $command" >&2
    exit 2
  }
done

rm -rf -- "$build"
mkdir -p "$build/downloads" "$build/src" "$(dirname -- "$out")"
curl -fL --retry 3 "$orig_url" -o "$build/downloads/orig.tar.xz"
curl -fL --retry 3 "$debian_url" -o "$build/downloads/debian.tar.xz"
echo "$orig_sha  $build/downloads/orig.tar.xz" | sha256sum -c -
echo "$debian_sha  $build/downloads/debian.tar.xz" | sha256sum -c -
tar -C "$build/src" -xf "$build/downloads/orig.tar.xz"
source=$build/src/polkit-gnome-0.105
tar -C "$source" -xf "$build/downloads/debian.tar.xz"
while IFS= read -r name; do
  patch -d "$source" -p1 < "$source/debian/patches/$name"
done < "$source/debian/patches/series"
patch -d "$source" -p1 < "$repo/patches/polkit-gnome-t630-process-agent.patch"

cd "$source"
printf '%s\n' \
  '#define GETTEXT_PACKAGE "polkit-gnome-1"' \
  '#define GNOMELOCALEDIR "/usr/share/locale"' \
  '#define HAVE_BIND_TEXTDOMAIN_CODESET 1' \
  '#define HAVE_CONFIG_H 1' \
  > config.h
cc -O2 -g0 -fPIE -ffile-prefix-map="$build"=/usr/src/t630-polkit-runtime \
  -I. -DHAVE_CONFIG_H \
  -DPOLKIT_AGENT_I_KNOW_API_IS_SUBJECT_TO_CHANGE \
  src/main.c src/polkitgnomelistener.c src/polkitgnomeauthenticator.c \
  src/polkitgnomeauthenticationdialog.c \
  $(pkg-config --cflags --libs gtk+-3.0 polkit-agent-1 polkit-gobject-1) \
  -Wl,--build-id=sha1 -pie -o "$build/t630-polkit-agent"

pkg=$build/package
mkdir -p "$pkg/DEBIAN" "$pkg/usr/local/libexec" \
  "$pkg/usr/share/dbus-1/system-services" \
  "$pkg/usr/share/doc/t630-polkit-runtime"
install -m 755 "$build/t630-polkit-agent" \
  "$pkg/usr/local/libexec/t630-polkit-agent"
install -m 644 "$repo/ubuntu/org.freedesktop.PolicyKit1.service" \
  "$pkg/usr/share/dbus-1/system-services/org.freedesktop.PolicyKit1.service"
install -m 644 "$source/COPYING" \
  "$pkg/usr/share/doc/t630-polkit-runtime/copyright"
printf '%s\n' \
  'Package: t630-polkit-runtime' \
  'Version: 0.1.0' \
  'Architecture: arm64' \
  'Maintainer: SM-T630 Ubuntu Port contributors' \
  'Depends: polkitd, libgtk-3-0t64, libpolkit-agent-1-0, libpolkit-gobject-1-0, util-linux' \
  'Section: admin' \
  'Priority: optional' \
  'Description: process-scoped PolicyKit agent for Samsung SM-T630 Ubuntu' \
  ' Preserves Ubuntu PolicyKit and PAM decisions while attaching authentication' \
  ' prompts to the installer-selected nested GNOME session.' \
  > "$pkg/DEBIAN/control"
printf '%s\n' \
  '#!/bin/sh' \
  'set -e' \
  'path=/usr/share/dbus-1/system-services/org.freedesktop.PolicyKit1.service' \
  'dpkg-divert --package t630-polkit-runtime --add --rename \' \
  '  --divert "$path.t630-stock" "$path"' \
  > "$pkg/DEBIAN/preinst"
printf '%s\n' \
  '#!/bin/sh' \
  'set -e' \
  'if [ "$1" = remove ] || [ "$1" = purge ]; then' \
  '  path=/usr/share/dbus-1/system-services/org.freedesktop.PolicyKit1.service' \
  '  dpkg-divert --package t630-polkit-runtime --remove --rename \' \
  '    --divert "$path.t630-stock" "$path"' \
  'fi' \
  > "$pkg/DEBIAN/postrm"
chmod 755 "$pkg/DEBIAN/preinst" "$pkg/DEBIAN/postrm"
(
  cd "$pkg"
  find usr -type f -print0 | sort -z | xargs -0 md5sum > DEBIAN/md5sums
)
find "$pkg" -exec touch -h -d "@$epoch" {} +
dpkg-deb --root-owner-group --build "$pkg" "$out" >/dev/null
sha256sum "$out"
