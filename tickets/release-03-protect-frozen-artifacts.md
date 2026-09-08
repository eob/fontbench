# release-03-protect-frozen-artifacts: Protect registered release inputs from generation

- **Status**: Completed (local implementation and verification)
- **Branch**: `valid-01-benchmark-audit` (coordinated delivery)
- **Base**: `d69e87e`
- **Machine**: eob-dev2
- **Harness**: codex
- **Session ID**: `01a082ae-164d-73f2-a49e-a3d6e48adfaf` (task `/root/verify_render_closure`)
- **Assignee**: Edward Benson

## Goal

Keep FontBench V1.0.0's registered rendering and Harbor package immutable during ordinary generation. Candidate development output must remain usable, including offline rendering with retained release font assets.

## Plan

1. [x] Prove existing renderer and packager reach unsafe output operations before recognizing registered release directories; intercept writes so the release remains untouched.
2. [x] Add one shared, fail-closed registry guard, including equal, ancestor, descendant, and symlink-resolved destinations.
3. [x] Move generator defaults and the packaging CLI to candidate directories.
4. [x] Check malformed registries, protected aliases, safe siblings, and separate offline replay output; capture Green and isolated source-reversion evidence.

## Decisions and durable findings

- Release registry paths are repository-relative. `dataset_manifest` protects its entire parent directory; `harbor_dataset` protects the entire packaged task tree.
- Output checks run before filesystem mutation or browser launch. Source font caches may point into frozen releases because replay reads them and writes to a distinct candidate destination.
- Existing corpus and package paths and bytes remain unchanged. This guard prevents accidental overwrite; it does not attempt to constrain an adversarial process modifying the registry or racing filesystem aliases.
- `releases/*.json` is required. Missing directories, invalid JSON, absent required paths, and paths containing traversal components fail without mutation. New output directories are checked through their nearest existing parent, so aliases cannot bypass protection simply by adding nonexistent child paths.
- Development defaults are `dataset/candidate-rendered` and `dataset/candidate-harbor`. The packaging CLI validates the candidate manifest before generating its candidate package.
- New development packages identify themselves as `fontbench-candidate` version `0.0.0`. The frozen V1.0.0 release retains its original package bytes and is identified by its release registry entry.
- The exported `FontAssets` constructor applies the same output guard, so callers cannot bypass protection by invoking the cache helper directly. `cacheDir` is a read source: added assets and updated lock metadata go only to `outputDir`, which must be mutable.

## Red and reversion evidence

The original renderer and packager both reached intercepted filesystem writes when targeting registered release directories. The intercept throws before the actual operation, so this proof did not touch frozen output:

```text
Expected pattern: /Frozen release output/
Received message: "Filesystem mutation reached"
0 pass
2 fail
```

The same two failures recur with the exact `d69e87e` source in an isolated temporary checkout and current regression tests. See [original Red](evidence/release-03-red.log) and [source reversion](evidence/release-03-reversion.log).

A boundary regression caught the filesystem root escaping a naive separator-prefix ancestor check. Replacing that ancestor condition with `path.relative` rejects `/` as an ancestor too. Its original [boundary Red](evidence/release-03-boundary-red.log) records 22 passes and one expected failure.

The existing public metadata test also asserts that a newly built candidate has name `fontbench-candidate` and version `0.0.0`. It failed against the old `fontbench-2` / `2.0.0` generator metadata and passed after the development-only descriptor update; [metadata Red](evidence/release-03-candidate-metadata-red.log) and [exact-source reversion](evidence/release-03-candidate-metadata-reversion.log) retain the mismatches.

Independent review found that directly constructing the exported `FontAssets` helper with a frozen output directory could bypass the renderer guard. An intercepted-write regression reproduced `Filesystem mutation reached` before the shared guard was added to its constructor. [Cache Red](evidence/release-03-cache-red.log) and [isolated original-source reversion](evidence/release-03-cache-reversion.log) retain that failure. An inverse test reads a pinned asset from the actual registered cache, adds a separate fixture font and lock entry to candidate output, and confirms the original cached asset, complete source lock, and source font file list remain unchanged. No network requests are permitted by that fixture.

## Validation gate matrix

| Gate | Source base | Result |
| --- | --- | --- |
| Generator release-target regressions before guard | `d69e87e` | Expected Red: 0 passed, 2 failed before any write |
| Same tests against isolated original renderer/packager | `d69e87e` | Same 0 passed, 2 failed; identical causal messages |
| `bun test ./src/release_protection.test.ts` | `d69e87e` + guard | 23 passed, 0 failed; overlap, aliases, malformed registry, and allowed sibling checks |
| `bun test ./src/render.test.ts ./src/generate_harbor_dataset.test.ts ./src/release_protection.test.ts ./src/font_assets.test.ts` | `d69e87e` + guard | 74 passed, 0 failed; 13.41 s |
| `bun test ./src/generate_harbor_dataset.test.ts` after candidate descriptor update | `d69e87e` + guard and metadata | 33 passed, 0 failed; 387 ms |
| `bun test ./src/font_assets.test.ts` after cache helper guard | `d69e87e` + guards | 3 passed, 0 failed; registered source-cache preservation and output refusal |
| `bun test ./src/render.test.ts ./src/font_assets.test.ts ./src/release_protection.test.ts` after cache helper guard | `d69e87e` + guards | 43 passed, 0 failed; 12.90 s |
| Stopped-server font-cache replay to a separate output | `d69e87e` + guard | 15 image hashes match; original cached manifest remains byte-identical |
| `bun run typecheck` | `d69e87e` + guard | Passed |
| `git diff --quiet d69e87e -- dataset/fontbench-2-rendered dataset/fontbench-2` | `d69e87e` + guard | Passed; registered release artifacts unchanged |
| `git diff --check` | `d69e87e` + guard | Passed |

The simplifyfu and comment review retained one shared guard and its nontrivial existing-parent resolver. No alternate bypass mode, extra generation configuration layer, test timeout change, or evaluator/protocol change was added.
