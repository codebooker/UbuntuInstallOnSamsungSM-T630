#!/usr/bin/python3
"""One negative GDM/PAM check. Never reads a real password or prompt text."""
import os
import gi
gi.require_version('Gdm', '1.0')
from gi.repository import Gdm, GLib

assert os.getuid() == 1000
client = Gdm.Client()
verifier = client.open_reauthentication_channel_sync('tablet', None)
loop = GLib.MainLoop()
outcome = 'timeout'
answered = False

def answer(v, service, _prompt):
    global answered
    if not answered:
        answered = True
        v.call_answer_query_sync(service, 't630-deliberately-invalid-check-4a98d2', None)

def done(_v, *unused):
    global outcome
    outcome = 'REJECTED' if answered else 'FAILED_BEFORE_ANSWER'
    loop.quit()

def success(_v, *unused):
    global outcome
    outcome = 'UNEXPECTED_ACCEPTANCE'
    loop.quit()

verifier.connect('secret-info-query', answer)
verifier.connect('verification-failed', done)
verifier.connect('verification-complete', success)
GLib.timeout_add_seconds(15, lambda: (loop.quit(), GLib.SOURCE_REMOVE)[1])
verifier.call_begin_verification_for_user_sync('gdm-password', 'tablet', None)
loop.run()
verifier.call_cancel_sync(None)
print('Single negative GDM/PAM check:', outcome)
raise SystemExit(0 if outcome == 'REJECTED' else 1)
