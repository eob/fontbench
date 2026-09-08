# valid-04-packaging-reporting: Isolate answers and preserve comparable measurements

- **Status**: Completed (local implementation and validation)
- **Branch**: `valid-01-benchmark-audit` (shared ownership coordinated by root)
- **Machine**: eob-dev2
- **Harness**: codex
- **Session ID**: `01a082ae-164d-73f2-a49e-a3d6e48adfaf` (packaging sub-agent)
- **PR**: Local audit; no publishing requested
- **Assignee**: Edward Benson
- **Base commit**: `14e792f`

## Goal
Package only intact benchmark images without exposing typography labels, and publish scores only with consistent dataset, grading, and cohort provenance.

## Observed failure mechanisms
- Harbor task names are font-bearing task IDs; task metadata tags contain category, weight, modifier, and width answers.
- Packaging accepts any file as PNG, mutates prior output in place, and permits extra environment files or symlinks in retained tasks.
- Generated verifier awards partial credit for incomplete schema, unlike the tightened six-field protocol.
- Structured export trusts aggregate score fields, lacks strict protocol/mock identity, and describes every export as 50 fonts regardless of evaluated data.
- Page can throw on malformed persisted cards; partial displays do not provide shared input counts. Dataset-validity wording precedes any validity gate.

## Plan
1. Pin corrupt image, label leakage, retained stale file/symlink, strict verifier, malformed card, aggregate mismatch, and provenance regressions with Red tests.
2. Build Harbor tasks in staging, validate PNG bytes/checksums and manifest image hashes, remove label-bearing public metadata, and replace only recognized generated output with rollback.
3. Align Harbor JSON validation with grading version 3 and evaluator schema.
4. Make page expose root validator results and shared-cohort metrics; validate scorecard protocol identity and malformed shapes.
5. Require complete/provenance-compatible export inputs and derive scores/taxonomy from task rows.
6. Run focused tests and isolated old-implementation controls, document exact evidence and validation gates, and simplify changed code.

## Red evidence
Executed before fixes, with expected causal failures:

```text
invalid complete response {"font":"   ","category":"non-serif","weight":"bold","modifier":"italic","kerning":"tight","line_height":"loose"} receives zero total credit
Expected: 0
Received: 0.8333333333333334

invalid complete response duplicate font keys receives zero total credit
Expected: 0
Received: 1

FAILED tests/test_export_structured.py::test_export_recomputes_metrics_from_task_outcomes
E       assert 100.0 == 0.0
FAILED tests/test_export_structured.py::test_export_font_count_comes_from_observed_data
E       assert 50 == 1

FAILED tests/test_build_page.py::test_corrupt_scorecard_json_is_excluded_with_warning
json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
FAILED tests/test_build_page.py::test_partial_comparison_records_intersection_of_measured_inputs
E       KeyError: 'comparison'

FAILED tests/test_harbor_agent.py::test_duplicate_response_keys_are_rejected_before_upload
E       Failed: DID NOT RAISE ValueError
```

The adapter's eventual contract preserves invalid response text for zero-credit verification instead of aborting the measurement. The final regression asserts duplicate keys survive unchanged for the verifier to reject, and provider exceptions still propagate without fabricated predictions.

Corrupt PNG bytes, label-bearing task metadata, retained environment extras, and failed staging writes were separately reproduced against the base implementation in isolated controls.

## Validation gate matrix
All gates use base commit `14e792f` plus the coordinated local audit changes.

| Gate / Command | Base commit | Result |
| --- | --- | --- |
| `bun test src/generate_harbor_dataset.test.ts` | `14e792f` | 32 passed, 0 failed; 73 assertions |
| `.venv/bin/python -m pytest tests/test_build_page.py tests/test_export_structured.py tests/test_harbor_agent.py -q` | `14e792f` | 70 passed |
| `bun run typecheck` | `14e792f` | Passed |
| Isolated base exporter, new outcome/census tests | `14e792f` | 2 failed for original 100%-instead-of-0 and 50-instead-of-1 errors |
| Isolated base page, malformed/corrupt/cohort tests | `14e792f` | 4 failed, 1 passed; crashes and absent shared comparison recur |
| Isolated base Harbor adapter, invalid-answer tests | `14e792f` | 6 failed; invalid answers abort or duplicate keys are normalized away |
| Isolated base packager, leakage/corruption/verifier/staging tests | `14e792f` | 8 failed, 0 passed; all original failures recur |

Control directory: `/tmp/fontbench-report-control-ak16lyax`. Controls copy the current dependency modules and final tests but replace only each owned implementation with `git show 14e792f:<path>`. The old packager control resolves its legacy source task directory so schema failures are proved by incorrect rewards rather than missing-path errors. No shared branch reversions, stashes, or paid inference were needed. Full logs were recorded in `/tmp/fontbench-control-{package,page,export,adapter}.log`; the causal excerpts above are durable.

A boundary pass additionally pinned unhashable persisted status/error-kind fields. Red raised `TypeError: unhashable type: 'dict'`; tuple membership now rejects these with a warning. No unexplained flaky failures occurred.

## Decisions and durable findings
Historical data and reports remain reviewable but are not evidence that an input set passed the new validity gate. Agent-visible Harbor files contain only generic task instructions and the PNG; original manifest IDs remain verifier-side.


## Completed changes
- Harbor release CLI defaults to FontBench-2 and requires the dataset readiness gate before creating anything. The pure builder remains available for isolated structural fixture tests.
- PNG input validation checks signature, chunk CRCs, RGB/RGBA layout, decompression length, scanline filters, and the recorded image SHA-256 when present. Its intentionally narrow format is the Chromium screenshot format used by the renderer; the release validator also fully decodes pixels using Pillow.
- Opaque task names derive from image bytes and internal task ID; public task tags and instructions contain no answer labels. Original IDs live only in verifier ground truth. All tasks use the shared frozen `baseline/prompt.txt` plus generic input/output paths.
- Packaging validates every existing generated task tree, rejects retained/stale extras and symlinks, stages all files, and restores the previous dataset on a failed final rename. A recovery directory is retained if restoration itself fails. Unsupported filesystem crash atomicity is not claimed.
- Harbor verifier accepts exactly six required string fields, normalizes allowed labels, rejects unknown fields/duplicate keys/empty fonts, and gives invalid objects zero total credit.
- Page and exporter share scorecard integrity validation: current grading/protocol fingerprints, cohort hash, explicit mock provenance, truthful completion counts, boolean outcome fields, and no infrastructure errors masquerading as completed measurements.
- Page displays dataset gate status, excludes invalid-input scorecards, reports the common measured cohort, and keeps partial-run limitations visible.
- Export derives metrics, latency, observed font taxonomy, and metered token-cost estimates from actual task rows. Stale hardcoded font/model descriptive registries and guessed token estimates were removed. Pareto groups require matching dataset, protocol, and completed cohort.
- `simplifyfu` and comment hygiene pass completed: common reporting checks are shared between two consumers, unused imports/constants and obsolete registries removed, and generated-file narration reduced. Repeated focused gates remained green.

## Remaining scope
Remote Harbor installation/container execution and live provider calls were not performed. Root owns the final fresh dataset release gate, generated site, integrated test run, and main audit ticket. Sampling-factor correlations were independently reviewed and resolved as an explicitly accepted compact-design limitation in `valid-05-experimental-design.md`.

## Generated-page browser verification

After the fresh site was built, Playwright Chromium checked both 1440×1000 desktop and 390×844 mobile layouts. Both report a passed dataset gate, 1,824 inputs, 50 font families, 11 pending model configurations, six dimension sections, seven successfully loaded contact-sheet images, zero JavaScript errors, and no document-level horizontal overflow. Switching the metric selector to line height updates its heading and preserves unmeasured values as dashes. Screenshots were visually reviewed at `/tmp/fontbench-page-desktop.png` and `/tmp/fontbench-page-mobile.png`; structured evidence is `/tmp/fontbench-page-browser-check.json`.

The first inspection harness timed out because it waited for below-the-fold lazy images without requesting their load. Setting those existing image elements to eager in the inspection harness verified every source asset; no application change was necessary.

A final adapter parity pass pinned its output cap: Google SDK requests previously had `max_output_tokens=None` while the default baseline protocol uses 1,024. The causal Red assertion was `AssertionError: assert None == 1024`; the adapter now sets 1,024 explicitly, and all 11 adapter tests pass. Nondefault model configurations remain a separate baseline-runner configuration, not an inferred Harbor setting.
