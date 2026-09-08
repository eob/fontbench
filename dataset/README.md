# Dataset releases

**FontBench V1.0.0** is the accepted release. Use `--release 1.0.0` when evaluating models or rebuilding the website. Its [descriptor](../releases/1.0.0.json) binds the data to Git commit `d69e87e2c206ea75c52f5b8340d677bd14af03e3` and the exact dataset/protocol fingerprints in the [changelog](../CHANGELOG.md).

| Directory | Classification |
| --- | --- |
| `fontbench-2-rendered/` | Frozen V1.0.0 inputs: 1,824 images, 50 families |
| `fontbench-2/` | Frozen V1.0.0 Harbor package |
| `candidate-rendered/`, `candidate-harbor/` | Unreleased development output; excluded from Git |
| `rendered/`, `fontbench-1/` | Invalid historical 1,000-image prototype |

The internal `fontbench-2` folder names predate public release naming and do not denote V2. The old `fontbench-1` folder is not V1.0.0.

Every accepted input has 2–5 measured visible lines. The [validation report](fontbench-2-rendered/validation.json) records zero errors, 129 independently checked fonts used by accepted samples, no duplicate images, all class distributions, and the census of 1,176 omitted candidates. All 139 downloaded font assets remain pinned for reproduction, including unsupported source faces. Each tracking, line-height, and width level occurs 608 times.

Run `bun run validate:release` to verify release identity and input integrity. Registered input/package directories are protected against generation overwrites. Keep the manifest, catalog, skipped census, font lock, source binaries, and PNGs together. Development generation writes the candidate directories; a changed accepted corpus needs a new public release descriptor.

The compact recipe design samples the typography space and retains documented conditional factor correlations. It does not claim exhaustive coverage or independent causal measurement of each attribute. See the [audit tickets](../tickets/README.md).
