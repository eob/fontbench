import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { create, type Font } from 'fontkit';
import type { APIRequestContext } from 'playwright';
import type { FontSpec } from './fonts';

export const sha256 = (bytes: Uint8Array | string): string => createHash('sha256').update(bytes).digest('hex');

export interface FontAsset {
  url: string;
  sha256: string;
  path: string;
  familyName: string;
  typographicFamily: string;
  subfamilyName: string;
  postscriptName: string;
  weight: number;
  weightRange: [number, number];
  italic: boolean;
}

export function inspectFont(bytes: Buffer): Omit<FontAsset, 'url' | 'sha256' | 'path'> {
  const parsed = create(bytes);
  if (!('familyName' in parsed)) throw new Error('Font collections require an explicit face');
  const font = parsed as Font & { getName(name: string): string | null };
  const axis = font.variationAxes.wght;
  const weight = font['OS/2'].usWeightClass;
  return {
    familyName: font.familyName,
    typographicFamily: font.getName('preferredFamily') || font.familyName,
    subfamilyName: font.subfamilyName,
    postscriptName: font.postscriptName,
    weight,
    weightRange: axis ? [axis.min, axis.max] : [weight, weight],
    italic: font['OS/2'].fsSelection.italic || font['OS/2'].fsSelection.oblique || font.italicAngle !== 0,
  };
}

export function verifyFontAsset(asset: FontAsset, font: FontSpec, weight: number, italic: boolean): void {
  const normalize = (name: string) => name.toLowerCase().replace(/[^a-z0-9]/g, '');
  const expected = [font.name, ...(font.binaryFamilyNames ?? [])].map(normalize);
  if (![asset.familyName, asset.typographicFamily].some(name => expected.includes(normalize(name)))) {
    throw new Error(`Font binary family identity mismatch: expected ${font.name}, found ${asset.familyName}/${asset.typographicFamily}`);
  }
  if (weight < asset.weightRange[0] || weight > asset.weightRange[1]) {
    throw new Error(`Font binary weight mismatch for ${font.name}: requested ${weight}, binary supports ${asset.weightRange.join('..')}`);
  }
  if (asset.italic !== italic) {
    throw new Error(`Font binary style mismatch for ${font.name}: requested ${italic ? 'italic' : 'normal'}, binary is ${asset.italic ? 'italic' : 'normal'}`);
  }
}

interface FontLock {
  version: 1;
  stylesheets: Record<string, string>;
  assets: Record<string, { path: string; sha256: string }>;
}

export class FontAssets {
  private lock: FontLock;
  private loaded = new Map<string, { bytes: Buffer; meta: FontAsset }>();

  constructor(private outputDir: string, private cacheDir: string, private request: APIRequestContext) {
    const lockPath = path.join(cacheDir, 'fonts.lock.json');
    this.lock = fs.existsSync(lockPath) ? JSON.parse(fs.readFileSync(lockPath, 'utf8')) : { version: 1, stylesheets: {}, assets: {} };
    if (this.lock.version !== 1) throw new Error('Unsupported font lock version');
    fs.mkdirSync(path.join(outputDir, 'fonts'), { recursive: true });
  }

  async stylesheet(font: FontSpec, userAgent: string): Promise<string> {
    const key = sha256(`${font.cssUrl}\n${font.cssOverride ?? ''}`);
    let css = this.lock.stylesheets[key];
    if (css === undefined) {
      if (font.cssOverride !== undefined) css = font.cssOverride;
      else if (font.cssUrl.startsWith('data:')) css = await (await fetch(font.cssUrl)).text();
      else {
        const response = await this.request.get(font.cssUrl, { timeout: 15000, headers: { 'User-Agent': userAgent } });
        if (!response.ok()) throw new Error(`Font stylesheet failed for ${font.name}: HTTP ${response.status()}`);
        css = await response.text();
      }
      this.lock.stylesheets[key] = css;
    }
    // Force downloads; local() can silently select a different installed face.
    css = css.replace(/local\([^)]*\)\s*,?\s*/gi, '');
    for (const match of css.matchAll(/url\(\s*['"]?([^)'"\s]+)['"]?\s*\)/gi)) {
      const url = match[1]!;
      if (url.startsWith('data:')) await this.asset(url);
    }
    return css;
  }

  async asset(url: string): Promise<{ bytes: Buffer; meta: FontAsset }> {
    const existing = this.loaded.get(url);
    if (existing) return existing;
    const pinned = this.lock.assets[url];
    let bytes: Buffer;
    if (pinned) {
      if (!/^fonts\/[a-f0-9]{64}\.font$/.test(pinned.path)) throw new Error('Invalid pinned font path');
      bytes = fs.readFileSync(path.join(this.cacheDir, pinned.path));
      if (sha256(bytes) !== pinned.sha256) throw new Error(`Pinned font hash mismatch: ${url}`);
    } else if (url.startsWith('data:')) {
      bytes = Buffer.from(await (await fetch(url)).arrayBuffer());
    } else {
      const response = await this.request.get(url, { timeout: 15000 });
      if (!response.ok()) throw new Error(`Font asset failed: HTTP ${response.status()} ${url}`);
      bytes = await response.body();
    }
    const digest = sha256(bytes);
    const relativePath = `fonts/${digest}.font`;
    let info: ReturnType<typeof inspectFont>;
    try { info = inspectFont(bytes); }
    catch (error) { throw new Error(`Invalid font binary ${url}: ${error}`); }
    const meta = { url, sha256: digest, path: relativePath, ...info };
    fs.writeFileSync(path.join(this.outputDir, relativePath), bytes);
    this.lock.assets[url] = { path: relativePath, sha256: digest };
    const loaded = { bytes, meta };
    this.loaded.set(url, loaded);
    return loaded;
  }

  forPlatformFonts(fonts: { postScriptName: string }[]): FontAsset[] {
    return fonts.map(font => {
      const matches = [...this.loaded.values()].filter(asset => asset.meta.postscriptName === font.postScriptName);
      if (!matches.length) throw new Error(`Used font has no retained binary: ${font.postScriptName}`);
      // Unicode subsets may share a PostScript name; retain every loaded subset.
      return matches.map(asset => asset.meta);
    }).flat().filter((asset, index, all) => all.findIndex(other => other.sha256 === asset.sha256) === index);
  }

  save(): void {
    fs.writeFileSync(path.join(this.outputDir, 'fonts.lock.json'), JSON.stringify(this.lock, null, 2));
  }
}
