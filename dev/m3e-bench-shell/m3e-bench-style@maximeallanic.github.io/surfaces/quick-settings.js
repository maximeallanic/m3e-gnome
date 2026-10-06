// Quick settings surfaces: the panel with test tiles, and a tile menu.
import Clutter from 'gi://Clutter';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as BoxPointer from 'resource:///org/gnome/shell/ui/boxpointer.js';
import {CheckBox} from 'resource:///org/gnome/shell/ui/checkBox.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as QuickSettings from 'resource:///org/gnome/shell/ui/quickSettings.js';
import {Slider} from 'resource:///org/gnome/shell/ui/slider.js';

import {TEXT_SIZE, descendant, findAllByClass} from './common.js';

// Height m3e-motion gives a slider (its bar handle: 52 dp x 56/72), see the comment in the `settings` surface.
const SLIDER_HEIGHT = 40;

// Test tiles added to the quick settings (real Shell classes: the hardware of the nested bench does not always
// provide any); removed and destroyed by closeSettings().
function closeSettings(ctx) {
    const qs = Main.panel.statusArea.quickSettings;
    for (const t of ctx.tiles ?? []) {
        t.menu?.close(BoxPointer.PopupAnimation.NONE);
        t.destroy();
    }
    ctx.tiles = null;
    qs.menu.close(BoxPointer.PopupAnimation.NONE);
    ctx.stockTitles = null;
    ctx.actors = null;
}

// Visible tile titles with their truncation: natural width, whether Pango ellipsized them, and the visible share
// (allocated / natural width).
function measureTitles(grid) {
    return findAllByClass(grid, 'quick-toggle-title').filter(l => l.visible && l.text).map(label => {
        const natural = label.clutter_text.get_preferred_width(-1)[1];
        return {label, natural, ellipsized: label.clutter_text.get_layout().is_ellipsized(),
            share: natural > 0 ? label.width / natural : 1};
    });
}

// Titles at fault: truncated, and more truncated than under the stock sheet in the SAME run (so in the same
// locale, with the same fonts and the same strings): visible share below the stock share (1 when the stock sheet
// does not truncate the title). Nothing here depends on a language or a script.
function faultyTitles(ctx, titles) {
    const faulty = [];
    for (const t of titles) {
        const stock = ctx.stockTitles?.get(t.label);
        const stockShare = stock?.ellipsized ? stock.share : 1;
        const fault = t.ellipsized && !(t.natural > 0 && t.share >= stockShare);
        if (fault)
            faulty.push(t.label);
        console.log(`m3e-bench title "${t.label.text}": allocated ${t.label.width} px, natural ${t.natural} px` +
            `${t.ellipsized ? ', TRUNCATED' : ''}` +
            `${t.ellipsized ? ` (visible ${Math.round(100 * t.share)} %, stock ${Math.round(100 * stockShare)} %)` : ''}` +
            `${fault ? ', FAULTY' : ''}`);
    }
    return faulty;
}

export const SETTINGS_SURFACES = {
    // Quick settings: panel open (Main.panel.statusArea.quickSettings.menu.open), with test tiles at the end of the
    // grid: plain tile (QuickToggle), tile with a menu (QuickMenuToggle: halves of the split button measured
    // separately), slider (QuickSlider at 70 %), system row (QuickSettingsItem .quick-settings-system-item:
    // battery = QuickToggle .power-item, .icon-button buttons like those of status/system.js). Two more tiles carry
    // a CJK and an Arabic title (width-sensitive text in other scripts: truncation witness). Margins: 2 px in the
    // panel (surroundings = panel background); 1 px for the halves of the split button (2 dp gap between them).
    settings: {
        open: async ctx => {
            const qs = Main.panel.statusArea.quickSettings;
            const tile = new QuickSettings.QuickToggle({title: 'Tile', subtitle: 'Subtitle',
                iconName: 'night-light-symbolic', toggleMode: true});
            const split = new QuickSettings.QuickMenuToggle({title: 'Menu tile', subtitle: 'Subtitle',
                iconName: 'network-wireless-symbolic', toggleMode: true});
            const tileCjk = new QuickSettings.QuickToggle({title: '接続を共有する', subtitle: '字幕',
                iconName: 'night-light-symbolic', toggleMode: true});
            const tileArabic = new QuickSettings.QuickToggle({title: 'مشاركة الاتصال', subtitle: 'عنوان فرعي',
                iconName: 'night-light-symbolic', toggleMode: true});
            const slider = new QuickSettings.QuickSlider({iconName: 'audio-volume-high-symbolic',
                menuEnabled: true});
            slider.slider.value = 0.7;
            // The track (-barlevel-height, 31 px) is drawn inside the slider's own allocation: St alone allocates
            // fewer pixels and clips it. In a session m3e-motion makes the slider as high as its bar handle
            // (SLIDER_HEIGHT, components/slider.js); the bench, which does not load it, gives the same room.
            slider.slider.style = `min-height: ${SLIDER_HEIGHT}px;`;
            // Sliders of the handle review: 0 %, 50 % and 100 % (visual review). Handle measured on a short .slider
            // (40 px, 0 %) put on the witness background: the active part is not drawn at 0 % and the handle covers
            // more of the cell than the rest of the track (dominant colour = handle).
            const sliders = [0, 0.5, 1].map(v => {
                const c = new QuickSettings.QuickSlider({iconName: 'display-brightness-symbolic'});
                c.slider.value = v;
                return c;
            });
            const handle = new Slider(0);
            handle.set({x: 160, y: 300, width: 40, height: SLIDER_HEIGHT});
            Main.layoutManager.uiGroup.add_child(handle);
            // Tile title truncation witness (native and test tiles): 12 px wide badge, plus 12 px per faulty title
            // (ellipsized by Pango and more truncated than under the stock sheet, see faultyTitles). Measured in
            // width (expected 12: no faulty title). Put on the witness background, outside the panel; titles and
            // widths in the Shell log. Witness colour (outside the palette, like the bench's witness background):
            // black on the grey background.
            const titlesWitness = new St.Widget({x: 160, y: 200, width: 12, height: 12,
                style: 'background-color: #000000;'});
            Main.layoutManager.uiGroup.add_child(titlesWitness);
            const system = new QuickSettings.QuickSettingsItem({style_class: 'quick-settings-system-item',
                reactive: false});
            const row = new St.BoxLayout();
            system.child = row;
            const battery = new QuickSettings.QuickToggle({title: '80%', iconName: 'battery-good-symbolic'});
            battery.add_style_class_name('power-item');
            row.add_child(battery);
            row.add_child(new Clutter.Actor({x_expand: true}));
            const iconButton = icon => new QuickSettings.QuickSettingsItem({style_class: 'icon-button',
                can_focus: true, icon_name: icon});
            const settingsButton = iconButton('emblem-system-symbolic');
            row.add_child(settingsButton);
            row.add_child(iconButton('system-lock-screen-symbolic'));
            row.add_child(iconButton('system-shutdown-symbolic'));
            ctx.tiles = [tile, split, tileCjk, tileArabic, slider, ...sliders, system, titlesWitness, handle];
            qs.menu.addItem(tile);
            qs.menu.addItem(split);
            qs.menu.addItem(tileCjk);
            qs.menu.addItem(tileArabic);
            qs.menu.addItem(slider, 2);
            for (const c of sliders)
                qs.menu.addItem(c, 2);
            qs.menu.addItem(system, 2);
            qs.menu.open(BoxPointer.PopupAnimation.NONE);
            const halves = split.get_child();
            ctx.actors = {panel: qs.menu.box, tile, head: halves.get_first_child(),
                arrow: halves.get_last_child(), slider: slider.slider, handle, battery,
                settingsButton, titlesWitness, grid: qs.menu._grid};
            // Truncation of every title under the stock sheet, same run, same locale: the reference of the
            // "faulty title" test (see faultyTitles). The candidate sheet is put back afterwards.
            await ctx.useSheet('stock');
            ctx.stockTitles = new Map(measureTitles(ctx.actors.grid).map(t => [t.label, t]));
            await ctx.useSheet('candidate');
        },
        cells: ctx => {
            const faulty = faultyTitles(ctx, measureTitles(ctx.actors.grid));
            ctx.actors.titlesWitness.width = 12 * (1 + faulty.length);
            return [
                {row: 'settings-panel', actor: ctx.actors.panel, margin: 24},
                {row: 'settings-tile', actor: ctx.actors.tile, margin: 2},
                {row: 'settings-split', actor: ctx.actors.head, margin: 1},
                {row: 'settings-split-menu', actor: ctx.actors.arrow, margin: 1},
                {row: 'settings-slider', actor: ctx.actors.slider, margin: 2},
                {row: 'settings-battery', actor: ctx.actors.battery, margin: 2},
                {row: 'settings-system', actor: ctx.actors.settingsButton, margin: 2},
                {row: 'settings-slider-handle', actor: ctx.actors.handle, margin: 6},
                {row: 'settings-titles', actor: ctx.actors.titlesWitness, margin: 12},
            ];
        },
        states: ['normal', 'hover', 'pressed', 'focus', 'active', 'disabled'],
        close: closeSettings,
    },

    // Tile menu: test QuickMenuToggle, checked (header icon .active), added to the open panel, menu open without
    // animation. Header (icon, title, subtitle); items: label at the bench size (colour measured), item (height,
    // corners, layers), switches off / on (PopupSwitchMenuItem), checkboxes (CheckBox). An unmeasured item between
    // two cells (pseudo-classes set on every cell).
    'settings-menu': {
        open: async ctx => {
            const qs = Main.panel.statusArea.quickSettings;
            const tile = new QuickSettings.QuickMenuToggle({title: 'Tile with menu', subtitle: 'Test tile',
                iconName: 'go-home-symbolic', toggleMode: true, checked: true});
            const m = tile.menu;
            m.setHeader('go-home-symbolic', 'Tile menu', 'Subtitle');
            const text = new PopupMenu.PopupMenuItem('List item');
            text.label.style = TEXT_SIZE;
            const item = new PopupMenu.PopupMenuItem('Item');
            const switchOff = new PopupMenu.PopupSwitchMenuItem('Switch', false);
            const switchOn = new PopupMenu.PopupSwitchMenuItem('Switch on', true);
            const boxes = new PopupMenu.PopupBaseMenuItem({reactive: false});
            const emptyBox = new CheckBox('Checkbox');
            const checkedBox = new CheckBox('Checked box');
            checkedBox.checked = true;
            // Box and label centred in the 56 dp item (the CheckBox fills its height).
            emptyBox.y_align = checkedBox.y_align = Clutter.ActorAlign.CENTER;
            boxes.add_child(emptyBox);
            boxes.add_child(checkedBox);
            // Disabled boxes (reactive = false: St sets :insensitive), empty and checked, and a focused box
            // (pseudo-class set on the CheckBox, ring drawn by its StBin): second row, short labels.
            const boxes2 = new PopupMenu.PopupBaseMenuItem({reactive: false});
            const disabledBox = new CheckBox('A');
            const disabledCheckedBox = new CheckBox('B');
            disabledCheckedBox.checked = true;
            disabledBox.reactive = disabledCheckedBox.reactive = false;
            const focusBox = new CheckBox('C');
            focusBox.add_style_pseudo_class('focus');
            for (const c of [disabledBox, disabledCheckedBox, focusBox]) {
                c.y_align = Clutter.ActorAlign.CENTER;
                boxes2.add_child(c);
            }
            m.addMenuItem(text);
            m.addMenuItem(new PopupMenu.PopupMenuItem('Unmeasured item'));
            m.addMenuItem(item);
            m.addMenuItem(new PopupMenu.PopupMenuItem('Unmeasured item'));
            m.addMenuItem(switchOff);
            m.addMenuItem(switchOn);
            m.addMenuItem(boxes);
            m.addMenuItem(boxes2);
            ctx.tiles = [tile];
            qs.menu.addItem(tile);
            qs.menu.open(BoxPointer.PopupAnimation.NONE);
            m.open(BoxPointer.PopupAnimation.NONE);
            const boxOf = c => c.get_child().get_first_child().get_child();
            ctx.actors = {menu: m.box, header: m._headerIcon, text, item,
                switchOff: descendant(switchOff, 'toggle-switch'), switchOn: descendant(switchOn, 'toggle-switch'),
                emptyBox: boxOf(emptyBox), checkedBox: boxOf(checkedBox),
                disabledBox: boxOf(disabledBox), disabledCheckedBox: boxOf(disabledCheckedBox),
                focusBox: focusBox.get_child().get_first_child(), focusButton: focusBox};
            // Pseudo-class set again after the menus opened (log: real state at measurement time).
            focusBox.add_style_pseudo_class('focus');
        },
        cells: ctx => {
            const fb = ctx.actors.focusButton;
            console.log(`m3e-bench focused checkbox: pseudo-classes "${fb.get_style_pseudo_class() ?? ''}", StBin ` +
                `${ctx.actors.focusBox.width}x${ctx.actors.focusBox.height}`);
            return [
                {row: 'settings-menu', actor: ctx.actors.menu, margin: 8},
                {row: 'settings-menu-header', actor: ctx.actors.header, margin: 2},
                {row: 'settings-menu-text', actor: ctx.actors.text, margin: 2},
                {row: 'settings-menu-item', actor: ctx.actors.item, margin: 2},
                {row: 'settings-switch', actor: ctx.actors.switchOff, margin: 4},
                {row: 'settings-switch-active', actor: ctx.actors.switchOn, margin: 4},
                {row: 'settings-checkbox', actor: ctx.actors.emptyBox, margin: 4},
                {row: 'settings-checkbox-active', actor: ctx.actors.checkedBox, margin: 4},
                {row: 'settings-checkbox-disabled', actor: ctx.actors.disabledBox, margin: 4},
                {row: 'settings-checkbox-active-disabled', actor: ctx.actors.disabledCheckedBox, margin: 4},
                {row: 'settings-checkbox-focus', actor: ctx.actors.focusBox, margin: 4},
            ];
        },
        states: ['normal', 'hover', 'pressed', 'focus'],
        close: closeSettings,
    },
};
