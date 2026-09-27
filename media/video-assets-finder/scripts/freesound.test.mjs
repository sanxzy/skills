import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, existsSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { parseArgs, search, download } from './freesound.mjs';

test('bounds arguments and requires credentials', async () => {
  assert.deepEqual(parseArgs(['search', 'low muted impact']), { mode: 'search', value: 'low muted impact' });
  assert.throws(() => parseArgs(['download', '../../escape', '/tmp/clip.wav']), /Usage/);
  await assert.rejects(search('impact', ''), /AUTH_FAILURE/);
  await assert.rejects(download('123', '/tmp/not-created.wav', ''), /AUTH_FAILURE/);
});

test('search uses token header and returns source metadata without exposing token', async () => {
  const old = globalThis.fetch;
  try {
    globalThis.fetch = async (url, init) => {
      assert.equal(url.pathname, '/apiv2/search/');
      assert.equal(url.searchParams.get('query'), 'soft impact');
      assert.equal(init.headers.Authorization, 'Token secret');
      assert.ok(!url.href.includes('secret'));
      return new Response(JSON.stringify({ count: 1, results: [{ id: 27, name: 'tap', username: 'author', license: 'Creative Commons 0', duration: 1 }] }), { status: 200 });
    };
    assert.equal((await search('soft impact', 'secret')).results[0].id, 27);
  } finally { globalThis.fetch = old; }
});

test('original download writes only a successful nonempty file and never overwrites', async t => {
  const dir = mkdtempSync(join(tmpdir(), 'freesound-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const target = join(dir, 'AST-SFX-001.wav');
  const old = globalThis.fetch;
  try {
    globalThis.fetch = async (url, init) => {
      assert.equal(url.pathname, '/apiv2/sounds/27/download/');
      assert.equal(init.headers.Authorization, 'Bearer bearer');
      return new Response(Buffer.from('sample'), { status: 200 });
    };
    assert.equal((await download('27', target, 'bearer')).sizeBytes, 6);
    assert.equal(readFileSync(target, 'utf8'), 'sample');
    assert.equal(existsSync(`${target}.part`), false);
    await assert.rejects(download('27', target, 'bearer'), /exists/);
  } finally { globalThis.fetch = old; }
});

test('a destination appearing during download is preserved, not replaced', async t => {
  const dir = mkdtempSync(join(tmpdir(), 'freesound-race-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const target = join(dir, 'AST-SFX-001.wav');
  const old = globalThis.fetch;
  try {
    globalThis.fetch = async () => {
      writeFileSync(target, 'existing user file');
      return new Response(Buffer.from('downloaded media'), { status: 200 });
    };
    await assert.rejects(download('27', target, 'bearer'), /EEXIST/);
    assert.equal(readFileSync(target, 'utf8'), 'existing user file');
    assert.equal(existsSync(`${target}.part`), false);
  } finally { globalThis.fetch = old; }
});
