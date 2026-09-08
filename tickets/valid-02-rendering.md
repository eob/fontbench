# valid-02-rendering: Verify font binaries and visible multiline labels

- **Status**: Completed (local implementation and verification; central delivery handled by valid-01)
- **Branch**: `valid-01-benchmark-audit` (central coordinated branch)
- **Base**: `14e792f`
- **Machine**: shared fontbench workspace
- **Harness**: codex
- **Session ID**: `01a082ae-164d-73f2-a49e-a3d6e48adfaf` (renderer sub-agent) (agent task identity)
- **PR**: central root coordination
- **Assignee**: Edward Benson

## Goal
Make every new sample traceable to verified font binaries and measured, unclipped multiline text. Preserve historical runs as audit evidence.

## Findings

| Finding | Evidence | Resolution |
| --- | --- | --- |
| Single-line inputs make line height unobservable | Frozen September 7 `font-oswald-v05` and `font-oswald-v17` are 640×184 pixels; removing 50 CSS px padding/border leaves 42 px, one 41.8 px loose line height. v05 was visually inspected. | Shared explicit paragraph break after `fox`; measured line count and glyph boxes; reject fewer than two lines or bounds violations. |
| Synthetic italics represent unavailable native designs | 21 of 639 frozen rows explicitly recorded syntheticItalic=true. | Require native italic descriptors and matching binary metadata; disable style synthesis; record unsupported variants in census. |
| CSS descriptors do not establish binary identity or weight | Browser fixture accepted `Unrelated Sans` around Fixture Sans bytes, and CSS 700 around a static 400 font. | Parse retained font bytes, check exact approved family names and actual static weight/variable range; bind CDP PostScript identities to those bytes. |
| Font provenance may report the previous style | Arial requested native italic and FontFace load returned italic, but CDP still reported ArialMT before layout. A local 15-recipe control accepted only 13 rows without a layout flush. | Measure layout before querying CDP glyph runs. Controlled local native-face tests pass all 15 and replay exact pixels with the server stopped. |
| Weight evidence conflicts for two ExtraLight sources | Current Poppins and Fira Sans stylesheets/catalogs call ExtraLight 200, while their static OpenType OS/2 tables say 275. Corresponding labels affect five frozen rows per family, but historical bytes were not retained. | Conservatively exclude all 30 protocol 2 candidates with this disagreement; record explicit reasons. This is a metadata convention disagreement, not proof of incorrect outlines. |
| Names on variable binaries may describe default instances | Montserrat variable bytes report both legacy/preferred family `Montserrat Thin` with wght 100..900; several other families use Light, ExtraLight, or optical-size base names. | Exact reviewed `binaryFamilyNames` allowlists; no generic suffix stripping or broad alias matching. |
| All-caps design concerns need controlled evidence | Cinzel, Bebas Neue, and Bungee small-caps screenshots differ from matched normal controls. | Retain these families; compare every small-caps render to a same-style normal control and omit no-op modifiers. |
| Source URLs do not freeze artifacts | Historical manifests retained live URLs, but no font binary bytes, stylesheet locks, or image hashes. | Retain font bytes by SHA-256, stylesheet/source lock, image hashes, actual face metadata, browser version, catalog, and skip census. |
| Rerendering retained obsolete managed PNGs | Replacing output kept `font-fixture-v99.png`, despite its absence from the new manifest. | Remove previous managed PNGs during atomic replacement while preserving unrelated files and complete old output on failure. |
| Broad grading aliases collapse different families | Catalog included Helvetica Neue for Helvetica, Garamond for EB Garamond, Times for Times New Roman, Baskerville for Libre Baskerville, and similar shortened family names. | Restrict aliases to canonical spelling variants and documented same-family alternatives; evaluator regression owned by valid-03. |

The fresh candidate contains 1824 accepted images across all 50 families, plus 1176 documented exclusions from 3000 candidates. Every accepted image has 2–5 measured lines; all 1824 decoded images are distinct. The independent validator passed 129 distinct font binaries. Tracking, line-height, and width levels each have exactly 608 samples per level. Recipe design and shortcut analysis are tracked in valid-05.

## Plan and changes

- [x] Identify historical single-line images and inspect actual rendering mechanism.
- [x] Capture red browser checks for false family/weight declarations and absent measurement evidence.
- [x] Retain and hash font sources; validate OpenType family, weight range, and italic metadata against requested labels and CDP evidence.
- [x] Guarantee a shared paragraph break and measure line boxes after loading; refuse clipping and no-op small-caps.
- [x] Account for every candidate in manifest or skipped census; detect image collisions.
- [x] Share the exact prompt in `baseline/prompt.txt`, including the numeric label rubric.
- [x] Preserve old data by defaulting new rendering to `dataset/fontbench-2-rendered`.
- [x] Run browser tests, base reversion, typecheck, simplify/comment audit.
- [x] Complete full blocked-network replay against the retained candidate.

## Verbatim red evidence

Full causal traces are retained in [base renderer reversion](evidence/valid-02-render-base-red.txt), [native layout reversion](evidence/valid-02-native-layout-red.txt), and [obsolete managed image](evidence/valid-02-stale-images-red.txt).

```text
Expected promise that rejects
Received promise that resolved: Promise { <resolved> }
(fail) rendered font integrity > refuses a CSS family alias around an unrelated font binary
(fail) rendered font integrity > refuses CSS weight declarations that mislabel a static font binary
TypeError: undefined is not an object (evaluating 'sample.layout.lineCount')
0 pass; 3 fail
```

A fresh isolated copy of the exact `14e792f` renderer/fonts with the new tests reproduced all three failures; restoring the implementation passes them. The native-layout reversion kept all binary checks and removed only the layout flush:

```text
Expected length: 15
Received length: 13
(fail) rendered font integrity > records the current native face after styles change between recipes
```

The initial live Arial reproduction was:

```text
font-arial-v19: Error: Font binary style mismatch for Arial: requested italic, binary is normal;
loaded=[{"family":"Arial","weight":"400","style":"italic"}];
used=[{"familyName":"Arial","postScriptName":"ArialMT","isCustomFont":true,"glyphCount":41}]
```

An additional retained-source Arial control produced 33 samples without the flush and the expected 42 after restoring it.

## Validation gate matrix

| Gate / command | Base commit | Result |
| --- | --- | --- |
| New family/weight/geometry checks against isolated original renderer | `14e792f` | Expected red:0 pass/3 fail; same causal refusal/absence failures |
| `bun test src/render.test.ts` | `14e792f` |16 passed,0 failed,51 assertions;12.24 s |
| `bun test src` | `14e792f` |51 passed,0 failed,218 assertions;12.71 s |
| `bun run typecheck` | `14e792f` | Passed |
| Render 50 fonts×60 recipes into temporary candidate | `14e792f` |1824 accepted,1176 skipped,174.8 s; no missing families |
| `python -m baseline.validate_dataset --manifest /tmp/fontbench-render-validation/manifest.json` | `14e792f` | valid=true;1824 unique pixels;129 verified font assets;0 errors |
| Native fixture source server stopped, pinned replay | `14e792f` | All 15 hashes equal; no source server available |
| Full browser-offline/API-request-disabled replay | `14e792f` | All 1824 PNG hashes, layouts/labels, and 1176 skips equal; metadata values equal after canonical asset ordering |
| `git diff --check` over owned files | `14e792f` | Clean |

One new cache test exceeded Bun's default 5 s budget while two browser suites overlapped; its isolated rerun passed in 1.6 s. The two tests that launch multiple browsers now explicitly allow 15 s. No production logic was changed to address that test scheduling issue.

## Offline replay and metadata ordering

The full replay disabled the browser context network and replaced `APIRequestContext.get` with an exception. All 1824 image hashes, layouts, labels, font metadata values, and 1176 skip records matched the retained candidate. The initial strict JSON comparison found 15 rows where two identical asset records appeared in opposite order: concurrent Lora/Bodoni Moda subset downloads completed in a different order. No pixels or metadata values changed.

The renderer now sorts font assets by SHA-256. A deterministic regression loads the same two valid font containers in opposite orders: it failed before sorting and passes afterward. The candidate arrays are canonicalized during central integration without changing image bytes. See [replay evidence](evidence/valid-02-offline-replay.txt) and [ordering red evidence](evidence/valid-02-assets-order-red.txt).

## Decisions and durable findings

1. Font identity uses exact canonical or approved binary family names. Variable font base names and OS/2 default weights do not describe every instance; `wght` range establishes supported variable weights.
2. Browser FontFace descriptors and `isCustomFont` alone cannot establish binary identity, glyph provenance, or native weight/style. Measure layout, query actual glyph runs, and cross-check retained bytes; the independent gate reparses them with FontTools.
3. Native italics are required. CSS small-caps synthesis remains an explicit supported rendering operation, and every small-caps case must differ from its normal control.
4. The shared text has one intentional break after `fox`; additional width-driven wrapping remains. Line height therefore has at least one observable baseline interval for every font.
5. `renderAllSamples(outputDir, { fontCacheDir })` reuses the pinned stylesheet and font bytes from a previous output. With no option, the destination is its own cache. Corrupt cached bytes fail before replacement. Browser version is recorded; exact pixel replay assumes the same browser/environment.
6. Manifests retain optional new fields at the TypeScript type level so historical data remains readable. Protocol 2 validation requires complete new evidence before evaluation or packaging.
7. Keep historical results unchanged. Current source inspection cannot establish the exact bytes downloaded during a historical run when that run did not retain its fonts.
8. Provider category taxonomy and relative numeric weights remain benchmark definitions, rather than universal perceptual truths; the shared prompt states the numeric label rubric.

## Sources (inspected 2026-09-08)

Fontkit supports WOFF2 parsing and exposes family names/variation axes ([upstream API](https://github.com/foliojs/fontkit)). Binary weight evidence comes from [OpenType OS/2](https://learn.microsoft.com/en-us/typography/opentype/spec/os 2) and variable ranges from [fvar](https://learn.microsoft.com/en-us/typography/opentype/spec/fvar). Google catalogs call ExtraLight 200 for both [Poppins](https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/METADATA.pb) and [Fira Sans](https://raw.githubusercontent.com/google/fonts/main/ofl/firasans/METADATA.pb), which is why their 275 binary values are documented as a disagreement rather than a conclusive outline defect.
