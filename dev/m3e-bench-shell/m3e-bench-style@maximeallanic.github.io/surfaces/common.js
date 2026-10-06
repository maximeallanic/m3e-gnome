// Helpers shared by the surface modules: test actors, measured text size, actor search, test media message.
//
// Surface shape (shared with the Python side of the bench):
//   <name>: {
//     open(ctx) -> Promise    opens the surface (menu, panel...); ctx = the bench scene (extension.js)
//     cells(ctx) -> [{row, actor, margin?}]
//                             row = row id of the expected data; actor = the St actor measured; margin (logical px,
//                             optional) = background edge added around the actor's rectangle, for an actor stuck to
//                             others (measure.py finds the container on the background of the cell)
//     states: [...]           grid states, forced through pseudo-classes (normal = none)
//     close(ctx)              closes what open() opened
//   }
import Gio from 'gi://Gio';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as MessageList from 'resource:///org/gnome/shell/ui/messageList.js';

// Measured label colour: bench font size (inline style, the size only) so that glyphs have a solid core; at 14 px
// (Body medium) the most frequent pixel of a glyph is an anti-aliased blend (deltaE 4 to 6 observed). Colour and
// font stay the sheet's; the real size is checked in the visual review.
export const TEXT_SIZE = 'font-size: 32px;';
// Calendar day (40 dp): two digits do not fit at 32 px, 28 px (glyph core still solid).
export const DAY_SIZE = 'font-size: 28px;';

// Test actors put in uiGroup (above the witness background, outside any Shell component), kept in ctx.actors (ctx
// lives for one scenario) and destroyed by removeActors().
export function placeActors(ctx, actors) {
    ctx.actors = actors;
    for (const a of Object.values(actors))
        Main.layoutManager.uiGroup.add_child(a);
}

export function removeActors(ctx) {
    for (const a of Object.values(ctx.actors ?? {}))
        a.destroy();
    ctx.actors = null;
}

// First descendant carrying the given style class (actors private to Shell classes: switch of a
// PopupSwitchMenuItem, box of a CheckBox).
export function descendant(actor, styleClass) {
    for (const e of actor.get_children()) {
        if (e.has_style_class_name?.(styleClass))
            return e;
        const found = descendant(e, styleClass);
        if (found)
            return found;
    }
    return null;
}

// First descendant (depth first) that satisfies the predicate.
export function findActor(actor, predicate) {
    for (const e of actor.get_children()) {
        if (predicate(e))
            return e;
        const found = findActor(e, predicate);
        if (found)
            return found;
    }
    return null;
}

// All descendants carrying the given style class.
export function findAllByClass(actor, styleClass) {
    const found = [];
    const walk = a => {
        for (const e of a.get_children()) {
            if (e.has_style_class_name?.(styleClass))
                found.push(e);
            walk(e);
        }
    };
    walk(actor);
    return found;
}

// Test media message (MessageList.Message + .media-message and three .message-media-control buttons, like
// MediaMessage, without any MPRIS player). Returns {media, buttons}.
export function createMediaMessage() {
    const player = new MessageList.Source({title: 'Test player',
        icon: new Gio.ThemedIcon({name: 'audio-x-generic-symbolic'})});
    const media = new MessageList.Message(player);
    media.add_style_class_name('media-message');
    media.set({title: 'Track title', body: 'Test artist',
        icon: new Gio.ThemedIcon({name: 'audio-x-generic-symbolic'})});
    const buttons = ['media-skip-backward-symbolic', 'media-playback-start-symbolic',
        'media-skip-forward-symbolic'].map(i => media.addMediaControl(i, () => {}));
    return {media, buttons};
}
