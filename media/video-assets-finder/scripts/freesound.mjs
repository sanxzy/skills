#!/usr/bin/env node
// Freesound APIv2 metadata search and authorized original-file acquisition. Never print credentials.
import { existsSync, mkdirSync, createWriteStream, linkSync, rmSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { Readable, Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { fileURLToPath } from 'node:url';

const BASE = 'https://freesound.org/apiv2/';

export function parseArgs(args) {
  const [mode, value, ...rest] = args;
  if (mode === 'search' && value && rest.length === 0 && value.length <= 300) return { mode, value };
  if (mode === 'download' && /^\d+$/.test(value ?? '') && rest.length === 1 && rest[0]) return { mode, value, file: rest[0] };
  throw Error('Usage: freesound.mjs search <query> | download <sound-id> <local-output-file>');
}

export async function search(query, token = process.env.FREESOUND_API_TOKEN) {
  if (!token) throw Error('FREESOUND_API_TOKEN unavailable (AUTH_FAILURE)');
  const url = new URL('search/', BASE);
  url.searchParams.set('query', query);
  url.searchParams.set('page_size', '10');
  url.searchParams.set('fields', 'id,url,name,username,license,tags,description,duration,type,channels,samplerate,previews');
  const response = await fetch(url, { headers: { Authorization: `Token ${token}` }, signal: AbortSignal.timeout(20000) });
  if (!response.ok) throw Error(`Freesound search HTTP ${response.status}`);
  const data = await response.json();
  return { count: data.count, results: (data.results ?? []).map(({ id, url, name, username, license, tags, description, duration, type, channels, samplerate, previews }) => ({ id, url, name, username, license, tags, description, duration, type, channels, samplerate, previews })) };
}

export async function download(id, output, token = process.env.FREESOUND_OAUTH_TOKEN) {
  if (!token) throw Error('FREESOUND_OAUTH_TOKEN unavailable (AUTH_FAILURE: original file requires OAuth2)');
  const target = resolve(output);
  if (existsSync(target) || existsSync(`${target}.part`)) throw Error('Target or partial file exists; inspect it before retrying');
  const response = await fetch(new URL(`sounds/${id}/download/`, BASE), { headers: { Authorization: `Bearer ${token}` }, redirect: 'follow', signal: AbortSignal.timeout(120000) });
  if (!response.ok || !response.body) throw Error(`Freesound download HTTP ${response.status}`);
  const length = Number(response.headers.get('content-length'));
  const limit = 200 * 1024 * 1024; // refuse unexpectedly huge SFX; configurable acquisition belongs to host.
  if (length > limit) throw Error('Freesound file exceeds 200 MiB safety limit');
  mkdirSync(dirname(target), { recursive: true });
  let bytes = 0;
  try {
    await pipeline(Readable.fromWeb(response.body), new Transform({ transform(chunk, _encoding, callback) {
      bytes += chunk.length;
      callback(bytes > limit ? Error('Freesound file exceeded 200 MiB safety limit') : null, chunk);
    } }), createWriteStream(`${target}.part`, { flags: 'wx' }));
    if (!bytes) throw Error('Freesound returned empty file');
    // Exclusive same-directory hard link publishes a fully written file without replacing
    // an unrelated destination that appeared after the initial existence check.
    linkSync(`${target}.part`, target);
    rmSync(`${target}.part`);
  } catch (error) { rmSync(`${target}.part`, { force: true }); throw error; }
  return { localFile: target, sizeBytes: bytes, sourceUrl: `https://freesound.org/s/${id}/`, kind: 'original' };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const args = parseArgs(process.argv.slice(2));
    console.log(JSON.stringify(args.mode === 'search' ? await search(args.value) : await download(args.value, args.file), null, 2));
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
