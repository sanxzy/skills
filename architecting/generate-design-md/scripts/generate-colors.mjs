#!/usr/bin/env node

/**
 * Generate Material Design 3 color scheme from a seed color.
 *
 * Usage: node generate-colors.js <hex-color>
 * Example: node generate-colors.js #131313
 *
 * Uses esm.sh CDN - no local install needed.
 */

import { argbFromHex, hexFromArgb, themeFromSourceColor } from '@material/material-color-utilities';

function generateColorScheme(seedHex) {
  // Parse seed color
  const seedArgb = argbFromHex(seedHex);
  const theme = themeFromSourceColor(seedArgb);

  // Extract color tokens from the generated scheme
  const scheme = theme.schemes.dark; // or .light for light theme

  const tokens = {
    // Surface colors
    surface: hexFromArgb(scheme.surface),
    'surface-dim': hexFromArgb(scheme.surfaceDim),
    'surface-bright': hexFromArgb(scheme.surfaceBright),
    'surface-container-lowest': hexFromArgb(scheme.surfaceContainerLowest),
    'surface-container-low': hexFromArgb(scheme.surfaceContainerLow),
    'surface-container': hexFromArgb(scheme.surfaceContainer),
    'surface-container-high': hexFromArgb(scheme.surfaceContainerHigh),
    'surface-container-highest': hexFromArgb(scheme.surfaceContainerHighest),
    'on-surface': hexFromArgb(scheme.onSurface),
    'on-surface-variant': hexFromArgb(scheme.onSurfaceVariant),
    'inverse-surface': hexFromArgb(scheme.inverseSurface),
    'inverse-on-surface': hexFromArgb(scheme.inverseOnSurface),
    outline: hexFromArgb(scheme.outline),
    'outline-variant': hexFromArgb(scheme.outlineVariant),
    'surface-tint': hexFromArgb(scheme.surfaceTint),

    // Primary colors
    primary: hexFromArgb(scheme.primary),
    'on-primary': hexFromArgb(scheme.onPrimary),
    'primary-container': hexFromArgb(scheme.primaryContainer),
    'on-primary-container': hexFromArgb(scheme.onPrimaryContainer),
    'inverse-primary': hexFromArgb(scheme.inversePrimary),

    // Secondary colors
    secondary: hexFromArgb(scheme.secondary),
    'on-secondary': hexFromArgb(scheme.onSecondary),
    'secondary-container': hexFromArgb(scheme.secondaryContainer),
    'on-secondary-container': hexFromArgb(scheme.onSecondaryContainer),

    // Tertiary colors
    tertiary: hexFromArgb(scheme.tertiary),
    'on-tertiary': hexFromArgb(scheme.onTertiary),
    'tertiary-container': hexFromArgb(scheme.tertiaryContainer),
    'on-tertiary-container': hexFromArgb(scheme.onTertiaryContainer),

    // Error colors
    error: hexFromArgb(scheme.error),
    'on-error': hexFromArgb(scheme.onError),
    'error-container': hexFromArgb(scheme.errorContainer),
    'on-error-container': hexFromArgb(scheme.onErrorContainer),

    // Fixed colors
    'primary-fixed': hexFromArgb(scheme.primaryFixed),
    'primary-fixed-dim': hexFromArgb(scheme.primaryFixedDim),
    'on-primary-fixed': hexFromArgb(scheme.onPrimaryFixed),
    'on-primary-fixed-variant': hexFromArgb(scheme.onPrimaryFixedVariant),
    'secondary-fixed': hexFromArgb(scheme.secondaryFixed),
    'secondary-fixed-dim': hexFromArgb(scheme.secondaryFixedDim),
    'on-secondary-fixed': hexFromArgb(scheme.onSecondaryFixed),
    'on-secondary-fixed-variant': hexFromArgb(scheme.onSecondaryFixedVariant),
    'tertiary-fixed': hexFromArgb(scheme.tertiaryFixed),
    'tertiary-fixed-dim': hexFromArgb(scheme.tertiaryFixedDim),
    'on-tertiary-fixed': hexFromArgb(scheme.onTertiaryFixed),
    'on-tertiary-fixed-variant': hexFromArgb(scheme.onTertiaryFixedVariant),

    // Background
    background: hexFromArgb(scheme.background),
    'on-background': hexFromArgb(scheme.onBackground),
    'surface-variant': hexFromArgb(scheme.surfaceVariant),
  };

  return tokens;
}

// CLI entry point
if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    console.error('Usage: node generate-colors.js <hex-color>');
    console.error('Example: node generate-colors.js #131313');
    process.exit(1);
  }

  const seedHex = args[0];

  // Validate hex format
  if (!/^#[0-9A-Fa-f]{6}$/.test(seedHex)) {
    console.error('Invalid hex color. Use format: #RRGGBB');
    process.exit(1);
  }

  try {
    const tokens = generateColorScheme(seedHex);
    console.log(JSON.stringify(tokens, null, 2));
  } catch (error) {
    console.error('Error generating color scheme:', error.message);
    process.exit(1);
  }
}

export { generateColorScheme };
