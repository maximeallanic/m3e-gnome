// Screenshot UI surface, with layered guards against any real capture.
import Clutter from 'gi://Clutter';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {wait, waitUntil} from '../tools.js';
import {TEXT_SIZE} from './common.js';

// Layered guard against any real capture: (1) no keystroke or click is sent (states forced by pseudo-classes,
// tooltip opened through the API); (2) the methods that write a file or start a recording
// (_onCaptureButtonClicked, _saveScreenshot, _startScreencast) are replaced, for the scenario, by a function that
// refuses and notes the attempt in ctx; (3) the scenario fails if an attempt was noted. open() only captures the
// scene IN MEMORY (screenshot_stage_to_content), without a file.
const CAPTURE_METHODS = ['_onCaptureButtonClicked', '_saveScreenshot', '_startScreencast'];

function blockCapture(ctx, ui) {
    ctx.refusedCaptures = [];
    ctx.blockedMethods = [];
    for (const name of CAPTURE_METHODS) {
        if (typeof ui[name] !== 'function')
            continue;
        ui[name] = async () => {
            ctx.refusedCaptures.push(name);
            console.warn(`m3e-bench capture: ${name} refused (the bench writes no capture)`);
        };
        ctx.blockedMethods.push(name);
    }
    if (!ctx.blockedMethods.includes('_onCaptureButtonClicked'))
        throw new Error('capture: _onCaptureButtonClicked not found, guard impossible');
}

function unblockCapture(ctx, ui) {
    // Removes the instance's own property: the (Shell) prototype method takes its place back.
    for (const name of ctx.blockedMethods ?? [])
        delete ui[name];
    ctx.blockedMethods = null;
}

// :checked pseudo-class of the interface's toggle buttons restored from their `checked` property: the bench's
// "active" state sets then REMOVES :checked on the cells, which also removed it from the buttons really checked
// (observed: in light mode, "Selection" and "shot" without :checked after the dark scenario, Main.screenshotUI
// being reused).
function resyncChecked(ui) {
    for (const b of [ui._selectionButton, ui._screenButton, ui._windowButton, ui._shotButton, ui._castButton,
        ui._showPointerButton]) {
        if (b.checked)
            b.add_style_pseudo_class('checked');
        else
            b.remove_style_pseudo_class('checked');
    }
}

// Tooltip (screenshot.js Tooltip, St.Label .screenshot-ui-tooltip child of Main.screenshotUI) of a given button.
function tooltipOf(ui, button) {
    return ui.get_children().find(c => c.has_style_class_name?.('screenshot-ui-tooltip') && c._widget === button);
}

export const SCREENSHOT_SURFACES = {
    // Screenshot: Main.screenshotUI.open() (image capture mode, area selection checked), capture guard set before
    // (blockCapture). Panel (.screenshot-ui-panel = Floating toolbar), type choice (.screenshot-ui-type-button =
    // Connected button group: "Selection" checked first, "Screen" in the middle, "Window" last, insensitive without
    // a window: visible state by default), shot button of the shot/cast group (.screenshot-ui-shot-cast-button,
    // checked), capture button disc (primary; the ring, separated from the disc by the panel background, is not seen
    // as the same container by measure.py), test "Show pointer" button, tooltip of the "Screen" button opened
    // through the API (Tooltip.open, 300 ms delay); tooltip text colour on a test tooltip with the same classes
    // (child of Main.screenshotUI), at the bench size. :checked resynchronised on opening and closing
    // (resyncChecked). Closing: close(true) (immediate).
    screenshot: {
        open: async ctx => {
            const ui = Main.screenshotUI;
            blockCapture(ctx, ui);
            await ui.open();
            if (!await waitUntil(() => ui.visible && ui.opacity === 255, 3000))
                throw new Error('screenshot: interface not open');
            resyncChecked(ui);
            await wait(300);
            // Tooltip of the "Screen" button: placed above the panel (on the scene background); the capture button's
            // overlaps the type buttons (same rules, visual review).
            const tooltip = tooltipOf(ui, ui._screenButton);
            if (!tooltip)
                throw new Error('screenshot: tooltip of the "Screen" button not found');
            tooltip.open();
            if (!await waitUntil(() => tooltip.visible && tooltip.opacity === 255, 2000))
                throw new Error('screenshot: tooltip not shown');
            const test = new St.Label({style_class: 'screenshot-ui-tooltip', text: 'Tooltip', x: 160, y: 120,
                style: TEXT_SIZE});
            ui.add_child(test);
            // Test panel (same classes): the end of the real panel's rows touches its stadium curve, and the scene
            // background caught in the cell's corner skews the measured corners (observed: "Window" and "Show
            // pointer" in light mode). It carries a type group of two buttons (corners of the last: outer corners
            // full, inner ones 8), a "Show pointer" button and a second, checked one: its shape when pressed
            // (secondary_container layer) is measured, that of the unchecked button (on_surface_variant layer at
            // 10 % over surface_container, in light mode) is below measure.py's resolution (9.5 for 8, visual review).
            // Inline spacings (bench): 12 inside the group like the real group's JS, 16 between the test panel's
            // items so that each cell's margin stays on the panel background.
            const testPanel = new St.BoxLayout({style_class: 'screenshot-ui-panel', x: 400, y: 120,
                style: 'spacing: 16px;'});
            const group = new St.BoxLayout({style_class: 'screenshot-ui-type-button-container', style: 'spacing: 12px;'});
            // Buttons without a label (shape and background only). The insensitive button ("Window") is measured on
            // the real one, background only: its corners, made by :last-child and not by :insensitive, are measured
            // here on a last active button (on_surface background at 12 % too pale in light mode for the corner
            // fit: 9.1 for 8).
            const typeA = new St.Button({style_class: 'screenshot-ui-type-button', width: 88});
            const typeB = new St.Button({style_class: 'screenshot-ui-type-button', width: 88});
            group.add_child(typeA);
            group.add_child(typeB);
            const pointer = new St.Button({style_class: 'screenshot-ui-show-pointer-button',
                icon_name: 'screenshot-ui-show-pointer-symbolic', toggle_mode: true, y_align: Clutter.ActorAlign.CENTER});
            const pointerChecked = new St.Button({style_class: 'screenshot-ui-show-pointer-button',
                icon_name: 'screenshot-ui-show-pointer-symbolic', toggle_mode: true, checked: true,
                y_align: Clutter.ActorAlign.CENTER});
            pointerChecked.add_style_pseudo_class('checked');
            for (const e of [group, pointer, pointerChecked])
                testPanel.add_child(e);
            ui.add_child(testPanel);
            await wait(200);
            if (!ui._selectionButton.checked || !ui._shotButton.checked)
                throw new Error('screenshot: unexpected default state (selection, shot)');
            ctx.ui = ui;
            ctx.actors = {panel: ui._panel, selection: ui._selectionButton, screen: ui._screenButton,
                window: ui._windowButton, shot: ui._shotButton, button: ui._captureButton,
                pointer, pointerChecked, typeB, testPanel, tooltip, test};
        },
        cells: ctx => [
            {row: 'screenshot-panel', actor: ctx.actors.panel, margin: 12},
            {row: 'screenshot-type', actor: ctx.actors.screen, margin: 1},
            {row: 'screenshot-type-active', actor: ctx.actors.selection, margin: 1},
            {row: 'screenshot-type-disabled', actor: ctx.actors.window, margin: 1},
            {row: 'screenshot-type-last', actor: ctx.actors.typeB, margin: 1},
            {row: 'screenshot-shot', actor: ctx.actors.shot, margin: 2},
            {row: 'screenshot-button', actor: ctx.actors.button.get_child(), margin: 4},
            {row: 'screenshot-pointer', actor: ctx.actors.pointer, margin: 4},
            {row: 'screenshot-pointer-checked', actor: ctx.actors.pointerChecked, margin: 4},
            {row: 'screenshot-tooltip', actor: ctx.actors.tooltip, margin: 6},
            {row: 'screenshot-tooltip-text', actor: ctx.actors.test, margin: 6},
        ],
        states: ['normal', 'hover', 'pressed', 'focus', 'active'],
        close: async ctx => {
            const ui = ctx.ui ?? Main.screenshotUI;
            try {
                ctx.actors?.test.destroy();
                ctx.actors?.testPanel.destroy();
                ctx.actors?.tooltip.close();
                ctx.actors = null;
                if (ui.visible)
                    ui.close(true);
                await waitUntil(() => !ui.visible, 2000);
                await wait(100);
                resyncChecked(ui);
            } finally {
                unblockCapture(ctx, ui);
                ctx.ui = null;
            }
            if (ctx.refusedCaptures?.length)
                throw new Error(`screenshot: capture attempt refused (${ctx.refusedCaptures.join(', ')})`);
        },
    },
};
