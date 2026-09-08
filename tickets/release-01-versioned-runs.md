# release-01-versioned-runs: Freeze FontBench V1.0.0 and preserve version-bound runs

- **Status**: Completed (implementation and final integration verified)
- **Branch**: `valid-01-benchmark-audit` (shared integration branch)
- **Machine**: eob-dev2
- **Harness**: codex
- **Session ID**: `/root/versioned_runs`
- **PR**: Local integration; parent handles commit and publication
- **Assignee**: Edward Benson
- **Base commit**: `d69e87e2c206ea75c52f5b8340d677bd14af03e3`

## Goal

Freeze the accepted compact corpus as FontBench V1.0.0 using the exact dataset git commit and content/protocol hashes. Keep independent, resumable model runs under that version with enough durable provenance to aggregate observations made at different times.

## Red evidence

Command: `.venv/bin/python -m pytest tests/test_releases.py -q`

```text
E       AssertionError: Versioned release identity API is missing
E       assert None is not None
E       AssertionError: FontBench V1.0.0 release descriptor is missing
2 failed in 0.02s
```

## Plan

- [x] Prove release identity and descriptor are absent.
- [x] Add strict release descriptor loader and frozen dataset/protocol validation.
- [x] Bind runner directories, checkpoint identity, cards and summary to release; export timestamped durable attempts.
- [x] Make the console entrypoint use the resumable runner and default to V1.0.0; retain explicit custom-manifest API without version claims.
- [x] Pin mismatched data, protocol, descriptor, resume identity, timestamps and cross-invocation model additions.
- [x] Run focused gates, reversion check, simplifyfu and record results.

## Decisions and durable findings

The physical `dataset/fontbench-2-rendered` path stays frozen; the semantic benchmark version is a separate release descriptor. Explicit custom manifests remain unversioned. Each model configuration stores its full public catalog data; the inference fingerprint groups provider, exact model identifier, endpoint and output-token cap while excluding catalog display identifiers and prices. No API credentials are serialized. Separate runs can be made on separate dates without one global model schedule. Existing SQLite checkpoints preserve retries and spend; an exported JSONL attempt ledger makes that history reviewable in git.

No paid calls, image regeneration, historical-result relabeling, or evaluation-protocol edits are included.

## Further Red evidence

The runner regression failed before changing the runner:

```text
E       AssertionError: Runs have no explicit benchmark version identity
E       assert 'benchmark_version' in {'run_id': 'test', ...}
1 failed in 0.17s
```

An incremental export test exposed that the first draft would rewrite every prior attempt at every checkpoint:

```text
E           AssertionError: Attempt exports need a durable incremental sequence
E           assert None == 1
1 failed in 0.07s
```

Provider-default endpoint equivalence was also pinned before correction:

```text
E           AssertionError: assert '8f27707303fb...3ce6907198a1f' == '1cd64a44e90a...dcba25a8ae363'
1 failed in 0.11s
```

## Validation gate matrix

All gates ran against base `d69e87e2c206ea75c52f5b8340d677bd14af03e3` plus the shared integration changes.

| Gate / Command | Base commit | Result |
| --- | --- | --- |
| `.venv/bin/python -m pytest tests/test_releases.py tests/test_runner.py tests/test_runner_lifecycle.py tests/test_run_state.py -q` | `d69e87e` | **87 passed**, 0 failures, 6.57s |
| `.venv/bin/python -m baseline.releases --release 1.0.0` | `d69e87e` | Exact descriptor, Git manifest, dataset hash, protocol hash and live dataset validation passed; 1,824 tasks |
| Zero-task, zero-budget official live readiness run with provider evaluation replaced by a failure sentinel | `d69e87e` | 1,824 frozen tasks; 11 configured models; zero provider calls, zero spend; valid versioned checkpoint produced in a temporary directory |
| `.venv/bin/python -m baseline.cli --help` | `d69e87e` | Console exposes the versioned resumable runner and mutually exclusive custom manifest option |
| Isolated base-source reversion with the three original Red tests retained | `d69e87e` | **3 failed**, reproducing all original missing-identity failures; [verbatim output](evidence/release-01-reversion.log) |
| `git diff --check` | `d69e87e` | Clean |
| simplifyfu and comment hygiene | `d69e87e` | Removed duplicate fingerprint work and scorecard metadata; replaced the legacy console implementation with the runner entrypoint |

## Final invariants and operation

- `releases/1.0.0.json` binds the accepted corpus to its full Git commit, dataset fingerprint, evaluation protocol fingerprint, expected task count and preserved physical paths. A changed manifest, image, protocol, count, or missing Git anchor is rejected before any provider client is created.
- Official runs write `results/runs/1.0.0/<run-id>/`; mock directories use `mock-`. Omitting a run ID generates a new timestamp-plus-random ID; reusing an ID resumes only its identical release/config checkpoint.
- `run.json` preserves the initial creation date and an invocation history with selected full public model configs, start/end timestamps, budget/subset/concurrency, code Git commit and dirty state. Summary/cards repeat the release identity; per-task `recorded_at` remains unchanged on resume.
- The public inference fingerprint resolves default endpoints exactly as the provider adapter does, normalizes trailing slashes, and excludes pricing/display labels. Different actual models, providers, endpoints and token caps stay separate.
- `state.sqlite3` remains the authoritative checkpoint and attempt-cost history. `attempts.jsonl` appends only new attempt sequences during a run, retaining superseded failures; resume atomically rebuilds the text log from SQLite to repair a torn append. A retained result ledger without its SQLite checkpoint is rejected to prevent accidental repeat spending.
- The runner writes repository files but does not automatically commit them. Preserve the closed SQLite checkpoint together with JSON/JSONL artifacts in the integration/operator commit. No credentials are read for identity generation or serialized into the ledger.
- Custom manifests receive `benchmark_version: null` and no dataset Git release claim. Historical/unversioned outputs cannot silently become V1.0.0 results.


## Resume provenance follow-up

Independent integration review found that a surviving SQLite checkpoint with lost `run.json` silently reconstructed only the current invocation. This could erase an earlier model's configuration history and make valid retained results disappear from the website. A changed `run.json.created_at` also permitted more evaluation before the website rejected the ledger.

Red command:

```text
.venv/bin/python -m pytest tests/test_runner.py::test_resume_refuses_lost_or_corrupt_invocation_history_before_inference tests/test_runner.py::test_brand_new_empty_checkpoint_recovers_without_run_metadata -q --tb=short
E   AssertionError: No inference after lost or corrupt provenance
E   AttributeError: 'dict' object has no attribute 'append'
5 failed, 1 passed in 1.70s
```

[Verbatim Red output](evidence/release-01-resume-provenance-red.log) and [isolated implementation reversion](evidence/release-01-resume-provenance-reversion.log) retain the proof. The reversion reproduced five failures while the empty-checkpoint control passed.

The runner now requires retained invocation history whenever the checkpoint has registered models, including an initialized zero-task run. It compares the creation timestamp to SQLite, rejects malformed or empty invocation containers, and requires prior checkpoint model configurations to remain declared in history. Validation occurs before inference and before registering newly selected models. A completely empty SQLite database remains recoverable. Restore the original `run.json` to resume a damaged ledger.

Final follow-up gate: `.venv/bin/python -m pytest tests/test_releases.py tests/test_runner.py tests/test_runner_lifecycle.py tests/test_run_state.py -q` — **95 passed**, 0 failures, 10.24s, base `d69e87e2c206ea75c52f5b8340d677bd14af03e3` plus shared integration changes. `git diff --check` is clean. The simplifyfu pass kept the checks local to resume metadata and left report aggregation validation in its existing consumer.

## Integration closure

The final full Python gate exposed one old CLI test still using a raw model name and the retired root scorecard layout. Its failure is retained in [release-01-cli-migration-red.log](evidence/release-01-cli-migration-red.log). The test now supplies an explicit model catalog and run ID and verifies that the corresponding live run directory is untouched by mock output; all prediction-preservation assertions remain. No production or protocol code changed for this test migration.

The complete suite passes **413 Python tests and 78 Bun tests**, with TypeScript clean. The real V1.0.0 offline CLI recorded six observations across two configured models; two resumes retained exactly six attempts and zero spend. [Durable smoke evidence](evidence/release-01-integration-smoke.json) records all release hashes. Final integration is committed with the local `v1.0.0` tag; no remote publication or live inference is part of this closure.
