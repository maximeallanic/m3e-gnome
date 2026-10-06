// Lock screen surfaces (clock page, unlock prompt, media message).
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {wait, waitUntil} from '../tools.js';
import {TEXT_SIZE, createMediaMessage} from './common.js';
import {TEST_USER_REAL_NAME, lockBench, unlockBench} from './lock-guards.js';

// Lock screen media message: lock like "lock", then a test media message inserted at the head of
// .unlock-dialog-notifications-container, like NotificationsBox._addPlayer. Title and body at the bench size if
// `benchSize` (otherwise the taller row would stretch the media buttons).
async function openLockMedia(ctx, benchSize) {
    const d = await lockBench(ctx);
    const box = d._notificationsBox;
    const container = box?._notificationBox;
    if (!container?.has_style_class_name('unlock-dialog-notifications-container'))
        throw new Error('lock: notifications container (.unlock-dialog-notifications-container) not found');
    const {media, buttons} = createMediaMessage();
    container.insert_child_at_index(media, 0);
    box._updateVisibility();
    if (benchSize) {
        media.titleLabel.style = TEXT_SIZE;
        media._bodyLabel.style = TEXT_SIZE;
    }
    ctx.lockMedia = {media, box};
    await wait(300);
    if (!box.visible || !media.mapped)
        throw new Error('lock: test media message not shown');
    ctx.actors = {media, title: media.titleLabel, body: media._bodyLabel, icon: media._icon, button: buttons[1]};
}

async function closeLockMedia(ctx) {
    try {
        const m = ctx.lockMedia;
        ctx.lockMedia = null;
        ctx.actors = null;
        if (m) {
            m.media.destroy();
            m.box._updateVisibility();
        }
    } finally {
        await unlockBench(ctx);
    }
}

export const LOCK_SURFACES = {
    // Lock, clock page: Main.screenShield.lock(false) of the nested Shell (guards: lockBench), wallpaper hidden.
    // Clock (.unlock-dialog-clock-time, Display large: 57 px glyphs, colour measured on the real one), date (bench
    // size), clock size on a gauge with the same classes (height 1em = font size set by the sheet), bar's quick
    // settings button (#panel.unlock-screen). "Click to unlock" hint made visible for the review (the Shell shows
    // it after 10 s of inactivity).
    lock: {
        open: async ctx => {
            const d = await lockBench(ctx);
            const clock = d._clock;
            if (!clock?._time)
                throw new Error('lock: clock not found');
            clock._hint.opacity = 255;
            clock._date.style = TEXT_SIZE;
            const box = new St.BoxLayout({style_class: 'unlock-dialog-clock', x: 80, y: 120});
            // Gauge: 1em height (font size of .unlock-dialog-clock-time), the bench's witness background.
            const gauge = new St.Widget({style_class: 'unlock-dialog-clock-time',
                style: 'height: 1em; width: 2em; background-color: #ff00ff;'});
            box.add_child(gauge);
            Main.layoutManager.uiGroup.add_child(box);
            const button = Main.panel.statusArea.quickSettings;
            if (!button?.visible || !Main.panel.has_style_class_name('unlock-screen'))
                throw new Error('lock: lock screen bar (#panel.unlock-screen) not found');
            ctx.actors = {time: clock._time, date: clock._date, box, gauge, button};
            await wait(200);
        },
        cells: ctx => [
            {row: 'lock-clock', actor: ctx.actors.time, margin: 8},
            {row: 'lock-clock-size', actor: ctx.actors.gauge, margin: 8},
            {row: 'lock-date', actor: ctx.actors.date, margin: 4},
            {row: 'lock-bar-button', actor: ctx.actors.button, margin: 2},
        ],
        states: ['normal', 'hover', 'pressed', 'focus'],
        close: async ctx => {
            try {
                if (ctx.actors) {
                    ctx.actors.box.destroy();
                    ctx.actors.date.style = null;
                }
                ctx.actors = null;
            } finally {
                await unlockBench(ctx);
            }
        },
    },

    // Unlock, prompt page: lock as above, then _showPrompt() (local question of blockGdm); password entry (test
    // text at the bench size), name and avatar of the test user, "switch user" button (shown by the bench: the Shell
    // only shows it with several accounts). Keyboard focus moved out of the entry (set on the dialog): real focus
    // makes the stock sheet's !important ring draw.
    unlock: {
        open: async ctx => {
            const d = await lockBench(ctx);
            d._showPrompt();
            // Local question received (_queryingService): setQuestion() gives the focus back to the entry.
            const prompt = await waitUntil(() => d._authPrompt?._queryingService === 'gdm-password' &&
                d._authPrompt._entry?.reactive && d._promptBox.visible && d._authPrompt._userWell.get_child() &&
                d._authPrompt, 5000);
            if (!prompt)
                throw new Error('lock: password prompt not shown');
            const widget = prompt._userWell.get_child();
            const name = widget._label?._realNameLabel;
            if (!name || name.text !== TEST_USER_REAL_NAME)
                throw new Error('lock: test user not shown');
            prompt._entry.set_text('password');
            prompt._entry.style = TEXT_SIZE;
            name.style = TEXT_SIZE;
            widget._label._userNameLabel.style = TEXT_SIZE;
            d._otherUserButton.visible = true;
            // Focus moved out of the entry, onto the prompt (like AuthPrompt.updateSensitivity(false)), then checked.
            const unfocused = await waitUntil(() => {
                if (prompt._entry.has_style_pseudo_class('focus'))
                    prompt.grab_key_focus();
                return !prompt._entry.has_style_pseudo_class('focus');
            }, 2000);
            await wait(300);
            if (!unfocused || prompt._entry.has_style_pseudo_class('focus'))
                throw new Error('lock: keyboard focus stayed on the entry');
            // Name cell on UserWidgetLabel: it only paints one of its two labels (real name or user name, depending
            // on the room) and gives the other an empty allocation.
            ctx.actors = {entry: prompt._entry, name: widget._label, avatar: widget._avatar,
                switchUser: d._otherUserButton};
        },
        cells: ctx => [
            {row: 'lock-entry', actor: ctx.actors.entry, margin: 6},
            {row: 'lock-user', actor: ctx.actors.name, margin: 4},
            {row: 'lock-avatar', actor: ctx.actors.avatar, margin: 6},
            {row: 'lock-switch-user', actor: ctx.actors.switchUser, margin: 4},
        ],
        states: ['normal', 'hover', 'pressed', 'focus'],
        close: async ctx => {
            try {
                if (ctx.actors) {
                    ctx.actors.entry.style = null;
                    ctx.actors.entry.set_text('');
                }
                ctx.actors = null;
            } finally {
                await unlockBench(ctx);
            }
        },
    },

    // Lock screen media message: card, title, body, icon and button at rest; the card, dark in both modes, must
    // carry a dark-palette text (otherwise dark text on a dark card in light mode).
    'lock-media': {
        open: ctx => openLockMedia(ctx, true),
        cells: ctx => [
            {row: 'lock-media', actor: ctx.actors.media, margin: 2},
            {row: 'lock-media-title', actor: ctx.actors.title, margin: 2},
            {row: 'lock-media-body', actor: ctx.actors.body, margin: 2},
            {row: 'lock-media-icon', actor: ctx.actors.icon, margin: 2},
            {row: 'lock-media-button', actor: ctx.actors.button, margin: 2},
        ],
        states: ['normal'],
        close: closeLockMedia,
    },

    // Lock screen media button, states (the card stays at rest: its layer would pass under the button). Text at its
    // real size: 48 dp row, like notif-media-button.
    'lock-media-button': {
        open: ctx => openLockMedia(ctx, false),
        cells: ctx => [
            {row: 'lock-media-button-states', actor: ctx.actors.button, margin: 2},
        ],
        states: ['hover', 'pressed'],
        close: closeLockMedia,
    },
};
