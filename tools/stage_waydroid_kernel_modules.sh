#!/bin/bash
# Replace the SM-T630 vendor-module payload with modules from the matching build.
set -euo pipefail

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    echo "usage: $0 KERNEL_BUILD CURRENT_MODULE_DIRECTORY [--apply]" >&2
    exit 2
fi

build=$1
current=$2
mode=${3:-check}
release=5.4.274-qgki-31225846-abT630XXSBDZE3
test "$current" = /opt/t630/vendor/lib/modules
parent=$(dirname "$current")
backup="$parent/modules-v8"
staging="$parent/.modules-v9.staging"

test -d "$build"
test -d "$current"
test ! -L "$current"
test ! -e "$backup"
test ! -e "$staging"
test "$(uname -r)" = "$release"
command -v modinfo >/dev/null

expected=$(find "$current" -maxdepth 1 -type f -name '*.ko' | wc -l)
test "$expected" -gt 50

mkdir "$staging"
cleanup() {
    find "$staging" -maxdepth 1 -type f -name '*.ko' -delete
    rmdir "$staging"
}
trap cleanup EXIT

while IFS= read -r old; do
    name=$(basename "$old")
    mapfile -t matches < <(find "$build" -type f -name "$name" -print)
    if [ "${#matches[@]}" -ne 1 ]; then
        echo "$name: expected one build result, found ${#matches[@]}" >&2
        exit 1
    fi
    vermagic=$(modinfo -F vermagic "${matches[0]}")
    case "$vermagic" in
        "$release "*) ;;
        *) echo "$name: wrong vermagic: $vermagic" >&2; exit 1 ;;
    esac
    install -m 0644 "${matches[0]}" "$staging/$name"
done < <(find "$current" -maxdepth 1 -type f -name '*.ko' -print | sort)

actual=$(find "$staging" -maxdepth 1 -type f -name '*.ko' | wc -l)
test "$actual" = "$expected"
echo "Validated $actual modules for $release."

if [ "$mode" != --apply ]; then
    echo 'Check only; no persistent files changed.'
    exit 0
fi

sync
mv "$current" "$backup"
if ! mv "$staging" "$current"; then
    mv "$backup" "$current"
    exit 1
fi
trap - EXIT
sync
echo "Installed matching modules; the previous payload is in $backup."
