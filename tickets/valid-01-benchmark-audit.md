# valid-01-benchmark-audit: Validate FontBench before final runs

- **Status**: Completed (local implementation, artifacts, and validation)
- **Branch**: `valid-01-benchmark-audit`
- **Base**: `14e792f`
- **Machine**: `eob-dev2`
- **Harness**: codex
- **Session ID**: `01a082ae-164d-73f2-a49e-a3d6e48adfaf`
- **Assignee**: Edward Benson
- **Delivery**: Local repository review and fixes; tickets are the central coordination record.

## Goal

Audit generated pixels, font identity, label observability, packaging, grading, run provenance, and reporting. Repair proven defects and prepare a reproducibly validated dataset before any final paid evaluation.

## Plan and ownership

1. Establish the baseline test result and inventory both historical and September 7 inputs.
2. Audit renderer/font sources, evaluator/runner, and packaging/reporting independently; record findings in numbered `valid-*` tickets with reproducible evidence before fixes.
3. Repair each confirmed issue with regression checks, including inverse/boundary cases and isolated base-code controls where practical.
4. Regenerate candidate inputs separately, validate every sample, inspect representative images, and package the accepted dataset.
5. Run combined checks, offline evaluation, and a simplification review; record a gate matrix and explicit remaining limitations.

## Initial evidence

The README marks the 1,000 packaged images as historical and unsuitable for new comparisons. A separate 639-sample September 7 input set is described as corrected, but the renderer does not measure line count or assert at least two lines before assigning a line-height label. Existing font verification asserts custom-font usage without verifying internal family identity.

## Decisions and durable findings

- Preserve existing paid-run inputs and checkpoints as historical evidence. Use a new dataset fingerprint and run ID after any image, label, or prompt correction.
- Final paid model runs are a subsequent activity; this audit uses offline tests and font-provider downloads.
- Individual audit tickets track defects and evidence; this ticket tracks integration and readiness.

## Handoff & Takeover Log

- 2026-09-08: Started audit from clean `main` at `14e792f`.

## Findings and repaired behavior

| Area | Original evidence | Accepted correction |
| --- | --- | --- |
| Pixel/label validity | Both old sets contain two single-line Oswald inputs; original set has 51 duplicate-pixel groups with conflicting labels | Mandatory shared break, measured line boxes, visible ink per line, no clipping or duplicate images |
| Font identity | Downloaded/custom status did not verify binary family, weight, or style; 639-set has 21 synthetic italics | Native faces, actual CDP glyph verification after layout flush, fontkit metadata plus independent fontTools parsing, pinned bytes |
| Source disagreements | Poppins and Fira Sans ExtraLight declared CSS200 but static binary OS/2 weight275 | Conservatively omit all 30 current candidate instances with conflicting numeric evidence; preserve reasons |
| Experimental design | Width-only line-height lookup scores 578/639 (90.45%) | Compact 1,824-sample corpus; width-only lookup 34.87%, every spacing/width level appears 608 times; conditional correlations documented and accepted |
| Evaluation | Extra/missing/duplicate fields, alias strings, stale checkpoints/protocols could distort results | Strict whole-answer schema, canonical manifest labels, source/protocol/cohort identity, fail-closed live validation |
| Harbor/reporting | Answer-bearing metadata, corrupt PNG acceptance, in-place writes, incomparable summaries | Opaque tasks, staged replacement, common prompt and grader, verified shared-cohort reports |

## Release artifacts

- `dataset/fontbench-2-rendered/manifest.json`: 1,824 accepted inputs across all 50 catalog families.
- `dataset/fontbench-2-rendered/validation.json`: complete gate report; zero errors, 1,824 unique decoded images, 129 independently parsed font binaries.
- `catalog.json`, `skipped.json`, `fonts.lock.json`, and `fonts/`: frozen recipes, all 3,000 candidates accounted for, 1,176 explicit exclusions, retained source bytes.
- `dataset/fontbench-2/tasks`: 1,824 opaque Harbor tasks matching every rendered image and label.
- `site/index.html`: current validated input preview, six breakdowns and seven contact sheets; all model rows pending with no inherited scores.

## Validation gate matrix

All integration gates use base `14e792f`, checkpoint `a6deba1`, plus the final audit changes on `valid-01-benchmark-audit`.

| Gate | Result |
| --- | --- |
| Baseline `bun run test` before changes | 196 Python, 27 Bun tests passed; existing tests did not detect the new validity defects |
| Final Python suite | 293 passed |
| Final Bun browser/generator/recipe suite | 51 passed; TypeScript typecheck passed |
| Whole frozen dataset, independent validator | 1,824 inputs / 50 families / 129 font binaries; zero errors |
| All-task package-to-manifest integrity check | 1,824 images, labels, opaque identities, common instructions match |
| Oracle and malformed-answer verification | All 50 families: oracle reward 1.0, empty answer reward 0.0 |
| Full offline evaluator | 1,824 tasks, zero infrastructure errors |
| Offline matrix plus identical resume | 33 results / 33 attempts; no duplicate requests; SQLite integrity `ok` |
| Desktop and mobile browser checks | 1,824 inputs; seven loaded contact sheets, six breakdowns; no JS errors or horizontal overflow |
| Wheel build and installation outside repository | Shared prompt, validator, evaluator and CLI imported successfully; dependency consistency passed |
| Base-code controls | Renderer, recipes, provider/evaluator/runner, packager, reporting and validator regression failures reproduced in isolated controls |
| Full offline rendering replay | All 1,824 PNG hashes, layouts, labels, and 1,176 exclusions reproduced exactly; metadata is now canonicalized |
| Historical preservation | `git diff --quiet 14e792f -- dataset/rendered dataset/fontbench-1 results/runs/fontbench-2026-09-07/input results/runs/fontbench-2026-09-07/state.sqlite3` passed |

## Review and limitations

The compact scope was explicitly confirmed during the audit. Factor correlations, unequal family counts, the fixed pangram, declared category taxonomy, and synthetic small-caps policy are documented in README and valid-05. No claim of exhaustive coverage or universal perceptual correctness is made. Every accepted artifact passes objective consistency checks; selected representative images across all typography classes were visually inspected.

Simplifyfu review kept one shared prompt, one shared report validation boundary, staged generation, and focused font/image checks. Fontkit and fontTools serve separate generation and independent verification roles. Earlier images and paid results remain unchanged and are explicitly historical. No paid model inference, remote PR, push, or publication was performed.

Detailed evidence: [historical census](evidence/valid-01-historical-census.json), [oracle validation](evidence/valid-01-oracle-validation.json), [browser validation](evidence/valid-01-browser-validation.json), and the linked issue tickets.

Final dataset fingerprint: `d40a3cafa91610bbebaa6c49719f24efcbe754a328e448d3e51f0e1f217c79a6`. Evaluation protocol fingerprint: `3769c8cc383a4959533c4801eec6202035a5a8cd30b76644e8cdfbc11cc859ce`. [Final offline resume evidence](evidence/valid-01-final-run-smoke.json) and [blocked-network replay evidence](evidence/valid-02-offline-replay.txt) are retained in the ticket folder.

Final combined `bun run test` passed: 293 Python tests, 51 Bun tests, TypeScript clean. The historical 639-input validation command returned exit status 1 as expected; the frozen release returned exit status 0. CI now runs the release gate as well as the source tests. Remote CI was not run.
