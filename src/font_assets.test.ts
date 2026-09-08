import { expect, test } from 'bun:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import type { APIRequestContext } from 'playwright';
import { FontAssets } from './font_assets';

test('font provenance is independent of subset download completion order', async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'fontbench-assets-test-'));
  try {
    const original = fs.readFileSync(new URL('./fixtures/fixture-italic.woff', import.meta.url));
    const secondVersion = Buffer.from(original);
    secondVersion.writeUInt16BE(original.readUInt16BE(20) + 1, 20);
    const urls = [original, secondVersion].map(bytes => `data:font/woff;base64,${bytes.toString('base64')}`);
    const request = { get: () => { throw new Error('Unexpected network request'); } } as unknown as APIRequestContext;
    const first = new FontAssets(path.join(directory, 'first'), directory, request);
    const second = new FontAssets(path.join(directory, 'second'), directory, request);
    for (const url of urls) await first.asset(url);
    for (const url of [...urls].reverse()) await second.asset(url);
    const used = [{ postScriptName: 'FixtureSans-Italic' }];
    expect(first.forPlatformFonts(used)).toEqual(second.forPlatformFonts(used));
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
