#!/bin/sh
# Local aliases for Maliit's symbolic names; preserve all package-owned files.
# Includes Maliit 2.3.1's misspelled lowercase backspace icon name.
set -eu
dest=/usr/local/share/icons/hicolor
install -d "$dest/scalable/actions"
install -m 644 /usr/share/icons/hicolor/index.theme "$dest/index.theme"
for name in keyboard-caps-disabled keyboard-caps-enabled keyboard-caps-locked keyboard-enter keyboard-spacebar; do
    install -m 644 "/usr/share/icons/breeze/devices/22/$name.svg" "$dest/scalable/actions/$name-symbolic.svg"
done
for name in edit-clear-symbolic edit-clear-symoblic; do
    install -m 644 /usr/share/icons/breeze/actions/22/edit-clear.svg "$dest/scalable/actions/$name.svg"
done
gtk-update-icon-cache -f "$dest"
