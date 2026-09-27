#!/usr/bin/env node
// Host gate for exact SEARCH/ACQUIRE handoffs. Semantic match and rights decisions remain host-owned.
import { createHash } from 'node:crypto';
import { readFileSync, realpathSync, statSync } from 'node:fs';
import { basename, dirname, isAbsolute, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const inside = (root, path) => { const r = relative(root, path); return r === '' || (r !== '..' && !r.startsWith(`..${sep}`) && !isAbsolute(r)); };
const located = (path, workspace) => resolve(workspace, path);
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const sameRange = (a, b) => a === b || (Array.isArray(a) && Array.isArray(b) && JSON.stringify(a) === JSON.stringify(b)) || (a && b && !Array.isArray(a) && !Array.isArray(b) && Number.isFinite(a.startMs) && a.startMs === b.startMs && a.endMs === b.endMs);
const containsRange = (outer, inner) => outer === 'FULL' || (inner !== 'FULL' && outer && inner && outer.startMs <= inner.startMs && outer.endMs >= inner.endMs);
const validRange = range => range === 'FULL' || (range && Number.isFinite(range.startMs) && Number.isFinite(range.endMs) && range.startMs >= 0 && range.endMs > range.startMs);
function validSourceUrl(provider, url, workspace, allowedLocalSources = []) {
  if (provider !== 'local') return /^https:\/\//.test(url ?? '');
  try {
    if (!allowedLocalSources.includes(url)) return false;
    const path = realpathSync(fileURLToPath(url));
    return inside(realpathSync(workspace), path) && statSync(path).isFile();
  } catch { return false; }
}

function validateAcquisition(handoff, result, assigned, packageRoot, workspace, fail) {
  let source;
  try {
    const path = realpathSync(located(handoff.sourceResultPath, workspace));
    if (!inside(packageRoot, path) || !path.includes(`${sep}.cache${sep}workers${sep}`) || basename(path) !== 'result.json') throw Error();
    const bytes = readFileSync(path);
    if (!/^[0-9a-f]{64}$/.test(handoff.sourceResultSha256 ?? '') || sha256(bytes) !== handoff.sourceResultSha256) throw Error();
    source = JSON.parse(bytes);
    if (source.role !== 'asset-finder-worker' || source.phase !== 'SEARCH' || source.status !== 'COMPLETE' || source.timelineSha256 !== handoff.timelineSha256 || !Array.isArray(source.findings)) throw Error();
  } catch { fail('Approved SEARCH result missing, stale or outside package'); return; }
  if (!Array.isArray(handoff.approvedAssets) || handoff.approvedAssets.length === 0 || !Array.isArray(result.assets)) {
    fail('ACQUIRE requires approvedAssets and result assets arrays'); return;
  }
  const approved = new Map(), acquired = new Map(), targets = new Set();
  for (const item of handoff.approvedAssets) {
    if (!/^AST-(?:VID|ARC|NAT|AMB|MUS|SFX|IMG)-\d{3,}$/.test(item?.assetId ?? '') || approved.has(item.assetId)) { fail(`Invalid/duplicate approved asset: ${item?.assetId}`); continue; }
    approved.set(item.assetId, item);
    if (!Array.isArray(item.requirementIds) || !item.requirementIds.length || new Set(item.requirementIds).size !== item.requirementIds.length || item.requirementIds.some(id => !assigned.has(id))) { fail(`${item.assetId}: unassigned/duplicate requirement IDs`); continue; }
    if (!item.provider || !item.sourceId || !validSourceUrl(item.provider, item.url, workspace, handoff.localSources) || !validRange(item.relevantRange) || !validRange(item.acquiredRange) || !containsRange(item.acquiredRange, item.relevantRange)) fail(`${item.assetId}: incomplete source or range`);
    const found = item.requirementIds.every(id => source.findings?.some(f => f?.requirementId === id && f.status === 'FOUND' && f.candidates?.some(candidate => candidate.provider === item.provider && candidate.sourceId === item.sourceId && candidate.url === item.url && containsRange(candidate.relevantRange, item.relevantRange))));
    if (!found) fail(`${item.assetId}: approved source/range was not found in accepted SEARCH result`);
    try {
      const target = located(item.localFile, workspace);
      const canonicalTarget = resolve(realpathSync(dirname(target)), basename(target));
      if (targets.has(canonicalTarget)) fail(`${item.assetId}: target path assigned to multiple assets`);
      targets.add(canonicalTarget);
      if (!inside(packageRoot, canonicalTarget) || inside(resolve(packageRoot, '.cache'), canonicalTarget) || ['manifest.json', 'progress.todo.md', 'assets.md'].includes(basename(target))) throw Error();
    } catch { fail(`${item.assetId}: target outside approved asset package or parent missing`); }
  }
  for (const item of result.assets) {
    const expected = approved.get(item?.assetId);
    if (!expected || acquired.has(item.assetId)) { fail(`Unexpected/duplicate acquired asset: ${item?.assetId}`); continue; }
    acquired.set(item.assetId, item);
    if (item.provider !== expected.provider || item.sourceId !== expected.sourceId || item.url !== expected.url || located(item.localFile, workspace) !== located(expected.localFile, workspace) || !sameRange(item.relevantRange, expected.relevantRange) || !sameRange(item.acquiredRange, expected.acquiredRange)) fail(`${item.assetId}: acquired asset differs from approved source/range/path`);
    if (item.verification?.technical !== 'PASS') fail(`${item.assetId}: missing technical probe PASS`);
    try { const path = realpathSync(located(item.localFile, workspace)); if (!inside(packageRoot, path) || !statSync(path).isFile() || statSync(path).size === 0) throw Error(); }
    catch { fail(`${item.assetId}: acquired local file missing or outside package`); }
  }
  const findings = new Map(result.findings.filter(Boolean).map(item => [item.requirementId, item]));
  for (const [id] of assigned) {
    const finding = findings.get(id);
    if (!finding) continue;
    const expectedIds = [...approved.values()].filter(asset => asset.requirementIds?.includes(id)).map(asset => asset.assetId).sort();
    if (!expectedIds.length) fail(`${id}: no approved asset for assigned requirement`);
    if (finding.status === 'ACQUIRED') {
      if (!sameRange([...new Set(finding.assetIds ?? [])].sort(), expectedIds) || !expectedIds.every(assetId => acquired.has(assetId))) fail(`${id}: ACQUIRED does not include every approved local asset`);
    } else if (finding.status !== 'BLOCKED' || !finding.reason || (finding.assetIds ?? []).length) fail(`${id}: expected ACQUIRED or reasoned BLOCKED finding`);
  }
}

export function validateWorkerResult(handoff, result, { handoffPath, resultPath, workspace = process.cwd() }) {
  const errors = [];
  const fail = message => errors.push(message);
  const expectedResult = located(handoff.resultPath ?? '', workspace);
  const handoffDir = dirname(resolve(handoffPath));
  let packageRoot;
  try {
    const root = realpathSync(workspace);
    const assigned = realpathSync(handoffDir);
    const parts = relative(root, assigned).split(sep);
    if (basename(handoffPath) !== 'handoff.json' || !inside(root, assigned) || parts.length < 5 || parts.at(-4) !== '.cache' || parts.at(-3) !== 'workers' || !parts.slice(-2).every(part => /^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(part))) fail('Handoff is outside active worker namespace');
    if (!inside(assigned, realpathSync(handoffPath))) fail('Handoff path is redirected');
    packageRoot = dirname(dirname(dirname(dirname(assigned))));
  } catch { fail('Handoff or workspace directory unreadable'); }
  if (handoff.schemaVersion !== 1 || handoff.role !== 'asset-finder-worker' || !['SEARCH', 'ACQUIRE'].includes(handoff.phase) || !/^AFW-[A-Za-z0-9_-]+$/.test(handoff.assignmentId ?? '')) fail('Invalid host handoff identity/phase');
  if (result.schemaVersion !== 1 || result.role !== 'asset-finder-worker' || result.assignmentId !== handoff.assignmentId || result.phase !== handoff.phase) fail('Worker result identity/phase does not match handoff');
  if (!['COMPLETE', 'BLOCKED'].includes(result.status)) fail('Worker result is not terminal');
  if (handoff.phase === 'SEARCH' && ((handoff.approvedAssets ?? []).length || (result.assets ?? []).length)) fail('SEARCH cannot approve or report final acquired assets');
  if (!handoff.resultPath || basename(expectedResult) !== 'result.json' || expectedResult !== resolve(resultPath) || !inside(handoffDir, expectedResult)) fail('Result path does not match assigned worker directory');
  try { if (!inside(realpathSync(handoffDir), realpathSync(resultPath))) fail('Result file escapes assigned worker directory'); }
  catch { fail('Worker result or handoff directory unreadable'); }
  if (!handoff.inspectionDirectory || dirname(located(handoff.inspectionDirectory ?? '', workspace)) !== handoffDir || basename(handoff.inspectionDirectory) !== 'inspection') fail('Inspection directory is outside assigned worker directory');
  else { try { if (!inside(realpathSync(handoffDir), realpathSync(located(handoff.inspectionDirectory, workspace)))) fail('Inspection directory escapes assigned worker directory'); }
    catch { fail('Inspection directory unreadable'); } }
  if (!/^[0-9a-f]{64}$/.test(handoff.timelineSha256 ?? '') || result.timelineSha256 !== handoff.timelineSha256) fail('Timeline snapshot mismatch');
  try { if (sha256(readFileSync(located(handoff.timeline, workspace))) !== handoff.timelineSha256) fail('Timeline changed after worker handoff'); }
  catch { fail('Handoff timeline unreadable'); }
  if (!Array.isArray(handoff.requirements) || handoff.requirements.length === 0 || !Array.isArray(result.findings)) return [...errors, 'Expected nonempty handoff requirements and result findings'];
  const assigned = new Map();
  for (const item of handoff.requirements) {
    if (typeof item.id !== 'string' || assigned.has(item.id) || !/^(?:(?:VIS|SRC-AUD|MUS|AMB|SFX)-\d{3,}|REQ-VIS-VIS-SEQ-\d{3,}-\d+)$/.test(item.id)) fail(`Invalid/duplicate assigned ID: ${item.id}`);
    assigned.set(item.id, item);
    if (!item.intent || !Array.isArray(item.hardConstraints)) fail(`${item.id}: missing intent/hardConstraints`);
  }
  const seen = new Set();
  for (const finding of result.findings) {
    const id = finding?.requirementId;
    if (!assigned.has(id) || seen.has(id)) { fail(`Unknown/duplicate finding: ${id}`); continue; }
    seen.add(id);
    if (handoff.phase === 'ACQUIRE') continue;
    if (!['FOUND', 'NOT_FOUND', 'BLOCKED'].includes(finding.status)) fail(`${id}: invalid SEARCH finding status`);
    if (!Array.isArray(finding.queries) || (finding.status !== 'BLOCKED' && finding.queries.length === 0)) fail(`${id}: missing search evidence`);
    if (!Array.isArray(finding.candidates)) { fail(`${id}: candidates must be an array`); continue; }
    if (finding.status === 'FOUND' && finding.candidates.length === 0) fail(`${id}: FOUND without source candidates`);
    if (finding.status !== 'FOUND' && finding.candidates.length !== 0) fail(`${id}: non-FOUND includes source candidates`);
    if (finding.status === 'BLOCKED' && !finding.reason) fail(`${id}: missing blocker reason`);
    for (const candidate of finding.candidates) {
      if (!candidate.provider || !candidate.sourceId || !candidate.title || !validSourceUrl(candidate.provider, candidate.url, workspace, handoff.localSources)) fail(`${id}: incomplete/unsafe source identity`);
      if (!validRange(candidate.relevantRange)) fail(`${id}: invalid source-relative range`);
      if (!candidate.rights?.status) fail(`${id}: missing rights status`);
      for (const constraint of assigned.get(id).hardConstraints ?? []) {
        if (!(candidate.hardConstraints ?? []).some(gate => gate.constraint === constraint && gate.result === 'PASS' && gate.basis)) fail(`${id}: candidate lacks evidence for hard constraint: ${constraint}`);
      }
      if (id.startsWith('VIS-') || id.startsWith('REQ-VIS-')) {
        const observed = (candidate.evidence ?? []).filter(entry => entry.kind === 'OBSERVED' && Number.isFinite(entry.sourceTimeMs) && entry.sourceTimeMs >= 0 && (candidate.relevantRange === 'FULL' || (candidate.relevantRange && entry.sourceTimeMs >= candidate.relevantRange.startMs && entry.sourceTimeMs <= candidate.relevantRange.endMs)) && entry.description && entry.sample);
        if (observed.length === 0) fail(`${id}: visual candidate lacks observed timestamped samples`);
        for (const entry of observed) {
          try { const allowed = realpathSync(located(handoff.inspectionDirectory, workspace)); const actual = realpathSync(located(entry.sample, workspace)); if (!inside(allowed, actual) || !statSync(actual).isFile()) throw Error(); }
          catch { fail(`${id}: observed sample missing or outside inspection directory`); }
        }
      }
    }
  }
  for (const id of assigned.keys()) if (!seen.has(id)) fail(`Missing assigned finding: ${id}`);
  if (handoff.phase === 'ACQUIRE' && packageRoot) validateAcquisition(handoff, result, assigned, packageRoot, workspace, fail);
  return errors;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [handoffPath, resultPath] = process.argv.slice(2);
  if (!handoffPath || !resultPath) { console.error('Usage: node verify-worker-result.mjs <handoff.json> <result.json>'); process.exitCode = 2; }
  else {
    try {
      const handoff = JSON.parse(readFileSync(handoffPath, 'utf8'));
      const result = JSON.parse(readFileSync(resultPath, 'utf8'));
      const errors = validateWorkerResult(handoff, result, { handoffPath, resultPath });
      if (errors.length) { console.error(errors.join('\n')); process.exitCode = 1; }
      else console.log(`Verified worker ${result.assignmentId} (${result.phase}): ${result.findings.length} assigned needs`);
    } catch (error) { console.error(error.message); process.exitCode = 1; }
  }
}
