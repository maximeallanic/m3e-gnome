// Overview helpers: open and close it (windows view or app grid) and reach the app grid items.
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {wait, waitUntil} from '../tools.js';

// Waits for the `signal` of Main.overview while `action` runs (5 s bound). St animations are off in the bench, but
// the overview has its own Clutter transitions: wait for `shown` / `hidden`.
function overviewSignal(signal, action) {
    return new Promise(resolve => {
        let id = 0, timeout = 0;
        const finish = () => {
            if (id)
                Main.overview.disconnect(id);
            if (timeout)
                GLib.source_remove(timeout);
            id = timeout = 0;
            resolve();
        };
        id = Main.overview.connect(signal, finish);
        timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 5000, () => {
            timeout = 0;
            finish();
            return GLib.SOURCE_REMOVE;
        });
        action();
    });
}

// Banners blocked while an overview surface is open: a notification of the nested session (observed: "Software
// Update Installed" from GNOME Software) covered the search bar in a capture.
export async function openOverview(apps) {
    Main.messageTray.bannerBlocked = true;
    if (Main.overview.visible && !Main.overview.animationInProgress) {
        if (apps)
            Main.overview.showApps();
        await wait(100);
    } else {
        await overviewSignal('shown', () => (apps ? Main.overview.showApps() : Main.overview.show()));
    }
    if (!Main.overview.visible)
        throw new Error('the overview does not open');
}

export async function closeOverview() {
    if (Main.overview.visible)
        await overviewSignal('hidden', () => Main.overview.hide());
    Main.messageTray.bannerBlocked = false;
}

// App grid: items of the current page (AppIcon .overview-tile, FolderIcon .overview-tile.app-folder).
export async function openAppGrid() {
    await openOverview(true);
    const appDisplay = Main.overview._overview._controls.appDisplay;
    const items = await waitUntil(() => {
        const t = appDisplay._orderedItems.filter(i => i.mapped);
        return t.some(i => i.has_style_class_name('app-folder')) &&
            t.filter(i => !i.has_style_class_name('app-folder')).length >= 2 ? t : null;
    }, 4000);
    if (!items)
        throw new Error('app grid without a folder or without visible apps');
    return {appDisplay, folder: items.find(i => i.has_style_class_name('app-folder')),
        apps: items.filter(i => !i.has_style_class_name('app-folder'))};
}
