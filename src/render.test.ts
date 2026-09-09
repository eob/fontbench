import { afterEach, beforeEach, describe, expect, spyOn, test } from 'bun:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { chromium, type Browser } from 'playwright';
import { TOP_50_FONTS, VARIANT_RECIPES, WIDTH_VARIANTS, type FontSpec, type VariantRecipe } from './fonts';
import { renderAllSamples } from './render';

// An original, minimal WOFF containing rectangle glyphs for the ASCII pangram.
// It keeps browser checks independent of network access and installed system fonts.
const FONT_DATA = 'd09GRgABAAAAAAQAAAoAAAAACuQAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAABPUy8yAAABZAAAAC4AAABgRQBECmNtYXAAAAGkAAAAPwAAAEwBIQENZ2x5ZgAAAlQAAAA1AAAFfA8u4cJoZWFkAAAA9AAAADYAAAA2Ln06aGhoZWEAAAEsAAAAIAAAACQEYgHiaG10eAAAAZQAAAANAAAAcAH0AABsb2NhAAAB5AAAAHAAAABwJlcnw21heHAAAAFMAAAAGAAAACAAOQAGbmFtZQAAAowAAAClAAABMloyVl9wb3N0AAADNAAAAMwAAAF/7iGq6wABAAAAAQAAs4lswF8PPPUAAQPoAAAAAObEe00AAAAA5sR7TQBQAAABkALuAAAAAwACAAAAAAAAeJxjYGRgYFb4b8HAwPiFgYFhC6MDA1AEBTACAFRZA0h4nGNgZGBgMGdgYQDRDAxMDGgAAAapAEB4nGNgZvzCOIGBlYGFgTBgRObYAwGQUmCoYlb4b8HAwKzAcAJNvQIDAwD8IwWPAAB4nGP8wkBXAABqrAD2AAAAeJxjYGBgYmBgYAZiESDJCKZZGCyANBcDB1COiUGBQY8hiqHq/3+gGIjtyJAIZIsycPw/8H8XWAcUAAAAaAooAAAAAA0AGgAnADQAQQBOAFsAaAB1AIIAjwCcAKkAtgDDANAA3QDqAPcBBAERAR4BKwE4AUUBUgFfAWwBeQGGAZMBoAGtAboBxwHUAeEB7gH7AggCFQIiAi8CPAJJAlYCYwJwAn0CigKXAqQCsQKxAr54nGNgZAhgYGCcwPSOgZmBwVhRUDGA0eHfASCXYVRmVGaIyDAeQpEBckdlRmUGuwwAwIslDgAAAHicdYzNCoJAFEaPPxhFtAmipasgyDdo5cIH0F7AZDBBRtARXPUIPXN3agJddBfD+c797gAbnnjY8dh+Xjs+K0lfDjiwdxzOOpHYs2y9cC3myNWxz46b44ALd8fhrBNx4pU1kxl7FRelHnJVj23ZZ502qdLVI54vHVtMXJGMhgnDSI8ipqBEM5BLqsW2km2rE2tIxWoqHtL8d7n0P5ssf3wDZHYyFwAAAHicfY4HbsQwEMTM86X33nPpvXhlnyW9yP//QWY+EAEcSAAJqJk1/5/cNMxombPCKmuss8EmW2yzwy577HPAIUccc8IpZ5xzwSVXXHPDLQvuuOeBR5545oVX3njng0+++OaHXzqCRM/AkpHcTuNSjML3Imo75U6ESKIXg5CX5WV5WV6WV+QVeUVekVfkFXlFXpFX5BV5VV7Vu+pd63yKrvOEJ3l6z+BZekZP9hSPi3ARLsJFuAgX4SJchItwES6Si+Qi6Xu9GMY/LfY3dg==';
const css = `@font-face { font-family: 'Fixture Sans'; font-weight: 400; font-style: normal; src: url(data:font/woff;base64,${FONT_DATA}); }`;
const fixtureFont: FontSpec = {
  id: 'fixture', name: 'Fixture Sans', cssFamily: 'Fixture Sans',
  cssUrl: `data:text/css,${encodeURIComponent(css)}`,
  category: 'non-serif', subCategory: 'fixture', aliases: ['fixture sans'], description: 'Test font',
};
const recipe: VariantRecipe = {
  variantIndex: 1, weight: 'regular', modifier: 'regular', kerning: 'normal', lineHeight: 'normal', widthId: 'narrow',
};

const originalFonts = [...TOP_50_FONTS];
const originalRecipes = [...VARIANT_RECIPES];
const originalWidths = WIDTH_VARIANTS.map(width => ({ ...width }));
const realLaunch = chromium.launch.bind(chromium);
let directory: string;
let browsers: Browser[];
let launchSpy: ReturnType<typeof spyOn>;

function traceFixture(stage: string) {
  if (process.env.CI) console.log(`[render-test] ${stage}`);
}

beforeEach(() => {
  traceFixture('setup begin');
  directory = fs.mkdtempSync(path.join(os.tmpdir(), 'fontbench-render-test-'));
  browsers = [];
  TOP_50_FONTS.splice(0, TOP_50_FONTS.length, fixtureFont);
  VARIANT_RECIPES.splice(0, VARIANT_RECIPES.length, recipe);
  launchSpy = spyOn(chromium, 'launch').mockImplementation(async options => {
    traceFixture('browser launch begin');
    const browser = await realLaunch(options);
    traceFixture('browser launch complete');
    browsers.push(browser);
    return browser;
  });
  traceFixture('setup complete');
});

afterEach(async () => {
  traceFixture('cleanup begin');
  launchSpy.mockRestore();
  for (const browser of browsers) {
    traceFixture('browser close begin');
    await browser.close();
    traceFixture('browser close complete');
  }
  TOP_50_FONTS.splice(0, TOP_50_FONTS.length, ...originalFonts);
  VARIANT_RECIPES.splice(0, VARIANT_RECIPES.length, ...originalRecipes);
  WIDTH_VARIANTS.splice(0, WIDTH_VARIANTS.length, ...originalWidths.map(width => ({ ...width })));
  fs.rmSync(directory, { recursive: true, force: true });
  traceFixture('cleanup complete');
});

// Native await avoids the browser-suite stalls seen with Bun's async rejection matcher.
// See tickets/evidence/publish-01-bun-runtime-gates.md for the executable A/B control.
async function expectRejection(promise: Promise<unknown>, expected: RegExp | string) {
  let rejected = false;
  let rejection: unknown;
  try {
    await promise;
  } catch (error) {
    rejected = true;
    rejection = error;
  }
  expect(rejected).toBe(true);
  expect(() => { throw rejection; }).toThrow(expected);
}

describe('rendered font integrity', () => {
  test('refuses registered release output before filesystem mutation or browser launch', async () => {
    const mkdir = spyOn(fs, 'mkdirSync').mockImplementation(() => { throw new Error('Filesystem mutation reached'); });
    try {
      await expectRejection(renderAllSamples(path.join(import.meta.dir, '../dataset/fontbench-2-rendered')), /Frozen release output/);
      expect(launchSpy).not.toHaveBeenCalled();
    } finally {
      mkdir.mockRestore();
    }
  });

  test('refuses a CSS family alias around an unrelated font binary', async () => {
    TOP_50_FONTS[0] = { ...fixtureFont, name: 'Unrelated Sans', cssFamily: 'Unrelated Sans',
      cssUrl: `data:text/css,${encodeURIComponent(css.replaceAll('Fixture Sans', 'Unrelated Sans'))}` };
    await expectRejection(renderAllSamples(directory), /identity|family/i);
  });

  test('refuses CSS weight declarations that mislabel a static font binary', async () => {
    TOP_50_FONTS[0] = { ...fixtureFont, cssUrl: `data:text/css,${encodeURIComponent(css.replace('font-weight: 400', 'font-weight: 700'))}` };
    VARIANT_RECIPES[0] = { ...recipe, weight: 'bold' };
    await expectRejection(renderAllSamples(directory), /binary.*weight|weight.*binary/i);
  });

  test('records actual multiline geometry and content hashes with pinned assets', async () => {
    const [sample] = await renderAllSamples(directory);
    expect(sample!.layout!.lineCount).toBeGreaterThanOrEqual(2);
    expect(sample!.imageSha256).toMatch(/^[a-f0-9]{64}$/);
    const asset = sample!.fontRendering!.assets![0]!;
    expect(fs.readFileSync(path.join(directory, asset.path))).toEqual(Buffer.from(FONT_DATA, 'base64'));
  });

  test('keeps line height observable even when the full pangram fits the width', async () => {
    WIDTH_VARIANTS.find(width => width.id === 'wide')!.widthPx = 1200;
    VARIANT_RECIPES[0] = { ...recipe, widthId: 'wide' };
    const [sample] = await renderAllSamples(directory);
    expect(sample!.layout!.lineCount).toBe(2);
    expect(sample!.layout!.cardHeightPx).toBeGreaterThan(110);
  });

  test('refuses a missing font instead of labeling a fallback', async () => {
    TOP_50_FONTS[0] = { ...fixtureFont, cssUrl: 'data:text/css,' };
    await expectRejection(renderAllSamples(directory), /font|fallback/i);
    expect(fs.existsSync(path.join(directory, 'manifest.json'))).toBe(false);
  });

  test('refuses broken webfont bytes', async () => {
    TOP_50_FONTS[0] = {
      ...fixtureFont,
      cssUrl: `data:text/css,${encodeURIComponent(css.replace(FONT_DATA, 'aW52YWxpZA=='))}`,
    };
    await expectRejection(renderAllSamples(directory), /font|network/i);
    expect(browsers.every(browser => !browser.isConnected())).toBe(true);
  });

  test('refuses partial glyph fallback even when a webfont loads', async () => {
    const partialCss = css.replace('font-weight: 400;', 'font-weight: 400; unicode-range: U+0041-005A;');
    TOP_50_FONTS[0] = { ...fixtureFont, cssUrl: `data:text/css,${encodeURIComponent(partialCss)}` };
    await expectRejection(renderAllSamples(directory), /fallback/i);
  });

  test('omits unsupported weights and records the face actually used', async () => {
    VARIANT_RECIPES.splice(0, VARIANT_RECIPES.length,
      ...(['thin', 'regular', 'bold', 'black'] as const).map((weight, index) => ({ ...recipe, variantIndex: index + 1, weight })),
    );
    const manifest = await renderAllSamples(directory);
    expect(manifest.map(sample => sample.weight)).toEqual(['regular']);
    expect(manifest[0]).toMatchObject({
      fontRendering: {
        loadedFaces: [{ family: 'Fixture Sans', weight: '400', style: 'normal' }],
        platformFonts: [{ familyName: 'Fixture Sans', postScriptName: 'FixtureSans-Regular', isCustomFont: true }],
        syntheticItalic: false,
      },
    });
    expect(fs.readFileSync(path.join(directory, manifest[0]!.imageFilename)).subarray(0, 8))
      .toEqual(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]));
    expect(browsers.every(browser => !browser.isConnected())).toBe(true);
  });

  test('refuses a CSS italic declaration around a regular font binary', async () => {
    TOP_50_FONTS[0] = { ...fixtureFont, cssUrl: `data:text/css,${encodeURIComponent(css.replace('font-style: normal', 'font-style: italic'))}` };
    VARIANT_RECIPES[0] = { ...recipe, modifier: 'italic' };
    await expectRejection(renderAllSamples(directory), /binary style mismatch/);
  });

  test('records the current native face after styles change between recipes', async () => {
    const italicBytes = fs.readFileSync(new URL('./fixtures/fixture-italic.woff', import.meta.url));
    const server = Bun.serve({ port: 0, fetch: () => new Response(italicBytes, { headers: { 'Content-Type': 'font/woff' } }) });
    try {
      const italicCss = css.replace('font-style: normal', 'font-style: italic').replace(`data:font/woff;base64,${FONT_DATA}`, `http://localhost:${server.port}/italic.woff`);
      TOP_50_FONTS[0] = { ...fixtureFont, cssUrl: `data:text/css,${encodeURIComponent(css + italicCss)}` };
      VARIANT_RECIPES.splice(0, VARIANT_RECIPES.length, ...originalRecipes.filter(recipe => recipe.weight === 'regular'));
      const manifest = await renderAllSamples(directory);
      expect(manifest).toHaveLength(15);
      for (const sample of manifest) {
        expect(sample.fontRendering!.platformFonts[0]!.postScriptName).toBe(sample.modifier === 'italic' ? 'FixtureSans-Italic' : 'FixtureSans-Regular');
      }
      await server.stop(true);
      const frozenManifest = fs.readFileSync(path.join(directory, 'manifest.json'));
      const replayDirectory = path.join(directory, 'replay');
      const replay = await renderAllSamples(replayDirectory, { fontCacheDir: directory });
      expect(replay.map(sample => sample.imageSha256)).toEqual(manifest.map(sample => sample.imageSha256));
      expect(fs.readFileSync(path.join(directory, 'manifest.json'))).toEqual(frozenManifest);
    } finally {
      await server.stop(true);
    }
  }, 15000);

  test('small caps visibly transforms lowercase letters and reports synthesis policy', async () => {
    VARIANT_RECIPES.push({ ...recipe, variantIndex: 2, modifier: 'small-caps' });
    const manifest = await renderAllSamples(directory);
    const regular = fs.readFileSync(path.join(directory, manifest[0]!.imageFilename));
    const smallCaps = fs.readFileSync(path.join(directory, manifest[1]!.imageFilename));
    expect(smallCaps.equals(regular)).toBe(false);
    expect(manifest[1]).toMatchObject({ fontRendering: { smallCapsSynthesisAllowed: true } });
  });

  test('omits a small-caps label when the requested style has no visible effect', async () => {
    TOP_50_FONTS[0] = { ...fixtureFont, cssUrl: `data:text/css,${encodeURIComponent(css + '#target { font-variant-caps: normal !important; }')}` };
    VARIANT_RECIPES.push({ ...recipe, variantIndex: 2, modifier: 'small-caps' });
    const manifest = await renderAllSamples(directory);
    expect(manifest.map(sample => sample.modifier)).toEqual(['regular']);
    expect(JSON.parse(fs.readFileSync(path.join(directory, 'skipped.json'), 'utf8'))[0].reason).toContain('no visible effect');
  });

  test('omits synthetic italic and preserves unrelated files on successful replacement', async () => {
    VARIANT_RECIPES.push({ ...recipe, variantIndex: 2, modifier: 'italic' });
    fs.writeFileSync(path.join(directory, 'notes.txt'), 'keep this');
    fs.writeFileSync(path.join(directory, 'font-fixture-v99.png'), 'obsolete managed image');
    fs.writeFileSync(path.join(directory, 'manifest.json'), 'previous manifest');
    fs.writeFileSync(path.join(directory, 'font-fixture-v01.png'), 'previous image');
    const manifest = await renderAllSamples(directory);
    expect(manifest).toHaveLength(1);
    expect(manifest[0]).toMatchObject({ fontRendering: { syntheticItalic: false } });
    expect(JSON.parse(fs.readFileSync(path.join(directory, 'skipped.json'), 'utf8'))).toMatchObject([{ taskId: 'font-fixture-v02', reason: expect.stringContaining('Unsupported face') }]);
    expect(fs.readFileSync(path.join(directory, 'notes.txt'), 'utf8')).toBe('keep this');
    expect(fs.existsSync(path.join(directory, 'font-fixture-v99.png'))).toBe(false);
    expect(JSON.parse(fs.readFileSync(path.join(directory, 'manifest.json'), 'utf8'))).toEqual(manifest);
  });

  test('reuses pinned font bytes and refuses tampered cache assets', async () => {
    const [sample] = await renderAllSamples(directory);
    const [repeated] = await renderAllSamples(directory);
    expect(repeated!.imageSha256).toBe(sample!.imageSha256);
    const asset = sample!.fontRendering!.assets![0]!;
    fs.writeFileSync(path.join(directory, asset.path), 'corrupt');
    await expectRejection(renderAllSamples(directory), /hash mismatch/);
  }, 15000);

  test('refuses identical images assigned to distinct tasks', async () => {
    VARIANT_RECIPES.push({ ...recipe, variantIndex: 2 });
    await expectRejection(renderAllSamples(directory), /Identical images/);
  });

  test('closes the browser and preserves previous output when a later screenshot fails', async () => {
    VARIANT_RECIPES.push({ ...recipe, variantIndex: 2 });
    const imagePath = path.join(directory, 'font-fixture-v01.png');
    fs.writeFileSync(imagePath, 'previous complete image');
    fs.writeFileSync(path.join(directory, 'manifest.json'), 'previous complete manifest');
    launchSpy.mockImplementation(async (options: Parameters<typeof chromium.launch>[0]) => {
      const browser = await realLaunch(options);
      browsers.push(browser);
      const newPage = browser.newPage.bind(browser);
      spyOn(browser, 'newPage').mockImplementation(async options => {
        const page = await newPage(options);
        const locator = page.locator.bind(page);
        spyOn(page, 'locator').mockImplementation(selector => {
          const target = locator(selector);
          const screenshot = target.screenshot.bind(target);
          let count = 0;
          spyOn(target, 'screenshot').mockImplementation(async options => {
            if (++count === 2) throw new Error('injected screenshot failure');
            return screenshot(options);
          });
          return target;
        });
        return page;
      });
      return browser;
    });
    await expectRejection(renderAllSamples(directory), 'injected screenshot failure');
    expect(browsers.every(browser => !browser.isConnected())).toBe(true);
    expect(fs.readFileSync(imagePath, 'utf8')).toBe('previous complete image');
    expect(fs.readFileSync(path.join(directory, 'manifest.json'), 'utf8')).toBe('previous complete manifest');
  });
});
