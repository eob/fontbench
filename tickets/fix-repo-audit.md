# fix-repo-audit: Repository audit and corrective fixes

- Status: Completed (historical audit; subsequent validity defects resolved in valid-01 through valid-06)
- Branch: `fix-repo-audit`
- Base: `080ac96`
- Harness: Codex
- Workspace: `/mnt/disks/data/fontbench`
- Delivery: Committed to `main`; implementation branch `fix-repo-audit`

> **Historical ticket.** This records the September 7 prototype repairs. Its 639-image output was later found unsuitable for final benchmarking. The [current release](../CHANGELOG.md) and [validity tickets](README.md) supersede the data claims below; the original evidence remains intact.

## Scope and plan

1. Inspect all source modules, packaging, tests, and generated dataset contracts.
2. Reproduce scoring, rendering, Harbor integration, installation, and validation defects.
3. Fix proven defects and add focused regression coverage.
4. Regenerate affected task text artifacts, preserving existing rendered images and manifest.
5. Run Python tests, Bun tests, type checking, wheel/install smoke checks, and dataset validation.
6. Review changes for simplicity and record results and remaining limitations.

## Initial evidence

`python -m pytest -q` fails during collection:

```text
ImportError: cannot import name 'grade_prediction' from 'baseline.evaluator'
1 error in 0.99s
```

`bunx tsc --noEmit` fails:

```text
src/render.ts(85,42): error TS18048: 'font' is possibly 'undefined'.
src/render.ts(127,33): error TS2584: Cannot find name 'document'. Do you need to change your target library? Try changing the 'lib' compiler option to include 'dom'.
```

## Coordination

- Evaluator/CLI/export: audit_evaluator
- Font catalog/renderer: audit_renderer
- Harbor generator/adapter: audit_harbor
- Packaging/docs/existing test suite/integration: root
- Pre-existing modified manifest and 1,000 untracked rendered PNGs are preserved; hashes recorded outside the repo for final comparison.

Python wheel build also failed before changing package configuration:

```text
ValueError: Unable to determine which files to ship inside the wheel using the following heuristics
The most likely cause of this is that there is no directory that matches the name of your project (fontbench).
```

The committed task directory contains 1,030 tasks, including 30 stale pilot tasks; dataset.toml declares 1,000. The existing test still expects 30.
The checked-in manifest describes the old 30-task pilot; the pre-existing working manifest describes 1,000 current tasks. All 1,000 working PNGs match their corresponding packaged task images byte for byte.

Updated integrity regression fails before dataset cleanup:

```text
FAILED tests/test_fontbench.py::test_harbor_dataset_integrity
AssertionError: assert 1030 == 1000
```

Relocatable offline fixture exposes evaluator path dependence:

```text
FAILED tests/test_fontbench.py::test_baseline_evaluator_mock
KeyError: 'imagePath'
```

The generated container base used Alpine 3.19, whose normal support ended 2025-11-01. Updated to Alpine 3.24 (supported through 2028-06-01), according to the [official release table](https://alpinelinux.org/releases/) checked 2026-09-07.

CI uses the documented [setup-bun](https://github.com/oven-sh/setup-bun), [setup-python](https://github.com/actions/setup-python), and [checkout](https://github.com/actions/checkout) actions. Local equivalents of the workflow commands are validated below; remote GitHub Actions has not been run.

## Audit outcome

| Area | Proven issue | Correction |
| --- | --- | --- |
| Harbor prompts | Correct six-field answer embedded in instruction | Invariant placeholder schema; regenerated 1,000 tasks |
| Scoring | Substring matches and missing-value defaults inflated scores | Exact font/alias and enum comparisons; malformed responses score zero |
| Harbor execution | Sync adapter, wrong files, missing abstract methods, shell interpolation | Async download/upload and structured JSON; no prediction shell interpolation |
| Verifier | Ground truth depended on working directory; arrays/null crashed | Script-relative ground truth; safe handling and full fractional reward |
| Generator | Missing images, duplicates, escaping failures, stale pilot tasks | Input preflight, JSON serialization, bounded removal of 30 stale generated tasks |
| Rendering | Arial loaded Arial Narrow; Verdana upright used italic; fallback silently accepted | Correct Arial source, explicit face loading and actual glyph checks |
| Rendering variants | Unsupported weights and disabled small-caps synthesis mislabeled pixels | Skip unsupported variants, enable/record synthesis and face provenance |
| Rendering output | Errors leaked browsers and overwrote partial output | Browser cleanup and staged output replacement |
| Evaluation | Nonrelocatable image paths, malformed manifests, lost response/error data | Manifest-relative paths, strict target validation, full task serialization |
| Reporting | Mock could overwrite real results; hard-coded Pareto/prices/dates | Separate mock outputs, measured comparable-run frontier, sourced/unknown pricing |
| Installation/checks | Wheel build failed; tests and TypeScript did not run | Explicit Python package selection, current tests, DOM types, combined checks and CI |

## Audit validation at base 080ac96

- Python suite: 82 passed after the final audit changes.
- Bun suite: 27 passed; TypeScript checking passed.
- Isolated original-code reversions reproduced renderer 8/8, Harbor generator 19/19, adapter 10/10, and evaluator/export 59 failing regressions.
- Full corrected render: 639 supported samples across all 50 families; final provider-source run completed in 184.7 seconds.
- Generated and validated a separate 639-task Harbor dataset; full offline CLI evaluated 639 tasks with no errors.
- Docker image built from the corrected Alpine 3.24 Dockerfile. Inside the container, the oracle earned 1.0 and an empty object earned 0.0.
- Evaluator and generated verifier produced equal rewards on 57 independent edge cases.
- Wheel build and editable install passed; wheel imported and CLI ran outside the repository. The original packaging configuration still fails in an isolated control build.
- Bun dependency audit reported no known vulnerabilities; pip dependency consistency check passed.
- Follow-up isolated pip-audit scan found no known vulnerabilities in the 27 installed Python runtime/transitive dependencies or five test-tool packages. The local virtual environment's bootstrap setuptools 66.1.1 had three unique CVEs; it was upgraded to 84.0.0, and all 34 installed third-party packages then audited clean. This was an environment-only change; FontBench builds with Hatchling. Primary advisory links and exact evidence are in `/tmp/fontbench-dependency-audit.md`.
- All 1,000 retained packaged PNGs remain byte-identical to their source images. Hash comparison confirmed the pre-existing manifest and 1,000 untracked rendered PNGs were unchanged.

## Decisions and remaining data limits

Historical images and result JSON were preserved and explicitly labeled in README/results notes. Their original rendering/scoring cannot be treated as corrected measurements. Fresh validated samples have been frozen separately for the subsequent multi-provider run.

The loaded variant count differs by family; use the same frozen image set for comparisons. Provider font files are still fetched remotely, and actual face metadata records what was used.

Harbor host adapters can inspect task identifiers and host metadata; the baseline VLM receives only the instruction and image. This benchmark does not attempt to sandbox a malicious host-side adapter.

## Evidence locations

Detailed original traces and reversions are retained at `/tmp/fontbench-evaluator-audit.md`, `/tmp/fontbench-harbor-audit.md`, `/tmp/fontbench-renderer-audit.md`, and `/tmp/fontbench-packaging-control.log`. New regression tests are checked into the source tree. The user subsequently extended this work with the model matrix, durable runner, live evaluation, and benchmark page tracked in `feat-multi-provider-benchmark.md`.
