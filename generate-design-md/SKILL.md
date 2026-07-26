---
name: generate-design-md
version: 1.0.0
description: |
  Generate a comprehensive, implementation-agnostic design specification (design.md) from user context. Use when the user wants to "generate design rules", "create UI rules", "build a design spec", "make design standards", or "generate design.md". Produces YAML frontmatter tokens (colors via Material Color Utilities, typography, spacing) plus narrative prose across 12 categories. Supports any platform: web, mobile, desktop, TUI, embedded, kiosk, cross-platform.
---

# Generate Design MD

Produce `_xzy-ai/design.md` — a project-level design specification defining how every future UI should be designed consistently. The output is NOT a design system, component library, wireframe, or code.

## Step 1: Collect Context

Gather whatever the user provides — prompt, reference documents, or both. Extract:

1. **Brand/seed color** — a hex value for Material Color Utilities generation
2. **Font family** — primary typeface for the type scale
3. **Base spacing unit** — e.g., 4px
4. **Target platform(s)** — web, mobile, desktop, TUI, embedded, kiosk, cross-platform
5. **Design direction** — adjectives, references, constraints

If any required input is missing, ask exactly **one** clarifying question.

**Completion:** All five inputs identified or user confirms defaults.

## Step 2: Set Dials

Three dials drive all downstream decisions. Defaults: `VARIANCE=7`, `MOTION=5`, `DENSITY=4`.

| Dial | Range | Controls |
|------|-------|----------|
| `DESIGN_VARIANCE` | 1–10 | Layout experimentation (1=symmetry, 10=asymmetric) |
| `MOTION_INTENSITY` | 1–10 | Animation depth (1=static, 10=cinematic) |
| `VISUAL_DENSITY` | 1–10 | Information per viewport (1=airy, 10=packed) |

User may override conversationally. Do not ask them to edit the file.

**Completion:** Dials set (defaults or user overrides).

## Step 3: Generate Color Scheme

Run the Material Color Utilities script to generate the full MD3 color scheme from the seed color.

```bash
node generate-design-md/scripts/generate-colors.mjs <seed-hex>
```

The script outputs a JSON object with all MD3 color tokens (surface, primary, secondary, tertiary, error, neutral, neutral-variant variants).

**Completion:** Color scheme JSON generated with all required tokens.

**Error:** If the binary fails, fall back to LLM-generated palette with a warning.

## Step 4: Select Typography

Given the font family from Step 1, generate the full type scale:

| Style | Role |
|-------|------|
| `display-xl` | Hero headings |
| `headline-lg` | Section headings |
| `headline-md` | Subsection headings |
| `body-lg` | Primary body text |
| `body-sm` | Secondary text |
| `label-mono` | Metadata, code |
| `label-code` | Inline code |

Each style includes: `fontFamily`, `fontSize`, `fontWeight`, `lineHeight`, `letterSpacing`.

Scale is influenced by `DESIGN_VARIANCE` (higher = more aggressive scaling) and `VISUAL_DENSITY` (higher = tighter leading).

**Completion:** Full type scale generated with all styles.

## Step 5: Define Spacing

Given the base unit from Step 1, generate spacing tokens:

| Token | Derivation |
|-------|------------|
| `unit` | Base unit (e.g., 4px) |
| `gutter` | Unit × 1 or 2 |
| `margin-mobile` | Unit × 4 |
| `margin-desktop` | Unit × 10 |
| `container-max` | 1200–1440px |

Spacing is influenced by `VISUAL_DENSITY` (higher = tighter spacing) and platform (mobile gets smaller margins).

**Completion:** Spacing tokens generated.

## Step 6: Define Layout, Elevation, Shapes

Write narrative rules for:

- **Layout** — Grid system, breakpoints, containment
- **Elevation** — Depth through color/contrast (flat) or shadows (elevated)
- **Shapes** — Corner radius, border style, structural framing

Influenced by `DESIGN_VARIANCE` (higher = more experimental layouts) and platform (mobile = touch-friendly targets).

**Completion:** Layout, elevation, and shapes rules written.

## Step 7: Write Component Rules

Define rules for key components:

- Buttons (primary, secondary, hover states)
- Cards (borders, padding, background)
- Input fields (borders, placeholder style)
- Lists (separation, prefacing)
- Chips/Tags (formatting)
- Icons (style, stroke weight)
- Motion (transitions, animations)

Influenced by all three dials and platform.

**Completion:** Component rules written for all applicable components.

## Step 8: Add Accessibility Constraints

Define accessibility requirements:

- WCAG compliance level (default: AA)
- Touch target minimums (platform-dependent)
- Color contrast ratios
- Keyboard navigation patterns
- Screen reader considerations

**Completion:** Accessibility constraints defined.

## Step 9: Assemble design.md

Combine all artifacts into `_xzy-ai/design.md`:

1. **YAML frontmatter:** Color tokens (from Step 3), typography tokens (Step 4), spacing tokens (Step 5)
2. **Markdown body:** Narrative sections for each category with prose describing the design philosophy and rules

**Completion:** `_xzy-ai/design.md` exists with valid YAML frontmatter and complete markdown body.

## Step 10: Validate

Run validation checks:

1. YAML syntax is valid
2. All 12 categories present
3. Color contrast ratios meet WCAG AA
4. No contradictory rules

**Completion:** All validation checks pass. Report any warnings to user.

## Modules

- [references/CATEGORIES.md](./references/CATEGORIES.md) — Full list of 12 design rule categories with descriptions.
- [references/TOKENS-SCHEMA.md](./references/TOKENS-SCHEMA.md) — YAML frontmatter schema for colors, typography, spacing.
- [references/DIAL-MAPPINGS.md](./references/DIAL-MAPPINGS.md) — Decision tables mapping dial values to concrete design decisions.

## References

- `scripts/generate-colors.mjs` — Material Color Utilities script for color generation
