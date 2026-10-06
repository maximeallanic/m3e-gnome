// On-screen display surface.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {wait, waitUntil} from '../tools.js';
import {TEXT_SIZE} from './common.js';

// Visible OSD window (one per screen, the bench has a single one); hide timer (1.5 s) cancelled.
function visibleOsd() {
    const windows = Main.osdWindowManager._osdWindows.filter(w => w?.visible);
    for (const w of windows) {
        if (w._hideTimeoutId) {
            GLib.source_remove(w._hideTimeoutId);
            w._hideTimeoutId = 0;
        }
    }
    return windows[0] ?? null;
}

export const OSD_SURFACES = {
    // OSD: Main.osdWindowManager.showAll(volume icon, 'Volume', 0.6, maximum 1) - API of 50.5 (show(icon, label,
    // levels); the show(-1, ...) form no longer exists), hide timer cancelled. Window (.osd-window), level (BarLevel
    // .level, at 60 %: the active part dominates), icon; label colour on a test label in a test .osd-window, at the
    // bench size.
    osd: {
        open: async ctx => {
            Main.osdWindowManager.showAll(new Gio.ThemedIcon({name: 'audio-volume-medium-symbolic'}), 'Volume', 0.6, 1);
            const w = await waitUntil(visibleOsd, 2000);
            if (!w)
                throw new Error('OSD not shown');
            await wait(300);
            visibleOsd();
            const box = new St.BoxLayout({style_class: 'osd-window', x: 60, y: 80});
            const label = new St.Label({text: 'Volume', style: TEXT_SIZE});
            box.add_child(label);
            Main.layoutManager.uiGroup.add_child(box);
            ctx.osd = w;
            ctx.actors = {background: w._hbox, level: w._level, icon: w._icon, box, label};
        },
        cells: ctx => [
            {row: 'osd-background', actor: ctx.actors.background, margin: 8},
            {row: 'osd-level', actor: ctx.actors.level, margin: 3},
            {row: 'osd-icon', actor: ctx.actors.icon, margin: 2},
            {row: 'osd-text', actor: ctx.actors.label, margin: 4},
        ],
        states: ['normal'],
        close: async ctx => {
            ctx.actors?.box.destroy();
            ctx.actors = null;
            ctx.osd?._hide();
            ctx.osd = null;
            await wait(100);
        },
    },
};
