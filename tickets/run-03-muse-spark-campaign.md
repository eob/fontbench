# run-03-muse-spark-campaign: V1.0.0 campaign for Meta Muse Spark 1.3 and 1.2

- **Status**: In Progress
- **Branch**: `run-03-muse-spark-campaign`
- **Base**: `df7445fe` (`main`)
- **Machine**: eob-dev2
- **Harness**: muse
- **Session ID**: `01a08930-2a59-7aa0-811b-63e91a3fd454` (pale-sinope)
- **PR**: Pending
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

- [ ] Red: `muse-spark-1.3`/`muse-spark-1.2` unselectable; catalog file absent.
- [ ] Add `config/models.meta.json`; validate it loads with `load_model_config`.
- [ ] Offline Green: mock run with the new catalog; `bun run test`; `bun run validate:release`.
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

## Handoff and takeover log

- `2026-09-10`: Started by `muse` on `eob-dev2` (Session `01a08930-2a59-7aa0-811b-63e91a3fd454`).

## Handoff memo

- **Verified working**: Nothing yet; ticket and branch created.
- **Pending / blocker**: `MODEL_API_KEY` must be provided before any live step. Offline wiring next.
- **Repro command**: `.venv/bin/python -m baseline.runner --help`
- **Next action**: Write `config/models.meta.json`, then run the mock smoke test with the new catalog.
