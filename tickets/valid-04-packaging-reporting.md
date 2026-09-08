# valid-04-packaging-reporting: Isolate answers and preserve comparable measurements

- **Status**: In Progress
- **Branch**: `valid-01-benchmark-audit` (shared ownership coordinated by root)
- **Machine**: eob-dev2
- **Harness**: codex
- **Session ID**: /root/packaging_reporting
- **PR**: Local audit; no publishing requested
- **Assignee**: Edward Benson
- **Base commit**: `14e792f`

## Goal
Package only intact benchmark images without exposing typography labels, and publish scores only with consistent dataset, grading, and cohort provenance.

## Observed failure mechanisms
- Harbor task names are font-bearing task IDs; task metadata tags contain category, weight, modifier, and width answers.
- Packaging accepts any file as PNG, mutates prior output in place, and permits extra environment files or symlinks in retained tasks.
- Generated verifier awards partial credit for incomplete schema, unlike the tightened six-field protocol.
- Structured export trusts aggregate score fields, lacks strict protocol/mock identity, and describes every export as 50 fonts regardless of evaluated data.
- Page can throw on malformed persisted cards; partial displays do not provide shared input counts. Dataset-validity wording precedes any validity gate.

## Plan
1. Pin corrupt image, label leakage, retained stale file/symlink, strict verifier, malformed card, aggregate mismatch, and provenance regressions with Red tests.
2. Build Harbor tasks in staging, validate PNG bytes/checksums and manifest image hashes, remove label-bearing public metadata, and replace only recognized generated output with rollback.
3. Align Harbor JSON validation with grading version 3 and evaluator schema.
4. Make page expose root validator results and shared-cohort metrics; validate scorecard protocol identity and malformed shapes.
5. Require complete/provenance-compatible export inputs and derive scores/taxonomy from task rows.
6. Run focused tests and isolated old-implementation controls, document exact evidence and validation gates, and simplify changed code.

## Red evidence
Pending execution.

## Validation gate matrix
Pending implementation.

## Decisions and durable findings
Historical data and reports remain reviewable but are not evidence that an input set passed the new validity gate. Agent-visible Harbor files contain only generic task instructions and the PNG; original manifest IDs remain verifier-side.
