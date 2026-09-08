# Dataset generations

Use **`fontbench-2-rendered/manifest.json`** for evaluation and **`fontbench-2/tasks`** for Harbor.

The accepted compact corpus contains 1,824 samples across 50 families. Every input has 2–5 measured visible lines. Its [validation report](fontbench-2-rendered/validation.json) records zero errors, 129 independently checked font binaries, no duplicate images, all class distributions, and the census of 1,176 omitted candidates. Each tracking, line-height, and width level occurs 608 times.

Run `bun run validate:dataset` from the repository root before final evaluation. Keep the manifest, catalog, skipped census, font lock, font binaries, and PNGs together. Rendering protocol 2 and grading version 3 are required; use a new run ID for the final campaign.

`rendered/` and `fontbench-1/` retain the original 1,000 historical samples. The separate September 7 run retains 639 later historical samples. Both generations have known validity defects and are rejected by the current live release gate. Existing scores cannot be reused for FontBench-2.

The compact recipe design samples the typography space and intentionally retains some conditional factor correlations. It does not claim exhaustive coverage or independent causal measurement of each attribute. See the [audit tickets](../tickets/README.md).
