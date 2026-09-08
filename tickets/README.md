# Benchmark validity audit

Started September 8, 2026 at `14e792f`. This folder is the authoritative local issue catalog. Existing tickets document earlier work; the `valid-*` series records the current audit and repairs.

| Ticket | Priority | Scope | State |
| --- | --- | --- | --- |
| [valid-01](valid-01-benchmark-audit.md) | Critical | Integration, historical artifact census, fresh corpus and final validation | In progress |
| [valid-02](valid-02-rendering.md) | Critical | Single-line images, binary family/weight/style identity, native faces, pinned font assets | Implementing and validating full render |
| [valid-03](valid-03-evaluation.md) | Critical | Strict prediction schema, protocol identity, resume/cohort correctness, live readiness gate | Regression checks passing |
| [valid-04](valid-04-packaging-reporting.md) | High | Answer leakage, package integrity/atomic replacement, paired reports and truthful provenance | Regression checks passing |
| [valid-05](valid-05-experimental-design.md) | High | Width/tracking shortcuts, layout coverage, task definitions and limitations | New recipes verified; corpus census pending |
| [valid-06](valid-06-dataset-release-gate.md) | Critical | Independent all-image/all-font validation and fail-closed release checks | Hardening and integration |

The 1,000-sample original dataset and the 639-sample September 7 comparison are historical evidence. Neither is an approved final benchmark. Existing paid results must not be transferred to changed images, prompts, labels, or grading.
