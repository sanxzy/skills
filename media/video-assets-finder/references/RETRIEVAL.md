# Source discovery, inspection and acquisition

For `asset-finder-worker`: this reference plus your own role definition, exact host handoff and assigned timeline sections are your only required instructions. Do not read the host-only `SKILL.md`, write host checklist/manifest, or create a Git worktree. In `SEARCH`, find and inspect candidates; in a separately approved `ACQUIRE` handoff, download selected files. Host chooses and accepts; worker performs both provider search and acquisition. If no worker agent is available, the host may run these same worker-phase procedures serially with full handoff/result evidence and independent acceptance checks; this is the explicit fallback, not the normal role boundary.

## Worker result contract

Read the exact `handoff.json` first. `phase: SEARCH` and `phase: ACQUIRE` are distinct, immutable assignments with different `assignmentId`/result paths. The `workerId` is the **same** across both phases and the ACQUIRE handoff is meant to arrive at you, the worker that searched: a new `assignmentId` is ordinary bookkeeping, not permission to re-search, re-choose a source, or forget the evidence you already inspected. Echo the handoff's `workerId` verbatim in your result so the host can see that one worker carried both phases. Never download finals in SEARCH or search/substitute sources in ACQUIRE. Fail closed if `assignmentId`, `timelineSha256`, per-ID requirements, `resultPath` or inspection directory are absent or disagree with the actual timeline or assigned workspace. Create/update/read back your result and samples; in ACQUIRE, also write **only** the exact approved target files and their temporary siblings. A completed result contains exactly one finding per ID, never a fabricated canonical `RESOLVED`. Minimal result shape:

```json
{
  "schemaVersion": 1,
  "role": "asset-finder-worker",
  "phase": "SEARCH",
  "assignmentId": "AFW-001",
  "workerId": "<same stable worker id as handoff>",
  "timelineSha256": "<same 64 lowercase hex as handoff>",
  "status": "COMPLETE",
  "findings": [{
    "requirementId": "VIS-001",
    "status": "FOUND",
    "queries": [{"provider": "youtube", "query": "Amazon rainforest aerial", "outcome": "candidate located"}],
    "candidates": [{
      "provider": "youtube", "sourceId": "video-id", "url": "https://www.youtube.com/watch?v=...",
      "title": "Original title", "creator": "Uploader",
      "relevantRange": {"startMs": 12000, "endMs": 30000},
      "evidence": [{"kind": "OBSERVED", "sourceTimeMs": 15000, "description": "Visible tree canopy", "sample": "<inspection path>"}],
      "hardConstraints": [{"constraint": "forest canopy visible", "result": "PASS", "basis": "OBSERVED"}],
      "audioContent": "NOT_LISTENED",
      "rights": {"status": "REVIEW_REQUIRED", "evidence": "No reusable license verified"}
    }]
  }]
}
```

For `phase: ACQUIRE`, the host handoff lists `sourceResultPath` and `sourceResultSha256` from the accepted SEARCH result plus `approvedAssets`: each has `assetId`, `requirementIds` (nonempty, assigned), provider, sourceId, URL, `relevantRange`, `acquiredRange` and `localFile`. The worker's acquisition result has the same identity fields, `status: COMPLETE | BLOCKED`, `findings` with one `{ "requirementId": "VIS-001", "status": "ACQUIRED", "assetIds": ["AST-VID-001"] }` (or `BLOCKED` with reason) per assigned ID, and `assets` with one item per acquired file: exact approved identity/ranges/path and `verification: { "technical": "PASS", "audioContent": "NOT_LISTENED" }` where applicable. Report actual media limitations; no `ACQUIRED` for a missing/broken or silently substituted file. The host checks file integrity independently before canonical `RESOLVED`.

`NOT_FOUND` has empty candidates and rejection/search evidence; `BLOCKED` names the operational issue, not an assertion of absence. A `COMPLETE` result may contain a `BLOCKED` finding if a provider could not be used, provided the reason is explicit. `FOUND` needs a real URL/source ID, source-relative range (or `FULL` for a genuinely complete short asset), and actual sampled visual evidence **inside that range** for visual requirements. Audio-only findings cannot claim heard content unless actually listened to; transcript/metadata clues must be labeled `METADATA_CLAIM` or `UNKNOWN`. The host validates identity and result shape with its own helper, then independently judges the media evidence; no agent report can complete the canonical requirement by itself.

Operational rule: **search broad → filter cheap → localize → inspect actual evidence → select → download last → probe**. Default per requirement group: 3 genuinely different query families, up to 10 results/query, 5 extended metadata checks and 2–3 detailed range inspections; expand only with a documented retrieval hypothesis and available provider budget. Avoid repeated near-identical searches, uncontrolled concurrency and full long-form downloads for discovery. Cache query/source IDs and inspected intervals in the package when useful. Do not use a transcript as proof of what the camera shows; do not use frames to claim audio was heard.

## Preflight and providers

Check `command -v yt-dlp ffmpeg ffprobe deno` for the tools your assignment needs. Workers report missing tools to the host and continue independent research; only the host asks the user for installation permission and installs after consent. The host alone may use a user-approved platform installer and verify its path/version; workers must not install tools or dependencies. Search providers can fail independently. Missing Freesound credentials are `AUTH_FAILURE` for that provider, not proof that no SFX exists. Never log API tokens or pass them in a command line if they would be exposed to process listings. Never bypass DRM, paywalls, protected access, or provider restrictions; publicly viewable/downloadable does not mean reuse is permitted.

- BROLL/AMBIENT/MUSIC: YouTube-compatible search when appropriate; archival: Archive plus YouTube-compatible; SFX: Freesound first, useful YouTube-compatible fallback. SOURCE_AUDIO/NAT_SOUND: same source as linked visual when required, keep video+sound together. The host inventories user-supplied local paths and lists any assigned ones in `handoff.localSources` as `file://` URLs. The worker inspects these files visually just like remote candidates and may report `provider: "local"` only for explicitly assigned workspace-contained files. Unrelated local paths are off-limits. If approved, the worker copies/extracts the required source material into the authorized asset path; the host does not perform provider search or acquisition. Remote provider candidates must use HTTPS URLs. For a supplied local source, a `queries` record may identify the assigned file and its inspection outcome instead of pretending a web provider was queried.
- Queries: translate *search context*, not narration wording. For named locations/entities use likely local uploader terms and native aliases plus distinct English fallback; for archival use period terminology and catalog language; for generic music use mood/energy/texture/instrumentation, not geographic language unless required. For non-musical SFX use the physical event and the [no-listening audio playbook](#no-listening-audio-search-playbook) below, not a dramatic title alone. For natural/original audio, consider local equivalents of `original sound`, `natural sound`, `raw recording`, `ASMR` **only where they describe a credible source**, not as proof of audio quality. For visual footage, `no text`, `no captions`, `no watermark`, `clean footage` are useful query leads for overlay-free material, never evidence: the frames decide. Execute the host's `searchDirection` first: it fixes **what** is wanted (`whatToShow`, `onpointTraits`, `rejectIf`) while you own **how** to reach it. If a direction element is missing, narrow it from the assigned timeline sections and record the assumption in the finding; never substitute a different target, and never present a generic lookalike as the requested asset.
- Separate inspectable hard gates (exact event, named place/entity, period, required action, continuous useful duration, **no burned-in text overlay**, same-source linkage and actual audio-stream presence) from preferences (resolution, provenance, clear license). Acoustic-content expectations that cannot be heard belong to pending listening criteria, not a fabricated hard-gate PASS. Source title/description are metadata evidence, not independent confirmation of the named place/entity. Distinguish observed visual facts, metadata-backed claims, and unknowns.
- **No text overlay** is a default hard gate on every `VIS-###`: reject footage carrying burned-in captions/subtitles in any language, lower-thirds or name straps, title cards and intertitles, watermarks, channel/uploader logos, on-screen timestamps or location slugs, and animated subscribe/UI text anywhere in the relevant range. Text that belongs to the photographed scene — signs, screens, book or record covers, plates, road markings — is not overlay and is allowed. Still images are out of scope. A waived need follows its host handoff: verify only that the overlay matches what the timeline explicitly asked for, and report it as waived. The worker cannot waive anything itself.

### No-listening audio search playbook

When the agent cannot hear, **improve candidate selection without pretending metadata is acoustic observation**. For an SFX such as battle noise (adapt the event/era/language to the actual timeline), spend the assigned query budget on distinct hypotheses rather than spelling variants:

| Query family | Archive example | What it tests |
| --- | --- | --- |
| Broad vocabulary | `mediatype:audio AND (title:"war sound effects" OR title:"battle sounds")` | Finds likely items; title alone is a weak lead. |
| Physical cause + catalog type | `mediatype:audio AND genre:"Sound Effects" AND description:"machine guns"` | Looks for a labeled effect with a specific recorded action. |
| Different physical cause + subject | `mediatype:audio AND subject:"Sound Effects" AND description:(mortar OR gunfire)` | Finds differently cataloged items; inspect individual cuts/files. |

For Freesound use similarly distinct physical-event phrases and inspect tags, description, duration, source ID, license and exact original-file type. For authentic SOURCE_AUDIO/NAT_SOUND, favor traceable original recordings linked to the visual source, not a generic designed SFX; a catalog's claim of “recorded from life” is provenance metadata until corroborated. Do **not** add `NOT collection:audio_music` mechanically: Archive's digitized sound-effects records may be inside that collection.

**Cheap rejection before approval:** read the full item description, subject/genre, creator, collection and **specific audio filename**. An item titled `Sound Explosions` can describe a psychedelic music sampler; reject an explicitly musical description even when the title matches. A generic `War Battle Sounds` description repeating only the title provides weaker support than an item whose catalog names distinct gun/mortar/explosion cuts. These fields often come from the same uploader/catalog and are **not independent acoustic confirmation**. A thumbnail, waveform, spectrogram, `ffprobe` audio stream, or meaningless/absent ASR speech cannot prove what was heard or that music is absent. If cut boundaries are not documented, do not invent useful source timestamps or call the entire long record one verified effect.

Send the host a few traceable candidates with query family, exact file URL, metadata-backed reason, rejected lookalikes, and `audioContent: NOT_LISTENED`. Only after exact host approval may a worker acquire a final file; a small derivative may be useful for authorized review but is not the original recording. Ask a capable listener to identify actual sound, unwanted music/speech and useful source-relative intervals; put `tersedia—audio perlu ditinjau` in the host TODO until that review happens. Bind user feedback to the exact source/file and revise candidate status or the next query hypothesis when it contradicts metadata (do not defend the title). Rights/attribution remain a separate check.

### YouTube-compatible discovery

Use `yt-dlp` search for metadata, not download-first selection. Example:

```bash
yt-dlp --flat-playlist --dump-single-json 'ytsearch10:Якутск люди на улице мороз'
```

Titles/uploader/IDs/durations are cheap screening, not approval. For promising candidates obtain extended metadata (without media): `yt-dlp --dump-single-json --skip-download '<url>'`; use captions/chapters if actually available. Some providers reject automated access; classify the operational failure honestly. Do not expose cookies or browser profiles unless the user explicitly authorizes them.

### Internet Archive discovery

Use the bundled standalone Deno script (pinned HTTPS ESM import, no npm package install):

```bash
deno run --allow-net=esm.sh,archive.org media/video-assets-finder/scripts/archive-search.mjs search 'mediatype:movies AND title:Amazon' --rows 10
deno run --allow-net=esm.sh,archive.org media/video-assets-finder/scripts/archive-search.mjs item '<identifier>'
```

Replace the path with the installed skill directory. `search` returns bounded identifier/title/creator/mediatype/date data; `item` uses Archive's metadata endpoint for description (bounded), subject, genre, rights, file names/formats and item provenance. The search-service package is browser-oriented; the script supplies its required location context before import. Archive metadata may be absent or inaccurate: verify actual files, rights and content separately. A SEARCH candidate for an Archive media file identifies the **specific file**, not only its item details page: use the item's identifier as `sourceId`, the `files[].url` of the specifically chosen file as candidate `url` (verify it resolves to the intended media before approval), and retain the item/details URL and file name in evidence. If `files[].url` is null or the file is inaccessible, do not fabricate a downloadable candidate. An ACQUIRE handoff approves that same exact file URL; choosing another file in the item is source substitution and needs a new SEARCH/approval. If `filesTruncated: true`, the displayed first 500 files are not a complete inventory; do not infer the desired file is absent without another bounded inspection of the item. **Only in an approved ACQUIRE phase**, the worker can fetch one exact metadata-listed file (full-file only) using:

```bash
deno run --allow-net --allow-read=<approved-output-directory> --allow-write=<approved-output-directory> <skill-dir>/scripts/archive-search.mjs download '<identifier>' '<exact-file-name>' '<approved-output-path>' --max-bytes 209715200
```

The script streams into an exclusive `.part` sibling, checks metadata size/MD5 when present, then publishes without overwriting and reports SHA-256. Adjust the bound only to a host-approved size. The network allowance permits Archive CDN redirects; the helper accepts only Archive file URLs/redirect hosts. This is **not** a ranged downloader: if the exact approved output is a bounded excerpt of a larger file, use a separately approved bounded extraction method rather than acquiring the full source unnoticed. Never download an item's entire directory merely to find a relevant video.

### Freesound SFX

Use Freesound APIv2 with user-provided credentials, never embed tokens. Workers may search through current `GET /apiv2/search/` (not deprecated `/apiv2/search/text/`):

```bash
# Set FREESOUND_API_TOKEN in the environment privately (not in a command-line URL).
node <skill-dir>/scripts/freesound.mjs search 'subtle low structural impact'
```

Search returns ID, creator, tags, duration, preview links and **declared** license/attribution. Original-file download is **worker-executed only after host ACQUIRE approval** and requires OAuth2; ordinary API token only allows read/search and previews. Do not call a preview an original or mark it acquired as one. Workers report authentication needs to the host; never attempt login as the user, store tokens in result files or print them. For approved original-file acquisition the worker uses the user-authorized OAuth token exposed through its environment, not an inline secret. Assess the actual sound only if an authorized listening path exists; metadata and waveform cannot establish acoustic content. On authentication failure report `BLOCKED` to the host. The host may authorize a new SEARCH/ACQUIRE handoff for another provider; only the host records terminal `FAILED` after viable authorized alternatives are exhausted. A short sound may have `relevantRange: "FULL"`. See [Freesound API resources](https://freesound.org/docs/api/resources_apiv2.html) and [authentication](https://freesound.org/docs/api/authentication.html) for provider contract and current limits.

## Visual localization without a full source download

For remote video, use provider chapters/subtitles/thumbnails first when informative. If actual frames are needed, use bounded inspection ranges with `yt-dlp` before selecting; for example:

```bash
yt-dlp --download-sections '*00:08:10-00:08:45' --merge-output-format mkv -o '<private-inspection-dir>/%(id)s.%(ext)s' '<url>'
ffmpeg -hide_banner -loglevel error -ss 00:00:05 -i '<inspection-file>' -frames:v 1 '<private-inspection-dir>/frame-05.png'
```

For an inspection file with local start `00:08:10`, that frame is approximately source `00:08:15`; report actual offset uncertainties. For a long video, sample **sparsely** by bounded regions and narrow around candidates; inspect more frequent frames or a playable bounded sample to establish action, continuity, and usable duration. Open image files with the host/agent image-capable tool. An extraction command completing or a frame filename is not a visual observation. To support an overlay-free claim, sample the **head, middle and tail** of the relevant range and add denser frames around each of those areas, because overlay usually enters at the start or end, or reappears intermittently in the middle; a single mid-range frame cannot establish absence. State the observed absence at named source times with `basis: "OBSERVED"` and record which span the samples actually covered. If that coverage is too sparse to support the claim, inspect more frames or reject the candidate rather than reporting a PASS. Report which exact sampled source times and which full candidate interval were inspected. If a region cannot be accessed without fetching the full source, weigh budget and report the limitation rather than asserting it was watched.

Audio/voice: inspect subtitles or transcript near suspected ranges for speech context when available; check audio stream via `ffprobe`, but never describe actual natural sound, music contamination or quality as *heard* if no agent listening capability exists. Place the agreed manual user-review note **only in the TODO**. Acquiring a visually suitable video with an audio stream under this policy is allowed with acoustic content marked `NOT_LISTENED` in machine metadata.

## Host selection, worker acquisition and integrity

Host reviews SEARCH findings and chooses only candidates satisfying visually verifiable hard gates; it creates a separate approved ACQUIRE handoff. The worker performs the provider download and local probe below; the host independently validates the ACQUIRE result and file before updating the manifest. For content whose essential exact claim cannot be established from inspected evidence, mark `UNRESOLVED` rather than falsely resolving. Source-audio content uncertainty is the explicitly agreed nonblocking exception, not permission to weaken visual/geographic/factual requirements. Prefer original traceable uploader where identifiable; credit and rights remain separate.

For bounded video use `yt-dlp --download-sections '*START-END'` and an output target/template that can produce **only the exact approved final file path or its temporary siblings** (choose container/extension based on inspected metadata and test actual tool behavior); preserve audio for original sound. Do not use `%(ext)s` for final output when that could write an unapproved extension. If a provider produces a different name, range or container, report `BLOCKED` for a revised approval rather than publishing an arbitrary final file. `yt-dlp -f 'bestaudio/best'` can acquire music/ambience audio when source/rights meet requirements. For Archive, choose a specific file from `item` metadata and download only that file/range when the server supports it. Name outputs with stable safe IDs, never arbitrary remote titles. For approved Freesound original SFX, the host arranges access to the user-authorized `FREESOUND_OAUTH_TOKEN` privately; the worker runs `node <skill-dir>/scripts/freesound.mjs download <sound-id> '<package>/sfx/<asset-id>.<original-extension>'`; match the extension to the source `type` metadata, then verify the resulting file rather than assuming a WAV. For added SFX retain downloaded source audio without creative processing. An extra conservative source interval around the relevant part protects downstream options; never present it as final edit in/out. If range download falls back to full media or produces inaccurate boundaries, record that and enforce budget rather than silently retaining huge files.

Verify with `ffprobe -v error -show_entries format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels -of json '<asset-file>'`; test decoded sample/range when damaged media is suspected. Required video → video stream; required source audio → audio stream too; audio-only → audio stream. Duration must be nonzero and satisfy the relevant continuous content when required; downloaded section duration alone does not prove the whole section is useful. If a file is corrupt, retry acquisition with an evidence-based correction or mark `FAILED`; do not treat exit status 0 as verified media. Record source-relative relevant range, actual acquisition range, metadata, credit, rights evidence and local size/hash. No final composition, speed change, transition, ducking, mix or render here.
