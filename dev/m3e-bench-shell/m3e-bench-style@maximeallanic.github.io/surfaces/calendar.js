// Calendar surface (clock menu).
import Clutter from 'gi://Clutter';
import Pango from 'gi://Pango';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as BoxPointer from 'resource:///org/gnome/shell/ui/boxpointer.js';

import {DAY_SIZE} from './common.js';

// Clock menu (DateMenuButton) opened without animation.
export function openCalendar() {
    const dm = Main.panel.statusArea.dateMenu;
    dm.menu.open(BoxPointer.PopupAnimation.NONE);
    return dm;
}

// Label ClutterText of a St.Button (StLabel child, or ClutterText depending on the St version).
function labelTextOf(button) {
    const child = button.get_child();
    console.log(`m3e-bench day label: ${child?.constructor?.name} ${child?.style_class ?? ''}`);
    return child.clutter_text ?? child;
}

export const CALENDAR_SURFACES = {
    // Calendar: clock menu open (Main.panel.statusArea.dateMenu.menu.open). Days (Calendar .calendar-day buttons):
    // today, an ordinary day of the month (geometry and layers, label at the real size) and another ordinary day
    // whose label is at the bench size (colour measured), chosen at least two rows apart (pseudo-classes set on
    // every cell). "Previous month" button (.pager-button). Cards: world clocks (always visible), events (made
    // visible, a test event added to the list), weather (made visible: without a weather service, header only).
    // Visibilities restored by close().
    calendar: {
        open: async ctx => {
            const dm = Main.panel.statusArea.dateMenu;
            const events = dm._eventsItem, clocks = dm._clocksItem, weather = dm._weatherItem;
            ctx.visibles = [[events, events.visible], [clocks, clocks.visible], [weather, weather.visible]];
            ctx.weatherTitle = weather._titleLabel.text;
            openCalendar();
            // After opening: it reloads the event list (EventsSection.setDate).
            events.visible = clocks.visible = weather.visible = true;
            weather._titleLabel.text = 'Weather';
            const box = new St.BoxLayout({style_class: 'event-box', orientation: Clutter.Orientation.VERTICAL});
            box.add_child(new St.Label({text: 'Bench meeting', style_class: 'event-summary'}));
            box.add_child(new St.Label({text: '10:00 – 11:00', style_class: 'event-time'}));
            for (const c of events._eventsList.get_children())
                c.visible = false;
            events._eventsList.add_child(box);
            ctx.event = box;
            const days = dm._calendar._buttons;
            const todayIndex = days.findIndex(b => b.has_style_class_name('calendar-today'));
            if (todayIndex < 0)
                throw new Error('current day not found in the calendar');
            // Two neighbouring cells (side or corner) would touch with their margins: 7-column grid.
            const far = (i, j) => Math.abs(Math.floor(i / 7) - Math.floor(j / 7)) > 1 || Math.abs(i % 7 - j % 7) > 1;
            const ordinary = days.map((b, i) => [b, i]).filter(([b, i]) => far(i, todayIndex) &&
                !b.has_style_class_name('calendar-other-month') && !b.has_style_class_name('calendar-day-with-events'));
            if (ordinary.length < 2)
                throw new Error('not enough ordinary days in the calendar');
            const [day, dayIndex] = ordinary[0];
            const textDay = ordinary.find(([, i]) => far(i, dayIndex))?.[0];
            if (!textDay)
                throw new Error('no second, distant ordinary day');
            const today = days[todayIndex];
            // Labels at 28 px without ellipsis: at 32 px, Pango cuts two digits in the 40 dp day ("...").
            // "Day with events" dot on the current day (visual review: the nested Shell has no calendar service).
            ctx.dotAdded = !today.has_style_class_name('calendar-day-with-events');
            if (ctx.dotAdded)
                today.add_style_class_name('calendar-day-with-events');
            for (const b of [textDay, today]) {
                b.style = DAY_SIZE;
                labelTextOf(b).ellipsize = Pango.EllipsizeMode.NONE;
            }
            // Test current day (same classes, in a .calendar container) put on the witness background: in the menu,
            // in dark mode, the on_primary label (#452b00) is too close to the menu background, which the measurement
            // takes for the cell background and sets apart from the text.
            const testCalendar = new St.Widget({style_class: 'calendar', layout_manager: new Clutter.BinLayout(),
                x: 160, y: 300});
            const testToday = new St.Button({label: '03', style: DAY_SIZE,
                style_class: 'calendar-day calendar-weekend calendar-today'});
            testCalendar.add_child(testToday);
            Main.layoutManager.uiGroup.add_child(testCalendar);
            ctx.testCalendar = testCalendar;
            ctx.actors = {popover: dm.menu.box, day, textDay, today, testToday, pager: dm._calendar._backButton,
                clocks: dm._clocksItem, events, weather};
        },
        cells: ctx => {
            // WorldClocksSection and WeatherSection recompute their visibility asynchronously (apps absent from
            // the nested Shell): set again before every capture.
            for (const [actor] of ctx.visibles)
                actor.visible = true;
            return [
                {row: 'cal-popover', actor: ctx.actors.popover, margin: 24},
                {row: 'cal-day', actor: ctx.actors.day, margin: 2},
                {row: 'cal-day-text', actor: ctx.actors.textDay, margin: 2},
                {row: 'cal-today', actor: ctx.actors.today, margin: 2},
                {row: 'cal-today-text', actor: ctx.actors.testToday, margin: 6},
                {row: 'cal-month-button', actor: ctx.actors.pager, margin: 2},
                {row: 'cal-card-clocks', actor: ctx.actors.clocks, margin: 2},
                {row: 'cal-card-weather', actor: ctx.actors.weather, margin: 2},
            ];
        },
        states: ['normal', 'hover', 'pressed'],
        close: ctx => {
            const a = ctx.actors;
            ctx.actors = null;
            if (a) {
                for (const b of [a.textDay, a.today]) {
                    b.style = null;
                    labelTextOf(b).ellipsize = Pango.EllipsizeMode.END;
                }
                a.weather._titleLabel.text = ctx.weatherTitle ?? '';
                if (ctx.dotAdded)
                    a.today.remove_style_class_name('calendar-day-with-events');
            }
            ctx.testCalendar?.destroy();
            ctx.testCalendar = null;
            ctx.event?.destroy();
            ctx.event = null;
            for (const [actor, visible] of ctx.visibles ?? [])
                actor.visible = visible;
            const events = Main.panel.statusArea.dateMenu._eventsItem;
            for (const c of events._eventsList.get_children())
                c.visible = true;
            ctx.visibles = null;
            Main.panel.statusArea.dateMenu.menu.close(BoxPointer.PopupAnimation.NONE);
        },
    },
};
