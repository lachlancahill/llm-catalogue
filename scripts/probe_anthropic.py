"""
Measure a Claude model's request-shape facts through the native Anthropic SDK.

    uv run -m scripts.probe_anthropic

The capability tree on the Models API already says which efforts and thinking
modes exist. This checks the things it does not say, each of which is a 400 on
every request if an app gets it wrong:

1. **Temperature.** Sends 0.5 with no thinking. Recent Claude models reject it.
2. **Tools with adaptive thinking.** A question that needs the tool, with thinking
   on, and whether a `tool_use` block came back.
3. **Forced tool choice.** `tool_choice` naming the tool, with thinking on.

Real requests, a cent or two per model.
"""

import logging

from anthropic import Anthropic

from scripts.common import api_key, configure_logging

logger = logging.getLogger(__name__)

# --- What to probe. Edit before running. ---------------------------------------
MODELS = ("claude-opus-5-5", "claude-sonnet-5-5")
# -------------------------------------------------------------------------------

# Enough for adaptive thinking to decide and still call the tool.
MAX_TOKENS = 16_000

TOOL_QUESTION = "What is 4321 times 1234? Use the calculator tool; do not do it in your head."
CALCULATOR_TOOL = {
    "name": "calculate",
    "description": "Evaluate an arithmetic expression and return the result.",
    "input_schema": {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    },
}
THINKING = {"type": "adaptive"}


def probe(client: Anthropic, model: str) -> None:
    """Run the three checks on one model, logging an outcome for each."""
    checks = {
        # Through extra_body: recent SDKs dropped the `temperature` argument, so a
        # keyword would fail in the SDK and never reach the API.
        "temperature 0.5": dict(extra_body={"temperature": 0.5}, messages=_ask("Say OK.")),
        "tools + thinking": dict(
            thinking=THINKING, tools=[CALCULATOR_TOOL], messages=_ask(TOOL_QUESTION)
        ),
        "forced tool_choice + thinking": dict(
            thinking=THINKING,
            tools=[CALCULATOR_TOOL],
            messages=_ask(TOOL_QUESTION),
            tool_choice={"type": "tool", "name": "calculate"},
        ),
    }
    for name, kwargs in checks.items():
        try:
            response = client.messages.create(model=model, max_tokens=MAX_TOKENS, **kwargs)
        except Exception as exc:  # noqa: BLE001 - a refusal is the measurement
            logger.info("%s  %-30s REJECTED - %s", model, name, str(exc)[:300])
            continue
        blocks = [block.type for block in response.content]
        logger.info(
            "%s  %-30s accepted, stop=%s, blocks=%s", model, name, response.stop_reason, blocks
        )


def _ask(text: str) -> list[dict]:
    return [{"role": "user", "content": text}]


def main() -> None:
    configure_logging()
    client = Anthropic(api_key=api_key("anthropic"))
    for model in MODELS:
        probe(client, model)


if __name__ == "__main__":
    main()
