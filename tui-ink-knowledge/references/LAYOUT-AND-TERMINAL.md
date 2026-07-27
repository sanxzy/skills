# Ink layout and terminal design

## Yoga layout

Ink's layout engine is Yoga flexbox. Styles are props rather than CSS classes. Start with the outer contract, then let flexbox distribute available cells:

```tsx
<Box flexDirection="column" height="100%">
  <Header />
  <Box flexGrow={1} flexDirection="row">
    <Sidebar width={30} />
    <Main flexGrow={1} />
  </Box>
  <Footer />
</Box>
```

Use `flexGrow={1}` on the region that owns remaining space, `flexShrink={0}` for load-bearing controls, and explicit `minWidth` or `minHeight` only where content requires a floor. Prefer relative sizing, percentages, flex growth, and max/min constraints over absolute coordinates.

A `<Text>` node has a custom Yoga measure function. Layout depends on text width, wrapping mode, padding, and borders. Changing text can therefore trigger both measurement and output work.

## Layout patterns

Choose the workflow shape before adding components:

- **Persistent panels:** fixed regions with focus moving between them. Keep spatial positions stable.
- **Miller columns:** parent, current, and preview for hierarchical data; collapse to one pane when narrow.
- **Drill-down:** list to detail with a back stack and Escape to return; it degrades well on small terminals.
- **Dashboard:** independent widgets with separate data cadences and focus.
- **IDE three-panel:** navigator, primary editor/content, and details/output; make side regions collapsible.
- **Overlay:** bounded inline picker, confirmation, or short-lived prompt.
- **Tabbed panel:** related views of the same selected object; keep the global layout stable.

The terminal edge already frames the app. Avoid an outer full-screen border plus nested borders. Use a border when it separates dynamic panes or communicates focus; use whitespace when a border adds no information.

## Responsive pressure test

Plan the degradation ladder explicitly:

- **Wide:** show the full layout and optional preview/detail regions.
- **Standard 80–120 columns:** preserve the primary workflow; move low-priority detail to Enter or a modal.
- **Narrow 60–80 columns:** collapse to one column or one primary pane; hide preview and low-priority fields.
- **Too small:** render a clear minimum-size message instead of overlapping, wrapping every label, or crashing.

Use `useWindowSize()` for current dimensions and recalculate from those dimensions. `useBoxMetrics()` is useful when content height is not predictable. Truncate dense cells rather than wrapping them; use detail-on-Enter to preserve access to hidden fields.

## Text and cell width

Text wrapping is a visual and data-model decision. Use `wrap="wrap"` for prose, hard wrapping only when character-level breaks are acceptable, and truncate modes for single-line labels, paths, and table cells. Reserve space for the ellipsis.

Never calculate visible width with `.length`. ANSI sequences occupy no cells; CJK and many emoji occupy two; combining marks may occupy zero. Ink uses width-aware measurement internally, but application code that builds tables, truncates paths, or aligns transformed strings must also be width-aware.

## Hierarchy and density

A terminal has no font-size hierarchy. Use position, bold, dim, reverse video, indentation, whitespace, symbols, and semantic border colors. Use reverse video or a clear background treatment for the current selection. Combine two or three signals for focus, but do not encode one state four different ways.

Choose density deliberately:

- Pack live tables, monitors, process lists, and logs.
- Pad forms, prose, confirmations, and single decisions.
- Keep the main data region larger than chrome. Remove decorative frames, repeated labels, and always-on markers that do not convey information.

## Semantic color and themes

Define roles such as `text.primary`, `text.muted`, `status.success`, `status.warning`, `status.error`, `border.default`, and `border.focus`, then map them to Ink color props. Named colors are safest across user themes; hex, `ansi256(...)`, and `rgb(...)` are available where the target terminal supports them.

Honor `NO_COLOR` and provide a readable monochrome path. Pair color with words, letters, symbols, position, or shape. Treat light/dark and community palette support as token-mapping concerns, not scattered color literals. Nerd-font icons have no reliable runtime detection; make them explicit opt-in and provide text symbols or ASCII alternatives.

## Borders and backgrounds

Single-line borders are the safe default. Rounded or bold borders can indicate a distinct surface or focused region, but nested heavy chrome quickly consumes terminal cells. A contrasting panel background can leak through border cells and create visible steps; keep border and panel backgrounds coherent.

Use per-side borders for separators and selective emphasis. Keep the focus indicator visible in monochrome through weight, reverse video, title changes, or a label as well as color.

## Alternate screen and inline output

The primary buffer is scrollback; the alternate buffer is a temporary workspace. Ink's `alternateScreen: true` is appropriate for a session users inhabit and restores the primary buffer at exit when the output is an interactive TTY. It is inappropriate for a short command whose receipt should remain in scrollback.

For a picker or command substitution, keep UI chrome away from stdout and print only the selected result to stdout. A bounded inline view preserves shell context better than taking over the entire terminal.

## Transform and terminal escapes

`<Transform>` operates on already-rendered lines after styling and before output placement. ANSI-aware manipulation is mandatory. Do not change the measured dimensions unexpectedly: Yoga measured before the transform, so adding/removing width can misalign the frame.

Use terminal escape capabilities sparingly and restore them:

- OSC 8 for hyperlinks, with plain-text degradation.
- OSC 52 for write-only clipboard copy, with local fallback.
- OSC 9/777 for rare completion notifications.
- DEC 2026 synchronized output when Ink manages the frame.
- Alternate screen, cursor visibility, bracketed paste, and enhanced keyboard modes only while active and only with cleanup.

Direct `useStdout().write()` bypasses the React/Yoga/output model. Reserve it for controlled side channels such as a receipt, an escape sequence, or output that is intentionally outside the live tree.
