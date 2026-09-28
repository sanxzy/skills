# Host-only worker coordination

This file elaborates `SKILL.md` for the host. Do not hand workers the host skill or this reference: workers read their own definition, `RETRIEVAL.md`, their assigned timeline excerpts, and **one validated handoff**. The useful analogy with squad is outcome ownership and durable handoffs, not Git worktrees or a ticket/reviewer/QA state machine. Asset workers do not code; no Git branches, worktrees, merge or integration stages are needed. SEARCH workers write only their assigned `result.json` and bounded inspection samples; after host approval, ACQUIRE workers also write the exact final asset paths from their new handoff. Provider tools may maintain their own runtime caches outside the project.

## Durable handoff before dispatch

For each related group of IDs create a unique `<package>/.cache/workers/<round>/<scope>/handoff.json` with an attempt-specific, immutable assignment. Never overwrite a previous attempt; use a new round/scope path and retain prior evidence on retry. Read it back before spawning. Use this shape (host may add fields):

```json
{
  "schemaVersion": 1,
  "role": "asset-finder-worker",
  "phase": "SEARCH",
  "assignmentId": "AFW-001",
  "workerId": "WKR-canopy-01",
  "timeline": ".artifacts/video-timeline-mapping/example.timeline.md",
  "timelineSha256": "<64 lowercase hex>",
  "resultPath": ".assets/example/.cache/workers/001/forest/result.json",
  "inspectionDirectory": ".assets/example/.cache/workers/001/forest/inspection",
  "requirements": [{
    "id": "VIS-001", "type": "BROLL", "intent": "Representative rainforest canopy",
    "searchDirection": {
      "whatToShow": "Emergent Amazonian canopy seen from inside the canopy layer, fronds moving in wind, no path or visitors",
      "onpointTraits": "broadleaf humid-forest species, green filtered understory light, unbroken canopy across the shot",
      "rejectIf": "conifer plantation rows, temperate birch or beech stand, canopy only from a distant drone view, a single still photograph"
    },
    "optional": false, "timelineRefs": ["VIS-SEQ-001"],
    "hardConstraints": ["forest canopy visible", "no burned-in text overlay in the relevant range"],
    "durationMs": 12000, "sourceAudio": "NOT_REQUIRED"
  }],
  "bounds": {"queryFamilies": 3, "resultsPerQuery": 10, "detailedInspections": 3},
  "excluded": ["final editing", "unapproved acquisition", "host checklist and manifest writes"]
}
```

When local source media is supplied, list its explicit workspace-contained `file://` URLs under `localSources`; a worker cannot report a different local path. Never invent a `durationMs` or hard constraint from the format alone; the example is illustrative. Give each assigned worker a stable `workerId` that survives both phases and every retry of that group. Every `VIS-###` also carries `searchDirection`, because only the host has read the whole timeline: write `whatToShow` as observable visual facts — subject, action, place, period — never narration wording; `onpointTraits` for the attributes that separate the requested asset from a generic lookalike; and `rejectIf` for the near-misses to discard. For a still-image need, state in `whatToShow` that in-image text is acceptable. A one-line `intent` is not a direction: a direction thinner than the requirement deserves is a handoff the host must fix, never a reason for the worker to guess the target. The worker still owns query craft and provider choice; the direction fixes the target, not the query strings. Put visually/technically checkable constraints in `hardConstraints`. Add `no burned-in text overlay in the relevant range` to every `VIS-###` you assign; it is a hard gate, not a preference. When the timeline explicitly requires on-screen text for one specific need, say so in that requirement's entry and note the waiver in the TODO as well — a waiver is never implicit and is never the worker's to grant. The worker's `FOUND` candidate must repeat each assigned hard-constraint string with an evidence-backed `PASS` in `candidate.hardConstraints`; the host still independently checks that the evidence really proves it. If agents cannot hear audio, **do not put acoustic-content claims into the PASS-required hardConstraints**: put them in the handoff as pending listening criteria, require same-source/stream checks where applicable, and preserve `audioContent: NOT_LISTENED` and the host TODO review note. This is the agreed review exception, not a fabricated acoustic PASS. Include explicit shared-source/associated-audio rules, allowed providers and credential limitations where applicable. The host uses a timeline SHA-256 snapshot so that a changed timeline invalidates a still-unconsumed result; per-ID retrieval fingerprints may preserve unaffected acquired files after change. Assign each active ID to only one worker at a time. Related IDs may share one worker, but must still have distinct findings. A worker never receives credentials or permissions unrelated to its group. Host writes TODO assignment status and handoff path before sending the validated brief. Runtime agent scheduling owns capacity; the host must not invent a hard `max_workers` override. If no worker agent is available, the host may execute SEARCH and approved ACQUIRE as a **serial worker-role fallback**: create the same handoffs/results and run the same result and package gates, while recording in the TODO that no agent was delegated. Do not silently replace worker evidence with a host conclusion or skip host acceptance simply because the same process executed both roles.

## Second handoff: host-approved acquisition

After validating SEARCH findings and inspecting their evidence, host decides which source(s) to acquire. Do not download yourself when a worker agent is available; the no-worker serial fallback above uses the same approved handoff. Create another immutable handoff at a fresh worker scope with `phase: "ACQUIRE"`, a new `assignmentId`, the **same `workerId`**, and the same timeline snapshot. Route it back to that same worker: continue the agent that produced the accepted SEARCH result instead of spawning a new one, so the downloader keeps the source identity, ranges and inspected frames it already established instead of re-deriving them. If that worker cannot be continued, a replacement is allowed only after the host records the reason in the TODO; the replacement still receives `sourceResultPath`/`sourceResultSha256` and must verify that digest, because continuity of evidence is what makes a substitution honest. Carry forward `localSources` if a provided local source was selected. Include `sourceResultPath`, the exact SHA-256 `sourceResultSha256`, and `approvedAssets`, each with `assetId`, assigned `requirementIds`, provider, sourceId, URL, source-relative `relevantRange`, encompassing `acquiredRange`, and a safe `localFile` inside the asset package. Host provisions safe target parent directories and ensures targets are absent (or separately verified for reuse) before dispatch. Only targets from that list may be written by the worker; siblings such as `.part` may be used during download. If one file satisfies two IDs, list both IDs on one approved asset. Never approve an unrelated URL, a range outside a researched candidate, or a new source not inspected by a worker. Host may reuse an unchanged, already accepted local asset without a new job; a newly supplied local source must instead be listed in SEARCH `localSources` and inspected by a worker, then copied/extracted by an approved ACQUIRE worker. Local paths must stay inside the active workspace.

The ACQUIRE worker verifies the approved SEARCH digest, downloads from approved providers (including Freesound with user-authorized OAuth when required), probes the local file, and writes its own phase-specific result. Host validates both the ACQUIRE result and actual file before `RESOLVED`. On auth/tool/download failure, affected needs become `FAILED` only after authorized recovery/fallback is exhausted; unrelated tasks continue. A worker must not replace sources on its own.

## Receiving a result

The worker starts a `result.json` with `status: IN_PROGRESS` before costly inspection when possible, updates its own file only, then writes and reads back a terminal `COMPLETE` or `BLOCKED` result. Result identity, findings and evidence shape are in [RETRIEVAL.md](RETRIEVAL.md). From the **active project workspace** (the scripts resolve workspace-relative paths against the current working directory), host runs:

```text
node <skill-dir>/scripts/verify-worker-result.mjs <handoff.json> <result.json>
```

This validates assignment/phase identity, one finding per delegated ID, allowed output path, source/range shape and (for ACQUIRE) approved source/digest/target correspondence; it cannot prove visual match. After SEARCH, host opens inspected frames/samples and checks claims/hard constraints. `FOUND` is a candidate. After ACQUIRE, `ACQUIRED` means a worker supplied a local file; only host independent file verification, provenance and manifest/TODO updates can complete `RESOLVED`. A terminal `NOT_FOUND` is evidence for refinement, not proof of universal absence. `BLOCKED` (auth/tool/provider/inspection failure) is not `NOT_FOUND`.

## Recovery and output ownership

If an agent stops with no result or an `IN_PROGRESS` result, keep its partial report and inspection media; examine whether any valid file exists before starting another attempt. Never infer success from agent termination, blindly repeat a download, or silently overwrite a prior result. A new handoff receives a new `assignmentId` and directory and cites earlier attempts/rejection evidence; keep the same `workerId` and continue that worker when it can be, recording a substitution reason in the TODO when it cannot. Reassign only affected IDs; independent work continues. If a worker reports `COMPLETE` but its exact assignment, result location, evidence or timeline snapshot fails validation, reject the handoff as **invalid context**, not as evidence that no asset exists. Persist the reason and next action in the host TODO; resubmit a corrected bounded brief. If upstream timeline changes, compare retrieval-relevant fields for each affected ID before reusing an asset; do not discard unrelated resolutions.

Do not mechanically copy squad's separate reviewer/QA agents, Git worktree isolation, large YAML control plane, or ticket state transitions into a retrieval task. The host's final manifest/package verifier and human examination of actual images are the applicable acceptance gates here.
