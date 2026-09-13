import St from 'gi://St';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as QuickSettings from 'resource:///org/gnome/shell/ui/quickSettings.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

export default class TabletKeyboard extends Extension {
    _displayRequest(args, callback = null) {
        try {
            const process = Gio.Subprocess.new(['/usr/local/bin/t630-display', ...args],
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
            process.communicate_utf8_async(null, null, (proc, result) => {
                try {
                    const [, output] = proc.communicate_utf8_finish(result);
                    if (this._displayActive && proc.get_successful())
                        callback?.(JSON.parse(output));
                } catch (_) { /* Keep the rest of the desktop usable if service is absent. */ }
            });
        } catch (_) { /* No privileged fallback. */ }
    }

    _refreshDisplay() {
        this._displayRequest(['status'], status => {
            this._updatingDisplay = true;
            this._brightness.slider.value = status.brightness / 100;
            this._keepAwake.checked = status.idle_seconds === 0;
            this._keepAwake.subtitle = status.idle_seconds === 0
                ? 'Automatic screen-off paused' : `Screen off after ${status.idle_seconds / 60} min`;
            this._brightness.visible = true;
            this._keepAwake.visible = true;
            this._updatingDisplay = false;
        });
    }

    _toggleKeyboard() {
        if (Main.keyboard.visible)
            Main.keyboard.close();
        else
            Main.keyboard.open(Main.layoutManager.focusIndex);
    }

    enable() {
        this._settings = this.getSettings();
        Main.wm.addKeybinding(
            'toggle-keyboard', this._settings,
            Meta.KeyBindingFlags.IGNORE_AUTOREPEAT,
            Shell.ActionMode.NORMAL | Shell.ActionMode.OVERVIEW,
            () => this._toggleKeyboard());
        this._indicator = new PanelMenu.Button(0, 'Tablet keyboard', true);
        const button = new St.Button({
            label: 'Keyboard', accessible_name: 'Show or hide keyboard',
            can_focus: false, reactive: true, track_hover: true,
            style: 'padding: 0 18px;',
        });
        button.connect('clicked', () => this._toggleKeyboard());
        this._indicator.add_child(button);
        Main.panel.addToStatusArea(this.uuid, this._indicator, 0, 'right');
        this._displayActive = true;
        this._powerIndicator = new QuickSettings.SystemIndicator();
        this._brightness = new QuickSettings.QuickSlider({
            iconName: 'display-brightness-symbolic', iconLabel: 'Screen brightness',
        });
        this._brightness.slider.accessible_name = 'Screen brightness';
        this._brightness.visible = false;
        this._brightness.slider.connect('notify::value', () => {
            if (this._updatingDisplay)
                return;
            if (this._brightnessTimer)
                GLib.Source.remove(this._brightnessTimer);
            this._brightnessTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 200, () => {
                this._brightnessTimer = 0;
                const value = Math.max(5, Math.round(this._brightness.slider.value * 100));
                this._displayRequest(['brightness', String(value)]);
                return GLib.SOURCE_REMOVE;
            });
        });
        this._keepAwake = new QuickSettings.QuickToggle({
            title: 'Keep Awake', iconName: 'weather-clear-symbolic', toggleMode: true,
        });
        this._keepAwake.visible = false;
        this._keepAwake.connect('clicked', () => {
            this._displayRequest(['idle', this._keepAwake.checked ? '0' : '300'],
                () => this._refreshDisplay());
        });
        this._powerIndicator.quickSettingsItems.push(this._brightness, this._keepAwake);
        Main.panel.statusArea.quickSettings.addExternalIndicator(this._powerIndicator, 2);
        this._powerMenu = Main.panel.statusArea.quickSettings.menu;
        this._powerMenuId = this._powerMenu.connect('open-state-changed', (_menu, open) => {
            if (open)
                this._refreshDisplay();
        });
        this._fullscreenTimer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 15, () => {
            if (!Main.sessionMode.isLocked && global.display.focus_window?.is_fullscreen())
                this._displayRequest(['inhibit']);
            return GLib.SOURCE_CONTINUE;
        });
        this._refreshDisplay();
    }

    disable() {
        this._displayActive = false;
        if (this._brightnessTimer)
            GLib.Source.remove(this._brightnessTimer);
        if (this._fullscreenTimer)
            GLib.Source.remove(this._fullscreenTimer);
        this._brightnessTimer = this._fullscreenTimer = 0;
        if (this._powerMenuId)
            this._powerMenu.disconnect(this._powerMenuId);
        this._powerMenuId = 0;
        this._powerMenu = null;
        this._powerIndicator?.quickSettingsItems.forEach(item => item.destroy());
        this._powerIndicator?.destroy();
        this._powerIndicator = null;
        Main.wm.removeKeybinding('toggle-keyboard');
        this._settings = null;
        this._indicator?.destroy();
        this._indicator = null;
    }
}
