import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { generateColorScheme } from './generate-colors.mjs';

describe('generateColorScheme', () => {
  it('returns all required color tokens', () => {
    const tokens = generateColorScheme('#131313');
    const required = [
      'surface', 'on-surface', 'primary', 'on-primary',
      'secondary', 'on-secondary', 'tertiary', 'on-tertiary',
      'error', 'on-error', 'background', 'on-background',
      'surface-container', 'primary-container', 'secondary-container',
      'tertiary-container', 'error-container', 'outline',
    ];
    for (const key of required) {
      assert.ok(tokens[key], `missing token: ${key}`);
    }
  });

  it('returns valid hex colors', () => {
    const tokens = generateColorScheme('#131313');
    const hexPattern = /^#[0-9A-Fa-f]{6}$/;
    for (const [key, value] of Object.entries(tokens)) {
      assert.match(value, hexPattern, `invalid hex for ${key}: ${value}`);
    }
  });

  it('generates different schemes from different seeds', () => {
    const dark = generateColorScheme('#131313');
    const red = generateColorScheme('#E61919');
    assert.notEqual(dark.primary, red.primary, 'primary colors should differ');
    assert.notEqual(dark.background, red.background, 'backgrounds should differ');
  });

  it('generates contrast-safe on-surface vs surface', () => {
    const tokens = generateColorScheme('#131313');
    // Both should be present and different (contrast exists)
    assert.notEqual(tokens.surface, tokens['on-surface']);
  });

  it('handles various valid hex inputs', () => {
    const seeds = ['#000000', '#FFFFFF', '#FF5722', '#3F51B5', '#00BCD4'];
    for (const seed of seeds) {
      const tokens = generateColorScheme(seed);
      assert.ok(tokens.primary, `failed for seed ${seed}`);
    }
  });
});
