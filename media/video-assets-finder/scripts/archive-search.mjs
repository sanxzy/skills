#!/usr/bin/env -S deno run --allow-net=esm.sh,archive.org
// Search Archive metadata and acquire a specifically identified file without an npm install.
// Neither download nor Archive metadata verifies visual suitability or reuse rights.
import { createHash } from 'node:crypto';

const SEARCH_SERVICE = 'https://esm.sh/@internetarchive/search-service@2.7.2';

function fail(message) {
  throw new Error(message);
}

export function parseArgs(args) {
  const [mode, value, ...rest] = args;
  if (!['search', 'item', 'download'].includes(mode) || !value) fail('Usage: archive-search.mjs search <query> [--rows 1..50] | item <identifier> | download <identifier> <file-name> <output> [--max-bytes 1..2147483648]');
  if (mode === 'item' && rest.length) fail('item accepts one identifier');
  if (mode === 'download') {
    const [name, output, flag, size] = rest;
    if (!name || !output || (flag && (flag !== '--max-bytes' || !/^[1-9]\d*$/.test(size ?? '') || rest.length !== 4)) || (!flag && rest.length !== 2)) fail('Expected download <identifier> <file-name> <output> [--max-bytes 1..2147483648]');
    const maxBytes = flag ? Number(size) : 200 * 1024 * 1024;
    if (maxBytes > 2147483648) fail('Download limit exceeds 2 GiB');
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$/.test(value)) fail('Invalid Archive identifier');
    return { mode, value, name, output, maxBytes };
  }
  let rows = 10;
  if (mode === 'search' && rest.length) {
    if (rest.length !== 2 || rest[0] !== '--rows' || !/^\d+$/.test(rest[1])) fail('Expected --rows 1..50');
    rows = Number(rest[1]);
    if (rows < 1 || rows > 50) fail('rows must be 1..50');
  }
  if (mode === 'item' && !/^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$/.test(value)) fail('Invalid Archive identifier');
  if (mode === 'search' && value.length > 500) fail('Query too long');
  return { mode, value, rows };
}

export async function search(query, rows) {
  // The browser-oriented search-service reads a page URL; esm.sh maps it to globalThis.location.
  globalThis.location ??= new URL('https://archive.org/');
  const { SearchService, SearchType } = await import(SEARCH_SERVICE);
  const result = await SearchService.default.search({
    query, rows, fields: ['identifier', 'title', 'creator', 'date', 'mediatype', 'licenseurl'],
    aggregations: { omit: true },
  }, SearchType.METADATA);
  if (!result.success) fail(`Archive search failed: ${result.error?.message ?? 'unknown provider error'}`);
  return {
    total: result.success.response.totalResults,
    results: result.success.response.results.map(item => ({
      identifier: item.identifier,
      title: item.title?.value ?? null,
      creator: item.creator?.value ?? null,
      date: item.date?.value ?? null,
      mediatype: item.mediatype?.value ?? null,
      licenseurl: item.licenseurl?.value ?? null,
    })),
  };
}

export async function item(identifier) {
  const response = await fetch(`https://archive.org/metadata/${encodeURIComponent(identifier)}`);
  if (!response.ok) fail(`Archive metadata HTTP ${response.status}`);
  const data = await response.json();
  if (!data.metadata || !Array.isArray(data.files)) fail('Archive item metadata/files unavailable');
  const { title, creator, date, licenseurl, rights, collection, mediatype, description, subject, genre } = data.metadata;
  return {
    identifier,
    url: `https://archive.org/details/${encodeURIComponent(identifier)}`,
    metadata: { title, creator, date, licenseurl, rights, collection, mediatype, description: typeof description === 'string' ? description.slice(0, 4000) : null, descriptionTruncated: typeof description === 'string' && description.length > 4000, subject, genre },
    filesTotal: data.files.length,
    filesTruncated: data.files.length > 500,
    files: data.files.slice(0, 500).map(({ name, source, size, length, format, md5 }) => ({
      name, source, size, length, format, md5,
      url: typeof name === 'string' && name && !name.split('/').includes('..')
        ? `https://archive.org/download/${encodeURIComponent(identifier)}/${name.split('/').map(encodeURIComponent).join('/')}` : null,
    })),
  };
}

export async function download(identifier, name, output, maxBytes = 200 * 1024 * 1024) {
  try { await Deno.lstat(output); fail('Target already exists; inspect it before retrying'); }
  catch (error) { if (!(error instanceof Deno.errors.NotFound)) throw error; }
  const listing = await item(identifier);
  const file = listing.files.find(entry => entry.name === name && entry.url);
  if (!file) fail('Named file unavailable in bounded Archive item listing');
  const expectedSize = file.size == null ? null : Number(file.size);
  if (expectedSize !== null && (!Number.isSafeInteger(expectedSize) || expectedSize <= 0 || expectedSize > maxBytes)) fail('Archive file size missing, invalid or exceeds download limit');
  const url = new URL(file.url);
  if (url.protocol !== 'https:' || url.hostname !== 'archive.org') fail('Unsafe Archive file URL');
  const response = await fetch(url, { signal: AbortSignal.timeout(120000) });
  if (response.status !== 200 || !response.body || !/^(?:archive\.org|[a-z0-9.-]+\.archive\.org)$/.test(new URL(response.url).hostname)) fail(`Archive download rejected: HTTP ${response.status}`);
  const reportedSize = Number(response.headers.get('content-length'));
  if (reportedSize > maxBytes) { await response.body.cancel(); fail('Archive response exceeds download limit'); }
  const part = `${output}.part`;
  let temporary = false, written = 0;
  const sha256 = createHash('sha256'), md5 = createHash('md5');
  try {
    const target = await Deno.open(part, { createNew: true, write: true });
    temporary = true;
    try {
      for await (const chunk of response.body) {
        written += chunk.byteLength;
        if (written > maxBytes) fail('Archive response exceeded download limit');
        sha256.update(chunk); md5.update(chunk);
        let offset = 0;
        while (offset < chunk.byteLength) offset += await target.write(chunk.subarray(offset));
      }
      if (!written || (expectedSize !== null && written !== expectedSize)) fail('Archive download size differs from item metadata');
      if (file.md5 && md5.digest('hex').toLowerCase() !== file.md5.toLowerCase()) fail('Archive download checksum differs from item metadata');
    } finally { target.close(); }
    await Deno.link(part, output); // publish exclusively; never replace an existing approved target
    return { identifier, name, sourceUrl: file.url, localFile: output, sizeBytes: written, sha256: sha256.digest('hex'), metadataMd5Verified: Boolean(file.md5) };
  } finally { if (temporary) await Deno.remove(part); }
}

if (import.meta.main) {
  try {
    const { mode, value, rows, name, output, maxBytes } = parseArgs(Deno.args);
    console.log(JSON.stringify(mode === 'search' ? await search(value, rows) : mode === 'item' ? await item(value) : await download(value, name, output, maxBytes), null, 2));
  } catch (error) {
    console.error(error.message);
    Deno.exitCode = 1;
  }
}
