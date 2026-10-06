// On-screen keyboard surface.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {wait, waitUntil} from '../tools.js';
import {TEXT_SIZE} from './common.js';

// screen-keyboard-enabled set in the NESTED SHELL's dconf database only: temporary XDG_CONFIG_HOME exported by
// nested.sh before dbus-run-session (the private bus's dconf-service writes into $TMP/config/dconf/user); refused
// if the configuration directory is the real session's. nested.sh's dconf guard (code 3) has the last word.
function benchA11ySettings() {
    const conf = GLib.get_user_config_dir();
    const real = GLib.build_filenamev([GLib.get_home_dir(), '.config']);
    if (!conf || conf === real || !(conf.startsWith(`${GLib.get_tmp_dir()}/`) || conf.startsWith('/tmp/')))
        throw new Error(`keyboard: configuration directory is not temporary (${conf}), setting refused`);
    return new Gio.Settings({schema_id: 'org.gnome.desktop.a11y.applications'});
}

// Visible keys (current page) of the keyboard: .keyboard-key buttons mapped on screen.
function visibleKeys(keyboard) {
    const keys = [];
    const walk = a => {
        for (const e of a.get_children()) {
            if (e.has_style_class_name?.('keyboard-key') && e.is_mapped() && e.width > 0)
                keys.push(e);
            walk(e);
        }
    };
    walk(keyboard);
    return keys;
}

export const KEYBOARD_SURFACES = {
    // On-screen keyboard: screen-keyboard-enabled = true in the nested Shell's dconf database
    // (benchA11ySettings), keyboard opened through the API (Main.layoutManager.keyboardIndex = primary screen,
    // Keyboard.open(true): without the rest delay), no typing. Background (#keyboard), normal key (letter, without
    // .default-key), special key (.default-key with an icon, e.g. delete); pressed key = "pressed" state (:active,
    // set by the Shell on click). Label and icon of the two keys at the bench size (inline style, colour measured).
    // Closing: close(true), setting restored to its previous value (the Shell then destroys the keyboard).
    // Background: test #keyboard (see open).
    keyboard: {
        open: async ctx => {
            const settings = benchA11ySettings();
            ctx.settings = settings;
            ctx.keyboardBefore = settings.get_boolean('screen-keyboard-enabled');
            settings.set_boolean('screen-keyboard-enabled', true);
            Gio.Settings.sync();
            const keyboard = await waitUntil(() => Main.keyboard.keyboardActor, 3000);
            if (!keyboard)
                throw new Error('keyboard: not created after screen-keyboard-enabled');
            Main.layoutManager.keyboardIndex = Main.layoutManager.primaryIndex;
            keyboard.open(true);
            if (!await waitUntil(() => keyboard.visible && keyboard.is_mapped() && keyboard.height > 0, 3000))
                throw new Error('keyboard: not shown');
            await wait(300);
            const keys = visibleKeys(keyboard);
            const normal = keys.find(t => !t.has_style_class_name('default-key') && /^\p{L}$/u.test(t.label ?? ''));
            const special = keys.find(t => t.has_style_class_name('default-key') &&
                !t.has_style_class_name('hide-key') && t.get_child() instanceof St.Icon);
            if (!normal || !special)
                throw new Error(`keyboard: keys not found (${keys.length} visible)`);
            normal.style = TEXT_SIZE;
            special.style = TEXT_SIZE;
            await wait(200);
            // Background measured on a test #keyboard (same id, on the witness background): the real keyboard, stuck
            // to the bottom and the sides of the screen, does not have enough free surroundings for the witness
            // background to be the majority.
            const background = new St.BoxLayout({name: 'keyboard', x: 600, y: 120, width: 400, height: 120});
            Main.layoutManager.uiGroup.add_child(background);
            ctx.actors = {keyboard, normal, special, background};
        },
        cells: ctx => [
            {row: 'keyboard-background', actor: ctx.actors.background, margin: 24},
            {row: 'keyboard-key', actor: ctx.actors.normal, margin: 2},
            {row: 'keyboard-special', actor: ctx.actors.special, margin: 2},
        ],
        states: ['normal', 'hover', 'pressed'],
        close: async ctx => {
            try {
                if (ctx.actors) {
                    ctx.actors.normal.style = null;
                    ctx.actors.special.style = null;
                    ctx.actors.background.destroy();
                    ctx.actors.keyboard.close(true);
                }
                ctx.actors = null;
                await wait(200);
            } finally {
                if (ctx.settings) {
                    ctx.settings.set_boolean('screen-keyboard-enabled', ctx.keyboardBefore ?? false);
                    Gio.Settings.sync();
                    await waitUntil(() => !Main.keyboard.keyboardActor, 3000);
                }
                ctx.settings = null;
            }
        },
    },
};
