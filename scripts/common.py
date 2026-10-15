"""
What refresh and the probes share: logging, where each gateway lives, and its key.

Keys are read from the environment at run time and nowhere else. This repo is
public, so it names the variables and never a key, a secret name or a GCP
project (research/0001, decision 7).
"""

import logging
import os

from openai import OpenAI

# The OpenAI-compatible base URL of each gateway that speaks Chat Completions.
# OpenAI's is spelled out rather than left to the SDK default, because the SDK
# would otherwise read OPENAI_BASE_URL from the shell (see `api_key`).
OPENAI_COMPATIBLE_BASE_URLS = {
    "deepinfra": "https://api.deepinfra.com/v1/openai",
    "together": "https://api.together.xyz/v1",
    "openai": "https://api.openai.com/v1",
}

API_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "deepinfra": "DEEPINFRA_API_KEY",
    "openai": "OPENAI_API_KEY",
    "together": "TOGETHER_API_KEY",
}


def configure_logging() -> None:
    """One format and level for every script, set once at the entry point."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # The HTTP clients log every request at INFO, which buries the results.
    logging.getLogger("httpx").setLevel(logging.WARNING)


def api_key(gateway: str) -> str:
    """
    The gateway's key from the environment, or an error naming the variable.

    Refuses to read OPENAI_API_KEY while OPENAI_BASE_URL points elsewhere. Lachlan's
    shell sets both to DeepInfra, and on 2026-10-15 a "list OpenAI models" call
    quietly returned DeepInfra's catalogue (chat 0048). The base URL is passed
    explicitly here, so the risk is the key: it would be DeepInfra's, and OpenAI
    would answer 401, or a probe would measure the wrong gateway.
    """
    name = API_KEY_ENV[gateway]
    base_url = os.environ.get("OPENAI_BASE_URL", "")
    if gateway == "openai" and base_url and "api.openai.com" not in base_url:
        raise RuntimeError(
            f"OPENAI_BASE_URL is {base_url}, so OPENAI_API_KEY is probably not an OpenAI "
            "key. Unset both and export OpenAI's key before probing or refreshing OpenAI."
        )
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set; export it to reach {gateway}.")
    return value


def openai_compatible_client(gateway: str) -> OpenAI:
    """A Chat Completions client for DeepInfra, Together or OpenAI."""
    return OpenAI(api_key=api_key(gateway), base_url=OPENAI_COMPATIBLE_BASE_URLS[gateway])
