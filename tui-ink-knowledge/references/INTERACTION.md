# Ink interaction patterns

## Input pipeline

Ink reads raw stdin, separates byte chunks into key events, parses legacy escape sequences or Kitty CSI-u sequences, and emits structured events to `useInput` subscribers. This is why input handling should consume the `input` string for printable text and named `key` flags for navigation and control keys.

`useInput` enables raw mode while active and removes its listener on cleanup. Make the hook inactive when a component should not receive input; do not rely on visual hiding alone. For text entry, handle return, backspace, cursor movement, paste, cancellation, and submission as separate policies.

Use `usePaste` for bracketed paste. A paste should arrive as one string, not as a sequence of ordinary keypresses. Sanitize or normalize pasted content at the application boundary rather than trying to infer paste from many `useInput` calls.

## Keymap design

Use one semantic keymap as the source for behavior, footer hints, help, and configurable bindings. Favor a modeless or hybrid design for general users: arrows plus `hjkl`, Enter, Space, Tab, and Escape. Modal designs are valid only when a persistent mode indicator, distinct cursor treatment, and discoverable help make the current interpretation obvious.

Conventional defaults are useful: `q` quit, `?` help, `/` search/filter, `n` and `N` next/previous match, Escape cancel/back, Enter confirm/drill in, Space toggle, `r` refresh, Tab and Shift+Tab focus navigation. Do not bind terminal-owned Ctrl+C, Ctrl+Z, Ctrl+\\, or Ctrl+S/Q casually. If an app deliberately changes terminal flow-control behavior, document and restore it.

Discoverability should be layered:

1. Show three to five context-relevant actions in a footer.
2. Let `?` open complete grouped help.
3. Use a leader or which-key surface when the map becomes large.
4. Add a searchable command palette when actions outgrow direct shortcuts.

## Focus

Ink's `useFocus` registers elements in render order. `useFocusManager` cycles or jumps among active ids. Focus order should follow visual reading order, and a dialog or form should trap focus until Escape or completion returns control to the parent.

A focused component should expose at least two signals, such as border/title emphasis plus reverse-video selection or a cursor. `isActive` removes a component from focus participation without destroying its place in the tree. `autoFocus` should be used sparingly and predictably.

Distinguish element focus from terminal-window focus. An application may separately opt into DEC 1004 focus reporting to suppress notifications or dim an unfocused prompt; that is not the same as Ink's element registry.

## Selection, search, and confirmation

For lists and tables:

- Keep selected index separate from scroll offset.
- Use Space for multi-select and a visible marker that survives monochrome output.
- Show match counts and highlight matched substrings.
- Keep filtering responsive; coalesce expensive work.
- Provide detail-on-Enter when columns disappear at narrow widths.
- Confirm destructive actions with friction proportional to consequence, defaulting to No.

For search, use `/`, Enter to accept, Escape to cancel, and `n`/`N` to cycle. For command palettes, every key-bound action should also have a searchable name and description.

## Dialog routing

A production Ink app should have one dialog owner that renders zero or one modal at a time. Use a prioritized route rather than independently rendering many boolean-controlled dialogs. A nullable request object is useful when opening a dialog also needs dynamic data; the non-null request both means visible and carries the payload.

A good dialog route:

- Checks fatal and blocking states first.
- Renders exactly one branch.
- Replaces or disables the underlying composer/input.
- Captures Escape and confirmation keys at the highest priority.
- Provides an explicit close or completion action.
- Re-evaluates the next pending dialog after the current one closes.

Do not allow two independent dialogs to compete for the same stdin and screen region.

## Async work, suspend, and external programs

Never perform network, filesystem, subprocess, or model work synchronously in a key handler or render function. Start the operation, expose loading/progress/error state, and update React state from completion events. Every long-running operation should have a cancellation path or a clear reason it cannot be cancelled.

Use `suspendTerminal()` before invoking an external editor, pager, or interactive shell. Await a render flush before handing off if the current frame must be visible, and resume with a full redraw. Keep child-process stdout/stderr away from Ink's owned live region unless deliberately suspended or routed through a controlled channel.

## Cursor and terminal protocols

`useCursor()` positions the real terminal cursor for input fields and IME-friendly editing. Clear it when the field is inactive or unmounted. Do not confuse the real cursor with a painted selection marker.

Bracketed paste, Kitty keyboard protocol, mouse reporting, OSC 8 links, OSC 52 clipboard, and terminal focus reporting are capability-dependent. Detect or configure them, provide legacy behavior, and always disable them on cleanup. A protocol query that times out must fall back without blocking the UI.

## Accessibility

Set `INK_SCREEN_READER=true` or pass `isScreenReaderEnabled` when the user needs semantic text output. Use `aria-role`, `aria-label`, `aria-state`, and `aria-hidden` on meaningful Box regions. Provide a linear reading order, words or symbols alongside color, numeric shortcuts for selectable lists where helpful, and a plain non-TUI mode for automation and assistive workflows.

A visual two-column layout that looks clear to a sighted user can become confusing when linearized. Screen-reader-specific layout is often simpler than trying to preserve every visual decoration.

## Interaction review failures

Look specifically for:

- A hidden component still consuming input.
- Focus order that differs from reading order.
- A dialog that leaves the composer active underneath it.
- Escape that cannot cancel or go back.
- A destructive one-key action without confirmation or undo.
- Mouse-only controls.
- Slow filters or key handlers that perform blocking work.
- Backspace/delete assumptions that changed across Ink majors.
- Raw mode, bracketed paste, or protocol enablement without a matching cleanup path.
