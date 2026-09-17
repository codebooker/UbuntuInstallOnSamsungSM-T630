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
    _hideStockControl(item) {
        if (!item)
            return;
        const wasVisible = item.visible;
        const signal = item.connect('notify::visible', () => {
            if (item.visible)
                item.hide();
        });
        item.hide();
        this._hiddenStock.push({item, signal, wasVisible});
    }

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
            this._autoSuspend.checked = status.auto_suspend;
            this._autoSuspend.visible = true;
            this._flashlight.checked = status.flashlight.enabled;
            this._flashlight.visible = status.flashlight.available;
            this._flashlightBrightness.slider.value = status.flashlight.brightness / 100;
            this._flashlightBrightness.visible = status.flashlight.available;
            this._updatingDisplay = false;
        });
    }

    _toggleKeyboard() {
        if (Main.keyboard.visible)
            Main.keyboard.close();
        else
            Main.keyboard.open(Main.layoutManager.focusIndex);
    }

    _openSettings() {
        try {
            // Shell itself is a nested compositor client. Join the desktop's
            // inner Wayland display rather than inheriting Shell's parent.
            Gio.Subprocess.new(['/usr/local/bin/t630-gnome-run',
                '/usr/bin/gnome-control-center'],
                Gio.SubprocessFlags.NONE);
        } catch (_) { /* The package dependency normally guarantees this app. */ }
    }

    _openAndroidSwitch() {
        try {
            Gio.Subprocess.new(['/usr/local/bin/t630-gnome-run',
                '/usr/local/libexec/t630-switch-dialog'],
                Gio.SubprocessFlags.NONE);
        } catch (_) { /* The guarded helper remains unavailable on unsupported installs. */ }
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
        this._hiddenStock = [];
        // GNOME 46's standard backlight path does not own this stock panel.
        // Its rotation toggle controls the deliberately isolated nested handler.
        const quickSettings = Main.panel.statusArea.quickSettings;
        this._hideStockControl(quickSettings._brightness?.quickSettingsItems?.[0]);
        this._hideStockControl(quickSettings._autoRotate?.quickSettingsItems?.[0]);
        this._powerIndicator = new QuickSettings.SystemIndicator();
        this._rotationLock = new QuickSettings.QuickToggle({
            title: 'Rotation Lock', iconName: 'rotation-locked-symbolic', toggleMode: true,
        });
        this._settings.bind('rotation-locked', this._rotationLock, 'checked',
            Gio.SettingsBindFlags.DEFAULT);
        const syncRotation = () => {
            const locked = this._settings.get_boolean('rotation-locked');
            this._rotationLock.subtitle = locked ? 'Keep current orientation' : 'Rotate automatically';
            this._rotationLock.iconName = locked ? 'rotation-locked-symbolic' : 'rotation-allowed-symbolic';
        };
        this._rotationSignal = this._settings.connect('changed::rotation-locked', syncRotation);
        syncRotation();
        this._settingsLauncher = new QuickSettings.QuickToggle({
            title: 'Settings', iconName: 'org.gnome.Settings-symbolic',
            toggleMode: false,
        });
        this._settingsLauncher.connect('clicked', () => this._openSettings());
        this._androidLauncher = new QuickSettings.QuickToggle({
            title: 'Restart into Android', iconName: 'system-reboot-symbolic',
            toggleMode: false,
        });
        this._androidLauncher.subtitle = 'Keep Ubuntu files and open native Android';
        this._androidLauncher.connect('clicked', () => this._openAndroidSwitch());
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
        this._autoSuspend = new QuickSettings.QuickToggle({
            title: 'Automatic Suspend', iconName: 'weather-clear-night-symbolic',
            toggleMode: true,
        });
        this._autoSuspend.subtitle = 'Sleep after the screen locks';
        this._autoSuspend.visible = false;
        this._autoSuspend.connect('clicked', () => {
            this._displayRequest(['suspend', 'automatic',
                this._autoSuspend.checked ? 'on' : 'off'], () => this._refreshDisplay());
        });
        this._flashlight = new QuickSettings.QuickToggle({
            title: 'Flashlight', iconName: 'media-flash-symbolic', toggleMode: true,
        });
        this._flashlight.visible = false;
        this._flashlight.connect('clicked', () => {
            this._displayRequest(['flashlight', this._flashlight.checked ? 'on' : 'off'],
                () => this._refreshDisplay());
        });
        this._flashlightBrightness = new QuickSettings.QuickSlider({
            iconName: 'media-flash-symbolic', iconLabel: 'Flashlight brightness',
        });
        this._flashlightBrightness.slider.accessible_name = 'Flashlight brightness';
        this._flashlightBrightness.visible = false;
        this._flashlightBrightness.slider.connect('notify::value', () => {
            if (this._updatingDisplay)
                return;
            if (this._flashlightBrightnessTimer)
                GLib.Source.remove(this._flashlightBrightnessTimer);
            this._flashlightBrightnessTimer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 200, () => {
                this._flashlightBrightnessTimer = 0;
                const value = Math.max(5, Math.round(this._flashlightBrightness.slider.value * 100));
                this._displayRequest(['flashlight', 'brightness', String(value)]);
                return GLib.SOURCE_REMOVE;
            });
        });
        this._powerIndicator.quickSettingsItems.push(
            this._settingsLauncher, this._androidLauncher, this._brightness,
            this._rotationLock, this._keepAwake, this._autoSuspend,
            this._flashlight, this._flashlightBrightness);
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
        this._flashlightLeaseTimer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 5, () => {
            if (this._flashlight.checked)
                this._displayRequest(['flashlight', 'renew']);
            return GLib.SOURCE_CONTINUE;
        });
        this._refreshDisplay();
    }

    disable() {
        if (this._flashlight?.checked)
            this._displayRequest(['flashlight', 'off']);
        this._displayActive = false;
        if (this._rotationSignal)
            this._settings.disconnect(this._rotationSignal);
        this._rotationSignal = 0;
        for (const {item, signal, wasVisible} of this._hiddenStock ?? []) {
            item.disconnect(signal);
            item.visible = wasVisible;
        }
        this._hiddenStock = [];
        if (this._flashlightBrightnessTimer)
            GLib.Source.remove(this._flashlightBrightnessTimer);
        if (this._flashlightLeaseTimer)
            GLib.Source.remove(this._flashlightLeaseTimer);
        if (this._brightnessTimer)
            GLib.Source.remove(this._brightnessTimer);
        if (this._fullscreenTimer)
            GLib.Source.remove(this._fullscreenTimer);
        this._brightnessTimer = this._fullscreenTimer = 0;
        this._flashlightBrightnessTimer = this._flashlightLeaseTimer = 0;
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
