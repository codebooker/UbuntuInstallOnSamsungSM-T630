#!/usr/bin/python3
"""Stage a version-checked, GNOME-only resource overlay; preserve distro files."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--trace', action='store_true',
                    help='Add temporary state-only lock transition tracing')
args = parser.parse_args()
assert os.getuid() == 0
assert Path('/etc/t630-install-id').read_text().strip() == 'SM-T630-T630XXSBDZE3-Ubuntu-v1'
source = subprocess.check_output([
    'gresource', 'extract', '/usr/lib/gnome-shell/libshell-14.so',
    '/org/gnome/shell/ui/keyboard.js',
])
assert hashlib.sha256(source).hexdigest() == 'ca04df3bd982c4034e35c1fdb83a2744be03bf41ac04db3eb98e4129f79af575', 'GNOME changed: review overlay before updating'
old = b'''        const actor = global.stage.get_event_actor(event);

        if (Main.layoutManager.keyboardBox.contains(actor) ||'''
new = b'''        const actor = global.stage.get_event_actor(event);
        // Crossing events during lock-screen transitions can have no actor.
        // Let the original event path continue; never alter authentication.
        if (!actor)
            return false;

        if (Main.layoutManager.keyboardBox.contains(actor) ||'''
assert source.count(old) == 1
target = Path('/usr/local/share/t630/gnome-resource-overlay/keyboard.js')
target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
target.write_bytes(source.replace(old, new))
target.chmod(0o644)
print('Installed actor-null guard only; packaged GNOME unchanged.')

# Unlock UI fixes; optional tracing never records events or credentials.
dialog = subprocess.check_output([
    'gresource', 'extract', '/usr/lib/gnome-shell/libshell-14.so',
    '/org/gnome/shell/ui/unlockDialog.js',
])
assert hashlib.sha256(dialog).hexdigest() == 'd456126f998cd0fb2d4e3e70cd58bde7c5bfbd326623c8ee1a4ab79d6e47ecdb'
# Backport the current upstream _ensureAuthPrompt status guard, adapting its
# sensitivity call to GNOME 46's boolean API. A tap must not reset an already
# active password conversation. Password success/failure decisions are intact.
reset_old = b'''        this._authPrompt.reset();
        this._authPrompt.updateSensitivity(true);'''
reset_new = b'''        const {verificationStatus} = this._authPrompt;
        switch (verificationStatus) {
        case AuthPrompt.AuthPromptStatus.NOT_VERIFYING:
        case AuthPrompt.AuthPromptStatus.VERIFICATION_CANCELLED:
        case AuthPrompt.AuthPromptStatus.VERIFICATION_FAILED:
            this._authPrompt.reset();
            this._authPrompt.updateSensitivity(
                verificationStatus === AuthPrompt.AuthPromptStatus.NOT_VERIFYING);
        }'''
assert dialog.count(reset_old) == 1
dialog = dialog.replace(reset_old, reset_new)
# Creating/focusing the password prompt during a bottom-originating swipe
# raises the OSK into that same touch sequence. In the nested input backend
# this cancels the swipe and can strand the sequence. Start authentication
# only after a swipe has settled on the prompt page, never during the drag.
begin_old = b'''        this._adjustment.remove_transition('value');

        this._ensureAuthPrompt();

        let progress = this._adjustment.value;'''
begin_new = b'''        this._adjustment.remove_transition('value');

        // Defer password focus/OSK until the gesture has released its touch.
        let progress = this._adjustment.value;'''
assert dialog.count(begin_old) == 1
dialog = dialog.replace(begin_old, begin_new)
end_old = b'''    _swipeEnd(tracker, duration, endProgress) {
        this._activePage = endProgress'''
end_new = b'''    _swipeEnd(tracker, duration, endProgress) {
        if (endProgress)
            this._ensureAuthPrompt();

        this._activePage = endProgress'''
assert dialog.count(end_old) == 1
dialog = dialog.replace(end_old, end_new)
methods = ('_showClock()', '_showPrompt()', '_fail()', '_escape()',
           '_swipeBegin(tracker, monitor)', '_swipeEnd(tracker, duration, endProgress)')
for method in methods if args.trace else ():
    needle = ('    ' + method + ' {\n').encode()
    assert dialog.count(needle) == 1
    message = method.split('(')[0]
    trace = f"        console.log('T630 lock trace {message}', new Error().stack);\n".encode()
    dialog = dialog.replace(needle, needle + trace)
dialog_target = target.with_name('unlockDialog.js')
dialog_target.write_bytes(dialog)
dialog_target.chmod(0o644)
print('Installed auth-status and deferred-keyboard guards; tracing:', args.trace)
