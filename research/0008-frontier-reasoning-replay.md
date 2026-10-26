# 0008 — Tools and reasoning replay on the frontier gateways

- Date: 2026-10-26
- Status: accepted

## Context

chat 0057 moved chat's four OpenAI models onto `/v1/responses`, so they can take tools
with reasoning on. That needed `supports_tools`, which this repo had left unmeasured on
the 5.6 line ("Tools on /v1/responses have not been measured"). It also raised the
question 0007 answered for GPT-6.1 Sol: is the reasoning passed back between tool calls
actually read?

On both OpenAI and Anthropic, what streams is a **summary**. The reasoning itself comes
back in a form only the provider can read: encrypted items on OpenAI (with
`include=["reasoning.encrypted_content"]` and `store=False`), signed `thinking` blocks on
Anthropic. An app that does not resend them gives the model no record of its own earlier
reasoning in the next call of a tool loop.

## Decision

Measured through chat's own clients, one tool loop per model at effort `high`. Call 1
asks for three parallel `get_weather` calls after some arithmetic. The follow-up is sent
twice, once without the carried reasoning and once with it:

| Model | Tool calls | Follow-up prompt (without / with) | Follow-up output (without / with) |
|---|---|---|---|
| GPT-5.6 Luna | 3 | 211 / 248 | 89 / 100 |
| GPT-5.6 Terra | 3 | 211 / 240 | 58 / 30 |
| GPT-5.6 Sol | 3 | 212 / 250, 212 / 225 | 84 / 63, 89 / 69 |
| GPT-5.5 | 3 | 211 / 280 | 201 / 41 |
| Claude Opus 5.5 | 3 | 701 / 735 | 97 / 66 |
| Claude Sonnet 5.5 | 3 | 730 / 780, 742 / 795, 762 / 825 | 70 / 64, 74 / 71, 74 / 71 |

- **`supports_tools=True`** on the four OpenAI models, beside the existing
  `tools_need_responses_api=True`. That is the shape 0007 gave GPT-6.1 Sol: the flag says
  where tools work, and `supports_tools` that they do.
- **`preserves_replayed_reasoning=True`** on all six. The field's comment now covers all
  three replay forms: `reasoning_content`, encrypted items, and signed thinking.
- A sample with no reasoning in it (Sol's and Sonnet's first) cannot measure replay and
  was repeated, not counted.

## Consequences

- **Anthropic accepts a tool loop with the thinking left out**, so an app that drops it
  never gets an error. chat did exactly that until 0057.
- Replay costs input tokens and usually saves output tokens, which cost several times
  more. One sample per model shows the direction, not a rate.
- Apps reading `supports_tools` for OpenAI models must serve them over `/v1/responses`.
  On Chat Completions the same request is still a 400.
