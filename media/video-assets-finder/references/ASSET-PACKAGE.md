# Asset package and host checklist contract

`progress.todo.md` belongs only to the host and is the durable work ledger. Start it **before** searching. Use `## Current requirements` with one stable checklist entry per ID; leave `## Log` for append-only attempts and previous/removed IDs:

```markdown
## Current requirements
- [x] VIS-010 | status=RESOLVED | required | VIS-SEQ-010 | AST-VID-001 | available; tersedia—audio perlu ditinjau
- [x] VIS-011 | status=WILL_BE_MADE_DURING_EDITING | required | VIS-SEQ-011 | diagram
- [ ] AMB-002 | status=SEARCHING | optional | VIS-SEQ-007 | next: inspect source A

## Log
- 2026-09-27: assigned VIS-010 to scope location-media; rejected candidate B (wrong entity).
```

Use `- [ ]` for pending/in-flight and `- [x]` only for terminal states. A terminal `UNRESOLVED` or `FAILED` is checked **only** when explicitly labeled as such—checked means processed, not necessarily fulfilled. Preserve prior attempts/changes in the chronological Log rather than erasing evidence. When input changes, retain removed IDs in history, not current entries. For undetectable acoustic content, put the exact user review note `tersedia—audio perlu ditinjau` on the corresponding checklist entry. A partial run keeps unfinished boxes.

Write `.assets/<title_name>/manifest.json` as canonical machine-readable data and `assets.md` as human-readable inventory, independently of the TODO. Suggested compact schema (extend only when needed):

```json
{
  "schemaVersion": 1,
  "timeline": ".artifacts/video-timeline-mapping/example.timeline.md",
  "timelineVersion": "3",
  "generatedAt": "2026-09-27T00:00:00Z",
  "requirements": [
    {
      "id": "VIS-010",
      "type": "BROLL",
      "intent": "Correctly shaped knup in use",
      "optional": false,
      "sourceAudioRequired": false,
      "timelineRefs": ["VIS-SEQ-010"],
      "status": "RESOLVED",
      "assetIds": ["AST-VID-001"]
    },
    {
      "id": "VIS-011",
      "type": "DIAGRAM",
      "intent": "Construction explanation",
      "status": "WILL_BE_MADE_DURING_EDITING",
      "assetIds": []
    },
    {
      "id": "AMB-002",
      "type": "AMBIENT",
      "optional": true,
      "status": "UNRESOLVED",
      "reason": "No field recording matched the location and usable duration",
      "providersAttempted": ["youtube"],
      "assetIds": []
    }
  ],
  "sources": [
    {
      "id": "SRC-YT-001",
      "provider": "youtube",
      "providerId": "original-id",
      "url": "https://www.youtube.com/watch?v=...",
      "title": "Source title",
      "creator": "Uploader",
      "publishedAt": null,
      "sourceDurationMs": 200000,
      "retrievedAt": "2026-09-27T00:00:00Z",
      "credit": "Source title — Uploader — source URL",
      "rights": {"status": "REVIEW_REQUIRED", "evidence": "No reusable license verified"}
    }
  ],
  "assets": [
    {
      "id": "AST-VID-001",
      "sourceId": "SRC-YT-001",
      "localFile": ".assets/example/video/AST-VID-001.mp4",
      "mediaKind": "VIDEO",
      "relevantRange": {"startMs": 5000, "endMs": 17000},
      "acquiredRange": {"startMs": 3000, "endMs": 19000},
      "verification": {"visual": "OBSERVED", "audioContent": "NOT_LISTENED", "technical": "PASS"},
      "sizeBytes": 1234
    }
  ]
}
```

`requirements[].id` is the timeline requirement ID, never an asset ID. Set `sourceAudioRequired: true` on a visual requirement that itself calls for authentic original audio, even when no separate `SRC-AUD-###` ID exists; the validator then requires an audio stream in every selected file. For a separate `SRC-AUD-###`/`NAT_SOUND` region linked to picture, set `linkedVisualRequirementId: "VIS-003"` on the source-audio requirement (resolve a `VIS-SEQ-###` link to its applicable VIS ID). Its selected asset must share the original source and overlap the linked visual's source-relative relevant range; one video+audio file may satisfy both IDs. Do not substitute separately sourced ambience/SFX as original location sound. Record `mediaKind: "IMAGE"` for an explicitly externally sourced still image (rather than a constructed graphic); `ffprobe` verifies its readable visual dimensions, not a positive playback duration. Each asset records `mediaKind: VIDEO | AUDIO | IMAGE`, consistent with its probed streams; VIDEO/AUDIO media require a positive duration. Set `requiresMotion: true` on a visual requirement that explicitly requires continuous moving footage; the validator then rejects an IMAGE for it. Never silently treat a still as continuous motion. `sources[]` is per **currently acquired** original source; `assets[]` is per local acquired file/range; many requirements can reference one asset, and one requirement can reference several. Keep searched-but-unacquired candidates in worker results/cache, not as orphan sources or assets in the canonical manifest. Retain files from removed requirements on disk if needed, but remove their current manifest entries without deleting their history. Keep `relevantRange` **source-relative**, never mistake a timeline time for it. `acquiredRange` is required and must contain the full source-relative `relevantRange`; it may be wider to preserve retrieval context. Use `FULL` for both when the entire original short audio/still/source file was acquired (not as a substitute for unknown boundaries). When extraction reports imprecise or unavailable cut timestamps, record measured values/limitations rather than invent precision. Prefer workspace-relative local paths under the package. No `RESOLVED` without a real validated file and recorded provenance/rights status. A `RESOLVED` requirement can carry technically present but **not listened to** audio under the user's chosen nonblocking policy: this means **acquired for retrieval**, not that a timeline condition requiring verified usable/synced natural sound is met. Keep `verification.audioContent: "NOT_LISTENED"`; the editor/user must review it and may omit or replace the conditional audio after listening. Do not claim acoustic verification. Search failures `UNRESOLVED` are distinct from auth/provider/tool/download `FAILED`. `NO_NEW_ASSET_REQUIRED` applies to HOLD/NONE. `WILL_BE_MADE_DURING_EDITING` applies to graphics/etc to be constructed downstream. Incremental manifest checkpoints may contain `PENDING`, `ASSIGNED`, `QUEUED`, `SEARCHING`, `INSPECTING`, `SELECTED`, `DOWNLOADING` for unfinished entries, but a **completed** package may not. Use `verify-package.mjs <timeline> <manifest> --partial` for checkpoints and the default strict command at completion; both compare current TODO and existing acquired files.

Rights `VERIFIED` requires observed evidence of rights compatible with the intended use; a source's own declared license may be recorded as `DECLARED` until its provenance/scope is checked. `REVIEW_REQUIRED`, `UNKNOWN`, `RESTRICTED` are honest outcomes and never silently treated as publication permission. Preserve attribution text for CC BY and other licenses; YouTube default access and Internet Archive hosting do **not** grant re-use rights. User accepts uncertain rights as nonblocking for research/acquisition and plans to replace material if a removal request occurs. That is not a legal exemption. Prefer clearer rights when candidates otherwise satisfy the same hard constraints.

`assets.md` includes each ID, selected source URL/title/credit, relevant range and local file, rights evidence/status, and unresolved/failed reasons. Keep it aligned with the manifest. Only the TODO needs the specific user-facing `tersedia—audio perlu ditinjau` note. Neither report nor manifest may imply sound content was heard when it was not. Run `scripts/verify-package.mjs` from the **active project workspace** after writing the manifest (workspace-relative asset paths resolve against the current working directory) and resolve any failures before claiming the package is ready.
