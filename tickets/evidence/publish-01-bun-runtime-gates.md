# publish-01: Bun runtime and rejection-matcher regression

Date: 2026-09-09. Investigated on `publish-01-v1-results` at source commit `b73184e44a3ffbdd048b4144fc8fb2db49029ac2`, before modifying runtime configuration.

## Failure and controlled comparison

PR #1 CI installed Bun 1.4.2 (`744846f84`) through an unversioned `oven-sh/setup-bun@v2` step. Python passed all 450 tests, then Bun reported 71 passes and seven failures. All seven failures were renderer rejection/error-handling cases exceeding their existing 5,000 ms deadlines. The duplicate-image case took 30,012.15 ms and the screenshot-failure case took 25,013.08 ms. The working local installation was Bun 1.3.14 (`0d9b296a`).

Downloaded the official Bun 1.4.2 Linux x64 release binary into `/tmp/fontbench-bun-1.4.2/bun-linux-x64/bun`. Compared the same source, lockfile, installed dependencies, Chromium executable, fixture fonts, and host with only the Bun executable changed. The renderer tests use local font fixtures and make no provider requests.

| Command | Result |
| --- | --- |
| `bun test src/render.test.ts -t 'refuses CSS weight declarations that mislabel a static font binary'` | Bun 1.3.14: 1 pass, 0 fail; test 222.32 ms |
| `/tmp/fontbench-bun-1.4.2/bun-linux-x64/bun test src/render.test.ts -t 'refuses CSS weight declarations that mislabel a static font binary'` | Bun 1.4.2: 1 pass, 0 fail; test 155.10 ms |
| `/tmp/fontbench-bun-1.4.2/bun-linux-x64/bun test src/render.test.ts` | Bun 1.4.2: 10 pass, 7 fail, 50 assertions; 102.24 s |
| `bun test src/render.test.ts` | Bun 1.3.14: 17 pass, 0 fail, 54 assertions; 12.58 s |

The final 1.3.14 control ran while the 1.4.2 reproduction was still running on the same machine. Its duplicate-image case passed in 2,324.62 ms and its screenshot-failure case passed in 1,918.09 ms. Positive single-image render cases in the failing 1.4.2 run still passed in approximately 230–245 ms.

Verbatim local Bun 1.4.2 failure evidence:

```text
(fail) rendered font integrity > refuses CSS weight declarations that mislabel a static font binary [12863.17ms]
  ^ this test timed out after 5000ms.
(fail) rendered font integrity > refuses a missing font instead of labeling a fallback [10212.18ms]
  ^ this test timed out after 5000ms.
(fail) rendered font integrity > refuses broken webfont bytes [5012.55ms]
  ^ this test timed out after 5000ms.
(fail) rendered font integrity > refuses partial glyph fallback even when a webfont loads [12292.24ms]
  ^ this test timed out after 5000ms.
(fail) rendered font integrity > refuses a CSS italic declaration around a regular font binary [12783.82ms]
  ^ this test timed out after 5000ms.
(fail) rendered font integrity > refuses identical images assigned to distinct tasks [30013.49ms]
  ^ this test timed out after 5000ms.
(fail) rendered font integrity > closes the browser and preserves previous output when a later screenshot fails [5006.54ms]
  ^ this test timed out after 5000ms.

 10 pass
 7 fail
 50 expect() calls
Ran 17 tests across 1 file. [102.24s]
```

The screenshot case also received `evaluate: Target page, context or browser has been closed` instead of the injected screenshot exception, and Bun reported `killed 1 dangling process`. This occurs after the ordered suite has accumulated timeouts; it does not establish a renderer cleanup defect on the validated runtime.

The controlled result establishes a runtime-dependent regression in ordered test execution. The exact Bun internal cause remains unproven. An isolated failing case is fast on either runtime, so increasing the deadlines would conceal the observed regression. Re-running the unchanged file with the older executable restores every original assertion; no renderer, lifecycle, or test timeout edits were needed.

## Fix and validation

The first fix pinned Bun 1.3.14 in CI and `package.json`, and documented that supported development runtime in the README. Future runtime upgrades must pass the complete ordered renderer suite, not only isolated cases. This initial runtime-pin commit changed no dependency, renderer, test, evaluator, provider, prompt, released dataset, or sealed result bytes.

| Gate | Result |
| --- | --- |
| Bun 1.4.2 original full-file reproduction | RED: same seven failures as hosted CI |
| Bun 1.3.14 unchanged full-file control | GREEN: all 17 tests pass |
| `bun install --frozen-lockfile --ignore-scripts` | GREEN: 21 installs checked across 22 packages; no changes |
| `bun run test:ts` on pinned runtime | GREEN: 78 pass, 0 fail, 257 assertions; 13.53 s |
| `bun run typecheck` | GREEN: exit 0 |
| `.venv/bin/python -m baseline.releases --release 1.0.0` | GREEN: exit 0; unchanged 1,824-input release and protocol fingerprints |
| `.venv/bin/python -m baseline.finalize --run-dir results/runs/1.0.0/2026-09-08-all-except-fable --verify` | GREEN: exit 0; immutable 8,102-response seal and 728-input comparison verified |
| `git diff --check`; scope review | GREEN: only runtime configuration, setup documentation, and ticket evidence changed |
| Hosted CI with explicit runtime pin | Both jobs reached the 15-minute job limit; follow-up below |

Local raw logs: `/tmp/fontbench-pr1-ci-failure.log`, `/tmp/fontbench-render-local-bun1314-control.log`, `/tmp/fontbench-render-bun142-red.log` (isolated case passed despite the filename), `/tmp/fontbench-render-bun142-full.log`, `/tmp/fontbench-render-bun1314-full-control.log`. The durable excerpts and command results above do not depend on retaining those temporary files.

## Hosted follow-up and assertion scheduling

The runtime-pin commit `fa1be6390cebcbcd03c80f35a0b5125469d30c6a` did select Bun 1.3.14 (`0d9b296a`) on both hosted jobs. [Run 34296595559](https://github.com/eob/fontbench/actions/runs/34296595559) passed all 450 Python tests in 26.93 s, then passed renderer tests 1–9, including four rejection cases that previously timed out. It stopped producing output at 00:50:16 UTC after the supported-weight test and was cancelled at the 15-minute job limit. [Run 34296599300](https://github.com/eob/fontbench/actions/runs/34296599300) passed Python in 29.66 s and renderer tests 1–6, then stopped after the missing-font rejection test. Neither produced a Bun test timeout; both left a Chromium process when the job was cancelled.

These logs bound the stall to the interval between a passing test and the following render-start message. That interval includes fixture cleanup/setup, browser launch, page/CDP setup, and route registration. They do not identify an individual operation or establish the internal cause of the hosted hang. The fixture has no remote font/provider dependency. Three additional controls on the unchanged pinned source passed:

| Command | Result |
| --- | --- |
| `bun run test` | 450 Python tests in 25.99 s; 78 Bun tests in 14.42 s; TypeScript passed |
| `timeout 120s env CI=true GITHUB_ACTIONS=true bun run test` | 450 Python tests in 21.77 s; 78 Bun tests in 13.36 s; TypeScript passed |
| `timeout 90s env CI=true GITHUB_ACTIONS=true taskset -c 0,1 bun test src/render.test.ts` | 17 pass, 0 fail; 13.81 s |

The original 1.4.2 failures all occurred in cases using `await expect(promise).rejects.toThrow(...)`. Created a scratch source copy at `/tmp/fontbench-native-await-359twhcg`, retaining the same dependency installation and font fixtures. Changed only these ten assertion call sites to use a small helper: native `await` catches the rejection, an explicit assertion verifies that rejection occurred, and the original synchronous `toThrow` regex/string matcher checks the captured error. No sentinel error is thrown on fulfillment, so a fulfilled promise cannot accidentally satisfy the expected regex. Every original deadline, error expectation, rendering operation, cleanup operation, and remaining assertion stays in place.

| Scratch control | Result |
| --- | --- |
| `timeout 120s /tmp/fontbench-bun-1.4.2/bun-linux-x64/bun test src/render.test.ts` with native-await helper | GREEN: 17 pass, 0 fail, 64 assertions; 9.41 s |
| Restore original `src/render.test.ts` in the same scratch directory; rerun with `timeout 150s` | RED restored: 10 pass, 7 fail, 54 assertions; 126.36 s; process exit 1 before watchdog |

In the native-await 1.4.2 run, duplicate-image rejection took 393.75 ms and screenshot-failure rejection took 235.59 ms, versus 30,013.49 ms and 5,006.54 ms in the initial Red run. This isolates the async assertion path as a cause of the reproducible 1.4.2 ordered-suite failure. The internal Bun mechanism and whether the same change resolves the separate hosted 1.3.14 hard hang still require hosted confirmation.

Verbatim same-directory reversal summary:

```text
(fail) rendered font integrity > refuses identical images assigned to distinct tasks [31730.79ms]
  ^ this test timed out after 5000ms.
(fail) rendered font integrity > closes the browser and preserves previous output when a later screenshot fails [24096.38ms]
  ^ this test timed out after 5000ms.

 10 pass
 7 fail
 54 expect() calls
Ran 17 tests across 1 file. [126.36s]
```

Apply the helper only to the renderer tests and retain the 1.3.14 pin. CI now runs Python, TypeScript/browser tests, and typechecking as separate named steps. The browser step has an external 180-second watchdog that fails the job on a hang; it does not alter any test deadline or ignore failures. CI-only fixture/launch/close markers and Playwright browser/API debug logs locate any remaining hosted stall. No renderer, dependency, evaluator, provider, prompt, released dataset, or sealed result bytes change.

| Final follow-up gate | Result |
| --- | --- |
| `timeout 180s env CI=true GITHUB_ACTIONS=true DEBUG=pw:browser,pw:api bun run test:ts` | GREEN on Bun 1.3.14: 78 pass, 0 fail, 267 assertions; 7.31 s |
| `bun run typecheck` | GREEN: exit 0 |
| Frozen release and sealed artifact verification | GREEN: both CLI verifiers exit 0; dataset/protocol and immutable run unchanged |
| `git diff --check`; final scope review | GREEN: only renderer test harness, CI phases/diagnostics, and ticket evidence changed |
| Hosted CI with native-await assertions and bounded diagnostics | Pending parent push/retest |

Follow-up raw logs: `/tmp/fontbench-pr1-pin-completed.log`, `/tmp/fontbench-pr1-pin-completed-second.log`, `/tmp/fontbench-pr1-pin-aggregate-control.log`, `/tmp/fontbench-pr1-pin-ci-env-control.log`, `/tmp/fontbench-pr1-pin-ci-two-core-control.log`, `/tmp/fontbench-native-await-bun142.log`, `/tmp/fontbench-native-await-bun142-reversal.log`, `/tmp/fontbench-native-await-pinned-ci-gate.log`.

## Browser-close failure must not contaminate later tests

Commit `aef66af55211944db047b8f88c432d9f18d7fc84` completed every phase in [push run 34298344351](https://github.com/eob/fontbench/actions/runs/34298344351): 450 Python tests, 78 Bun tests (267 assertions, 10.34 s), TypeScript, dataset/release validation, and wheel build. The paired [PR run 34298349971](https://github.com/eob/fontbench/actions/runs/34298349971) failed during the final screenshot-failure test. Chromium's debugging pipe closed during the first real screenshot, before the second screenshot's injected error, and the browser process exited with code 0. The fixture then stopped at `browser close begin`; its hook timed out. Because restoring the shared font/recipe/width arrays occurred after that close, two later recipe tests inherited the injected recipes and failed. The first transport failure's cause remains unproven; this follow-up fixes the observed cleanup contamination without retrying or suppressing renderer errors.

The parent reran only that failed hosted PR job on unchanged `aef66af5`; the retry completed every phase successfully, as did the original push job. Preserve the first failure alongside that successful retry: the transport disconnect is intermittent, and no renderer change is justified by this evidence. The cleanup contamination remains a deterministic defect worth repairing independently.

Verbatim hosted failure excerpts:

```text
[render-test] cleanup begin
[render-test] browser close begin
(fail) rendered font integrity > closes the browser and preserves previous output when a later screenshot fails [10003.76ms]
  ^ a beforeEach/afterEach hook timed out for this test.
Expected length: 3
Received length: 0
(fail) every weight/modifier combination samples all spacing and width levels [0.28ms]
```

A controlled regression supplies a browser close that remains pending until explicitly rejected. Before releasing that close, it verifies the complete original font, recipe, and width state is restored. It then changes the current fixture directory, rejects the close with a known error, verifies that same error propagates, and checks that cleanup removed its captured directory while preserving the later directory. A disconnected fake browser rejects any redundant close call. The unchanged cleanup hook fails the shared-state assertion deterministically:

```text
92 |       expect(TOP_50_FONTS).toEqual(originalFonts);
                                ^
error: expect(received).toEqual(expected)
(fail) rendered font integrity > restores shared fixtures before a failed browser close and cleans only its own directory [195.47ms]

 0 pass
 17 filtered out
 1 fail
 3 expect() calls
```

The repair captures the browser list and directory, clears the tracked list, and restores the launch spy and all shared arrays synchronously before any browser-close await. It closes only connected browsers, preserving close failures. One 4,000 ms deadline for the entire close operation fits inside the existing 5,000 ms hook budget; a never-settling close reports `Renderer test browsers did not close within 4000ms`. The timer is cleared and the captured directory is removed in `finally`. A second regression exercises the never-settling close and checks filesystem cleanup. No renderer, benchmark data, protocol, or original test expectation/deadline changes.

| Cleanup validation gate | Result |
| --- | --- |
| Original cleanup with controlled failed-close regression | RED: original shared font state not restored |
| Focused repaired cleanup tests | GREEN: 2 pass, 0 fail; 10 assertions |
| Scratch reversal restoring only the original cleanup body | RED restored: same shared-state failure; 1 fail, 3 assertions |
| `timeout --kill-after=15s 180s env CI=true GITHUB_ACTIONS=true DEBUG=pw:browser,pw:api bun run test:ts` | GREEN: 80 pass, 0 fail, 277 assertions; 9.88 s |
| `bun run typecheck`; `git diff --check`; final scope review | GREEN: exit 0; cleanup edits limited to renderer tests and this evidence record |

Logs: `/tmp/fontbench-native-await-hosted-pr-failed.log`, `/tmp/fontbench-native-await-hosted-push-success.log`, `/tmp/fontbench-cleanup-red.log`, `/tmp/fontbench-cleanup-green.log`, `/tmp/fontbench-cleanup-reversal.log`, `/tmp/fontbench-cleanup-ts-gate.log`, `/tmp/fontbench-cleanup-typecheck.log`. The scratch reversal lives at `/tmp/fontbench-cleanup-control-56ytuh2d`.

## Hosted result with cleanup repair

At exact commit `9d3905184d995c4daa6f5f50a5fefa25a6ac04f5`, [PR run 34299177701](https://github.com/eob/fontbench/actions/runs/34299177701) passed every phase: 450 Python tests in 34.38 seconds, all 80 TypeScript/browser tests with 277 assertions in 13.26 seconds, typechecking, dataset/release integrity, and wheel build. The paired [push run 34299173713](https://github.com/eob/fontbench/actions/runs/34299173713) passed Python but reported 79 passing TypeScript/browser tests and one failure with 272 assertions in 22.83 seconds. Both outcomes remain part of the validation record.

The sole push failure is the final nested-spy screenshot-injection test. Browser launch, page/CDP setup, font checks, and layout all completed. The first real screenshot began at 01:27:57.068 UTC; Chromium reported its debugging pipe closed at 01:27:57.117 and exited with code 0. The second screenshot's injected error was not reached. The test reached its unchanged 5,000 ms deadline; cleanup then reported its own 4,000 ms deadline, removed the captured directory, and restored the shared arrays. All subsequent recipe tests passed, confirming that cleanup no longer contaminates other tests.

This is an intermittent hosted browser-transport failure observed inside the test's nested instrumentation. The underlying cause is unknown; neither a renderer defect nor generic hosting failure is established. The all-green exact-head PR run verifies the cleanup change and frozen integrity gates. Preserve the failing push without another blind retry. Track further investigation in [ci-01-browser-transport.md](../ci-01-browser-transport.md); no renderer, test, dataset, or result changes accompany this evidence update.

Raw logs: `/tmp/fontbench-cleanup-hosted-pr-success.log` and `/tmp/fontbench-cleanup-hosted-push-failed.log`.

Final CI review adds `--kill-after=15s` to the 180-second process watchdog so a stuck browser cleanup cannot ignore the termination signal indefinitely. This only bounds a stalled test process; normal assertions, browser behavior, and per-test deadlines remain unchanged.

## Transport disconnect also observed without nested screenshot spies

The exact-match presentation commit `3c3b58875883a23b4c07c9c09286f9778e850027` changed no renderer, renderer test, or font-cache implementation relative to the previously green `9d3905184d995c4daa6f5f50a5fefa25a6ac04f5`. Its two initial hosted jobs each reported 79 passing browser/TypeScript tests and one failure, with different failing cases:

| Hosted job | Cache-reuse/tamper case | Screenshot-injection case | Browser phase |
| --- | --- | --- | --- |
| [PR 34299994333](https://github.com/eob/fontbench/actions/runs/34299994333) | Failed after 19,003.64 ms: 15-second test deadline plus four-second cleanup deadline | Passed in 291.89 ms | 79 pass, 1 fail, 274 assertions; 32.21 s |
| [Push 34299989851](https://github.com/eob/fontbench/actions/runs/34299989851) | Passed in 695.97 ms | Failed after 9,005.18 ms: five-second test deadline plus four-second cleanup deadline | 79 pass, 1 fail, 272 assertions; 23.25 s |

The PR's cache case stopped during its **first** `renderAllSamples` call. The first screenshot started at 01:39:52.301 UTC, reported loaded fonts and waited for element stability, then Chromium logged the debugging-pipe disconnection at 01:39:52.369. The browser exited with code 0 at 01:39:52.396. No screenshot success or second browser launch appeared before the test deadline. The second render, image-hash equality assertion, intentional cached-font corruption, and hash-mismatch rejection assertion were therefore not reached. This failure does not establish a defect in cache reuse or corruption detection.

Verbatim PR log excerpt:

```text
2026-09-09T01:39:52.301Z pw:api => screenshot started
2026-09-09T01:39:52.369Z pw:browser [pid=6779][err] [0909/013952.369130:ERROR:content/browser/devtools/devtools_pipe_handler.cc:188] Connection terminated while reading from pipe
2026-09-09T01:39:52.396Z pw:browser [pid=6779] <process did exit: exitCode=0, signal=null>
error: Renderer test browsers did not close within 4000ms
(fail) rendered font integrity > reuses pinned font bytes and refuses tampered cache assets [19003.64ms]
  ^ this test timed out after 15000ms.
```

Unlike the screenshot-injection case, the cache test does not install nested page/locator/screenshot spies; both cases use the fixture's shared browser-launch instrumentation. This broadens the observed boundary beyond nested screenshot spies without identifying the transport's internal cause. The push's separate screenshot failure has the same sequence: screenshot start at 01:39:56.832 UTC, pipe disconnection at .874, browser exit 0 at .901, then explicit test/cleanup deadlines. Subsequent recipe tests passed in both jobs, preserving the evidence that cleanup restores shared state.

| Bounded local check on unchanged source | Result |
| --- | --- |
| `timeout --kill-after=10s 45s env CI=true GITHUB_ACTIONS=true DEBUG=pw:browser,pw:api bun test src/render.test.ts -t 'reuses pinned font bytes and refuses tampered cache assets'` | GREEN on Bun 1.3.14: 1 pass, 18 filtered out, 0 fail, 3 assertions; test 1,351.57 ms, process 2.08 s |
| `.venv/bin/python -m baseline.releases --release 1.0.0` | GREEN: unchanged 1,824-input dataset and evaluation-protocol fingerprints |
| `.venv/bin/python -m baseline.finalize --run-dir results/runs/1.0.0/2026-09-08-all-except-fable --verify` | GREEN: immutable 8,102-response seal and 728-input comparison verified |

The passing focused control does not erase either hosted failure or prove the intermittent issue resolved. [ci-01](../ci-01-browser-transport.md) remains open; this follow-up changes only documentation, with no renderer/test edits or paid inference. Raw logs: `/tmp/fontbench-exact-hosted-pr-failed.log`, `/tmp/fontbench-exact-hosted-push-failed.log`, `/tmp/fontbench-exact-cache-focused.log`, `/tmp/fontbench-exact-cache-release.log`, and `/tmp/fontbench-exact-cache-seal.log`.

## Final bounded retry and current-head control

The one authorized [PR retry, attempt 2](https://github.com/eob/fontbench/actions/runs/34299994333/attempts/2), retained head `3c3b58875883a23b4c07c9c09286f9778e850027` and again failed the cache case during its first render. Its screenshot began at 01:43:10.674 UTC, the debugging pipe disconnected at .751, and Chromium exited with code 0 at .773. The unchanged 15-second test deadline and four-second cleanup deadline produced a 19,001.33 ms failure. The nested screenshot case passed in 308.41 ms; the complete browser phase reported 79 passes, one failure, and 274 assertions in 33.07 seconds. No further hosted retry was requested. Run metadata from `gh run view 34299994333 --json attempt,headSha,conclusion,url` confirms attempt 2 and conclusion `failure` at this exact head.

The final local control used the existing full ordered CI browser command, including its environment, diagnostics, and external process watchdog. It did not alter source, tests, test deadlines, or expectations:

| Exact current-head local gate | Result |
| --- | --- |
| `env CI=true GITHUB_ACTIONS=true DEBUG=pw:browser,pw:api timeout --kill-after=15s 180s bun run test:ts` | GREEN: 80 pass, 0 fail, 277 assertions; 10.34 s |
| `bun run typecheck` | GREEN: exit 0 |
| `.venv/bin/python -m pip wheel . --no-deps --wheel-dir /tmp/fontbench-exact-current-wheels` | GREEN: built `fontbench-1.0.0-py3-none-any.whl` |
| Renderer/test/protocol/data comparison to `9d3905184d995c4daa6f5f50a5fefa25a6ac04f5` | Unchanged: `git diff --quiet` exits 0 for `src`, `baseline/evaluator.py`, `baseline/providers.py`, `baseline/prompt.txt`, `baseline/finalize.py`, `baseline/runner.py`, `releases`, `dataset`, `results`, `config`, `bun.lock`, `package.json`, and `.github/workflows/ci.yml` |

The complete Git change list since that fully green hosted commit contains only report presentation (`README.md`, `baseline/build_page.py`, `site/index.html`), its two new Python regressions (`tests/test_build_page.py`), and ticket/evidence documentation. Current presentation validation already passed all 452 Python tests; the frozen release and immutable seal were reverified immediately before this control, as recorded above.

The source has passing current-head local benchmark gates and an unresolved current-head hosted browser-transport failure. It must not be described as fully green in hosted CI. Retain the failure and the differing local outcome in [ci-01](../ci-01-browser-transport.md); no new inference, source repair, or test workaround is part of this documentation update. Logs: `/tmp/fontbench-exact-hosted-pr-retry-failed.log`, `/tmp/fontbench-exact-hosted-pr-retry-metadata.json`, `/tmp/fontbench-exact-current-ts-gate.log`, `/tmp/fontbench-exact-current-typecheck.log`, and `/tmp/fontbench-exact-current-wheel.log`.
