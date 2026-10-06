// Screen rectangles of Shell actors, by selector, so that the video scenarios can aim the virtual pointer at a real
// quick settings tile, panel button, app grid icon or switch instead of at guessed pixels.
// Selectors:  panel:<statusArea key>   top bar button (quickSettings, dateMenu, a11y)
//             tile:<title>             quick settings tile whose title matches (case-insensitive)
//             app:<desktop id>         mapped app grid / dash icon of that application
//             switch:<index>           index-th mapped popup menu switch (PopupMenu.Switch), in tree order
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

function* walk(actor) {
    yield actor;
    for (const child of actor.get_children())
        yield* walk(child);
}

const mapped = actor => actor.is_mapped() && actor.get_paint_visibility();

// `.app` and `.title` are accessors that can throw on unrelated actors: those do not match.
function safe(read) {
    try {
        return read();
    } catch {
        return undefined;
    }
}

function find(selector) {
    const sep = selector.indexOf(':');
    const kind = selector.slice(0, sep);
    const arg = selector.slice(sep + 1);
    if (kind === 'panel')
        return Main.panel.statusArea[arg];
    const all = [...walk(global.stage)].filter(mapped);
    if (kind === 'tile')
        return all.find(a => safe(() => a.title)?.toLowerCase() === arg.toLowerCase());
    if (kind === 'app')
        return all.find(a => safe(() => a.app?.get_id()) === arg && a.get_width() > 0);
    if (kind === 'switch')
        return all.filter(a => a instanceof PopupMenu.Switch)[Number(arg)];
    throw new Error(`unknown selector: ${selector}`);
}

export function rectOf(selector) {
    const actor = find(selector);
    if (!actor)
        throw new Error(`no actor for ${selector} (tiles: ${[...walk(global.stage)].filter(mapped).map(a => safe(() => a.title)).filter(Boolean).join(' | ')})`);
    const [x, y] = actor.get_transformed_position();
    const [w, h] = actor.get_transformed_size();
    return JSON.stringify({x: Math.round(x), y: Math.round(y), w: Math.round(w), h: Math.round(h)});
}
