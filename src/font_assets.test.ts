import { expect, spyOn, test } from 'bun:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import type { APIRequestContext } from 'playwright';
import { FontAssets } from './font_assets';

test('font cache helper refuses registered output before filesystem mutation', () => {
  const frozen = path.join(import.meta.dir, '../dataset/fontbench-2-rendered');
  const request = { get: () => { throw new Error('Unexpected network request'); } } as unknown as APIRequestContext;
  const mkdir = spyOn(fs, 'mkdirSync').mockImplementation(() => { throw new Error('Filesystem mutation reached'); });
  try {
    expect(() => new FontAssets(frozen, frozen, request)).toThrow(/Frozen release output/);
  } finally {
    mkdir.mockRestore();
  }
});

test('a registered cache stays read-only while new assets and metadata enter candidate output', async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'fontbench-cache-readonly-test-'));
  const frozen = path.join(import.meta.dir, '../dataset/fontbench-2-rendered');
  const frozenLock = fs.readFileSync(path.join(frozen, 'fonts.lock.json'));
  const lock = JSON.parse(frozenLock.toString());
  const fontFiles = fs.readdirSync(path.join(frozen, 'fonts'));
  const request = { get: () => { throw new Error('Unexpected network request'); } } as unknown as APIRequestContext;
  try {
    const assets = new FontAssets(directory, frozen, request);
    const cached = await assets.asset(Object.keys(lock.assets)[0]!);
    const sourceBytes = fs.readFileSync(path.join(frozen, cached.meta.path));
    const fixture = fs.readFileSync(new URL('./fixtures/fixture-italic.woff', import.meta.url));
    const url = `data:font/woff;base64,${fixture.toString('base64')}`;
    const added = await assets.asset(url);
    assets.save();
    expect(fs.readFileSync(path.join(directory, added.meta.path))).toEqual(fixture);
    expect(JSON.parse(fs.readFileSync(path.join(directory, 'fonts.lock.json'), 'utf8')).assets[url]).toBeDefined();
    expect(fs.readFileSync(path.join(frozen, 'fonts.lock.json'))).toEqual(frozenLock);
    expect(fs.readdirSync(path.join(frozen, 'fonts'))).toEqual(fontFiles);
    expect(fs.readFileSync(path.join(frozen, cached.meta.path))).toEqual(sourceBytes);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

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
