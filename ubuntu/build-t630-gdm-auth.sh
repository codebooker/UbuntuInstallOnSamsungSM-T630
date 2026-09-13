#!/bin/sh
# Build the matching Ubuntu-patched GDM source in an isolated prefix.
set -eu
cd /usr/local/src/gdm3-46.2
export PKG_CONFIG_PATH=/opt/t630/elogind-255.27/lib/pkgconfig
export LD_LIBRARY_PATH=/opt/t630/elogind-255.27/lib
/opt/t630/mesa-build-venv/bin/meson setup build-auth \
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
ninja -C build-auth -j2
