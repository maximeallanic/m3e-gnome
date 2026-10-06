// Popup menu surface (PanelMenu.Button added to the panel, like an extension does).
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as BoxPointer from 'resource:///org/gnome/shell/ui/boxpointer.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

import {TEXT_SIZE} from './common.js';

export const MENU_SURFACES = {
    // Menus: test PopupMenu of a button added to the panel (PanelMenu.Button, like an extension), opened without
    // animation: plain item (label at the bench size: colour measured), ornamented item (check; height, corners and
    // layers measured), separator, open submenu (two items), disabled item (label at the bench size). Menu margin:
    // its shadow spills a few px; items margin: 2 px, inside the menu (surroundings = menu background, neighbour
    // item not measured).
    menu: {
        open: async ctx => {
            const button = new PanelMenu.Button(0.5, 'M3E bench', false);
            button.add_child(new St.Icon({icon_name: 'open-menu-symbolic', style_class: 'system-status-icon'}));
            Main.panel.addToStatusArea('m3e-bench-menu', button, 0, 'right');
            const m = button.menu;
            const plain = new PopupMenu.PopupMenuItem('Plain item');
            plain.label.style = TEXT_SIZE;
            const ornamented = new PopupMenu.PopupMenuItem('Ornamented item');
            ornamented.setOrnament(PopupMenu.Ornament.CHECK);
            const submenu = new PopupMenu.PopupSubMenuMenuItem('Submenu');
            submenu.menu.addMenuItem(new PopupMenu.PopupMenuItem('Submenu item'));
            submenu.menu.addMenuItem(new PopupMenu.PopupMenuItem('Another item'));
            const off = new PopupMenu.PopupMenuItem('Disabled');
            off.label.style = TEXT_SIZE;
            off.setSensitive(false);
            // An unmeasured item between two cells: the pseudo-classes are set on every cell, two neighbouring
            // state layers would merge.
            m.addMenuItem(plain);
            m.addMenuItem(new PopupMenu.PopupMenuItem('Item'));
            m.addMenuItem(ornamented);
            m.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            m.addMenuItem(submenu);
            m.addMenuItem(new PopupMenu.PopupMenuItem('Last item'));
            m.addMenuItem(off);
            m.open(BoxPointer.PopupAnimation.NONE);
            submenu.menu.open(false);
            ctx.actors = {button, menu: m.box, plain, ornamented, submenu: submenu.menu.actor, off};
        },
        cells: ctx => [
            {row: 'menu', actor: ctx.actors.menu, margin: 24},
            {row: 'menu-item', actor: ctx.actors.ornamented, margin: 2},
            {row: 'menu-text', actor: ctx.actors.plain, margin: 2},
            {row: 'menu-disabled', actor: ctx.actors.off, margin: 2},
            {row: 'menu-submenu', actor: ctx.actors.submenu, margin: 2},
        ],
        states: ['normal', 'hover', 'pressed', 'focus'],
        close: ctx => {
            const b = ctx.actors?.button;
            ctx.actors = null;
            if (b) {
                b.menu.close(BoxPointer.PopupAnimation.NONE);
                b.destroy();
            }
        },
    },
};
