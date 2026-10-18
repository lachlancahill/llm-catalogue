# 0004 — Adding DeepSeek-V4.1-Flash-1017

- Date: 2026-10-18
- Status: accepted

## Context

DeepSeek released a checkpoint of V4.1-Flash on 2026-10-17, and DeepInfra lists it
as `deepseek-ai/DeepSeek-V4.1-Flash-1017`. It is the first model added after the
catalogue was built, so it is also the first test of 0002's "probe, add, refresh"
steps. Together did not list it on 2026-10-18 (checked by Lachlan; this shell had
no Together key to confirm).

## Decision

Add `deepinfra:deepseek-ai/DeepSeek-V4.1-Flash-1017` as its own entry, measured from
scratch, beside the September checkpoint rather than in place of it. Leave
Together out until Together lists it, then probe it there separately (wandly 0156:
a gateway twin inherits nothing).

| Fact | 1017 | September V4.1-Flash |
|---|---|---|
| Billed in / out | 0.098 / 0.294 (0.51 off 0.20 / 0.60) | 0.14 / 0.42 (0.3 off) |
| Ladder | `none`, `low`, `high`, `max` | `none`, `high` |
| Unset | off | off |
| Replay | dropped, no control turns it on | dropped |
| Tools, temperature, images | yes, yes, yes | yes, yes, yes |

The sweep was 5 samples a level, alternating, with the 64,000 ceiling, on the
documented levels (`low`/`high`/`max`). Each level sat wholly above the one below,
5 of 5 against 5 of 5. Medians were `low` 1,471, `high` 3,447 and `max` 30,999
reasoning characters. The narrowest gap was `low` against `high`, where the
closest pair was 2,472 and 2,482. All 25 answers were correct, `none` included.
`usage.estimated_cost` matched the discounted price.

## Why

A new checkpoint is a new template and possibly new serving, so inheriting the
September entry's flags is the mistake 0001 was written to stop. The ladder shows
why: the September checkpoint has `none`/`high` from a 3-sample sweep where `low`
drew 429s. This one served `low` and separated all three levels at 5 samples.

## Alternatives considered

- **Replace the September entry.** Apps still pin it, and DeepInfra has not
  deprecated it. Refresh will report it when DeepInfra does.
- **Run the full refresh.** It needs Together, Anthropic and OpenAI keys, and this
  shell had none of them (its `OPENAI_API_KEY` is DeepInfra's). The new row was
  written with refresh's own `_deepinfra` reader and the file kept in
  `measured.py`'s order. The other DeepInfra rows were compared against the live
  listing and showed no drift. The next full `uv run main.py` rewrites everything
  anyway.

## Consequences

- The 0.51 discount is a promotion with no end date. An app that bills from the
  catalogue rather than `estimated_cost` under-charges once it ends, until the pin
  is bumped (0002, `discount`).
- `low` against `high` is the step to re-check if an app's menu ever depends on it.
  At n=5 it separated on every pair but one.
- Re-running the September checkpoint's sweep at 5 samples might put `low` and
  `max` on its ladder too. Nobody has done that yet.
