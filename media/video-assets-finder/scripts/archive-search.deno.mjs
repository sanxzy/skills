import { createHash } from 'node:crypto';
import { parseArgs, item, download } from './archive-search.mjs';

Deno.test('Archive adapter bounds query and identifier input', () => {
  if (parseArgs(['search', 'mediatype:movies', '--rows', '2']).rows !== 2) throw Error('rows not parsed');
  const args = parseArgs(['download', 'valid-id', 'clip.mp3', 'clip.mp3', '--max-bytes', '100']);
  if (args.maxBytes !== 100 || args.name !== 'clip.mp3') throw Error('Download arguments not parsed');
  for (const invalid of [['item', '../escape'], ['search', 'test', '--rows', '1000'], ['search', ''], ['download', 'valid-id', 'clip.mp3'], ['download', 'valid-id', 'clip.mp3', 'clip.mp3', '--max-bytes', '0']]) {
    let rejected = false;
    try { parseArgs(invalid); } catch { rejected = true; }
    if (!rejected) throw Error(`Accepted invalid arguments: ${invalid.join(' ')}`);
  }
});

Deno.test('Archive metadata preserves file and rights metadata', async () => {
  const prior = globalThis.fetch;
  try {
    globalThis.fetch = async url => {
      if (url !== 'https://archive.org/metadata/valid-id') throw Error('Unexpected URL');
      return new Response(JSON.stringify({ metadata: { title: 'Archive item', creator: 'Archive', rights: 'rights statement', description: 'Three recorded gunshots', subject: ['Sound Effects'], genre: 'Sound Effects' }, files: [{ name: 'old films/video clip.mp4', source: 'original', size: '42', format: 'MPEG4', md5: 'abc' }] }), { status: 200 });
    };
    const found = await item('valid-id');
    if (found.metadata.rights !== 'rights statement' || found.metadata.genre !== 'Sound Effects' || found.metadata.description !== 'Three recorded gunshots' || found.metadata.subject[0] !== 'Sound Effects' || found.files[0].url !== 'https://archive.org/download/valid-id/old%20films/video%20clip.mp4') throw Error('Incomplete metadata or incorrect file URL');
  } finally { globalThis.fetch = prior; }
});

Deno.test('Archive download streams one listed file, verifies metadata and cannot overwrite output', async () => {
  const root = await Deno.makeTempDir();
  const output = `${root}/clip.mp3`;
  const prior = globalThis.fetch;
  const bytes = new TextEncoder().encode('small real payload');
  const md5 = createHash('md5').update(bytes).digest('hex');
  try {
    globalThis.fetch = async url => {
      if (url === 'https://archive.org/metadata/valid-id') return new Response(JSON.stringify({ metadata: { title: 'Test' }, files: [{ name: 'clip.mp3', size: String(bytes.length), md5 }] }), { status: 200 });
      if (String(url) !== 'https://archive.org/download/valid-id/clip.mp3') throw Error('Unexpected download URL');
      const response = new Response(bytes, { status: 200 });
      Object.defineProperty(response, 'url', { value: 'https://ia800000.us.archive.org/download/valid-id/clip.mp3' });
      return response;
    };
    const found = await download('valid-id', 'clip.mp3', output, 100);
    if (found.sizeBytes !== bytes.length || !found.metadataMd5Verified || found.sha256 !== createHash('sha256').update(bytes).digest('hex')) throw Error('Downloaded integrity report is incorrect');
    if (new TextDecoder().decode(await Deno.readFile(output)) !== 'small real payload') throw Error('Wrong local file content');
    let rejected = false;
    try { await download('valid-id', 'clip.mp3', output, 100); } catch { rejected = true; }
    if (!rejected || new TextDecoder().decode(await Deno.readFile(output)) !== 'small real payload') throw Error('Existing output was overwritten');
    if ([...Deno.readDirSync(root)].some(entry => entry.name.endsWith('.part'))) throw Error('Leaked partial download');
    const badOutput = `${root}/bad.mp3`;
    globalThis.fetch = async url => {
      if (url === 'https://archive.org/metadata/valid-id') return new Response(JSON.stringify({ metadata: {}, files: [{ name: 'clip.mp3', size: String(bytes.length), md5: '00000000000000000000000000000000' }] }), { status: 200 });
      const response = new Response(bytes, { status: 200 });
      Object.defineProperty(response, 'url', { value: 'https://ia800000.us.archive.org/download/valid-id/clip.mp3' });
      return response;
    };
    let badChecksumRejected = false;
    try { await download('valid-id', 'clip.mp3', badOutput, 100); } catch (error) { badChecksumRejected = /checksum differs/.test(error.message); }
    if (!badChecksumRejected || [...Deno.readDirSync(root)].some(entry => entry.name.startsWith('bad.mp3'))) throw Error('Corrupt file published or partial left behind');
  } finally { globalThis.fetch = prior; await Deno.remove(root, { recursive: true }); }
});
