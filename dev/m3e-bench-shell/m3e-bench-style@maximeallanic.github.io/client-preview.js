// Test Wayland client of the style bench (surfaces "previews", "alttab", "workspaces"): an empty Gtk 4 window,
// titled ARGV[0] (default "Bench test window"). Started by surfaces/client-window.js in the nested Shell only
// (WAYLAND_DISPLAY of the nested Shell, private XDG_RUNTIME_DIR of the bench), killed by PID when the surface
// closes. Start nothing else here.
imports.gi.versions.Gtk = '4.0';
const {GLib, Gtk} = imports.gi;

Gtk.init();
const title = ARGV[0] || 'Bench test window';
const window = new Gtk.Window({title, default_width: 900, default_height: 560});
window.set_child(new Gtk.Label({label: 'M3E bench test window'}));
const loop = GLib.MainLoop.new(null, false);
window.connect('close-request', () => {
    loop.quit();
    return false;
});
window.present();
loop.run();
