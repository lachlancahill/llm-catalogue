"""
What the catalogue guarantees to every app that pins it.

Importing `llm_catalogue` already refuses mismatched keys and double-written
facts, so most of these assert on the loaded result. The guards on CatalogModel
are tested directly, because each one stands for a 400 an app would otherwise
ship.
"""

import dataclasses

import pytest

import llm_catalogue
from llm_catalogue.manual import MANUAL
from llm_catalogue.measured import MEASURED
from llm_catalogue.model import CatalogModel


def test_every_measured_key_loads():
    assert [m.key for m in llm_catalogue.ALL] == list(MEASURED)


def test_get_returns_the_entry_and_refuses_unknown_keys():
    glm = llm_catalogue.get("deepinfra:zai-org/GLM-5.3")
    assert (glm.gateway, glm.api_model_name) == ("deepinfra", "zai-org/GLM-5.3")
    with pytest.raises(KeyError, match="not in llm_catalogue"):
        llm_catalogue.get("zai-org/GLM-5.3")  # a bare id, without its gateway


def test_no_entry_is_deprecated():
    """
    `refresh` writes a deprecation when a gateway announces one. This failing is
    the signal: remove the entry, and bump the apps still using it.
    """
    deprecated = {
        m.key: (m.deprecated_at, m.replaced_by) for m in llm_catalogue.ALL if m.deprecated_at
    }
    assert deprecated == {}


def test_only_anthropic_and_openai_have_typed_prices():
    """Everything a listing publishes is refreshed. Typing it would let it drift."""
    assert {key.split(":", 1)[0] for key in MANUAL} == {"anthropic", "openai"}
    assert all(
        m.price_source.startswith("https://api.") for m in llm_catalogue.ALL if m.key not in MANUAL
    )


def test_every_entry_says_where_its_measurements_came_from():
    assert all(m.measured for m in llm_catalogue.ALL)


def test_prices_are_positive():
    for m in llm_catalogue.ALL:
        assert m.prompt_price_per_mtok > 0 and m.completion_price_per_mtok > 0, m.key
        assert m.cache_read_multiplier > 0 and m.cache_write_multiplier >= 1.0, m.key


def test_only_openai_needs_the_responses_api_for_tools():
    assert {m.gateway for m in llm_catalogue.ALL if m.tools_need_responses_api} == {"openai"}


def test_only_anthropic_has_adaptive_thinking():
    assert {m.gateway for m in llm_catalogue.ALL if m.supports_thinking} == {"anthropic"}


# --- CatalogModel's guards ----------------------------------------------------------


def _valid(**changes) -> CatalogModel:
    """A real entry with some fields changed, which re-runs __post_init__."""
    return dataclasses.replace(llm_catalogue.get("deepinfra:zai-org/GLM-5.3"), **changes)


def test_thinking_and_temperature_cannot_both_be_supported():
    with pytest.raises(ValueError, match="mutually exclusive"):
        _valid(supports_thinking=True, supports_temperature=True)


def test_ladder_must_be_known_values_weakest_first():
    with pytest.raises(ValueError, match="unknown effort"):
        _valid(effort_ladder=("none", "turbo"))
    with pytest.raises(ValueError, match="weakest first"):
        _valid(effort_ladder=("high", "low"))
    with pytest.raises(ValueError, match="weakest first"):
        _valid(effort_ladder=("low", "low"))


def test_unset_effort_must_be_a_behaviour_or_a_ladder_level():
    assert _valid(unset_effort="high").unset_effort == "high"
    with pytest.raises(ValueError, match="unset_effort"):
        _valid(unset_effort="medium")  # not on GLM-5.3's ladder


def test_gateway_must_be_known():
    with pytest.raises(ValueError, match="gateway"):
        _valid(key="openrouter:zai-org/GLM-5.3")


def test_discount_is_a_fraction():
    with pytest.raises(ValueError, match="discount"):
        _valid(discount=1.0)


def test_long_context_fields_go_together():
    with pytest.raises(ValueError, match="long-context"):
        _valid(long_context_above_tokens=272_000)
