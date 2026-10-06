// Dialog surfaces: modal dialog, end-session warnings, run dialog.
import Clutter from 'gi://Clutter';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as Dialog from 'resource:///org/gnome/shell/ui/dialog.js';
import * as ModalDialog from 'resource:///org/gnome/shell/ui/modalDialog.js';

import {wait, waitUntil} from '../tools.js';
import {TEXT_SIZE, findActor, placeActors, removeActors} from './common.js';

// Waits for the OPENED state, then moves the keyboard focus out of the buttons / the entry (set on the dialog's
// surface): real focus makes the stock sheet's !important ring draw, which the bench's "focus" state measures
// separately.
async function waitDialogOpen(d) {
    const open = await waitUntil(() => d.state === ModalDialog.State.OPENED, 3000);
    if (!open)
        throw new Error('dialog not open');
    await wait(200);
    global.stage.set_key_focus(d.dialogLayout._dialog);
    await wait(100);
}

async function closeDialog(d) {
    if (d && d.state !== ModalDialog.State.CLOSED && d.state !== ModalDialog.State.CLOSING)
        d.close();
    await waitUntil(() => !d || d.state === ModalDialog.State.CLOSED, 2000);
    await wait(100);
}

// Test dialog buttons with the same classes (.modal-dialog .modal-dialog-button-box .modal-dialog-button, :default
// for the default action), label at the bench size: text colour measured (14 px real: anti-aliased blends). Put
// above the real dialog (last child of uiGroup, outside its veil), on the witness background (.modal-dialog box
// without background or shadow, inline style): in light mode, on_primary (label of the default action) and
// surface_bright (dialog background) are almost equal, and measure.py would take the label for the cell
// background.
function testButtons() {
    const box = new St.BoxLayout({style_class: 'modal-dialog', x: 60, y: 80, orientation: Clutter.Orientation.VERTICAL,
        style: 'background-color: transparent; box-shadow: none;'});
    const row = new St.BoxLayout({style_class: 'modal-dialog-button-box'});
    box.add_child(row);
    const cancel = new St.Button({style_class: 'modal-dialog-button', label: 'Cancel', style: TEXT_SIZE});
    const defaultButton = new St.Button({style_class: 'modal-dialog-button', label: 'OK', style: TEXT_SIZE});
    defaultButton.add_style_pseudo_class('default');
    row.add_child(cancel);
    row.add_child(defaultButton);
    Main.layoutManager.uiGroup.add_child(box);
    return {box, cancel, default: defaultButton};
}

export const DIALOG_SURFACES = {
    // Dialog: test ModalDialog + MessageDialogContent (title, text), "Cancel" (Text button) and "OK" (default action,
    // :default = Filled button). Title and text at the bench size (colour measured); button label colour on test
    // buttons with the same classes (testButtons); shapes and layers on the real buttons. Keyboard focus moved out
    // of the buttons (waitDialogOpen).
    dialog: {
        open: async ctx => {
            const d = new ModalDialog.ModalDialog({destroyOnClose: true});
            const content = new Dialog.MessageDialogContent({title: 'Dialog title',
                description: 'Test dialog text from the bench.'});
            d.contentLayout.add_child(content);
            const cancel = d.addButton({label: 'Cancel', action: () => {}, key: Clutter.KEY_Escape});
            const defaultButton = d.addButton({label: 'OK', action: () => {}, default: true});
            ctx.dialog = d;
            if (!d.open())
                throw new Error('dialog: pushModal refused');
            await waitDialogOpen(d);
            content._title.style = TEXT_SIZE;
            content._description.style = TEXT_SIZE;
            const test = testButtons();
            ctx.actors = {background: d.dialogLayout._dialog, title: content._title, text: content._description,
                cancel, default: defaultButton, test};
            await wait(100);
        },
        cells: ctx => [
            {row: 'dialog-background', actor: ctx.actors.background, margin: 24},
            {row: 'dialog-title', actor: ctx.actors.title, margin: 2},
            {row: 'dialog-text', actor: ctx.actors.text, margin: 2},
            {row: 'dialog-default', actor: ctx.actors.default, margin: 3},
            {row: 'dialog-cancel', actor: ctx.actors.cancel, margin: 3},
            {row: 'dialog-default-text', actor: ctx.actors.test.default, margin: 3},
            {row: 'dialog-cancel-text', actor: ctx.actors.test.cancel, margin: 3},
        ],
        states: ['normal', 'hover', 'pressed', 'focus', 'disabled'],
        close: async ctx => {
            ctx.actors?.test.box.destroy();
            ctx.actors = null;
            await closeDialog(ctx.dialog);
            ctx.dialog = null;
        },
    },

    // Warnings of the end-session dialog: test actors with the real classes (.end-session-dialog >
    // .end-session-dialog-battery-warning, .end-session-dialog .dialog-list > .dialog-list-title) on the witness
    // background, text at the bench size.
    'dialog-warning': {
        open: async ctx => {
            const box = new St.BoxLayout({style_class: 'end-session-dialog', x: 160, y: 200,
                orientation: Clutter.Orientation.VERTICAL});
            const battery = new St.Label({style_class: 'end-session-dialog-battery-warning',
                text: 'Low battery', style: TEXT_SIZE});
            const list = new St.BoxLayout({style_class: 'dialog-list', orientation: Clutter.Orientation.VERTICAL});
            const title = new St.Label({style_class: 'dialog-list-title', text: 'Updates', style: TEXT_SIZE});
            list.add_child(title);
            box.add_child(battery);
            box.add_child(list);
            placeActors(ctx, {box});
            ctx.targets = {battery, title};
            await wait(100);
        },
        cells: ctx => [
            {row: 'dialog-warning', actor: ctx.targets.battery, margin: 4},
            {row: 'dialog-list-warning', actor: ctx.targets.title, margin: 4},
        ],
        states: ['normal'],
        close: ctx => {
            ctx.targets = null;
            removeActors(ctx);
        },
    },

    // Run dialog: Main.openRunDialog() (module-private instance, found in modalDialogGroup). Background and
    // description (.run-dialog-description, bench size) on the real dialog. Entry (.run-dialog-entry) measured on
    // a test entry with the same classes (.modal-dialog.run-dialog StEntry.run-dialog-entry, typed text at the
    // bench size) whose test dialog is made transparent (witness background below): in light mode, the Filled text
    // field (surface_container_highest) is within 6 per channel of the dialog surface (surface_container_high),
    // under measure.py's "background colour" threshold (same case as settings-switch). The real entry: visual
    // review.
    'run-dialog': {
        open: async ctx => {
            Main.openRunDialog();
            const d = await waitUntil(() => Main.layoutManager.modalDialogGroup.get_children()
                .find(c => c._entryText && c.state === ModalDialog.State.OPENED), 3000);
            if (!d)
                throw new Error('Run dialog not open');
            ctx.dialog = d;
            await waitDialogOpen(d);
            const description = findActor(d, e => e.has_style_class_name?.('run-dialog-description'));
            if (!description)
                throw new Error('Run dialog description not found');
            description.style = TEXT_SIZE;
            const box = new St.BoxLayout({style_class: 'modal-dialog run-dialog', x: 60, y: 80,
                style: 'background-color: transparent; box-shadow: none;'});
            const entry = new St.Entry({style_class: 'run-dialog-entry', text: 'command', style: TEXT_SIZE,
                width: 360});
            box.add_child(entry);
            Main.layoutManager.uiGroup.add_child(box);
            ctx.actors = {background: d.dialogLayout._dialog, description, box, entry};
            await wait(100);
        },
        cells: ctx => [
            {row: 'run-background', actor: ctx.actors.background, margin: 24},
            {row: 'run-description', actor: ctx.actors.description, margin: 2},
            {row: 'run-entry', actor: ctx.actors.entry, margin: 6},
        ],
        states: ['normal', 'hover', 'focus'],
        close: async ctx => {
            if (ctx.actors) {
                ctx.actors.description.style = null;
                ctx.actors.box.destroy();
            }
            ctx.actors = null;
            await closeDialog(ctx.dialog);
            ctx.dialog = null;
        },
    },
};
