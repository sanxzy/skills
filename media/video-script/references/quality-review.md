# Quality review

Use after the complete draft, not as a substitute for writing it. Repair the script before delivery; do not export a defect list as the finished product.

## Hard delivery checks

- Both correctly named files exist in `.artifacts/video-scripts/`: `<stem>.srt` and `<stem>.source.md`.
- The main file contains only consecutive, chronological, non-overlapping **SRT cues with at most one spoken sentence across one or two visual text lines**, and intentional `♪ ♪` music intervals where useful. The SRT should import into a standard video subtitle track.
- The default reaches at least eight minutes; a requested duration or a chosen short-form duration takes precedence and is approximately met. Any explicit maximum or duration-range boundary is respected even when the validator's target tolerance would allow more.
- Words, local rates, pauses, and useful visuals plausibly fill that time.
- Every material factual claim is supported and traceable to final cue number(s) in the paired `.source.md` file.
- Uncertainty that changes interpretation is audible in the script.
- The narration is complete and ready to record: no placeholders, missing names, unexplained “this year,” or unfinished ending.

Fix any failure before treating the script as production-ready. If research or a required input is unavailable, state the specific limitation outside the main file.

## Editorial review by function

| Dimension | Strong result | Common failure | Repair |
| --- | --- | --- | --- |
| Opening | Subject and meaningful promise appear promptly | Vague spectacle or long preamble | Start with a supported observation and its consequence |
| Structure | Each beat depends on or develops an earlier idea | An encyclopedia list | Reorder around a question, mechanism, route, or task |
| Progression | New understanding in each block | Same point in different language | Remove repetition; add explanation or a distinct verified implication |
| Clarity | Understandable on one hearing | Stacked names, jargon, nested clauses | Introduce dependencies; split at changes of thought |
| Rhythm | Connected short cues with natural spoken emphasis | Isolated fragments or long breathless cues | Vary sentence jobs; read several adjacent cues aloud |
| Transitions | Relationship between ideas is explicit | Repeated “but why?” or arbitrary cuts | State cause, contrast, location, or unresolved condition |
| Density | Relevant detail with enough explanation | Statistics without meaning | Retain consequential figures; explain scale |
| Evidence | Wording matches the source's strength | “May” silently becomes “will” | Restore scope, attribution, and qualification |
| Visual use | Pictures make processes and changes legible | Abstract monologue or unsupported scene | Add a concrete mechanism or a clearly illustrative visual |
| Ending | Opening promise is resolved once | Repeated moral conclusions | Keep the strongest supported resolution |

## Adversarial read

Read as a viewer who does not know the topic. Ask what they would misunderstand, not whether the prose sounds impressive. Then read as a skeptical fact checker. Examine superlatives, causal connectors, present-day claims, named people's motives, and exciting comparisons. Finally read as an editor: can each interval be narrated and pictured without extra explanatory text?

Check structural promises against coverage. A title about why a country became wealthy needs an actual mechanism and limitations. A script about a species' danger needs a defined danger measure. A mystery needs evidence, not just a late reveal. An eight-minute script must offer eight minutes of useful understanding.

When developing a title, check that a stranger can identify the subject and curiosity loop at a glance, that the complete script delivers the promised payoff, and that any thumbnail concept adds complementary information. Avoid unearned shock, repeated title text in the thumbnail, and claims of proven click performance without comparative evidence. Use [titles-and-thumbnails.md](titles-and-thumbnails.md) for the full review.

For a documentary investigation, review several consecutive blocks together. Can a viewer follow an event, the difficulty it creates, the response, and the new result? If the blocks mostly restate the value or limitations of evidence, announce an audit, or explain why qualifications matter, rebuild the chain around the actual developments. Retain material qualifications at their point of use; do not let repeated verification commentary become the narration's voice. See the Hiraoka revision in [documentary-storytelling.md](documentary-storytelling.md) for a concrete repair.

## Revisions

When a user changes duration, reselect and deepen or compress beats; do not simply scale timestamps. When a user changes tone, preserve qualifications and evidence. When a user changes the central premise, recheck affected research. Any substantive wording change can introduce a new fact, so update claim mappings and downstream timing.

Passing automated checks proves only the checks performed. Final judgment remains grounded in the narration, sources, and available production context.
