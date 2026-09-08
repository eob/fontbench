# run-01-v1-model-campaign: First V1.0.0 multi-provider campaign

- **Status**: In Progress
- **Branch**: `run-01-v1-model-campaign`
- **Base**: `df65c633c25b81b6abc55b732e8d526c0e7cbe20` (`v1.0.0`)
- **Machine**: eob-dev2
- **Harness**: codex
- **Session ID**: `/root` / FontBench release campaign
- **Assignee**: Edward Benson
- **Delivery**: Local run ledger and website; no remote publication requested.

## Authorized outcome

Run the complete frozen V1.0.0 corpus against all enabled OpenAI, Gemini, and Claude model configurations except `claude-fable-5-1`. Fable is deferred at the user's request until quota resets. The already-disabled historical Gemini 2.5 Flash-Lite remains excluded. Ten configurations target 18,240 final model–input observations.

The existing cumulative estimated $25 spending guard applies at launch. The user has been asked for the campaign ceiling because historical OpenAI/Gemini usage alone projects about $141 for complete coverage, plus unknown Claude usage. No higher cap applies until the user selects it.

## Plan and gates

- [x] Confirm V1.0.0 manifest, dataset/protocol fingerprints and independent readiness gate.
- [x] Verify credentials are present without exposing values; authenticated read-only model lists include all ten selected IDs.
- [x] Check current provider pricing documentation against the dated catalog.
- [ ] Run selected models using the checkpointed versioned runner; monitor completion, costs and provider errors.
- [ ] Preserve all final observations; retry only infrastructure failures within the authorized spending limit.
- [ ] Build the website from compatible versioned logs and verify recorded coverage/origins.
- [ ] Check SQLite integrity, freeze complete run exports, record outcome and commit local results.

## Run identity and command

Run ID: `2026-09-08-all-except-fable`.

```bash
bun run benchmark --release 1.0.0 --run-id 2026-09-08-all-except-fable \
  --models claude-opus-5 claude-sonnet-5 claude-haiku-4-5-20251001 \
    gpt-6-astra gpt-5.6-sol gpt-5.6-terra gpt-5.6-luna \
    gemini-3.1-pro-preview gemini-3.8-flash gemini-3.5-flash-lite \
  --budget-usd 25 --concurrency 10
```

The process writes `results/runs/1.0.0/2026-09-08-all-except-fable/`. Reusing this run ID preserves completed answers and attempt costs. Malformed model answers remain final zero-credit observations; infrastructure failures remain retryable. The corpus, rubric, grading, provider protocol and model configurations are unchanged.

## Preflight evidence and cost basis

Authenticated model-list evidence: [run-01-provider-preflight.json](evidence/run-01-provider-preflight.json). The dataset and evaluation hashes match `releases/1.0.0.json`; all 1,824 frozen inputs passed the release gate.

Current reference pricing checked September 8, 2026: [OpenAI model comparison](https://developers.openai.com/api/docs/models/compare?model-1=gpt-6-astra&model-2=gpt-5.6-sol&model-3=gpt-5.6-terra), [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna), [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), and [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing). Selected standard token rates match the catalog; no inference configuration changed.

A read-only inspection of the historical checkpoint projects $141.35 for the seven OpenAI/Gemini configurations at their previous mean cost per observation. This is a planning estimate on a changed corpus/prompt, not a billing guarantee. Claude has no usable prior metered observations; its historical provider-wide credit failures do not establish today's availability. Current inference responses will determine it.
