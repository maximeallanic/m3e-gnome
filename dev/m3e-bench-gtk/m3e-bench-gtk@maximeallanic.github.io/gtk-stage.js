// Installs the GTK configuration prepared by stage.py into the PRIVATE XDG directories of the nested Shell.
// Layout of $M3E_BENCH_GTK_STAGE:  config/gtk-3.0/*, config/gtk-4.0/*  (files copied into $XDG_CONFIG_HOME)
//                                  data/themes, data/icons             (linked in $XDG_DATA_HOME)
// Runs at enable(), before any application starts. Refuses to write outside $M3E_BENCH_TMP (nested.sh's private dir).
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

function privateDir(path) {
    const tmp = GLib.getenv('M3E_BENCH_TMP');
    if (!tmp || !path.startsWith(`${tmp}/`))
        throw new Error(`refusing to write outside the private directory: ${path} (M3E_BENCH_TMP=${tmp})`);
    return path;
}

function listFiles(dir) {
    const names = [];
    const e = dir.enumerate_children('standard::name,standard::type', Gio.FileQueryInfoFlags.NONE, null);
    for (let info = e.next_file(null); info; info = e.next_file(null))
        if (info.get_file_type() === Gio.FileType.REGULAR || info.get_file_type() === Gio.FileType.SYMBOLIC_LINK)
            names.push(info.get_name());
    return names;
}

export function stageGtk() {
    const stage = GLib.getenv('M3E_BENCH_GTK_STAGE');
    if (!stage)
        throw new Error('M3E_BENCH_GTK_STAGE is not set');
    const config = privateDir(GLib.get_user_config_dir());
    const data = privateDir(GLib.get_user_data_dir());
    for (const dir of ['gtk-3.0', 'gtk-4.0']) {
        const from = Gio.File.new_for_path(`${stage}/config/${dir}`);
        const to = Gio.File.new_for_path(`${config}/${dir}`);
        GLib.mkdir_with_parents(to.get_path(), 0o755);
        for (const name of listFiles(from))
            from.get_child(name).copy(to.get_child(name), Gio.FileCopyFlags.OVERWRITE, null, null);
    }
    GLib.mkdir_with_parents(data, 0o755);
    for (const dir of ['themes', 'icons']) {
        const link = Gio.File.new_for_path(`${data}/${dir}`);
        if (!link.query_exists(null))
            link.make_symbolic_link(`${stage}/data/${dir}`, null);
    }
}
