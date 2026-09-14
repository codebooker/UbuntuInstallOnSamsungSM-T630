# Everyday Ubuntu applications — 2026-09-12

## Scope and installed baseline

Installed native ARM64 Ubuntu packages on the existing persistent Ubuntu
24.04.5 SM-T630 system. No reflash, partition changes, kernel changes, compositor
restart, input recalibration, password reset, or new network listener.

- GNOME Software 46.0-1ubuntu2 with PackageKit and Ubuntu repository catalog.
- Firefox 155.0.1~build1, native DEB from Mozilla's signed APT repository.
- LibreOffice Writer, Calc and Impress 24.2.7, with GTK3 integration.
- Nautilus Files, GNOME Text Editor, GNOME Terminal.
- Evince PDFs, Eye of GNOME photos, File Roller archives.
- Calculator, Clocks, Calendar, System Monitor, Disks, Characters, Fonts.
- Totem Videos and common GStreamer codec plugins.
- Fonts, spellcheck, GVFS backends, XDG utilities and standard home folders.

`ubuntu/install-everyday-apps.sh` records the Ubuntu package selection. Its
deployment is `/usr/local/share/t630/install-everyday-apps.sh`. Install completed
with exit 0; `/run/t630-everyday-install.log` is the tablet log. Firefox's
separate install also completed with exit 0. `dpkg --audit` is clean.

Firefox is the default browser. `ubuntu/configure-everyday-desktop.sh` configures
standard home folders and common file associations in the isolated GNOME
profile. Office desktop files have an explicit `/home/tablet` working directory:
the running GNOME inherited `/root`, which broke Office's shell launcher. Future
GNOME launches now change to HOME before starting the session. Existing desktop
files and user documents under the ordinary home profile were not overwritten.

## Validation so far

- Firefox ran as UID 1000, loaded Mozilla over HTTPS and spawned its normal
  content processes. No browser sandbox-disable flag was used.
- Writer rendered its normal document window on the tablet after the cwd fix.
- Inkscape rendered full-screen and the live view showed the owner's freehand
  drawing. Its unsaved document was left open; no desktop restart was performed.
- Calculator launched and remained running with only a currency-rate warning;
  it was not brought over the owner's active Inkscape drawing for visual testing.
- Software displayed its catalog with application icons and details.
- The owner confirmed password approval worked. PackageKit then installed
  Contacts 46.0-1build1 and Inkscape 1.2.2-2ubuntu12 through Software. Both are
  confirmed installed by dpkg and by APT history entries whose command line is
  `packagekit role='install-packages'`, at 16:06 and 16:07 respectively.
- Default browser, PDF, text and DOCX associations were queried successfully.
- Shell scripts passed `sh -n`; Python helpers passed `py_compile`.
- About 102 GiB remained free and 4.3 GiB RAM available at the final resource
  check. Battery reported Charging and 22% during this turn.

Not every application has been functionally tested. Sound still has no ALSA
hardware card; installing media applications is not proof of working audio.
Boot still starts Weston; full-screen GNOME remains a normal-user nested session.

## Store authentication integration

This prototype has no systemd/logind login session. Two independent issues
prevented normal graphical PackageKit authentication:

1. D-Bus started polkitd as root, then polkitd dropped UID. On this Samsung
   kernel its own `/proc/self/fdinfo` remained root-owned/inaccessible after
   dropping privileges. A read-only syscall trace showed pidfd_open succeeded
   but opening that fd's fdinfo failed EACCES, yielding "Process not found".
   D-Bus activation now starts as `User=polkitd` with `setpriv --no-new-privs`,
   matching those aspects of Ubuntu's normal systemd service. Process lookup
   now succeeds. No authorization rules were relaxed.
2. GNOME's built-in authentication agent registers for a logind session, which
   does not exist here. A small adaptation of Ubuntu's polkit-gnome agent
   registers for a specific same-user process instead, using PolkitUnixProcess
   with library-resolved start time/pidfd. Native polkit/PAM still verify the
   tablet user's password and apply Ubuntu's normal sudo-group admin rules.

The packaged D-Bus service has a dpkg diversion at:
`/usr/share/dbus-1/system-services/org.freedesktop.PolicyKit1.service.t630-stock`.
Replacement source: `ubuntu/org.freedesktop.PolicyKit1.service`.

Agent source and Ubuntu patches are retained in
`ubuntu/polkit-gnome-source/polkit-gnome-0.105/` with their licenses, deployed at
`/usr/local/share/t630/polkit-gnome-0.105/`. Rebuild with
`sh /usr/local/share/t630/build-polkit-agent.sh`; development prerequisites are
gcc, pkg-config, libgtk-3-dev, libpolkit-agent-1-dev and libpolkit-gobject-1-dev.
The executable `/usr/local/libexec/t630-polkit-agent` is root-owned mode 755,
not setuid, and runs as tablet. The current Ubuntu system PAM helper retains its
normal package-provided setuid permissions and security updates.

An Ubuntu patch unconditionally called an X11 timestamp accessor on the dialog.
For this Wayland session, that call is now guarded with GDK_IS_X11_WINDOW and
the Wayland branch uses gtk_window_present. Before this fix an agent disappeared
and its helper reported PAM authentication failure; that did not establish that
the owner had typed an incorrect password. After the fix, the agent and its PAM
helper remained alive with the password prompt open for account `tablet`.

`ubuntu/t630-auth-watch.py` supervises process-scoped agents only for Software,
Settings, Files and Disks belonging to UID 1000 in this exact GNOME session. It
does not change policy. It stops when the session bus closes. GNOME's launcher
starts/stops the supervisor. These startup changes are deployed but have not
yet been verified by a complete new GNOME session or reboot. Current session's
supervisor was started manually and restarted after authentication completed to
activate its latest exit-status logging refinement.

Compiled agent SHA256:
`98264228a53c2f42881b03972798bce205e249c7b5ab6dfeb44e2b4d704f4014`.
Matching local artifact: `output/t630-polkit-agent`.

### End-to-end store test passed

Contacts was requested through GNOME Software's own install action as tablet:
`gnome-software '--install=system/package/*/org.gnome.Contacts.desktop/*' --interaction=full`.
The original bare component ID was rejected; the five-part AppStream ID invoked
the real store transaction and opened authentication. The owner entered their
password on the tablet and confirmed success; PackageKit/dpkg independently
confirmed Contacts installed. The owner's subsequent Inkscape install also
completed through PackageKit. Neither was installed separately by root APT to
bypass this test. A fresh unrelated process's noninteractive package-install
authorization still returns exit 2 (authentication required).

## Browser repository and constraints

Mozilla setup follows its official instructions:
https://support.mozilla.org/en-US/kb/install-firefox-linux

Signing key fingerprint was verified as:
`35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3`.
Repository/key paths are `/etc/apt/sources.list.d/mozilla.sources` and
`/etc/apt/keyrings/packages.mozilla.org.asc`. Only Firefox and its locale
packages are preferentially pinned to Mozilla; Ubuntu's Firefox Snap transition
is excluded. Local definitions: `ubuntu/mozilla.sources` and
`ubuntu/mozilla-firefox.pref`. No accounts, passwords, browser imports or sync
were configured by the agent.

This is GNOME Software for native Ubuntu packages, not Canonical's Snap-based
App Center. Snap/Flatpak were not enabled: this kernel lacks PID/user namespaces.
No sandbox bypass was added to force unsupported packaging to run.

## Clean release-root acceptance (2026-09-14)

The same native application set is now part of
`tools/provision_rehearsal_root.sh`, rather than an untracked step performed only
on the development tablet. It installed 360 public packages into the preserved,
identity-clean Ubuntu Base rehearsal root. The explicit applications, Firefox
APT policy, repository-key SHA256/fingerprint, empty package audit, absent
`snapd`, and clean release identity audit were all checked afterward.

Downloaded package archives and the temporary GnuPG inspection home were
removed, leaving a 3.1 GB root. APT indexes and AppStream metadata were retained
so GNOME Software has a catalog after the end user completes first boot.

## Useful maintenance entry points

`/usr/local/bin/t630-gnome-run COMMAND` launches an app in the current GNOME
session as tablet, from its home directory. It accepts only callers UID 0 or
1000 and always executes the app as UID 1000; it is not setuid. It locates one
matching GNOME process and reads only its session environment without printing
it. Use this instead of guessing stale bus addresses or exporting the setup
desktop's input/preload environment.

Physical desktop, Wi-Fi and SSH recovery remain as documented in the earlier
GNOME and remote-access reports. No full user-data snapshot was made this turn;
do not copy credential-bearing home or network configuration into public reports.
