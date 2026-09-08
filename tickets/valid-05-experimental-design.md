# valid-05-experimental-design: Remove layout shortcuts and disclose benchmark scope

- **Status**: Completed — compact sampling explicitly accepted
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
2. Every supported weight/modifier combination contributes every tracking, line-height, and width level; rotate phases to remove the global width/line-height and tracking/line-height mappings.
3. Report final corpus census, per-family/label distributions, duplicate/conflicting pixels, and width/tracking shortcut baselines.
4. Document the task as recognition of a fixed pangram and declared CSS settings, with explicit typography taxonomy, aliases, and synthetic small-caps policy. Avoid generalization claims beyond the frozen corpus.

## Decisions and durable findings

- Supporting font weights vary; exact global family balance cannot be achieved by pretending absent faces exist. Publish per-family counts and dimension distributions and compare identical complete cohorts.
- The expanded design permits up to 3,000 candidates; no paid model requests are part of this audit. Final runs must use the new fingerprint and a separately chosen spending limit.
- Category is a declared taxonomy and is partly predictable from family identity. The six scores are distinct task dimensions, not six statistically independent measurements.
- Use one shared two-line pangram for every sample to make inter-line distance observable; text content itself remains fixed across labels.


## Independent sampling review and accepted limitation

The user confirmed that compact sampling is intended; full factorial coverage is unnecessary. The final 60-candidate recipe set contains a conditional relationship: `lineHeightIndex = (kerningIndex + modifierIndex) % 3`. Thus an observer who knows the recipe and recognizes modifier and tracking can infer line height without measuring its pixels. This is an accepted sampling limitation, not a claim of causal isolation or independent factors. Expanding to nine layout repeats would cross tracking and line height; fully crossing all three layout axes would require 27 repeats (540 candidates per family before support filtering), which is outside the accepted scope.

Independent census of the 1,824 accepted inputs verifies that each tracking, line-height, and width level occurs exactly 608 times and all nine width/line-height combinations occur:

| Width | Tight line height | Normal line height | Loose line height |
| --- | ---: | ---: | ---: |
| Narrow | 190 | 212 | 206 |
| Medium | 206 | 190 | 212 |
| Wide | 212 | 206 | 190 |

The corresponding best width-only lookup achieves 636/1,824 (34.87%), compared with the earlier 90.45% shortcut. The best tracking-only lookup achieves 756/1,824 (41.45%); imperfect balancing remains because supported modifiers differ across fonts. These are disclosed sampling properties. Exact cohort and pixel identity are frozen in `dataset/fontbench-2-rendered/manifest.json` and the root audit evidence.
