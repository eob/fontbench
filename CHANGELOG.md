# FontBench changelog

## V1.0.0 — 2026-09-08

First named, frozen benchmark release. The accepted compact sample contains **1,824 images across 50 font families**, with 2–5 visible text lines per image, 129 independently verified font binaries, and no duplicate images or validation errors.

| Identity | Frozen value |
| --- | --- |
| Version | `1.0.0` |
| Release descriptor | [releases/1.0.0.json](releases/1.0.0.json) |
| Dataset Git commit | [`d69e87e2c206ea75c52f5b8340d677bd14af03e3`](https://github.com/eob/fontbench/commit/d69e87e2c206ea75c52f5b8340d677bd14af03e3) |
| Dataset fingerprint | `d40a3cafa91610bbebaa6c49719f24efcbe754a328e448d3e51f0e1f217c79a6` |
| Evaluation protocol fingerprint | `3769c8cc383a4959533c4801eec6202035a5a8cd30b76644e8cdfbc11cc859ce` |
| Rendering / grading protocols | `2` / `3` |
| Compatible release checkout | Git tag `v1.0.0` |

The dataset commit predates this release naming and records the exact frozen inputs. The release tag records the version-aware tooling and run-log workflow. Dataset folder names and internal protocol counters predate the public version label; they are not public benchmark versions.

This release fixes single-line inputs, unverified or conflicting font identities/styles/weights, permissive answer grading, answer-bearing Harbor metadata, and misleading report comparisons. It retains exact source font bytes for offline reproduction and rejects mismatched release data before live requests. Full details and causal regression evidence are in the [ticket catalog](tickets/README.md).

Runs record the release label, dataset Git commit and fingerprint, evaluation protocol, model configuration, code checkout, timestamps, and every attempt. Runs made at different times can contribute to the same website; repeated model/configuration–input pairs are resolved by first recorded observation, without choosing the highest score. Changed inference configurations remain distinct.

The benchmark intentionally samples the typography space. Unequal family counts and conditional factor correlations are documented sampling limits; exhaustive combinations and independent causal measurements are not claimed.

## Unversioned prototypes — historical, invalid for V1.0.0 comparisons

- The original 1,000-image generation includes duplicate/conflicting labels and unsupported or unintended font faces. Earlier graders and Harbor prompts also inflated scores or revealed answers.
- The September 7, 2026 639-image pilot still includes two single-line samples, synthesized italics, conflicting font evidence, and a strong layout shortcut. Its paid responses and checkpoint are preserved as historical records.
- Code and measurements at `14e792f` and earlier are pre-release prototypes. They must not be relabeled as V1.0.0 or combined with its measurements.

See [historical classifications](results/historical.json) and the [results guide](results/README.md). No historical scores were carried into V1.0.0.
