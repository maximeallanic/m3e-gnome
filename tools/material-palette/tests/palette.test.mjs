// Unit tests for lib.mjs. Run with `npm test` (bundles first: the published library uses extension-less ESM imports).
import test from 'node:test';
import assert from 'node:assert/strict';
import { argbFromHex } from '@material/material-color-utilities';
import { buildColors, colorEntry, parseArgs, snake } from '../lib.mjs';

// Seed and values of the phone this tool was checked against (SPEC_2025, PHONE, contrast 1.0): the library must
// reproduce the system colours byte for byte.
const SEED = argbFromHex('#7B9F1C');
const CFG = { scheme: 'scheme-tonal-spot', spec: '2025', platform: 'phone', contrast: 1.0 };

test('snake converts MaterialDynamicColors names to matugen role names', () => {
    assert.equal(snake('onPrimaryContainer'), 'on_primary_container');
    assert.equal(snake('surfaceContainerHighest'), 'surface_container_highest');
    assert.equal(snake('primaryFixedDim'), 'primary_fixed_dim');
    assert.equal(snake('surface'), 'surface');
});

test('colorEntry has matugen shape', () => {
    assert.deepEqual(colorEntry(argbFromHex('#1c2800')), {
        hex: '#1c2800', hex_stripped: '1c2800', red: '28', green: '40', blue: '0', alpha: '1',
    });
    assert.equal(colorEntry(argbFromHex('#ffffff'), 0.5).opacity, '0.5');
});

test('parseArgs accepts a colour or an image, rejects bad input', () => {
    assert.deepEqual(parseArgs(['--config', 'c.json', '--color', '#fff', '--mode', 'dark']),
        { config: 'c.json', color: '#fff', mode: 'dark' });
    assert.throws(() => parseArgs(['--config', 'c.json', '--mode', 'dark']), /usage/);
    assert.throws(() => parseArgs(['--config', 'c.json', '--color', '#fff', '--image', 'a', '--mode', 'dark']), /usage/);
    assert.throws(() => parseArgs(['--config', 'c.json', '--color', '#fff', '--mode', 'blue']), /mode must be/);
    assert.throws(() => parseArgs(['--config']), /bad argument/);
});

test('2025 spec reproduces the reference Pixel colours', () => {
    const c = buildColors(SEED, CFG, 'light');
    assert.equal(c.primary.light.hex, '#1c2800');
    assert.equal(c.on_primary.light.hex, '#cee29d');
    assert.equal(c.surface_container.light.hex, '#eeefe1');
});

test('default variant follows the mode; SystemUI roles carry an opacity', () => {
    const light = buildColors(SEED, CFG, 'light'), dark = buildColors(SEED, CFG, 'dark');
    assert.equal(light.primary.default.hex, light.primary.light.hex);
    assert.equal(dark.primary.default.hex, dark.primary.dark.hex);
    assert.notEqual(light.primary.light.hex, light.primary.dark.hex);
    assert.equal(light.surface_effect_1.light.opacity, '0.54');
    assert.equal(light.source_color.light.hex, '#7b9f1c');
});

test('custom colours add the four roles plus source/value', () => {
    const cfg = { ...CFG, custom_colors: { ansi_red: { color: '#f44336', blend: true } } };
    const c = buildColors(SEED, cfg, 'dark');
    for (const k of ['ansi_red', 'on_ansi_red', 'ansi_red_container', 'on_ansi_red_container', 'ansi_red_source', 'ansi_red_value'])
        assert.ok(c[k], k);
    assert.equal(c.ansi_red_source.dark.hex, '#f44336');
});

test('unknown scheme is an error', () => {
    assert.throws(() => buildColors(SEED, { ...CFG, scheme: 'scheme-nope' }, 'light'), /unknown scheme/);
});
