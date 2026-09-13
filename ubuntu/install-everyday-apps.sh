#!/bin/sh
# Native Ubuntu packages; no kernel, display-manager or Snap transition.
set -u
export DEBIAN_FRONTEND=noninteractive
apt-get install -y --no-install-recommends \
  gnome-software packagekit nautilus gnome-text-editor evince eog file-roller \
  gnome-calculator gnome-clocks gnome-calendar gnome-system-monitor \
  gnome-disk-utility gnome-characters gnome-font-viewer gnome-terminal \
  libreoffice-writer libreoffice-calc libreoffice-impress libreoffice-gtk3 \
  hunspell-en-us fonts-crosextra-carlito fonts-crosextra-caladea \
  fonts-noto-color-emoji totem gstreamer1.0-libav gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad pipewire-pulse wireplumber evolution-data-server \
  gvfs-backends gvfs-fuse gpg curl ca-certificates xdg-user-dirs xdg-utils \
  > /run/t630-everyday-install.log 2>&1
result=$?
printf '%s\n' "$result" > /run/t630-everyday-install.exit
exit "$result"
