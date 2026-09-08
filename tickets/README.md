# FontBench issue catalog

This folder is the authoritative local workfu/ticketfu issue catalog. It includes the two earlier implementation tickets, six validity audit tickets, and three V1.0.0 release tickets. The accepted benchmark intentionally uses compact sampling; exhaustive coverage is not required.

| Ticket | Priority | Scope | State |
| --- | --- | --- | --- |
| [run-01](run-01-v1-model-campaign.md) | High | First V1.0.0 campaign across eleven provider models; $50 cap, all providers active | In Progress |
| [fix-repo-audit](fix-repo-audit.md) | High | Initial repository, renderer, grader, package, and installation repairs | Completed; historical |
| [feat-multi-provider-benchmark](feat-multi-provider-benchmark.md) | High | Provider adapters, checkpoints, budgeted pilot, and first website | Completed; historical |
| [valid-01](valid-01-benchmark-audit.md) | Critical | Audit integration, artifact census, fresh corpus, final verification | Completed |
| [valid-02](valid-02-rendering.md) | Critical | Multiline inputs, binary family/weight/style identity, pinned assets | Completed |
| [valid-03](valid-03-evaluation.md) | Critical | Strict prediction schema, protocol identity, resume/cohort correctness | Completed |
| [valid-04](valid-04-packaging-reporting.md) | High | Answer leakage, package integrity, honest reports and malformed data | Completed |
| [valid-05](valid-05-experimental-design.md) | High | Layout shortcuts, sampling coverage, definitions and limits | Completed; compact sampling accepted |
| [valid-06](valid-06-dataset-release-gate.md) | Critical | Independent image/font validation and mandatory release checks | Completed |
| [release-01](release-01-versioned-runs.md) | High | V1.0.0 identity, Git anchor, resumable dated runs and attempt logs | Completed |
| [release-02](release-02-aggregate-run-history.md) | High | Aggregate compatible model runs across time and publish their origins | Completed |
| [release-03](release-03-protect-frozen-artifacts.md) | High | Protect frozen directories and isolate candidate generation | Completed |

**FontBench V1.0.0** contains 1,824 samples across 50 families, with zero validation errors. Its [release descriptor](../releases/1.0.0.json) and [changelog](../CHANGELOG.md) pin the dataset Git commit and content/protocol hashes. The original 1,000-image set and September 7 639-image pilot are invalid historical artifacts. Their paid checkpoints and original responses remain preserved; no scores carry forward.

Use [the run guide](../results/README.md) to add measurements later and rebuild [the benchmark website](../site/index.html). New paid campaigns are separate from these implementation tickets.

The **11 audit/release tickets are completed**; the newly authorized model campaign is tracked separately in run-01. Final integration passed 413 Python tests, 78 Bun tests, TypeScript checking, frozen release validation, offline resume, wheel packaging, and desktop/mobile website checks. See [the integration record](valid-01-benchmark-audit.md#v100-release-and-ticket-closure) and [machine-readable gate evidence](evidence/release-final-gates.json).
