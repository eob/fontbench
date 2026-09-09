# publish-01-v1-results: Finalize and publish FontBench V1.0.0 measurements

- **Status**: In Progress
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
- [ ] Resolve publication scope, retry infrastructure failures if any, score and seal the chosen final artifact.
- [ ] Replace obsolete FontBench-1 app data and images with the verified V1 artifact; align all tables/charts on one cohort and remove fabricated metrics/scales.
- [ ] Run focused and required repository checks plus browser inspection.
- [ ] Push FontBench records and land the app changes on Kaya main via its required PR workflow.
- [ ] Promote only reviewed FontBench changes to edwardbenson-prod, preserving unrelated production work; verify the live page.

## Decisions and durable findings

Publication finality is separate from full dataset coverage. Never relabel partial 1,824-input scorecards complete or change the frozen expected task count to the shared sample size. All existing raw responses and attempt costs stay intact. Successful responses and malformed model responses are final; only infrastructure failures are retryable. There are no current failures to retry in the stopped checkpoint.

Kaya main and edwardbenson-prod have many unrelated divergent commits, but their current FontBench files match. Use a scoped promotion after the main PR, rather than merging all of main into production. Existing page defects include obsolete dataset identity, hardcoded category counts, unequal comparison cohorts, fabricated fallback scores/costs, and distorted exact-match scales.

## Validation checkpoint

Offline finalization tooling passed 450 Python tests; the final focused run passed all 29 seal/scoring cases. Frozen release validation passed without changing the dataset or protocol. Regression tests reproduce the missing seal guards and reject modified source bytes, forged provenance, invalid chronology, and inconsistent metrics. See [the finalizer gate record](evidence/publish-01-finalizer-gates.md).

A scratch conversion in `/tmp` supported website inspection using actual saved measurements. It must be replaced by the strict committed-artifact importer before publication. The final scope is the common 728-input cohort, relying on the existing sampling instruction rather than treating an unanswered optional full-coverage offer as authorization to increase spending.
