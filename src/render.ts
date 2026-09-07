import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import {
  TOP_50_FONTS,
  WIDTH_VARIANTS,
  VARIANT_RECIPES,
  STANDARD_PANGRAM,
  WEIGHT_NUMERIC_MAP,
  KERNING_CSS_MAP,
  LINE_HEIGHT_CSS_MAP,
  type FontSpec,
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
}

export const BENCHMARK_PROMPT = `Examine the rendered text in the image. Identify its typographic properties:
1. font: The canonical font family name (e.g., Arial, Times New Roman, Roboto, Georgia, Courier New, Comic Sans MS, etc.)
2. category: Exactly one of [serif, non-serif, mono, handwriting, other]
3. weight: Exactly one of [thin, regular, bold, black]
4. modifier: Exactly one of [regular, italic, underline, strikethrough, small-caps]
5. kerning: Exactly one of [tight, normal, loose]
6. line_height: Exactly one of [tight, normal, loose]

Respond ONLY with a valid JSON object matching this schema:
{
  "font": "<font name>",
  "category": "<serif|non-serif|mono|handwriting|other>",
  "weight": "<thin|regular|bold|black>",
  "modifier": "<regular|italic|underline|strikethrough|small-caps>",
  "kerning": "<tight|normal|loose>",
  "line_height": "<tight|normal|loose>"
}`;

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

export async function renderAllSamples(outputDir: string = 'dataset/rendered'): Promise<RenderedSampleMeta[]> {
  fs.mkdirSync(outputDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ deviceScaleFactor: 2 });
  const manifest: RenderedSampleMeta[] = [];

  const widthMap = new Map(WIDTH_VARIANTS.map(w => [w.id, w.widthPx]));

  console.log(`Starting Chromium rendering for ${TOP_50_FONTS.length} fonts across ${VARIANT_RECIPES.length} variants (${TOP_50_FONTS.length * VARIANT_RECIPES.length} total tasks)...`);

  const tStart = performance.now();

  for (let fIdx = 0; fIdx < TOP_50_FONTS.length; fIdx++) {
    const font = TOP_50_FONTS[fIdx];
    const fallback = getCategoryFallback(font.category);

    const baseHtml = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="${font.cssUrl}">
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
      font-synthesis: weight style;
    }
  </style>
</head>
<body>
  <div class="text-card" id="target">
    ${STANDARD_PANGRAM}
  </div>
</body>
</html>
    `;

    try {
      await page.setContent(baseHtml, { waitUntil: 'load', timeout: 15000 });
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(50);
    } catch (e) {
      console.warn(`Warning loading font ${font.name} (${font.cssUrl}):`, e);
    }

    const cardLocator = page.locator('#target');

    for (const recipe of VARIANT_RECIPES) {
      const vNum = recipe.variantIndex.toString().padStart(2, '0');
      const taskId = `font-${font.id}-v${vNum}`;
      const imageFilename = `${taskId}.png`;
      const imagePath = path.join(outputDir, imageFilename);

      const widthPx = widthMap.get(recipe.widthId) || 320;
      const weightNum = WEIGHT_NUMERIC_MAP[recipe.weight];
      const kerningCss = KERNING_CSS_MAP[recipe.kerning];
      const lineHeightCss = LINE_HEIGHT_CSS_MAP[recipe.lineHeight];

      // Mutate styles in-page for maximum rendering speed
      await page.evaluate(({ widthPx, weightNum, modifier, kerningCss, lineHeightCss }) => {
        const el = document.getElementById('target');
        if (!el) return;
        el.style.width = `${widthPx}px`;
        el.style.fontWeight = `${weightNum}`;
        el.style.fontStyle = modifier === 'italic' ? 'italic' : 'normal';
        el.style.textDecoration = modifier === 'underline' ? 'underline' : modifier === 'strikethrough' ? 'line-through' : 'none';
        el.style.fontVariantCaps = modifier === 'small-caps' ? 'small-caps' : 'normal';
        el.style.fontVariant = modifier === 'small-caps' ? 'small-caps' : 'normal';
        el.style.letterSpacing = kerningCss;
        el.style.lineHeight = `${lineHeightCss}`;
      }, {
        widthPx,
        weightNum,
        modifier: recipe.modifier,
        kerningCss,
        lineHeightCss,
      });

      await cardLocator.screenshot({ path: imagePath });

      manifest.push({
        taskId,
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
      });
    }

    if ((fIdx + 1) % 10 === 0 || fIdx === TOP_50_FONTS.length - 1) {
      console.log(`[${fIdx + 1}/${TOP_50_FONTS.length}] Rendered fonts through ${font.name} (${manifest.length} samples total)...`);
    }
  }

  await browser.close();

  const tEnd = performance.now();
  console.log(`Rendering completed in ${((tEnd - tStart) / 1000).toFixed(1)}s!`);

  const manifestPath = path.join(outputDir, 'manifest.json');
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), 'utf-8');
  console.log(`Manifest saved to ${manifestPath}`);

  return manifest;
}

if (import.meta.main) {
  renderAllSamples().catch(err => {
    console.error('Rendering failed:', err);
    process.exit(1);
  });
}
