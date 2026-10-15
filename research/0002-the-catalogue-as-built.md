# 0002 — The catalogue as built

- Date: 2026-10-15
- Status: accepted

## Context

0001 proposed a shape "for the new session to confirm". This records what was
confirmed, what changed, and why, so the apps adopting it know what they are
pinning.

## Decision

### Name: `llm-catalogue`

The GitHub repo was created as `lachlancahill/llm-catalogue`, so the distribution is
`llm-catalogue` and the import is `llm_catalogue`. 0001's `llm-catalog` appears in the
copied text only. An app adds it with
`uv add "git+https://github.com/lachlancahill/llm-catalogue" --branch main`.

### Layout

```
main.py                       # runs refresh
src/llm_catalogue/
  __init__.py                 # get(key), ALL — the join and nothing else
  model.py                    # CatalogModel and its guards
  measured.py                 # kind 2, typed, with provenance
  manual.py                   # kind 1 that no provider publishes machine-readably
  published.json              # kind 1, written by refresh
scripts/                      # a package: run as `uv run -m scripts.<name>`
  common.py                   # logging, gateway URLs, keys from the environment
  refresh.py
  probe_model.py              # OpenAI-compatible gateways: temperature, tools, replay, effort
  probe_anthropic.py          # Claude: temperature, tools with thinking, forced tool_choice
  probe_images.py
```

Changes from 0001's proposal:

- **`manual.py`, not `manual_prices.py`.** OpenAI publishes its context window
  nowhere machine-readable either, so the file holds every hand-typed kind-1 fact,
  not only prices.
- **`scripts/` is a package**, so `main.py`, the probes and the tests all import
  `scripts.common` the same way. The SDKs it needs are in the `scripts` dependency
  group and never reach a consumer. The runtime package has no dependencies, which
  was checked by installing the wheel into a clean 3.12 venv.
- **Claude has its own probe.** The native SDK and the Chat Completions shape share
  almost nothing, and the questions differ: the Models API already answers effort
  and thinking, so the probe checks only what it does not say.
- **`gateway` and `api_model_name` are derived from `key`**, not stored beside it,
  so the three can never disagree.

### Each fact has exactly one writer

The loader joins `published.json` + `manual.py` + `measured.py` per key at import.
The import fails if the key sets differ, if `manual.py` has a stray key, or if two
files set the same field. Every kind-1 field is required, so a gap is an import
error, not a silent default. `refresh` reads `measured.py`'s keys with `runpy`
rather than importing the package, because a newly added key is exactly the case
where the join fails until refresh has run.

### Unmeasured is `None`, not `False`

Kind-2 booleans are `bool | None`. MiMo's images and temperature were unmeasured
when 0001 was written, and `False` would have claimed a measurement nobody made.
`None` is falsy, so `if model.supports_images:` still treats unmeasured as
unsupported. That keeps the chat app's long-standing safe direction, where a wrong
False loses a feature and a wrong True fails requests.

### `none` is on the ladder when it measurably turns reasoning off

`effort_ladder` lists the values that behave differently, weakest first, and that
includes `none` where it measured off. This makes 0001's "MiMo's ladder is empty"
into `("none",)`. 0001's own seed is inconsistent otherwise: it records
V4.1-Flash as `none/high` and accepts fitness's `none/low/high/max` on GLM-5.3, both
with `none` on. An app's menu is a subset of the ladder, so chat's planned "no menu
for MiMo" is unaffected.

What unset does is `unset_effort`: `off`, `on`, `below_max`, or a ladder level
where the provider documents one (Opus 5.5 `medium`, Sonnet 5.5 `high`).

### Fields 0001 did not list

- `discount`: DeepInfra's promotional fraction, already applied to the prices (0003).
- `long_context_above_tokens` and its two prices: OpenAI bills prompts over 272K
  at a higher rate (0003). Every other gateway has `None`.
- `supports_forced_tool_choice`: 0001 asked for Claude's 400 to be recorded.
- `tools_need_responses_api`: 0001 asked for OpenAI's "tools with reasoning are a
  400 on /v1/chat/completions" to be recorded as a fact of the endpoint. Chat's
  `supports_tools` becomes `entry.supports_tools and not entry.tools_need_responses_api`.
- `price_source`: the listing URL, or the pricing page and the date it was read.

### Refresh

DeepInfra's listing is public, so refresh needs three keys: Together's, Anthropic's
and OpenAI's. It refuses to use `OPENAI_API_KEY` while `OPENAI_BASE_URL` points at
another gateway (Lachlan's shell). A model a gateway no longer lists writes nothing
and exits 1. A deprecation is written, because it is true, and exits 1, and then
`test_no_entry_is_deprecated` fails until the entry is removed. No dates are
written into `published.json`, so an unchanged listing is an unchanged file, and git
dates each change.

### Secret scanning

pre-commit runs gitleaks and ruff. gitleaks was checked against a randomly generated
Anthropic-shaped key and blocked it (rule `anthropic-api-key`).

## Why

Every adjustment either removes a way for two sources to disagree (derived
identity, one writer per fact, required kind-1 fields) or stops the catalogue
claiming more than was measured (`None`, `price_source`, provenance strings).
Those are the two failures 0001 was written about.

## Alternatives considered

- **Two dataclasses (Published, Measured) composed into CatalogModel.** Every field
  list would be written twice. Dicts of keyword arguments into one dataclass let
  the constructor reject an unknown or missing field.
- **`False` for unmeasured.** Rejected above. It is the bug in legal's MiMo menu, in
  the opposite direction.
- **A `cost()` method on CatalogModel.** Each app already has one, shaped to its own
  usage records. It is worth sharing once the long-context tier needs handling in
  more than one app; not before.

## Consequences

- Adding a model is three steps: probe, add to `measured.py` (and `manual.py` for
  Anthropic/OpenAI), then `uv run main.py && uv run pytest`.
- `manual.py` is the one place prices can drift. Its source strings carry the read
  date. Re-read both pricing pages whenever refresh runs.
- An app that computes cost must handle `long_context_*` for OpenAI or knowingly
  under-charge above 272K.
