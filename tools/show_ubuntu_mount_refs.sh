#!/bin/sh
# Read-only outer-recovery diagnostic for an orderly unmount refusal.
# Read process references/maps, not descriptor contents or arbitrary sysfs.
set -eu
test -f /run/t630-selected-root
for proc in /proc/[0-9]*; do
    for reference in "$proc/root" "$proc/cwd" "$proc/exe" "$proc"/fd/*; do
        path=$(readlink "$reference" 2>/dev/null || true)
        case "$path" in
            /run/ubuntu|/run/ubuntu/*)
                printf 'pid=%s reference=%s path=%s\n' "${proc##*/}" "$reference" "$path" ;;
        esac
    done
    if [ -r "$proc/maps" ]; then
        awk -v pid="${proc##*/}" '$6 == "/run/ubuntu" || index($6,"/run/ubuntu/") == 1 {
            print "pid=" pid " mapped_file=" $6
        }' "$proc/maps" 2>/dev/null | sort -u || true
    fi
done
awk '$2 == "/run/ubuntu" || index($2,"/run/ubuntu/") == 1 {
    print "mount=" $2 " type=" $3
}' /proc/mounts
