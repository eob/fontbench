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
- [ ] Live 1-task probe for both models; confirm structured output, usage accounting, cost math.
- [ ] Full run: `--release 1.0.0 --config config/models.meta.json --run-id <id> --models
  muse-spark-1.3 muse-spark-1.2 --budget-usd 100`; retry only infrastructure failures.
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

## Handoff and takeover log

- `2026-09-10`: Started by `muse` on `eob-dev2` (Session `01a08930-2a59-7aa0-811b-63e91a3fd454`).

## Handoff memo

- **Verified working**: Meta catalog loads; mock run Green for both models; pytest 452, bun 80, tsc, release gate all pass.
- **Pending / blocker**: `MODEL_API_KEY` must be provided before any live step.
- **Repro command**: `bun run benchmark --release 1.0.0 --config config/models.meta.json --mock --run-id smoke-meta --max-tasks 3 --models muse-spark-1.3 muse-spark-1.2`
- **Next action**: With `MODEL_API_KEY` set, run the 1-task live probe (`--run-id probe-meta-detail-01 --max-tasks 1 --budget-usd 5`), then start the full campaign on a fresh run ID.
