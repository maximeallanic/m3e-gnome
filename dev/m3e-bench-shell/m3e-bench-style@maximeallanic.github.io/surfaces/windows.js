// Surfaces driven by test client windows: window previews, Alt+Tab, workspace switcher.
import GLib from 'gi://GLib';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as AltTab from 'resource:///org/gnome/shell/ui/altTab.js';
import * as WorkspaceSwitcherPopup from 'resource:///org/gnome/shell/ui/workspaceSwitcherPopup.js';

import {wait, waitUntil} from '../tools.js';
import {launchClient, killClients} from './client-window.js';
import {TEXT_SIZE, findActor} from './common.js';
import {closeOverview, openOverview} from './overview.js';

export const WINDOW_SURFACES = {
    // Window previews: test window (client-preview.js, gjs + Gtk 4) started on the nested Shell's Wayland socket,
    // overview open, preview overlay shown (WindowPreview.showOverlay(false)): close button (.window-close) and
    // title (.window-caption). Title text colour measured on a test tooltip with the same classes, at the bench
    // size; title height on a test tooltip at the real size (outside the overview's workspace scale); corners of the
    // pressed state on a test close button (plain background). Client killed by PID on closing.
    previews: {
        open: async ctx => {
            const window = await launchClient(ctx);
            await openOverview(false);
            const preview = await waitUntil(() => findActor(Main.layoutManager.overviewGroup,
                e => e.metaWindow === window && typeof e.showOverlay === 'function'), 3000);
            if (!preview)
                throw new Error('preview of the test window not found');
            preview.showOverlay(false);
            ctx.preview = preview;
            await wait(200);
            const textTitle = new St.Label({style_class: 'window-caption', text: 'Title', x: 160, y: 900,
                style: TEXT_SIZE});
            Main.layoutManager.uiGroup.add_child(textTitle);
            // The test button is put on a witness background (grey, outside the palette): the real button lies on its
            // window preview, but on the overview background a primary button is invisible in light mode, where the
            // light overview is primary itself.
            const closeWitness = new St.Widget({x: 580, y: 880, width: 80, height: 80,
                style: 'background-color: #808080;'});
            Main.layoutManager.uiGroup.add_child(closeWitness);
            const testClose = new St.Button({style_class: 'window-close', icon_name: 'preview-close-symbolic',
                x: 600, y: 900});
            Main.layoutManager.uiGroup.add_child(testClose);
            // Test tooltip at the real size: the preview is drawn at the overview's workspace scale (~1.04 observed:
            // a 24 logical px tooltip measured 25.0 to 25.03 px on screen).
            const shapeTitle = new St.Label({style_class: 'window-caption', text: 'Bench test window', x: 1000,
                y: 900});
            Main.layoutManager.uiGroup.add_child(shapeTitle);
            ctx.actors = {close: preview._closeButton, title: preview._title, textTitle, testClose, closeWitness,
                shapeTitle};
        },
        cells: ctx => [
            {row: 'preview-close', actor: ctx.actors.close, margin: 4},
            {row: 'preview-close-shape', actor: ctx.actors.testClose, margin: 6},
            {row: 'preview-title', actor: ctx.actors.title, margin: 4},
            {row: 'preview-title-shape', actor: ctx.actors.shapeTitle, margin: 6},
            {row: 'preview-title-text', actor: ctx.actors.textTitle, margin: 6},
        ],
        states: ['normal', 'hover', 'pressed'],
        close: async ctx => {
            ctx.actors?.textTitle.destroy();
            ctx.actors?.testClose.destroy();
            ctx.actors?.closeWitness.destroy();
            ctx.actors?.shapeTitle.destroy();
            ctx.actors = null;
            try {
                ctx.preview?.hideOverlay(false);
            } catch {}
            ctx.preview = null;
            try {
                await closeOverview();
            } finally {
                killClients(ctx);
            }
        },
    },

    // Alt+Tab: two test windows (client-preview.js, two processes: two apps), AppSwitcherPopup opened through the
    // API: show(false, null, 0) (null mask), then the "no modifier" timer (1.5 s, which would ACTIVATE the
    // selection) cancelled and the display forced (_showImmediately). List (.switcher-list), selected item
    // (:selected, set by highlight()), another item (layers), labels at the bench size. Closing: fadeAndDestroy()
    // (no activation), clients killed by PID.
    alttab: {
        open: async ctx => {
            await launchClient(ctx, 'Test window A');
            await launchClient(ctx, 'Test window B');
            const p = new AltTab.AppSwitcherPopup();
            ctx.popup = p;
            if (!p.show(false, null, 0))
                throw new Error('Alt+Tab: no item');
            if (p._noModsTimeoutId) {
                GLib.source_remove(p._noModsTimeoutId);
                p._noModsTimeoutId = 0;
            }
            p._showImmediately();
            await wait(300);
            const list = p._switcherList;
            const n = list._items.length;
            if (n < 2)
                throw new Error(`Alt+Tab: ${n} item(s), 2 expected`);
            const i = p._selectedIndex;
            const j = i === 0 ? 1 : 0;
            const selected = list._items[i], other = list._items[j];
            if (!selected.has_style_pseudo_class('selected'))
                throw new Error('Alt+Tab: selected item without :selected');
            list.icons[i].label.style = TEXT_SIZE;
            list.icons[j].label.style = TEXT_SIZE;
            await wait(200);
            ctx.actors = {list, selected, other, selectedText: list.icons[i].label, otherText: list.icons[j].label};
        },
        cells: ctx => [
            {row: 'alttab-list', actor: ctx.actors.list, margin: 24},
            {row: 'alttab-selected', actor: ctx.actors.selected, margin: 4},
            {row: 'alttab-selected-text', actor: ctx.actors.selectedText, margin: 2},
            {row: 'alttab-item', actor: ctx.actors.other, margin: 4},
            {row: 'alttab-item-text', actor: ctx.actors.otherText, margin: 2},
        ],
        states: ['normal', 'hover', 'pressed', 'focus'],
        close: async ctx => {
            ctx.actors = null;
            try {
                ctx.popup?.fadeAndDestroy();
                ctx.popup = null;
                await wait(200);
            } finally {
                killClients(ctx);
            }
            await wait(200);
        },
    },

    // Workspace switcher: one test window (dynamic workspaces: workspace 1 occupied, workspace 2 empty, two
    // indicators), WorkspaceSwitcherPopup opened through the API (display(active workspace)), hide timer (600 ms)
    // cancelled. Container (.workspace-switcher), active (:active) and inactive indicators.
    workspaces: {
        open: async ctx => {
            await launchClient(ctx);
            const wm = global.workspace_manager;
            if (!await waitUntil(() => wm.n_workspaces >= 2, 3000))
                throw new Error('workspaces: only one workspace');
            const p = new WorkspaceSwitcherPopup.WorkspaceSwitcherPopup();
            ctx.popup = p;
            p.display(wm.get_active_workspace_index());
            if (p._timeoutId) {
                GLib.source_remove(p._timeoutId);
                p._timeoutId = 0;
            }
            await wait(300);
            const list = findActor(p, e => e.has_style_class_name?.('workspace-switcher'));
            const indicators = list?.get_children() ?? [];
            const active = indicators.find(e => e.has_style_pseudo_class('active'));
            const inactive = indicators.find(e => !e.has_style_pseudo_class('active'));
            if (!list || !active || !inactive)
                throw new Error('workspace switcher incomplete');
            ctx.actors = {list, active, inactive};
        },
        cells: ctx => [
            {row: 'workspaces-background', actor: ctx.actors.list, margin: 24},
            {row: 'workspaces-active', actor: ctx.actors.active, margin: 4},
            {row: 'workspaces-inactive', actor: ctx.actors.inactive, margin: 4},
        ],
        states: ['normal'],
        close: async ctx => {
            ctx.actors = null;
            try {
                ctx.popup?.destroy();
                ctx.popup = null;
            } finally {
                killClients(ctx);
            }
            await wait(300);
        },
    },
};
