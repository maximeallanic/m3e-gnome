// Test Wayland client (client-preview.js, gjs + Gtk 4) started in the nested Shell, one process per window
// (Alt+Tab shows one entry per app); the subprocess handles are kept in ctx.clients and all killed by PID.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

import {wait, waitUntil} from '../tools.js';

const SOCKET_PATTERN = /^m3e-bench-\d+$/;

// Wayland socket of the nested Shell: m3e-bench-<pid> (nested.sh) inside the bench's PRIVATE XDG_RUNTIME_DIR.
// nested.sh starts the Shell with --wayland-display m3e-bench-<pid>; mutter normally exports that name in the
// Shell's own WAYLAND_DISPLAY, which is read first; if it is missing the socket is looked up by name in the private runtime
// directory. Refused if the runtime directory is the real
// session's (/run/user/<uid>) or if the name is not the bench's.
function nestedSocket() {
    const run = GLib.getenv('XDG_RUNTIME_DIR');
    if (!run || run.startsWith('/run/user/'))
        throw new Error(`XDG_RUNTIME_DIR is not private: ${run}`);
    let name = GLib.getenv('WAYLAND_DISPLAY');
    if (!name || !SOCKET_PATTERN.test(name)) {
        const dir = Gio.File.new_for_path(run);
        const list = dir.enumerate_children('standard::name', Gio.FileQueryInfoFlags.NONE, null);
        name = null;
        for (let info; (info = list.next_file(null));) {
            if (SOCKET_PATTERN.test(info.get_name()))
                name = info.get_name();
        }
    }
    if (!name || !SOCKET_PATTERN.test(name) || !GLib.file_test(`${run}/${name}`, GLib.FileTest.EXISTS))
        throw new Error(`Wayland socket of the nested Shell not found in ${run}`);
    return {run, name};
}

// Test window titled `title`; returns its MetaWindow once painted and sized.
export async function launchClient(ctx, title = 'Bench test window') {
    const {run, name} = nestedSocket();
    const launcher = new Gio.SubprocessLauncher({flags: Gio.SubprocessFlags.STDOUT_SILENCE});
    launcher.setenv('XDG_RUNTIME_DIR', run, true);
    launcher.setenv('WAYLAND_DISPLAY', name, true);
    launcher.setenv('GDK_BACKEND', 'wayland', true);
    launcher.setenv('GSK_RENDERER', 'cairo', true);
    launcher.setenv('GTK_A11Y', 'none', true);
    launcher.unsetenv('DISPLAY');
    // This module lives in <extension>/surfaces/, the client script in <extension>/.
    const dir = GLib.path_get_dirname(GLib.path_get_dirname(GLib.filename_from_uri(import.meta.url)[0]));
    const script = GLib.build_filenamev([dir, 'client-preview.js']);
    let window = null, client = null;
    const createdId = global.display.connect('window-created', (d, w) => {
        if (client && `${w.get_pid()}` === client.get_identifier())
            window = w;
    });
    try {
        client = launcher.spawnv(['gjs', script, title]);
        ctx.clients = [...ctx.clients ?? [], client];
        console.log(`m3e-bench preview client: PID ${client.get_identifier()} on ${run}/${name}`);
        window = await waitUntil(() => window ?? global.get_window_actors().map(a => a.meta_window)
            .find(w => `${w.get_pid()}` === client.get_identifier()), 10000);
    } finally {
        global.display.disconnect(createdId);
    }
    if (!window)
        throw new Error('test window did not appear');
    // Window painted and sized before the overview opens: a zero-size preview gives WindowPreview an infinite scale
    // (translation +-inf seen in shell.log, then the nested Shell stopped).
    const ready = await waitUntil(() => {
        const a = window.get_compositor_private();
        const r = window.get_frame_rect();
        return a?.visible && a.width > 0 && a.height > 0 && r.width > 0 && r.height > 0;
    }, 5000);
    if (!ready)
        throw new Error('test window without a size');
    await wait(500);
    return window;
}

export function killClients(ctx) {
    const clients = ctx.clients ?? [];
    ctx.clients = [];
    for (const c of clients) {
        console.log(`m3e-bench preview client: stopping PID ${c.get_identifier()}`);
        c.force_exit();
    }
}
