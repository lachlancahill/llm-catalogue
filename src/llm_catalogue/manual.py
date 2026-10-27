"""
Published facts that no provider publishes in machine-readable form. Typed in by hand.

Anthropic's Models API gives the context window, output cap and deprecation, which
`refresh` reads, but no price. OpenAI's model list gives only the id. So their
prices, and OpenAI's limits, are typed in here, each with the page and the date
it was read. This is the one exception to "refreshed from the source, never
transcribed" (research/0001), and the dates are what show how stale it is.

Every key here is also in `measured.py`. A field set here must not also be set by
`refresh` in `published.json`; the loader refuses an overlap, so each fact has one
writer.
"""

ANTHROPIC_PRICING = "https://platform.claude.com/docs/en/about-claude/pricing, read 2026-10-15"
OPENAI_PRICING = "https://developers.openai.com/api/docs/pricing, read 2026-10-15"

# Anthropic bills the whole 1M context at one rate ("a 900k-token request is billed
# at the same per-token rate as a 9k-token request"), so no long-context tier.
# Cache writes are the 5-minute TTL, the one the apps use. Cache reads on the 5.5
# line are 0.05x the base input price, not the 0.1x of earlier Claude models.
_ANTHROPIC_PRICE_ONLY = {
    "discount": 0.0,
    "long_context_above_tokens": None,
    "long_context_prompt_price_per_mtok": None,
    "long_context_completion_price_per_mtok": None,
    "price_source": ANTHROPIC_PRICING,
}

# OpenAI publishes neither a deprecation nor a successor on its API, nor an output
# cap anywhere.
_OPENAI_UNPUBLISHED = {
    "discount": 0.0,
    "provider_max_output_tokens": None,
    "deprecated_at": None,
    "replaced_by": None,
    "price_source": OPENAI_PRICING,
}

# The 5.6 line's context window was measured on 2026-09-29 from the error an
# oversized request returns: "exceed the configured limit of 922000 tokens"
# (chat 0046). OpenAI publishes it nowhere machine-readable.
_GPT_5_6_CONTEXT = 922_000

MANUAL: dict[str, dict] = {
    # $4 in, $5 to write the cache (5 min), $0.20 cache hit, $20 out.
    "anthropic:claude-opus-5-5": {
        "prompt_price_per_mtok": 4.00,
        "completion_price_per_mtok": 20.00,
        "cache_read_multiplier": 0.05,
        "cache_write_multiplier": 1.25,
        **_ANTHROPIC_PRICE_ONLY,
    },
    # $2 in, $2.50 to write the cache (5 min), $0.10 cache hit, $10 out.
    "anthropic:claude-sonnet-5-5": {
        "prompt_price_per_mtok": 2.00,
        "completion_price_per_mtok": 10.00,
        "cache_read_multiplier": 0.05,
        "cache_write_multiplier": 1.25,
        **_ANTHROPIC_PRICE_ONLY,
    },
    # $2 in, $0.10 cached, $2.50 cache write, $10 out; above 272K input tokens,
    # $4 / $0.20 / $5 / $15.
    #
    # 922,000 is the model page's "max input tokens" (1,050,000 context, 128,000
    # output; developers.openai.com/api/docs/models/gpt-6.1-sol, read 2026-10-23).
    # The 272,000 recorded before was a floor, from legal 0022 reading the
    # long-context price tier as the window. An oversized request (wandly,
    # 2026-10-23) returns `context_length_exceeded` without naming a number, so
    # the page is the source.
    "openai:gpt-6.1-sol": {
        "prompt_price_per_mtok": 2.00,
        "completion_price_per_mtok": 10.00,
        "cache_read_multiplier": 0.05,
        "cache_write_multiplier": 1.25,
        "long_context_above_tokens": 272_000,
        "long_context_prompt_price_per_mtok": 4.00,
        "long_context_completion_price_per_mtok": 15.00,
        "context_tokens": 922_000,
        **_OPENAI_UNPUBLISHED,
    },
    # $1 in, $0.05 cached, $1.25 cache write (30 min), $5 out; above 272K input
    # tokens, $2 / $0.10 / $2.50 / $7.50 (pricing page, read 2026-10-27).
    #
    # 922,000 is the model page's "max input tokens" (1,050,000 context, 128,000
    # output; developers.openai.com/api/docs/models/gpt-6.1-terra, read 2026-10-27),
    # the same window as GPT-6.1 Sol.
    "openai:gpt-6.1-terra": {
        "prompt_price_per_mtok": 1.00,
        "completion_price_per_mtok": 5.00,
        "cache_read_multiplier": 0.05,
        "cache_write_multiplier": 1.25,
        "long_context_above_tokens": 272_000,
        "long_context_prompt_price_per_mtok": 2.00,
        "long_context_completion_price_per_mtok": 7.50,
        "context_tokens": 922_000,
        **_OPENAI_UNPUBLISHED,
    },
    # $4 in, $0.40 cached, $5 cache write, $20 out; above 272K, $8 / $0.80 / $10
    # / $30. Was $5 / $30 when the chat app last read it, on 2026-07-20.
    "openai:gpt-5.6-sol": {
        "prompt_price_per_mtok": 4.00,
        "completion_price_per_mtok": 20.00,
        "cache_read_multiplier": 0.1,
        "cache_write_multiplier": 1.25,
        "long_context_above_tokens": 272_000,
        "long_context_prompt_price_per_mtok": 8.00,
        "long_context_completion_price_per_mtok": 30.00,
        "context_tokens": _GPT_5_6_CONTEXT,
        **_OPENAI_UNPUBLISHED,
    },
    # $2 in, $0.20 cached, $2.50 cache write, $12 out; above 272K, $4 / $0.40 /
    # $5 / $18. Was $2.50 / $15 on 2026-07-20.
    "openai:gpt-5.6-terra": {
        "prompt_price_per_mtok": 2.00,
        "completion_price_per_mtok": 12.00,
        "cache_read_multiplier": 0.1,
        "cache_write_multiplier": 1.25,
        "long_context_above_tokens": 272_000,
        "long_context_prompt_price_per_mtok": 4.00,
        "long_context_completion_price_per_mtok": 18.00,
        "context_tokens": _GPT_5_6_CONTEXT,
        **_OPENAI_UNPUBLISHED,
    },
    # $0.20 in, $0.02 cached, $0.25 cache write, $1.20 out; above 272K, $0.40 /
    # $0.04 / $0.50 / $1.80. Was $1 / $6 on 2026-07-20.
    "openai:gpt-5.6-luna": {
        "prompt_price_per_mtok": 0.20,
        "completion_price_per_mtok": 1.20,
        "cache_read_multiplier": 0.1,
        "cache_write_multiplier": 1.25,
        "long_context_above_tokens": 272_000,
        "long_context_prompt_price_per_mtok": 0.40,
        "long_context_completion_price_per_mtok": 1.80,
        "context_tokens": _GPT_5_6_CONTEXT,
        **_OPENAI_UNPUBLISHED,
    },
    # $5 in, $0.50 cached, $30 out. No cache-write price and no long-context tier
    # listed, so 1.0x and none.
    #
    # The chat app recorded 922,000 for this model too (chat 0046), but the pricing
    # page lists it with a context under 272K, and which model the 922,000 error
    # came from is not recorded. 272,000 is the safe floor until it is re-measured.
    "openai:gpt-5.5": {
        "prompt_price_per_mtok": 5.00,
        "completion_price_per_mtok": 30.00,
        "cache_read_multiplier": 0.1,
        "cache_write_multiplier": 1.0,
        "long_context_above_tokens": None,
        "long_context_prompt_price_per_mtok": None,
        "long_context_completion_price_per_mtok": None,
        "context_tokens": 272_000,
        **_OPENAI_UNPUBLISHED,
    },
}
