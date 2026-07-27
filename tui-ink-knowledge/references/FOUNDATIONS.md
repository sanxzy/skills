# Ink foundations

## React for the terminal

Ink is a React renderer, not a terminal widget toolkit. A component returns JSX, React reconciles the tree, Ink maps host elements to terminal-oriented nodes, Yoga computes layout, and a renderer writes the resulting cell grid. Browser concepts map approximately as follows:

| React/web idea | Ink idea |
|---|---|
| DOM | Terminal character-cell grid |
| `div` | `<Box>` |
| `span` | `<Text>` |
| CSS flexbox | Yoga style props |
| Browser paint | Output buffer to ANSI |
| DOM diff | React reconciliation plus frame diffing |
| Browser events | Raw stdin parsed into `useInput` events |
| SSR string output | `renderToString()` |

React still owns props, state, effects, refs, context, memoization, and component lifecycle. The terminal changes the constraints: every position is a cell, text width is not string length, and a terminal is a byte stream rather than a browser frame buffer.

## Frame pipeline

A state change or key event follows this path:

1. React schedules work.
2. React commits host mutations through Ink's custom reconciler.
3. Host nodes and Yoga nodes are updated.
4. `resetAfterCommit` recalculates layout for the current terminal width.
5. The renderer walks the layout tree.
6. Text is squashed, measured, wrapped, styled, and written into an Output cell buffer.
7. Backgrounds, borders, clipping, and transforms are applied.
8. The buffer becomes an ANSI string.
9. `log-update` compares the new frame with the previous frame.
10. Ink emits cursor movement, erasure, and changed content to stdout, optionally wrapped in synchronized output sequences.

The whole React tree can participate in reconciliation while the terminal receives only the output needed to move from the previous frame to the next. A large live tree can still be expensive: reconciliation, Yoga measurement, string construction, and output diffing all occur before bytes reach the terminal.

## Terminal constraints

The terminal is a fixed grid, conventionally around 80×24 but variable at runtime. Ink reads the current columns and rows and falls back to terminal-size detection or 80×24. Layout is recomputed on resize; never cache positions as if the terminal were a fixed canvas.

Important consequences:

- There is no sub-cell positioning, alpha blending, z-index, or browser-style overflow model.
- Box-drawing characters occupy cells and may fail on minimal terminals; supply readable Unicode or ASCII alternatives where compatibility matters.
- CJK, emoji, combining marks, and ANSI styling affect printed width. Do not use `.length` for layout or truncation.
- A color capability ladder exists: named ANSI colors, 256-color values, and truecolor. Design semantic tokens and degrade gracefully.
- The terminal does not natively retain application frames. Ink emulates updates with cursor control, erasure, diffing, and synchronized output.
- Mouse reports and terminal focus reports require opt-in escape protocols and are not universally available.

## Interactive and non-interactive rendering

Ink detects whether stdout is a usable TTY and whether the process is running in CI. Interactive rendering can use raw mode, cursor control, resize handling, alternate-screen output, and keyboard protocols. Non-interactive rendering must produce stable text suitable for pipes and logs.

Do not let spinners, prompts, cursor movement, or ANSI UI leak into a command substitution or CI log. Separate UI chrome from the command's result: terminal interaction belongs on a TTY or stderr, while the selected value or machine-readable result belongs on stdout.

## Inline versus alternate screen

Use inline rendering when the user summons a short interaction and expects a receipt in scrollback: a picker, prompt, confirmation, or bounded progress display. Use `alternateScreen: true` for a long-lived workspace such as a dashboard, editor-like tool, monitor, or full-screen REPL. Ink returns to the primary buffer on unmount when alternate-screen rendering is active.

Alternate screen is meaningful only for an interactive TTY. It is not a substitute for non-TTY output handling. A full-screen app must also restore raw mode, cursor visibility, keyboard protocols, console patching, and signal handlers during every exit path.

## Concurrent rendering and timing

Legacy rendering is the default and commits synchronously. `concurrent: true` enables React concurrent scheduling and is required for features such as Suspense, transitions, and deferred values to behave as intended. It changes timing: tests may need to await commits, and code must not assume that a state update is already visible until the appropriate flush completes.

`maxFps` throttles frame generation, with a default around 30 FPS in the documented Ink API. Debug and accessibility paths can have different timing. `waitUntilRenderFlush()` is the synchronization point when code must run after pending render work and stdout writes have settled.

## Terminal lifecycle

A robust Ink application has one owner for lifecycle. The owner should:

- Enter raw mode only while interactive input needs it.
- Treat Ctrl+C as an intentional exit or route it to the app's cancellation policy.
- Restore terminal state on normal exit, thrown errors, rejected streams, SIGINT, SIGTERM, and suspend/resume.
- Show the cursor and leave alternate screen before printing a failure trace.
- Remove resize, stdin, timer, child-process, and signal listeners.
- Await `waitUntilExit()` when the process needs a completion barrier.

`useApp().suspendTerminal()` is the safe seam for temporarily releasing the terminal while opening an editor or running an external interactive program. Do not write arbitrary output while Ink owns the same cursor and screen region.

## Architecture terms

- **React tree:** application components and state.
- **Host tree:** Ink DOM elements such as `ink-root`, `ink-box`, and `ink-text`.
- **Yoga tree:** layout nodes synchronized with host nodes.
- **Output buffer:** virtual cell grid containing styled characters, clipping, and writes.
- **Dynamic output:** the region redrawn on each live frame.
- **Static output:** append-only output emitted above the dynamic region.
- **Frame diff:** cursor and erase operations that reconcile terminal output between frames.

Use these terms when diagnosing a problem. For example, a wrong panel width is usually a Yoga/layout issue; a shifted colored cell may be an Output width or ANSI issue; stale history belongs to static/dynamic ownership; a flicker problem belongs to throttling, diffing, or synchronized writes.
