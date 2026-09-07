import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { PILOT_FONTS, WIDTH_VARIANTS, STANDARD_PANGRAM, type FontSpec, type RenderWidth } from './fonts';

export interface RenderedSampleMeta {
  taskId: string;
  fontId: string;
  fontName: string;
  category: string;
  subCategory?: string;
  aliases: string[];
  widthId: 'narrow' | 'medium' | 'wide';
  widthPx: number;
  imageFilename: string;
  imagePath: string;
  pangram: string;
  prompt: string;
}

export async function renderAllSamples(outputDir: string = 'dataset/rendered'): Promise<RenderedSampleMeta[]> {
  fs.mkdirSync(outputDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ deviceScaleFactor: 2 });
  const manifest: RenderedSampleMeta[] = [];

  console.log(`Starting Chromium rendering for ${PILOT_FONTS.length} fonts across ${WIDTH_VARIANTS.length} widths...`);

  for (const font of PILOT_FONTS) {
    for (const width of WIDTH_VARIANTS) {
      const taskId = `font-${font.id}-${width.id}`;
      const imageFilename = `${taskId}.png`;
      const imagePath = path.join(outputDir, imageFilename);

      const html = `
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
      width: ${width.widthPx}px;
      font-family: '${font.cssFamily}', ${font.category === 'serif' ? 'serif' : font.category === 'monospace' ? 'monospace' : font.category === 'handwriting' ? 'cursive' : 'sans-serif'};
      font-size: 22px;
      line-height: 1.45;
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

      await page.setContent(html);
      await page.evaluate(() => document.fonts.ready);

      // Brief sleep to ensure glyph rasterization
      await page.waitForTimeout(100);

      const el = page.locator('#target');
      await el.screenshot({ path: imagePath });

      manifest.push({
        taskId,
        fontId: font.id,
        fontName: font.name,
        category: font.category,
        subCategory: font.subCategory,
        aliases: font.aliases,
        widthId: width.id,
        widthPx: width.widthPx,
        imageFilename,
        imagePath,
        pangram: STANDARD_PANGRAM,
        prompt: 'Examine the rendered text in the provided image. Identify the primary font family used to typeset this text. Output only the canonical font name (e.g., Arial, Times New Roman, Roboto).'
      });

      console.log(`✓ Rendered: ${font.name} (${width.id} - ${width.widthPx}px) -> ${imageFilename}`);
    }
  }

  await browser.close();

  const manifestPath = path.join(outputDir, 'manifest.json');
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), 'utf-8');
  console.log(`\n🎉 Rendering complete! Generated ${manifest.length} samples. Manifest saved to ${manifestPath}`);

  return manifest;
}

if (import.meta.main) {
  renderAllSamples().catch(err => {
    console.error('Rendering failed:', err);
    process.exit(1);
  });
}
