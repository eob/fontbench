# FontBench V1.0.0

FontBench measures recognition of six typographic properties from an image: font family, category, weight, modifier, letter spacing (`kerning`), and line height. **V1.0.0 freezes 1,824 images across 50 families**, with 2–5 visible lines per image, 129 verified font binaries, and zero validation errors.

The [release descriptor](releases/1.0.0.json) binds this version to dataset Git commit [`d69e87e2c206ea75c52f5b8340d677bd14af03e3`](https://github.com/eob/fontbench/commit/d69e87e2c206ea75c52f5b8340d677bd14af03e3), the dataset fingerprint, and the evaluation protocol fingerprint. [CHANGELOG.md](CHANGELOG.md) records the release; Git tag `v1.0.0` identifies its compatible tooling. The accepted files remain in `dataset/fontbench-2-rendered` and `dataset/fontbench-2`: these directory names predate public versioning and do not mean V2.

The original 1,000-image dataset and September 7 639-image pilot are **invalid historical prototypes**. Their inputs, paid checkpoints, and reports are preserved and labeled in the [dataset guide](dataset/README.md) and [historical result catalog](results/historical.json). The [ticket catalog](tickets/README.md) records the defects, repairs, and regression evidence.

## Setup and validate the release

Requires Bun 1.3.14, Python 3.10+, Git history containing the dataset commit, and Chromium for browser tests or candidate generation. CI uses this tested Bun version; review the [runtime regression evidence](tickets/evidence/publish-01-bun-runtime-gates.md) before upgrading it.

```bash
bun install --frozen-lockfile
bunx playwright install chromium
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
bun run validate:release
```

On Linux, `bunx playwright install --with-deps chromium` can install browser system dependencies. The release validator runs offline: it verifies committed manifest bytes, dataset and protocol fingerprints, and the independent all-image/font gate. Live runs require this gate before contacting a model.

## Run any supported vision model, now or later

Run an offline smoke check first:

```bash
bun run benchmark --release 1.0.0 --mock --run-id smoke --max-tasks 3
```

Select models from [`config/models.json`](config/models.json), or provide your own catalog with `--config path/to/models.json`. Native adapters support OpenAI Responses, Anthropic Messages, and Google generateContent; an OpenAI-compatible endpoint can use `base_url`. Set the API key environment variable specified by each configuration. Catalog IDs and prices are dated records; verify availability and rates when scheduling a new campaign.

Separate runs can contribute to the same release:

```bash
# Example: GPT in one campaign.
bun run benchmark --release 1.0.0 --run-id gpt-september \
  --models gpt-6-astra --budget-usd 25

# Example: Gemini in a later campaign.
bun run benchmark --release 1.0.0 --run-id gemini-later \
  --models gemini-3.1-pro-preview --budget-usd 25

# Rebuild the website from all compatible recorded runs.
bun run build:page --release 1.0.0 --results-dir results/runs --output-dir site
python3 -m http.server 8000 --directory site
```

These live commands make paid requests. The budget is a cumulative estimate for that run based on configured rates and conservative reservations, not a provider invoice or provider-enforced limit.

Each run writes to `results/runs/1.0.0/<run-id>/`. Its `run.json` records the release, full dataset Git hash, data/protocol fingerprints, model configurations, timestamps, and executing code commit/dirty state. `state.sqlite3` is the resumable checkpoint; `attempts.jsonl` retains every attempt; summaries and scorecards expose the scored observations. Commit a completed run directory to contribute it to this repository. The runner does not commit or push automatically. See the [run log guide](results/README.md) for the artifact layout and contribution workflow.

Repeat the same command to resume. `--max-tasks N` selects a reproducible subset that can be extended later; `--concurrency N` controls simultaneous requests. Omitting `--run-id` creates a unique run. New model IDs can be added in separate runs at any time. Changed inference settings need a new run ID and remain separate configurations on the website. Explicit `--manifest` runs are unversioned experiments and do not enter the release leaderboard.

The website combines complementary observations for the same provider/model/endpoint/output limit, keeps the earliest final observation for each input, and retains all contributing run records and attempt costs. Repeating a task cannot replace a lower score with a higher one. Mocks, incompatible releases, and malformed reports are excluded. Rankings use shared task cohorts; partial coverage is displayed explicitly.

Completed answers and malformed model outputs are final datapoints. Malformed outputs receive zero; infrastructure failures remain retryable and appear in error counts. The report leads with exact match: all six fields must be correct. It also shows the six individual attribute accuracies. Extra fields, duplicate JSON keys, missing fields, and invalid enum values invalidate the whole prediction.

## What the benchmark measures

Every input uses the same pangram with a mandatory break after “fox”; narrow cards can wrap further. The compact corpus samples the typographic space. It is not an exhaustive factorial design.

The catalog has 50 candidate families and 60 recipes per family: four weights × five modifiers × three layout repeats. Supported combinations sample all three tracking, line-height, and width levels. Unsupported native faces are excluded, with the reason retained for each skipped candidate. The [frozen validation report](dataset/fontbench-2-rendered/validation.json) publishes the actual counts.

The shared [prompt](baseline/prompt.txt) defines the labels for every provider and Harbor task:

| Dimension | Labels and definition |
| --- | --- |
| Font | Complete canonical family or an explicitly declared spelling alias |
| Category | `serif`, `non-serif`, `mono`, `handwriting`, `other`, following the published catalog |
| Weight | `thin` = 200, `regular` = 400, `bold` = 700, `black` = 900 |
| Modifier | `regular`, native `italic`, `underline`, `strikethrough`, `small-caps` |
| Letter spacing | `tight` = −0.05em, `normal` = 0em, `loose` = 0.12em |
| Line height | `tight` = 1.15, `normal` = 1.45, `loose` = 1.9 times the 22px font size |

`thin` names the numeric 200 bucket. `kerning` means uniform tracking, not adjustment of individual letter pairs. Category is an annotation policy and is partly predictable from font identity. Family counts differ with face availability, so sample-weighted scores do not imply equal family weighting.

Conditional correlations remain in the compact recipes. For example, knowing the recipe, modifier, and tracking can determine line height. This accepted sampling limit means the benchmark does not isolate independent causal effects. It also does not establish generalization to arbitrary text, sizes, browsers, languages, or unseen fonts. Inspect per-family results and input contact sheets alongside aggregate scores.

## Candidate generation and Harbor

The release inputs are already checked in. Generation commands create development candidates; they refuse to overwrite or overlap registered release directories.

```bash
bun run build:all
# render -> dataset/candidate-rendered
# validate candidate -> package -> dataset/candidate-harbor
```

The renderer verifies binary family, weight, style, and the fonts Chromium actually uses. It forbids synthetic italic/weight and accepts synthetic small caps only if they visibly change the image. It retains source font bytes, stylesheets, and hashes. Initial acquisition needs network access; pinned cache assets support subsequent offline replay to a separate destination.

The independent gate decodes every image and parses all 129 font binaries used by the release (139 assets are retained in total). It checks hashes, visible text, line geometry, CSS settings, duplicate pixels, font identity, and complete accounting of 3,000 rendered or skipped candidates. Keep `manifest.json`, `catalog.json`, `skipped.json`, `fonts.lock.json`, PNGs, and `fonts/` together. Changes to released inputs or evaluation behavior require a new release descriptor and version.

Install Harbor separately to use the frozen task package:

```bash
harbor run -p dataset/fontbench-2/tasks \
  --agent baseline.harbor_agent:BaselineVLMAgent --model YOUR_MODEL_ID
```

Instructions, opaque task names, and public tags do not reveal the answers. The verifier writes `/logs/verifier/reward.txt`; it does not sandbox a malicious host-side adapter with access to verifier files. Harbor's own run output is separate from the versioned model ledger; use `bun run benchmark` for website contributions.

## Development checks

```bash
bun run test
bun run validate:release
```

The checks cover Python, local-fixture browser tests, TypeScript, and frozen release integrity. Browser tests need no provider access or API keys. Repository code is MIT licensed; source fonts retain their providers' licenses. See [LICENSE](LICENSE).
