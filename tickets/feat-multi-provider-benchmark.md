# Multi-provider benchmark, resumable execution, and visual results page

- Status: Implemented and validated; live run stopped cleanly at its spending guard
- Branch: fix-repo-audit
- Base: 080ac96
- Harness: Codex

## Requested outcome

Configure no more than five models per vendor, including the best Anthropic, OpenAI, and Google vision models; run the benchmark with credit-exhaustion recovery and later model additions. Build a benchmark page with H3 breakdowns and actual input montages, including a three-row landscape overview.

## Plan

1. Verify public model IDs, account availability, modalities, and prices; record source/date in config/models.json.
2. Add native provider image requests with structured outputs, error classification, and token accounting.
3. Checkpoint every attempted task in SQLite; preserve final results across restarts and additions; fingerprint images and inference configuration.
4. Run a representative model matrix on the frozen 639 supported samples with a default cumulative estimated cap of $25 unless user specifies another limit.
5. Build static site/index.html with embedded-source SVG contact sheets and honest partial/completed result counts.
6. Run unit/integration/browser checks, inspect the page, and record run state plus exact resume commands.

## Initial absence evidence

The repository's runner used only a Gemini client and kept results in memory until all tasks finished. There was no native OpenAI/Anthropic adapter, model matrix, checkpoint ledger, resumable CLI, or web page. New runner import regression failed before implementation; provider and persistence tests capture their own causal failures.

## Model selection

Authenticated, read-only model lists exposed all 12 initial IDs; no inference calls were made during catalog verification. Live inference on September 7, 2026 returned HTTP 404 for Gemini 2.5 Flash-Lite, stating that it is unavailable to new users and recommending Gemini 3.5 Flash-Lite. The older entry is retained but disabled. The active catalog now contains 11 models: four Anthropic, four OpenAI, and three Google. Sources and rate notes are in config/models.json and /tmp/fontbench-model-catalog.md.

## Data

Fresh corrected rendering: results/runs/fontbench-2026-09-07/input/manifest.json (639 images, 50 families). The original working dataset remains unchanged.

## Implemented behavior

- Native HTTP clients for Anthropic Messages, OpenAI Responses, and Google generateContent send the same image and six-field task. Structured output constraints, usage accounting, and redacted error records are tested with local transports.
- SQLite stores every completed attempt with a separate final-result index. Credit, authentication, and rate failures pause the provider; other infrastructure failures pause the model. Invalid model output is a final zero-score datapoint, so repeated sampling cannot silently inflate scores.
- Resuming skips final results. New model selections preserve older model summaries. A run refuses changed images, labels, or registered model configuration. Concurrent processes cannot duplicate a run's requests.
- Seeded cohorts use canonical task-ID order, so reordering a manifest does not change a limited run's sample selection. Capped resumes reject unknown historical costs, including failed attempts hidden by later successful retries.
- Existing scorecards or summaries without their SQLite checkpoint cause a preflight refusal. Restoring a checkout without its checkpoint cannot silently overwrite paid results or start duplicate work.
- SIGINT and SIGTERM stop scheduling, drain outstanding requests, and checkpoint their responses. A live controlled SIGINT saved 17 final results; the next invocation reused all 17 with no repeated requests for those pairs.
- The spending guard is cumulative across resumes. It reserves capacity for two requests before scheduling and conservatively charges unmetered attempts against the guard. Reported dollars are estimates, not provider invoices.
- The static page embeds actual PNGs in seven SVG contact sheets: a balanced 3×8 overview plus category, weight, modifier, letter spacing, line height, and font-family sections with H3 headings. Weight and spacing progress in natural visual order. Every metric cell includes its measured sample count.
- The page validates dataset, grading, model, and mock provenance; partial runs are identified explicitly and are not presented as final rankings.

## Operational evidence and limits

Anthropic returned an actual insufficient-credit error during the pilot. Its remaining tasks were paused, while seven available OpenAI and Google models returned metered results. Gemini 2.5 Flash-Lite's unavailable response remains in the ledger even though that catalog entry is now disabled.

The first tool-managed pilot process was externally terminated with SIGTERM before graceful TERM handling was added. Already committed results survived. A response received by a provider but not locally committed can still require a remote retry after a hard kill; SQLite cannot make a transaction atomic across a provider API. The resumed campaign runs in a detached local process, with graceful interrupt handling enabled.

HTTP timeouts measure inactivity per operation, not an overall wall-clock deadline. Interruptions drain submitted requests. Spending reservations assume the benchmark's small images and configured output caps; the guard is not a provider-enforced billing limit for arbitrary inputs.

## Resume and rebuild

After adding Anthropic credits, use the same frozen dataset and run ID. Increase the cumulative budget to allow further work after budget exhaustion:

```bash
bun run benchmark --manifest results/runs/fontbench-2026-09-07/input/manifest.json --run-id fontbench-2026-09-07 --budget-usd 50
bun run build:page --manifest results/runs/fontbench-2026-09-07/input/manifest.json --results-dir results/runs/fontbench-2026-09-07 --output-dir site
```

The example authorizes a total estimated $50 across all attempts in this run, not an additional $50. This run's frozen `input/` and completed `state.sqlite3` checkpoint are versioned; commit the updated checkpoint and reports together after extending it. Other runs' input caches and checkpoints remain ignored by default and need separate backups. Add an enabled catalog entry and select its ID with `--models` to contribute another model without repeating existing final datapoints.

## Final implementation validation

- Full Python suite: 196 passed. Runner/store subset: 40 passed, including credit pauses, interruption draining, concurrency exclusion, cohort stability, new-model additions, missing-checkpoint protection, and historical cost guards.
- Bun: 27 passed; TypeScript checking passed. Source was unchanged after that gate.
- Wheel build passed; installed wheel modules and CLI were exercised outside the repository.
- Desktop and mobile browser checks passed. Six H3 sections, metric switching, actual PNG embeds, natural axis ordering, and no page-wide horizontal overflow were verified.
- The 24 overview tiles use distinct families; category counts are 4–6, weight counts 5–7, modifier counts 4–5, and both spacing axes have exactly eight samples per level.
- Dependency audits are clean after updating the local environment's bootstrap setuptools. All 1,001 pre-existing changed/untracked dataset files retain their original SHA256 hashes.
- Simplification review kept one checkpoint path for normal completion and interruption draining, one native provider boundary, and a static report without an added frontend framework.

## Live outcome

The September 7 run stopped cleanly with 2,216 completed model–input pairs, 2,222 recorded evaluation attempts, and $24.988759 in cumulative estimated spending against the $25 guard. All models remain partial on the 639-input dataset. Anthropic paused for insufficient credits; Gemini 3.5 Flash-Lite and 3.8 Flash paused for repeated service/read timeouts. The remaining models stopped when their next conservative reservation could not fit the budget.

The frozen page includes all 11 active configurations and all 2,216 completed pairs, with no provenance warnings. Final database integrity and preservation checks passed. Counts, states, and exact resume commands are in [the run notes](../results/runs/fontbench-2026-09-07/README.md).

## Committed recovery snapshot

The frozen input images and standalone SQLite checkpoint are included in the repository with the code, reports, and page. Restoring the staged Git tree into a separate directory retained all 2,216 completed results and the $24.988759 estimated ledger total; a zero-task resume made no API calls. Environments, caches, credentials, locks, and SQLite sidecars remain excluded.
