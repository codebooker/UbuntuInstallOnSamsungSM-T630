#!/bin/sh
set -eu

# Build the small QRTR protection-domain mapper used by the SM-T630 audio DSP.
# The source revision and archive bytes are pinned; nothing is installed live.

repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build=${T630_PD_MAPPER_BUILD_ROOT:-/tmp/t630-pd-mapper-build}
out=${T630_PD_MAPPER_OUTPUT:-$repo/output/t630-pd-mapper_0.1.0_arm64.deb}
epoch=${SOURCE_DATE_EPOCH:-1700000000}
revision=5ecd2fe926aca7abfe40724177f63b942cff3947
archive_sha256=08972b8813d08da5e20d27e57c5989398a0b750be92cd4398b5b21190c6ccdd0

case "$build" in
  /|/tmp|/var/tmp|"$repo")
    echo "Refusing unsafe T630_PD_MAPPER_BUILD_ROOT: $build" >&2
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
    build-essential ca-certificates curl dpkg-dev liblzma-dev libqrtr-glib-dev \
    >/dev/null
fi
for command in cc curl sha256sum tar dpkg-deb; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Missing build command: $command" >&2
    exit 2
  }
done

rm -rf -- "$build"
mkdir -p "$build" "$(dirname -- "$out")"
curl -fL --retry 3 \
  "https://github.com/linux-msm/pd-mapper/archive/$revision.tar.gz" \
  -o "$build/source.tar.gz"
echo "$archive_sha256  $build/source.tar.gz" | sha256sum -c -
tar -C "$build" -xf "$build/source.tar.gz"
source="$build/pd-mapper-$revision"

cc -Wall -Wextra -O2 -fPIE -ffile-prefix-map="$build"=/usr/src/t630-pd-mapper \
  "$source/pd-mapper.c" "$source/assoc.c" "$source/json.c" \
  "$source/servreg_loc.c" "$source/lzma_decomp.c" \
  -Wl,--build-id=sha1 -pie -lqrtr -llzma -o "$build/t630-pd-mapper"

pkg="$build/package"
mkdir -p "$pkg/DEBIAN" "$pkg/usr/local/sbin" \
  "$pkg/usr/share/doc/t630-pd-mapper"
install -m 755 "$build/t630-pd-mapper" "$pkg/usr/local/sbin/t630-pd-mapper"
install -m 644 "$source/LICENSE" "$pkg/usr/share/doc/t630-pd-mapper/copyright"
printf '%s\n' \
  'Package: t630-pd-mapper' \
  'Version: 0.1.0' \
  'Architecture: arm64' \
  'Maintainer: SM-T630 Ubuntu Port contributors' \
  'Depends: libc6, liblzma5, libqrtr-glib0' \
  'Section: admin' \
  'Priority: optional' \
  'Description: Qualcomm protection-domain mapper for Samsung SM-T630' \
  ' Source-built QRTR service used to start the tablet audio DSP.' \
  > "$pkg/DEBIAN/control"
(
  cd "$pkg"
  find usr -type f -print0 | sort -z | xargs -0 md5sum > DEBIAN/md5sums
)
find "$pkg" -exec touch -h -d "@$epoch" {} +
dpkg-deb --root-owner-group --build "$pkg" "$out" >/dev/null
sha256sum "$out"
