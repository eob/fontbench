# ci-01-browser-transport: Investigate intermittent hosted renderer-test transport disconnect

- **Status**: Open
- **Branch**: `ci-01-browser-transport` (not started)
- **Assignee**: Unassigned
- **Machine**: eob-dev2 (observed)
- **Harness**: codex
- **Session ID**: `/root` / FontBench publication follow-up

## Problem and evidence

The hosted Bun 1.3.14 / Playwright renderer suite intermittently loses Chromium's debugging pipe during a real screenshot. This has occurred in both `closes the browser and preserves previous output when a later screenshot fails` and `reuses pinned font bytes and refuses tampered cache assets`. The first test adds nested browser/page/locator/screenshot spies; the cache test uses only the shared browser-launch spy. Nested screenshot instrumentation therefore does not bound the observed failure. The transport's underlying cause is unknown. No benchmark data defect, cache-integrity failure, or renderer defect has been established.

At exact commit `9d3905184d995c4daa6f5f50a5fefa25a6ac04f5`, [PR run 34299177701](https://github.com/eob/fontbench/actions/runs/34299177701) passed every phase, including all 80 browser/TypeScript tests and frozen integrity checks. The paired [push run 34299173713](https://github.com/eob/fontbench/actions/runs/34299173713) passed Python, then reported 79 passing tests and this one failure. Its first screenshot starts at 01:27:57.068 UTC; the pipe closes at 01:27:57.117 and Chromium exits with code 0. The test times out after 5 seconds and bounded cleanup fails clearly after 4 seconds. Shared state is restored and every subsequent recipe test passes.

An earlier occurrence on `aef66af5` also failed one hosted job while an identical push job and an unchanged-head retry passed. The independent cleanup contamination has been repaired and regression-tested. See [the runtime evidence record](evidence/publish-01-bun-runtime-gates.md) for controlled local results and both passing and failing hosted outcomes.

At `3c3b58875883a23b4c07c9c09286f9778e850027`, [PR run 34299994333](https://github.com/eob/fontbench/actions/runs/34299994333) lost the pipe during the cache test's first render: screenshot started at 01:39:52.301 UTC, pipe disconnected at .369, and Chromium exited with code 0 at .396. The repeated render, image-hash comparison, deliberate cache corruption, and expected hash-mismatch rejection were not reached. Its 15-second test deadline and four-second cleanup deadline failed clearly; subsequent tests, including the nested screenshot test, passed. The paired [push run 34299989851](https://github.com/eob/fontbench/actions/runs/34299989851) passed the cache case in 695.97 ms and failed the nested screenshot case instead. Both jobs reported 79 passes and one failure. A bounded local cache-case control on the same source passed all three assertions; the frozen release and immutable result-seal verifiers also passed.

The one authorized [unchanged-head PR retry, attempt 2](https://github.com/eob/fontbench/actions/runs/34299994333/attempts/2), again failed the cache case during its first screenshot (01:43:10.674 UTC; pipe disconnect at .751; browser exit 0 at .773), reporting 79 passes and one failure. The exact current-head local CI browser command then passed all 80 tests and 277 assertions in 10.34 seconds; typechecking and wheel packaging passed. Git comparison confirms the renderer, all `src` tests, protocol/grader/provider code, frozen dataset, sealed responses, dependency lock, and CI workflow are unchanged from the fully green hosted `9d3905184d995c4daa6f5f50a5fefa25a6ac04f5`. This local control does not clear the current hosted failure. The CI limitation remains open; no further hosted retry or speculative repair accompanies this record.

## Acceptance criteria

- [ ] Establish a bounded reproduction or diagnostic evidence identifying the transport cause across both affected cases; do not assume nested spies are required or infer a generic hosting or renderer defect from intermittent outcomes alone.
- [ ] If changing test instrumentation, preserve cache-reuse equality and tamper rejection, the real first screenshot, the injected second-screenshot error, output preservation, browser cleanup assertions, and existing test deadlines. Show a failing control and successful repair.
- [ ] Verify the complete ordered suite and hosted phase with existing diagnostics and process watchdog; preserve failures without unconditional retries or ignored errors.
- [ ] Keep frozen renderer behavior, dataset, evaluation protocol, model responses, and sealed publication artifacts unchanged.

This follow-up is investigation only. No speculative source change is prescribed, and no paid inference is needed.
