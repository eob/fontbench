# valid-01-benchmark-audit: Validate FontBench before final runs

- **Status**: In Progress
- **Branch**: `valid-01-benchmark-audit`
- **Base**: `14e792f`
- **Machine**: `eob-dev2`
- **Harness**: codex
- **Session ID**: `01a082ae-164d-73f2-a49e-a3d6e48adfaf`
- **Assignee**: Edward Benson
- **Delivery**: Local repository review and fixes; tickets are the central coordination record.

## Goal

Audit generated pixels, font identity, label observability, packaging, grading, run provenance, and reporting. Repair proven defects and prepare a reproducibly validated dataset before any final paid evaluation.

## Plan and ownership

1. Establish the baseline test result and inventory both historical and September 7 inputs.
2. Audit renderer/font sources, evaluator/runner, and packaging/reporting independently; record findings in numbered `valid-*` tickets with reproducible evidence before fixes.
3. Repair each confirmed issue with regression checks, including inverse/boundary cases and isolated base-code controls where practical.
4. Regenerate candidate inputs separately, validate every sample, inspect representative images, and package the accepted dataset.
5. Run combined checks, offline evaluation, and a simplification review; record a gate matrix and explicit remaining limitations.

## Initial evidence

The README marks the 1,000 packaged images as historical and unsuitable for new comparisons. A separate 639-sample September 7 input set is described as corrected, but the renderer does not measure line count or assert at least two lines before assigning a line-height label. Existing font verification asserts custom-font usage without verifying internal family identity.

## Decisions and durable findings

- Preserve existing paid-run inputs and checkpoints as historical evidence. Use a new dataset fingerprint and run ID after any image, label, or prompt correction.
- Final paid model runs are a subsequent activity; this audit uses offline tests and font-provider downloads.
- Individual audit tickets track defects and evidence; this ticket tracks integration and readiness.

## Handoff & Takeover Log

- 2026-09-08: Started audit from clean `main` at `14e792f`.
