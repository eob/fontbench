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
- [ ] Run focused and required repository checks plus browser inspection.
- [ ] Push FontBench records and land the app changes on Kaya main via its required PR workflow.
- [ ] Promote only reviewed FontBench changes to edwardbenson-prod, preserving unrelated production work; verify the live page.

## Decisions and durable findings

Publication finality is separate from full dataset coverage. Never relabel partial 1,824-input scorecards complete or change the frozen expected task count to the shared sample size. All existing raw responses and attempt costs stay intact. Successful responses and malformed model responses are final; only infrastructure failures are retryable. There are no current failures to retry in the stopped checkpoint.

Kaya main and edwardbenson-prod have many unrelated divergent commits, but their current FontBench files match. Use a scoped promotion after the main PR, rather than merging all of main into production. Existing page defects include obsolete dataset identity, hardcoded category counts, unequal comparison cohorts, fabricated fallback scores/costs, and distorted exact-match scales.

## Validation checkpoint

Offline finalization tooling passed 450 Python tests; the final focused run passed all 29 seal/scoring cases. Frozen release validation passed without changing the dataset or protocol. Regression tests reproduce the missing seal guards and reject modified source bytes, forged provenance, invalid chronology, and inconsistent metrics. See [the finalizer gate record](evidence/publish-01-finalizer-gates.md).

A scratch conversion in `/tmp` supported website inspection using actual saved measurements. It must be replaced by the strict committed-artifact importer before publication. The final scope is the common 728-input cohort, relying on the existing sampling instruction rather than treating an unanswered optional full-coverage offer as authorization to increase spending.

The official common-cohort publication is now sealed and verified: 728 shared inputs, 49 families, eleven configurations, all 8,102 retained responses marked final. Source checkpoint `8e1f3026307e5a865c47f2b25bbac2c2b074f925`; clean finalizer `3d16dacc021f26c46c09b762b5c985b5b7004151`. No inference was issued during scoring or sealing.

FontBench source and the `v1.0.0` tag are pushed; [PR #1](https://github.com/eob/fontbench/pull/1) targets main. The sealed artifact commit is `805e2146e5ee1637d05cd82c0477371f2b9e3228`. The Kaya importer verified this exact committed artifact, the frozen dataset manifest, and specimen PNG hashes. FontBench also passed all 78 Bun tests, TypeScript checking, and a sealed release-page build. Kaya focused checks, production build, and 320/768/1440 browser interactions pass; the mandatory repository preflight and final production promotion remain in progress.

PR #1's first hosted run exposed an unpinned Bun runtime: CI installed 1.4.2 and seven renderer error-handling tests timed out. A controlled executable-only comparison reproduced all seven failures locally on 1.4.2 and passed the unchanged 17-test renderer suite on 1.3.14. Pin the validated 1.3.14 runtime in CI/package metadata without changing test deadlines, rendering, or any frozen inputs/results. See [the runtime evidence and gate record](evidence/publish-01-bun-runtime-gates.md); hosted confirmation remains required after the fix is pushed.
