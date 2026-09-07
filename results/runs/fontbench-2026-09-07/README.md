# September 7, 2026 live comparison — partial

The run stopped cleanly at its cumulative $25 spending guard with **2,216 completed model–input pairs** and 2,222 recorded evaluation attempts. Estimated spending is **$24.988759**, including conservative reservations for unmetered requests. This is not a provider invoice.

The frozen corrected dataset contains 639 inputs across 50 font families, using grading version 2. No model has completed the full dataset; these partial samples should not be treated as final rankings.

| Model | Completed / 639 | State | Estimated USD |
| --- | ---: | --- | ---: |
| Claude Fable 5.1 | 0 | paused | 0.2548 |
| Claude Haiku 4.5 | 0 | paused | 0.0000 |
| Claude Opus 5 | 0 | paused | 0.1274 |
| Claude Sonnet 5 | 0 | paused | 0.0510 |
| Gemini 2.5 Flash-Lite (disabled) | 0 | paused | 0.0009 |
| Gemini 3.1 Pro Preview | 329 | budget exhausted | 3.5005 |
| Gemini 3.5 Flash-Lite | 162 | paused | 0.1044 |
| Gemini 3.8 Flash | 288 | paused | 2.7185 |
| GPT-5.6 Luna | 473 | budget exhausted | 0.3434 |
| GPT-5.6 Sol | 322 | budget exhausted | 3.8513 |
| GPT-5.6 Terra | 330 | budget exhausted | 1.7293 |
| GPT-6 Astra | 312 | budget exhausted | 12.3073 |

Anthropic has insufficient credits. Gemini 3.5 Flash-Lite paused after repeated HTTP 503 deadline failures; Gemini 3.8 Flash paused after read timeouts. Their completed results are retained, and infrastructure failures are retryable. Gemini 2.5 Flash-Lite rejected inference as unavailable to new users and is disabled in the active catalog.

All 11 active models appear on the [benchmark page](../../../site/index.html), including pending Anthropic rows. The page includes a balanced three-row montage and six H3 breakdowns made from the real inputs. Its data passed provenance validation against this run.

## Resume after adding credits

```bash
bun run benchmark --manifest results/runs/fontbench-2026-09-07/input/manifest.json --run-id fontbench-2026-09-07 --budget-usd 50
bun run build:page --manifest results/runs/fontbench-2026-09-07/input/manifest.json --results-dir results/runs/fontbench-2026-09-07 --output-dir site
```

The example sets a cumulative $50 estimate for the entire run, including existing attempts. Select a model with `--models ID` to extend only that model. Add an enabled configuration entry to contribute another model; existing final results are reused. Preserve model settings and the frozen input images when resuming.

This run's frozen `input/` and completed `state.sqlite3` checkpoint are versioned so a checkout can resume. Commit the updated checkpoint and reports together after extending this run. Other runs' input caches and checkpoint files remain ignored by default and need separate backups. If reports remain but the checkpoint is missing, the runner refuses to overwrite them. Restore the checkpoint or use a new run ID. SIGINT/SIGTERM drain outstanding requests; a hard kill between remote processing and local commit can still require a remote retry.

Dataset fingerprint: `b2dbd988d5c5c9c8cfdce397c2346531e9623e90e8752046ebaea3df142f6df8`.

Finalized 2026-09-07T15:50:46.326947+00:00. Local database integrity, page/model provenance, and preservation of all 1,001 pre-existing dataset changes were verified. See [implementation notes](../../../tickets/feat-multi-provider-benchmark.md) and [audit findings](../../../tickets/fix-repo-audit.md).
