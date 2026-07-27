# Ink testing and operations

## Test layers

Use three layers, with most coverage at the bottom:

1. **Pure behavior tests:** reducers, stream state machines, keymap matching, safe content splitting, selection, focus transitions, and cancellation. These tests should not need a TTY.
2. **Rendered frame tests:** render a component with a fixed terminal width and assert visible output, status, focus, error, and empty states. Pin dimensions and color mode so snapshots do not flap.
3. **PTY smoke tests:** build and run the real CLI in a pseudo-terminal for a small number of flows involving raw mode, arrow keys, paste, alternate screen, cursor movement, resize, suspend, and cleanup.

Test the terminal contract separately from business logic. A component can render the right string while the real process still leaves raw mode enabled or mishandles a multi-byte key sequence.

## `renderToString()`

Use Ink's synchronous string renderer for pure visual components and accessible output paths. It avoids stdout, stdin, terminal listeners, and asynchronous frame timing. It is especially useful for testing status rows, dialogs, message renderers, and layout fragments that do not need live hooks.

Do not use it as proof that raw input, focus registration, resize, alternate screen, cursor positioning, or asynchronous effects work.

## `ink-testing-library`

The library provides helpers such as `lastFrame()`, `frames`, `rerender`, `stdin`, and `unmount`. It is useful for frame assertions, but inspect its compatibility with the installed Ink major before using it for input simulation. The wiki notes that its older release line and Ink 6/7 input changes can make `stdin.write()` unreliable for `useInput` flows.

When input simulation is unreliable, wrap Ink's own render with application providers and assert frames through a project-specific harness, then use node-pty for the keyboard paths that must exercise a real terminal. Keep test utilities typed and local to the app's actual provider tree.

## Debugging

- `render(<App />, {debug: true})` appends each frame and is useful for finding the first wrong render.
- `onRender` can record render duration, but it does not mean stdout has flushed; use `waitUntilRenderFlush()` for that barrier.
- `patchConsole` normally routes console output around the live frame. Direct `process.stdout.write()` can still corrupt the UI.
- Use `useStderr().write()` or a file tailed in a second terminal for high-volume diagnostics.
- React DevTools can inspect the component tree when supported by the installed Ink/React versions; do not assume its profiler integration is meaningful for Ink's custom renderer.
- Use Node CPU profiles to find expensive components, Yoga/layout work, text formatting, or stream handling. Measure at realistic history sizes and terminal widths.

## Operational paths

Test at least these modes:

- Interactive TTY with normal color.
- `NO_COLOR` or monochrome terminal.
- stdout redirected to a pipe or file.
- CI/non-interactive environment.
- Narrow terminal and resize during active work.
- Ctrl+C during idle, streaming, and a child process.
- SIGTERM and process shutdown.
- Ctrl+Z/suspend and resume where the platform supports it.
- Terminal without Unicode, enhanced keyboard, mouse, or hyperlink support.
- Screen-reader mode when accessibility is a stated requirement.

Fast commands such as `--version`, `--help`, completion, and machine-readable subcommands should avoid mounting Ink unless they need its output model.

## Error and cleanup contract

Use an error boundary or a top-level catch that ensures `unmount(error)` runs before printing diagnostics. Await the instance's exit promise when cleanup ordering matters. Check that cleanup:

- Disables raw mode.
- Shows the cursor.
- Leaves the alternate screen.
- Disables Kitty keyboard, bracketed paste, mouse, and focus reporting if enabled.
- Removes stdin, resize, timer, child-process, and signal listeners.
- Restores the native console.
- Does not leave a partial dead frame or duplicate static output.

Calling `render()` twice on one stdout without unmounting is not a supported way to switch modes or options.

## Accessibility verification

Test `INK_SCREEN_READER=true` and any explicit `isScreenReaderEnabled` path. Verify that roles, labels, selected/checked/disabled states, and hidden decorative content produce useful linear text. Check that the app remains operable with keyboard focus and does not rely on color, border geometry, or side-by-side placement alone.

A plain output mode is still valuable even when a screen-reader mode exists: it supports pipes, logs, CI, and users who prefer non-interactive output.

## Ink exemplars and design lessons

Ink-based production CLIs such as Claude Code, GitHub Copilot CLI, Gemini CLI, Wrangler, Gatsby, and Prisma demonstrate a recurring architecture: append-only history above, a live streaming region, input at the bottom, explicit tool/status states, and slash-command or key-driven actions. Study the pattern, not incidental branding.

Useful cross-app lessons that remain valid in Ink:

- fzf: instant filtering, visible match counts, and a clean exit contract.
- lazygit: fixed spatial layout, context-aware actions, and a footer derived from the keymap.
- htop: persistent action hints are better than hidden discoverability.
- Posting and Harlequin: detail-on-Enter, empty states that explain the next action, and serious large-data performance.

Do not import another framework's implementation model into Ink. Borrow the interaction result, then express it through React state, Ink hooks, Yoga layout, and Ink's terminal lifecycle.

## Release checklist

- Confirm the supported Node, React, Ink, and module-format versions.
- Keep interactive and non-interactive output contracts separate.
- Verify startup cost for frequently invoked commands.
- Test build artifacts, ESM imports, bundled versus unbundled execution, and source maps.
- Run lint, typecheck, unit/frame tests, and PTY smoke tests.
- Exercise cleanup under success, cancellation, thrown error, signal, resize, and suspend.
- Document terminal capability fallbacks and screen-reader activation.
