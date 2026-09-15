// Manual lab instrument, not installed by release packages. It never grabs,
// injects, consumes input, opens UI, changes grabs, or bypasses authentication.
// Counts only touch/button event types, never keys, coordinates, or text.
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const EVENT_KEYS = new Map([
    [Clutter.EventType.TOUCH_BEGIN, 'touchBegin'],
    [Clutter.EventType.TOUCH_END, 'touchEnd'],
    [Clutter.EventType.BUTTON_PRESS, 'buttonPress'],
    [Clutter.EventType.BUTTON_RELEASE, 'buttonRelease'],
]);

export default class InputDiagnostic extends Extension {
    _snapshot() {
        const overview = Main.overview;
        const controls = overview._overview?._controls;
        console.log('T630 input diagnostic', JSON.stringify({
            events: this._counts,
            modalCount: Main.modalCount,
            modalActors: Main.modalActorFocusStack.map(record => ({
                type: record.actor.constructor.name,
                seatState: record.grab.get_seat_state(),
            })),
            overview: {shown: overview._shown, visible: overview.visible,
                animating: overview._animationInProgress, modal: overview._modal,
                coverVisible: overview._coverPane?.visible,
                coverReactive: overview._coverPane?.reactive,
                state: controls?._stateAdjustment?.value,
                appsChecked: overview.dash.showAppsButton.checked},
        }));
    }

    enable() {
        this._counts = {touchBegin: 0, touchEnd: 0, buttonPress: 0, buttonRelease: 0};
        this._samples = 0;
        this._capture = global.stage.connect('captured-event', (_stage, event) => {
            if (!Main.sessionMode.isLocked) {
                const key = EVENT_KEYS.get(event.type());
                if (key)
                    this._counts[key]++;
            }
            return Clutter.EVENT_PROPAGATE;
        });
        this._snapshot();
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 3, () => {
            this._snapshot();
            if (++this._samples < 60)
                return GLib.SOURCE_CONTINUE;
            this._timer = 0;
            this._stopCapture();
            console.log('T630 input diagnostic stopped after 180 seconds.');
            return GLib.SOURCE_REMOVE;
        });
    }

    _stopCapture() {
        if (this._capture)
            global.stage.disconnect(this._capture);
        this._capture = 0;
    }

    disable() {
        this._stopCapture();
        if (this._timer)
            GLib.Source.remove(this._timer);
        this._timer = 0;
    }
}
