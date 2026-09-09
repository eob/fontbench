# V1.0.0 first multi-provider campaign

Status: **budget_exhausted**. Last checkpoint: `2026-09-09T00:05:16.479947+00:00`.

**8,102 / 20,064 final observations**; cumulative estimated spend **$99.991901** against a **$100** guard.

The campaign includes all enabled Claude, OpenAI, and Gemini configurations, including Fable added on resume. The original run ID is retained to preserve checkpoints and history; its name describes the initial selection. Current provider issues appear below.

| Model | Completed / 1,824 | State | Estimated USD |
| --- | ---: | --- | ---: |
| claude-fable-5-1 | 728 | budget_exhausted | 14.434580 |
| claude-haiku-4-5-20251001 | 743 | budget_exhausted | 1.044965 |
| claude-opus-5 | 731 | budget_exhausted | 7.222810 |
| claude-sonnet-5 | 734 | budget_exhausted | 2.613030 |
| gemini-3.1-pro-preview | 734 | budget_exhausted | 12.464466 |
| gemini-3.5-flash-lite | 754 | budget_exhausted | 0.438957 |
| gemini-3.8-flash | 736 | budget_exhausted | 8.908375 |
| gpt-5.6-luna | 748 | budget_exhausted | 0.703283 |
| gpt-5.6-sol | 732 | budget_exhausted | 13.619300 |
| gpt-5.6-terra | 734 | budget_exhausted | 4.767556 |
| gpt-6-astra | 728 | budget_exhausted | 33.774580 |

## Recorded provider issues

- Increase --budget-usd to resume

## Provenance and recovery

Frozen release: [1.0.0](../../../../releases/1.0.0.json). Dataset Git commit: `d69e87e2c206ea75c52f5b8340d677bd14af03e3`.

[run.json](run.json) preserves invocation history, exact model configurations and release/code identities. [summary.json](summary.json) is the current machine-readable state; [attempts.jsonl](attempts.jsonl) retains all attempts and estimated costs, including conservative reservations for unmetered failures. These estimates are not provider invoices.

Resume the same run ID to reuse all completed final observations. Invalid model outputs remain final zero-credit measurements; infrastructure failures are retryable. Restore missing or inconsistent checkpoint/history files before resuming.

While the runner is active, keep SQLite WAL/SHM sidecars with the checkpoint. Commit the closed checkpoint and all JSON/JSONL exports together after the process finishes or gracefully drains.

[Campaign ticket](../../../../tickets/run-01-v1-model-campaign.md). The local website refresh helper rebuilds `site/` about once per minute while the campaign runs and once when it stops.

Latest website refresh exit status: `0`.
