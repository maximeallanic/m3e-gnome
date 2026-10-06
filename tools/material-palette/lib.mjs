// Pure palette logic of material-palette (no I/O): argument parsing, scheme selection and colour-role computation.
// Kept apart from palette.mjs (CLI, image reading) so it can be unit-tested; see tests/.

import {
    argbFromHex, Blend, blueFromArgb, DynamicColor, greenFromArgb, Hct, hexFromArgb, MaterialDynamicColors,
    redFromArgb, SchemeContent, SchemeExpressive, SchemeFidelity, SchemeFruitSalad, SchemeMonochrome, SchemeNeutral,
    SchemeRainbow, SchemeTonalSpot, SchemeVibrant,
} from '@material/material-color-utilities';

export const USAGE = 'usage: palette.mjs --config FILE (--image FILE | --color HEX) --mode light|dark [--output FILE]';

export const SCHEMES = {
    'scheme-content': SchemeContent, 'scheme-expressive': SchemeExpressive, 'scheme-fidelity': SchemeFidelity,
    'scheme-fruit-salad': SchemeFruitSalad, 'scheme-monochrome': SchemeMonochrome, 'scheme-neutral': SchemeNeutral,
    'scheme-rainbow': SchemeRainbow, 'scheme-tonal-spot': SchemeTonalSpot, 'scheme-vibrant': SchemeVibrant,
};

// SystemUI's extra roles (frameworks/libs/systemui, monet/CustomDynamicColors.java, android17-release):
// palette, tone in light / dark, opacity in light / dark. Used by the shade (tiles, notifications, sliders).
export const SYSTEMUI_ROLES = {
    surface_effect_0: { palette: 'primaryPalette', tone: [90, 20], opacity: [0.5, 0.5] },
    surface_effect_1: { palette: 'neutralPalette', tone: [98, 6], opacity: [0.54, 0.54] },
    surface_effect_2: { palette: 'primaryPalette', tone: [100, 90], opacity: [0.32, 0.15] },
    surface_effect_3: { palette: 'primaryPalette', tone: [40, 90], opacity: [0.15, 0.10] },
};

export function parseArgs(argv) {
    const args = {};
    for (let i = 0; i < argv.length; i += 2) {
        const key = argv[i];
        if (!key.startsWith('--') || argv[i + 1] === undefined)
            throw new Error(`bad argument: ${key}`);
        args[key.slice(2)] = argv[i + 1];
    }
    if (!args.config || !args.mode || (!args.image === !args.color))
        throw new Error(USAGE);
    if (!['light', 'dark'].includes(args.mode))
        throw new Error(`mode must be light or dark, not ${args.mode}`);
    return args;
}

export function colorEntry(argb, opacity) {
    const hex = hexFromArgb(argb);
    const entry = {
        hex, hex_stripped: hex.slice(1),
        red: String(redFromArgb(argb)), green: String(greenFromArgb(argb)), blue: String(blueFromArgb(argb)),
        alpha: '1',
    };
    if (opacity !== undefined)
        entry.opacity = String(opacity);
    return entry;
}

export const snake = name => name.replace(/[A-Z]/g, c => `_${c.toLowerCase()}`).replace(/(\D)(\d)/g, '$1_$2');

export function schemes(seed, cfg) {
    const Scheme = SCHEMES[cfg.scheme];
    if (!Scheme)
        throw new Error(`unknown scheme ${cfg.scheme}`);
    const hct = Hct.fromInt(seed);
    return {
        light: new Scheme(hct, false, cfg.contrast, cfg.spec, cfg.platform),
        dark: new Scheme(hct, true, cfg.contrast, cfg.spec, cfg.platform),
    };
}

/** Colour roles of `seed` (ARGB int) for `cfg` (palette.json settings); `mode` picks the `default` variant. */
export function buildColors(seed, cfg, mode) {
    const s = schemes(seed, cfg);
    const mdc = new MaterialDynamicColors();
    const colors = {};
    const put = (name, light, dark, opacity = [undefined, undefined]) => {
        const l = colorEntry(light, opacity[0]), d = colorEntry(dark, opacity[1]);
        colors[name] = { light: l, dark: d, default: mode === 'dark' ? d : l };
    };

    // Every role MaterialDynamicColors exposes (allColors leaves out shadow, scrim, surface_variant… in the 2025 spec).
    for (const key of Object.getOwnPropertyNames(MaterialDynamicColors.prototype)) {
        const dc = key === 'constructor' || typeof mdc[key] !== 'function' || mdc[key].length ? null : mdc[key]();
        if (dc instanceof DynamicColor)
            put(snake(dc.name), dc.getArgb(s.light), dc.getArgb(s.dark));
    }
    put('source_color', seed, seed);
    for (const [name, role] of Object.entries(SYSTEMUI_ROLES)) {
        const tone = isDark => s[isDark ? 'dark' : 'light'][role.palette].tone(role.tone[isDark ? 1 : 0]);
        put(name, tone(false), tone(true), role.opacity);
    }
    // Custom colours, computed like matugen's [config.custom_colors] (src/color/color.rs, make_custom_color): the colour
    // is harmonized toward the seed if `blend`, a scheme of the same variant and spec is built from it, and its primary
    // roles become <name>, on_<name>, <name>_container, on_<name>_container.
    for (const [name, c] of Object.entries(cfg.custom_colors ?? {})) {
        const original = argbFromHex(c.color);
        const cs = schemes(c.blend ? Blend.harmonize(original, seed) : original, cfg);
        const role = r => [mdc[r]().getArgb(cs.light), mdc[r]().getArgb(cs.dark)];
        put(name, ...role('primary'));
        put(`on_${name}`, ...role('onPrimary'));
        put(`${name}_container`, ...role('primaryContainer'));
        put(`on_${name}_container`, ...role('onPrimaryContainer'));
        put(`${name}_source`, original, original);
        put(`${name}_value`, original, original);
    }

    return colors;
}
