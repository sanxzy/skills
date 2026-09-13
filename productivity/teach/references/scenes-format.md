# Scene Lesson Format (scenes-format.md)

The visual lesson is a single self-contained HTML file in `lessons/NNNN-<dash-case-name>.html`. It teaches one tightly-scoped thing as a **step-by-step evolving visual** in a **side-by-side layout**: the evolving visual stays sticky on the left while the active step's full explanation is shown on the right. One meaningful change per step; only one step is active at a time.

## Layout

- **Desktop (lg+): fixed viewport.** The lesson fills the whole viewport height (`h-dvh`) and the page **never scrolls**. Inside: one compact top bar (fixed chrome) — title/subtitle on the left, Prev/Next + dots + counter on the right, on the same row so the material workspace gets maximum height — then a **50:50 split**: left = the evolving visual (`data-scn-stage`), fixed and `overflow-hidden` (must fit the pane — no scrolling in the visual); right = the active step's comprehensive explanation (`data-scn-scroll` pane with `overflow-y-auto`), which has **its own scrollbar** and can be as long as needed.
- **Mobile (<lg):** normal page scroll; visual first, explanation below; the top bar wraps (title above, controls below).
- The controls are part of the fixed top bar — they never scroll away on desktop. Arrow keys work too; each step change resets the right pane to the top.
- Keep the visual **compact** — it must fit the fixed pane height (roughly the viewport minus header/controls). Long diagrams belong in the explanation; cap wide diagrams at a comfortable width (e.g. `max-w-xl`) so a code panel stays readable.

## File layout

```
teach skill:
  templates/lesson-template.html   ← starting skeleton for every lesson
  templates/scenes.js              ← runtime (navigation, captions, dots)
  templates/scenes.css             ← runtime styles

teaching workspace:
  assets/scenes.js                 ← copy of runtime (copy once, reuse for all lessons)
  assets/scenes.css                ← copy of runtime styles
  lessons/0001-<name>.html         ← the lesson, links ../assets/scenes.js + scenes.css
```

First lesson in a workspace: copy `scenes.js` and `scenes.css` into `./assets/`. Then copy `lesson-template.html` into `./lessons/0001-<name>.html` and author it. Never inline the runtime into a lesson.

## Authoring steps

1. **Copy and rename** `lesson-template.html` → `lessons/0001-<dash-case-name>.html`.
2. **Choose a theme (or stay universal).** Pick the industry theme from `templates/themes/` — indexed in its [README](../templates/themes/README.md) and mapped to the canonical taxonomy in [`industries.md`](./industries.md) — then replace the font `<link>`s + the two `<style>` blocks in the head and paste the theme's signature into the stage. Universal (no theme) is neutral slate + teal. The `@theme` block defines the fixed semantic tokens `brand, ink, steel, paper, soft, panel, pinline, ok, mut`; mirror `--scn-accent`, `--scn-tint`, `--scn-ink` in the plain `:root` block — the runtime styles read those. Choose tokens that fit the topic; one dominant color, one ink, one sharp accent — never generic blue.
3. **Author the evolving visual once** in `<section data-scn-stage>` (the left/sticky column). Tag each element with the scene at which it appears or becomes the focus: `data-step="2"`. Elements without `data-step` are always visible.
   - A new element in a later scene: `data-step="3"` → hidden until scene 3.
   - The element added at the current scene gets a highlight (drop-shadow ring) automatically; once passed, it stays visible without the ring.
   - **Code panels show step progress:** write the program once, tag each line with its scene, and add the class `scn-code` to the `<pre>` — the runtime then marks the active step's line(s) with a ▶ marker and a highlight as the learner moves from step to step.
   - Author the FULL visual once; never duplicate markup per scene.
4. **Write the scene data** in `<script type="application/json" id="scene-data">` as an array, one object per scene:
   ```json
   [
     {
       "title": "One value, one owner",
       "paragraphs": ["Full paragraph one.", "Full paragraph two."],
       "points": ["Key point one", "Key point two"],
       "code": "let s1 = String::from(\"halo\");\nlet s2 = s1;",
       "why": "Why it matters — tie to the mission."
     }
   ]
   ```
   - `title`: short scene title. `paragraphs`: the full explanation, 1+ paragraphs. `points`: optional key takeaways (bullets). `code`: optional code snippet (use `\n` for newlines). `why`: one line on why it matters.
   - The number of scenes must match the highest `data-step` used in the stage.
5. **Add icons** as inline SVG in the Lucide/Feather family (the same icons `react-icons` exposes for pptx; embed the SVG paths directly — no rasterization needed). Typical use: icons inside small colored circles next to headings, per pptx design rules.
6. **Link the lesson** via HTML anchors to sibling lessons and reference documents, and recommend one primary source (the highest-quality, high-trust resource found for the topic). End with a reminder that the learner can ask the teaching agent follow-up questions.

## Scene data fields

| Field | Type | Required | Rendered as |
|---|---|---|---|
| `title` | string | yes | Heading |
| `paragraphs` | array of strings | yes | Full paragraphs |
| `points` | array of strings | no | Bullet list |
| `code` | string | no | Dark code block (`\n` = newline) |
| `why` | string | no | Accent "why it matters" box (label via `data-scn-why-label`) |

## Rules

- **One active step at a time.** The stage shows the full evolved picture up to the current scene; the right column shows only the current step's explanation.
- **One evolving visual, not one visual per scene.** Author the complete visual once and tag elements; never duplicate markup per scene.
- **Comprehensive but tight explanations.** Full paragraphs, honest technical depth, every claim grounded in the cited source. Difficulty is the enemy of working memory — cut fluff, never cut accuracy.
- **Contrast first.** Icons and text need strong contrast; light text on light backgrounds is forbidden.
- **No AI-slide clichés.** No accent bars/stripes under titles or along card edges; use background tint, shadow, or an icon instead. No default cream/beige backgrounds; default to white or the topic palette.
- **Don't toggle Tailwind utility classes at runtime.** The Tailwind v4 browser CDN recompiles when the DOM changes; scene visibility and highlight must use the `.scn-on` / `.scn-hot` classes from `scenes.css` (the runtime handles this — do not hand-roll your own show/hide logic).
- **Print.** The runtime styles flatten all scenes for print (one explanation per page, all stage elements revealed). Design the visual so it also reads as a static diagram; explanations print as a linear document.
- **Visual fits the sticky column.** If the full visual is taller than a viewport, split it — move dense detail into the right column's explanation or into a reference document.

## Runtime contract (scenes.js)

The runtime looks for, in order:

| Hook | Purpose |
|---|---|
| `[data-scenes]` | Lesson root; if missing, the runtime does nothing |
| `[data-scn-stage]` | The stage holding the evolving visual (left/sticky column) |
| `[data-step="N"]` | Elements revealed at scene N |
| `[data-scn-captions]` | Container the runtime fills with the active step's explanation (inside the scroll pane) |
| `[data-scn-scroll]` | The scrollable right pane; the runtime resets it to the top on every step change |
| `#scene-data` | JSON array of scene objects (see table above) |
| `data-scn-why-label` | Label for the "why it matters" box (language-aware) |
| `[data-scn-prev]`, `[data-scn-next]` | Prev/next buttons |
| `[data-scn-dots]` | Container for clickable progress dots |
| `[data-scn-counter]` | `N / Total` counter |

Behavior: `ArrowRight` next, `ArrowLeft` previous; buttons and dots do the same. Each step change re-renders the stage and captions, then resets the right scroll pane (`[data-scn-scroll]`) to the top.

## Verification checklist (run before delivering a lesson)

- [ ] `node --check assets/scenes.js` passes (runtime sanity)
- [ ] `#scene-data` is valid JSON; scene count == highest `data-step`
- [ ] Every scene has `title` + at least one `paragraph`; claims match the cited source
- [ ] Desktop: fixed-viewport lesson (page never scrolls); visual left has no scrollbar; explanation right has its own scrollbar
- [ ] Code panel (if any) reveals lines progressively and marks the active step's line(s) (▶ + highlight)
- [ ] Step change resets the right pane to the top
- [ ] Mobile: layout stacks cleanly with normal page scroll (visual first, explanation below)
- [ ] Arrow keys, buttons, dots, and counter all work
- [ ] Print preview flattens all scenes, controls hidden
- [ ] Lesson links to siblings/references and one primary source, and reminds the learner to ask questions
- [ ] No leftover template placeholders or duplicated runtime code