# Ink API reference

Inspect the installed Ink version before relying on release-sensitive details. The wiki corpus describes Ink 7-era APIs and behavior, while older applications may be on Ink 6 or earlier.

## `render()` and `RenderOptions`

```tsx
import {render} from 'ink';

const instance = render(<App />, {
  alternateScreen: true,
  maxFps: 30,
});

await instance.waitUntilExit();
```

`render(node, options?)` mounts a React tree and returns an `Instance`. Passing a write stream as the second argument is a stdout shorthand. The important options are:

| Option | Use |
|---|---|
| `stdout`, `stdin`, `stderr` | Inject streams, isolate tests, or route diagnostics |
| `interactive` | Explicitly choose interactive versus plain output |
| `alternateScreen` | Use the alternate buffer for long-lived full-screen sessions |
| `debug` | Append frames instead of replacing them to inspect render behavior |
| `maxFps` | Cap render frequency and prevent runaway writes |
| `incrementalRendering` | Rewrite changed lines selectively; verify the layout does not produce artifacts |
| `concurrent` | Enable React concurrent scheduling |
| `patchConsole` | Keep console output from corrupting the live frame |
| `exitOnCtrlC` | Let Ink unmount on Ctrl+C or handle the key in application code |
| `isScreenReaderEnabled` | Force text-only semantic output |
| `kittyKeyboard` | Opt into enhanced keyboard protocol detection or enablement |
| `onRender` | Observe render timing; use `waitUntilRenderFlush()` for stdout completion |

The default options and option names vary by Ink major. Never copy an option from a different major without checking its type definition.

## `Instance`

The controller returned by `render()` exposes:

- `rerender(node)`: replace the root tree or update root props from outside React.
- `unmount(error?)`: stop the app and restore terminal state. It is idempotent.
- `waitUntilExit()`: await the exit result or error after cleanup and pending writes.
- `waitUntilRenderFlush()`: await React work, throttled output, and the stdout write barrier.
- `cleanup()`: unmount and remove the per-stdout instance for advanced reuse.
- `clear()`: clear the live output in interactive mode.

Ink maintains one live instance per stdout stream. Calling `render()` again on the same stream before unmounting reuses the existing instance and does not apply new options. Unmount before changing render configuration or mounting a fresh root.

## Built-in components

### `<Box>`

`Box` is a flex container backed by Yoga. It accepts layout, spacing, dimension, display, overflow, background, border, and accessibility props. Important props include `flexDirection`, `flexGrow`, `flexShrink`, `flexBasis`, `justifyContent`, `alignItems`, `gap`, `width`, `height`, `minWidth`, `maxWidth`, `padding`, `margin`, `display`, `overflow`, `backgroundColor`, `borderStyle`, `borderColor`, and per-side border toggles/colors.

### `<Text>`

`Text` is the host for strings and styled text. It supports `color`, `backgroundColor`, `bold`, `dimColor`, `italic`, `underline`, `strikethrough`, `inverse`, and `wrap`. Common wrap values are `wrap`, `hard`, `truncate-end`, `truncate-middle`, and `truncate-start`. Nested `<Text>` is useful for inline emphasis; direct strings under `<Box>` are not.

### `<Newline>` and `<Spacer>`

`<Newline count={n}>` inserts line breaks inside a text flow. `<Spacer>` consumes remaining flex space and is useful for pushing a footer or status value to an edge.

### `<Static>`

`<Static items={items}>{item => <... key={item.id} />}</Static>` emits append-only items above the live region. Root rendered items need stable keys. Items must be complete and immutable after absorption; append new items rather than editing or reordering old ones.

### `<Transform>`

`Transform` receives rendered lines and returns transformed lines. It is useful for prefixes, hanging indents, gradients, hyperlinks, and ANSI-aware effects. The transform runs after styling and layout measurement, so preserve dimensions and use ANSI-aware string utilities when slicing or padding.

## Ink hooks

| Hook | Purpose and important rule |
|---|---|
| `useInput(handler, {isActive})` | Parse keyboard events and expose `input` plus named key flags. Register only while the component should respond. |
| `usePaste(handler, {isActive})` | Receive bracketed paste as one string. Active paste handling prevents pasted text from arriving character-by-character through `useInput`. |
| `useApp()` | Access `exit`, `waitUntilRenderFlush`, and `suspendTerminal`. |
| `useStdin()` | Access stdin, raw-mode control, and raw-mode support. Guard non-TTY paths. |
| `useStdout()` / `useStderr()` | Access streams and write outside the React output tree. Use stderr or a file for diagnostics. |
| `useFocus(options)` | Register a focusable element, optionally autofocus it, and read `isFocused`. |
| `useFocusManager()` | Enable/disable focus, move next/previous, jump by id, and inspect the active id. |
| `useWindowSize()` | Read live columns and rows after resize. |
| `useBoxMetrics(ref)` | Read measured width, height, left, and top after layout. Expect an initial unmeasured state. |
| `useAnimation(options)` | Subscribe to Ink's shared animation scheduler; pause it when inactive. |
| `useCursor()` | Place the real terminal cursor for IME-friendly input. Clear the position on unmount. |
| `useIsScreenReaderEnabled()` | Branch to accessible labels, linear layout, and alternate interactions. |

React hooks remain ordinary React hooks. Respect dependency arrays, cleanup, stale-closure risks, and concurrent rendering semantics.

## Input key shape

`useInput` supplies named booleans such as `upArrow`, `downArrow`, `leftArrow`, `rightArrow`, `pageUp`, `pageDown`, `home`, `end`, `return`, `escape`, `tab`, `backspace`, `delete`, `ctrl`, `shift`, and `meta`. Enhanced flags such as `super`, `hyper`, `capsLock`, `numLock`, and event-type information depend on Kitty keyboard protocol support.

Ink 7-era behavior distinguishes `key.backspace` from `key.delete`. Upgrade handlers deliberately; old code that treats `key.delete` as Backspace can silently stop deleting the expected character.

## Accessibility props

`Box` supports `aria-label`, `aria-hidden`, `aria-role`, and `aria-state` fields such as `busy`, `checked`, `disabled`, `expanded`, `multiline`, `multiselectable`, `readonly`, `required`, and `selected`. `Text` supports `aria-label` and `aria-hidden`; `Transform` supports `accessibilityLabel`. These props affect screen-reader output, not Yoga layout.

## Version and module boundaries

Ink is ESM-only in modern majors. Check `package.json`, the Node engine, React peer version, TypeScript module resolution, and test runner before changing imports. The wiki notes that Ink 7 targets Node 22 and React 19, while Ink 6 is the compatibility choice for Node 20-era deployments. Treat this as a planning signal, not a substitute for the installed package's declarations.

Keep fast non-UI paths separate from Ink. React, Yoga, reconciliation, and startup work are expensive for commands such as `--version`, `--help`, or machine-readable subcommands. Lazy-load the interactive module when the command is actually entering a TTY UI.
