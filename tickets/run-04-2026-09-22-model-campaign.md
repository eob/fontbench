# run-04-2026-09-22-model-campaign: New OpenAI and Anthropic models

- **Status**: In Progress
- **Branch**: `main` (direct repository data push)
- **Machine**: `eob-dev2`
- **Harness**: `codex`
- **Assignee**: Edward Benson
- **Run ID**: `2026-09-23-openai-anthropic`

## Goal

Measure the frozen FontBench V1.0.0 release with only the models released on 2026-09-22: `gpt-6-sol`, `gpt-6-luna`, and `claude-opus-5-5`. Commit and push a sealed, FontBench-specific run. Do not rerun any earlier model or alter benchmark inputs, prompt, adapters, or scoring.

## Sources and decisions

- [OpenAI changelog](https://developers.openai.com/api/docs/changelog) identifies the two GPT-6 IDs and release date. [OpenAI pricing](https://developers.openai.com/api/docs/pricing) gives standard rates of $2/$10 and $0.10/$0.50 per million input/output tokens.
- [Anthropic model card](https://platform.claude.com/docs/en/models/opus-5-5/overview) identifies `claude-opus-5-5`, the release date, default medium adaptive thinking, and $4/$20 rates.
- `config/models.json` already has four enabled OpenAI models; the catalog loader limits each provider to five. A separate `config/models.2026-09-22.json` keeps all earlier models selectable in their original catalog and restricts this campaign to the three new IDs.
- All three use the existing native provider adapters and model-default reasoning settings. A 16,384-token output cap allows headroom for reasoning. The released evaluation protocol and task set remain fixed.

## Red evidence

Before the catalog addition, this command failed for the expected reason:

```sh
.venv/bin/python -c 'from baseline.model_config import load_model_config; m=load_model_config(); need={"gpt-6-sol","gpt-6-luna","claude-opus-5-5"}; have={x["id"] for x in m}; assert need <= have, f"Unselectable models: {sorted(need-have)}"'
```

```text
AssertionError: Unselectable models: ['claude-opus-5-5', 'gpt-6-luna', 'gpt-6-sol']
```

## Plan and gates

- [x] Verify the three-model catalog loads, reverses to the same Red result without `--config`, and passes a small offline mock run.
- [x] Verify the frozen release and relevant model-config checks.
- [x] Probe one live image per model; inspect structured responses, output usage, and API errors.
- [ ] Run the complete 1,824-image release for only these three IDs; resume retryable infrastructure failures as needed.
- [ ] Review coverage, errors, response profiles, and costs. Commit the closed source checkpoint and exports.
- [ ] Seal with `baseline.finalize --scope common`, verify the seal, commit and push the publication.

## Validation evidence

| Gate | Base commit | Result |
| --- | --- | --- |
| Catalog load of `config/models.2026-09-22.json` | `14b09c3a` + new catalog | Exactly the three expected IDs, provider IDs, prices, and 16,384 output caps |
| Mock runner, 3 tasks/model | `14b09c3a` + new catalog | 3/3 saved per model, $0 estimated spend |
| Reversion check using original `config/models.json` | `14b09c3a` | The same three IDs remain absent |
| `bun run validate:release` | `14b09c3a` + new catalog | 1,824 tasks; dataset and protocol fingerprints match release descriptor |
| `bun run test:python` | `14b09c3a` + new catalog | 456 passed, 0 failed |
| `bun run test:ts` | `c4ed9c88` | 80 passed, 0 failed |
| `bun run typecheck` | `c4ed9c88` | Clean |

Live probe at `c4ed9c88` used the first seeded task in the resumable run. All three returned valid structured predictions, metered token usage, and no provider error:

| Model | Input / output tokens | Cost | Latency |
| --- | ---: | ---: | ---: |
| `gpt-6-sol` | 692 / 1,489 | $0.016274 | 23.4s |
| `gpt-6-luna` | 692 / 671 | $0.000405 | 13.2s |
| `claude-opus-5-5` | 1,320 / 55 | $0.006380 | 2.7s |

The first full invocation was gracefully interrupted for a durable WIP checkpoint before increasing concurrency. Its SQLite integrity check returned `ok`; the run retained 154/155/155 final responses for Opus/Sol/Luna, $3.111 estimated spend, and zero unresolved errors. The next invocation resumes exactly the remaining tasks.

At 391 final responses, Anthropic returned HTTP 400: `Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.` The one affected task remains retryable; it is not scored as a model answer. Sol and Luna continued without errors. A second graceful checkpoint at 391/614/613 final responses for Opus/Sol/Luna (1,618 total) passed SQLite `integrity_check`. The next invocation selects only Sol and Luna to finish their corpus without prematurely retrying Opus; a single Opus retry follows the OpenAI completion.

The OpenAI-only invocation reached 915 Sol and 914 Luna finals with zero OpenAI errors. A third graceful checkpoint passed SQLite `integrity_check` at $15.532 cumulative estimated spend. The next invocation raises concurrency from 16 to 24 for the same two models; concurrent benchmark runners have finished, and this scheduling change does not alter any model configuration or the frozen protocol.

At concurrency 24, Sol and Luna each reached 1,428/1,824 final responses with no OpenAI retries or provider errors. A fourth graceful checkpoint passed SQLite `integrity_check` at $22.666 cumulative estimated spend. The remaining 396 tasks per GPT model resume with the same catalog, run ID, and inference settings.

## Durable findings

Pending.
