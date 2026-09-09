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

Final CI review adds `--kill-after=15s` to the 180-second process watchdog so a stuck browser cleanup cannot ignore the termination signal indefinitely. This only bounds a stalled test process; normal assertions, browser behavior, and per-test deadlines remain unchanged.
