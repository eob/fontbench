# valid-02-rendering: Prove font identity and visible multiline labels

- **Status**: In Progress
- **Branch**: `valid-01-benchmark-audit` (central coordinated branch)
- **Base**: `14e792f`
- **Machine**: shared fontbench workspace
- **Harness**: codex
- **Session ID**: `/root/render_validity`
- **PR**: root coordination
- **Assignee**: Edward Benson

## Goal
Make every newly rendered sample traceable to verified font binaries and measured, unclipped multiline text. Preserve historical runs as audit evidence.

## Evidence and causal mechanism
The frozen September 7 manifest has 639 images. Two are single-line: `font-oswald-v05` and `font-oswald-v17`, both 640×184 pixels. Subtracting 50 CSS px for padding/border leaves 42px, one 41.8px loose line-height. The v05 image was visually inspected and contains the entire pangram on one line. Existing code trusts the intended container widths and records no line geometry. Frozen rows also contain 25 synthesized italics; such faces were not downloaded native italic designs.

Existing checks require `isCustomFont` but do not compare the font binary's family or weight to requested labels. A provider can declare arbitrary CSS names/weights around unrelated regular-weight bytes, and the renderer accepts them. Live CDN bytes were never retained or hashed, so the historical provider URLs cannot establish which exact bytes were used.

## Plan
- [x] Identify historical single-line images and inspect rendering mechanism.
- [ ] Capture red browser tests for misnamed/misweighted binary and absent measured evidence.
- [ ] Pin downloaded font assets; inspect OpenType family, weight range, and italic metadata against requested labels and CDP evidence.
- [ ] Guarantee a shared paragraph break and measure line boxes after loading; refuse clipping and no-op small-caps.
- [ ] Account for every candidate in manifest or skipped census; detect image collisions.
- [ ] Run local browser tests, reversion check, typecheck, simplify/comment audit.

## Decisions and durable findings
Variable font base names may include Thin/Light/optical sizes even when Chromium selects a bold instance. Use the font's declared `wght` axis range instead of rejecting its base name suffix or OS/2 default weight. CSS FontFace weight descriptors alone cannot establish binary weights. Fontkit supports WOFF2 metadata ([upstream API](https://github.com/foliojs/fontkit)); binary weight metadata comes from [OpenType OS/2](https://learn.microsoft.com/en-us/typography/opentype/spec/os2) and variable ranges from [fvar](https://learn.microsoft.com/en-us/typography/opentype/spec/fvar).

## Validation gate matrix
Pending implementation; all gates based on `14e792f`.

## Verbatim red evidence
```text
bun test v1.3.14 (0d9b296a)

src/render.test.ts:
Starting Chromium rendering for 1 fonts across 1 variants (1 total tasks)...
[1/1] Rendered fonts through Unrelated Sans (1 samples total)...
Rendering completed in 0.2s!
Manifest saved to /tmp/fontbench-render-test-8JxkWs/manifest.json
48 | 
49 | describe('rendered font integrity', () => {
50 |   test('refuses a CSS family alias around an unrelated font binary', async () => {
51 |     TOP_50_FONTS[0] = { ...fixtureFont, name: 'Unrelated Sans', cssFamily: 'Unrelated Sans',
52 |       cssUrl: `data:text/css,${encodeURIComponent(css.replaceAll('Fixture Sans', 'Unrelated Sans'))}` };
53 |     await expect(renderAllSamples(directory)).rejects.toThrow(/identity|family/i);
                                                           ^
error: 

Expected promise that rejects
Received promise that resolved: Promise { <resolved> }

      at <anonymous> (/mnt/disks/data/fontbench/src/render.test.ts:53:55)
(fail) rendered font integrity > refuses a CSS family alias around an unrelated font binary [600.33ms]
Starting Chromium rendering for 1 fonts across 1 variants (1 total tasks)...
[1/1] Rendered fonts through Fixture Sans (1 samples total)...
Rendering completed in 0.6s!
Manifest saved to /tmp/fontbench-render-test-OYCTVB/manifest.json
54 |   });
55 | 
56 |   test('refuses CSS weight declarations that mislabel a static font binary', async () => {
57 |     TOP_50_FONTS[0] = { ...fixtureFont, cssUrl: `data:text/css,${encodeURIComponent(css.replace('font-weight: 400', 'font-weight: 700'))}` };
58 |     VARIANT_RECIPES[0] = { ...recipe, weight: 'bold' };
59 |     await expect(renderAllSamples(directory)).rejects.toThrow(/binary.*weight|weight.*binary/i);
                                                           ^
error: 

Expected promise that rejects
Received promise that resolved: Promise { <resolved> }

      at <anonymous> (/mnt/disks/data/fontbench/src/render.test.ts:59:55)
(fail) rendered font integrity > refuses CSS weight declarations that mislabel a static font binary [1617.59ms]
Starting Chromium rendering for 1 fonts across 1 variants (1 total tasks)...
[1/1] Rendered fonts through Fixture Sans (1 samples total)...
Rendering completed in 0.1s!
Manifest saved to /tmp/fontbench-render-test-NsmQPj/manifest.json
59 |     await expect(renderAllSamples(directory)).rejects.toThrow(/binary.*weight|weight.*binary/i);
60 |   });
61 | 
62 |   test('records actual multiline geometry and content hashes with pinned assets', async () => {
63 |     const [sample] = await renderAllSamples(directory);
64 |     expect(sample).toMatchObject({ layout: { lineCount: expect.any(Number) }, imageSha256: expect.stringMatching(/^[a-f0-9]{64}$/) });
                        ^
error: expect(received).toMatchObject(expected)

  {
-   "imageSha256": StringMatching /^[a-f0-9]{64}$/,
-   "layout": {
-     "lineCount": Any<Number>,
+   "al
0 pass; 3 fail (family alias accepted, false weight accepted, measured evidence absent).
```
