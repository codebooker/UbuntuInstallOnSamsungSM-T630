#!/bin/sh
set -eu
cd /usr/local/share/t630/pd-mapper-source
output=$(mktemp /usr/local/sbin/t630-pd-mapper.XXXXXX)
trap 'rm -f "$output"' EXIT
gcc -Wall -O2 pd-mapper.c assoc.c json.c servreg_loc.c lzma_decomp.c \
    -lqrtr -llzma -o "$output"
chmod 755 "$output"
chown root:root "$output"
mv "$output" /usr/local/sbin/t630-pd-mapper
