# 0010 — ChatGPT plan usage is not a gateway here

- Date: 2026-11-15
- Status: accepted

## Context

Lachlan asked whether a ChatGPT Plus subscription could pay for the OpenAI calls Lachlan's apps
make, falling back to the API. OpenAI's "Sign in with ChatGPT" (2026-09-29) allows it: the
plan is spent through the ordinary Responses API on `api.openai.com`, with an OAuth token in
place of the key. The build and the measurements are in wandly 0205.

## Decision

The catalogue gains no `chatgpt:` gateway, and nothing here calls the plan. Apps keep keying
OpenAI models as `openai:` and pricing them from these entries, because a plan-served call is
charged to the reader at the API's price, and which side served it is the app's bookkeeping.

## Why

Measured in wandly 0205 on `gpt-6.1-sol`, the plan matches the API on everything this
catalogue records: all five efforts accepted and calling tools, encrypted reasoning returned
and read on replay, the prompt cache hit and reported, and images on `gpt-6.1-terra`. A
gateway entry would duplicate the `openai:` facts. The probes and `refresh` keep using the
organisation's key, so what they measure stays the API.

## Facts an app needs that are not catalogue fields

- The plan refuses `stream=False` (400, "Stream must be set to true").
- It **enforces** `max_output_tokens`, though OpenAI's docs list it as unsupported.
- **Reasoning the plan wrote is silently ignored by the API** (prompt +0, three of three),
  while API-written reasoning is read on the plan. A thread that falls back from the plan to
  the key loses its earlier reasoning with no error, the same silent drop 0008 records for
  Anthropic.

## Measured since, by the apps (2026-11-15)

Three apps now ask the plan first. Their probes found four more things, none of them a
field here, and two of them the first real differences from the API:

- **`gpt-5.5` is not served on the plan**: 400, "not supported when using Codex with a
  ChatGPT account". `gpt-6.1-sol`, `gpt-6.1-terra` and `gpt-5.6-luna` are, at every effort
  on their ladders, with tools and images.
- **`input` must be a list** on the plan (400, "Input must be a list"); the API takes a string.
- **Sol at `high` reasoned about 40% as much on the plan**: mean 62 reasoning tokens against
  160 on the key, ten samples a side on one app's own request, after three a side elsewhere
  pointed the same way. Answer quality on each side is not measured.
- **The plan reported no prompt-cache hit** on ten identical 1,899-token requests in that
  probe, where the key hit nine of nine. An earlier probe saw one hit on a 2,751-token
  prompt, so this is "not reliably", not "never".

## Consequences

If the plan ever diverges from the API on a catalogued fact (a level refused, replay dropped),
that is the point to add a gateway, measured by its own probe.

**That point may have arrived, and the decision is Lachlan's.** A model the plan does not
serve, and an effort level that reasons less, are differences in kind from what this note
assumed. The apps cope without a gateway (the app with `gpt-5.5` keeps a list of models
the plan refuses), and the hand-over for this work said to keep keying models `openai:`,
so nothing was added. The case for a `chatgpt:` gateway now is that "which models the plan
serves" is being recorded in an app instead of here.
