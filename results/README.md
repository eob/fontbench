# Historical results

The checked-in scorecards and `fontbench_summary.json` were produced before the repository audit. They are retained as historical artifacts, not validated results for the corrected benchmark.

The old grader accepted font substrings and assigned default attribute values to missing or invalid predictions, which could inflate scores. The old renderer could capture an unintended face, fallback font, or unsupported weight while retaining the requested label. The Harbor instructions also contained each task's answer.

Existing scorecards do not contain enough raw response or font provenance data to establish corrected measurements reliably. Re-render into a separate directory and run a new evaluation with the corrected code. Do not compare the old and new scores as if they used the same protocol.

The old structured summary also includes hard-coded pricing, evaluation dates, performance notes, and Pareto-frontier labels. Those values should not be treated as current provider prices or independently computed comparisons. The current exporter derives comparisons from supplied scorecards and leaves unknown pricing unset.

The September 7 multi-provider campaign in `runs/fontbench-2026-09-07` is also historical after the September 8 validity audit. It still contains single-line images and remaining font/layout design defects. The new live validation gate rejects both generations. Use `dataset/fontbench-2-rendered` and a new run ID for grading version 3; see [the current audit catalog](../tickets/README.md).
