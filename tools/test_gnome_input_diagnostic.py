import json
from pathlib import Path
import shutil
import subprocess
import unittest


class InputDiagnosticTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_observer_propagates_input_excludes_keys_and_lock_and_stops(self):
        path = Path(__file__).with_name('gnome-input-diagnostic') / 'extension.js'
        script = r'''
const assert = require('node:assert/strict');
const vm = require('node:vm');
const source = SOURCE.replace(/^import .*;\n/gm, '')
    .replace('export default class', 'class');
let capture, timer, disconnected = 0, removed = 0;
const Clutter = {EventType: {TOUCH_BEGIN: 1, TOUCH_END: 2,
    BUTTON_PRESS: 3, BUTTON_RELEASE: 4}, EVENT_PROPAGATE: false};
const Main = {sessionMode: {isLocked: false}, modalCount: 0,
    modalActorFocusStack: [], overview: {_shown: false, visible: false,
        _animationInProgress: false, _modal: false,
        _coverPane: {visible: false, reactive: true},
        dash: {showAppsButton: {checked: false}}}};
const sandbox = {Clutter, Main, Extension: class {},
    console: {log() {}},
    global: {stage: {connect(signal, callback) {
        assert.equal(signal, 'captured-event'); capture = callback; return 123;
    }, disconnect(id) {assert.equal(id, 123); disconnected++;}}},
    GLib: {PRIORITY_DEFAULT: 0, SOURCE_CONTINUE: true, SOURCE_REMOVE: false,
        timeout_add_seconds(priority, seconds, callback) {
            assert.equal(seconds, 3); timer = callback; return 456;
        }, Source: {remove(id) {assert.equal(id, 456); removed++;}}}};
vm.runInNewContext(source + '\nthis.Diagnostic = InputDiagnostic;', sandbox);
const diagnostic = new sandbox.Diagnostic();
diagnostic.enable();
for (const type of [1, 2, 3, 4, 99])
    assert.equal(capture(null, {type: () => type}), false);
assert.equal(JSON.stringify(diagnostic._counts), JSON.stringify({
    touchBegin: 1, touchEnd: 1, buttonPress: 1, buttonRelease: 1}));
Main.sessionMode.isLocked = true;
capture(null, {type: () => 1});
assert.equal(diagnostic._counts.touchBegin, 1);
for (let i = 0; i < 59; i++) assert.equal(timer(), true);
assert.equal(timer(), false);
assert.equal(disconnected, 1);
diagnostic.disable();
assert.equal(disconnected, 1);
assert.equal(removed, 0);
diagnostic.enable(); diagnostic.disable();
assert.equal(disconnected, 2);
assert.equal(removed, 1);
'''.replace('SOURCE', json.dumps(path.read_text()), 1)
        subprocess.run([shutil.which('node'), '-e', script], check=True,
                       capture_output=True, text=True, timeout=10)


if __name__ == '__main__':
    unittest.main()
