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

## Live startup

Started `2026-09-08T21:36:04Z` from clean code commit `db0f3421f49af7ae6955744c5d640a495c72c6cf` with ten workers and the $25 cumulative estimated guard. Native responses immediately showed an Anthropic account billing block for all three selected Claude models:

```text
HTTP 400: Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.
```

The runner paused Anthropic and continued OpenAI/Gemini. Fable was never requested. The Claude failures and conservative unmetered reservations are retained in the checkpoint; resetting a Fable model quota alone does not resolve this separate API credit-balance error. Resume the same run after the account has usable credits.

## Startup verification and monitoring

An independent read-only audit at `2026-09-08T21:38:53.722205+00:00` passed 627 checks over 144 attempts and 141 final observations. It recomputed the frozen dataset and protocol identities, checked all ten selected models with Fable absent, verified canonical targets and six-field grading, cost formulas, timestamps, configuration hashes, task uniqueness, and equality between the coherent SQLite transaction and exports. Estimated spending was $1.9826138, including $0.18848 conservatively reserved for the three unmetered Claude billing failures. No invalid model response had occurred in that initial sample.

The runner is detached and continues independently of the chat session. Initial runner PID: `3895324`; process command metadata is retained at `/tmp/fontbench-v1-campaign-process.json`. The operator helper `/tmp/fontbench-v1-campaign-monitor.py` (PID recorded in `/tmp/fontbench-v1-campaign-monitor.pid`) refreshes the run's README and local `site/` approximately every 60 seconds, with a final refresh when the runner stops. Helper logs remain in `/tmp`. It makes no model requests and does not automatically commit or push files.

Current work remains active while the guarded campaign runs. Higher spending and Anthropic credit availability remain user-controlled; neither is inferred from elapsed time. Any later resume uses the same run ID and preserves every completed final observation.
