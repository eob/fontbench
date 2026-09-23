# FontBench V1.0.0 run log

Release: [1.0.0](../../../releases/1.0.0.json). Frozen dataset Git commit: `d69e87e2c206ea75c52f5b8340d677bd14af03e3`.

The first live campaign is [2026-09-08-all-except-fable](2026-09-08-all-except-fable/README.md). Its checkpoints record current progress. Each future campaign belongs in its own `<run-id>/` directory here, with `run.json`, the closed SQLite checkpoint, attempt log, summary, and scorecards committed together. Different models and dates can contribute independently.

The [2026-09-23 OpenAI and Anthropic campaign](2026-09-23-openai-anthropic/final_results.json) seals a full-release comparison for GPT-6 Sol, GPT-6 Luna, and Claude Opus 5.5. Its 5,472 final responses cover all 1,824 inputs per model; the [seal](2026-09-23-openai-anthropic/finalization.json) verifies the committed source checkpoint.

Follow [the run guide](../../README.md), then rebuild the website with:

```bash
bun run build:page --release 1.0.0 --results-dir results/runs --output-dir site
```
