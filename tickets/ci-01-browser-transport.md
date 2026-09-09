# ci-01-browser-transport: Investigate intermittent hosted screenshot-test transport disconnect

- **Status**: Open
- **Branch**: `ci-01-browser-transport` (not started)
- **Assignee**: Unassigned
- **Machine**: eob-dev2 (observed)
- **Harness**: codex
- **Session ID**: `/root` / FontBench publication follow-up

## Problem and evidence

The hosted Bun 1.3.14 / Playwright renderer suite intermittently loses Chromium's debugging pipe during the first real screenshot in `closes the browser and preserves previous output when a later screenshot fails`. That test uniquely instruments browser, page, and locator methods with nested spies before injecting a failure on the second screenshot. The pipe disconnect occurs before the intended injection; its cause is unknown. No benchmark data defect or renderer defect has been established.

At exact commit `9d3905184d995c4daa6f5f50a5fefa25a6ac04f5`, [PR run 34299177701](https://github.com/eob/fontbench/actions/runs/34299177701) passed every phase, including all 80 browser/TypeScript tests and frozen integrity checks. The paired [push run 34299173713](https://github.com/eob/fontbench/actions/runs/34299173713) passed Python, then reported 79 passing tests and this one failure. Its first screenshot starts at 01:27:57.068 UTC; the pipe closes at 01:27:57.117 and Chromium exits with code 0. The test times out after 5 seconds and bounded cleanup fails clearly after 4 seconds. Shared state is restored and every subsequent recipe test passes.

An earlier occurrence on `aef66af5` also failed one hosted job while an identical push job and an unchanged-head retry passed. The independent cleanup contamination has been repaired and regression-tested. See [the runtime evidence record](evidence/publish-01-bun-runtime-gates.md) for controlled local results and both passing and failing hosted outcomes.

## Acceptance criteria

- [ ] Establish a bounded reproduction or diagnostic evidence identifying the transport/instrumentation cause; do not infer a generic hosting or renderer defect from intermittent outcomes alone.
- [ ] If changing test instrumentation, preserve the real first screenshot, the injected second-screenshot error, output preservation, browser cleanup assertions, and existing test deadlines. Show a failing control and successful repair.
- [ ] Verify the complete ordered suite and hosted phase with existing diagnostics and process watchdog; preserve failures without unconditional retries or ignored errors.
- [ ] Keep frozen renderer behavior, dataset, evaluation protocol, model responses, and sealed publication artifacts unchanged.

This follow-up is investigation only. No speculative source change is prescribed, and no paid inference is needed.
