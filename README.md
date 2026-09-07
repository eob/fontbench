# `fontbench`

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Format: Harbor](https://img.shields.io/badge/Benchmark-Harbor%201.0-orange.svg)](https://github.com/laude-institute/harbor)

**FontBench-1** is a benchmark for evaluating multimodal Vision-Language Models (VLMs) and agent harnesses on **fine-grained typographic discernment and visual font identification**.

While modern frontier models excel at transcription (OCR), they routinely fail at identifying the typeface itself—confusing *Arial* with *Roboto*, *Courier New* with *Outfit*, or *Helvetica* with *Segoe UI*. FontBench measures this capability directly.

---

## The Core Task: `[(Image, Prompt), (Font Name)]`

Each task presents an evaluation unit:
- **Input Image**: A high-DPI rasterization of the classic English pangram:
  > *"The quick brown fox jumps over the lazy dog."*
- **Prompt**:
  > *"Examine the rendered text in the provided image. Identify the primary font family used to typeset this text. Output only the canonical font name."*
- **Ground Truth Target**: Canonical font family name (e.g. `Arial`, `Times New Roman`, `Playfair Display`, `Courier New`).

### Why Narrow Width & Wrapping Matter
In a single horizontal line, models only observe isolated character glyphs. By rendering at **narrow container widths** (220px, 320px, 440px), the text is forced to wrap across 2 to 4 lines. This exposes:
1. **Vertical Metrics & Leading**: Interline clearance, line height, and line rhythm.
2. **Ascender/Descender Clashes**: Geometry between `b, d, f, h, k, l, t` and `g, j, p, q, y`.
3. **Tracking & Kerning**: Glyph advance widths and word spacing texture.

---

## Pilot Catalog (FontBench-1 Pilot)

The initial pilot spans 10 representative font families across 3 width variations (30 tasks total):

| Font Family | Classification | Distinctive Anatomical Tell-Tales |
|---|---|---|
| **Arial** | Neo-Grotesque Sans | Angled stroke terminals on `t`, `c`, `s`; curved leg on `R`. |
| **Helvetica** | Swiss Neo-Grotesque | Strictly horizontal terminals on `c`, `s`, `e`; uniform stroke weight. |
| **Times New Roman** | Transitional Serif | Sharp triangular serifs, high stroke contrast, narrow newsprint proportions. |
| **Georgia** | Digital Screen Serif | Broad proportions, open counters, distinctive ball terminals on `c`, `r`, `g`. |
| **Courier New** | Monospace Slab | Fixed-pitch typewriter proportions, flat slab serifs. |
| **Comic Sans MS** | Casual Script | Asymmetrical handwriting forms, informal stroke dynamics. |
| **Roboto** | Neo-Grotesque Sans | Dual-nature: mechanical geometric skeleton with friendly open curves. |
| **Inter** | Interface Sans | High x-height, square dot on `i` and `j`, optimized for digital screens. |
| **Playfair Display** | Didone Modern Serif | High contrast hairlines, delicate bracketless serifs, transitional italic influence. |
| **Montserrat** | Geometric Sans | Broad architectural capitals, geometric circular geometry. |

---

## Directory Structure

```text
fontbench/
├── dataset/
│   ├── rendered/                        # Rendered high-DPI PNGs & manifest.json
│   └── fontbench-1/                     # Canonical Harbor benchmark dataset
│       ├── dataset.toml
│       └── tasks/
│           ├── font-arial-narrow/
│           │   ├── task.toml            # Task metadata & timeouts
│           │   ├── instruction.md       # Agent instructions
│           │   ├── environment/         # Sandbox & sample.png
│           │   ├── solution/solve.sh    # Oracle solution
│           │   └── tests/test.sh        # Robust verifier & reward output
│           └── ... (30 tasks)
├── src/
│   ├── fonts.ts                         # Font definitions & CSS configurations
│   ├── render.ts                        # Playwright Chromium headless renderer
│   └── generate_harbor_dataset.ts       # Harbor packaging generator
├── baseline/
│   ├── evaluator.py                     # Zero-shot VLM evaluation engine
│   ├── cli.py                           # CLI benchmark runner
│   └── harbor_agent.py                  # Harbor BaseAgent compliant adapter
├── tests/
│   └── test_fontbench.py                # Pytest verification suite
├── package.json
└── pyproject.toml
```

---

## Quickstart

### 1. Prerequisites
- **Bun** (for Playwright renderer): [bun.sh](https://bun.sh)
- **Python 3.10+** (for baseline evaluation & verifiers)

```bash
git clone https://github.com/eob/fontbench.git
cd fontbench

# Install JS & Python dependencies
bun install
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Render Benchmark Samples
Render all 10 fonts across the 3 width variants using headless Chromium:

```bash
bun run render
```

### 3. Generate the Harbor Dataset
Compile the rendered images into the official Harbor task layout:

```bash
bun run build:harbor
```

---

## Running the Baseline Evaluator

### Standalone CLI
Run the baseline zero-shot VLM evaluation using Google Gemini (`gemini-2.5-flash` or `gemini-2.5-pro`):

```bash
export GEMINI_API_KEY="your-api-key"
python -m baseline.cli --model gemini-2.5-flash
```

Or test offline in mock mode:
```bash
python -m baseline.cli --mock
```

### Running with Harbor
Because FontBench-1 is fully packaged with standard Harbor task layouts (`task.toml`, `instruction.md`, `Dockerfile`, `solve.sh`, `test.sh`), you can run it directly with [Harbor](https://github.com/laude-institute/harbor):

```bash
harbor run \
  -d "dataset/fontbench-1" \
  --agent baseline.harbor_agent:BaselineVLMAgent \
  --ak model=gemini-2.5-flash
```

---

## Early Baseline Findings

In initial zero-shot pilot trials on `gemini-2.5-flash`:
- **Arial** was consistently misclassified as **`Roboto`** and **`Segoe UI`**.
- **Courier New** was misclassified as **`Outfit`**.
- **Comic Sans MS** was misclassified as **`Indie Flower`**.

This confirms that zero-shot VLMs lack the structured inspection ladders needed to disambiguate subtle typographic markers.

---

## Testing

Run the test suite to verify dataset integrity and verifier logic:

```bash
pytest tests/ -v
```

---

## License

MIT © Edward Benson
