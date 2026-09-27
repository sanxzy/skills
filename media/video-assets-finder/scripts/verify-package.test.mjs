import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { validate, validateTodo } from './verify-package.mjs';

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'asset-package-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const packageDir = join(root, '.assets', 'example');
  mkdirSync(packageDir, { recursive: true });
  const localFile = join(packageDir, 'AST-VID-001.mp4');
  writeFileSync(localFile, 'placeholder');
  const manifest = {
    schemaVersion: 1,
    requirements: [
      { id: 'VIS-001', type: 'BROLL', status: 'RESOLVED', assetIds: ['AST-VID-001'] },
      { id: 'MUS-001', type: 'MUSIC', status: 'UNRESOLVED', reason: 'No suitable candidate', assetIds: [] },
      { id: 'VIS-002', type: 'HOLD', status: 'NO_NEW_ASSET_REQUIRED', assetIds: [] },
    ],
    sources: [{ id: 'SRC-YT-001', provider: 'youtube', url: 'https://example.org/video', title: 'Example', credit: 'Example — https://example.org/video', retrievedAt: '2026-01-01', rights: { status: 'REVIEW_REQUIRED' } }],
    assets: [{ id: 'AST-VID-001', sourceId: 'SRC-YT-001', localFile, mediaKind: 'VIDEO', relevantRange: { startMs: 1000, endMs: 5000 }, acquiredRange: { startMs: 0, endMs: 6000 }, verification: { technical: 'PASS', audioContent: 'NOT_LISTENED' } }],
  };
  return { root, packageDir, localFile, manifest, timeline: 'Visual: VIS-001 — video\nVisual: VIS-002 — HOLD VIS-001\nAudio: MUS-001 optional\n' };
}

test('validates coverage, stable refs, local paths, and limits without probing', t => {
  const f = fixture(t);
  assert.deepEqual(validate(f.timeline, f.manifest, f.packageDir, { probe: false }), []);
  delete f.manifest.assets[0].mediaKind;
  assert.match(validate(f.timeline, f.manifest, f.packageDir, { probe: false }).join('\n'), /invalid or missing mediaKind/);
  f.manifest.assets[0].mediaKind = 'VIDEO';
  const credit = f.manifest.sources[0].credit;
  delete f.manifest.sources[0].credit;
  assert.match(validate(f.timeline, f.manifest, f.packageDir, { probe: false }).join('\n'), /provenance\/credit\/rights incomplete/);
  f.manifest.sources[0].credit = credit;
  f.manifest.sources[0].rights.status = 'VERIFIED';
  assert.match(validate(f.timeline, f.manifest, f.packageDir, { probe: false }).join('\n'), /rights claim lacks evidence/);
  f.manifest.sources[0].rights = { status: 'REVIEW_REQUIRED' };
  f.manifest.sources.push({ id: 'SRC-ORPHAN', provider: 'youtube', url: 'https://example.org/orphan', title: 'Orphan', credit: 'Orphan — https://example.org/orphan', retrievedAt: '2026-01-01', rights: { status: 'REVIEW_REQUIRED' } });
  assert.match(validate(f.timeline, f.manifest, f.packageDir, { probe: false }).join('\n'), /source has no current acquired asset/);
  f.manifest.sources.pop();
  f.manifest.requirements.pop();
  assert.match(validate(f.timeline, f.manifest, f.packageDir, { probe: false }).join('\n'), /Missing timeline requirement ID: VIS-002/);
  f.manifest.requirements.push({ id: 'VIS-002', status: 'NO_NEW_ASSET_REQUIRED', assetIds: [] });
  f.manifest.assets[0].localFile = join(f.root, 'outside.mp4');
  writeFileSync(f.manifest.assets[0].localFile, 'outside');
  assert.match(validate(f.timeline, f.manifest, f.packageDir, { probe: false }).join('\n'), /escapes asset package/);
});

test('acquisition must contain the entire source-relative useful range', t => {
  const f = fixture(t);
  f.manifest.assets[0].acquiredRange.endMs = 3000;
  assert.match(validate(f.timeline, f.manifest, f.packageDir, { probe: false }).join('\n'), /acquiredRange does not contain relevantRange/);
  f.manifest.assets[0].acquiredRange = 'FULL';
  assert.deepEqual(validate(f.timeline, f.manifest, f.packageDir, { probe: false }), []);
  f.manifest.assets[0].relevantRange = 'FULL';
  f.manifest.assets[0].acquiredRange = { startMs: 0, endMs: 6000 };
  assert.match(validate(f.timeline, f.manifest, f.packageDir, { probe: false }).join('\n'), /full relevant content was not acquired/);
});

test('in-progress requirement checkpoints pass partial gate but not final gate', t => {
  const f = fixture(t);
  f.manifest.requirements[1] = { id: 'MUS-001', type: 'MUSIC', status: 'SEARCHING', assetIds: [] };
  assert.deepEqual(validate(f.timeline, f.manifest, f.packageDir, { probe: false, complete: false }), []);
  f.manifest.requirements[1].status = 'QUEUED';
  assert.deepEqual(validate(f.timeline, f.manifest, f.packageDir, { probe: false, complete: false }), []);
  assert.match(validate(f.timeline, f.manifest, f.packageDir, { probe: false }).join('\n'), /MUS-001: nonterminal/);
});

test('host TODO entries reconcile against manifest and retain non-current log separately', t => {
  const f = fixture(t);
  const todo = `## Current requirements\n- [x] VIS-001 | status=RESOLVED | required | AST-VID-001\n- [x] MUS-001 | status=UNRESOLVED | optional | no match\n- [x] VIS-002 | status=NO_NEW_ASSET_REQUIRED | required | HOLD\n\n## Log\n- [x] VIS-099 | status=RESOLVED | removed prior ID\n`;
  assert.deepEqual(validateTodo(todo, f.manifest), []);
  assert.match(validateTodo(todo.replace('status=UNRESOLVED', 'status=SEARCHING'), f.manifest).join('\n'), /TODO checkbox\/status mismatch/);
  assert.match(validateTodo(todo.replace('VIS-002 |', 'VIS-003 |'), f.manifest).join('\n'), /VIS-002: missing current TODO entry/);
});

test('probes actual stream type and duration for resolved files', t => {
  const f = fixture(t);
  const ffmpeg = spawnSync('ffmpeg', ['-v', 'error', '-f', 'lavfi', '-i', 'color=c=black:s=32x32:d=1', '-c:v', 'mpeg4', '-y', f.localFile], { encoding: 'utf8', timeout: 20000 });
  if (ffmpeg.error?.code === 'ENOENT') return t.skip('ffmpeg unavailable');
  assert.equal(ffmpeg.status, 0, ffmpeg.stderr);
  assert.deepEqual(validate(f.timeline, f.manifest, f.packageDir, { workspace: f.root }), []);
  f.manifest.requirements[0].assetIds = null;
  assert.match(validate(f.timeline, f.manifest, f.packageDir, { workspace: f.root }).join('\n'), /assetIds must be an array/);
  f.manifest.requirements[0].assetIds = ['AST-VID-001'];
  f.manifest.requirements[0].type = 'SOURCE_AUDIO';
  assert.match(validate(f.timeline, f.manifest, f.packageDir, { workspace: f.root }).join('\n'), /missing required source-audio stream/);
});

test('source audio associated with footage must share its source and relevant time range', t => {
  const f = fixture(t);
  f.timeline += 'SOURCE_AUDIO SRC-AUD-001\n';
  f.manifest.requirements.push({ id: 'SRC-AUD-001', type: 'NAT_SOUND', status: 'RESOLVED', linkedVisualRequirementId: 'VIS-001', assetIds: ['AST-VID-001'] });
  assert.deepEqual(validate(f.timeline, f.manifest, f.packageDir, { probe: false }), []);
  f.manifest.assets.push({ id: 'AST-NAT-002', sourceId: 'SRC-YT-001', localFile: f.localFile, mediaKind: 'VIDEO', relevantRange: { startMs: 6000, endMs: 8000 }, acquiredRange: { startMs: 0, endMs: 9000 }, verification: { technical: 'PASS' } });
  f.manifest.requirements.at(-1).assetIds = ['AST-NAT-002'];
  assert.match(validate(f.timeline, f.manifest, f.packageDir, { probe: false }).join('\n'), /does not overlap its linked visual/);
  f.manifest.assets.at(-1).relevantRange = { startMs: 2000, endMs: 3000 };
  assert.deepEqual(validate(f.timeline, f.manifest, f.packageDir, { probe: false }), []);
  f.manifest.sources.push({ id: 'SRC-YT-OTHER', provider: 'youtube', url: 'https://example.org/other', title: 'Other', credit: 'Other — https://example.org/other', retrievedAt: '2026-01-01', rights: { status: 'REVIEW_REQUIRED' } });
  f.manifest.assets.at(-1).sourceId = 'SRC-YT-OTHER';
  assert.match(validate(f.timeline, f.manifest, f.packageDir, { probe: false }).join('\n'), /does not overlap its linked visual/);
});

test('visual requirements with original audio cannot resolve from silent video', t => {
  const f = fixture(t);
  const generated = spawnSync('ffmpeg', ['-v', 'error', '-f', 'lavfi', '-i', 'color=c=black:s=32x32:d=1', '-c:v', 'mpeg4', '-y', f.localFile], { encoding: 'utf8', timeout: 20000 });
  if (generated.error?.code === 'ENOENT') return t.skip('ffmpeg unavailable');
  assert.equal(generated.status, 0, generated.stderr);
  f.manifest.requirements[0].sourceAudioRequired = true;
  assert.match(validate(f.timeline, f.manifest, f.packageDir, { workspace: f.root }).join('\n'), /missing required source-audio stream/);
});

test('explicitly sourced stills pass dimension checks without fabricated playback duration', t => {
  const f = fixture(t);
  const image = join(f.packageDir, 'AST-IMG-001.png');
  const generated = spawnSync('ffmpeg', ['-v', 'error', '-f', 'lavfi', '-i', 'color=c=black:s=32x32:d=1', '-frames:v', '1', '-y', image], { encoding: 'utf8', timeout: 20000 });
  if (generated.error?.code === 'ENOENT') return t.skip('ffmpeg unavailable');
  assert.equal(generated.status, 0, generated.stderr);
  f.manifest.assets[0].localFile = image;
  f.manifest.assets[0].mediaKind = 'IMAGE';
  f.manifest.assets[0].relevantRange = 'FULL';
  f.manifest.assets[0].acquiredRange = 'FULL';
  assert.deepEqual(validate(f.timeline, f.manifest, f.packageDir, { workspace: f.root }), []);
  f.manifest.requirements[0].requiresMotion = true;
  assert.match(validate(f.timeline, f.manifest, f.packageDir, { workspace: f.root }).join('\n'), /still image cannot satisfy required moving footage/);
  f.manifest.assets[0].mediaKind = 'VIDEO';
  assert.match(validate(f.timeline, f.manifest, f.packageDir, { workspace: f.root }).join('\n'), /no measurable positive duration/);
});

test('CLI verifies a complete local package with the host checklist', t => {
  const f = fixture(t);
  const ffmpeg = spawnSync('ffmpeg', ['-v', 'error', '-f', 'lavfi', '-i', 'color=c=black:s=32x32:d=1', '-c:v', 'mpeg4', '-y', f.localFile], { encoding: 'utf8', timeout: 20000 });
  if (ffmpeg.error?.code === 'ENOENT') return t.skip('ffmpeg unavailable');
  assert.equal(ffmpeg.status, 0, ffmpeg.stderr);
  const timelinePath = join(f.root, 'example.timeline.md');
  const manifestPath = join(f.packageDir, 'manifest.json');
  writeFileSync(timelinePath, f.timeline);
  writeFileSync(manifestPath, JSON.stringify(f.manifest));
  writeFileSync(join(f.packageDir, 'progress.todo.md'), '## Current requirements\n- [x] VIS-001 | status=RESOLVED | required\n- [x] MUS-001 | status=UNRESOLVED | optional\n- [x] VIS-002 | status=NO_NEW_ASSET_REQUIRED | required\n\n## Log\n');
  const script = fileURLToPath(new URL('./verify-package.mjs', import.meta.url));
  const run = spawnSync(process.execPath, [script, timelinePath, manifestPath], { cwd: f.root, encoding: 'utf8' });
  assert.equal(run.status, 0, run.stderr);
  assert.match(run.stdout, /Verified: 3 requirements, 1 local assets/);
});
