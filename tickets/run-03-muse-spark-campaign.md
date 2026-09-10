# run-03-muse-spark-campaign: V1.0.0 campaign for Meta Muse Spark 1.3 and 1.2

- **Status**: Completed
- **Branch**: `run-03-muse-spark-campaign`
- **Base**: `df7445fe` (`main`)
- **Machine**: eob-dev2
- **Harness**: muse
- **Session ID**: `01a08930-2a59-7aa0-811b-63e91a3fd454` (pale-sinope)
- **PR**: https://github.com/eob/fontbench/pull/2
- **Assignee**: Edward Benson
- **Delivery**: Sealed two-model common-cohort publication; website import tracked in kaya-web `feature-fontbench-muse-spark-results`.
- **Completed**: 2026-09-10 through PR #2, merged to `main` as `234803f8`. Kaya-web page (PR #1249, production PR #1269) verified live with the Muse comparison.

## Goal

Run the complete frozen V1.0.0 corpus (1,824 inputs) against Meta's `muse-spark-1.3` and
`muse-spark-1.2` (Standard tier) over the Meta Model API, then seal the run as a fixed
common-cohort publication. The user authorized a **$100 cumulative estimated spending cap**
for this campaign.

## Context and requirements

- Meta Model API is OpenAI-compatible at `https://api.meta.ai/v1` (Responses API, `text.format`
  strict JSON schema, `usage.input_tokens`/`output_tokens`), keyed by `MODEL_API_KEY`. Model IDs
  and pricing verified at https://dev.meta.ai/docs/models and
  https://dev.meta.ai/docs/pricing-rate-limits: Standard tier $1.25 input / $4.25 output per 1M
  tokens for both versions.
- Wiring uses a separate catalog (`config/models.meta.json`) with `provider: openai` plus
  `base_url`, leaving the frozen `config/models.json` and request bodies untouched. A separate
  catalog also avoids the five-enabled-models-per-provider limit (the main catalog already has
  four OpenAI entries).
- One unverified field: the OpenAI adapter sends `detail: "high"` on `input_image` blocks, which
  Meta's docs do not mention. A 1-task live probe proves acceptance before the full run. If Meta
  rejects it, add a native `meta` provider instead of changing the frozen OpenAI body.
- No `--task-ids` targeting exists; the run covers the full corpus and seals with
  `--scope common`. The sealed 728-task run-01 cohort stays fixed and untouched.
- Live runs need `MODEL_API_KEY`, which is not present in this environment. The user provides it
  before the probe step.

## Plan and gates

- [x] Red: `muse-spark-1.3`/`muse-spark-1.2` unselectable; catalog file absent.
- [x] Add `config/models.meta.json`; validate it loads with `load_model_config`.
- [x] Offline Green: mock run with the new catalog; `bun run test`; `bun run validate:release`.
- [x] Live probes for both models; confirm structured output, usage accounting, cost math.
- [x] Full run: `--release 1.0.0 --config config/models.meta.json --run-id 2026-09-10-muse-spark
  --models muse-spark-1.3 muse-spark-1.2 --budget-usd 100 --concurrency 10`; retry only
  infrastructure failures.
- [x] Validity review: full coverage, zero unresolved infra failures, plausible score profiles.
- [x] Commit checkpoint and exports; `finalize --scope common`; `--verify`; commit the seal.
- [ ] Commit checkpoint and exports; `finalize --scope common`; `--verify`; commit the seal.
- [ ] Open PR for review; record merge provenance here.

## Red evidence (2026-09-10, pre-wiring)

`config/` holds only `models.json`. Selecting the Muse IDs fails for the expected causal
reason (no matching catalog entry), not a crash or bad flag:

```text
ValueError: Unknown or disabled models: muse-spark-1.2, muse-spark-1.3
```

Command: `.venv/bin/python -m baseline.runner --release 1.0.0 --mock --run-id red-check
--max-tasks 1 --models muse-spark-1.3 muse-spark-1.2` (raises at `runner.py:104`).

## Green evidence (2026-09-10, offline)

`config/models.meta.json` loads two enabled models via `load_model_config`, and the mock
smoke test completes 3/3 tasks for each:

```text
muse-spark-1.3 | openai | muse-spark-1.3 | https://api.meta.ai/v1 | MODEL_API_KEY | 1.25 / 4.25 | 4096
muse-spark-1.2 | openai | muse-spark-1.2 | https://api.meta.ai/v1 | MODEL_API_KEY | 1.25 / 4.25 | 4096
```

Reversion check: the same mock command without `--config config/models.meta.json` fails with
the identical Red signature (`ValueError: Unknown or disabled models`), proving the catalog
is what turns selection Green. Mock run directories are git-ignored.

| Gate / command | Base commit | Result |
| :--- | :--- | :--- |
| `bun run benchmark --release 1.0.0 --config config/models.meta.json --mock --run-id smoke-meta --max-tasks 3 --models muse-spark-1.3 muse-spark-1.2` | `df7445fe`+branch | 3/3 mock tasks per model, cost $0 |
| `.venv/bin/python -m pytest -q` | `df7445fe`+branch | 452 passed, 0 failed (21s) |
| `bun test src` | `df7445fe`+branch | 80 pass, 0 fail |
| `tsc --noEmit` | `df7445fe`+branch | clean |
| `bun run validate:release` | `df7445fe`+branch | fingerprints match; 1,824 expected tasks |

## Live probe saga (2026-09-10)

All probes used throwaway run IDs (dirs removed after analysis); only the numbers below are kept.

1. **4096 cap**: `muse-spark-1.2` completed cleanly (512 in / 2531 out, 18.3s, valid
   parsed prediction). `muse-spark-1.3` returned `status: incomplete`
   (`max_output_tokens`) with all 4096 output tokens spent on high-effort reasoning,
   59.4s, scored 0 as `invalid_response`. A 4096 cap would have silently zeroed 1.3
   across the campaign, so the cap moved to 8192 for both (identical inference settings).
2. **8192 cap, 60s transport timeout**: 1.3 completed one task (4173 out, 59.8s) and
   timed out twice on the next (121s, `unavailable`, keeps its reservation). 1.2 stayed
   clean (2972–3254 out, ~20s). 1.3-high routinely needs 60–120s per request.
3. **Fix**: the evaluation protocol fingerprint hashes `evaluator.py`/`providers.py`
   source, so the 60s default there is untouchable for a V1.0.0 campaign. Following the
   existing anthropic-workspace-header precedent, `runner.py` (not fingerprinted) now
   extends the httpx timeout to 300s for the Meta endpoint only. Pinned by
   `test_meta_endpoint_gets_extended_transport_timeout` (Meta with/without trailing
   slash → 300s; default and OpenAI URLs → 60s).
4. **300s proof**: all 4 attempts clean — 1.3 at 67.6s/3215 out and 105s/6892 out, 1.2
   at 11–22s. Both 1.3 requests would have died at 60s.
5. **Headroom**: max observed output is 6892 tokens, so the cap moved to 16384 for both
   models. Unused headroom costs nothing (metered billing; reservations only gate the
   last ~$0.15 of headroom per scheduling check).

Projections for 1,824 x 2: ~$45–85 actual spend (1.3 ~$0.015–0.03/task, 1.2 ~$0.01–0.018),
~5h wall time at concurrency 10. The $100 guard trips first if projections slip; a partial
seal (`--scope common`) is the fallback.

| Gate / command | Base commit | Result |
| :--- | :--- | :--- |
| `pytest tests/test_runner.py::test_meta_endpoint_gets_extended_transport_timeout` | branch | Red 2 failed/2 passed → Green 4 passed |
| `.venv/bin/python -m pytest -q` | branch | 456 passed, 0 failed |
| `bun run validate:release` | branch | fingerprint `3769c8cc…` unchanged |
| Live 300s probe (throwaway ID, since removed) | branch | 4/4 clean, parsed predictions valid |

Stale probe run directories were deleted (superseded 4096/8192-cap and 60s-timeout configs
would otherwise pollute release aggregation as distinct configurations).

## Validity review and seal (2026-09-10)

Run `2026-09-10-muse-spark` finished `complete` in one invocation ($100 guard, concurrency
10): **3,648/3,648 observations, $66.9465 spent, SQLite `integrity_check ok`**, no duplicate
(model, task) pairs, release/dataset/protocol identity matching V1.0.0.

- `muse-spark-1.2`: 1824/1824 clean, zero retries, zero unmetered attempts.
- `muse-spark-1.3`: 1819 clean + 5 `invalid_response`, all `status: incomplete` at exactly
  16384 output tokens in a single request (genuine non-answers, final zeroes per protocol,
  0.27% of its tasks). 7 responses topped 15000 output tokens. One transport retry
  (font-playfair-display-v42) recovered cleanly; its $0.0905 cost retains the unmetered
  reservation per protocol. Zero unresolved infrastructure failures.
- Latency vindicates the 300s fix: 1.3 median 73.3s with 1222/1824 responses over 60s (max
  254.3s, inside the 300s budget); even 1.2 peaked at 63.0s twice.
- Score profiles are plausible with no degeneracies (category ~94%, modifier ~91–96%,
  kerning/line-height ~51–57%, weight ~77–80%).

Sealed with `--scope common`: **1824 tasks x 2 models across all 50 families** (full-release
coverage, unlike run-01's 728/49 sample). `--verify` re-parsed and re-scored all 3,648
responses with zero discrepancies; artifact hashes match committed bytes.

| Model | Exact | Font | Mean cost/input | Mean latency |
| :--- | :--- | :--- | :--- | :--- |
| muse-spark-1.3 | 4.17% | 19.68% | $0.022801 | 79.37s |
| muse-spark-1.2 | 2.85% | 12.45% | $0.013861 | 19.64s |

- Checkpoint commit: `d88a09dc` (source == finalizer, clean)
- Seal commit: `e1e95f25`
- Shared cohort SHA-256: `d46fb9667177ae3a652f06ded92c09da042a08c3beaee4926ad70778423d44ac`

This cohort (full 1824) differs from run-01's 728-task cohort, so cross-publication model
rankings are not valid. The website presents the Muse results as a second fixed comparison.

## Handoff and takeover log

- `2026-09-10`: Started by `muse` on `eob-dev2` (Session `01a08930-2a59-7aa0-811b-63e91a3fd454`).

## Handoff memo

- **Verified working**: Campaign complete (3648/3648, $66.95); validity review passed; seal committed at `e1e95f25` and `--verify` clean.
- **Pending / blocker**: None. Merge PR #2 to `main` (pre-authorized), then close the ticket.
- **Repro command**: `.venv/bin/python -m baseline.finalize --run-dir results/runs/1.0.0/2026-09-10-muse-spark --verify`
- **Next action**: Push the seal, merge PR #2, hand the seal commit to the kaya-web page import.
- **Merge authorization**: User pre-authorized merging PR #2 to `main` after the seal verifies.
