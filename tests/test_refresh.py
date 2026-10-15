"""
The listing readers in scripts/refresh.py, on rows copied from the live APIs.

These are the conversions that turn a provider's units into the catalogue's.
A wrong one is a wrong price in every app that bumps, so each is pinned to a
real row and, for DeepInfra, to a real bill.
"""

from scripts.refresh import anthropic_facts, deepinfra_facts, together_facts

# GLM-5.3 on DeepInfra's /models/list, 2026-10-15 (pricing trimmed to what is read).
DEEPINFRA_GLM_5_3 = {
    "model_name": "zai-org/GLM-5.3",
    "pricing": {
        "discount": 0.375,
        "cents_per_input_token": 9e-05,
        "cents_per_output_token": 0.0004,
        "rate_per_input_token_cached": 0.22222222,
        "rate_per_input_token_cache_write": None,
    },
    "max_tokens": 1048576,
    "replaced_by": None,
    "deprecated": None,
}

DEEPINFRA_QWEN_2_4T = {
    "model_name": "Qwen/Qwen3.8-2.4T-A95B",
    "pricing": {
        "discount": None,
        "cents_per_input_token": 0.0002,
        "cents_per_output_token": 0.0006,
        "rate_per_input_token_cached": 0.1,
        "rate_per_input_token_cache_write": None,
    },
    "max_tokens": 262144,
    "replaced_by": "zai-org/GLM-5.3",
    "deprecated": 1791848967,
}


def test_deepinfra_prices_are_billed_prices_with_the_discount_taken_off():
    facts = deepinfra_facts(DEEPINFRA_GLM_5_3)
    assert facts["prompt_price_per_mtok"] == 0.5625  # $0.90 list x 0.625
    assert facts["completion_price_per_mtok"] == 2.5  # $4.00 list x 0.625
    assert facts["discount"] == 0.375
    assert facts["cache_read_multiplier"] == 0.22222222
    assert facts["cache_write_multiplier"] == 1.0
    assert facts["context_tokens"] == 1048576
    assert facts["provider_max_output_tokens"] is None


def test_deepinfra_prices_reproduce_a_real_bill():
    """15 prompt + 8 completion tokens on GLM-5.3, 2026-10-15: estimated_cost $0.0000284375."""
    facts = deepinfra_facts(DEEPINFRA_GLM_5_3)
    computed = (15 * facts["prompt_price_per_mtok"] + 8 * facts["completion_price_per_mtok"]) / 1e6
    assert abs(computed - 2.84375e-05) < 1e-12


def test_deepinfra_deprecation_becomes_a_date_and_a_successor():
    facts = deepinfra_facts(DEEPINFRA_QWEN_2_4T)
    assert facts["deprecated_at"] == "2026-10-12"
    assert facts["replaced_by"] == "zai-org/GLM-5.3"
    assert facts["discount"] == 0.0


def test_together_cache_price_becomes_a_multiplier():
    row = {
        "id": "zai-org/GLM-5.3",
        "context_length": 1048575,
        "pricing": {"input": 1.4, "output": 4.4, "cached_input": 0.25999999999999995},
    }
    facts = together_facts(row)
    assert (facts["prompt_price_per_mtok"], facts["completion_price_per_mtok"]) == (1.4, 4.4)
    assert facts["cache_read_multiplier"] == 0.18571429
    assert facts["context_tokens"] == 1048575


def test_anthropic_gives_limits_and_deprecation_only():
    body = {"max_input_tokens": 1000000, "max_tokens": 128000, "deprecated_at": None}
    assert anthropic_facts(body) == {
        "context_tokens": 1000000,
        "provider_max_output_tokens": 128000,
        "deprecated_at": None,
        "replaced_by": None,
    }
    body["deprecated_at"] = "2027-03-01T00:00:00Z"
    assert anthropic_facts(body)["deprecated_at"] == "2027-03-01"
