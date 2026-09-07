# FontBench

FontBench evaluates visual identification of six typographic properties: font family, category, weight, modifier, letter spacing (`kerning`), and line height. Each task presents a high-DPI image of “The quick brown fox jumps over the lazy dog.” and requests a JSON prediction.

The catalog defines 50 font families and 20 recipes per family, using container widths of 220, 320, and 440 CSS pixels. Rendering produces up to 1,000 tasks; recipes whose weight or face is unavailable are skipped. The generated manifest records the actual task set. Supported variant counts differ by font; compare runs using the same frozen manifest and images.

The packaged dataset currently contains 1,000 historical samples. These images and the existing scorecards predate the rendering and grading corrections described in [the audit notes](tickets/fix-repo-audit.md). Re-render and re-evaluate before using them for new model comparisons.

The corrected September 7 comparison, frozen inputs, and resume commands are described in [the live run notes](results/runs/fontbench-2026-09-07/README.md). Open [the benchmark page](site/index.html) to explore its partial measurements and input montages.

## Setup

Requires Bun and Python 3.10 or newer. Rendering also requires Chromium, its system dependencies, and network access to the configured font providers.

```bash
bun install --frozen-lockfile
bunx playwright install chromium
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

On Linux, `bunx playwright install --with-deps chromium` also installs browser system dependencies and may require administrator privileges.

## Render and package a dataset

```bash
bun run render
bun run build:harbor
# Or run both:
bun run build:all
```

The renderer waits for each font variant to load and checks the fonts actually used by Chromium. It rejects fallback rendering and records loaded face information. Unsupported weights or faces are skipped; synthetic styling is recorded where used. Fonts are fetched from external providers, so the source files and available variants can change over time.

By default, rendering writes to `dataset/rendered` and packaging writes to `dataset/fontbench-1`. To keep an existing dataset intact, use separate directories:

```bash
bun -e 'import {renderAllSamples} from "./src/render"; await renderAllSamples("/tmp/fontbench-rendered")'
bun -e 'import {buildHarborDataset} from "./src/generate_harbor_dataset"; buildHarborDataset("/tmp/fontbench-rendered", "/tmp/fontbench-dataset")'
```

The generator uses the manifest as the source of truth. It validates input images, removes stale generated tasks, and keeps answers in the verifier and oracle files. Instructions describe the output schema without revealing the answers.

## Run a resumable model comparison

[`config/models.json`](config/models.json) enables 11 models: four Anthropic, four OpenAI, and three Google models, with exact API IDs, documented rates, output caps, and source links. Gemini 2.5 Flash-Lite remains recorded but disabled after live inference returned HTTP 404 for this account on September 7, 2026. Configure `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and `GEMINI_API_KEY` in the environment. Keys are never stored in run files.

Freeze a corrected rendering in its own directory, then start the matrix:

```bash
bun -e 'import {renderAllSamples} from "./src/render"; await renderAllSamples("dataset/validated-rendered")'
bun run benchmark --manifest dataset/validated-rendered/manifest.json --run-id comparison --budget-usd 25
```

The runner shuffles samples reproducibly and cycles across models. It checkpoints each finished attempt in `results/runs/comparison/state.sqlite3` and writes scorecards plus `summary.json`. Infrastructure errors pause the affected provider or model. Valid answers and malformed model responses are final results; malformed answers score zero. Credit, network, or authentication failures remain retryable.

Run the same command after adding credits. Completed datapoints are reused. The budget is cumulative for the run; increase `--budget-usd` to authorize more work. `--no-budget-limit` removes the runner's spending guard. The guard uses documented rates and conservative reservations for unmetered requests, so reported spending is an estimate rather than an invoice.

A cumulative spending limit cannot be applied to a run with unresolved historical costs, including earlier unpriced attempts. The runner rejects that combination before making new requests.

To add a model later, add a configuration entry and rerun. Existing model configurations and the image/label fingerprint must stay the same; use a new run ID for a changed dataset or changed inference settings. `--models ID [ID ...]` selects models; `--max-tasks N` performs a reproducible subset that can be extended later. `--concurrency N` controls simultaneous requests. Keep the SQLite file as well as the input images to resume. An abrupt process or machine failure between a provider response and its local commit can still require one remote retry.

If scorecards remain but the checkpoint database is missing, the runner stops before making requests or overwriting reports. Restore the database from backup or choose a new run ID.

For an offline smoke test:

```bash
bun run benchmark --mock --manifest dataset/validated-rendered/manifest.json --run-id smoke --max-tasks 3
```

Mock runs use separate directories and never enter live comparisons. The original single-model Gemini CLI remains available as `fontbench --mock --limit 6` or `python -m baseline.cli`.

Each prediction has this shape:

```json
{
  "font": "<font family>",
  "category": "<serif|non-serif|mono|handwriting|other>",
  "weight": "<thin|regular|bold|black>",
  "modifier": "<regular|italic|underline|strikethrough|small-caps>",
  "kerning": "<tight|normal|loose>",
  "line_height": "<tight|normal|loose>"
}
```

Each dimension contributes one sixth of the composite score. Font matching ignores case and punctuation but requires a complete canonical name or declared alias. Other dimensions require a listed value. Exact match requires all six dimensions to be correct. The `kerning` field describes CSS letter spacing (tracking), rather than changes to individual kerning pairs.

## Build the benchmark page

```bash
bun run build:page --manifest dataset/validated-rendered/manifest.json --results-dir results/runs/comparison --output-dir site
python3 -m http.server 8000 --directory site
```

Open `http://localhost:8000`. The page uses real dataset images in its overview and H3 breakdown contact sheets. Results show sample counts and completion status, and mismatched dataset fingerprints are excluded. Rebuild the page after resuming a run or adding a model.

See [results/README.md](results/README.md) for the status of checked-in historical results.

## Run with Harbor

Install Harbor separately in the same Python environment. The adapter uses Harbor’s asynchronous environment download/upload methods to read `/workspace/sample.png` and write `/workspace/output.json`.

```bash
harbor run \
  -p dataset/fontbench-1/tasks \
  --agent baseline.harbor_agent:BaselineVLMAgent \
  --model YOUR_MODEL_ID
```

The verifier writes a reward between 0 and 1 to `/logs/verifier/reward.txt`. It can also be run locally with `HARBOR_LOGS_DIR` selecting a writable log directory.

## Validation

```bash
bun run test
# Individual checks:
bun run test:python
bun run test:ts
bun run typecheck
```

The tests cover dataset integrity, strict grading, malformed predictions, mock evaluation, report generation, font loading, and the Harbor adapter. Browser tests use local fixtures and require the Chromium installation above; they do not need font-provider access or API keys.

## Repository layout

- `src/fonts.ts`: font catalog and rendering recipes.
- `src/render.ts`: Chromium renderer and manifest format.
- `src/generate_harbor_dataset.ts`: Harbor task generator and verifier template.
- `baseline/`: provider clients, evaluator, durable runner, page builder, exporter, and Harbor adapter.
- `config/models.json`: verified model matrix and pricing sources.
- `site/`: generated static benchmark page and SVG input montages.
- `dataset/rendered/`: rendered images and manifest.
- `dataset/fontbench-1/tasks/`: packaged tasks, environments, verifiers, and oracle solutions.
- `tests/` and `src/*.test.ts`: Python and Bun tests.

## License

Repository code is MIT licensed; see [LICENSE](LICENSE). Font files come from the providers listed in the catalog and retain their respective licenses.
