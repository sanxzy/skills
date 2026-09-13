# Dial-to-Decision Mappings

Concrete decision tables for each dial value.

## DESIGN_VARIANCE (1–10)

| Value | Layout | Typography | Shapes |
|-------|--------|------------|--------|
| 1 | Perfect symmetry, centered | Standard scale | All square |
| 3 | Slight asymmetry | Moderate scale | Minimal radius |
| 5 | Balanced experimentation | Aggressive tracking | Small radius |
| 7 | Asymmetric grids | Tight leading | Mixed radius |
| 10 | Experimental, broken grids | Extreme scale | Organic shapes |

## MOTION_INTENSITY (1–10)

| Value | Transitions | Scroll | Micro-interactions |
|-------|-------------|--------|-------------------|
| 1 | None | None | None |
| 3 | 150ms ease | Subtle fade | Hover color |
| 5 | 200ms ease-out | Slide-in | Scale on hover |
| 7 | 300ms spring | Parallax | Magnetic hover |
| 10 | 500ms physics | Cinematic | Continuous animation |

## VISUAL_DENSITY (1–10)

| Value | Spacing | Padding | Touch Targets | Information |
|-------|---------|---------|---------------|-------------|
| 1 | 8px base | 32px | 48px min | Airy, sparse |
| 3 | 6px base | 24px | 44px min | Moderate |
| 5 | 4px base | 16px | 40px min | Balanced |
| 7 | 3px base | 12px | 36px min | Dense |
| 10 | 2px base | 8px | 32px min | Packed |

## Platform Modifiers

| Platform | Touch Targets | Spacing | Typography |
|----------|---------------|---------|------------|
| Web | 40px min | Standard | Standard |
| Mobile | 44px min | Tighter margins | Larger body |
| Desktop | 32px min | Standard | Standard |
| TUI | N/A | Monospace grid | Monospace |
| Embedded | 48px min | High contrast | Larger |
| Kiosk | 48px min | High contrast | Larger |
