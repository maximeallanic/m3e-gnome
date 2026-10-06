// Notification surfaces: calendar message list, buttons inside cards, group header, banner.
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as BoxPointer from 'resource:///org/gnome/shell/ui/boxpointer.js';
import * as MessageTray from 'resource:///org/gnome/shell/ui/messageTray.js';

import {wait} from '../tools.js';
import {openCalendar} from './calendar.js';
import {createMediaMessage, placeActors, removeActors} from './common.js';

// Test notification sources (nested Shell only: MessageTray.Source + Notification, no D-Bus). LOW urgency: never a
// banner (messageTray._onNotificationRequestBanner), they only go to the calendar list.
// Group: three notifications of one source (stack); another source, a notification with two actions, expanded
// (action buttons visible); a test media message (see createMediaMessage), at the end of the list.
// Welded cards: the bench sets itself the position pseudo-classes that m3e-motion sets in a session (contract of
// the motion bench: :m3e-first on the first visible message of the list, :m3e-last on the last); list order:
// reminder (Agenda), group stack, media message. The 2 px gap between cards comes from the extensions sheet (not
// loaded here: 12 px in the stock sheet), checked by the extensions bench.
async function openNotifications(ctx) {
    const dm = openCalendar();
    const view = dm._messageList._messageView;
    const notification = (source, title, body) => {
        const n = new MessageTray.Notification({source, title, body,
            gicon: new Gio.ThemedIcon({name: 'mail-unread-symbolic'})});
        n.urgency = MessageTray.Urgency.LOW;
        return n;
    };
    const group = new MessageTray.Source({title: 'M3E bench', iconName: 'mail-unread-symbolic'});
    Main.messageTray.add(group);
    for (let i = 1; i <= 3; i++)
        group.addNotification(notification(group, `Test message ${i}`, 'Body of the bench test notification.'));
    const agenda = new MessageTray.Source({title: 'Agenda', iconName: 'x-office-calendar-symbolic'});
    Main.messageTray.add(agenda);
    const reminder = notification(agenda, 'Meeting in 10 minutes', 'Bench room, 10:00.');
    reminder.addAction('Snooze', () => {});
    reminder.addAction('Open', () => {});
    agenda.addNotification(reminder);
    const {media, buttons: mediaButtons} = createMediaMessage();
    view._addMessageAtIndex(media, view.messages.length);
    const groupWidget = view._notificationSourceToGroup.get(group);
    const agendaWidget = view._notificationSourceToGroup.get(agenda);
    const reminderMessage = agendaWidget._notificationToMessage.get(reminder);
    reminderMessage.expand(false);
    reminderMessage.add_style_pseudo_class('m3e-first');
    media.add_style_pseudo_class('m3e-last');
    ctx.notifs = {dm, view, sources: [group, agenda], media};
    ctx.actors = {
        popover: dm.menu.box, view, group: groupWidget, top: groupWidget.get_first_child().child,
        reminder: reminderMessage, action: reminderMessage._buttonBox.get_first_child(),
        close: reminderMessage._header.closeButton, media,
        expand: reminderMessage._header.expandButton.get_child(),
        mediaButton: mediaButtons[1], clear: dm._messageList._clearButton,
    };
}

function closeNotifications(ctx) {
    const n = ctx.notifs;
    ctx.notifs = null;
    ctx.actors = null;
    if (!n)
        return;
    for (const s of n.sources)
        s.destroy(MessageTray.NotificationDestroyedReason.SOURCE_CLOSED);
    if (n.view.messages.includes(n.media))
        n.view._removeMessage(n.media);
    n.dm.menu.close(BoxPointer.PopupAnimation.NONE);
}

export const NOTIFICATION_SURFACES = {
    // Notifications: calendar list with the test notifications (openNotifications). Cards alone (group stack,
    // notification with actions, media message) and "Clear all": their state layers (inner shadow) would pass under
    // the transparent buttons they contain, measured in "notifications-buttons".
    notifications: {
        open: ctx => openNotifications(ctx),
        cells: ctx => [
            {row: 'notif-card', actor: ctx.actors.top, margin: 2},
            {row: 'notif-card-actions', actor: ctx.actors.reminder, margin: 2},
            {row: 'notif-media', actor: ctx.actors.media, margin: 2},
            {row: 'notif-clear', actor: ctx.actors.clear, margin: 2},
        ],
        states: ['normal', 'hover', 'pressed'],
        close: closeNotifications,
    },

    // Buttons inside cards: action button (.notification-button), close (.message-close-button), media button
    // (.message-media-control); the cards stay at rest.
    'notifications-buttons': {
        open: ctx => openNotifications(ctx),
        cells: ctx => [
            {row: 'notif-action', actor: ctx.actors.action, margin: 2},
            {row: 'notif-close', actor: ctx.actors.close, margin: 2},
            {row: 'notif-media-button', actor: ctx.actors.mediaButton, margin: 2},
            {row: 'notif-expand', actor: ctx.actors.expand, margin: 2},
        ],
        states: ['normal', 'hover', 'pressed'],
        close: closeNotifications,
    },

    // Expanded group header: test actor with the classes of NotificationMessageGroup (.message-notification-group >
    // .message-group-header: title .message-group-title, "collapse" button .message-collapse-button), put on the
    // witness background. The real expanded group (MessageView._setExpandedGroup) comes out empty in the bench: the
    // Shell fades the list (FadeEffect) and the header is not allocated without animation; visual review of the
    // real header in a session.
    'notifications-group': {
        open: async ctx => {
            const group = new St.BoxLayout({style_class: 'message-notification-group', x: 160, y: 200,
                width: 360});
            const header = new St.BoxLayout({style_class: 'message-group-header', x_expand: true});
            header.add_child(new St.Label({text: 'M3E bench', style_class: 'message-group-title',
                y_align: Clutter.ActorAlign.CENTER}));
            const collapse = new St.Button({style_class: 'message-collapse-button', icon_name: 'group-collapse-symbolic',
                x_align: Clutter.ActorAlign.END, y_align: Clutter.ActorAlign.CENTER, x_expand: true});
            header.add_child(collapse);
            group.add_child(header);
            placeActors(ctx, {group});
            ctx.collapse = collapse;
        },
        cells: ctx => [
            {row: 'notif-collapse', actor: ctx.collapse, margin: 4},
        ],
        states: ['normal', 'hover', 'pressed'],
        close: ctx => {
            ctx.collapse = null;
            removeActors(ctx);
        },
    },

    // Banner: one CRITICAL notification of a test source, shown by messageTray as a banner (expanded outright,
    // actions visible, no expiry delay), calendar closed; the source is destroyed by close().
    banner: {
        open: async ctx => {
            const source = new MessageTray.Source({title: 'M3E bench', iconName: 'mail-unread-symbolic'});
            Main.messageTray.add(source);
            const n = new MessageTray.Notification({source, title: 'Test banner',
                body: 'Notification shown as a banner by the bench.',
                gicon: new Gio.ThemedIcon({name: 'mail-unread-symbolic'})});
            n.urgency = MessageTray.Urgency.CRITICAL;
            n.addAction('Reply', () => {});
            n.addAction('Dismiss', () => {});
            ctx.bannerSource = source;
            source.addNotification(n);
            for (let i = 0; i < 40 && !Main.messageTray._banner; i++)
                await wait(50);
            if (!Main.messageTray._banner)
                throw new Error('banner not shown');
            ctx.actors = {banner: Main.messageTray._banner};
        },
        cells: ctx => [
            {row: 'notif-banner', actor: ctx.actors.banner, margin: 24},
        ],
        states: ['normal', 'hover'],
        close: ctx => {
            ctx.actors = null;
            ctx.bannerSource?.destroy(MessageTray.NotificationDestroyedReason.SOURCE_CLOSED);
            ctx.bannerSource = null;
        },
    },
};
