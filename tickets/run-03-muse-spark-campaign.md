# run-03-muse-spark-campaign: V1.0.0 campaign for Meta Muse Spark 1.3 and 1.2

- **Status**: In Progress
- **Branch**: `run-03-muse-spark-campaign`
- **Base**: `df7445fe` (`main`)
- **Machine**: eob-dev2
- **Harness**: muse
- **Session ID**: `01a08930-2a59-7aa0-811b-63e91a3fd454` (pale-sinope)
- **PR**: https://github.com/eob/fontbench/pull/2
- **Assignee**: Edward Benson
- **Delivery**: Sealed two-model common-cohort publication; website import tracked in kaya-web `feature-fontbench-muse-spark-results`.

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
- [ ] Full run: `--release 1.0.0 --config config/models.meta.json --run-id 2026-09-10-muse-spark
  --models muse-spark-1.3 muse-spark-1.2 --budget-usd 100 --concurrency 10`; retry only
  infrastructure failures.
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

## Handoff and takeover log

- `2026-09-10`: Started by `muse` on `eob-dev2` (Session `01a08930-2a59-7aa0-811b-63e91a3fd454`).

## Handoff memo

- **Verified working**: Probes prove the wire path; 300s Meta timeout fix tested (456 pytest pass, fingerprint unchanged); full campaign launched.
- **Pending / blocker**: None. Campaign `2026-09-10-muse-spark` running detached; log at `/tmp/fontbench-muse-run.log`.
- **Repro command**: `bun run benchmark --release 1.0.0 --config config/models.meta.json --mock --run-id smoke-meta --max-tasks 3 --models muse-spark-1.3 muse-spark-1.2`
- **Next action**: Monitor the campaign (`tail -f /tmp/fontbench-muse-run.log`), then commit the checkpoint, `finalize --scope common`, `--verify`, and push the seal.
