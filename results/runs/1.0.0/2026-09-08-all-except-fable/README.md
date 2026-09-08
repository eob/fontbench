# V1.0.0 first multi-provider campaign

Status: **interrupted**. Last checkpoint: `2026-09-08T22:18:54.804932+00:00`.

**1,597 / 20,064 final observations**; cumulative estimated spend **$24.453236** against a **$25** guard.

The campaign includes all enabled Claude, OpenAI, and Gemini configurations, including Fable added on resume. The original run ID is retained to preserve checkpoints and history; its name describes the initial selection. Current provider issues appear below.

| Model | Completed / 1,824 | State | Estimated USD |
| --- | ---: | --- | ---: |
| claude-fable-5-1 | 0 | paused | 1.274000 |
| claude-haiku-4-5-20251001 | 0 | paused | 0.030360 |
| claude-opus-5 | 0 | paused | 0.509600 |
| claude-sonnet-5 | 0 | paused | 0.152880 |
| gemini-3.1-pro-preview | 228 | paused | 3.560440 |
| gemini-3.5-flash-lite | 228 | paused | 0.132798 |
| gemini-3.8-flash | 228 | paused | 2.724868 |
| gpt-5.6-luna | 228 | paused | 0.217607 |
| gpt-5.6-sol | 228 | paused | 4.095852 |
| gpt-5.6-terra | 228 | paused | 1.453710 |
| gpt-6-astra | 229 | paused | 10.301120 |

## Recorded provider issues

- HTTP 400: Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.
- Interrupted; resume to continue

## Provenance and recovery

Frozen release: [1.0.0](../../../../releases/1.0.0.json). Dataset Git commit: `d69e87e2c206ea75c52f5b8340d677bd14af03e3`.

[run.json](run.json) preserves invocation history, exact model configurations and release/code identities. [summary.json](summary.json) is the current machine-readable state; [attempts.jsonl](attempts.jsonl) retains all attempts and estimated costs, including conservative reservations for unmetered failures. These estimates are not provider invoices.

Resume the same run ID to reuse all completed final observations. Invalid model outputs remain final zero-credit measurements; infrastructure failures are retryable. Restore missing or inconsistent checkpoint/history files before resuming.

While the runner is active, keep SQLite WAL/SHM sidecars with the checkpoint. Commit the closed checkpoint and all JSON/JSONL exports together after the process finishes or gracefully drains.

[Campaign ticket](../../../../tickets/run-01-v1-model-campaign.md). The local website refresh helper rebuilds `site/` about once per minute while the campaign runs and once when it stops.

Latest website refresh exit status: `0`.
