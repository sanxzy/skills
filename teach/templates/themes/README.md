# Industry Themes — teach lesson templates

The lesson structure lives ONCE in [`lesson-template.html`](../lesson-template.html) (universal, neutral
slate+teal). Every other template in this folder is a **drop-in theme**: fonts + palette tokens + one
signature element. Picking a theme never changes the structure, so layout/runtime fixes happen in one place.

The canonical industry taxonomy is [`../../references/industries.md`](../../references/industries.md).

## How to apply a theme

1. Copy `templates/lesson-template.html` → `lessons/0001-<name>.html`.
2. In the lesson head, replace the font `<link>`s + the two `<style>` blocks with the chosen theme's blocks.
3. Paste the theme's `<div data-theme-signature …>` into `<section data-scn-stage>` as the first element (it is the field's memorable motif — keep everything else quiet).
4. Adjust caption tone and icons to the field (inline SVG, Lucide/Feather family).

## Index

| Theme | File | For | Vibe | Signature |
|---|---|---|---|---|
| Universal | `lesson-template.html` | any topic, no field look needed | neutral slate + teal | none (plain) |
| Technology & Digital | [`technology-digital.html`](technology-digital.html) | software, AI/ML, cloud, cybersecurity, data, fintech, hardware | compiler window | file tab + LED "compiler OK" |
| Finance | [`finance.html`](finance.html) | ALL money topics — deliberately generic | ledger & gold | SUMMARY strip with big number |
| Healthcare | [`healthcare.html`](healthcare.html) | hospitals, pharma, biotech, medical devices, healthtech | clinical calm | vitals card + BAIK chip |
| Manufacturing & Engineering | [`manufacturing-engineering.html`](manufacturing-engineering.html) | manufacturing, construction, chemicals, mining, defense | drafting table | dimension frame (A—B) |
| Energy & Environment | [`energy-environment.html`](energy-environment.html) | energy & utilities, environmental, sustainability | energy transition | load gauge |
| Transportation & Logistics | [`transportation-logistics.html`](transportation-logistics.html) | airlines, railways, shipping, freight, delivery | route & fleet | route card A→B |
| Commerce & Consumer | [`commerce-consumer.html`](commerce-consumer.html) | retail, e-commerce, tourism & hospitality | modern shop | product tag + price |
| Media & Creative | [`media-creative.html`](media-creative.html) | film, streaming, gaming, creative industries | screen & spectrum | spectrum strip "SCENE" |
| Education | [`education.html`](education.html) | schools, universities, training, edtech | friendly motivator | STEPS chips |
| Professional & Public | [`public-institutional.html`](public-institutional.html) | government, public sector, legal/accounting/consulting | official document | REV stamp |
| Science & Research | [`science-research.html`](science-research.html) | research, biotech, physics, chemistry, space, quantum | laboratory | specimen card + VALID chip |
| Agrifood & Nature | [`agrifood-nature.html`](agrifood-nature.html) | agriculture, fisheries, food, agritech | field & harvest | season chips |
| Fitness | [`fitness.html`](fitness.html) | sports, yoga, wellness — beyond the industry taxonomy | energetic earthy | progress ring "POSITION" |

## Industry mapping (industries.md → theme)

| industries.md category | Theme |
|---|---|
| 1. Technology & Digital | [`technology-digital.html`](technology-digital.html) |
| 2. Financial Services | [`finance.html`](finance.html) (generic by design — see note below) |
| 3. Healthcare | [`healthcare.html`](healthcare.html) |
| 4. Manufacturing | [`manufacturing-engineering.html`](manufacturing-engineering.html) |
| 5. Energy & Utilities | [`energy-environment.html`](energy-environment.html) |
| 6. Transportation & Logistics | [`transportation-logistics.html`](transportation-logistics.html) |
| 7. Retail & Consumer | [`commerce-consumer.html`](commerce-consumer.html) |
| 8. Media & Entertainment | [`media-creative.html`](media-creative.html) |
| 9. Education | [`education.html`](education.html) |
| 10. Real Estate & Construction | [`manufacturing-engineering.html`](manufacturing-engineering.html) |
| 11. Agriculture & Food | [`agrifood-nature.html`](agrifood-nature.html) |
| 12. Chemicals & Materials | [`manufacturing-engineering.html`](manufacturing-engineering.html) |
| 13. Mining | [`manufacturing-engineering.html`](manufacturing-engineering.html) |
| 14. Professional & Business Services | [`public-institutional.html`](public-institutional.html) |
| 15. Tourism & Hospitality | [`commerce-consumer.html`](commerce-consumer.html) |
| 16. Government & Public Sector | [`public-institutional.html`](public-institutional.html) |
| 17. Creative Industries | [`media-creative.html`](media-creative.html) |
| 18. Science & Research | [`science-research.html`](science-research.html) |
| 19. Defense & Aerospace | [`manufacturing-engineering.html`](manufacturing-engineering.html) |
| 20. Environmental & Sustainability | [`energy-environment.html`](energy-environment.html) |
| _beyond the taxonomy_ (sports, yoga, wellness) | [`fitness.html`](fitness.html) |

> **Finance is generic on purpose.** The `finance` theme covers every money topic (personal finance,
> investing, accounting, taxes, budgeting) with one face — no per-sub-industry variations. When in doubt
> for anything about money, use `finance.html`.

## Rules

- **Semantic token names are fixed**: `brand, ink, steel, paper, soft, panel, pinline, ok, mut` (plus
  `--scn-accent/tint/ink` for the runtime). Themes change VALUES only.
- **One signature per lesson.** The theme ships one `data-theme-signature` element; do not stack several.
- **Don't create a new theme by copying a themed lesson** — copy the universal template and vary the tokens.
- Adding a field? Add one small theme file here (fonts + tokens + signature) — structure stays untouched.
- If the taxonomy in `references/industries.md` changes, update the mapping table above.