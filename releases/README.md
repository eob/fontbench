# Frozen releases

**FontBench V1.0.0** is the first named release. [Its descriptor](1.0.0.json) binds the public version to an exact dataset Git commit, image/label fingerprint, and evaluation protocol fingerprint. The [changelog](../CHANGELOG.md) records the release's scope and provenance.

Use `--release 1.0.0` when running models or building the website. Validation checks the committed manifest, current image/label fingerprint, protocol identity, and all input evidence before issuing live requests. A version label alone is insufficient provenance.

Existing descriptors and registered dataset/package directories are frozen. Development rendering writes candidate directories. Changes to inputs, labels, prompts, or grading require a new descriptor/version and matching recorded hashes; do not update an old descriptor to disguise changed inputs. Reproduce a release in a separate directory using its retained font cache.

The retained dataset lives at `dataset/fontbench-2-rendered`, and its Harbor package at `dataset/fontbench-2`. These implementation directory names predate release naming. Both belong to **V1.0.0**; the unversioned `dataset/fontbench-1` is an invalid historical prototype.

Run records live under `results/runs/<version>/<run-id>/`. Model configurations, execution dates, and source code commits belong to individual runs. They do not change the dataset release. Preserve the original measurements; the website derives comparisons from compatible records.

[Finalize a publication](FINALIZATION.md) to freeze its exact model roster and shared input cohort, independently re-score saved responses, and seal the source artifacts. Dataset coverage and publication finality are recorded separately.
