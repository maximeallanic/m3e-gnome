// Top bar and base surfaces.
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {TEXT_SIZE, findAllByClass, placeActors, removeActors} from './common.js';

export const BAR_SURFACES = {
    // Top bar (#panel), nothing to open. Witness: the layout (36 px) must not move.
    // 100 px margin: under the bar, the witness background of the scene covers most of the cell's surroundings
    // (2 x 100 px + 1920 at the bottom against 2 x 36 + 1920 at the top), so it is the cell background.
    // Panel buttons: states forced on the button (the clock's style is on its .clock child, the button's
    // pseudo-class propagates to it). 2 px margin: the surroundings stay inside the bar (button 2 px from the top
    // and bottom edges, 1 px each side + 1 px of the neighbour); cell background = translucent bar background on
    // the witness background. Indicator: dot of the active workspace (expand 1, the widest).
    // Message indicator of the date button: hidden without notifications, made visible for the scenario.
    bar: {
        open: async ctx => {
            const indicator = Main.panel.statusArea.dateMenu._indicator;
            ctx.indicator = {actor: indicator, visible: indicator.visible};
            indicator.visible = true;
        },
        cells: () => {
            const area = Main.panel.statusArea;
            const dots = findAllByClass(area.activities, 'workspace-dot');
            const active = dots.reduce((m, p) => (!m || p.get_transformed_extents().size.width >
                m.get_transformed_extents().size.width ? p : m), null);
            if (!active)
                throw new Error('workspace indicator not found');
            return [
                {row: 'witness-bar', actor: Main.panel, margin: 100},
                {row: 'bar-button', actor: area.quickSettings, margin: 2},
                {row: 'bar-clock', actor: area.dateMenu, margin: 2},
                {row: 'bar-indicator', actor: active, margin: 3},
                {row: 'bar-clock-indicator', actor: area.dateMenu._indicator, margin: 2},
            ];
        },
        states: ['normal', 'hover', 'pressed', 'focus', 'active'],
        close: ctx => {
            if (ctx.indicator)
                ctx.indicator.actor.visible = ctx.indicator.visible;
            ctx.indicator = null;
        },
    },

    // Base: body text outside any component (colour and font inherited from `stage`) and an empty dialog
    // (.modal-dialog, base surface). Dialog margin: its stock shadow (0 12px 8px 12px) spills ~32 px downwards;
    // 48 px of witness background around keep that background the majority of the surroundings.
    // "preview" labels: the same text at the sheet's size, not measured (visual review): Latin, CJK and Arabic, so
    // that fallback fonts and right-to-left layout are seen in the capture.
    base: {
        open: async ctx => {
            placeActors(ctx, {
                text: new St.Label({text: 'Shell body text', x: 160, y: 200, style: TEXT_SIZE}),
                preview: new St.Label({text: 'Shell body text (Body medium) 0123', x: 600, y: 210}),
                previewCjk: new St.Label({text: 'シェルの本文テキスト 外壳正文 0123', x: 600, y: 250}),
                previewArabic: new St.Label({text: 'نص الصدفة الأساسي 0123', x: 600, y: 290}),
                modal: new St.BoxLayout({style_class: 'modal-dialog', x: 160, y: 320, width: 320, height: 200}),
            });
        },
        cells: ctx => [
            {row: 'type-body', actor: ctx.actors.text, margin: 12},
            {row: 'modal-background', actor: ctx.actors.modal, margin: 48},
        ],
        states: ['normal'],
        close: removeActors,
    },
};
