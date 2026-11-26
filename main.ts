// One Image: Wednesday 25 November 2026 — entrypoint.
//
// The submitted artifact is the PNG beside this file (entry.png), drawn
// by render.py from headlines.json. This program checks that artifact
// and hands it to the grader: it reads the PNG, walks every chunk to
// confirm the file is whole, checks its size and dimensions, compares
// its SHA-256 and byte count against image_manifest.json, and recounts
// the rendered headlines from headlines.json so the manifest cannot
// drift from the source data. Only then does it copy the verified PNG
// bytes into the grader's output directory, together with a small
// deterministic summary.json, and read the delivered file back to prove
// the copy is byte-identical.
//
// The grader mounts the repo READ-ONLY, so this program writes nowhere
// except the output directory named by MAKEFUN_OUTPUT_DIR (default
// "/output"). Verification itself is pure reads.
//
// Run: node main.ts   (exit 0 = artifact verified and delivered)

import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const COMPETITION = "news-image-20261125";
const DATE = "2026-11-25";
const MIN_BYTES = 200_000; // winning editions of this bounty land ~200-900 KB
const MAX_BYTES = 900_000;

function fail(msg: string): never {
  console.error(`VERIFY FAIL: ${msg}`);
  process.exit(1);
}

// CRC-32 (PNG chunk checksums) built once at startup.
const CRC_TABLE = (() => {
  const table = new Int32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c;
  }
  return table;
})();

function crc32(buf: Buffer, from: number, to: number): number {
  let c = 0xffffffff;
  for (let i = from; i < to; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

// Walk every chunk: the stored CRC of each chunk must match the CRC32
// of its type+data, and the file must end with IEND. A truncated or
// corrupted download fails here instead of reaching the judge.
function pngDimensions(buf: Buffer): { width: number; height: number } {
  const sig = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
  for (let i = 0; i < sig.length; i++) {
    if (buf[i] !== sig[i]) fail("entry.png is not a PNG (bad signature)");
  }
  let off = 8;
  let size: { width: number; height: number } | null = null;
  let sawIend = false;
  while (off + 8 <= buf.length) {
    const len = buf.readUInt32BE(off);
    const type = buf.toString("ascii", off + 4, off + 8);
    if (off + 12 + len > buf.length) fail(`entry.png chunk ${type} overruns the file`);
    const stored = buf.readUInt32BE(off + 8 + len);
    if (crc32(buf, off + 4, off + 8 + len) !== stored) {
      fail(`entry.png chunk ${type} has a bad CRC`);
    }
    if (type === "IHDR") {
      size = { width: buf.readUInt32BE(off + 8), height: buf.readUInt32BE(off + 12) };
    }
    off += 12 + len;
    if (type === "IEND") {
      sawIend = true;
      break;
    }
  }
  if (!size) fail("entry.png has no IHDR chunk");
  if (!sawIend) fail("entry.png has no IEND chunk");
  return size;
}

// The renderer draws the lead, the second story, the first three
// stories of every section, and the first eight briefs. Recount them
// from the source data so the manifest cannot drift from the headlines.
function expectedItems(data: any): string[] {
  const items: string[] = [data.lead.headline, data.second.headline];
  for (const sec of data.sections) {
    for (const st of sec.stories.slice(0, 3)) items.push(st.h);
  }
  for (const [tag, text] of data.briefs.slice(0, 8)) items.push(`${tag}: ${text}`);
  return items;
}

function main(): void {
  const png = readFileSync(join(HERE, "entry.png"));
  const data = JSON.parse(readFileSync(join(HERE, "headlines.json"), "utf8"));
  const manifest = JSON.parse(readFileSync(join(HERE, "image_manifest.json"), "utf8"));

  const { width, height } = pngDimensions(png);
  if (width !== 1024 || height !== 1024) {
    fail(`entry.png is ${width}x${height}, expected 1024x1024`);
  }
  if (png.length < MIN_BYTES || png.length > MAX_BYTES) {
    fail(`entry.png is ${png.length} bytes, outside the ${MIN_BYTES}-${MAX_BYTES} profile`);
  }

  const sha = createHash("sha256").update(png).digest("hex");
  if (sha !== manifest.sha256) fail("entry.png hash does not match image_manifest.json");
  if (png.length !== manifest.bytes) fail("entry.png size does not match image_manifest.json");
  if (manifest.date !== DATE) fail(`manifest date is ${manifest.date}, expected ${DATE}`);
  if (data.date_line !== "Wednesday 25 November 2026") {
    fail(`headlines date_line is ${data.date_line}`);
  }

  const expected = expectedItems(data);
  if (manifest.items_rendered !== expected.length) {
    fail(`manifest claims ${manifest.items_rendered} items, headlines give ${expected.length}`);
  }
  for (const h of manifest.headlines) {
    if (!expected.includes(h)) fail(`manifest headline not in source data: ${h}`);
  }
  for (const h of expected) {
    if (!manifest.headlines.includes(h)) fail(`rendered headline missing from manifest: ${h}`);
  }

  const summary = {
    competition: COMPETITION,
    date: manifest.date,
    file: "entry.png",
    width,
    height,
    bytes: png.length,
    sha256: sha,
    items: expected.length,
    sections: data.sections.map((s: any) => s.name),
    per_section: Object.fromEntries(
      data.sections.map((s: any) => [s.name, Math.min(3, s.stories.length)]),
    ),
    briefs: Math.min(8, data.briefs.length),
    status: "ok",
  };

  // Deliver into the grader's output directory ONLY. The repo mount is
  // read-only; the committed entry.png bytes are copied verbatim so the
  // delivered file is byte-identical to the verified artifact, and a
  // second run overwrites it with the same bytes (deterministic).
  // Refuse an output directory inside the repo itself: that would be a
  // write into the read-only mount under the grader.
  const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? "/output";
  const resolvedOut = resolve(outDir);
  if (resolvedOut === HERE || resolvedOut.startsWith(HERE + "/")) {
    fail(`MAKEFUN_OUTPUT_DIR ${outDir} is inside the repo; refusing to write there`);
  }
  const outPng = join(outDir, "entry.png");
  try {
    mkdirSync(outDir, { recursive: true });
    writeFileSync(outPng, png);
    writeFileSync(join(outDir, "summary.json"), JSON.stringify(summary, null, 1) + "\n");
  } catch (err) {
    fail(`could not write deliverables into ${outDir}: ${(err as Error).message}`);
  }

  // Read the delivered file back and prove it is the verified artifact:
  // a short write or a filesystem quirk must fail loudly here rather
  // than hand the judge a different image than the one just checked.
  const delivered = readFileSync(outPng);
  if (delivered.length !== png.length) {
    fail(`delivered entry.png is ${delivered.length} bytes, expected ${png.length}`);
  }
  const deliveredSha = createHash("sha256").update(delivered).digest("hex");
  if (deliveredSha !== sha) fail("delivered entry.png hash differs from the verified artifact");
  console.log(
    `verified entry.png: ${width}x${height}, ${png.length} bytes, ${expected.length} news items, sha256 ${sha.slice(0, 16)}… → ${outPng} (read-back verified)`,
  );
}

main();
