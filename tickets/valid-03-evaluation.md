# valid-03-evaluation: Strict answers and reproducible evaluation

- **Status**: Completed (local implementation and validation)
- **Branch**: `valid-01-benchmark-audit`
- **Base**: `14e792f`
- **Machine**: `eob-dev2`
- **Harness**: codex
- **Session ID**: `01a082ae-164d-73f2-a49e-a3d6e48adfaf` / evaluation_validity
- **Assignee**: Edward Benson
- **Delivery**: Shared local audit branch; parent coordinates integration.

## Goal

Reject ambiguous malformed answers, pin evaluation protocol identity, and make completion and compared cohorts auditable before final runs. Audit evaluator/provider requests and SQLite resumption entirely offline.

## Initial findings (regressions and repairs completed below)

- Prediction schema silently ignores additional keys and accepts whitespace-only font names. Python JSON parsing also silently resolves repeated keys, leaving ambiguous answers scorable.
- Dataset fingerprint excludes rendering evidence and uses a hardcoded grading marker. Default prompts differ between runner and evaluator, and changing request/grading code does not prevent mixing old and new protocol attempts in one run.
- Per-task scorecards do not expose cohort fingerprints, completion state, or invalid-answer counts explicitly. Runner deliberately leaves infrastructure errors retryable; invalid model answers are already final zero-credit tasks.

## Plan

1. Pin strict schema, duplicate JSON, protocol-resume changes, and scorecard cohort/status invariants with failing tests; record exact output.
2. Use one default prompt; fingerprint source/schema/prompt protocol and retain rendering evidence in dataset identity.
3. Add auditable cohort, status and invalid-response counters; coordinate dataset preflight and reporting integration with parent/other agents.
4. Run focused offline gates, isolated base-source reversions, full owned suites, and simplification review.

## Decisions and durable findings

- No paid requests. Existing provider accounting tests use local HTTP transports.
- Invalid model answers remain final zero-credit responses. Infrastructure failures pause models and remain retryable; partial scorecards must identify incompleteness rather than treating missing requests as model mistakes.
- Preserve historical results/checkpoints and refuse protocol changes under existing run IDs.

## Red evidence (before implementation)

Command: `.venv/bin/pytest -q tests/test_providers.py tests/test_evaluator.py tests/test_runner.py -k 'ambiguous_answers or whitespace_is_normalized or grading_boundary or partial_cohort or changed_evaluation_protocol or changed_rendering_evidence'`

Verbatim excerpts; complete output in [valid-03-red.log](evidence/valid-03-red.log):

```text
>       assert result.error_kind == 'invalid_response'
E       assert None == 'invalid_response'

>       assert result.composite_score == 0
E       AssertionError: assert 0.16666666666666666 == 0

>       assert card.status == 'partial'
E       AttributeError: 'FontBenchScorecard' object has no attribute 'status'

>       with pytest.raises(ValueError, match='fingerprint|protocol'):
E       Failed: DID NOT RAISE ValueError

14 failed, 88 deselected in 0.32s
```

A second checkpoint integrity reproduction found that foreign task IDs could replace missing cohort members by count and mark a partial run complete. Before the fix:

```text
>       with pytest.raises(ValueError, match='checkpoint'):
E       Failed: DID NOT RAISE ValueError
1 failed, 7 deselected in 0.16s
```

Command: `.venv/bin/pytest -q tests/test_runner.py -k foreign_checkpoint`.

Malformed aliases are also accepted by the manifest loader. A string alias container is iterated by character by the grader, admitting false font matches. Manifest conformance tests for strings, nonstrings, blank strings, and punctuation-only aliases recorded:

```text
>       with pytest.raises(ValueError, match='[Aa]lias'):
E       Failed: DID NOT RAISE ValueError
5 failed, 51 deselected in 0.17s
```

Command: `.venv/bin/pytest -q tests/test_evaluator.py -k malformed_aliases`; full output: [valid-03-alias-red.log](evidence/valid-03-alias-red.log).

## Implementation and decisions

- Grading version **3** rejects incomplete answers at both the provider and evaluator boundaries. Whitespace is stripped from every value; categorical values normalize case. Unknown/missing keys, duplicate JSON keys, nonstring values, and blank fonts produce one final zero-credit invalid response with original response/usage preserved.
- A single fallback prompt serves both evaluator entry points. `evaluation_protocol_fingerprint()` hashes the fallback prompt, schema, grading version, and UTF-8 source of request/grading modules, with platform line endings normalized. It has no absolute install paths. Conservative source hashing may require a new run ID after a formatting-only change; that is preferable to mixing protocols silently.
- Dataset identity includes rendering evidence and PNG bytes. Run identity combines dataset and protocol hashes; the full model configuration remains immutable in SQLite. Exported cards retain separate dataset and protocol fields.
- Scorecards state their sorted-task cohort hash, partial/complete status, and invalid-response count. Invalid responses stay in the denominator; transport/auth/billing errors remain retryable and incomplete rather than getting selected out of a supposedly complete leaderboard.
- Resumed completed checkpoints must match known task IDs, selected model identity, and current target labels. Image paths may change when relocating an identical dataset; source images remain pinned by dataset hash.
- Nonmock runner validation precedes client construction. Nonmock direct evaluation validates before predictions. Offline lifecycle fixtures explicitly substitute the gate; separate guard tests assert rejected data causes zero clients/requests.
- CLI clients close on both evaluation success and failure. Scorecard Markdown no longer claims an invariant 50-font universe.

## Validation gate matrix

| Gate / command | Base | Result |
| --- | --- | --- |
| Initial 14 strict-answer/protocol/cohort regressions | `14e792f` | RED: 14 failed; fixed: 14 passed |
| Isolated checkout of base Python sources with new tests | `14e792f` | Same 14 failures reproduced; [full output](evidence/valid-03-reversion.log) |
| Extended isolated base-source check including malformed aliases and foreign checkpoint IDs | `14e792f` | 20 failed; fixed: 20 passed; [full output](evidence/valid-03-reversion-extended.log) |
| `.venv/bin/pytest -q tests/test_providers.py tests/test_evaluator.py tests/test_runner.py tests/test_runner_lifecycle.py tests/test_run_state.py tests/test_model_config.py` | `14e792f` + audit changes | **168 passed** after removing one duplicate test |
| `git diff --check` | `14e792f` + audit changes | Clean |

## Completion

Implementation and integration completed in `d69e87e`. The simplifyfu and comment-hygiene pass removed one redundant test; changes introduce no transport wrapper or configurable policy abstraction. No remote inference was issued. Existing SQLite retention/idempotency, cumulative cost, concurrent runner locking, interruption draining, and retry tests remain green.

Final integration update: renderer and evaluator now read the exact same checked-in `baseline/prompt.txt` rubric. At audit closure, defaults pointed to `dataset/fontbench-2-rendered/manifest.json`; release-01 now selects that same corpus through the V1.0.0 registry. Historical manifests still require explicit paths and cannot pass the live validation gate. Explicit canonical grading tests pin `Helvetica Neue` != `Helvetica` and `Times` != `Times New Roman` without declared aliases. Complete Python suite at `a6deba1` plus final review changes: **293 passed in 7.48s**; `git diff --check` clean.
