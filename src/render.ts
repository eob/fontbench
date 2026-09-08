import { chromium, type Browser } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { FontAssets, verifyFontAsset, sha256, type FontAsset } from './font_assets';
import {
  TOP_50_FONTS,
  WIDTH_VARIANTS,
  VARIANT_RECIPES,
  STANDARD_PANGRAM,
  WEIGHT_NUMERIC_MAP,
  KERNING_CSS_MAP,
  LINE_HEIGHT_CSS_MAP,
  type TypographicCategory,
  type TypographicWeight,
  type TypographicModifier,
  type TypographicKerning,
  type TypographicLineHeight,
  type ContainerWidthId
} from './fonts';

export interface RenderedSampleMeta {
  taskId: string;
  fontId: string;
  fontName: string;
  category: TypographicCategory;
  subCategory?: string;
  aliases: string[];
  weight: TypographicWeight;
  weightNumeric: number;
  modifier: TypographicModifier;
  kerning: TypographicKerning;
  lineHeight: TypographicLineHeight;
  widthId: ContainerWidthId;
  widthPx: number;
  imageFilename: string;
  imagePath: string;
  pangram: string;
  prompt: string;
  imageSha256?: string;
  layout?: {
    lineCount: number;
    lineBoxes: { x: number; y: number; width: number; height: number }[];
    contentWidthPx: number;
    cardWidthPx: number;
    cardHeightPx: number;
    fontSizePx: number;
    lineHeightPx: number;
    letterSpacingPx: number;
    deviceScaleFactor: number;
  };
  fontRendering?: {
    browserVersion: string;
    assets?: FontAsset[];
    cssUrl: string;
    cssOverride?: string;
    loadedFaces: { family: string; weight: string; style: string }[];
    platformFonts: { familyName: string; postScriptName: string; isCustomFont: boolean; glyphCount: number }[];
    syntheticItalic: boolean;
    smallCapsSynthesisAllowed: boolean;
  };
}

export const BENCHMARK_PROMPT = fs.readFileSync(new URL('../baseline/prompt.txt', import.meta.url), 'utf8').trim();

function getCategoryFallback(cat: TypographicCategory): string {
  switch (cat) {
    case 'serif': return 'serif';
    case 'mono': return 'monospace';
    case 'handwriting': return 'cursive';
    case 'other': return 'fantasy, sans-serif';
    case 'non-serif':
    default: return 'sans-serif';
  }
}

export async function renderAllSamples(outputDir: string = 'dataset/fontbench-2-rendered', options: { fontCacheDir?: string } = {}): Promise<RenderedSampleMeta[]> {
  const destination = path.resolve(outputDir);
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  const stagingDir = fs.mkdtempSync(path.join(path.dirname(destination), `.${path.basename(destination)}-render-`));
  let browser: Browser | undefined;
  try {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ deviceScaleFactor: 2 });
    const session = await page.context().newCDPSession(page);
    await session.send('DOM.enable');
    await session.send('CSS.enable');
    const userAgent = await page.evaluate(() => navigator.userAgent);
    const manifest: RenderedSampleMeta[] = [];
    const skipped: { taskId: string; fontId: string; reason: string }[] = [];
    const fontAssets = new FontAssets(stagingDir, options.fontCacheDir ?? destination, page.request);
    let assetError: unknown;
    await page.route('**/*', async route => {
      if (route.request().resourceType() !== 'font') return route.continue();
      try {
        const asset = await fontAssets.asset(route.request().url());
        await route.fulfill({ body: asset.bytes, contentType: 'font/woff2', headers: { 'Access-Control-Allow-Origin': '*' } });
      } catch (error) {
        assetError = error;
        await route.abort();
      }
    });
    const imageHashes = new Map<string, string>();

    const widthMap = new Map(WIDTH_VARIANTS.map(w => [w.id, w.widthPx]));

    console.log(`Starting Chromium rendering for ${TOP_50_FONTS.length} fonts across ${VARIANT_RECIPES.length} variants (${TOP_50_FONTS.length * VARIANT_RECIPES.length} total tasks)...`);

    const tStart = performance.now();

    for (const [fIdx, font] of TOP_50_FONTS.entries()) {
      const fallback = getCategoryFallback(font.category);
      const stylesheet = await fontAssets.stylesheet(font, userAgent);
      const baseHtml = `
  <!DOCTYPE html>
  <html>
  <head>
    <meta charset="utf-8">
    <style>${stylesheet}</style>
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body {
        background-color: #f3f4f6;
        display: inline-block;
        padding: 40px;
      }
      .text-card {
        font-family: '${font.cssFamily}', ${fallback};
        font-size: 22px;
        color: #111827;
        background-color: #ffffff;
        padding: 24px;
        border-radius: 8px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        text-rendering: optimizeLegibility;
        -webkit-font-smoothing: antialiased;
        word-break: normal;
        overflow-wrap: break-word;
        font-synthesis: small-caps;
        white-space: pre-line;
      }
    </style>
  </head>
  <body>
    <div class="text-card" id="target">${STANDARD_PANGRAM}</div>
  </body>
  </html>
      `;

      await page.setContent(baseHtml, { waitUntil: 'load', timeout: 15000 });

      const cardLocator = page.locator('#target');

      for (const recipe of VARIANT_RECIPES) {
        const vNum = recipe.variantIndex.toString().padStart(2, '0');
        const taskId = `font-${font.id}-v${vNum}`;
        const imageFilename = `${taskId}.png`;
        const imagePath = path.join(outputDir, imageFilename);

        const widthPx = widthMap.get(recipe.widthId);
        if (widthPx === undefined) throw new Error(`Unknown render width: ${recipe.widthId}`);
        const weightNum = WEIGHT_NUMERIC_MAP[recipe.weight];
        const kerningCss = KERNING_CSS_MAP[recipe.kerning];
        const lineHeightCss = LINE_HEIGHT_CSS_MAP[recipe.lineHeight];

        // Mutate styles in-page for maximum rendering speed
        await page.evaluate(({ widthPx, weightNum, modifier, kerningCss, lineHeightCss }) => {
          const el = document.getElementById('target');
          if (!el) throw new Error('Missing text card');
          el.style.width = `${widthPx}px`;
          el.style.fontWeight = `${weightNum}`;
          el.style.fontStyle = modifier === 'italic' ? 'italic' : 'normal';
          el.style.textDecoration = modifier === 'underline' ? 'underline' : modifier === 'strikethrough' ? 'line-through' : 'none';
          el.style.fontVariantCaps = modifier === 'small-caps' ? 'small-caps' : 'normal';
          el.style.letterSpacing = kerningCss;
          el.style.lineHeight = `${lineHeightCss}`;
        }, {
          widthPx,
          weightNum,
          modifier: recipe.modifier,
          kerningCss,
          lineHeightCss,
        });

        const loadedFaces = await page.evaluate(async ({ family, weight, modifier, text }) => {
          const style = modifier === 'italic' ? 'italic' : 'normal';
          let timer: ReturnType<typeof setTimeout> | undefined;
          try {
            const faces = await Promise.race([
              document.fonts.load(`${style} ${weight} 22px "${family}"`, text),
              new Promise<never>((_, reject) => {
                timer = setTimeout(() => reject(new Error(`Font loading timed out: ${family}`)), 15000);
              }),
            ]);
            if (!faces.length || faces.some(face => face.status !== 'loaded')) {
              throw new Error(`Font unavailable: ${family}; refusing fallback rendering`);
            }
            return faces.map(face => ({ family: face.family.replace(/^['"]|['"]$/g, ''), weight: face.weight, style: face.style }));
          } finally {
            clearTimeout(timer);
          }
        }, { family: font.cssFamily, weight: weightNum, modifier: recipe.modifier, text: STANDARD_PANGRAM });

        if (assetError) throw assetError;

        // CSS otherwise silently picks the nearest weight or uses italic for upright text.
        const supported = loadedFaces.every(face => {
          const weights = face.weight.split(/\s+/).map(Number);
          const min = weights[0]!;
          const max = weights[1] ?? min;
          return weightNum >= min && weightNum <= max && face.style === (recipe.modifier === 'italic' ? 'italic' : 'normal');
        });
        if (!supported) {
          const reason = `Unsupported face: requested ${weightNum}/${recipe.modifier}, available ${loadedFaces.map(face => `${face.weight}/${face.style}`).join(', ')}`;
          skipped.push({ taskId, fontId: font.id, reason });
          continue;
        }

        await cardLocator.evaluate(el => el.getBoundingClientRect().height);
        const { root } = await session.send('DOM.getDocument');
        const { nodeId } = await session.send('DOM.querySelector', { nodeId: root.nodeId, selector: '#target' });
        const { fonts: platformFonts } = await session.send('CSS.getPlatformFontsForNode', { nodeId });
        if (!platformFonts.length || platformFonts.some(face => !face.isCustomFont)) {
          throw new Error(`Font fallback detected for ${taskId}: ${platformFonts.map(face => face.familyName).join(', ')}`);
        }
        const assets = fontAssets.forPlatformFonts(platformFonts);
        try {
          for (const asset of assets) verifyFontAsset(asset, font, weightNum, recipe.modifier === 'italic');
        } catch (error) {
          if (!(error instanceof Error) || !/Font binary (weight|style) mismatch/.test(error.message)) throw error;
          skipped.push({ taskId, fontId: font.id, reason: error.message });
          continue;
        }
        const layout = await page.evaluate(() => {
          const el = document.getElementById('target')!;
          const bounds = el.getBoundingClientRect();
          const style = getComputedStyle(el);
          const range = document.createRange();
          range.selectNodeContents(el);
          const lineBoxes = [...range.getClientRects()].filter(rect => rect.width > 0).map(rect => ({
            x: rect.x - bounds.x, y: rect.y - bounds.y, width: rect.width, height: rect.height,
          }));
          const lineCount = new Set(lineBoxes.map(rect => Math.round(rect.y * 100) / 100)).size;
          if (lineCount < 2) throw new Error('Multiline text required to observe line height');
          if (lineBoxes.some(rect => rect.x < 0 || rect.y < 0 || rect.x + rect.width > bounds.width || rect.y + rect.height > bounds.height)) {
            throw new Error('Rendered text extends beyond image bounds');
          }
          return { lineCount, lineBoxes, contentWidthPx: el.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight),
            cardWidthPx: bounds.width, cardHeightPx: bounds.height, fontSizePx: parseFloat(style.fontSize),
            lineHeightPx: parseFloat(style.lineHeight), letterSpacingPx: parseFloat(style.letterSpacing) || 0, deviceScaleFactor: devicePixelRatio };
        });
        const image = await cardLocator.screenshot();
        if (recipe.modifier === 'small-caps') {
          await cardLocator.evaluate(el => { (el as HTMLElement).style.fontVariantCaps = 'normal'; });
          const control = await cardLocator.screenshot();
          await cardLocator.evaluate(el => { (el as HTMLElement).style.fontVariantCaps = 'small-caps'; });
          if (image.equals(control)) {
            skipped.push({ taskId, fontId: font.id, reason: 'Small-caps has no visible effect in controlled screenshot' });
            continue;
          }
        }
        const imageSha256 = sha256(image);
        const duplicate = imageHashes.get(imageSha256);
        if (duplicate) throw new Error(`Identical images for distinct tasks: ${duplicate} and ${taskId}`);
        imageHashes.set(imageSha256, taskId);
        fs.writeFileSync(path.join(stagingDir, imageFilename), image);

        manifest.push({
          taskId,
          imageSha256,
          layout,
          fontId: font.id,
          fontName: font.name,
          category: font.category,
          subCategory: font.subCategory,
          aliases: font.aliases,
          weight: recipe.weight,
          weightNumeric: weightNum,
          modifier: recipe.modifier,
          kerning: recipe.kerning,
          lineHeight: recipe.lineHeight,
          widthId: recipe.widthId,
          widthPx,
          imageFilename,
          imagePath,
          pangram: STANDARD_PANGRAM,
          prompt: BENCHMARK_PROMPT,
          fontRendering: {
            browserVersion: browser.version(),
            assets,
            cssUrl: font.cssUrl,
            ...(font.cssOverride ? { cssOverride: font.cssOverride } : {}),
            loadedFaces,
            platformFonts,
            syntheticItalic: false,
            smallCapsSynthesisAllowed: recipe.modifier === 'small-caps',
          },
        });
      }

      if ((fIdx + 1) % 10 === 0 || fIdx === TOP_50_FONTS.length - 1) {
        console.log(`[${fIdx + 1}/${TOP_50_FONTS.length}] Rendered fonts through ${font.name} (${manifest.length} samples total)...`);
      }
    }

    if (!manifest.length) throw new Error(`No supported font variants were rendered: ${skipped[0]?.reason ?? 'empty catalog'}`);

    const tEnd = performance.now();
    console.log(`Rendering completed in ${((tEnd - tStart) / 1000).toFixed(1)}s!`);
    fs.writeFileSync(path.join(stagingDir, 'manifest.json'), JSON.stringify(manifest, null, 2), 'utf-8');
    fs.writeFileSync(path.join(stagingDir, 'skipped.json'), JSON.stringify(skipped, null, 2));
    fs.writeFileSync(path.join(stagingDir, 'catalog.json'), JSON.stringify({
      protocolVersion: 2, fonts: TOP_50_FONTS, recipes: VARIANT_RECIPES, pangram: STANDARD_PANGRAM,
      widths: WIDTH_VARIANTS, weights: WEIGHT_NUMERIC_MAP, kerning: KERNING_CSS_MAP, lineHeights: LINE_HEIGHT_CSS_MAP,
      prompt: BENCHMARK_PROMPT, browserVersion: browser.version(),
    }, null, 2));
    fontAssets.save();

    // Keep previous output intact until every image and the manifest are complete.
    // Preserve unrelated files when replacing an existing rendered directory.
    const backupDir = `${stagingDir}.previous`;
    if (fs.existsSync(destination)) {
      fs.cpSync(destination, stagingDir, {
        recursive: true, force: false,
        filter: source => source === destination || !/^font-.+-v\d+\.png$/.test(path.basename(source)),
      });
      fs.renameSync(destination, backupDir);
    }
    try {
      fs.renameSync(stagingDir, destination);
    } catch (error) {
      if (fs.existsSync(backupDir)) fs.renameSync(backupDir, destination);
      throw error;
    }
    fs.rmSync(backupDir, { recursive: true, force: true });
    console.log(`Manifest saved to ${path.join(outputDir, 'manifest.json')}`);
    return manifest;
  } finally {
    try {
      await browser?.close();
    } finally {
      fs.rmSync(stagingDir, { recursive: true, force: true });
    }
  }
}

if (import.meta.main) {
  renderAllSamples().catch(err => {
    console.error('Rendering failed:', err);
    process.exit(1);
  });
}
