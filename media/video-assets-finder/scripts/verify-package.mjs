#!/usr/bin/env node
// Structural and local-media integrity gate; semantic match and license judgments belong to the host.
import { readFileSync, realpathSync, statSync } from 'node:fs';
import { resolve, dirname, relative, isAbsolute, sep } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const TERMINAL = new Set(['RESOLVED', 'UNRESOLVED', 'FAILED', 'NO_NEW_ASSET_REQUIRED', 'WILL_BE_MADE_DURING_EDITING']);
const NO_ASSET = new Set(['NO_NEW_ASSET_REQUIRED', 'WILL_BE_MADE_DURING_EDITING']);
const AUDIO = new Set(['MUSIC', 'AMBIENT', 'SFX']);
const RIGHTS = new Set(['VERIFIED', 'DECLARED', 'UNKNOWN', 'RESTRICTED', 'REVIEW_REQUIRED']);

function inside(parent, child) {
  const offset = relative(parent, child);
  return offset === '' || (offset !== '..' && !offset.startsWith(`..${sep}`) && !isAbsolute(offset));
}

function sourceId(id) { return /^(?:VIS|SRC-AUD|MUS|AMB|SFX)-\d{3,}$/.test(id); }

export function validateTodo(todoText, manifest) {
  const errors = [];
  const section = todoText.match(/^## Current requirements\s*\n([\s\S]*?)(?=^## |$(?![\s\S]))/m)?.[1];
  if (section === undefined) return ['TODO missing ## Current requirements section'];
  const entries = new Map();
  for (const line of section.split('\n').filter(line => /^- \[[ x]\]/.test(line))) {
    const match = line.match(/^- \[([ x])\] ((?:VIS|SRC-AUD|MUS|AMB|SFX)-\d{3,}|REQ-VIS-VIS-SEQ-\d{3,}-\d+) \| status=([A-Z_]+)\b/);
    if (!match) { errors.push(`Malformed TODO entry: ${line}`); continue; }
    const [, checked, id, status] = match;
    if (entries.has(id)) errors.push(`Duplicate TODO entry: ${id}`);
    entries.set(id, { checked, status });
    if ((checked === 'x') !== TERMINAL.has(status)) errors.push(`${id}: TODO checkbox/status mismatch`);
  }
  for (const requirement of manifest.requirements) {
    const entry = entries.get(requirement.id);
    if (!entry) errors.push(`${requirement.id}: missing current TODO entry`);
    else if (entry.status !== requirement.status) errors.push(`${requirement.id}: TODO status ${entry.status} != manifest ${requirement.status}`);
  }
  for (const id of entries.keys()) if (!manifest.requirements.some(r => r.id === id)) errors.push(`${id}: current TODO absent from manifest`);
  return errors;
}

export function validate(timelineText, manifest, baseDirectory, { probe = true, complete = true, command = 'ffprobe', workspace = process.cwd() } = {}) {
  const errors = [];
  const add = text => errors.push(text);
  if (manifest.schemaVersion !== 1) add('Unsupported schemaVersion');
  if (!Array.isArray(manifest.requirements) || !Array.isArray(manifest.sources) || !Array.isArray(manifest.assets)) {
    return ['requirements, sources and assets must be arrays'];
  }
  const requirements = new Map(), sources = new Map(), assets = new Map();
  for (const entry of manifest.requirements) {
    if (!entry || typeof entry.id !== 'string' || requirements.has(entry.id)) { add(`Invalid/duplicate requirement ID: ${entry?.id}`); continue; }
    requirements.set(entry.id, entry);
    if (!TERMINAL.has(entry.status) && (complete || !['PENDING', 'ASSIGNED', 'QUEUED', 'SEARCHING', 'INSPECTING', 'SELECTED', 'DOWNLOADING'].includes(entry.status))) add(`${entry.id}: nonterminal/invalid status ${entry.status}`);
    if (!Array.isArray(entry.assetIds)) add(`${entry.id}: assetIds must be an array`);
    else if (entry.status === 'RESOLVED' ? entry.assetIds.length === 0 : entry.assetIds.length !== 0) add(`${entry.id}: assetIds inconsistent with status ${entry.status}`);
    if (entry.status === 'UNRESOLVED' || entry.status === 'FAILED') {
      if (!entry.reason) add(`${entry.id}: missing failure reason`);
    }
    if (!sourceId(entry.id) && !/^REQ-VIS-VIS-SEQ-\d{3,}-\d+$/.test(entry.id)) add(`${entry.id}: unsupported requirement ID`);
  }
  for (const id of new Set(timelineText.match(/\b(?:VIS|SRC-AUD|MUS|AMB|SFX)-\d{3,}\b/g) ?? [])) {
    if (!requirements.has(id)) add(`Missing timeline requirement ID: ${id}`);
  }
  for (const entry of manifest.sources) {
    if (!entry?.id || sources.has(entry.id)) { add(`Invalid/duplicate source ID: ${entry?.id}`); continue; }
    sources.set(entry.id, entry);
    if (!entry.provider || !entry.url || !entry.title || !entry.credit || !entry.retrievedAt || !RIGHTS.has(entry.rights?.status)) add(`${entry.id}: provenance/credit/rights incomplete or invalid`);
    if (['VERIFIED', 'DECLARED'].includes(entry.rights?.status) && !entry.rights.evidence) add(`${entry.id}: rights claim lacks evidence`);
  }
  let root;
  try { root = realpathSync(baseDirectory); } catch { add(`Asset package missing: ${baseDirectory}`); return errors; }
  for (const entry of manifest.assets) {
    if (!entry?.id || assets.has(entry.id)) { add(`Invalid/duplicate asset ID: ${entry?.id}`); continue; }
    assets.set(entry.id, entry);
    if (!sources.has(entry.sourceId)) add(`${entry.id}: unknown source ${entry.sourceId}`);
    if (!['VIDEO', 'AUDIO', 'IMAGE'].includes(entry.mediaKind)) add(`${entry.id}: invalid or missing mediaKind`);
    if (!entry.localFile || typeof entry.localFile !== 'string') { add(`${entry.id}: missing localFile`); continue; }
    let filename;
    try {
      filename = realpathSync(isAbsolute(entry.localFile) ? entry.localFile : resolve(workspace, entry.localFile));
      if (!inside(root, filename)) throw Error('path escapes asset package');
      if (!statSync(filename).isFile() || statSync(filename).size < 1) throw Error('file missing or empty');
    } catch (error) { add(`${entry.id}: invalid localFile: ${error.message}`); continue; }
    const range = entry.relevantRange;
    if (range !== 'FULL' && (!range || !Number.isFinite(range.startMs) || !Number.isFinite(range.endMs) || range.startMs < 0 || range.endMs <= range.startMs)) add(`${entry.id}: invalid source-relative relevantRange`);
    const acquired = entry.acquiredRange;
    if (!acquired || (acquired !== 'FULL' && (!Number.isFinite(acquired.startMs) || !Number.isFinite(acquired.endMs) || acquired.startMs < 0 || acquired.endMs <= acquired.startMs))) add(`${entry.id}: invalid or missing acquiredRange`);
    else if (range === 'FULL' && acquired !== 'FULL') add(`${entry.id}: full relevant content was not acquired`);
    else if (range && range !== 'FULL' && acquired !== 'FULL' && (acquired.startMs > range.startMs || acquired.endMs < range.endMs)) add(`${entry.id}: acquiredRange does not contain relevantRange`);
    if (entry.verification?.technical !== 'PASS') add(`${entry.id}: missing technical verification PASS`);
    if (!probe) continue;
    const result = spawnSync(command, ['-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height', '-of', 'json', filename], { encoding: 'utf8', timeout: 30000 });
    let info;
    try { if (result.status !== 0 || result.error) throw Error(result.stderr || result.error?.message || 'probe failed'); info = JSON.parse(result.stdout); }
    catch (error) { add(`${entry.id}: ffprobe failed: ${error.message}`); continue; }
    const streams = info.streams ?? [];
    const kinds = new Set(streams.map(stream => stream.codec_type));
    if (entry.mediaKind === 'IMAGE') {
      if (!streams.some(stream => stream.codec_type === 'video' && stream.width > 0 && stream.height > 0)) add(`${entry.id}: missing readable image dimensions`);
    } else if (!(Number(info.format?.duration) > 0)) add(`${entry.id}: no measurable positive duration`);
    if (entry.mediaKind === 'VIDEO' && !kinds.has('video')) add(`${entry.id}: VIDEO missing video stream`);
    if (entry.mediaKind === 'AUDIO' && !kinds.has('audio')) add(`${entry.id}: AUDIO missing audio stream`);
    const users = [...requirements.values()].filter(r => r.status === 'RESOLVED' && Array.isArray(r.assetIds) && r.assetIds.includes(entry.id));
    if (users.some(r => r.requiresMotion === true) && entry.mediaKind === 'IMAGE') add(`${entry.id}: still image cannot satisfy required moving footage`);
    if (users.some(r => r.id.startsWith('VIS-') || r.id.startsWith('REQ-VIS-')) && !kinds.has('video')) add(`${entry.id}: missing visual stream for visual requirement`);
    if (users.some(r => r.sourceAudioRequired === true) && !kinds.has('audio')) add(`${entry.id}: missing required source-audio stream`);
    if (users.some(r => AUDIO.has(r.type) || /^(?:MUS|AMB|SFX|SRC-AUD)-/.test(r.id)) && !kinds.has('audio')) add(`${entry.id}: missing audio stream for audio requirement`);
    if (users.some(r => r.type === 'SOURCE_AUDIO' || r.type === 'NAT_SOUND') && !kinds.has('audio')) add(`${entry.id}: missing required source-audio stream`);
  }
  for (const entry of assets.values()) if (![...requirements.values()].some(requirement => requirement.status === 'RESOLVED' && Array.isArray(requirement.assetIds) && requirement.assetIds.includes(entry.id))) add(`${entry.id}: asset has no resolved requirement`);
  for (const entry of sources.values()) if (![...assets.values()].some(asset => asset.sourceId === entry.id)) add(`${entry.id}: source has no current acquired asset`);
  for (const entry of requirements.values()) {
    for (const id of Array.isArray(entry.assetIds) ? entry.assetIds : []) if (!assets.has(id)) add(`${entry.id}: references unknown asset ${id}`);
    if (NO_ASSET.has(entry.status) && entry.assetIds?.length) add(`${entry.id}: no-asset status has asset IDs`);
    if (entry.linkedVisualRequirementId && entry.status === 'RESOLVED') {
      const visual = requirements.get(entry.linkedVisualRequirementId);
      if (!visual || visual.status !== 'RESOLVED') add(`${entry.id}: linked visual requirement is not resolved`);
      else {
        const visualAssets = (Array.isArray(visual.assetIds) ? visual.assetIds : []).map(id => assets.get(id)).filter(Boolean);
        for (const id of Array.isArray(entry.assetIds) ? entry.assetIds : []) {
          const audioAsset = assets.get(id);
          if (!audioAsset || !visualAssets.some(videoAsset => {
            if (videoAsset.sourceId !== audioAsset.sourceId) return false;
            const a = audioAsset.relevantRange, v = videoAsset.relevantRange;
            return a === 'FULL' || v === 'FULL' || (a && v && a.startMs < v.endMs && v.startMs < a.endMs);
          })) add(`${entry.id}: source audio does not overlap its linked visual source/range`);
        }
      }
    }
  }
  return errors;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [timelinePath, manifestPath, flag] = process.argv.slice(2);
  if (!timelinePath || !manifestPath || (flag && flag !== '--partial')) { console.error('Usage: node verify-package.mjs <timeline.md> <manifest.json> [--partial]'); process.exitCode = 2; }
  else {
    try {
      const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
      const baseDirectory = dirname(resolve(manifestPath));
      const errors = validate(readFileSync(timelinePath, 'utf8'), manifest, baseDirectory, { complete: flag !== '--partial' });
      try { errors.push(...validateTodo(readFileSync(resolve(baseDirectory, 'progress.todo.md'), 'utf8'), manifest)); }
      catch { errors.push('Missing or unreadable progress.todo.md'); }
      if (errors.length) { console.error(errors.join('\n')); process.exitCode = 1; }
      else console.log(`Verified: ${manifest.requirements.length} requirements, ${manifest.assets.length} local assets`);
    } catch (error) { console.error(error.message); process.exitCode = 1; }
  }
}
