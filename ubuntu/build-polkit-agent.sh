#!/bin/sh
# Build on the tablet from the retained Ubuntu-patched upstream source.
set -eu
cd /usr/local/share/t630/polkit-gnome-0.105
output=$(mktemp /usr/local/libexec/t630-polkit-agent.XXXXXX)
trap 'rm -f "$output"' EXIT
gcc -O2 -I. -DHAVE_CONFIG_H \
    -DPOLKIT_AGENT_I_KNOW_API_IS_SUBJECT_TO_CHANGE \
    src/main.c src/polkitgnomelistener.c src/polkitgnomeauthenticator.c \
    src/polkitgnomeauthenticationdialog.c \
    $(pkg-config --cflags --libs gtk+-3.0 polkit-agent-1 polkit-gobject-1) \
    -o "$output"
chmod 755 "$output"
chown root:root "$output"
mv "$output" /usr/local/libexec/t630-polkit-agent
