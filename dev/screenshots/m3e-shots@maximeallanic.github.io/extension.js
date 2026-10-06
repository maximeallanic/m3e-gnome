// Capture driver of dev/screenshots. Only enabled in the nested Shell started by nested.sh (through capture.sh).
// Exposes the D-Bus API (name and path from "m3e-bench-name" / "m3e-bench-path" of metadata.json) on the private
// session bus:
//   Ping()                  -> 'pong' (Shell ready)
//   Run(scenario)           -> starts shots.py for that scenario (returns at once)
//   Result(scenario)        -> '' while it runs, then a JSON {type, ok, exit_code, scenario}
//   Windows()               -> JSON [{id, title, wm_class, x, y, w, h}] (window frames, logical px)
//   Place(id, x, y, w, h)   -> unmaximizes, moves and resizes a window, then activates it
//   Activate(id)            -> gives a window the focus
//   Action(name, arg)       -> opens a Shell surface (actions.js)
//   Pointer / Click / Wheel / Key -> virtual pointer and keyboard of the nested Shell
//   Capture(path)           -> PNG of the whole virtual screen (no pointer)
// The devices are virtual Clutter devices of the nested Shell: nothing leaves it (no uinput, no real session).
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

import {startLogindGuard, stopLogindGuard} from './logind-guard.js';
import {stageOverlay, loadShellTheme} from './stage.js';
import {runAction} from './actions.js';

const SCENARIO = /^[a-z0-9-]+$/;
const now = () => GLib.get_monotonic_time();

const xml = name => `
<node>
  <interface name="${name}">
    <method name="Ping"><arg type="s" direction="out" name="reply"/></method>
    <method name="Run"><arg type="s" direction="in" name="scenario"/></method>
    <method name="Result"><arg type="s" direction="in" name="scenario"/><arg type="s" direction="out" name="json"/></method>
    <method name="Windows"><arg type="s" direction="out" name="json"/></method>
    <method name="Place"><arg type="u" direction="in" name="id"/><arg type="i" direction="in" name="x"/><arg type="i" direction="in" name="y"/><arg type="i" direction="in" name="w"/><arg type="i" direction="in" name="h"/></method>
    <method name="Activate"><arg type="u" direction="in" name="id"/></method>
    <method name="Action"><arg type="s" direction="in" name="name"/><arg type="s" direction="in" name="arg"/></method>
    <method name="Pointer"><arg type="d" direction="in" name="x"/><arg type="d" direction="in" name="y"/></method>
    <method name="Click"><arg type="u" direction="in" name="button"/><arg type="b" direction="in" name="pressed"/></method>
    <method name="Wheel"><arg type="d" direction="in" name="dx"/><arg type="d" direction="in" name="dy"/></method>
    <method name="Key"><arg type="u" direction="in" name="keyval"/><arg type="b" direction="in" name="pressed"/></method>
    <method name="Capture"><arg type="s" direction="in" name="path"/><arg type="s" direction="out" name="name"/></method>
  </interface>
</node>`;

export default class M3eShots extends Extension {
    enable() {
        startLogindGuard().catch(e => console.error(`m3e-shots: logind guard: ${e.message}\n${e.stack}`));
        stageOverlay();
        loadShellTheme();
        this._dbusName = this.metadata['m3e-bench-name'];
        this._dbusPath = this.metadata['m3e-bench-path'];
        this._runs = new Map();
        const seat = Clutter.get_default_backend().get_default_seat();
        this._pointer = seat.create_virtual_device(Clutter.InputDeviceType.POINTER_DEVICE);
        this._keyboard = seat.create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
        this._exported = Gio.DBusExportedObject.wrapJSObject(xml(this._dbusName), this);
        this._exported.export(Gio.DBus.session, this._dbusPath);
        const own = () => {
            if (this._ownerId)
                return;
            Main.overview.hide();
            this._ownerId = Gio.bus_own_name_on_connection(Gio.DBus.session, this._dbusName,
                Gio.BusNameOwnerFlags.NONE, null, null);
        };
        if (!Main.layoutManager._startingUp)
            own();
        else
            this._startupId = Main.layoutManager.connect('startup-complete', own);
    }

    disable() {
        stopLogindGuard();
        if (this._startupId)
            Main.layoutManager.disconnect(this._startupId);
        if (this._ownerId)
            Gio.bus_unown_name(this._ownerId);
        this._exported?.unexport();
        for (const run of this._runs?.values() ?? [])
            run.process.force_exit();
        this._pointer = this._keyboard = null;
    }

    Ping() {
        return 'pong';
    }

    Run(scenario) {
        const scripts = GLib.getenv('M3E_SHOTS_SCRIPTS');
        const out = GLib.getenv('M3E_BENCH_OUT');
        const display = GLib.getenv('WAYLAND_DISPLAY');
        if (!SCENARIO.test(scenario) || !scripts || !out || !display)
            throw new Error(`Run ${scenario}: invalid scenario, or M3E_SHOTS_SCRIPTS / M3E_BENCH_OUT / WAYLAND_DISPLAY missing`);
        if (this._runs.get(scenario)?.result === null)
            return;
        const launcher = new Gio.SubprocessLauncher({flags: Gio.SubprocessFlags.STDERR_MERGE});
        launcher.set_stdout_file_path(`${out}/driver-${scenario}.log`);
        launcher.setenv('WAYLAND_DISPLAY', display, true);
        // Names read by dev/m3e-bench-gtk/driver.py, which shots.py reuses for the bus calls and the applications.
        launcher.setenv('M3E_BENCH_GTK_NAME', this._dbusName, true);
        launcher.setenv('M3E_BENCH_GTK_PATH', this._dbusPath, true);
        const process = launcher.spawnv(['python3', `${scripts}/shots.py`, out, scenario]);
        const run = {process, result: null};
        this._runs.set(scenario, run);
        process.wait_async(null, (p, res) => {
            p.wait_finish(res);
            const code = p.get_if_exited() ? p.get_exit_status() : -1;
            run.result = JSON.stringify({type: 'result', ok: code === 0, exit_code: code, scenario});
        });
    }

    Result(scenario) {
        return this._runs.get(scenario)?.result ?? '';
    }

    _window(id) {
        const actor = global.get_window_actors().find(a => a.meta_window.get_id() === id);
        if (!actor)
            throw new Error(`no window ${id}`);
        return actor.meta_window;
    }

    Windows() {
        return JSON.stringify(global.get_window_actors().map(a => a.meta_window)
            .filter(w => w.get_window_type() === Meta.WindowType.NORMAL)
            .map(w => {
                const r = w.get_frame_rect();
                return {id: w.get_id(), title: w.get_title() ?? '', wm_class: w.get_wm_class() ?? '',
                    x: r.x, y: r.y, w: r.width, h: r.height};
            }));
    }

    Place(id, x, y, w, h) {
        const win = this._window(id);
        if (win.is_maximized())
            win.unmaximize();
        win.move_resize_frame(false, x, y, w, h);
        win.activate(global.get_current_time());
    }

    Activate(id) {
        this._window(id).activate(global.get_current_time());
    }

    Action(name, arg) {
        runAction(name, arg);
    }

    Pointer(x, y) {
        this._pointer.notify_absolute_motion(now(), x, y);
    }

    Click(button, pressed) {
        this._pointer.notify_button(now(), button, pressed ? Clutter.ButtonState.PRESSED : Clutter.ButtonState.RELEASED);
    }

    Wheel(dx, dy) {
        this._pointer.notify_scroll_continuous(now(), dx, dy, Clutter.ScrollSource.WHEEL, Clutter.ScrollFinishFlags.NONE);
    }

    Key(keyval, pressed) {
        this._keyboard.notify_keyval(now(), keyval, pressed ? Clutter.KeyState.PRESSED : Clutter.KeyState.RELEASED);
    }

    CaptureAsync([path], invocation) {
        const shot = new Shell.Screenshot();
        const stream = Gio.File.new_for_path(path).replace(null, false, Gio.FileCreateFlags.NONE, null);
        shot.screenshot(false, stream, (o, res) => {
            try {
                o.screenshot_finish(res);
                stream.close(null);
                invocation.return_value(new GLib.Variant('(s)', [path]));
            } catch (e) {
                invocation.return_error_literal(Gio.DBusError, Gio.DBusError.FAILED, `${e}`);
            }
        });
    }
}
