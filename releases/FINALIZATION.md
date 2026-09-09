# Finalizing measured results

A publication can be final while covering a sample of the frozen release. FontBench keeps the full release's `expected_task_count` and records the publication's exact model roster and task cohort separately.

Finish the runner and commit its checkpoint, attempt export, metadata, summary, and scorecards before sealing. Finalization acquires the same exclusive run lock as inference, refuses a nonempty SQLite WAL, verifies release identity and committed source bytes, and independently parses and scores every retained final response. It makes no provider requests and does not change the source artifacts.

```sh
# Publish the intersection completed by every recorded model.
.venv/bin/python -m baseline.finalize \
  --run-dir results/runs/1.0.0/your-run \
  --scope common

# Alternatively, require all release inputs for every recorded model.
.venv/bin/python -m baseline.finalize \
  --run-dir results/runs/1.0.0/your-run \
  --scope full

# Verify the committed evidence, artifact hashes, scoring, and fixed cohort.
.venv/bin/python -m baseline.finalize \
  --run-dir results/runs/1.0.0/your-run --verify
```

Use `--models model-a model-b` only when intentionally choosing an explicit publication roster. All recorded final responses remain in the export, including responses outside that roster or common cohort. Unresolved infrastructure failures must be retried before finalization; invalid model responses remain final, scored zero, and are never retried to obtain a better answer.

`final_results.json` contains the fixed comparison, per-model metrics and seven group breakdowns, and every original final response wrapped with `status: "final"`, `included_in_comparison`, its source attempt ID, and a canonical result hash. All metrics are fractions. Model and group metrics use the same comparison cohort. `dataset_font_count` describes the full release; `comparison.font_count` describes the selected inputs. Missing group observations have count zero and null metrics.

The exported mean API response cost uses recorded metered token usage and the recorded model's prices. It excludes separate infrastructure attempts and unmetered retry reservations. Because usage can accumulate within a request's retries, interpret this as **metered API cost per scored input**, rather than an invoice amount or a marginal single HTTP-call price. Unknown usage, pricing, or latency produces a null mean and an explicit known-response count. Campaign totals retain all recorded attempt costs, including conservative reservations.

`finalization.json` records the release, dataset and protocol identities, source checkpoint Git commit, finalizer Git commit and dirty state, chronology, fixed comparison, and SHA-256 hashes of the SQLite checkpoint, full attempt export, run metadata, summary, all scorecards, and `final_results.json`. Verification also re-parses and re-scores the source responses and checks their committed bytes; updating a file hash alone cannot make changed evidence valid.

A sealed run ID cannot resume. Additional measurements use another run ID and remain compatible with normal release aggregation. Repeating finalization with the same scope and roster verifies the existing files without changing their bytes. A different scope requires a separate publication. An interrupted finalization that has written `final_results.json` without its seal fails closed and needs inspection before any further action.

The ordinary release website continues to distinguish partial dataset coverage from complete coverage and rejects a run with invalid sealed artifacts. A published comparison should consume `final_results.json` so future runs cannot change its fixed roster or cohort. Commit both finalization files with the source records before publishing or importing them elsewhere.
