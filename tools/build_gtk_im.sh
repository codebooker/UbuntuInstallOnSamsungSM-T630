#!/bin/sh
set -eu
cd /usr/local/share/t630/gtk-im-build
protocol=/usr/share/wayland-protocols/unstable/text-input/text-input-unstable-v1.xml
/usr/bin/wayland-scanner client-header "$protocol" text-input-v1-client.h
/usr/bin/wayland-scanner private-code "$protocol" text-input-v1-protocol.c
/usr/bin/gcc -shared -fPIC -Wall -Wextra -Werror -O2 \
    -o im-t630-wayland.so t630_gtk_im.c text-input-v1-protocol.c \
    $(/usr/bin/pkg-config --cflags --libs gtk+-3.0 wayland-client)
/usr/bin/test ! -e /usr/local/lib/im-t630-wayland.so.next
/usr/bin/install -m 755 im-t630-wayland.so /usr/local/lib/im-t630-wayland.so.next
/usr/bin/mv /usr/local/lib/im-t630-wayland.so.next /usr/local/lib/im-t630-wayland.so
/usr/lib/aarch64-linux-gnu/libgtk-3-0t64/gtk-query-immodules-3.0 \
    /usr/local/lib/im-t630-wayland.so > /usr/local/share/t630/gtk-immodules.cache
