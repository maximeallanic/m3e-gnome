// Shell surfaces the screenshot scenarios open, by name. Each action returns once the surface is open (animations
// still run: the scenario waits). All of them are public Shell UI calls, no private bus, no eval.
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as Dialog from 'resource:///org/gnome/shell/ui/dialog.js';
import * as ModalDialog from 'resource:///org/gnome/shell/ui/modalDialog.js';

let demoDialog = null;

function closeMenus() {
    Main.panel.statusArea.quickSettings?.menu.close(false);
    Main.panel.statusArea.dateMenu?.menu.close(false);
    if (demoDialog) {
        demoDialog.destroy();
        demoDialog = null;
    }
}

// Quick settings: open, optionally with the submenu of the tile whose title matches `arg`.
function quickSettings(arg) {
    const qs = Main.panel.statusArea.quickSettings;
    qs.menu.open(false);
    if (!arg)
        return;
    const tile = qs.menu.box.get_children().flatMap(row => row.get_children?.() ?? [])
        .find(a => a.menu && (a.title ?? a._title?.text ?? '').toLowerCase() === arg.toLowerCase());
    tile?.menu.open(false);
}

function dialog() {
    demoDialog = new ModalDialog.ModalDialog({destroyOnClose: true});
    demoDialog.contentLayout.add_child(new Dialog.MessageDialogContent({
        title: 'Move 3 items to the bin?',
        description: 'The files will stay in the bin until you empty it. You can restore them at any time.',
    }));
    demoDialog.addButton({label: 'Cancel', action: () => demoDialog.close(), key: Clutter.KEY_Escape});
    demoDialog.addButton({label: 'Move to bin', action: () => demoDialog.close(), default: true});
    if (!demoDialog.open())
        throw new Error('dialog: pushModal refused');
}

function volumeOsd() {
    Main.osdWindowManager.showOne(Main.layoutManager.primaryIndex, new Gio.ThemedIcon({name: 'audio-volume-medium-symbolic'}),
        null, 0.62, 1);
}

// Removes every notification (the Shell posts a few of its own at start-up in a nested session).
function clearNotifications() {
    for (const source of Main.messageTray.getSources())
        source.destroy();
}

// The Shell draws an orange indicator while a screencast runs; the video should not show it. Kept hidden whatever the
// Shell does with it (it toggles its own visibility when the recording starts and stops).
function hideRecordingIndicator() {
    const area = Main.panel.statusArea;
    for (const indicator of [area.quickSettings?._remoteAccess, area.screenRecording, area.screenSharing]) {
        if (!indicator)
            continue;
        indicator.hide();
        indicator.connect('notify::visible', () => indicator.visible && indicator.hide());
    }
}

export const ACTIONS = {
    'hide-recording-indicator': hideRecordingIndicator,
    'overview': () => Main.overview.show(),
    'appgrid': () => {
        Main.overview.show();
        Main.overview.dash.showAppsButton.checked = true;
    },
    'close': () => {
        closeMenus();
        Main.overview.hide();
    },
    'quick-settings': quickSettings,
    'calendar': () => Main.panel.statusArea.dateMenu.menu.open(false),
    'dialog': dialog,
    'osd-volume': volumeOsd,
    'clear-notifications': clearNotifications,
};

export function runAction(name, arg) {
    const action = ACTIONS[name];
    if (!action)
        throw new Error(`unknown action: ${name}`);
    action(arg);
    return GLib.SOURCE_REMOVE;
}
