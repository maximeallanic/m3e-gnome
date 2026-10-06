// Login screen surfaces (nested Shell in gdm mode: nested.sh --mode gdm).
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {wait, waitUntil} from '../tools.js';
import {TEXT_SIZE} from './common.js';
import {TEST_USER_NAME, TEST_USER_REAL_NAME, TestUser, blockGdm, unblockGdm} from './lock-guards.js';

// Login (gdm mode): LoginDialog of Main.screenShield, user list; real accounts hidden, test user added (list item
// with the real classes).
async function openLogin(ctx) {
    const d = Main.screenShield?._dialog;
    if (!Main.sessionMode.isGreeter || !d?._userList)
        throw new Error('login: nested Shell not in gdm mode (nested.sh --mode gdm)');
    blockGdm(ctx);
    if (!await waitUntil(() => d._userListLoaded && d._userSelectionBox.visible, 5000))
        throw new Error('login: user list not shown');
    ctx.loginDialog = d;
    ctx.fakeUser = new TestUser(TEST_USER_NAME, TEST_USER_REAL_NAME);
    ctx.hiddenReal = [];
    for (const item of d._userList._items.values()) {
        if (item.user !== ctx.fakeUser && item.visible) {
            item.hide();
            ctx.hiddenReal.push(item);
        }
    }
    d._userList.addUser(ctx.fakeUser);
    const item = d._userList.getItemFromUserName(TEST_USER_NAME);
    if (!item)
        throw new Error('login: test user item not found');
    return {d, item};
}

async function closeLogin(ctx) {
    const d = ctx.loginDialog;
    try {
        if (d) {
            if (d._authPrompt.visible)
                d._authPrompt.cancel();
            await waitUntil(() => d._userSelectionBox.visible, 3000);
            if (ctx.fakeUser)
                d._userList.removeUser(ctx.fakeUser);
            for (const item of ctx.hiddenReal ?? [])
                item.show();
        }
        await wait(200);
    } finally {
        ctx.loginDialog = null;
        ctx.fakeUser = null;
        ctx.hiddenReal = null;
        unblockGdm(ctx);
    }
}

export const LOGIN_SURFACES = {
    // Login (nested Shell in gdm mode: run.sh -> nested.sh --mode gdm), user list: test user item (real accounts
    // hidden), its name at the bench size, "Not listed?" (real button; label colour on a test button with the same
    // classes, at the bench size), accessibility button and bar's quick settings button (#panel.login-screen).
    // Keyboard focus moved out of the list (set on the dialog).
    login: {
        open: async ctx => {
            const {d, item} = await openLogin(ctx);
            const name = item._userWidget._label;
            name._realNameLabel.style = TEXT_SIZE;
            name._userNameLabel.style = TEXT_SIZE;
            const box = new St.BoxLayout({style_class: 'login-dialog', x: 80, y: 120});
            const text = new St.Button({style_class: 'login-dialog-not-listed-button',
                child: new St.Label({style_class: 'login-dialog-not-listed-label', text: 'Not listed?',
                    style: TEXT_SIZE})});
            box.add_child(text);
            Main.layoutManager.uiGroup.add_child(box);
            const button = Main.panel.statusArea.quickSettings;
            if (!button?.visible || !Main.panel.has_style_class_name('login-screen'))
                throw new Error('login: login bar (#panel.login-screen) not found');
            await wait(200);
            global.stage.set_key_focus(d);
            await wait(200);
            ctx.actors = {item, name, notListed: d._notListedButton, box, text, a11y: d._a11yMenuButton, button};
        },
        cells: ctx => [
            {row: 'login-user', actor: ctx.actors.item, margin: 4},
            {row: 'login-user-text', actor: ctx.actors.name, margin: 2},
            {row: 'login-not-listed', actor: ctx.actors.notListed, margin: 3},
            {row: 'login-not-listed-text', actor: ctx.actors.text, margin: 3},
            {row: 'login-a11y', actor: ctx.actors.a11y, margin: 4},
            {row: 'login-bar-button', actor: ctx.actors.button, margin: 2},
        ],
        states: ['normal', 'hover', 'pressed', 'focus'],
        close: async ctx => {
            try {
                ctx.actors?.box.destroy();
                ctx.actors = null;
            } finally {
                await closeLogin(ctx);
            }
        },
    },

    // Login (gdm mode), prompt: the test user chosen through the API (_onUserListActivated, no click; local question
    // of blockGdm); password entry (test text at the bench size), cancel button and session choice button. Closing:
    // prompt cancelled (back to the list).
    'login-prompt': {
        open: async ctx => {
            const {d, item} = await openLogin(ctx);
            d._onUserListActivated(item);
            const prompt = await waitUntil(() => d._authPrompt.visible && d._authPrompt._entry?.reactive &&
                d._sessionMenuButton.visible && d._authPrompt, 5000);
            if (!prompt)
                throw new Error('login: password prompt not shown');
            prompt._entry.set_text('password');
            prompt._entry.style = TEXT_SIZE;
            // Session choice button: the Shell hides it when a single session is installed (a single gnome.desktop
            // session); shown for the scenario to see its style.
            const session = d._sessionMenuButton._button;
            ctx.sessionHidden = !session.visible;
            session.show();
            global.stage.set_key_focus(d);
            await wait(300);
            ctx.actors = {entry: prompt._entry, cancel: prompt.cancelButton, session};
        },
        cells: ctx => [
            {row: 'login-entry', actor: ctx.actors.entry, margin: 6},
            {row: 'login-cancel', actor: ctx.actors.cancel, margin: 4},
            {row: 'login-session', actor: ctx.actors.session, margin: 4},
        ],
        states: ['normal', 'hover', 'pressed', 'focus'],
        close: async ctx => {
            try {
                if (ctx.actors) {
                    ctx.actors.entry.style = null;
                    ctx.actors.entry.set_text('');
                    if (ctx.sessionHidden)
                        ctx.actors.session.hide();
                }
                ctx.actors = null;
            } finally {
                await closeLogin(ctx);
            }
        },
    },
};
