# Exact-match presentation gates — 2026-09-09

The requested presentation omits composite scores. The report now defaults to all six correct and offers the six separate attribute accuracies. Initial model, subgroup, and shared-comparison values use exact match; changing the metric updates subgroup labels and values together. Stored metrics, raw responses, and the publication seal remain unchanged.

Two regressions distinguish a zero exact-match score from a stored 5/6 composite. Both fail against the original presentation and pass after the change; an isolated source reversal reproduces both failures.

| Gate | Result |
| --- | --- |
| Focused page/aggregation tests | 74 passed |
| Full Python suite | 452 passed in 25.25 s |
| Chromium browser inspection | All seven selector options, eleven model scores/bars, six subgroup headings, 770 subgroup cells and denominators pass; mobile exact view passes; no page errors |
| Generated artifact preservation | All fifteen JSON/JSONL page artifacts byte-identical; only generated HTML changed |
| Frozen scope check | No difference in released dataset, evaluator/provider/prompt, release descriptor, or sealed run paths |
| Diff review | Clean; presentation, two regressions, README, generated HTML only |

Initial Python-formatted HTML and JavaScript's selector formatter differ at exact half-decimal ties in two cells; both remain within the displayed 0.1 percentage-point precision. Underlying exact values are unchanged. Initial values were checked against this precision and selector-driven values against the existing formatter.

Local evidence: `/tmp/fontbench-exact-presentation-red.log`, `-reversion.log`, `-focused.log`, `-python.log`, `-artifacts.json`, `-browser.json`, and `-browser.log`. Screenshots: `/tmp/fontbench-report-exact-desktop.png` and `/tmp/fontbench-report-exact-mobile.png`.
