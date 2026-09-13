# Login and additional buttons — 2026-09-12

## Owner instructions

Tablet is lab equipment, not holding active work. Routine setup/test restarts
are authorized without repeated save-work questions. Preserve credentials,
calibration, partitions and existing protections. User requested the remaining
buttons and then a lock screen/login screen; Power target is now lock/wake,
not merely an unprotected black overlay. Do not claim secure locking before
password verification and physical-compositor escape paths are addressed.

## Buttons

Active/red: owner confirmed show/hide keyboard works after targeted gpio_keys
udev remove/add refreshed libinput's cached capabilities. Early udev rule
71-t630-active-key.rules now maps before Weston. Reboot to
3bcae144-d96e-46cb-803e-d37a645078cf verified mapping lock file at14:40:26.368,
before Weston startup at14:40:28.199. Extensionv2 ACTIVE, audio auto-start passed.

Subsequent mapping expanded t630-red-button.py to handle Recents as well:
gpio_keys indices0=115(volumeup),1=185(Recents/F15/XF86Launch6),2=158(Back),
3=172(Home/XF86HomePage),4=184(Active/F14/XF86Launch5). Default remaps only1/4;
--restore restores both to254/252. Full keymap guard protects other entries.
GNOME settings preserve existing shortcuts and add:
- org.gnome.shell.keybindings toggle-application-view: XF86HomePage
- org.gnome.shell.keybindings toggle-overview: XF86Launch6

Owner confirmed **Home and Recents work**. Back native XF86Back is unchanged
and still needs app/navigation validation. Power lock/wake not implemented.
Power-button-action temporarily set to 'nothing' for session-service tests;
previous value 'suspend' did not provide a working power action in this setup.

## Login prerequisites and test

Original setup: no GDM daemon, no logind, no systemd PID1. GNOME lock-enabled
false. Physical root Weston+privateXwayland:3+normal-user nested GNOME cannot
be called a secure login boundary merely by drawing a password UI in GNOME:
the outer recovery desktop/root terminal must also be dealt with.
Kernel has cgroups but lacks VT, USER_NS, PID_NS, FHANDLE, SYSVIPC.

Installed Ubuntu packages (policy-rc.d101 prevented unsolicited startup):
gdm3 46.2-1ubuntu1~24.04.9, x11-xserver-utils, libcap-dev, libudev-dev,
libpam0g-dev, libacl1-dev, libattr1-dev, gperf, python3-jinja2 and dependency.
No packages removed. GDM package account gdmUID105/GID109 created normally.

Built upstream elogind255.27, matching Ubuntu's255-era protocol, from
https://github.com/elogind/elogind/archive/refs/tags/v255.27.tar.gz
Downloaded source SHA256:
1ef0dffaad77e8d8ded047895fc5e60b7ab5cf7137d356cebd821cc5a0d566c9
Source /usr/local/src/elogind-255.27, build/build, staged/stage.
Installed ONLY staged prefix /opt/t630/elogind-255.27; no system-library
replacement or global LD_PRELOAD. Daemon is libexec/elogind, not lib/elogind.
Build log /var/log/t630-elogind-build.log. Initial missingjinja2 resolved with
Ubuntu python3-jinja2 package. Native build -j2 succeeded.

Options: prefix/sysconfdir privateopt; libdirlib; localstatedir/var; release;
testsfalse, man/html disabled, translationsfalse, pam/polkitenabled;
pamconfdirno, privatepamlibdir/dbuspolicy/dbussystemservice/udevrules paths;
default-hierarchy legacy, cgroup-controller elogind,
default-kill-user-processesfalse, group-render-mode0660.
Private 90-t630-lab configs ignore all automatic power/lid/idle actions,
KillUserProcessesno, RemoveIPCno, disable all suspend/hibernate variants.

Manual elogind test ran successfully, exported real login1, mounted cgroups,
and accepted actual session accounting. register-gnome-session-test.py is a
bounded600-second root accounting test, NOT authentication/login verification.
It registered the existing GNOME PID1098 as actual login1 sessionc1.

Manual GDM test used process-local LD_PRELOAD of private libelogind.so.0;
standard daemon exposed version46.2. **Auth-only configuration did not suppress
the local greeter:** upstream gdm-manager.c starts local_factory when
!xdmcp_enabled OR show_local_greeter. Thus ShowLocalGreeterfalse only suppresses
it with XDMCP enabled. Do NOT enable a remote XDMCP listener as a workaround.
GDM spawned a native gdm-owned greeter on card0 while the existing desktop
remained displayed. Stopped GDM/PID4430, verified its GNOME children exited.
Original /etc/gdm3/custom.conf restored from custom.conf.before-t630-auth-test.

## Runtime collision and recovery (resolved)

Adding elogind beneath an already-running unmanaged desktop mounted fresh
tmpfs over /run/user/1000 and /run/user/0. PipeWire remained alive but its
public socket was obscured; root runtime cleanup also removed the old physical
Wayland socket path. This service must be integrated BEFORE creating user
runtime files. Root SSH PAM sessions must not manage the physical Weston's
unregistered runtime directory. No PAM authentication changes have been made.

Stopped experimental elogind/PID4342 and session holder/PID4897. Ordinary
unmount of exact experimental tmpfs /run/user/1000 and /run/user/0 restored
audio connections. Ordinary unmount /sys/fs/cgroup/elogind then /sys/fs/cgroup
removed experimental mounts. No forced/lazy unmount or driver unload.
Clean reboot restored the physical runtime socket as well.

Current verified recovery boot: c6c2a321-9826-48a3-a6ac-6a278e124ba3.
SSH/Wi-Fi connected automatically, physical Wayland socket exists, GNOME
extensionv2 ACTIVE, speaker sink unmuted, battery18% Charging. Experimental
elogind/GDM are NOT in startup. Locking remains off. No password was requested,
read, logged, changed or bypassed. No secure lock/login claimed.

## Work in progress

Added signed official Ubuntu deb-src repositories (main, noble/updates/security)
via t630-source-repositories.sources. Fetching matching patched Ubuntu GDM
source for a narrow auth-only local-greeter control, rather than changing any
authentication decisions or enabling remote login. Need assess managed session
startup and physical-compositor lock boundary before enabling a real lock.

## Managed-session test prepared

Matching Ubuntu GDM source was downloaded via signed apt repository indices;
dpkg-source applied the distribution patch series. Extra build dependencies
were installed as needed; no authentication packages removed. Private build
uses the project's supported `logind-provider=elogind` option: no LD_PRELOAD
needed. Prefix `/opt/t630/gdm-46.2-auth`, config `/etc/t630/gdm-auth/custom.conf`,
runtime `/run/t630-gdm`. XDMCP compiled OUT, remote-login disabled, automatic and
timed login disabled. Uses original Ubuntu `/etc/pam.d/gdm-password` unchanged.
Only additional GDM source patch: honor ShowLocalGreeter=false independently
of XDMCP state. No authentication/reauthentication decisions changed.
Source/build/install logs: `/var/log/t630-gdm-{build,extract,install}.log`.
Build script: `ubuntu/build-t630-gdm-auth.sh`; 275 targets built successfully.

Startup integration is a ONE-BOOT flag, `/etc/t630/login-next-boot`, consumed
as `/run/t630-login-test-consumed`. Normal boot remains the previous path.
`t630-login-start` launches real elogind and private auth-only GDM before
the GNOME child or its audio server creates runtime files.
`t630-managed-session` root parent registers its paused child with login1,
holds the returned session descriptor, and starts the existing normal-user
GNOME launcher with real XDG_SESSION_ID. This is lab-session accounting,
NOT password verification. GNOME locking is still off by default.

The root-only app launcher `t630-gnome-run` now joins the verified running
GNOME's exact elogind /cN cgroup before dropping to UID1000, when applicable.
It propagates XDG_SESSION_ID privately. Without elogind, old behavior remains.

PAM **session bookkeeping only**: inserted a conditional immediately before
the existing optional pam_systemd.so in common-session. Only root SSH skips
that one optional session module, preventing root's physical Weston runtime
from being mounted/removed by SSH accounting. All authentication, account,
password, pam_unix session, and other modules remain unchanged. Other users
and services retain the normal optional session module. Backup baselineSHA:
f237c090d61f72820ede6f77f4889e9db292b84fafb2c5d19ae6c125ea3bd371.
Patch dry-run/application, new SSH connection and sshd config check passed.

Clean-stop helper now explicitly stops experimental login daemons and
ordinarily unmounts the known UID1000/105 runtime/fuse and elogind cgroup
mounts before their parent mounts. No force/lazy unmount. Current helperSHA:
9146f3cdd0f47460aaba1e062a28bddd1c8cb70fd5aac66e3f40c545d1975437
Installed source and outer RAM helper hashes match. Remote-start accepts the
previous9ea0f7c8 helper for guarded upgrade.

Pre-test backups: `/usr/local/share/t630/backups/login-start.yPpTPv/` on tablet.
Shell/Python syntax checks, launcher --check, current audio/socket checks passed.
Managed-login restart dispatched; wait for the result before any lock test.

### First managed boot / lock UI feedback

Boot `31c4bc98-33a7-49ce-a64f-3a8bd0731413`: actual c1 session registered
before runtime creation. Audio remained working; no root runtime mount was
created by root SSH. Private GDM opened the normal reauthentication channel.
GNOME's real lock/password UI appeared and the user successfully authenticated
with their existing password. Wrong-password rejection is not yet tested.
Home and Recents were both confirmed working by the user.

User reported first swipe/password focus bounced back to clock; second attempt
unlocked. Full shell stack identifies `keyboard.js:1165 maybeHandleEvent` called
by `unlockDialog.js:672`: `keyboardBox.contains(null)` throws on crossing
events during transition. Narrow guard staged with a hash-checked resource
overlay; only null actors return false to the normal event path. No PAM,
authentication or screen-shield decisions are changed. Packaged GNOME files
remain untouched. Installer `ubuntu/install-t630-keyboard-guard.py` verifies
the installed keyboard module SHA256 before adding the guard.

Elogind PID687 also disappeared during that test, with no recorded diagnostic.
The managed session holder727 still held c1.ref and shell1161 remained in /c1.
Restarting elogind reused the existing UID1000 runtime mount and deserialized
c1 correctly; foreground diagnostic run stayed alive. Cause not yet known.
Added detached session startup and a wrapper logging daemon lifetime/exit
status (no authentication conversation logging). No restart loop was added.

Second one-boot managed-session test dispatched with the UI guard. Backup on
tablet: `/usr/local/share/t630/backups/lock-ui.BtfpLW`. Automatic locking and
power-button mapping remain pending. Outer recovery desktop/root USB console
still exist, so this is not yet a hardened whole-device login boundary.

Second managed boot `227d8a4e-2e67-4773-aa32-1d4b206274ef` successfully loaded
the exact keyboard overlay (confirmed by GLib's resource-open message).
Elogind691, parent686 in detached session686, registered c1 and stayed alive
through network/NTP startup and the next lock request. LockedHint=yes and
ScreenSaver.GetActive=true agree. No null-descendant error has recurred in
the current log. User has been asked to test one wrong password, then normal
password, and whether first-swipe focus is stable; response still pending.
No password/screen capture was taken during this test. Wi-Fi restored, audio
sink unmuted, battery18% Charging. Only network listener22 and loopback8765.
Keyboard overlay is also checked against distro resource hash at every launch,
so future GNOME upgrades disable the old overlay pending review.

### Retest failed; power-daemon crash identified

User reported bounce again and then unresponsive touch. Shell and login1 were
still running at first inspection; no null-actor JS exception recurred, so the
guard removed a real error but did not resolve the interaction bug. Synthetic
Return opened the password prompt, demonstrating shell event loop was alive.
Three Clutter touch-dispatch return-value warnings appeared during the gesture.

Lifetime logging then caught elogind exiting134: two power-key shutdown requests
hit `!m->action_job` assertion in logind-dbus.c:2183. Source inspection found
the cause of missing safety policy: private PKGSYSCONFDIR applies to the MAIN
config, but config_parse_config_file builds drop-in paths from fixed CONF_PATHS.
The private logind.conf.d safety settings were silently not loaded.
Installed existing safety contents into private main logind.conf/sleep.conf,
backing originals up to `/usr/local/share/t630/backups/elogind-config.plO0Yq`.
Restarted daemon deserialized c1; D-Bus confirmed HandlePowerKey='ignore' and
PreparingForShutdown=false. Startup now checks both config and live power
policy. This fixes the independently reproduced daemon/power fault; it does
not establish the swipe-bounce cause.

Recovery reboot dispatched with temporary unlockDialog state/stack tracing.
It logs only method names/stacks, not event data, characters, or passwords.
Third test boot brings up an unlocked desktop first; automatic locking remains
off. Need reproduce gesture and remove temporary tracing once understood.

Third boot `6609306a-d973-4069-a808-fea85a91278f`: corrected main policy loaded;
elogind692 survived successful user password unlock (user explicitly confirmed
they typed/submitted it) and the bounded separate GDM negative test.
`tools/check-gdm-rejection.py` ran as tabletUID1000 in c1 and submitted exactly
one deliberately invalid string through the normal GDM reauthentication API:
result REJECTED. No real password was read. passwd -S confirmed P (set).

Synthetic swipes and focus taps reliably logged `_showPrompt` multiple times,
including when a prompt was already active. GNOME46 `_ensureAuthPrompt`
unconditionally resets the active authentication conversation before checking
which page is shown; every such focus tap also emitted stale Clutter actor
warnings. Current upstream GNOME handles this by inspecting verificationStatus
and resetting only NOT_VERIFYING, CANCELLED or FAILED states:
https://github.com/GNOME/gnome-shell/blob/main/js/ui/unlockDialog.js
Backported that guard with GNOME46's boolean sensitivity API; password
success/failure decisions remain unchanged. Keyboard/null guard retained.
Both resources' original hashes are now checked at startup to avoid shadowing
updated package code. Fourth one-boot test dispatched with state tracing
retained temporarily for verification. User has not yet validated this guard.

Fourth boot `9b5b5d73-adef-463a-bf50-03048565c937` hit a separate graphics
failure before the lock test: GNOME1163 Turnip/KGSL write translation fault at
boot14.876s, GPU hang, threshold3faults/3s, Zink VK_ERROR_DEVICE_LOST. Shell
process stayed alive but did not answer lock D-Bus; serial diagnosis/SSH worked.
Full log saved on tablet `/var/log/t630-gnome-gpu-startup-fault.log`.
This is new evidence that accelerated startup is not fully reliable despite
earlier passing boots. Next test uses existing llvmpipe fallback, with a new
one-boot `/etc/t630/software-next-boot` marker consumed by desktop-autostart.
Persistent gpu.enabled is preserved. This isolates UI testing from the GPU
failure; it is not a hardware acceleration fix.

The fourth boot's clean shutdown correctly refused to proceed after 30s:
GNOME1163 ignored TERM and remained in futex_wait_queue_me. Read-only process
checks confirmed it was the sole remaining /run/ubuntu-rooted process, parent1,
comm gnome-shell. Sent KILL to that validated PID only, then retried the same
ordinary-unmount stop helper. No forced/lazy unmount or raw reboot was used.

### Software-rendered validation, awaiting physical confirmation

Boot `a57f879e-cde4-4c6f-9123-da5a38b04523` successfully started normal-user
GNOME1083 using software rendering and real session c1 with elogind686.
Important test-harness correction: older synthetic touch helpers predated the
installed -1/0/1,0/-1/1 calibration. Their taps were reversed (900,660 landed at
1018,540). Fixed the INVERSE transform in the synthetic helpers only; no physical
input calibration/driver was changed. Verified a requested900,660 now lands
899,659. Earlier synthetic swipe directions and key targets are NOT valid
evidence of real physical gesture behavior. The unconditional active-prompt
reset is still source-confirmed; upstream status guard retained.

With the corrected test path, swipe-up, field tap, touch-keyboard Q, another
field tap, and a second Q retained two masked test characters. Same verifier
PID2090 stayed alive through field taps. No new stale-actor/JS error appeared
in that corrected sequence. Earlier pre-correction reversed swipes had produced
stale-actor/disposed-verifier warnings; keep that distinction in diagnostics.

Submitted the previously verified deliberately invalid string through the real
UI, pressing on-screen Enter via synthetic touch. UI displayed password
authentication failure and remained locked with a ready password field. No
real password was read. Three further calibrated swipe/type/focus cycles
passed; intentional Escape between cycles returned to clock as expected.
Verifiers2217/2234/2250 correspond to separate intentional new attempts, not
unexpected mid-entry resets. Daemon stayed alive, sound unmuted, Charging.

Selected `/etc/t630/gpu.disabled` temporarily, preserving gpu.enabled, to keep
the observed startup fault from returning during ongoing login work. Current
desktop uses software rendering. Hardware acceleration remains an open issue.
Returned to clock with Escape and asked user to swipe/login normally, without
another wrong-password attempt. No further screenshots/input while user types.
State-only tracing remains active for this experimental boot. Automatic lock
and persistent login startup have not yet been enabled. Source/driver limits
mean no hardened whole-device login boundary is claimed.

Physical retest still FAILED. At19:34:03 swipe began; at19:34:04.874 it ended
via `_cancelTouchGesture`/`vfunc_gesture_cancel`, coincident with Clutter touch
dispatch warning. No PAM failure or idle timeout caused that return. This
distinguishes the original reported behavior from active-prompt-reset bugs.
The password OSK is raised during `_swipeBegin` by creating/focusing AuthPrompt;
on a slow/bottom-originating swipe it can intercept the in-progress touch.
Changed overlay to defer `_ensureAuthPrompt` until `_swipeEnd` settles on page1.
Cancelled gestures remain at clock without ever opening the password keyboard.
Password authentication decisions remain unchanged. Recovery reboot dispatched
with this new guard; need test slow bottom-originating swipe and physical input.
After the physical cancellation, synthetic swipes no longer reached the tracker,
matching user's touch-stalled report; simulated keyboard still worked.

Deferred-keyboard boot `1e27b825-7a4b-415e-83d9-b4cbdfda1674`, GNOME1089,
elogind693, software renderer: tested calibrated bottom-originating swipes
(960,1100)->(960,350) over1.8s and (960,1100)->(960,250) over3s. Both ended via
the normal gesture_end path, not gesture_cancel; current log has zero
_cancelTouchGesture and zero Clutter-WARNING matches. These are more relevant
than the earlier quick swipes starting above the keyboard region.
Returned to clock and requested physical swipe/login confirmation again.
No further input or screen capture while user tests. This revision's physical
confirmation is pending; do not describe the original issue as resolved yet.

### Owner-confirmed outcome

Owner replied **“Yeah, it worked.”** to the physical swipe/password test after
deferring keyboard activation. Trace recorded physical swipe19:39:52 via normal
gesture_end (no cancellation), and ScreenSaver.GetActive=false confirmed unlock.
Elogind693 remains alive, no automatic shutdown request. This resolves the
reported swipe-bounce/touch stall on the current software-rendered test boot.

Installed overlays now omit temporary tracing by default; installer supports
explicit `--trace` for future diagnosis. The running shell has already loaded
its diagnostic module, so those state-only traces persist until its next normal
restart; no extra reboot was performed after successful user validation.
Installed keyboard SHA256 e385ba42ee567ccbbd757dc502bd5b4847c5adb6c3ff2d8cfcf0b363011ee935;
unlockDialog SHA256 feca050fb51f4cd49d3b037f870213d30690d112c574844135dce2cb6a59875c.
Python installers/test helpers passed compile checks. Packaged GNOME and
authentication stacks remain unchanged. Software-renderer opt-out remains on.

Next work: persistent managed login/lock startup (currently one-boot testing),
Power binding once lock integration is persistent, outer recovery escape/login
boundary, then independent GPU startup fault. Do not claim boot authentication
or a hardened lock boundary; current standard GDM/PAM screen unlock is verified.
