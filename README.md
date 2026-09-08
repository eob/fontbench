# FontBench

FontBench measures recognition of six typographic properties from an image: font family, category, weight, modifier, letter spacing (`kerning`), and line height. Every input uses the same pangram with a mandatory break after “fox”; narrow cards can wrap further. Each input must contain at least two visible lines.

The September 8 validity audit found single-line samples, conflicting font evidence, layout shortcuts, permissive grading, and task metadata that exposed answers. The repairs and verification evidence are cataloged in [tickets/README.md](tickets/README.md). Both the original 1,000-image dataset and the September 7 639-image comparison are historical, unsuitable for final benchmark scores. Their files and paid checkpoints are preserved.

The current rendering protocol is **2**, with grading version **3**. Final evaluation requires the new validated inputs and a new run ID. [The benchmark page](site/index.html) previews the current inputs; model scores appear only after compatible runs have been performed.

## Setup

Requires Bun, Python 3.10+, and Chromium. Initial font acquisition requires network access; retained font assets support subsequent rendering without provider downloads.

```bash
bun install --frozen-lockfile
bunx playwright install chromium
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

On Linux, `bunx playwright install --with-deps chromium` can install browser system dependencies.

## Validate and package the inputs

```bash
bun run render
bun run validate:dataset
bun run build:harbor
# Or all three:
bun run build:all
```

Rendering writes `dataset/fontbench-2-rendered`. Packaging writes `dataset/fontbench-2`, using opaque task identifiers and generic metadata. Old datasets remain in their original directories.

The renderer checks internal font family, native weight range and style, and the fonts Chromium actually uses. It omits unsupported faces and records each exclusion. It forbids synthetic italic and weight; synthetic small caps are permitted only when they visibly change the image. Font binaries and stylesheets are retained with SHA256 hashes in the rendering directory. Re-rendering that directory reuses its pinned assets.

The release gate independently decodes every image and parses every retained font binary. It checks hashes, visible text, line geometry, CSS settings, duplicate pixels, font identity, and complete accounting of every rendered or skipped candidate. It emits a failing exit status for missing or inconsistent evidence. Live evaluation and the packaging CLI require this gate to pass.

```bash
.venv/bin/python -m baseline.validate_dataset \
  --manifest dataset/fontbench-2-rendered/manifest.json \
  --output dataset/fontbench-2-rendered/validation.json
```

Keep `manifest.json`, `catalog.json`, `skipped.json`, `fonts.lock.json`, PNGs, and the `fonts/` directory together. A manifest alone does not establish validity. Source fonts retain their providers' licenses; local font acquisition and any later redistribution are separate matters.

## What the benchmark measures

The catalog has 50 candidate families and 60 recipes per family: four weights × five modifiers × three layout repeats. Each supported face/modifier combination samples all three tracking, line-height, and width levels. Recipes rotate these levels to remove the previous deterministic layout shortcuts. Unsupported faces are excluded rather than labeled with the requested style; actual family and class counts are published in the validation report.

The shared [prompt](baseline/prompt.txt) defines the labels for every provider and Harbor task:

| Dimension | Labels and definition |
| --- | --- |
| Font | Complete canonical family or an explicitly declared spelling alias |
| Category | `serif`, `non-serif`, `mono`, `handwriting`, `other`, following the published catalog |
| Weight | `thin` = 200, `regular` = 400, `bold` = 700, `black` = 900 |
| Modifier | `regular`, native `italic`, `underline`, `strikethrough`, `small-caps` |
| Letter spacing | `tight` = −0.05em, `normal` = 0em, `loose` = 0.12em |
| Line height | `tight` = 1.15, `normal` = 1.45, `loose` = 1.9 times the 22px font size |

`thin` is this benchmark's name for the numeric 200 bucket. `kerning` means uniform tracking, not adjustment of individual letter pairs. Category is an annotation policy; it is partly predictable from font identity. A family can contribute fewer tasks because it supplies fewer supported faces, so sample-weighted results do not imply equal family weighting.

This is a fixed-text, fixed-renderer typography recognition benchmark. Passing integrity checks establishes consistency of this corpus; it does not prove generalization to arbitrary text, sizes, browsers, languages, or unseen fonts. Inspect the contact sheets and per-family results alongside aggregate scores.

## Evaluate models

[`config/models.json`](config/models.json) records model IDs, inference settings, rates, and their source dates. Set the relevant `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `GEMINI_API_KEY`. Model availability and prices should be rechecked before the final campaign.

Start with an offline smoke test:

```bash
bun run benchmark --mock --manifest dataset/fontbench-2-rendered/manifest.json \
  --run-id smoke --max-tasks 3
```

For a live run, the following command authorizes up to the runner's cumulative estimated $25 guard:

```bash
bun run benchmark --manifest dataset/fontbench-2-rendered/manifest.json \
  --run-id fontbench-2-final --budget-usd 25
```

The audit itself makes no paid inference calls. The guard is an estimate based on configured rates and conservative reservations, not a provider invoice or provider-enforced limit.

The runner checkpoints each attempt in `results/runs/<run-id>/state.sqlite3`, shuffles inputs reproducibly, and cycles across models. Resume with the same command and inputs. `--models ID [ID ...]` selects models; `--max-tasks N` selects a reproducible subset that can be extended later; `--concurrency N` controls simultaneous requests. Raising the cumulative budget allows additional work. Preserve the database and frozen inputs when backing up a run.

Completed answers and malformed model outputs are final datapoints. Malformed outputs receive zero; infrastructure failures remain retryable and appear in error counts. Exact match requires all six correct fields; the composite is their equal-weight mean. Extra fields, duplicate JSON keys, missing fields, and invalid enum values invalidate the whole prediction.

Changed images, labels, prompts, grading code, provider protocol, or existing model settings require a new run ID. A run refuses changed provenance and missing checkpoints before issuing requests. Historical version 2 grading results cannot resume into version 3 or be copied into its reports.

## Reports and Harbor

```bash
bun run build:page --manifest dataset/fontbench-2-rendered/manifest.json \
  --results-dir results/runs/fontbench-2-final --output-dir site
python3 -m http.server 8000 --directory site
```

The page shows real input contact sheets, dataset validation status, per-dimension counts, completion status, and scores on shared task cohorts. Partial samples are not final rankings. The exporter recomputes metrics from validated task rows and compares only matching dataset, protocol, and cohort identities. Rebuild the page after extending a run.

Install Harbor separately in the Python environment, then use:

```bash
harbor run -p dataset/fontbench-2/tasks \
  --agent baseline.harbor_agent:BaselineVLMAgent --model YOUR_MODEL_ID
```

Answers are confined to verifier and oracle files; instructions, task names, and public tags do not identify the target family or labels. The verifier writes its reward to `/logs/verifier/reward.txt`. This does not sandbox a malicious host-side adapter that can access verifier files.

## Development checks

```bash
bun run test
# Python tests, local-fixture browser tests, and TypeScript checking.
```

Browser tests do not need font-provider access or API keys. The Python wheel contains the shared prompt and validation tools. Repository code is MIT licensed; see [LICENSE](LICENSE).
