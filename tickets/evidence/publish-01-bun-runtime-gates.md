# publish-01: Bun runtime regression and CI pin

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

Pin Bun 1.3.14 in CI and `package.json`, and document that supported development runtime in the README. Future runtime upgrades must pass the complete ordered renderer suite, not only isolated cases. No dependency, renderer, test, evaluator, provider, prompt, released dataset, or sealed result bytes changed.

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
| Hosted CI with explicit runtime pin | Pending parent push/retest |

Local raw logs: `/tmp/fontbench-pr1-ci-failure.log`, `/tmp/fontbench-render-local-bun1314-control.log`, `/tmp/fontbench-render-bun142-red.log` (isolated case passed despite the filename), `/tmp/fontbench-render-bun142-full.log`, `/tmp/fontbench-render-bun1314-full-control.log`. The durable excerpts and command results above do not depend on retaining those temporary files.
