// material-palette: Material 3 colour roles computed the way a Pixel computes them, written as matugen render data.
//
// Android 16+ builds its dynamic theme with the 2025 colour spec (SpecVersion.SPEC_2025, platform PHONE) of
// material-color-utilities; matugen 4.2 only implements the 2021 spec. This tool uses the official library (pinned in
// package.json) and emits the JSON that `matugen json <file>` renders templates from, with the same shape matugen
// produces itself (colors.<role>.{default,light,dark}.{hex,red,green,blue,…}, mode, is_dark_mode), so templates stay
// unchanged.
//
// Usage:
//   palette.mjs --config FILE (--image FILE | --color HEX) --mode light|dark [--output FILE]
//
// Seed extraction follows Android's WallpaperColors: the image is scaled down to at most 112×112 pixels of area,
// quantized with QuantizerCelebi (128 colours) and ranked by Score.

import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { argbFromHex, argbFromRgb, QuantizerCelebi, Score } from '@material/material-color-utilities';
import { buildColors, parseArgs } from './lib.mjs';

// WallpaperColors.MAX_WALLPAPER_EXTRACTION_AREA (frameworks/base, core/java/android/app/WallpaperColors.java).
const EXTRACTION_AREA = 112 * 112;

function imagePixels(path) {
    const probe = execFileSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=width,height', '-of', 'csv=p=0', path], { encoding: 'utf8' }).trim().split('\n')[0];
    const [w, h] = probe.split(',').map(Number);
    if (!(w > 0 && h > 0))
        throw new Error(`cannot read image size: ${path}`);
    const scale = Math.min(1, Math.sqrt(EXTRACTION_AREA / (w * h)));
    const sw = Math.max(1, Math.round(w * scale)), sh = Math.max(1, Math.round(h * scale));
    const raw = execFileSync('ffmpeg', ['-v', 'error', '-i', path, '-frames:v', '1', '-vf', `scale=${sw}:${sh}:flags=area`,
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], { maxBuffer: 64 * 1024 * 1024 });
    const pixels = [];
    for (let i = 0; i + 2 < raw.length; i += 3)
        pixels.push(argbFromRgb(raw[i], raw[i + 1], raw[i + 2]));
    return pixels;
}

function seedFromImage(path, fallback) {
    const quantized = QuantizerCelebi.quantize(imagePixels(path), 128);
    return Score.score(quantized, { desired: 4, fallbackColorARGB: fallback, filter: true })[0];
}

function main() {
    const args = parseArgs(process.argv.slice(2));
    const cfg = JSON.parse(readFileSync(args.config, 'utf8'));
    const fallback = argbFromHex(cfg.fallback_color);
    const seed = args.image ? seedFromImage(args.image, fallback) : argbFromHex(args.color);
    const colors = buildColors(seed, cfg, args.mode);
    const out = JSON.stringify({ colors, mode: args.mode, is_dark_mode: args.mode === 'dark' }, null, 1);
    if (args.output)
        writeFileSync(args.output, out);
    else
        process.stdout.write(out + '\n');
}

try {
    main();
} catch (e) {
    process.stderr.write(`material-palette: ${e.message}\n`);
    process.exit(1);
}
