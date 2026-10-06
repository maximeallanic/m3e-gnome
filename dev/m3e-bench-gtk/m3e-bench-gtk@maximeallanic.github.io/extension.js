// Extension of the GTK motion bench. Only enabled in the nested Shell started by nested.sh (through run.sh).
// Exposes the bench D-Bus API (name and path from the "m3e-bench-name" / "m3e-bench-path" keys of metadata.json) on
// the private session bus:
//   Ping()                  -> 'pong' (Shell ready)
//   Run(scenario)           -> starts scenario.py for that scenario (returns at once)
//   Result(scenario)        -> '' while it runs, then a JSON {type, ok, exit_code, scenario}
//   State()                 -> JSON {overview, focus}
//   Windows()               -> JSON [{id, title, wm_class, x, y, w, h}] (window frames, logical px)
//   Maximize(wm_class)      -> maximizes and activates the windows of that WM class ('' = all)
//   Pointer(x, y)           -> moves the virtual pointer (absolute stage coordinates)
//   Click(button, pressed)  -> presses (true) or releases (false) a button (1 left, 2 middle)
//   Wheel(dx, dy)           -> smooth scroll (wheel units)
//   Key(keyval, pressed)    -> presses / releases a key (virtual keyboard)
//   Capture(path)           -> PNG screenshot of the virtual screen
// The devices are virtual Clutter devices of the nested Shell: nothing leaves the bench (no uinput, no real session).
//
// GTK stacking: at enable(), before any application starts, the extension installs the GTK configuration prepared by
// stage.py (directory $M3E_BENCH_GTK_STAGE) into the PRIVATE XDG directories of the Shell: config/gtk-3.0 and
// config/gtk-4.0 are copied into $XDG_CONFIG_HOME, data/themes and data/icons are linked in $XDG_DATA_HOME. It refuses
// to write anywhere that is not under $M3E_BENCH_TMP (the private directory created by nested.sh).
// The applications inherit the environment of the Shell (private XDG_*, session bus); WAYLAND_DISPLAY is read from
// the Shell's own environment, where mutter sets the name of its socket.
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

import {startLogindGuard, stopLogindGuard} from './logind-guard.js';
import {stageGtk} from './gtk-stage.js';

const NAME_KEY = 'm3e-bench-name';
const PATH_KEY = 'm3e-bench-path';
const SCENARIO = /^[a-z0-9]+$/;

const now = () => GLib.get_monotonic_time();

const xml = name => `
<node>
  <interface name="${name}">
    <method name="Ping"><arg type="s" direction="out" name="reply"/></method>
    <method name="Run"><arg type="s" direction="in" name="scenario"/></method>
    <method name="Result"><arg type="s" direction="in" name="scenario"/><arg type="s" direction="out" name="json"/></method>
    <method name="State"><arg type="s" direction="out" name="json"/></method>
    <method name="Windows"><arg type="s" direction="out" name="json"/></method>
    <method name="Maximize"><arg type="s" direction="in" name="wm_class"/><arg type="i" direction="out" name="count"/></method>
    <method name="Pointer"><arg type="d" direction="in" name="x"/><arg type="d" direction="in" name="y"/></method>
    <method name="Click"><arg type="u" direction="in" name="button"/><arg type="b" direction="in" name="pressed"/></method>
    <method name="Wheel"><arg type="d" direction="in" name="dx"/><arg type="d" direction="in" name="dy"/></method>
    <method name="Key"><arg type="u" direction="in" name="keyval"/><arg type="b" direction="in" name="pressed"/></method>
    <method name="Capture"><arg type="s" direction="in" name="path"/><arg type="s" direction="out" name="name"/></method>
  </interface>
</node>`;

export default class M3eBenchGtk extends Extension {
    enable() {
        startLogindGuard().catch(e => console.error(`m3e-bench-gtk: logind guard: ${e.message}\n${e.stack}`));
        stageGtk();
        this._dbusName = this.metadata[NAME_KEY];
        this._dbusPath = this.metadata[PATH_KEY];
        this._runs = new Map();
        const seat = Clutter.get_default_backend().get_default_seat();
        this._pointer = seat.create_virtual_device(Clutter.InputDeviceType.POINTER_DEVICE);
        this._keyboard = seat.create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
        this._exported = Gio.DBusExportedObject.wrapJSObject(xml(this._dbusName), this);
        this._exported.export(Gio.DBus.session, this._dbusPath);
        // Start-up overview: hidden as soon as a window appears (otherwise keystrokes go to its search).
        this._windowCreatedId = global.display.connect('window-created', (_d, w) => {
            GLib.timeout_add(GLib.PRIORITY_DEFAULT, 300, () => {
                Main.overview.hide();
                w.activate(global.get_current_time());
                return GLib.SOURCE_REMOVE;
            });
        });
        const own = () => {
            Main.overview.hide();
            if (!this._ownerId)
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
        if (this._windowCreatedId)
            global.display.disconnect(this._windowCreatedId);
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
        const scripts = GLib.getenv('M3E_BENCH_GTK_SCRIPTS');
        const out = GLib.getenv('M3E_BENCH_OUT');
        const display = GLib.getenv('WAYLAND_DISPLAY');
        if (!SCENARIO.test(scenario) || !scripts || !out || !display)
            throw new Error(`Run ${scenario}: invalid scenario, or M3E_BENCH_GTK_SCRIPTS / M3E_BENCH_OUT / WAYLAND_DISPLAY missing`);
        if (this._runs.get(scenario)?.result === null)
            return;
        const launcher = new Gio.SubprocessLauncher({flags: Gio.SubprocessFlags.STDERR_MERGE});
        launcher.set_stdout_file_path(`${out}/driver-${scenario}.log`);
        launcher.setenv('WAYLAND_DISPLAY', display, true);
        launcher.setenv('M3E_BENCH_GTK_NAME', this._dbusName, true);
        launcher.setenv('M3E_BENCH_GTK_PATH', this._dbusPath, true);
        const process = launcher.spawnv(['python3', `${scripts}/scenario.py`, out, scenario, scripts]);
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

    State() {
        return JSON.stringify({overview: Main.overview.visible, focus: global.display.focus_window?.get_wm_class() ?? null});
    }

    Windows() {
        if (Main.overview.visible)
            Main.overview.hide();
        return JSON.stringify(global.get_window_actors().map(a => a.meta_window)
            .filter(w => w.get_window_type() === Meta.WindowType.NORMAL)
            .map(w => {
                const r = w.get_frame_rect();
                return {id: w.get_id(), title: w.get_title() ?? '', wm_class: w.get_wm_class() ?? '',
                    x: r.x, y: r.y, w: r.width, h: r.height};
            }));
    }

    Maximize(wmClass) {
        let count = 0;
        for (const actor of global.get_window_actors()) {
            const w = actor.meta_window;
            if (wmClass && w.get_wm_class() !== wmClass)
                continue;
            try {
                w.maximize();  // mutter 50: no argument
            } catch {
                w.maximize(Meta.MaximizeFlags.BOTH);
            }
            w.activate(global.get_current_time());
            count++;
        }
        return count;
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
