"""
Rewrite `published.json` from the providers' live listings.

    uv run main.py

For every key in `measured.py`, read what its gateway publishes:

- **DeepInfra** `/models/list`: prices, cache multipliers, discount, context,
  deprecation and `replaced_by`. Public, so no key is needed.
- **Together** `/v1/models`: prices and context.
- **Anthropic** Models API: context window, output cap, deprecation. No prices;
  those are typed into `manual.py`.
- **OpenAI** model list: only that the id exists. Everything else is in `manual.py`.

Each change is logged, field by field. The run fails (exit 1) on a model the
gateway no longer lists, and on one it marks deprecated. A deprecation is still
written, because it is true, and the catalogue's tests then fail until the entry
is removed. That failure is the signal to bump the apps that use the model
(research/0001). A missing model writes nothing, since the file would then have a
hole the loader refuses.

Run it whenever you touch the repo, and before bumping any app.
"""

import datetime
import json
import logging
import runpy
from pathlib import Path

import requests

from scripts.common import api_key

logger = logging.getLogger(__name__)

PACKAGE_DIR = Path(__file__).resolve().parent.parent / "src" / "llm_catalogue"
PUBLISHED_PATH = PACKAGE_DIR / "published.json"
MEASURED_PATH = PACKAGE_DIR / "measured.py"

DEEPINFRA_LIST_URL = "https://api.deepinfra.com/models/list"
TOGETHER_LIST_URL = "https://api.together.xyz/v1/models"
ANTHROPIC_MODEL_URL = "https://api.anthropic.com/v1/models/{}"
OPENAI_MODEL_URL = "https://api.openai.com/v1/models/{}"
ANTHROPIC_VERSION = "2023-06-01"

# Long enough for a listing under load, short enough that a hung provider fails
# the run instead of holding it open.
TIMEOUT_SECONDS = 30

# Prices are rounded so float noise (9e-05 * 1e4 = 0.9000000000000001) does not
# show up as a change on every run.
PRICE_DECIMALS = 6
MULTIPLIER_DECIMALS = 8

# The long-context fields only OpenAI has. Every other gateway bills one rate.
NO_LONG_CONTEXT = {
    "long_context_above_tokens": None,
    "long_context_prompt_price_per_mtok": None,
    "long_context_completion_price_per_mtok": None,
}


def deepinfra_facts(row: dict) -> dict:
    """
    One `/models/list` row as catalogue fields.

    Four conversions, none optional:
    - `cents_per_*_token` is cents per token, so x 10,000 for dollars per million.
    - `discount` is a fraction off both rates, and the list prices are before it.
      Checked against the bill on 2026-10-15: a GLM-5.3 call of 15 prompt and 8
      completion tokens reported $0.0000284375, which is (15 x 0.90 + 8 x 4.00)
      x 0.625 exactly (research/0002).
    - `rate_per_input_token_cached` is already a multiplier, not a rate. Null
      means no prefix-cache price, so a cached token costs a normal one.
    - `deprecated` is a Unix timestamp.
    """
    pricing = row["pricing"]
    discount = float(pricing["discount"] or 0.0)
    payable = 1.0 - discount
    deprecated = row["deprecated"]
    return {
        "prompt_price_per_mtok": round(
            pricing["cents_per_input_token"] * 1e4 * payable, PRICE_DECIMALS
        ),
        "completion_price_per_mtok": round(
            pricing["cents_per_output_token"] * 1e4 * payable, PRICE_DECIMALS
        ),
        "cache_read_multiplier": round(
            float(pricing["rate_per_input_token_cached"] or 1.0), MULTIPLIER_DECIMALS
        ),
        "cache_write_multiplier": float(pricing["rate_per_input_token_cache_write"] or 1.0),
        "discount": discount,
        **NO_LONG_CONTEXT,
        "context_tokens": row["max_tokens"],
        "provider_max_output_tokens": None,
        "deprecated_at": (
            datetime.datetime.fromtimestamp(deprecated, datetime.UTC).date().isoformat()
            if deprecated
            else None
        ),
        "replaced_by": row["replaced_by"],
        "price_source": DEEPINFRA_LIST_URL,
    }


def together_facts(row: dict) -> dict:
    """
    One `/v1/models` row as catalogue fields. Prices are already dollars per
    million. Together publishes no deprecation, discount, cache-write price or
    output cap.
    """
    pricing = row["pricing"]
    cached = pricing.get("cached_input", pricing["input"])
    return {
        "prompt_price_per_mtok": round(pricing["input"], PRICE_DECIMALS),
        "completion_price_per_mtok": round(pricing["output"], PRICE_DECIMALS),
        "cache_read_multiplier": round(cached / pricing["input"], MULTIPLIER_DECIMALS),
        "cache_write_multiplier": 1.0,
        "discount": 0.0,
        **NO_LONG_CONTEXT,
        "context_tokens": row["context_length"],
        "provider_max_output_tokens": None,
        "deprecated_at": None,
        "replaced_by": None,
        "price_source": TOGETHER_LIST_URL,
    }


def anthropic_facts(body: dict) -> dict:
    """The Models API's limits and deprecation. Anthropic names no successor."""
    deprecated = body.get("deprecated_at")
    return {
        "context_tokens": body["max_input_tokens"],
        "provider_max_output_tokens": body["max_tokens"],
        "deprecated_at": deprecated[:10] if deprecated else None,
        "replaced_by": None,
    }


def _deepinfra(names: set[str]) -> dict[str, dict]:
    response = requests.get(DEEPINFRA_LIST_URL, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return {
        r["model_name"]: deepinfra_facts(r) for r in response.json() if r["model_name"] in names
    }


def _together(names: set[str]) -> dict[str, dict]:
    # Through `requests`: Together's Cloudflare front 403s urllib's user agent.
    response = requests.get(
        TOGETHER_LIST_URL,
        headers={"Authorization": f"Bearer {api_key('together')}"},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return {r["id"]: together_facts(r) for r in response.json() if r["id"] in names}


def _per_model(names: set[str], url: str, headers: dict, to_facts) -> dict[str, dict]:
    """Ask for each model by id. A 404 means the gateway no longer serves it."""
    found = {}
    for name in sorted(names):
        response = requests.get(url.format(name), headers=headers, timeout=TIMEOUT_SECONDS)
        if response.status_code == 404:
            continue
        response.raise_for_status()
        found[name] = to_facts(response.json())
    return found


def _anthropic(names: set[str]) -> dict[str, dict]:
    headers = {"x-api-key": api_key("anthropic"), "anthropic-version": ANTHROPIC_VERSION}
    return _per_model(names, ANTHROPIC_MODEL_URL, headers, anthropic_facts)


def _openai(names: set[str]) -> dict[str, dict]:
    # OpenAI publishes nothing beyond the id, so an entry is just "it exists".
    headers = {"Authorization": f"Bearer {api_key('openai')}"}
    return _per_model(names, OPENAI_MODEL_URL, headers, lambda body: {})


READERS = {
    "anthropic": _anthropic,
    "deepinfra": _deepinfra,
    "openai": _openai,
    "together": _together,
}


def log_changes(old: dict[str, dict], new: dict[str, dict]) -> None:
    """One line per added, removed or changed fact, so a refresh reads as a diff."""
    for key in sorted(set(old) - set(new)):
        logger.info("removed %s", key)
    for key in sorted(new):
        if key not in old:
            logger.info("added %s", key)
            continue
        for field in sorted(set(old[key]) | set(new[key])):
            if old[key].get(field) != new[key].get(field):
                logger.info("%s %s: %r -> %r", key, field, old[key].get(field), new[key].get(field))


def refresh() -> bool:
    """
    Read every gateway, rewrite published.json, and report whether all is well.

    Returns False on a missing or deprecated model, after logging which.
    """
    # Read straight from the file, not imported: importing llm_catalogue joins
    # measured.py with published.json, and a newly added key is exactly the case
    # where that join fails until this has run.
    keys = list(runpy.run_path(str(MEASURED_PATH))["MEASURED"])

    published = {}
    missing = []
    for gateway, reader in READERS.items():
        names = {key.split(":", 1)[1] for key in keys if key.split(":", 1)[0] == gateway}
        found = reader(names)
        logger.info("%s: %d of %d models listed", gateway, len(found), len(names))
        for name in names:
            key = f"{gateway}:{name}"
            if name in found:
                published[key] = found[name]
            else:
                missing.append(key)

    if missing:
        logger.error("Not listed by their gateway, so nothing was written: %s", sorted(missing))
        return False

    old = json.loads(PUBLISHED_PATH.read_text()) if PUBLISHED_PATH.exists() else {}
    ordered = {key: published[key] for key in keys}
    log_changes(old, ordered)
    PUBLISHED_PATH.write_text(json.dumps(ordered, indent=2) + "\n")
    logger.info("Wrote %d entries to %s", len(ordered), PUBLISHED_PATH.name)

    # `.get`: an OpenAI entry is empty, because OpenAI publishes no deprecation.
    deprecated = {
        key: (facts["deprecated_at"], facts["replaced_by"])
        for key, facts in ordered.items()
        if facts.get("deprecated_at")
    }
    if deprecated:
        logger.error("Deprecated by their gateway (deprecated_at, replaced_by): %s", deprecated)
        return False
    return True
