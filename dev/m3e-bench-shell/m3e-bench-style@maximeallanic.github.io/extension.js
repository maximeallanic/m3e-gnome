// Shell style bench extension: exposes io.github.maximeallanic.M3eBenchStyle on the session bus (of the nested
// Shell), puts the stock sheet and the candidate sheet of the requested mode, then captures the surfaces of
// surfaces/index.js. Must never be enabled in a real session.
//
// Scenario "<surface>:<mode>" (e.g. bar:dark). Files read from <extension>/sheets/: stock-<mode>.css (default
// sheet) and candidate-<mode>.css (the theme's sheet). Output in $M3E_BENCH_STYLE_OUT/<mode>/:
// shell-<surface>-<state>.png, layout-shell-<surface>-<state>.json, shell-<surface>-<state>-screen.json.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Shell from 'gi://Shell';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

import {startLogindGuard, stopLogindGuard} from './logind-guard.js';
import {SURFACES} from './surfaces/index.js';

const BUS_NAME = 'io.github.maximeallanic.M3eBenchStyle';
const OBJECT_PATH = '/io/github/maximeallanic/M3eBenchStyle';
const XML = `
<node>
  <interface name="${BUS_NAME}">
    <method name="Run"><arg type="s" direction="in" name="scenario"/></method>
    <method name="Result"><arg type="s" direction="in" name="scenario"/><arg type="s" direction="out" name="json"/></method>
    <method name="Ping"><arg type="s" direction="out" name="response"/></method>
  </interface>
</node>`;

const MODES = ['dark', 'light'];
// Bench states -> St pseudo-classes (normal: none).
const PSEUDO = {hover: 'hover', pressed: 'active', focus: 'focus', active: 'checked', disabled: 'insensitive'};
// Witness background of the scene, under the bar and the surfaces (bench colour, outside the palette: the only
// hardcoded witness).
const WITNESS_BACKGROUND = '#808080';
// Bounded wait for frames: a still scene no longer paints (NOTES.md of the motion bench).
const FRAMES_TIMEOUT_MS = 2000;
const OVERVIEW_TIMEOUT_MS = 5000;
// Asynchronous reload of the icons after a state change (see _play).
const ICONS_DELAY_MS = 250;

export default class StyleBench extends Extension {
    enable() {
        // Before anything else: cut the nested Shell's link to the REAL logind session (Lock/Unlock signals,
        // _loginSession, SetLockedHint), for the whole life of the nested Shell and not only during the lock
        // scenarios (logind-guard.js, shared with the extensions bench). The lock scenarios expect this result.
        startLogindGuard().catch(e => logError(e, 'm3e-bench: logind guard'));
        this._results = new Map();
        this._connections = new Set();
        this._timeouts = new Set();
        this._running = false;
        // St transitions off (transition-duration of the stock sheets, e.g. .toggle-switch 100 ms): otherwise a
        // capture taken two frames after a state change lands in the middle of a transition.
        St.Settings.get().inhibit_animations();
        this._animationsOff = true;
        // Plain background under the bar (above the wallpaper, under the windows and the chrome).
        this._background = new St.Widget({
            name: 'm3e-bench-style-background', reactive: false, x: 0, y: 0,
            width: global.stage.width, height: global.stage.height,
            style: `background-color: ${WITNESS_BACKGROUND};`,
        });
        global.window_group.add_child(this._background);

        this._exported = Gio.DBusExportedObject.wrapJSObject(XML, this);
        this._exported.export(Gio.DBus.session, OBJECT_PATH);
        // Name taken after start-up (scene displayed), like the other bench extension.
        const own = () => {
            if (this._ownerId || !this._exported)
                return;
            this._ownerId = Gio.bus_own_name_on_connection(Gio.DBus.session, BUS_NAME,
                Gio.BusNameOwnerFlags.NONE, null, null);
        };
        if (!Main.layoutManager._startingUp && global.stage.mapped)
            own();
        else
            this._startupId = Main.layoutManager.connect('startup-complete', own);
    }

    disable() {
        stopLogindGuard();
        if (this._startupId)
            Main.layoutManager.disconnect(this._startupId);
        this._startupId = null;
        if (this._ownerId)
            Gio.bus_unown_name(this._ownerId);
        this._ownerId = null;
        this._exported?.unexport();
        this._exported = null;
        for (const id of this._connections ?? [])
            global.stage.disconnect(id);
        this._connections = null;
        for (const id of this._timeouts ?? [])
            GLib.source_remove(id);
        this._timeouts = null;
        this._background?.destroy();
        this._background = null;
        this._results = null;
        if (this._animationsOff)
            St.Settings.get().uninhibit_animations();
        this._animationsOff = false;
    }

    Ping() {
        return 'pong';
    }

    Run(scenario) {
        this._results.delete(scenario);
        this._play(scenario).then(
            r => this._results?.set(scenario, JSON.stringify(r)),
            e => this._results?.set(scenario, JSON.stringify({type: 'error', message: `${e}`, stack: `${e?.stack ?? ''}`})));
    }

    Result(scenario) {
        return this._results?.get(scenario) ?? '';
    }

    _connectPaint(callback) {
        const stage = global.stage;
        const id = stage.connect('after-paint', callback);
        this._connections.add(id);
        return () => {
            if (this._connections?.delete(id))
                stage.disconnect(id);
        };
    }

    // Resolves after n painted frames, or after FRAMES_TIMEOUT_MS (still scene); returns the number painted.
    _waitFrames(n) {
        return new Promise(resolve => {
            let painted = 0, timeoutId = 0, done = false;
            const finish = () => {
                if (done)
                    return;
                done = true;
                disconnect();
                if (timeoutId && this._timeouts?.delete(timeoutId))
                    GLib.source_remove(timeoutId);
                resolve(painted);
            };
            const disconnect = this._connectPaint(() => {
                if (++painted >= n)
                    finish();
                else
                    global.stage.queue_redraw();
            });
            timeoutId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, FRAMES_TIMEOUT_MS, () => {
                this._timeouts?.delete(timeoutId);
                timeoutId = 0;
                finish();
                return GLib.SOURCE_REMOVE;
            });
            this._timeouts.add(timeoutId);
            global.stage.queue_redraw();
        });
    }

    _wait(ms) {
        return new Promise(resolve => {
            const id = GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
                this._timeouts?.delete(id);
                resolve();
                return GLib.SOURCE_REMOVE;
            });
            this._timeouts.add(id);
        });
    }

    async _closeOverview() {
        if (!Main.overview.visible)
            return;
        await new Promise(resolve => {
            let timeoutId = 0;
            const id = Main.overview.connect('hidden', () => finish());
            const finish = () => {
                Main.overview.disconnect(id);
                if (timeoutId && this._timeouts?.delete(timeoutId))
                    GLib.source_remove(timeoutId);
                timeoutId = 0;
                resolve();
            };
            timeoutId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, OVERVIEW_TIMEOUT_MS, () => {
                this._timeouts?.delete(timeoutId);
                timeoutId = 0;
                finish();
                return GLib.SOURCE_REMOVE;
            });
            this._timeouts.add(timeoutId);
            Main.overview.hide();
        });
        if (Main.overview.visible)
            throw new Error('the overview does not close');
    }

    // Puts the theme of `mode`: stock sheet as the default stylesheet and the candidate sheet as the theme
    // stylesheet; with `stockOnly`, the stock sheet alone (reference of the surfaces that compare the candidate
    // with the stock rendering in the same run).
    _setTheme(mode, stockOnly = false) {
        const sheet = name => {
            const f = Gio.File.new_for_path(`${this.path}/sheets/${name}`);
            if (!f.query_exists(null))
                throw new Error(`missing sheet: ${f.get_path()}`);
            return f;
        };
        const theme = new St.Theme({
            default_stylesheet: sheet(`stock-${mode}.css`),
            theme_stylesheet: stockOnly ? null : sheet(`candidate-${mode}.css`),
        });
        St.ThemeContext.get_for_stage(global.stage).set_theme(theme);
    }

    // ctx.useSheet('stock' | 'candidate'): switches the whole theme and waits for two painted frames.
    async _useSheet(mode, which) {
        if (which !== 'stock' && which !== 'candidate')
            throw new Error(`unknown sheet: ${which}`);
        this._setTheme(mode, which === 'stock');
        const n = await this._waitFrames(2);
        if (n < 2)
            throw new Error(`${which} sheet: ${n} frame(s) painted out of 2 in ${FRAMES_TIMEOUT_MS} ms`);
    }

    _scale() {
        const monitor = global.display.get_monitor_scale(global.display.get_primary_monitor());
        const theme = St.ThemeContext.get_for_stage(global.stage).scale_factor;
        return {monitor, theme};
    }

    _capture(path) {
        const shot = new Shell.Screenshot();
        const stream = Gio.File.new_for_path(path).replace(null, false, Gio.FileCreateFlags.NONE, null);
        return new Promise((resolve, reject) => {
            shot.screenshot(false, stream, (o, res) => {
                try {
                    o.screenshot_finish(res);
                    stream.close(null);
                    resolve();
                } catch (e) {
                    try {
                        stream.close(null);
                    } catch {}
                    reject(e);
                }
            });
        });
    }

    _rectangle(actor, margin = 0) {
        const r = actor.get_transformed_extents();
        const x0 = Math.max(0, r.origin.x - margin), y0 = Math.max(0, r.origin.y - margin);
        const x1 = Math.min(global.stage.width, r.origin.x + r.size.width + margin);
        const y1 = Math.min(global.stage.height, r.origin.y + r.size.height + margin);
        const round = v => Math.round(v * 100) / 100;
        return {x: round(x0), y: round(y0), w: round(x1 - x0), h: round(y1 - y0)};
    }

    async _play(scenario) {
        const [surface, mode, ...rest] = scenario.split(':');
        const surf = SURFACES[surface];
        if (!surf || !MODES.includes(mode) || rest.length)
            return {type: 'error', message: `unknown scenario: ${scenario} (expected <surface>:<dark|light>)`};
        if (this._running)
            return {type: 'error', message: 'a scenario is already running'};
        const root = GLib.getenv('M3E_BENCH_STYLE_OUT');
        if (!root)
            return {type: 'error', message: 'M3E_BENCH_STYLE_OUT is not set'};
        this._running = true;
        const folder = `${root}/${mode}`;
        GLib.mkdir_with_parents(folder, 0o755);
        const ctx = {mode, surface, stage: global.stage, waitFrames: n => this._waitFrames(n),
            useSheet: which => this._useSheet(mode, which)};
        // Two painted frames required before every capture: fewer = style or pseudo-classes maybe not on screen
        // yet, the capture is worthless (error rather than a wrong measurement).
        const frames = [];
        const twoFrames = async what => {
            const n = await this._waitFrames(2);
            frames.push(n);
            if (n < 2)
                throw new Error(`${what}: ${n} frame(s) painted out of 2 in ${FRAMES_TIMEOUT_MS} ms`);
        };
        let opened = false, pseudo = [];
        try {
            // Virtual screen at scale 1: 1 dp = 1 px (spec section 5); otherwise the measurements are meaningless.
            const scale = this._scale();
            if (scale.monitor !== 1 || scale.theme !== 1)
                throw new Error(`screen scale is not 1: ${JSON.stringify(scale)}`);
            await this._closeOverview();
            this._background.set_size(global.stage.width, global.stage.height);
            this._setTheme(mode);
            await twoFrames('theme set');
            opened = true;
            await surf.open(ctx);
            await twoFrames('surface open');
            const files = [];
            for (const state of surf.states) {
                const cells = surf.cells(ctx);
                const pc = PSEUDO[state];
                if (pc) {
                    for (const c of cells) {
                        c.actor.add_style_pseudo_class(pc);
                        pseudo.push([c.actor, pc]);
                    }
                }
                await twoFrames(`state ${state}`);
                // Symbolic icons recoloured by the state (e.g. on_primary of the selected button): St reloads them
                // asynchronously, the icon may be missing two frames later (observed: quick settings button without
                // icons, in light mode, one time in four). Delay, then two more frames.
                await this._wait(ICONS_DELAY_MS);
                await twoFrames(`state ${state} (icons)`);
                const name = `shell-${surface}-${state}`;
                await this._capture(`${folder}/${name}.png`);
                const layout = {
                    toolkit: 'shell',
                    cells: cells.map(c => ({row: c.row, state, ...this._rectangle(c.actor, c.margin ?? 0)})),
                };
                GLib.file_set_contents(`${folder}/layout-${name}.json`, JSON.stringify(layout, null, 1));
                GLib.file_set_contents(`${folder}/${name}-screen.json`,
                    JSON.stringify({screen: {scale: scale.monitor}, screen_detail: {...scale,
                        width: global.stage.width, height: global.stage.height}}));
                files.push(`${name}.png`, `layout-${name}.json`, `${name}-screen.json`);
                for (const [a, p] of pseudo)
                    a.remove_style_pseudo_class(p);
                pseudo = [];
            }
            return {type: 'capture', ok: true, files, painted_frames: frames};
        } finally {
            for (const [a, p] of pseudo)
                a.remove_style_pseudo_class(p);
            try {
                if (opened)
                    await surf.close(ctx);
            } finally {
                this._running = false;
            }
        }
    }
}
