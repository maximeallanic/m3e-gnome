// App grid surfaces: grid, page dots, open folder, dash tooltip.
import Clutter from 'gi://Clutter';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PageIndicators from 'resource:///org/gnome/shell/ui/pageIndicators.js';

import {wait, waitUntil} from '../tools.js';
import {TEXT_SIZE, findActor, placeActors, removeActors} from './common.js';
import {closeOverview, openAppGrid, openOverview} from './overview.js';

export const APP_GRID_SURFACES = {
    // App grid: overview on the grid (Main.overview.showApps). App tile (.overview-tile), closed folder
    // (.overview-tile.app-folder, default folders of org.gnome.desktop.app-folders), label of another tile at the
    // bench size (colour measured), hint of the empty search bar (bench size).
    grid: {
        open: async ctx => {
            const g = await openAppGrid();
            const [tile, other] = g.apps;
            other.icon.label.style = TEXT_SIZE;
            // Real, empty search bar: hint at the bench size (no test bar created then destroyed), without :focus
            // (see openSearch), cursor hidden.
            const bar = Main.overview.searchEntry;
            bar.style = TEXT_SIZE;
            bar.remove_style_pseudo_class('focus');
            bar.clutter_text.set_cursor_visible(false);
            // Leading icon (on_surface) hidden: the text measurement would take it for the text colour.
            const magnifier = bar.get_primary_icon();
            if (magnifier)
                magnifier.opacity = 0;
            ctx.actors = {tile, folder: g.folder, label: other.icon.label, bar, magnifier};
        },
        cells: ctx => [
            {row: 'grid-tile', actor: ctx.actors.tile, margin: 2},
            {row: 'grid-folder', actor: ctx.actors.folder, margin: 2},
            {row: 'grid-text', actor: ctx.actors.label, margin: 2},
            {row: 'search-hint', actor: ctx.actors.bar, margin: 12},
        ],
        states: ['normal', 'hover', 'pressed', 'focus'],
        close: async ctx => {
            if (ctx.actors) {
                ctx.actors.label.style = null;
                ctx.actors.bar.style = null;
                ctx.actors.bar.clutter_text.set_cursor_visible(true);
                if (ctx.actors.magnifier)
                    ctx.actors.magnifier.opacity = 255;
            }
            ctx.actors = null;
            await closeOverview();
        },
    },

    // Page dots: the Shell's PageIndicators (3 pages, page 0 current) in a test .app-folder-dialog actor (colours of
    // the open folder, identical in dark and light; the bench grid has a single page). Dot of the current page
    // (scale 1) and of another page (scale 2/3, opacity 128: pageIndicators.js).
    'page-dots': {
        open: async ctx => {
            const box = new St.BoxLayout({style_class: 'app-folder-dialog', x: 160, y: 200});
            const dots = new PageIndicators.PageIndicators(Clutter.Orientation.HORIZONTAL);
            box.add_child(dots);
            dots.setNPages(3);
            dots.setCurrentPosition(0);
            placeActors(ctx, {box});
            await wait(100);
            const [current, other] = dots.get_children();
            ctx.dots = {current: current.child, other: other.child};
        },
        cells: ctx => [
            {row: 'page-dots-current', actor: ctx.dots.current, margin: 3},
            {row: 'page-dots-other', actor: ctx.dots.other, margin: 3},
        ],
        states: ['normal'],
        close: ctx => {
            ctx.dots = null;
            removeActors(ctx);
        },
    },

    // Open folder: first folder of the grid opened by FolderIcon.open() (AppFolderDialog). Dialog background
    // (.app-folder-dialog), app tile inside the folder, folder title (.folder-name-label, at the bench size:
    // colour measured).
    folder: {
        open: async ctx => {
            const g = await openAppGrid();
            g.folder.open();
            ctx.folder = g.folder;
            const dialog = await waitUntil(() => {
                const d = g.folder._dialog;
                return d?.mapped ? d : null;
            }, 3000);
            if (!dialog)
                throw new Error('folder not open');
            await wait(300);
            const background = findActor(dialog, e => e.has_style_class_name?.('app-folder-dialog'));
            const tile = await waitUntil(() => g.folder.view._orderedItems.find(i => i.mapped), 2000);
            const title = findActor(dialog, e => e.has_style_class_name?.('folder-name-label'));
            if (!background || !tile || !title)
                throw new Error('open folder incomplete');
            title.style = TEXT_SIZE;
            ctx.actors = {background, tile, title};
        },
        cells: ctx => [
            {row: 'folder-background', actor: ctx.actors.background, margin: 24},
            {row: 'folder-tile', actor: ctx.actors.tile, margin: 2},
            {row: 'folder-title', actor: ctx.actors.title, margin: 2},
        ],
        states: ['normal', 'hover', 'pressed', 'focus'],
        close: async ctx => {
            if (ctx.actors)
                ctx.actors.title.style = null;
            ctx.actors = null;
            ctx.folder?._dialog?.popdown();
            ctx.folder = null;
            await wait(100);
            await closeOverview();
        },
    },

    // Dash tooltip (.dash-label = Plain tooltip): app grid open (in the windows view, the tooltip overlaps the
    // bottom of the workspace: cell background half wallpaper, half view), tooltip of the "Show Applications" button
    // shown through the API (DashItemContainer.showLabel()). Text colour on a test tooltip with the same classes, at
    // the bench size.
    tooltip: {
        open: async ctx => {
            await openOverview(true);
            const icon = Main.overview.dash._showAppsIcon;
            icon.showLabel();
            await waitUntil(() => icon.label.visible && icon.label.opacity === 255, 2000);
            await wait(200);
            const test = new St.Label({style_class: 'dash-label', text: 'Tooltip', x: 160, y: 980,
                style: TEXT_SIZE});
            Main.layoutManager.uiGroup.add_child(test);
            ctx.icon = icon;
            ctx.actors = {real: icon.label, test};
        },
        cells: ctx => [
            {row: 'tooltip-dash', actor: ctx.actors.real, margin: 4},
            {row: 'tooltip-dash-text', actor: ctx.actors.test, margin: 6},
        ],
        states: ['normal'],
        close: async ctx => {
            ctx.actors?.test.destroy();
            ctx.actors = null;
            ctx.icon?.hideLabel();
            ctx.icon = null;
            await closeOverview();
        },
    },
};
