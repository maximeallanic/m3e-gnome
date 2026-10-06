// Installs what dev/screenshots/stage.py prepared into the PRIVATE XDG directories of the nested Shell, then loads
// the rendered Shell theme like the user-theme extension does. Runs at enable(), before any application starts.
// Layout of $M3E_SHOTS_STAGE:  overlay/config/**  -> copied into $XDG_CONFIG_HOME (GTK 3/4 stacks, user-dirs...)
//                              overlay/data/**    -> copied into $XDG_DATA_HOME (Ptyxis palette)
//                              gnome-shell.css    -> the Shell theme stylesheet
// Refuses to write anywhere that is not under $M3E_BENCH_TMP (the private directory created by nested.sh).
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

function privateDir(path) {
    const tmp = GLib.getenv('M3E_BENCH_TMP');
    if (!tmp || !path.startsWith(`${tmp}/`))
        throw new Error(`refusing to write outside the private directory: ${path} (M3E_BENCH_TMP=${tmp})`);
    return path;
}

function copyTree(from, to) {
    GLib.mkdir_with_parents(to.get_path(), 0o755);
    const children = from.enumerate_children('standard::name,standard::type', Gio.FileQueryInfoFlags.NONE, null);
    for (let info = children.next_file(null); info; info = children.next_file(null)) {
        const source = from.get_child(info.get_name());
        const target = to.get_child(info.get_name());
        if (info.get_file_type() === Gio.FileType.DIRECTORY)
            copyTree(source, target);
        else
            source.copy(target, Gio.FileCopyFlags.OVERWRITE, null, null);
    }
}

export function stageOverlay() {
    const stage = GLib.getenv('M3E_SHOTS_STAGE');
    if (!stage)
        throw new Error('M3E_SHOTS_STAGE is not set');
    for (const [name, dir] of [['config', GLib.get_user_config_dir()], ['data', GLib.get_user_data_dir()]]) {
        const from = Gio.File.new_for_path(`${stage}/overlay/${name}`);
        if (from.query_exists(null))
            copyTree(from, Gio.File.new_for_path(privateDir(dir)));
    }
}

// Same two calls as the user-theme extension.
export function loadShellTheme() {
    const sheet = Gio.File.new_for_path(`${GLib.getenv('M3E_SHOTS_STAGE')}/gnome-shell.css`);
    if (!sheet.query_exists(null))
        throw new Error(`Shell theme missing: ${sheet.get_path()}`);
    Main.setThemeStylesheet(sheet.get_path());
    Main.loadTheme();
}
