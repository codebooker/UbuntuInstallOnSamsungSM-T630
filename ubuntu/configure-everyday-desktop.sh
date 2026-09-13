#!/bin/sh
# Run as tablet inside its GNOME environment, not the root setup desktop.
set -eu
test "$(id -u)" = 1000
test "$XDG_CONFIG_HOME" = /home/tablet/.config/t630-gnome-preview
cd "$HOME"
xdg-user-dirs-update
xdg-settings set default-web-browser firefox.desktop
xdg-mime default org.gnome.Nautilus.desktop inode/directory
xdg-mime default org.gnome.TextEditor.desktop text/plain
xdg-mime default org.gnome.Evince.desktop application/pdf
xdg-mime default org.gnome.eog.desktop image/png image/jpeg
xdg-mime default org.gnome.FileRoller.desktop application/zip
xdg-mime default libreoffice-writer.desktop application/vnd.oasis.opendocument.text application/vnd.openxmlformats-officedocument.wordprocessingml.document
xdg-mime default libreoffice-calc.desktop application/vnd.oasis.opendocument.spreadsheet application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
xdg-mime default libreoffice-impress.desktop application/vnd.oasis.opendocument.presentation application/vnd.openxmlformats-officedocument.presentationml.presentation
# The already-running GNOME inherited /root as its working directory. Office's
# startup script requires an accessible cwd. New sessions also cd HOME early.
for desktop in /usr/share/applications/libreoffice-*.desktop; do
    desktop-file-install --dir="$XDG_DATA_HOME/applications" \
        --set-key=Path --set-value="$HOME" "$desktop"
done
update-desktop-database "$XDG_DATA_HOME/applications"
