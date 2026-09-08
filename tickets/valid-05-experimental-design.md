# valid-05-experimental-design: Remove layout shortcuts and disclose benchmark scope

- **Status**: In Progress
- **Branch**: `valid-01-benchmark-audit`
- **Base**: `14e792f`
- **Machine**: eob-dev2
- **Harness**: codex
- **Session ID**: `01a082ae-164d-73f2-a49e-a3d6e48adfaf`
- **Assignee**: Edward Benson

## Evidence

The original recipes couple width and tracking with line height. On the September 7 manifest, a lookup using only card width predicts 578/639 line-height labels (90.45%); using tracking predicts the same count. Every medium card has loose line height. The historical set has 900/1,000 correct width-only predictions. The frozen set contains only one example per supported weight/modifier combination, so conditioning on font support retains this confound.

`bun test src/recipes.test.ts` before implementation:

```text
Expected length: 3
Received length: 1
(fail) every weight/modifier combination samples all spacing and width levels
Expected: 3
Received: 2
(fail) card width and tracking cannot determine line-height labels
0 pass
2 fail
```

## Plan

1. Replace 20 fixed recipes with 60 recipes: four weights × five modifiers × three layout repeats.
2. Every supported weight/modifier combination contributes every tracking, line-height, and width level; rotate phases to remove deterministic cross-axis mappings.
3. Report final corpus census, per-family/label distributions, duplicate/conflicting pixels, and width/tracking shortcut baselines.
4. Document the task as recognition of a fixed pangram and declared CSS settings, with explicit typography taxonomy, aliases, and synthetic small-caps policy. Avoid generalization claims beyond the frozen corpus.

## Decisions and durable findings

- Supporting font weights vary; exact global family balance cannot be achieved by pretending absent faces exist. Publish per-family counts and dimension distributions and compare identical complete cohorts.
- The expanded design permits up to 3,000 candidates; no paid model requests are part of this audit. Final runs must use the new fingerprint and a separately chosen spending limit.
- Category is a declared taxonomy and is partly predictable from family identity. The six scores are distinct task dimensions, not six statistically independent measurements.
- Use one shared two-line pangram for every sample to make inter-line distance observable; text content itself remains fixed across labels.
