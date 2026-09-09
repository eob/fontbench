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

## First V1.0.0 result publication — 2026-09-09

The first sealed publication compares eleven OpenAI, Gemini, and Claude configurations (including Fable) on the same **728 inputs across 49 of the 50 release families**. All 8,102 retained responses have explicit final status; 8,008 belong to the fixed comparison and 94 remain supplementary. Full-release coverage remains partial. Cumulative recorded spending is $99.991901 under the $100 guard.

All 20 historical infrastructure failures were recovered. Original responses, attempts, checkpoint bytes, model settings, and cost history remain intact. Every final response was independently scored with the frozen V1 protocol; no grading discrepancy remains. Metered comparison cost excludes unmetered retry reservations and separate failed attempts.

- [Final results and exact cohort](results/runs/1.0.0/2026-09-08-all-except-fable/final_results.json)
- [Artifact seal and verification hashes](results/runs/1.0.0/2026-09-08-all-except-fable/finalization.json)
- Source checkpoint Git commit: `8e1f3026307e5a865c47f2b25bbac2c2b074f925`
- Finalizer Git commit: `3d16dacc021f26c46c09b762b5c985b5b7004151` (clean)
- Shared cohort SHA-256: `19097ac3b1a2cab662304dcea8f051297779934f2fc35d8d22bc79a1e66ee19e`

This publication does not change the V1.0.0 dataset, release tag, or protocol. New campaigns use new run IDs; existing sealed publications remain reproducible. See the [finalization guide](releases/FINALIZATION.md).

## Unversioned prototypes — historical, invalid for V1.0.0 comparisons

- The original 1,000-image generation includes duplicate/conflicting labels and unsupported or unintended font faces. Earlier graders and Harbor prompts also inflated scores or revealed answers.
- The September 7, 2026 639-image pilot still includes two single-line samples, synthesized italics, conflicting font evidence, and a strong layout shortcut. Its paid responses and checkpoint are preserved as historical records.
- Code and measurements at `14e792f` and earlier are pre-release prototypes. They must not be relabeled as V1.0.0 or combined with its measurements.

See [historical classifications](results/historical.json) and the [results guide](results/README.md). No historical scores were carried into V1.0.0.
