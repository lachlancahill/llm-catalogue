"""
The one record the catalogue holds per (gateway, model) pair.

A `CatalogModel` carries two of the three kinds of fact from research/0001:

1. **Published** by the provider: prices, cache multipliers, context window,
   output cap, deprecation. Written by `scripts/refresh.py` into `published.json`,
   or, where the provider publishes nothing machine-readable, typed into
   `manual.py` with the date and page.
2. **Measured** behaviour of the pair: tools, temperature, images, the effort
   ladder and so on. Typed into `measured.py`, with provenance.

The third kind, the app's own decisions (menus, defaults, display names, the
output ceiling it chooses), is deliberately absent. It stays in each app.

Measured fields are `bool | None`: **None means nobody has measured it.** None is
falsy, so an app that writes `if model.supports_images:` treats an unmeasured
capability as unsupported. That is the safe direction: a wrong False loses a
feature, a wrong True fails every request that uses it.
"""

from dataclasses import dataclass

# The gateways a key may name. A model's facts belong to the pair, never to the
# model alone: the same id on two gateways has different ladders, templates and
# cost reporting (wandly 0156).
GATEWAYS = ("anthropic", "deepinfra", "openai", "together")

# Every reasoning-effort value any gateway has accepted, weakest first. Ladders
# are checked against this order, so "weakest first" cannot drift.
EFFORT_VOCABULARY = ("none", "minimal", "low", "medium", "high", "xhigh", "max")

# What sending no effort at all does, where it is not simply a named level. The
# three behaviours seen so far:
#   off        no reasoning (the DeepSeek checkpoints on DeepInfra)
#   on         reasoning, at no level anyone has placed on a ladder
#   below_max  reasoning, measurably short of the top level (GLM-5.3-Flash)
# Where the provider documents unset as a level (Anthropic, OpenAI), it is that
# level's name instead.
UNSET_BEHAVIOURS = ("off", "on", "below_max")


@dataclass(frozen=True)
class CatalogModel:
    """
    Everything the catalogue knows about one model on one gateway.

    `key` is the identity, `gateway:api_model_name`, e.g.
    `deepinfra:zai-org/GLM-5.3`. Apps look entries up by it and keep their own
    ids; nothing here is stored on a conversation.
    """

    key: str

    # --- Kind 1: published by the provider -----------------------------------
    # Dollars per million tokens, as billed. On DeepInfra that is the list
    # price with any promotional `discount` already taken off (research/0002).
    prompt_price_per_mtok: float
    completion_price_per_mtok: float
    # Multiples of the prompt price. 1.0 where the provider prices no discount
    # (or no surcharge), so a cached token simply costs a normal one.
    cache_read_multiplier: float
    cache_write_multiplier: float
    # The fraction already taken off the prices above, 0.0 for none. Recorded
    # because a promotion can end before the app's pin is bumped: an app that
    # computes cost will then under-charge until it is.
    discount: float
    # OpenAI prices a prompt longer than this many tokens at a higher rate. None where the
    # whole context is billed at one rate. The cache multipliers apply to both
    # tiers alike (checked on the pricing page, 2026-10-15).
    long_context_above_tokens: int | None
    long_context_prompt_price_per_mtok: float | None
    long_context_completion_price_per_mtok: float | None
    # The most tokens one request may carry.
    context_tokens: int
    # The provider's own cap on one response. None where the provider publishes
    # none: DeepInfra has accepted every ceiling it was ever sent (chat 0037).
    # An app's own ceiling is an app decision and is never stored here.
    provider_max_output_tokens: int | None
    # ISO date the gateway marks the model deprecated, and what it names as the
    # successor. A test fails while any entry is deprecated.
    deprecated_at: str | None
    replaced_by: str | None
    # Where the prices came from: a live listing, or a page and the date it was read.
    price_source: str

    # --- Kind 2: measured behaviour of the pair -------------------------------
    # A real tool call came back, not prose about one.
    supports_tools: bool | None = None
    # A caller-chosen temperature (0.5) was accepted.
    supports_temperature: bool | None = None
    # Anthropic's adaptive thinking. False on every other gateway, where
    # reasoning is governed by effort alone.
    supports_thinking: bool = False
    # An image sent alongside a message was described (scripts/probe_images.py).
    supports_images: bool | None = None
    # `tool_choice` naming a specific tool was accepted.
    supports_forced_tool_choice: bool | None = None
    # OpenAI only: on /v1/chat/completions, function tools are a 400 with any
    # effort but `none`. Tools with reasoning work only through /v1/responses.
    tools_need_responses_api: bool = False
    # The effort values that measurably behave differently, weakest first.
    # `none` is included where it measurably turns reasoning off. A value the
    # gateway merely accepts earns nothing (chat 0007: acceptance is not
    # support). For Anthropic and OpenAI this is the provider's documented
    # ladder, which bills reasoning tokens per level.
    effort_ladder: tuple[str, ...] = ()
    # What sending no effort does: one of UNSET_BEHAVIOURS, a level from the
    # ladder, or None if unmeasured.
    unset_effort: str | None = None
    # The streamed delta field that carries reasoning text (`reasoning_content`
    # on DeepInfra and Together), Anthropic's `thinking` block type, or None
    # where the endpoint streams no reasoning text.
    reasoning_field: str | None = None
    # Whether each response carries the provider's own billed figure
    # (DeepInfra's `usage.estimated_cost`).
    reports_cost: bool | None = None
    # Whether reasoning sent back with the next request reaches the prompt with
    # no extra controls sent: a replayed `reasoning_content` on the OpenAI-
    # compatible gateways (wandly 0141), OpenAI's encrypted reasoning items with
    # `store=False` (0007), Anthropic's signed thinking blocks (0008). Measured by
    # the prompt count moving. On OpenAI and Anthropic what streams is only a
    # summary, so replay is the one way the model sees its own earlier reasoning
    # between tool calls.
    preserves_replayed_reasoning: bool | None = None
    # Provenance: date, script, samples and the note the measurement came from.
    measured: str = ""

    @property
    def gateway(self) -> str:
        """Who serves the model: the part of the key before the first colon."""
        return self.key.split(":", 1)[0]

    @property
    def api_model_name(self) -> str:
        """What goes on the wire: the part of the key after the first colon."""
        return self.key.split(":", 1)[1]

    def __post_init__(self) -> None:
        """
        Refuse an entry that would fail requests, at import time.

        Every check here stands for a 400 on every request an app would send
        with the bad value, which is the outage this catalogue exists to stop.
        """
        if self.gateway not in GATEWAYS:
            raise ValueError(f"{self.key}: gateway must be one of {GATEWAYS}.")

        # Anthropic rejects the combination: "`temperature` may only be set to 1
        # when thinking is enabled or in adaptive mode".
        if self.supports_thinking and self.supports_temperature:
            raise ValueError(
                f"{self.key}: supports_thinking and supports_temperature are mutually "
                f"exclusive - adaptive thinking pins temperature to 1."
            )

        unknown = set(self.effort_ladder) - set(EFFORT_VOCABULARY)
        if unknown:
            raise ValueError(f"{self.key}: unknown effort values {sorted(unknown)}.")
        ordered = tuple(e for e in EFFORT_VOCABULARY if e in self.effort_ladder)
        if self.effort_ladder != ordered:
            raise ValueError(
                f"{self.key}: effort_ladder {self.effort_ladder} must be weakest first, "
                f"without repeats: {ordered}."
            )

        allowed_unset = UNSET_BEHAVIOURS + self.effort_ladder
        if self.unset_effort is not None and self.unset_effort not in allowed_unset:
            raise ValueError(
                f"{self.key}: unset_effort {self.unset_effort!r} must be one of {allowed_unset}."
            )

        if not 0.0 <= self.discount < 1.0:
            raise ValueError(f"{self.key}: discount {self.discount} must be in [0, 1).")

        long_context = (
            self.long_context_above_tokens,
            self.long_context_prompt_price_per_mtok,
            self.long_context_completion_price_per_mtok,
        )
        if len({value is None for value in long_context}) != 1:
            raise ValueError(f"{self.key}: the long-context fields are all set or all None.")
