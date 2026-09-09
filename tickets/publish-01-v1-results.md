# publish-01-v1-results: Finalize and publish FontBench V1.0.0 measurements

- **Status**: In Review
- **Branch**: `publish-01-v1-results`
- **Assignee**: Edward Benson
- **Machine**: eob-dev2
- **Harness**: codex
- **Session ID**: `/root` / FontBench publication

## Authorized outcome

Verify provider failures are resolved, independently score every retained output, explicitly seal the final measurements and publication cohort, commit and push the FontBench results, replace invalid historical results in the edwardbenson.com app through Kaya main, improve page accuracy and clarity, then publish the reviewed page through edwardbenson-prod. The user explicitly authorized remote pushes and website publication.

The $100 run has ended with 8,102 correctly scored final responses and no unresolved provider errors. The shared comparison has 728 tasks across all eleven models. The user previously authorized a compact sample rather than exhaustive coverage. Apply that authorization to the fixed 728-input shared comparison, preserve all 8,102 responses, and retain the $100 spending cap. The published page must explicitly distinguish this sample from the full 1,824-input release. A larger campaign can use a new run ID later.

## Plan and gates

- [x] Close and preserve the $100 checkpoint; independently re-parse/re-score all raw responses (zero discrepancies).
- [x] Add an immutable publication seal with release/source hashes, fixed model roster/cohort, explicit per-result finality, and offline verification.
- [x] Refuse mutation of sealed run IDs; preserve historical attempts and existing completion semantics.
- [x] Resolve publication scope, retry infrastructure failures if any, score and seal the chosen final artifact.
- [x] Replace obsolete FontBench-1 app data and images with the verified V1 artifact; align all tables/charts on one cohort and remove fabricated metrics/scales.
- [x] Run focused and required repository checks plus browser inspection; final source CI confirmation is recorded below.
- [ ] Push FontBench records and land the app changes on Kaya main via its required PR workflow.
- [x] Promote only reviewed FontBench changes to edwardbenson-prod, preserving unrelated production work; verify the live page.

## Decisions and durable findings

Publication finality is separate from full dataset coverage. Never relabel partial 1,824-input scorecards complete or change the frozen expected task count to the shared sample size. All existing raw responses and attempt costs stay intact. Successful responses and malformed model responses are final; only infrastructure failures are retryable. There are no current failures to retry in the stopped checkpoint.

Kaya main and edwardbenson-prod have many unrelated divergent commits, but their current FontBench files match. Use a scoped promotion after the main PR, rather than merging all of main into production. Existing page defects include obsolete dataset identity, hardcoded category counts, unequal comparison cohorts, fabricated fallback scores/costs, and distorted exact-match scales.

## Validation checkpoint

Offline finalization tooling passed 450 Python tests; the final focused run passed all 29 seal/scoring cases. Frozen release validation passed without changing the dataset or protocol. Regression tests reproduce the missing seal guards and reject modified source bytes, forged provenance, invalid chronology, and inconsistent metrics. See [the finalizer gate record](evidence/publish-01-finalizer-gates.md).

An early scratch conversion supported website inspection; the published page now uses the strict committed-artifact importer. The final scope is the common 728-input cohort, relying on the existing sampling instruction rather than treating an unanswered optional full-coverage offer as authorization to increase spending.

The official common-cohort publication is now sealed and verified: 728 shared inputs, 49 families, eleven configurations, all 8,102 retained responses marked final. Source checkpoint `8e1f3026307e5a865c47f2b25bbac2c2b074f925`; clean finalizer `3d16dacc021f26c46c09b762b5c985b5b7004151`. No inference was issued during scoring or sealing.

FontBench source and the `v1.0.0` tag are pushed; [PR #1](https://github.com/eob/fontbench/pull/1) targets main. The sealed artifact commit is `805e2146e5ee1637d05cd82c0477371f2b9e3228`. The Kaya importer verified this exact committed artifact, the frozen dataset manifest, and specimen PNG hashes. FontBench also passed all 78 Bun tests, TypeScript checking, and a sealed release-page build. Kaya focused checks, production build, mandatory main preflight, and 320/768/1440 browser interactions passed. Main and production publication are complete, as recorded below.

## Website delivery — 2026-09-09

Published at [edwardbenson.com/benchmarks/fontbench](https://edwardbenson.com/benchmarks/fontbench). Kaya [main PR #1076](https://github.com/eob/kaya-web/pull/1076) merged as `e3ecbb8294f91d98ed98e9ed156306e58a8edf27`; scoped [production PR #1078](https://github.com/eob/kaya-web/pull/1078) merged as `9c96d775265c6a2027730a2428288351df231a93`. Vercel deployment succeeded at 00:51:16 UTC. Kaya [closure PR #1081](https://github.com/eob/kaya-web/pull/1081) records the completed ticket on main.

The page replaces historical scores and SVGs, uses the fixed cohort for all scores and breakdowns, removes fabricated fallback metrics and nonlinear chart scales, and explains sample coverage, scoring, costs, and provenance. Ten actual specimen PNGs match the frozen dataset hashes. Live verification passed at 320/768/1440 px, all sixteen chart configurations, all seven table views, mouse/keyboard selection, source commit identity, and both downloadable artifact hashes.

Kaya main's required six-lane preflight passed (37 typecheck tasks, 5,544 tests, 3 skipped), along with fifteen focused app tests and 400 assertions, app typecheck, and production build. Closure preflight also passed all six lanes on newer main. Production app checks passed; the production-wide stale syntax-WASM gate failure reproduced on untouched production base and is recorded separately in Kaya's `tickets/considering/bug-edwardbenson-prod-stale-syntax-wasm.md`. Hosted Kaya Actions refused startup for account billing, so the prescribed local validation gates were used. Unrelated production changes were preserved.

The final FontBench source merge uses a merge commit to retain the dataset, finalizer, and sealed-artifact commits in main's ancestry. The sealed artifact bytes remain unchanged during CI harness cleanup and ticket closure.

## Source CI follow-up

PR #1's first hosted run exposed an unpinned Bun runtime: CI installed 1.4.2 and seven renderer error-handling tests timed out. A controlled executable-only comparison reproduced all seven failures locally on 1.4.2 and passed the unchanged 17-test renderer suite on 1.3.14. Pin the validated 1.3.14 runtime in CI/package metadata without changing test deadlines, rendering, or any frozen inputs/results. See [the runtime evidence and gate record](evidence/publish-01-bun-runtime-gates.md); hosted confirmation remains required after the fix is pushed.

The hosted 1.3.14 follow-up passed the prior rejection cases but hung at different subsequent browser/fixture boundaries until the job limit. Ordinary, CI-flags, and two-core local controls all passed. A narrower scratch experiment isolated the original 1.4.2 failure to async rejection assertion scheduling: native-awaiting each rejection before applying the same error matcher passed all 17 renderer tests in 9.41 seconds. Apply that test-only helper, retain all expectations/deadlines, and add separate CI phases plus a 180-second browser-step watchdog and CI-only stage diagnostics. Final hosted confirmation is still required; this changes no benchmark or sealed artifact bytes.

The native-await source commit passed every hosted phase in push run [34298344351](https://github.com/eob/fontbench/actions/runs/34298344351). The paired PR run encountered an intermittent Chromium debugging-pipe failure and then passed unchanged on retry [34298349971](https://github.com/eob/fontbench/actions/runs/34298349971). Its failed cleanup exposed a separate deterministic fixture-contamination defect. The test harness now restores shared state before closing browsers, captures its own resources, avoids redundant disconnected-browser closes, and reports a bounded close failure while guaranteeing directory cleanup. Both new cleanup regressions pass; restoring the original cleanup recreates the shared-state failure. The final local TypeScript/browser suite passes 80 tests / 277 assertions, with TypeScript checking also passing. Cleanup commit `9d3905184d995c4daa6f5f50a5fefa25a6ac04f5` passed all hosted PR phases in [34299177701](https://github.com/eob/fontbench/actions/runs/34299177701). The paired push encountered one intermittent screenshot-test browser transport disconnect; cleanup restored every shared fixture and all later recipe tests passed. The unresolved test-transport cause is tracked separately in [ci-01](ci-01-browser-transport.md); no benchmark data or renderer defect has been established.

## Presentation correction

The requested presentation excludes the composite score. Keep all original scoring fields and sealed artifact bytes for provenance, but use exact match (all six fields correct) as the report/chart default, show each attribute accuracy separately, and use explicitly labeled exact-match subgroup values. Apply the same rule to FontBench's generated HTML and the edwardbenson.com app through a scoped main/production follow-up. This changes presentation only; it does not revise V1.0.0 scoring or remeasure responses.

FontBench generated-report correction passed all 452 Python tests and browser verification of seven selectors, eleven model scores, and 770 subgroup cells. All fifteen generated JSON artifacts and every sealed source byte remain unchanged. See [presentation gate evidence](evidence/publish-01-exact-presentation-gates.md).

The exact-match app correction landed through [Kaya main #1089](https://github.com/eob/kaya-web/pull/1089), commit `df9229a9d7bacbb2292f2079bfb4c1e1a7f407da`, and [production #1092](https://github.com/eob/kaya-web/pull/1092), commit `aa06441566ed329869a3cdb998037519eabd6d93`. Production deployment succeeded at 01:45:10 UTC. No composite score appears in the corrected comparison UI; original immutable score fields remain preserved.

Final source control at `3c3b5887` passed all 80 browser/TypeScript tests (277 assertions), TypeScript checking, and wheel packaging locally; all 452 Python tests, frozen release checks, and seal verification passed. Hosted browser jobs remain intermittent, including one failed bounded retry at the same head. The renderer/test/protocol/data bytes match the earlier fully green hosted `9d390518` run; the separate browser transport investigation stays open. These results support publication integrity without claiming uniformly green hosted execution.
