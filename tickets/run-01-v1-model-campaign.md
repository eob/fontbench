# run-01-v1-model-campaign: First V1.0.0 multi-provider campaign

- **Status**: Completed
- **Branch**: `run-01-v1-model-campaign`
- **Base**: `df65c633c25b81b6abc55b732e8d526c0e7cbe20` (`v1.0.0`)
- **Machine**: eob-dev2
- **Harness**: codex
- **Session ID**: `/root` / FontBench release campaign
- **Assignee**: Edward Benson
- **Delivery**: Final shared-cohort publication and remote run history; publication authorized in the follow-up task.

## Current outcome

The campaign ended at its $100 guard with 8,102 final responses across all eleven configurations and no unresolved provider errors. The fixed publication contains 728 identical inputs per model (49 families), consistent with the accepted compact-sampling scope. All final responses and historical attempts are preserved and sealed; full 1,824-input coverage remains partial. The source checkpoint is `8e1f3026307e5a865c47f2b25bbac2c2b074f925`, and final publication artifacts are committed at `805e2146e5ee1637d05cd82c0477371f2b9e3228`.

This run ID cannot resume after sealing. Later measurements use a new run ID. [Publication ticket](publish-01-v1-results.md) tracks remote integration and the website replacement; the operational notes below retain the earlier execution history.

## Original campaign target

Run the complete frozen V1.0.0 corpus against all enabled OpenAI, Gemini, and Claude configurations. The user subsequently added Anthropic funds/limits and explicitly included `claude-fable-5-1`. All eleven enabled configurations now target 20,064 final model–input observations. The already-disabled historical Gemini 2.5 Flash-Lite remains excluded.

The user has authorized a **$100 cumulative estimated spending cap**, raised from the earlier $25 and $50 guards. This includes all earlier attempts in the same campaign. Historical OpenAI/Gemini usage alone projects about $141 for complete coverage, plus unknown Claude usage; the campaign stops at the authorized guard if it cannot finish within it.

## Plan and gates

- [x] Confirm V1.0.0 manifest, dataset/protocol fingerprints and independent readiness gate.
- [x] Verify credentials are present without exposing values; authenticated read-only model lists include all ten selected IDs.
- [x] Check current provider pricing documentation against the dated catalog.
- [x] Run selected models using the checkpointed versioned runner; monitor completion, costs and provider errors.
- [x] Preserve all final observations; retry only infrastructure failures within the authorized spending limit.
- [x] Build the website from compatible versioned logs and verify recorded coverage/origins.
- [x] Check SQLite integrity, freeze final run exports, record outcome and commit local results.

## Run identity and command

Run ID: `2026-09-08-all-except-fable`.

```bash
bun run benchmark --release 1.0.0 --run-id 2026-09-08-all-except-fable \
  --models claude-fable-5-1 claude-opus-5 claude-sonnet-5 claude-haiku-4-5-20251001 \
    gpt-6-astra gpt-5.6-sol gpt-5.6-terra gpt-5.6-luna \
    gemini-3.1-pro-preview gemini-3.8-flash gemini-3.5-flash-lite \
  --budget-usd 100 --concurrency 10
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


## Anthropic funding and Fable inclusion

The user reported adding funds and raising provider limits, and explicitly requested inclusion of Fable. The current invocation was gracefully drained before resuming the same checkpoint with all eleven enabled catalog configurations. The existing run ID remains unchanged because it is part of immutable checkpoint identity; its `all-except-fable` suffix describes only the original selection, while `run.json` records the expanded invocation.

All four exact Anthropic model IDs appear in the authenticated Models API. Current [Claude model and pricing documentation](https://platform.claude.com/docs/en/models/overview) confirms Fable 5.1 supports image input and retains the catalog's standard $10/$50 input/output token rates. The cumulative campaign cap remains $25; the user changed provider funding/limits but has not selected a higher numeric benchmark spending ceiling.

The pre-resume checkpoint, final result hashes and original attempt IDs are captured for an independent preservation check. No final answer is eligible for remeasurement; prior billing failures remain in the attempt history and their conservative cost reservations remain in the cumulative guard.


### Anthropic retry outcome

The full eleven-model resume at `2026-09-08T21:49:05Z` still received HTTP 400 insufficient-credit responses for all four Claude models, including Fable. The runner paused Anthropic while OpenAI/Gemini progressed. A second graceful drain preserved 675 final observations. At `2026-09-08T21:51:56Z`, a bounded Claude-only retry (`--max-tasks 1 --concurrency 1`) again received the same credit error on Fable and stopped scheduling that provider. No Claude final observation was produced; no successful answer was retried.

Independent validation confirms all 559 pre-expansion final responses are byte-identical and all 562 original attempt IDs remain. The latest closed checkpoint contains 675 final observations and all billing failures, with $11.0935009 in cumulative estimated spending. This includes conservative unmetered reservations rather than confirmed charges for failed requests. See [run-01-claude-resume.json](evidence/run-01-claude-resume.json).

OpenAI/Gemini continue under the same run ID and $25 cumulative cap, selecting only their seven configurations until the Anthropic billing issue is resolved. All eleven registered models remain in the ledger and website records. Fable is now part of the authorized campaign and remains paused alongside the other three Claude models.

The [Anthropic API billing guide](https://support.claude.com/en/articles/8977456-how-do-i-pay-for-my-claude-api-usage) documents prepaid Console credits. The account backing the configured `ANTHROPIC_API_KEY` still receives the billing refusal; model-list access succeeds. The provider's status page lists an older credit-purchase delay resolved September 2, which does not establish a current incident or explain this account's failure.


### Additional user-requested Claude retry

At `2026-09-08T22:10:31.630073+00:00`, another bounded serial Claude retry received the same HTTP 400 insufficient-credit error on Fable. The provider pause prevented further Claude requests in that invocation; all four Claude models remain registered with zero final observations.

Independent verification confirmed all 1,514 prior final responses are byte-identical and all 1,528 prior attempt IDs remain. Exactly one failed attempt was added. SQLite integrity passes. The cumulative estimate is $23.3024662 against the unchanged $25 guard, including a $0.2548 conservative reservation for this unmetered failure, not a confirmed provider charge. See [run-01-claude-retry-2.json](evidence/run-01-claude-retry-2.json).

OpenAI/Gemini resume from this checkpoint under the same cap. Claude remains paused pending usable API credits; this retry does not change the frozen dataset or evaluation protocol.


### Cumulative cap raised to $50

The user explicitly authorized increasing the campaign ceiling to $50. The $25 invocation was gracefully drained at `2026-09-08T22:18:54.804932+00:00` with 1,597 final observations, 1,612 recorded attempts, and $24.4532358 in cumulative estimated spending. SQLite integrity passes and a preservation snapshot was taken before resuming.

Resume the seven OpenAI/Gemini configurations with `--budget-usd 50 --concurrency 10` under the same run ID. All prior costs count toward the new total ceiling. The four Claude configurations remain registered and paused after the latest API credit refusal. The local website refresh helper continues recording progress.


### Replacement Anthropic credential attempt

At `2026-09-08T22:20:23.380767+00:00`, a bounded serial retry used the replacement credential under the authorized $50 cumulative cap. Each of the four Claude models returned HTTP 400: the key is not scoped to a workspace and requires the `anthropic-workspace-id` header. The read-only List Workspaces request then returned HTTP 403, “Missing permissions.” Claude has no completed observations.

All 1,597 prior final responses and 1,612 prior attempt IDs remain unchanged. The closed checkpoint now contains 1,616 attempts and $24.8965158 in cumulative estimated spending, including conservative reservations for the four unmetered failures. SQLite integrity passes. See [run-01-cap50-new-key.json](evidence/run-01-cap50-new-key.json).

A workspace-scoped replacement key has been requested. [Anthropic authentication documentation](https://platform.claude.com/docs/en/manage-claude/authentication) confirms that these keys can omit the workspace header. No credential value is recorded in the repository. OpenAI/Gemini continue with the $50 cumulative cap and the existing versioned checkpoint.


### Anthropic workspace authentication support

The user supplied a workspace ID for the replacement credential. The V1.0.0 provider client sends the API key but has no workspace routing setting. Add the optional `ANTHROPIC_WORKSPACE_ID` runtime setting at the runner's client initialization boundary, before workers start, and record the workspace ID in invocation metadata. Keep all model configurations, inference bodies, prompt/schema/grading, frozen protocol sources, dataset files, and release identities unchanged.

Validation plan: reproduce the missing header offline; verify the header reaches only Anthropic, absent settings retain prior behavior, invalid IDs fail before client creation, and metadata contains the workspace ID but no API key. Run the runner/provider/release gates and independently compare request bodies with and without workspace routing. Then issue a bounded Claude retry under the $50 cumulative cap and resume the applicable models from the same checkpoint.

#### Workspace support validation

Base commit: `da4a6ea718c3a9377819d90101cd0db6824b5fdb`. The offline reproduction failed with `AssertionError: assert None == 'wrkspc_test123'`; invalid workspace input also constructed a client instead of failing preflight. [Verbatim Red evidence](evidence/run-01-workspace-red.txt) and [reversion evidence](evidence/run-01-workspace-reversion.txt) retain both failures. With the fix, all seven initial targeted cases pass; an eighth case additionally verifies offline runs ignore workspace settings.

| Gate | Result |
| --- | --- |
| `.venv/bin/python -m pytest -q` | 421 passed in 17.00s |
| `.venv/bin/python -m baseline.releases --release 1.0.0` | Passed; all 1,824 inputs and exact release identities |
| Independent offline request comparison | Identical request bodies/URLs; only Anthropic workspace header added |
| Read-only Models API with supplied workspace | HTTP 200; all four Claude IDs available |
| Simplification and code review | No issues; limited to the authentication header and invocation metadata |

The prior invocation drained at `2026-09-08T22:31:29.264469+00:00`, retaining 2,041 final observations and 2,060 attempts with $31.5235744 in cumulative estimated spending. [Gate details](evidence/run-01-workspace-gates.json) record the verification base. The bounded Claude retry will use workspace `wrkspc_01QaUFx97Qe9NkmYhy6hgLng` and the same $50 cumulative guard. Model-list access alone does not establish inference credit availability.

The runner sets account routing before starting any workers, with client cleanup already registered. The limited access to the frozen client's HTTP defaults keeps authentication setup outside the inference sources. API keys stay in process environment, while the non-secret workspace ID is recorded per invocation.

#### Workspace retry outcome

At `2026-09-08T22:35:18.265137+00:00`, the request using workspace `wrkspc_01QaUFx97Qe9NkmYhy6hgLng` received HTTP 400 insufficient credits. Workspace scoping is no longer the reported error. The first Fable failure paused the provider before the other three models were requested. All four Claude models still have zero completed observations.

Independent verification preserves all 2,041 prior final response hashes and 2,060 prior attempt IDs. The closed checkpoint now has 2,061 attempts, with $31.7783744 in cumulative estimated spending under the $50 cap. Its $0.2548 increase is a conservative reservation for the unmetered failed request, not a confirmed charge. SQLite integrity and all V1.0.0 release identities pass. [Retry evidence](evidence/run-01-workspace-retry.json) records the workspace and runner commit.

The workspace authentication fix is complete. The campaign continues with OpenAI/Gemini while Anthropic's credit error remains unresolved. The same run ID, successful observations, failed-attempt history, and cumulative cost guard are retained.


### Claude inference succeeds after account funding

The user reported funding the Claude Platform account and authorized another retry. At `2026-09-08T22:46:17.815142+00:00`, all four Claude models, including Fable, returned valid, metered benchmark responses using the previously supplied key and workspace. The conditionally supplied fallback credential was not needed.

Independent preservation checks retain every one of the 2,439 prior final responses and 2,459 prior attempt IDs. The closed checkpoint contains 2,443 completed observations and 2,463 attempts. All four new Claude responses have no provider or schema error and include input/output token usage. SQLite integrity and V1.0.0 release identities pass. [Success evidence](evidence/run-01-claude-funded-success.json) records the outcome without credentials.

Cumulative estimated spending is $37.8790802 against the authorized $50 cap. Resume all eleven enabled model configurations under the same run ID and guard; prior completed measurements remain final and all historical failed-attempt costs remain in the ledger. Anthropic's billing blocker is resolved for the tested requests. The local website refresh helper continues updating progress.


### Cumulative cap raised to $100

The user authorized increasing the campaign ceiling to $100 if the $50 guard was reached. The runner is resuming with that total ceiling so it can continue across $50 without another intervention. All previous attempts count toward the $100 maximum.

The $50 invocation drained at `2026-09-08T22:54:03.256565+00:00`, preserving 3,644 completed observations and 3,664 attempts with $47.2365062 in cumulative estimated spending. SQLite integrity passes. The preservation snapshot precedes the new invocation, which selects all eleven enabled configurations with `--budget-usd 100 --concurrency 10`. The supplied Anthropic key and workspace remain in use; the fallback key has not been used.

The local website monitor continues refreshing the versioned ledger. Claude is catching up with previously completed OpenAI/Gemini observations; all selected models remain eligible for their missing inputs.


### $100 campaign checkpoint

The runner exited after its budget guard stopped further scheduling at `2026-09-09T00:05:16.479947+00:00`. The final closed checkpoint contains 8,102 completed observations and 8,122 attempts, with $99.99190145 in cumulative estimated spending. All eleven configurations share 728 completed inputs; individual coverage differs slightly as inexpensive requests continued within the remaining cap.

Independent offline rescoring re-parsed all 8,102 raw responses and recomputed every dimension, exact match, and composite against the frozen V1.0.0 labels: zero discrepancies and zero current response errors. The 20 historical infrastructure failures remain in the attempt ledger and are excluded from output-accuracy scores. SQLite integrity and release identities pass.

This checkpoint was subsequently sealed for the accepted compact shared sample. The final publication and delivery are recorded in `publish-01-v1-results`; no spending above $100 was needed or incurred.

## Closure — 2026-09-09

Completed through [FontBench PR #1](https://github.com/eob/fontbench/pull/1), merge `23a25545952a2415e8c3da7a31d337c0457bf43c`. All eleven configurations, including Fable, have 728 shared final measurements; all 8,102 retained responses and 8,122 historical attempts are preserved. No current provider or malformed-response error remains. The final cumulative estimate is $99.99190145. Results are live at [edwardbenson.com/benchmarks/fontbench](https://edwardbenson.com/benchmarks/fontbench), using exact match and separate attribute accuracies. Later campaigns require new run IDs and cannot mutate this seal.
