#!/usr/bin/python3
"""Launch native GTK pen apps in the existing unprivileged GNOME session.

Does not create/reset preferences, record input, or modify existing documents.
"""
import os
import sys

COMMANDS = {'notes': '/usr/bin/xournalpp', 'drawing': '/usr/local/libexec/t630-mypaint'}


def main():
    if os.getuid() == 0:
        raise SystemExit('Launch through t630-gnome-run as the desktop owner, not root.')
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        raise SystemExit('Usage: t630-pen-app notes|drawing [FILES...]')
    env = os.environ.copy()
    if env.get('WAYLAND_DISPLAY') != 't630-gnome-0':
        raise SystemExit('Launch through the existing tablet GNOME session.')
    env.update(GDK_BACKEND='wayland', GTK_THEME='Adwaita:dark')
    if sys.argv[1] == 'drawing':
        # Noble's MyPaint extension calls Python from OpenMP workers without
        # holding the GIL (upstream #1253, Debian #1079663). Until a patched
        # native package is accepted, serialize this app only.
        env['OMP_NUM_THREADS'] = '1'
    command = COMMANDS[sys.argv[1]]
    os.execve(command, [command, *sys.argv[2:]], env)


if __name__ == '__main__':
    main()
