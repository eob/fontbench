# FontBench V1.0.0 — finalized multi-provider publication

Publication status: **finalized** at `2026-09-09T00:28:53.514566+00:00`. The fixed comparison contains **728 shared inputs across 49 font families for each of eleven model configurations** (8,008 scored comparison responses).

**8,102 original final responses** are preserved, including 94 outside the shared comparison. The full frozen release has 1,824 inputs and 50 families; this publication samples that release and does not claim full coverage.

**No unresolved provider errors remain.** All 20 historical infrastructure failures have subsequent final responses. They remain in the attempt ledger and do not count as accuracy failures. All retained final responses were independently re-parsed and re-scored with zero discrepancies.

The cumulative recorded estimate is **$99.991901** against the authorized **$100** cap. The runner ended with `budget_exhausted`; that original execution state remains unchanged in the sealed source records. Publication finality is recorded separately.

| Model | Comparison inputs | Retained responses | Composite | All correct |
| --- | ---: | ---: | ---: | ---: |
| claude-fable-5-1 | 728 | 728 | 73.60% | 13.32% |
| claude-haiku-4-5-20251001 | 728 | 743 | 50.92% | 0.41% |
| claude-opus-5 | 728 | 731 | 69.55% | 4.26% |
| claude-sonnet-5 | 728 | 734 | 60.81% | 1.51% |
| gemini-3.1-pro-preview | 728 | 734 | 63.67% | 3.16% |
| gemini-3.5-flash-lite | 728 | 754 | 55.06% | 1.37% |
| gemini-3.8-flash | 728 | 736 | 65.04% | 3.98% |
| gpt-5.6-luna | 728 | 748 | 71.11% | 3.98% |
| gpt-5.6-sol | 728 | 732 | 74.95% | 8.10% |
| gpt-5.6-terra | 728 | 734 | 69.39% | 4.67% |
| gpt-6-astra | 728 | 728 | 87.77% | 40.11% |

## Immutable evidence

[final_results.json](final_results.json) contains the explicit cohort, configuration identities, comparison metrics, group breakdowns, and every original response wrapped with final status and its source attempt. [finalization.json](finalization.json) hashes all source artifacts and records source/finalizer provenance.

- Frozen release: [V1.0.0](../../../../releases/1.0.0.json); dataset Git commit `d69e87e2c206ea75c52f5b8340d677bd14af03e3`.
- Source checkpoint Git commit: `8e1f3026307e5a865c47f2b25bbac2c2b074f925`.
- Finalizer Git commit: `3d16dacc021f26c46c09b762b5c985b5b7004151`; clean checkout.
- Shared cohort SHA-256: `19097ac3b1a2cab662304dcea8f051297779934f2fc35d8d22bc79a1e66ee19e`.

The 728 inputs are the first 728 in the existing deterministic seed-0 shuffled task schedule, shared by every model. Selection does not inspect output scores. Verdana is the only release family absent from this cohort. Inputs have equal weight; families with more inputs contribute more to aggregate scores.

[run.json](run.json) retains invocation history, exact model configurations and code identities. [summary.json](summary.json), [attempts.jsonl](attempts.jsonl), the scorecards, and the SQLite checkpoint retain their original bytes. The run ID contains `all-except-fable` for historical continuity; Fable was added on resume and is included in this publication.

Metered API cost per scored input uses recorded token usage and model rates across the same comparison cohort. It excludes separate infrastructure attempts and unmetered reservations. Campaign spending includes all recorded attempts and conservative reservations; it is an estimate, not a provider invoice.

## Verification and future measurements

```bash
.venv/bin/python -m baseline.finalize \
  --run-dir results/runs/1.0.0/2026-09-08-all-except-fable --verify
```

This sealed run ID cannot resume. Use a new run ID for additional measurements against V1.0.0, preserving the same release identity. See [the run guide](../../../README.md), [finalization guide](../../../../releases/FINALIZATION.md), and [publication ticket](../../../../tickets/publish-01-v1-results.md).
