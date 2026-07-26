#!/usr/bin/env bun

import { argbFromHex, hexFromArgb, themeFromSourceColor } from '@material/material-color-utilities';

const args = process.argv.slice(2);

if (args.length === 0) {
  console.error('Usage: generate-colors <hex-color>');
  console.error('Example: generate-colors #131313');
  process.exit(1);
}

const seedHex = args[0];

if (!/^#[0-9A-Fa-f]{6}$/.test(seedHex)) {
  console.error('Invalid hex color. Use format: #RRGGBB');
  process.exit(1);
}

try {
  const seedArgb = argbFromHex(seedHex);
  const theme = themeFromSourceColor(seedArgb);
  const scheme = theme.schemes.dark;

  const tokens = {
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
    primary: hexFromArgb(scheme.primary),
    'on-primary': hexFromArgb(scheme.onPrimary),
    'primary-container': hexFromArgb(scheme.primaryContainer),
    'on-primary-container': hexFromArgb(scheme.onPrimaryContainer),
    'inverse-primary': hexFromArgb(scheme.inversePrimary),
    secondary: hexFromArgb(scheme.secondary),
    'on-secondary': hexFromArgb(scheme.onSecondary),
    'secondary-container': hexFromArgb(scheme.secondaryContainer),
    'on-secondary-container': hexFromArgb(scheme.onSecondaryContainer),
    tertiary: hexFromArgb(scheme.tertiary),
    'on-tertiary': hexFromArgb(scheme.onTertiary),
    'tertiary-container': hexFromArgb(scheme.tertiaryContainer),
    'on-tertiary-container': hexFromArgb(scheme.onTertiaryContainer),
    error: hexFromArgb(scheme.error),
    'on-error': hexFromArgb(scheme.onError),
    'error-container': hexFromArgb(scheme.errorContainer),
    'on-error-container': hexFromArgb(scheme.onErrorContainer),
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
    background: hexFromArgb(scheme.background),
    'on-background': hexFromArgb(scheme.onBackground),
    'surface-variant': hexFromArgb(scheme.surfaceVariant),
  };

  console.log(JSON.stringify(tokens, null, 2));
} catch (error) {
  console.error('Error generating color scheme:', error.message);
  process.exit(1);
}
