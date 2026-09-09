# release-02-aggregate-run-history: Aggregate measurements for frozen releases

- **Status**: Completed (local implementation and validation)
- **Branch**: `valid-01-benchmark-audit` (shared branch coordinated by root)
- **Base**: `d69e87e`
- **Machine**: `eob-dev2`
- **Harness**: codex
- **Session ID**: `01a082cc-90d5-7b22-8096-9c43596303be` / verify_eval_closure
- **Assignee**: Edward Benson
- **Delivery**: Local implementation; root handles integration and publishing decisions.

## Goal

Build the FontBench 1.0.0 website from compatible measurements collected across arbitrary dated runs. Every compared result must identify the frozen corpus, protocol, request configuration, and original run; repeated measurements must never increase a task's weight or replace an earlier answer with a better score.

## Decisions and durable findings

- Group by the inference-configuration fingerprint supplied by `baseline.releases`: provider, model, normalized endpoint, and output cap. Preserve the full recorded configuration per run. Presentation IDs and pricing changes do not create a new measurement cohort.
- For each configuration and task, retain the first valid final measurement ordered by durable task `recorded_at`, then `run_id`, then source model ID. Invalid model answers are final zero-credit measurements. Infrastructure failures do not contribute completed tasks.
- Load only ledgers under the requested version and require matching release/version/Git/data/protocol provenance, explicit nonmock state, valid model configuration fingerprints, and valid task identities. Report exclusions and duplicates explicitly.
- Discover models from recorded run configurations. The current model catalog is not a prerequisite for reporting past measurements.
- Keep the existing single-directory page API for inspection. The release website shares its presentation and contact-sheet rendering while adding release/run provenance.

## Plan and validation gates

1. Completed: capture Red for missing cross-run aggregation/release-page behavior with offline fixture ledgers covering disjoint partial runs, duplicate chronology and ties, changed configurations, malformed/mismatched provenance, arbitrary catalog IDs, and origin display.
2. Completed: implement release-aware aggregation in `baseline/reporting.py`, using the release/run metadata APIs owned by `versioned_runs`; add a release page entry point and CLI to `baseline/build_page.py`.
3. Completed: preserve existing page/export behavior and run focused aggregation/page/export checks. Verify deterministic first-recorded selection and no duplicate weighting, including invalid-answer and peer-preservation cases.
4. Completed: reproduce the missing behavior in isolated source controls; run simplifyfu/comment hygiene and record final gates. Root owns full-suite validation, final website generation, and release documentation.

## Handoff & Takeover Log

- `2026-09-08`: Started by `codex` on `eob-dev2` after explicit user steering to freeze version 1.0.0 and accumulate future LLM runs. Coordinating API contracts directly with `versioned_runs`; no paid requests or dataset regeneration.

## Red evidence

Before implementation, `.venv/bin/pytest -q tests/test_run_aggregation.py` recorded **22 failed in 0.27s**. The failures directly show the missing aggregation and release-page entry points; fixture setup makes no provider requests. Full output: [release-02-red.log](evidence/release-02-red.log).

```text
E       AttributeError: module 'baseline.reporting' has no attribute 'aggregate_release_runs'
E       AttributeError: module 'baseline.build_page' has no attribute 'build_release_page'
```

Final review found that the legacy single-directory exporter still claimed version `2.0.0` and overwrote `results/fontbench_summary.json` when invoked without arguments. Three focused tests first reproduced the false version, default historical overwrite, and ignored explicit output arguments: **3 failed, 53 deselected in 0.48s**. Full output: [release-02-legacy-export-red.log](evidence/release-02-legacy-export-red.log). The repair marks utility output explicitly unversioned and requires both CLI paths; the release website's `benchmark.json` remains the canonical versioned export.

```text
E       AssertionError: assert '2.0.0' is None
E         - Historical results must stay intact.
E         + {
E         +   "benchmark_id": "fontbench",
```

## Implementation and final decisions

- `build_release_page()` and `python -m baseline.build_page --release 1.0.0` validate the frozen release and aggregate all compatible version-directory ledgers. The existing single-directory page API uses the same renderer. The release website's `benchmark.json` includes release hashes, shared cohort metrics, selected task origins, run history, duplicate policy, and exclusions.
- Model configurations come from recorded cards and invocation history. Inference-equivalent catalog IDs/prices combine; endpoint/model/provider/output-cap changes remain separate configurations. The website displays output caps and configuration IDs alongside run origins.
- `run.json`, summary, cards, and full configuration records must agree. Git identities require full hashes plus boolean dirty state, or an explicit unavailable `(null, null)` pair. Invocation histories preserve runner-code changes across resumed runs. Summary completed counts must match card coverage.
- All chronology is parsed as timezone-aware datetimes and emitted in UTC. Selected tasks must fall within an invocation that declares their exact configuration. Missing/naive timestamps and transport failures cannot become final measurements; invalid model answers remain final zero-credit rows.
- Duplicate scoring never erases cost history. Every compatible origin retains its full configuration, attempt counts, cost, dates, and runner provenance. Displayed costs include repeated attempts. Original `run.json`, summaries, scorecards, and available attempt exports are copied into the local site for inspection. Missing attempt exports are marked unavailable, and active-run exports may lag their summaries.
- The legacy single-directory utility remains available with explicit unversioned output. Its CLI requires `--results-dir` and `--output`, so a no-argument invocation cannot replace historical summaries.
- The simplifyfu pass kept shared rendering in one function, reused existing model/release validation, removed temporary test guards and redundant grouping fallbacks, and added no configurable policy wrapper. Comment hygiene found no narrative code comments to retain. Dataset/evaluator/provider sources and historical JSON artifacts were not changed by this ticket.

## Additional Red and reversion evidence

Independent reviews pinned **10** missing run-history/code-provenance checks and **3** task-finality/invocation-window checks before their fixes. The former admitted malformed histories or omitted invocation data; the latter admitted a timeout as a scored result or a task recorded outside its declared model invocation. Logs: [provenance Red](evidence/release-02-provenance-red.log), [finality Red](evidence/release-02-finality-red.log).

An isolated `d69e87e` report/page control with the final tests reproduced **39** missing-feature failures. A second isolated control removed only the finality/invocation-window checks and reproduced the same **3** malformed-admission failures. The legacy-export control replaced only that implementation with `d69e87e` and reproduced the same **3** false-version/default-overwrite failures. No shared branch reversions were used.

## Validation gate matrix

| Gate / command | Base | Result |
| --- | --- | --- |
| Initial aggregation/page regressions | `d69e87e` | **22 failed** for missing behavior; [Red log](evidence/release-02-red.log) |
| Final aggregation tests with isolated base report/page source | `d69e87e` | **39 failed** for the original missing APIs; [control log](evidence/release-02-reversion.log) |
| Isolated removal of finality/invocation-window checks | `d69e87e` + release work before those checks | **3 failed, 36 deselected** with the original admission failures; [control log](evidence/release-02-finality-reversion.log) |
| Final legacy-export tests with isolated base exporter | `d69e87e` | **3 failed, 53 deselected** with false version and unintended overwrite; [control log](evidence/release-02-legacy-export-reversion.log) |
| `.venv/bin/pytest -q tests/test_run_aggregation.py tests/test_build_page.py tests/test_export_structured.py` after simplification | `d69e87e` + coordinated release changes | **128 passed in 1.66s** |
| `git diff --check` on owned source/tests/ticket | `d69e87e` + coordinated release changes | Clean |
| Chromium desktop 1440px and mobile 390px, all release details open | `d69e87e` + coordinated release changes | **1,824 inputs, 50 families, seven loaded images, six dimensions, zero JS errors/overflow**; [browser report](evidence/release-02-browser-validation.json) |

The first mobile inspection proved a 461px document at a 390px viewport when full hashes were expanded; [Red evidence](evidence/release-02-mobile-red.json). Wrapping long release/configuration hashes restored the document width to 390px. Root visually reviewed the final desktop and mobile screenshots and verified the metric selector. The current site truthfully shows zero compatible release runs and explicitly excludes the historical September 7 pilot.

## Completion and handoff

Implementation, focused checks, isolated reversion controls, simplification, and browser checks are complete. Root coordinates the full combined gate and final commit. No paid requests, branch changes, or commits were performed by this subtask.
