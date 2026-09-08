# FontBench V1.0.0 run log

Release: [1.0.0](../../../releases/1.0.0.json). Frozen dataset Git commit: `d69e87e2c206ea75c52f5b8340d677bd14af03e3`.

The first live campaign is [2026-09-08-all-except-fable](2026-09-08-all-except-fable/README.md). Its checkpoints record current progress. Each future campaign belongs in its own `<run-id>/` directory here, with `run.json`, the closed SQLite checkpoint, attempt log, summary, and scorecards committed together. Different models and dates can contribute independently.

Follow [the run guide](../../README.md), then rebuild the website with:

```bash
bun run build:page --release 1.0.0 --results-dir results/runs --output-dir site
```
