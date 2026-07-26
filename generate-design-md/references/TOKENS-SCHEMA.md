# Design Tokens Schema

YAML frontmatter structure for `design.md`. Downstream skills validate against this schema.

## Colors

```yaml
colors:
  surface: '#hex'
  surface-dim: '#hex'
  surface-bright: '#hex'
  surface-container-lowest: '#hex'
  surface-container-low: '#hex'
  surface-container: '#hex'
  surface-container-high: '#hex'
  surface-container-highest: '#hex'
  on-surface: '#hex'
  on-surface-variant: '#hex'
  inverse-surface: '#hex'
  inverse-on-surface: '#hex'
  outline: '#hex'
  outline-variant: '#hex'
  surface-tint: '#hex'
  primary: '#hex'
  on-primary: '#hex'
  primary-container: '#hex'
  on-primary-container: '#hex'
  inverse-primary: '#hex'
  secondary: '#hex'
  on-secondary: '#hex'
  secondary-container: '#hex'
  on-secondary-container: '#hex'
  tertiary: '#hex'
  on-tertiary: '#hex'
  tertiary-container: '#hex'
  on-tertiary-container: '#hex'
  error: '#hex'
  on-error: '#hex'
  error-container: '#hex'
  on-error-container: '#hex'
  primary-fixed: '#hex'
  primary-fixed-dim: '#hex'
  on-primary-fixed: '#hex'
  on-primary-fixed-variant: '#hex'
  secondary-fixed: '#hex'
  secondary-fixed-dim: '#hex'
  on-secondary-fixed: '#hex'
  on-secondary-fixed-variant: '#hex'
  tertiary-fixed: '#hex'
  tertiary-fixed-dim: '#hex'
  on-tertiary-fixed: '#hex'
  on-tertiary-fixed-variant: '#hex'
  background: '#hex'
  on-background: '#hex'
  surface-variant: '#hex'
```

## Typography

```yaml
typography:
  display-xl:
    fontFamily: string
    fontSize: string (e.g., '120px')
    fontWeight: string (e.g., '800')
    lineHeight: string (e.g., '102px')
    letterSpacing: string (e.g., '-0.06em')
  headline-lg:
    fontFamily: string
    fontSize: string
    fontWeight: string
    lineHeight: string
    letterSpacing: string
  headline-md:
    fontFamily: string
    fontSize: string
    fontWeight: string
    lineHeight: string
    letterSpacing: string
  body-lg:
    fontFamily: string
    fontSize: string
    fontWeight: string
    lineHeight: string
    letterSpacing: string
  body-sm:
    fontFamily: string
    fontSize: string
    fontWeight: string
    lineHeight: string
    letterSpacing: string
  label-mono:
    fontFamily: string
    fontSize: string
    fontWeight: string
    lineHeight: string
    letterSpacing: string
  label-code:
    fontFamily: string
    fontSize: string
    fontWeight: string
    lineHeight: string
    letterSpacing: string
```

## Spacing

```yaml
spacing:
  unit: string (e.g., '4px')
  gutter: string (e.g., '1px')
  margin-mobile: string (e.g., '16px')
  margin-desktop: string (e.g., '40px')
  container-max: string (e.g., '1440px')
```

## Required Fields

- `colors` — All MD3 color tokens
- `typography` — All 7 type styles
- `spacing` — All 5 spacing tokens

## Optional Fields

- `name` — Project/design system name
- `version` — Schema version
- `generated` — ISO timestamp
