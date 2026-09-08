# September 7, 2026 historical comparison — invalid for final benchmark use

The September 8 audit found two single-line inputs, remaining font-evidence conflicts, 21 synthetic italics, and a width-only shortcut that predicts 578/639 line-height labels. These results are retained for historical inspection. Use [FontBench V1.0.0](../../../releases/1.0.0.json) and grading version 3 for final measurements; the current live runner rejects this old dataset. See [the validity tickets](../../../tickets/README.md).

The run stopped cleanly at its cumulative $25 spending guard with **2,216 completed model–input pairs** and 2,222 recorded evaluation attempts. Estimated spending is **$24.988759**, including conservative reservations for unmetered requests. This is not a provider invoice.

The historical dataset contains 639 inputs across 50 font families, using grading version 2. No model has completed the full dataset; these partial samples should not be treated as final rankings.

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

## Preserved recovery evidence

The frozen `input/` directory and `state.sqlite3` checkpoint preserve all recorded responses and costs. Do not copy these datapoints into the new benchmark or change their frozen inputs. The current evaluator uses a different prompt, grading version, and protocol fingerprint and intentionally refuses to resume this campaign.

Historical execution instructions and implementation details remain in Git at commit `14e792f`. The current benchmark page previews the replacement corpus. This run's checkpoint can still be inspected with SQLite without making provider requests.

Dataset fingerprint: `b2dbd988d5c5c9c8cfdce397c2346531e9623e90e8752046ebaea3df142f6df8`.

Finalized 2026-09-07T15:50:46.326947+00:00. Local database integrity, page/model provenance, and preservation of all 1,001 pre-existing dataset changes were verified. See [implementation notes](../../../tickets/feat-multi-provider-benchmark.md) and [audit findings](../../../tickets/fix-repo-audit.md).
