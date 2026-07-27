# Ink streaming and scale patterns

## Static/live split

The most important scaling pattern in Ink is separating append-only history from mutable live content. Put completed tasks, log lines, sent chat turns, and finalized stream chunks in `<Static>`. Keep only the active spinner, current response, input, status, or pending tool call in the live tree.

```tsx
<Static items={completedItems}>
  {item => <HistoryItem key={item.id} item={item} />}
</Static>
<LiveItem item={activeItem} />
```

Static items must have stable keys and must be appended, not reordered or edited after absorption. Do not put mutable content in `<Static>`, nest it casually inside a dynamic flex container, or expect a static item to stream internally. Static output is emitted immediately so the item is not removed from React before its bytes reach the terminal.

## Streaming state machine

Represent streaming explicitly rather than inferring it from scattered booleans. A useful state model is:

```
Idle -> Responding -> Idle
              |\
              | -> WaitingForConfirmation -> Responding
              -> Error/Cancelled -> Idle
```

Keep separate state for finalized history, the active pending item, tool-call lifecycle, cancellation, and errors. A context can expose the streaming state to indicators, the composer, dialogs, and footer without coupling them to the stream implementation.

For token or log streams:

1. Start the operation and enter `Responding`.
2. Accumulate chunks outside render.
3. Update the pending live item at a controlled cadence.
4. Flush semantically complete content into history.
5. Move immutable history to `<Static>` when it is complete.
6. Handle tool requests and confirmation as explicit state transitions.
7. On completion, flush the tail, clear the spinner, and return to `Idle`.
8. On Escape or cancellation, abort work, preserve a clear partial/error state, and release focus.

## Structured content boundaries

Do not split streaming Markdown at arbitrary character counts. A safe split strategy prioritizes:

1. Never split inside an open fenced code block.
2. Prefer the last paragraph boundary outside a code block.
3. If there is no safe boundary, keep accumulating the pending tail.

This permits completed paragraphs to become stable history while the incomplete paragraph remains live. The same principle applies to JSON, tool-call envelopes, log records, and any syntax with delimiters: finalize only at a boundary that preserves structure.

## Scrolling and virtualization

Ink does not provide a universal scroll widget. For a growing history, track viewport dimensions, scroll offset, measured or estimated item heights, and whether the user is following the bottom. Render only visible or near-visible items for large mutable lists. Use spacer boxes for content above and below the visible window, then correct estimates with measured heights.

Keep append-only finalized history static where possible. Virtualization is for large content that is still mutable, selectable, searchable, or scrollable. Do not render thousands of rows and hope frame diffing makes the Yoga and React cost disappear.

For scrolling driven by repeated wheel/key events, batch pending offsets within one event cycle and commit the final position once. Keep scroll state separate from data state so a new token does not unexpectedly reset a user's manual scroll position.

## State organization

Start with local `useState` and `useReducer`. When an app grows:

- Split independent concerns into domain hooks or providers.
- Keep frequently changing stream state away from stable configuration where practical.
- Separate read state from action callbacks in two contexts so components that only dispatch do not re-render for every token.
- Memoize context values and callbacks with complete dependency lists.
- Use a state-plus-ref pattern when an asynchronous callback must read the latest value without waiting for a render closure to refresh.

Do not centralize every value merely because the app is large. Centralization is useful when it makes ownership, transitions, and cross-feature invariants clearer.

## Dialog and tool-call flow

Tool-driven chat UIs need explicit tool states such as requested, awaiting approval, running, succeeded, failed, and cancelled. Render tool calls separately from prose so their status and side effects are clear. A high-priority dialog or confirmation should replace or suspend the composer and own input until resolved.

Keep the stream protocol adapter separate from presentation state. The adapter turns external events into typed state transitions; Ink components render those transitions. This keeps tests independent of a live network or model process.

## Performance model

Profile before optimizing, but understand the cost centers:

- React reconciliation and context cascades.
- Yoga layout and text measurement after commits.
- ANSI tokenization, width calculation, wrapping, and cell placement.
- Frame diffing and stdout writes.
- Large live trees and repeated Markdown rendering.
- Always-running animations that prevent the app from idling.

Use the default render throttle as a safety net. Use `useDeferredValue` or explicit batching for high-rate streams, memoize stable leaves, avoid recreating large arrays unnecessarily, and pause animation when it is not visible. `incrementalRendering` can reduce bytes but should be tested for structural changes. Static output is usually a bigger win than micro-optimizing JSX.

The shared animation scheduler is preferable to one timer per spinner. `useAnimation` subscribers share timing and Ink coalesces frames with its render throttle. Keep animations bounded and stop them when the associated state is idle.

## Performance failure modes

- Streaming every token through a large live history.
- Recomputing all message Markdown on each token.
- Re-rendering finalized output instead of freezing it.
- Virtualizing without stable keys or without correcting item-height estimates.
- Adding a spinner that keeps the whole app rendering continuously.
- Using `useMemo` as a substitute for a correct state boundary.
- Reading stale state from long-lived async callbacks.
- Changing layout dimensions inside `<Transform>` after Yoga measured them.
- Using direct stdout writes that fight Ink's diff cursor.
- Optimizing frame bytes while ignoring an expensive Yoga tree.
