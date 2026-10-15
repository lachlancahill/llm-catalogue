# 0001 — Why this repo exists

- Date: 2026-10-15
- Status: accepted. Copied from lachlancahill-com-chat research/0048, where the plan was made.

> Copied verbatim below, so the reasoning lives where the work does. Two things changed
> in the building, both recorded in 0002: the repo and package are named `llm-catalogue` /
> `llm_catalogue` (the GitHub repo was created with that spelling), not `llm-catalog`; and
> the proposed layout was adjusted. Facts found stale since this was written are in 0003.

---

# (chat 0048) A shared model catalog across projects

- Date: 2026-10-15
- Status: accepted (plan). The work continues in the new `llm-catalog` repo.

## Context

Lachlan asked to add `XiaomiMiMo/MiMo-V2.6-Pro` and move the Claude entries to 5.5, and
asked whether model settings should live in one place, given how many projects call
Claude, OpenAI or DeepInfra.

Five live projects keep a registry of their own, each with its own `ModelSpec`. Paths are
under `~/PycharmProjects/`:

| Project | Registry | Python | Notes |
|---|---|---|---|
| lachlancahill-com-chat | `src/chat_app/llm/models.py` | 3.13 | The richest registry, and the only one calling Anthropic. Native Anthropic SDK plus OpenAI-compatible clients. |
| wandly-data-automation | `webapp/chat/models.py`, `pricing.py` | 3.12 | Keys entries by gateway (`deepinfra:` / `together:`). Fetches prices at runtime. |
| legal-assistant | `src/legal_app/llm.py`; `services/ingest/src/ingest/constants.py` | 3.13 | OpenAI models go through the Responses API. |
| moving-house | `src/moving_house/constants.py` | 3.13 | Two GLM entries. Computes cost from its own prices. |
| fitness | `src/fitness/coach/models.py` | 3.12 | Two entries with effort ladders only. |

Two more projects carry bare model-id strings and stay as they are: local_reverse_proxy
(`openai/gpt-oss-120b`) and trucking-automation (`gpt-5.4`, `gpt-5.6-luna`).

## What the duplication has already cost

Checked against the live sources on 2026-10-15: DeepInfra's `/models/list`, Anthropic's
Models API and OpenAI's model list.

| Fact | Live | What the copies say |
|---|---|---|
| GLM-5.3 price | $0.90 / $4.00, cache 0.22222222x | chat $1.40 / $4.40, 0.18571429x; moving-house $1.20 input; legal correct |
| Qwen3.8-27B price | $0.20 / $2.50, cache 0.25x | chat $0.40 / $3.00, 0.1x |
| Qwen3.8-2.4T-A95B | deprecated 2026-10-12, `replaced_by` GLM-5.3 | still offered in chat and legal |
| DeepSeek-V4.1-Flash efforts | one measurement (wandly 0169) | chat `none/high`; wandly `none/high/xhigh/max`; fitness all seven |
| MiMo-V2.6-Pro efforts | wandly 0178: only `none` separates; 3 samples × 8 levels | legal offers `low/high/max` from a 200/tool-call check |
| Claude Sonnet 5 price | Anthropic now lists $2 / $10 | chat $3 / $15 |

None of these was a judgement call. Each is a fact somebody transcribed or measured
once, in one repo, and that went stale or never reached the others. Legal's MiMo menu
breaks 0007's "acceptance is not support" rule, and nobody noticed, because the
measurement that refutes it lives in another repo.

## Three kinds of fact

The registries mix three things with different owners and different rates of change.
This split is the core of the design.

1. **Published by the provider**: price, cache multipliers, context window, the
   provider's output cap, deprecation and `replaced_by`. DeepInfra publishes all of
   these on `/models/list`, and Together publishes prices on `/v1/models`. Anthropic's
   Models API gives the context window, output cap and the effort and thinking
   capability tree, but no price. OpenAI publishes only the model ids. These go in the
   catalog and are **refreshed from the source, never transcribed**. Anthropic and
   OpenAI prices are the one exception: they are hand-entered, with the date and the
   page they came from.
2. **Measured behaviour of a (gateway, model) pair**: tool calling, temperature, image
   input, the effort ladder (the levels that separate, per 0007), what sending no effort
   does, which delta field carries reasoning, whether the gateway reports
   `estimated_cost`, and whether a replayed reasoning block survives. These cost money
   and wall clock to measure, and they do not depend on the app. They go in the catalog,
   measured once. Wandly's rule (0156) holds: the key is gateway plus model,
   `deepinfra:zai-org/GLM-5.3`, never the model alone.
3. **The app's decisions**: which models the menu offers, the default model,
   `default_effort`, the menu as a subset of the measured ladder, display names, the
   output ceiling the app chooses (chat 64,000; wandly 32,768; moving-house 32,000), and
   quality at a setting on that app's workload. Legal's "`low` skipped the tools and
   invented a citation" is quality at a setting. Data retention per account (wandly
   0060, 0068) is also an app decision. **These stay in each app.**

## Decisions

1. **A new repo, `llm-catalog`, holds kinds 1 and 2.** It is not a shared client and not
   runtime configuration.
2. **The repo is public on GitHub.** Every app builds its image in Cloud Build inside its
   own GCP project: the chat app's CI trigger and `gcloud builds submit`, legal,
   moving-house and wandly's `gcloud builds submit`, fitness's `gcloud run deploy
   --source`. None of these builds has GitHub credentials inside the Docker build. A
   private repo would need an access token in Secret Manager in five projects, a BuildKit
   secret mount in five Dockerfiles, and five rotations. The content is prices and
   capability flags, which is safe to publish under the rules in decision 7.
3. **Apps consume it as a uv git dependency that tracks `main`.**
   `uv add "git+https://github.com/lachlancahill/llm-catalog" --branch main` writes the
   source to `[tool.uv.sources]`, and `uv.lock` pins the exact commit. Builds use
   `uv sync --frozen` / `--locked`, so they stay reproducible while `main` moves. To
   update an app: `uv lock --upgrade-package llm-catalog`, run its tests, and deploy.
   An app that does not want a new model does nothing. No tags and no submodules: a
   submodule would need `git submodule update` and `--recursive` clones in every build.
4. **Each Dockerfile installs `git` where `uv sync` runs**, because uv needs a `git`
   binary to fetch a git dependency and every image starts from a slim base:
   ```dockerfile
   RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
   ```
   Chat, legal and moving-house have a separate builder stage, so `git` stays out of
   the deployed image. Fitness and wandly are single-stage and carry it. **The first
   real Cloud Build in the pilot is what proves this works.**
5. **PyPI is deferred, not rejected.** It would remove `git` from the images, but every
   update would need a version bump and a tag, releases are immutable, and the package
   becomes a public product. Switching later changes one source line per app and no app
   code. The name `llm-catalog` was free on 2026-10-15 (PyPI's JSON API returned 404).
6. **Build-time pinning, never a runtime fetch.** The apps live in five GCP projects,
   and 0035 is trying to cut cold start. Most importantly, a wrong flag is a 400 on every
   request (CLAUDE.md, rule 1), and a runtime fetch would ship it to every app at once,
   past every app's tests. Wandly's runtime price fetch for Together cost (`pricing.py`)
   is a separate concern and stays.
7. **Public-repo rules.**
   - No key ever enters the repo. Scripts read keys from the environment or Secret
     Manager at run time, and a secret scanner runs as a pre-commit hook. This repo's
     history still holds dead keys.
   - Provenance cites notes by number, such as "wandly 0178", and copies only
     measurements. Never quote the surrounding context: wandly's notes name clinic
     staff, customers and their balances.
   - No GCP project ids or secret names go in the repo.
   - Assume anything pushed is permanent.

## The `llm-catalog` repo

Lachlan-style throughout: uv, ruff, `logging`, constants instead of CLI arguments, a
`research/` directory, and pytest. `requires-python = ">=3.12"`, because fitness and
wandly run 3.12. The runtime package has **no dependencies**. The provider SDKs the
scripts need (`openai`, `anthropic`, `requests`) go in a dependency group, which
consumers never install.

Proposed shape, for the new session to confirm:

```
llm-catalog/
├── pyproject.toml
├── main.py                       # runs refresh (the common task); probe runs from scripts/
├── src/llm_catalog/
│   ├── __init__.py               # get(key) -> CatalogModel, ALL; nothing else public
│   ├── model.py                  # the frozen CatalogModel dataclass and its __post_init__ guards
│   ├── measured.py               # hand-written: kind-2 facts, with provenance comments
│   ├── manual_prices.py          # hand-written: Anthropic and OpenAI prices, dated
│   └── published.json            # machine-written by refresh: kind-1 facts
├── scripts/
│   ├── refresh.py                # rewrites published.json from the live listings; fails on deprecation
│   ├── probe_model.py            # merged probe (below)
│   └── probe_images.py
├── tests/
└── research/
    ├── README.md
    └── 0001-why-this-repo-exists.md   # a copy of this note
```

**The split between `measured.py` and `published.json` mirrors kinds 2 and 1**, so each
file has one writer. A script writes the JSON and a person writes the Python, whose
comments carry provenance as `models.py` does today. The loader joins them by key. A test
fails on a key that is in one file and not the other, on a key whose gateway marks it
deprecated, and on any CatalogModel whose guards fail.

**CatalogModel fields**, which are the union of what the five registries record today
minus kind-3:
- **Identity:** `key` (`gateway:model_id`), `gateway`, `api_model_name`.
- **Kind 1:** `prompt_price_per_mtok`, `completion_price_per_mtok`,
  `cache_read_multiplier`, `cache_write_multiplier`, `context_tokens`,
  `provider_max_output_tokens`, `deprecated_at`, `replaced_by`.
- **Kind 2:** `supports_tools`, `supports_temperature`, `supports_thinking` (Anthropic
  adaptive), `supports_images`, `effort_ladder` (the levels that separate, weakest
  first), `unset_effort` (`"off"`, `"on"` or `"below_max"`, the three behaviours seen
  so far), `reasoning_field`, `reports_cost`, `preserves_replayed_reasoning`.
- **Provenance:** a short `measured` note per entry: date, script, samples and a source
  note number.

Carry the guards from chat's `ModelSpec.__post_init__` into CatalogModel: thinking and
temperature are mutually exclusive. The app-side guard ("`default_effort` must be in
the menu") becomes "the menu must be a subset of `effort_ladder`", checked in each app.

**`refresh.py`** reads DeepInfra's `/models/list` (cents per token ×10,000 = $/Mtok;
`rate_per_input_token_cached` is already the multiplier), Together's `/v1/models` and
Anthropic's `models.retrieve`, for every key in the catalog. It rewrites
`published.json` and logs each change. It exits non-zero on a missing or deprecated
model. Run it whenever you touch the repo, and before bumping any app.

Readers already exist: wandly's `webapp/chat/pricing.py` (`_deepinfra_rows`,
`_together_rows`). Together's gateway 403s `urllib`'s user agent, so use `requests`.

**`probe_model.py`** merges four existing scripts:
- chat's `scripts/probe_model.py`: temperature, tools, and the effort ladder with
  repeats and the app's output ceiling, per 0031;
- chat's `scripts/probe_images.py`;
- wandly's `scripts/probes/probe_chat_models.py`, including the
  `DOCUMENTED_EFFORTS` search-first sweep from wandly 0178 decision 3;
- wandly's `scripts/probes/probe_preserved_thinking.py`.

It prints a table to paste into `measured.py`'s comments and draws no conclusions, as
today. Carry the hard-won rules across with it:
- **Three samples settle on against off, and do not separate two levels.** Use five,
  alternating levels (chat 0031).
- **The output ceiling must be the app's**, or the probe measures its own cap (chat
  0031).
- **Unset `OPENAI_BASE_URL` and `OPENAI_API_KEY` when probing OpenAI.** Lachlan's shell
  sets both to DeepInfra, and the SDK honours them silently: on 2026-10-15 a "list
  OpenAI models" call returned DeepInfra's catalogue.

## Seed content: the first commit

Every model any of the five apps registers today, re-checked:

- **DeepInfra:**
  - `XiaomiMiMo/MiMo-V2.6-Pro`: wandly 0178. $0.43 / $0.87, cache 0.00837209x, context
    1,048,576. Calls tools and reports `estimated_cost`. Unset effort means thinking on;
    only `none` separates, so the ladder is empty. The template preserves a replayed
    reasoning block unasked. Images and temperature are unmeasured: run the image probe
    and the temperature check before an app relies on either.
  - `zai-org/GLM-5.3`, `zai-org/GLM-5.3-Flash`, `zai-org/GLM-5.2`,
    `deepseek-ai/DeepSeek-V4-Pro-0813`, `deepseek-ai/DeepSeek-V4.1-Flash`,
    `moonshotai/Kimi-K3`, `Qwen/Qwen3.8-27B`: kind-2 facts from chat `models.py` and
    wandly `models.py`. Kind-1 facts come from `refresh`.
  - `Qwen/Qwen3.8-2.4T-A95B` is **left out**: deprecated 2026-10-12.
  - **V4.1-Flash's ladder has to be settled, not merged.** The data in wandly 0169 and
    chat 0037 is the same; the two repos read it differently. Chat offers `none/high`,
    wandly `none/high/xhigh/max`, and fitness offers all seven unmeasured. Record the
    ladder 0007's bar supports, `none/high` at n=3, and let wandly re-probe if it wants
    `xhigh`/`max`.
  - Also include `openai/gpt-oss-120b` for local_reverse_proxy, if it ever adopts the
    catalog.
- **Together:** `zai-org/GLM-5.3` (wandly). Its facts are its own, never inherited from
  the DeepInfra twin (wandly 0156).
- **Anthropic**, from the Models API on 2026-10-15:
  - `claude-opus-5-5`: 1,000,000 in, 128,000 out, efforts `low` to `max`, thinking
    adaptive only (`disabled` and `enabled` both unsupported), images. $4 / $20; cache
    reads $0.20, so **0.05x**; cache writes 1.25x.
  - `claude-sonnet-5-5`: same shape. $2 / $10; cache reads $0.20, so 0.1x.
  - **Opus 5.5 unset effort is `medium`**, not `high` as on Opus 5. Sonnet 5.5's is
    `high`, with recalibrated levels.
  - Temperature: removed on both (400), so `supports_temperature=False`.
  - Forced `tool_choice` is a 400 on both. No app sends it today; record it so none
    starts to.
- **OpenAI:** `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5` (chat) and
  `gpt-6.1-sol` (legal). All exist on the API as of 2026-10-15. Kind-2 facts from chat
  0018 and legal 0022. Tools with reasoning are a 400 on `/v1/chat/completions`, so
  record that as a fact of the endpoint.

## Rollout

1. **Build the catalog** with the seed content and the tests. Run `refresh` against the
   live APIs once.
2. **Pilot consumer 1: lachlancahill-com-chat.** Make the two changes Lachlan asked for
   through the catalog:
   - Replace the measured and published fields in `models.py` with values from
     `llm_catalog.get(...)`. Keep chat's `ModelSpec` field names, because the rest of
     the app reads `model.supports_tools` and so on, so it is filled from the catalog
     entry plus chat's own fields. Chat keeps `display_name`, `default_effort`, the
     menu, `max_output_tokens` (64,000, capped at the provider's), `DEFAULT_MODEL_ID`
     and `TITLE_MODEL_ID`.
   - Add MiMo-V2.6-Pro, with no effort menu.
   - Replace Opus 5 and Sonnet 5 with Opus 5.5 and Sonnet 5.5. Set
     `default_effort="high"` on Opus 5.5 to keep today's behaviour, and fix the comment
     at `anthropic_client.py:175`, which assumes `high`.
   - **Map `anthropic/claude-opus-5` and `anthropic/claude-sonnet-5` to their 5.5
     successors** in `get_model`. Otherwise a stored Claude conversation falls back to
     GLM 5.3 at `low` (chat 0030), a silent switch of provider.
   - Remove Qwen3.8-2.4T; the GLM-5.3 and Qwen3.8-27B prices now come from the catalog.
   - Update the tests that name the old Claude ids: `test_effort.py`, `test_images.py`,
     `test_tool_budgets.py`, `test_conversation_paging.py`, `test_model_picker.py`.
   - Add `git` to the builder stage of `Dockerfile`.
   - Deploy to testing, which proves the git dependency in Cloud Build. Then deploy to
     production.
3. **Pilot consumer 2: fitness.** It is single-stage, which is the other Dockerfile
   shape. It is also the app most in need: its V4.1-Flash menu offers seven unmeasured
   levels, so it should narrow to the catalog's ladder. Its GLM-5.3 ladder is labelled
   as chat's 0034 already.
4. **Then legal-assistant**, including the `ingest` service, which names models in
   constants. Narrow MiMo to an empty menu and remove Qwen3.8-2.4T.
5. **Then moving-house.** Its GLM-5.3 input price is stale, and it computes cost from
   its own prices, so this one changes what it records.
6. **Wandly last.** It is the largest registry, with two gateways, retention per
   provider and runtime pricing. It adopts the catalog for kind 1 and kind 2 and keeps
   `Provider.retention`, `secret_name`, `api_key_env` and `pricing.py`.

At each step, write a research note in that app saying what moved to the catalog and
what stayed local.

## Alternatives considered

- **Runtime fetch** of a catalog JSON from GCS or Firestore. Rejected; see decision 6.
- **A shared client library.** The clients are where the apps differ for real reasons:
  the native Anthropic SDK and the SSE `Turn` here, the Responses API in legal, two
  gateways and preserved thinking in wandly. Sharing them couples five apps' streaming
  code for little gain. Revisit only if the same client bug gets fixed twice.
- **LiteLLM's price table or OpenRouter.** LiteLLM's table is community-maintained and
  records nothing about measured behaviour, which is the expensive half. OpenRouter
  would change who receives the data, and wandly's privacy position depends on knowing
  exactly that (wandly 0060, 0068).
- **Status quo plus a drift check in each repo.** It would catch the kind-1 drift above,
  but not the effort-ladder contradictions, and the check would be maintained five
  times.
- **A private repo, a git submodule, or PyPI now.** See decisions 2, 3 and 5.

## Consequences

- A new model means probing once in `llm-catalog`, then in each app that wants it
  `uv lock --upgrade-package llm-catalog`, a key added to its menu, its tests, and a
  deploy.
- Disagreements between projects get settled once, in the catalog, rather than living
  on in parallel.
- An app can lag the catalog, by design. `refresh` failing on a deprecation is the
  signal to bump the pins of the apps using that model.
- Until chat's pilot lands, this repo's `models.py` stays as described in the
  2026-10-15 table above, stale prices included.
