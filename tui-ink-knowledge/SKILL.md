---
name: tui-ink-knowledge
description: Ink.js, React, JSX, Yoga, and terminal UI design knowledge for building, reviewing, debugging, testing, and scaling Ink-based TUIs and interactive CLIs. Use ONLY when the task explicitly involves Ink, inkjs, React terminal interfaces, or an existing Ink application.
---

# Ink.js TUI Knowledge

Use this skill as the Ink-specific companion to broader TUI design guidance. It teaches the architecture, APIs, design rules, and production patterns of Ink.js: React components reconciled into Yoga layout nodes, rendered into terminal cells, diffed into ANSI output, and managed through Node streams.

## Scope

This skill is for:

- Ink applications and libraries.
- React and TypeScript terminal interfaces built with Ink.
- Ink component, hook, layout, input, lifecycle, performance, accessibility, and testing decisions.
- Interactive CLIs that use Ink for their UI, including chat, streaming, task, picker, dashboard, and full-screen workflows.

Do not use this skill for Bubble Tea, Ratatui, Textual, blessed, OpenTUI, or a generic CLI that does not use Ink. Do not replace application-specific package documentation with memory: inspect the installed Ink and React versions when exact behavior matters.

## Read references by problem

| Problem | Read |
|---|---|
| Understand Ink's architecture or explain a render bug | `references/FOUNDATIONS.md` |
| Choose `render()` options, components, hooks, or lifecycle methods | `references/API.md` |
| Design Yoga layout, terminal sizing, colors, borders, alternate screen, or transforms | `references/LAYOUT-AND-TERMINAL.md` |
| Implement input, focus, keymaps, dialogs, paste, cursor, suspend, or terminal escape behavior | `references/INTERACTION.md` |
| Build chat, logs, streaming output, scrolling, virtualization, state, or high-throughput UI | `references/STREAMING-AND-SCALE.md` |
| Test, debug, profile, ship, or review an Ink app | `references/TESTING-AND-OPERATIONS.md` |

Read only the references needed for the current question. For a substantial implementation, read `FOUNDATIONS.md`, `API.md`, and the reference matching the feature.

## Operating workflow

1. **Inspect the project before prescribing APIs.** Read `package.json`, the entrypoint, the current Ink render call, and nearby components. Confirm the Ink major, React major, module format, TypeScript settings, and test runner.
2. **Classify the terminal contract.** Decide whether the command is one-shot output, inline interactive output, or a long-lived full-screen session. Use inline output for summon–choose–exit flows and `alternateScreen: true` for sessions users live in. Keep a machine-readable result on stdout when the command is composed in a pipeline.
3. **Model the workflow.** Identify the data model, the persistent regions, the live region, the 5–8 common actions, focus order, modal states, loading/error/empty states, and cancellation behavior before writing JSX.
4. **Sketch the Yoga tree.** Decide which boxes are rows or columns, which region grows, what is allowed to shrink, how text wraps or truncates, and what collapses at 80×24 and in a narrow tmux split.
5. **Choose the smallest state surface.** Keep local state local. Use reducers or contexts for genuinely shared state. For large apps, separate read state from action callbacks and keep asynchronous stream state explicit.
6. **Keep side effects outside rendering.** Use hooks and injected services for stdin, subprocesses, network calls, timers, terminal escape sequences, and persistence. Never block the event loop with I/O.
7. **Design terminal hygiene.** Ensure Ctrl+C, signals, resize, suspend, alternate-screen transitions, raw mode, cursor visibility, console output, and errors all restore the terminal.
8. **Test the pure behavior first.** Test state transitions and key handling without a TTY, snapshot rendered frames at fixed dimensions, then add only a few PTY smoke flows for real terminal behavior.
9. **Verify the actual target.** Run the repository's lint, typecheck, and tests. Test both a real TTY and non-TTY/CI output when the command is intended to run in automation.

## Ink's central model

Think in this pipeline:

```
React state and props
  -> React reconciliation
  -> Ink host nodes and Yoga layout
  -> Output cell buffer
  -> ANSI string
  -> log-update frame diff
  -> stdout
```

React owns component composition and state. Ink's reconciler maps `<Box>` and `<Text>` to host nodes. Yoga computes integer cell positions from flexbox styles. The renderer paints a virtual grid, handles clipping, borders, styling, and text width, then emits a string. `log-update` transforms the previous frame into the next one with cursor movement and erasure sequences. The terminal interprets the bytes; it does not provide a DOM or a retained frame buffer.

This model explains the most important design rule: describe the current UI declaratively, but keep high-volume or immutable output out of the live tree when it no longer needs to change.

## Universal Ink rules

- Strings belong inside `<Text>`. A string directly under `<Box>` is invalid.
- `<Box>` is a Yoga flex container, not a browser `div`; there is no CSS stylesheet or pixel positioning.
- Use `flexDirection="column"` deliberately for vertical regions. Use `flexGrow={1}` for the region that owns leftover space.
- Use semantic color tokens and preserve meaning in monochrome. Never make color the only status signal.
- Measure terminal cells, not JavaScript string length. CJK, emoji, ANSI sequences, and wrapping change visible width.
- Render on events, not an unconditional fixed-rate loop. Animation and streaming must be throttled or coalesced.
- Keep the UI responsive while work runs. Promise, subprocess, and network results should update state rather than block rendering.
- Use `<Static>` only for append-only content that is complete and will never need mutation.
- Use `useDeferredValue`, throttling, batching, memoization, and virtualization based on measured cost, not speculation.
- Keep `console.*` and diagnostics compatible with Ink's output ownership. Use `useStderr()` or a file for high-volume tracing.
- Provide keyboard parity. Mouse support can augment, but it must never be the only route to an action.
- Design a plain or screen-reader-friendly path when the app matters to users who cannot consume visual terminal layout.

## Review checklist

When reviewing an Ink app, ask:

- Does the render mode match the workflow: inline for short interactions, alternate screen for a session?
- Is there one clear owner for exit, signals, raw mode, and terminal restoration?
- Are strings nested in `<Text>` and are layout decisions expressed through Yoga props?
- Does the layout degrade at 80×24, narrow widths, and small heights without overlapping content?
- Are text cells measured with terminal width semantics and truncation used where wrapping would damage structure?
- Are focus, selection, mode, and disabled states visually and semantically clear?
- Are Ctrl+C, Ctrl+Z, Ctrl+S/Q, Escape, and resize handled intentionally?
- Does async work avoid blocking the UI and support cancellation where users wait?
- Are append-only items static, mutable items live, and large lists virtualized?
- Are render frequency, Yoga cost, and output writes observable and tested?
- Are non-TTY, CI, `NO_COLOR`, screen-reader, and ESM/module-format paths deliberate?
- Do tests cover state transitions, frame output, input handling, cleanup, and at least one real PTY flow where terminal behavior matters?

Recommend a concrete change rather than saying only that the UI should be simpler or faster. Name the specific state, region, render path, or terminal contract that needs to change.
