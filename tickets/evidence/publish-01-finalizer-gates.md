# Publication finalizer implementation evidence

Base commit: `8e1f3026307e5a865c47f2b25bbac2c2b074f925`.

Workfu/ticketfu execution: establish missing finalization and missing sealed-run guards with failing tests; implement offline source validation/scoring and fixed-cohort exports; pin immutable source and consumer guards; run isolated source reversions and regression gates; simplify implementation and record handoff. Root owns commits, live finalization, and publication.

| Gate | Result |
| --- | --- |
| Initial `tests/test_finalization.py` | 14 expected failures: missing tooling and missing sealed-run refusal. Verbatim: `publish-01-finalization-red.log`. |
| Sealed aggregation regression before its guard | 1 expected failure: changed sealed scorecard still accepted. Verbatim: `publish-01-sealed-aggregation-red.log`. |
| Isolated base checkout with finalization tests | 27 expected failures after removing implementation. Verbatim: `publish-01-finalization-reversion.log`. |
| Current finalizer with original runner/report consumer in isolated checkout | 2 expected failures: sealed resume and tampered sealed aggregation accepted. Verbatim: `publish-01-finalization-guards-reversion.log`. |
| Focused finalization + run aggregation + runner/lifecycle/state + page tests | 165 passed before final boundary cases. |
| Full `.venv/bin/python -m pytest -q` | 450 passed in 21.26 seconds, including 29 finalization cases. |
| Final focused rerun after historical-attempt chronology validation | 29 passed in 4.23 seconds. |
| `.venv/bin/python -m baseline.releases --release 1.0.0` | Passed; frozen release and protocol fingerprints unchanged. |
| `git diff --check -- baseline tests` | Passed. |

## Decisions and durable findings

- The physical run lock establishes inactivity. Budget status and invocation `finished_at` can be reported while cheaper work remains active; finalization does not trust either field for process closure.
- Successful and invalid-response outcomes are already immutable in the checkpoint. Finalization seals the campaign/publication boundary; it does not overwrite or relabel original records.
- Original source files must match a committed checkpoint. Their hashes and source Git bytes are checked both when creating and when verifying a seal. Finalizer provenance is recorded separately.
- Every final response is re-parsed and scored using the unchanged frozen parser, grade function, and release targets. Responses are then preserved verbatim as dictionaries in the export; raw SQLite and attempt artifacts remain byte-identical.
- Publication metrics, costs, latency, and all seven axis breakdowns share one explicit cohort. Full-release counts remain separate from publication counts. All final responses, including measurements outside the comparison, are retained.
- Metered cost derives from recorded token usage and model prices, excluding unmetered reservations and separate failed attempts. Unknown components yield null means and explicit known counts.
- Existing invalid answers remain final zeroes; unresolved infrastructure failures prevent sealing. No inference code is called by finalization.
- Aggregation validates existing seals before consuming their scorecards; unsealed live runs remain compatible. Explicit repository roots propagate through release-page construction.
- Independent review identified the need to verify source Git bytes during seal verification as well as creation. Shared `_committed_source` validation and a forgery test pin this invariant.
- Simplifyfu review kept the validation flow linear, used small shared helpers for repeated scoring/hash/source checks, and replaced a nested comprehension with a clear group loop. No frozen evaluator, provider, prompt, release descriptor, or corpus files changed.

## Handoff

Implementation: `baseline/finalize.py`; source-run guards in `baseline/runner.py`; sealed consumer validation in `baseline/reporting.py` and root propagation in `baseline/build_page.py`; tests in `tests/test_finalization.py`; usage/schema notes in `releases/FINALIZATION.md`.

No live campaign was finalized by this implementation agent. Root must resolve common/full publication scope, commit reviewed finalizer code, then invoke the finalizer against the committed source checkpoint and commit both generated publication files. Test artifacts are synthetic, use local HTTP mock transports only, and are not publication measurements.
