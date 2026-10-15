# 0003 — What the first refresh and probes found

- Date: 2026-10-15
- Status: accepted

## Context

0001's table of stale facts was checked against the live sources on the morning of
2026-10-15. Building the catalogue meant reading those sources again with code, and
running the probes 0001 said were missing. Some of 0001's "live" figures were
themselves wrong. This note is what each pilot app should read before adopting the
catalogue's numbers.

## Findings

### 1. DeepInfra's prices are list prices before a discount

`/models/list` carries `pricing.discount`, a fraction off both rates. Wandly's
`pricing.py` already applies it (wandly 0156). 0001's table, and legal's and chat's
registries, read the list price. **Checked against the bill:** a GLM-5.3 call of 15
prompt and 8 completion tokens reported `estimated_cost` $0.0000284375, which is
(15 × 0.90 + 8 × 4.00) × 0.625 exactly. A DeepSeek-V4.1-Flash call matched the same
way, at a 0.3 discount.

| Model | List in / out | Discount | Billed in / out | 0001 said |
|---|---|---|---|---|
| GLM-5.3 | 0.90 / 4.00 | 0.375 | **0.5625 / 2.50** | 0.90 / 4.00 |
| GLM-5.3-Flash | 0.15 / 0.50 | 0.5 | 0.075 / 0.25 | — |
| GLM-5.2 | 0.75 / 2.40 | 0.25 | 0.5625 / 1.80 | — |
| DeepSeek-V4.1-Flash | 0.20 / 0.60 | 0.3 | 0.14 / 0.42 | — |
| Qwen3.8-27B | 0.20 / 2.50 | 0.25 | 0.15 / 1.875 | 0.20 / 2.50 |

The catalogue publishes the billed price and records `discount` beside it, because a
promotion can end before an app bumps its pin. Apps on DeepInfra bill from
`estimated_cost` anyway; the catalogue price is their fallback.

### 2. OpenAI cut the GPT-5.6 line's prices and added a long-context tier

From the pricing page on 2026-10-15, standard tier, prompts up to 272K tokens:

| Model | Now (in / cached / write / out) | Chat's registry (2026-07-20) |
|---|---|---|
| gpt-5.6-sol | 4.00 / 0.40 / 5.00 / 20.00 | 5.00 / — / — / 30.00 |
| gpt-5.6-terra | 2.00 / 0.20 / 2.50 / 12.00 | 2.50 / — / — / 15.00 |
| gpt-5.6-luna | 0.20 / 0.02 / 0.25 / 1.20 | 1.00 / — / — / 6.00 |
| gpt-6.1-sol | 2.00 / 0.10 / 2.50 / 10.00 | (legal) unchanged |
| gpt-5.5 | 5.00 / 0.50 / — / 30.00 | unchanged |

Above 272K input tokens, the 5.6 line and 6.1-sol charge double the input rate and
1.5x the output rate. The cache multipliers stay the same. OpenAI reports no cost, so
for an app on OpenAI these prices are the bill, and chat's were overcharging the
user's spend cap by up to 5x on Luna.

### 3. Sonnet 5.5's cache reads are 0.05x, not 0.1x

Anthropic's pricing page: "Cache hits and refreshes on Claude Opus 5.5 and Claude
Sonnet 5.5 are priced at 0.05x the base input price." Sonnet 5.5 is $2 in and $0.10
for a cache hit. 0001's seed had $0.20 and 0.1x. Opus 5.5 is $4 / $0.20, 0.05x, as
0001 said. Cache writes are 1.25x (5 min) on both.

### 4. OpenAI context windows: a floor, not a measurement

The pricing page lists gpt-5.5 with a context under 272K. The chat app records 922,000
for it, from an error message on 2026-09-29, but does not say which model sent that
error. Legal recorded gpt-6.1-sol at "272k", but the page bills prompts above 272K, so
the true window must be larger. Both are recorded as 272,000, the safe floor: an app
refuses a long conversation early rather than 400ing. The 5.6 line keeps chat's
922,000. Sending one oversized request per model would settle all three.

### 5. Probes run in this repo

All on 2026-10-15, for the facts 0001 listed as missing or the pilot depends on.

| Pair | Check | Result |
|---|---|---|
| Opus 5.5, Sonnet 5.5 | temperature 0.5 | 400 "`temperature` is deprecated for this model" |
| Opus 5.5, Sonnet 5.5 | tools + adaptive thinking | `stop_reason=tool_use`, a real `tool_use` block |
| Opus 5.5, Sonnet 5.5 | forced `tool_choice` | 400 `type "tool" and "any" are not supported for this model` |
| Opus 5.5, Sonnet 5.5, MiMo-V2.6-Pro | image | all three named green, red circle, 47 |
| MiMo-V2.6-Pro, DeepSeek-V4.1-Flash, Together GLM-5.3 | temperature 0.5 | accepted |

V4.1-Flash's temperature flag had been inherited from V4-Flash-0731 unmeasured
(chat 0037). It is now measured.

One trap for the probe: the installed `anthropic` SDK no longer accepts a
`temperature` keyword on `messages.create`, so a naive check fails in the SDK and
looks like an API rejection. The probe sends it through `extra_body`.

### 6. Refresh, first run

All 17 keys were listed by their gateways, and none is deprecated. Qwen3.8-2.4T-A95B is
listed as deprecated on 2026-10-12, `replaced_by` GLM-5.3, and is left out as 0001
said.

## Consequences

- The chat pilot's cost fallback changes for every DeepInfra model with a discount,
  and its OpenAI prices drop. Spend-cap arithmetic moves with them.
- Legal's GLM-5.3 price ($0.90 / $4.00) is the list price, not the bill. Its MiMo menu
  (`low/high/max`) is still unsupported: the catalogue's ladder is `("none",)`.
- Moving-house computes cost from its own prices, so its GLM-5.3 numbers change what
  it records (0001, rollout step 5).
