"""
Measure one model on one OpenAI-compatible gateway before it enters `measured.py`.

    uv run -m scripts.probe_model

Real requests, real money: cents on a cheap model, more on a slow thinker at a
high level. Set the constants below first. Claude has its own probe
(`probe_anthropic`), and images have theirs (`probe_images`).

Merged from four scripts: chat's probe_model.py, wandly's probe_chat_models.py
and probe_preserved_thinking.py, and chat's probe_images.py (now its own script).
In order, it checks:

1. **Temperature.** Sends 0.5 and reports whether it was accepted.
2. **Tools.** One tool, a question that cannot be answered without it, and
   whether a real call came back. Narrating the call in prose fails.
3. **Reasoning field and cost.** Which delta field streamed reasoning, and
   whether usage carried the gateway's own `estimated_cost`.
4. **Effort.** Unset, `none` and each documented level on a hard question with a
   checkable answer, EFFORT_SAMPLES each, alternating levels.
5. **Replayed reasoning.** Whether a prior turn's `reasoning_content` reaches the
   prompt, and whether either known control makes it.

It prints what it saw and draws no conclusions. Which levels separate, and so
which go on the ladder, is read from the output by a person. The rules that
reading follows were each learned the hard way:

- **Three samples settle on against off. They do not separate two levels.** Use
  five, alternating, so provider load drifts across all levels rather than into
  one (chat 0031). Three-against-three cannot reach p < 0.10 whatever it sees
  (wandly 0108).
- **The output ceiling must be the app's**, or the probe measures its own cap and
  reads it as a level that never stops (chat 0031, wandly 0108). The warning at
  the end of the sweep says when that happened.
- **Sweep the documented levels, not the gateway's vocabulary** (wandly 0178).
  DeepInfra accepts all seven values on most models. Accepted earns a level
  nothing, and documented earns it a sweep, not a ladder position.
- **Sending nothing is a condition, not the absence of one** (wandly 0108). On
  some models it turns reasoning off entirely.
- **A refusal's list of valid values can be wrong** (wandly 0119). Record what
  returned 200, never the list an error quotes.
"""

import logging
import statistics

from scripts.common import configure_logging, openai_compatible_client

logger = logging.getLogger(__name__)

# --- What to probe. Edit before running. ---------------------------------------
GATEWAY = "together"
MODEL = "deepseek-ai/DeepSeek-V4.1-Flash-1017"
# The levels the model card, the lab and the gateway's page document, found by a
# web search before running. Empty sweeps unset against `none` alone, which asks
# "does it think, and can it be told not to".
DOCUMENTED_EFFORTS: tuple[str, ...] = ("low", "high", "max")
# The largest output ceiling any app using this model sends (chat 64,000).
OUTPUT_CEILING = 64_000
# Five, not three: see the docstring.
EFFORT_SAMPLES = 5
# -------------------------------------------------------------------------------

TOOL_QUESTION = "What is 4321 times 1234? Use the calculator tool; do not do it in your head."
CALCULATOR_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate",
        "description": "Evaluate an arithmetic expression and return the result.",
        "parameters": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    },
}

# Hard enough that levels have room to diverge, with an answer checked
# independently (18,061 domino tilings of a 4x10, by transfer matrix), so a level
# that thinks longer can be checked for thinking better too.
HARD_QUESTION = (
    "In how many ways can a 4x10 rectangle be tiled by 1x2 dominoes? "
    "Work it out exactly and state the final number."
)
HARD_ANSWER = "18061"

# The delta fields gateways have streamed reasoning on.
REASONING_FIELDS = ("reasoning_content", "reasoning")

# A long, repetitive block, so a rendered replay moves the prompt count by
# ~1,800 tokens and cannot be mistaken for template whitespace.
REPLAY_REASONING = (
    "The user asked for the total. I should check the revenue table first, then "
    "confirm the date filter is on the past side of last_refreshed. "
) * 60
REPLAY_RENDERED_THRESHOLD = 100
# Z.ai's own switch, and the vLLM recipe's route to the same template argument.
REPLAY_CONTROLS = (
    ("thinking", {"thinking": {"clear_thinking": False}}),
    ("chat_template_kwargs", {"chat_template_kwargs": {"clear_thinking": False}}),
)


def probe_temperature(client) -> None:
    """Whether a caller-chosen temperature is accepted. A 400 is the result, not a crash."""
    try:
        client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Say OK."}],
            temperature=0.5,
            max_tokens=OUTPUT_CEILING,
        )
    except Exception as exc:  # noqa: BLE001 - a refusal is the measurement
        logger.info("temperature: REJECTED - %s", str(exc)[:300])
        return
    logger.info("temperature: accepted")


def probe_tools(client) -> None:
    """Whether a real tool call comes back, not prose about one."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": TOOL_QUESTION}],
        tools=[CALCULATOR_TOOL],
        max_tokens=OUTPUT_CEILING,
    )
    choice = response.choices[0]
    calls = choice.message.tool_calls or []
    if calls:
        logger.info(
            "tools: called %s(%s), finish_reason=%s",
            calls[0].function.name,
            calls[0].function.arguments,
            choice.finish_reason,
        )
    else:
        logger.info(
            "tools: NO CALL - finish_reason=%s, said %r",
            choice.finish_reason,
            (choice.message.content or "")[:200],
        )


def stream_once(client, effort: str | None) -> dict:
    """
    One streamed answer to the hard question at one effort (None sends nothing).

    Streamed because that is how the apps call, and the reasoning field is a
    property of the stream's deltas. Returns the error instead of raising: which
    values draw a refusal is part of the result.
    """
    extra = {} if effort is None else {"reasoning_effort": effort}
    sample = {"reasoning": {}, "answer": "", "usage": None, "finish": "", "error": None}
    try:
        stream = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": HARD_QUESTION}],
            max_tokens=OUTPUT_CEILING,
            stream=True,
            stream_options={"include_usage": True},
            **extra,
        )
        for chunk in stream:
            if chunk.usage is not None:
                sample["usage"] = chunk.usage.model_dump()
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            sample["finish"] = choice.finish_reason or sample["finish"]
            # Non-standard fields, so read off the raw delta.
            raw = choice.delta.model_dump()
            for field in REASONING_FIELDS:
                if raw.get(field):
                    sample["reasoning"][field] = sample["reasoning"].get(field, 0) + len(raw[field])
            sample["answer"] += choice.delta.content or ""
    except Exception as exc:  # noqa: BLE001 - a refusal is the measurement
        sample["error"] = f"{type(exc).__name__}: {exc}"
    return sample


def sweep_efforts(client) -> None:
    """
    Unset, `none` and each documented level, alternating, EFFORT_SAMPLES rounds.

    Logs each level's reasoning characters (median and range), completion
    tokens, reported cost, correct answers and capped runs, then each level as a
    multiple of `high` where `high` was swept.
    """
    efforts: tuple[str | None, ...] = (None, "none", *DOCUMENTED_EFFORTS)
    samples: dict[str | None, list[dict]] = {effort: [] for effort in efforts}
    refused: dict[str | None, str] = {}

    # Alternating: round 1 runs every level once, then round 2, and so on.
    for round_number in range(1, EFFORT_SAMPLES + 1):
        for effort in efforts:
            if effort in refused:
                continue
            sample = stream_once(client, effort)
            if sample["error"]:
                refused[effort] = sample["error"]
                continue
            samples[effort].append(sample)
            logger.info(
                "  round %d %-8s %7d reasoning chars",
                round_number,
                effort or "(unset)",
                sum(sample["reasoning"].values()),
            )

    fields_seen = {f for runs in samples.values() for s in runs for f in s["reasoning"]}
    logger.info("reasoning streamed on: %s", sorted(fields_seen) or "NO FIELD")
    cost_reported = any(
        s["usage"] and s["usage"].get("estimated_cost") is not None
        for runs in samples.values()
        for s in runs
    )
    logger.info("cost reported (usage.estimated_cost): %s", cost_reported)

    logger.info("--- effort, %d samples each, alternating ---", EFFORT_SAMPLES)
    medians: dict[str, float] = {}
    capped_total = 0
    for effort in efforts:
        label = effort or "(unset)"
        if effort in refused:
            logger.info("%-8s REFUSED - %s", label, refused[effort][:200])
            continue
        runs = samples[effort]
        chars = [sum(s["reasoning"].values()) for s in runs]
        completion = [s["usage"]["completion_tokens"] for s in runs if s["usage"]]
        costs = [s["usage"].get("estimated_cost") or 0 for s in runs if s["usage"]]
        capped = sum(s["finish"] == "length" for s in runs)
        capped_total += capped
        medians[label] = statistics.median(chars)
        logger.info(
            "%-8s reasoning median %7.0f [%d-%d]  tokens %6.0f  cost $%.5f  "
            "%d/%d correct  %d/%d capped",
            label,
            medians[label],
            min(chars),
            max(chars),
            statistics.mean(completion) if completion else 0,
            statistics.mean(costs) if costs else 0,
            sum(HARD_ANSWER in s["answer"].replace(",", "") for s in runs),
            len(runs),
            capped,
            len(runs),
        )

    if capped_total:
        logger.warning(
            "!! %d runs hit the %d-token ceiling. Those measured the cap, not the level. "
            "Raise OUTPUT_CEILING to the app's and re-run before reading them.",
            capped_total,
            OUTPUT_CEILING,
        )

    if medians.get("high"):
        logger.info("--- each level as a multiple of `high` (a guide, not a verdict) ---")
        for label, median in medians.items():
            logger.info("%-8s %5.2fx", label, median / medians["high"])


def probe_replay(client) -> None:
    """
    Whether a replayed `reasoning_content` reaches the prompt (wandly 0141).

    The same four-message conversation, with and without the prior turn's
    reasoning: if the template renders it, prompt_tokens rises by the block's
    length. Then each known control, because accepted is not honoured. A 200 that
    moves no count is a parameter the gateway swallowed.
    """

    def prompt_tokens(with_reasoning: bool, extra: dict) -> int:
        assistant: dict = {"role": "assistant", "content": "17 times 23 is 391."}
        if with_reasoning:
            assistant["reasoning_content"] = REPLAY_REASONING
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Answer in one short sentence."},
                {"role": "user", "content": "What is 17 times 23?"},
                assistant,
                {"role": "user", "content": "Now add 9 to that."},
            ],
            max_tokens=16,
            extra_body=extra,
        )
        return response.usage.prompt_tokens

    without = prompt_tokens(False, {})
    with_it = prompt_tokens(True, {})
    preserved = with_it - without > REPLAY_RENDERED_THRESHOLD
    logger.info(
        "replay: without=%d with=%d - %s",
        without,
        with_it,
        "PRESERVED unasked" if preserved else "DROPPED by the template",
    )
    for name, body in REPLAY_CONTROLS:
        # Together reads `thinking` as its own object and 400s without a `type`.
        try:
            tokens = prompt_tokens(True, body)
        except Exception as exc:  # noqa: BLE001 - a refusal is the measurement
            logger.info("  %s: REJECTED - %s", name, str(exc)[:300])
            continue
        turns_on = tokens - without > REPLAY_RENDERED_THRESHOLD
        logger.info(
            "  %s: prompt_tokens=%d%s",
            name,
            tokens,
            " - turns preservation on" if turns_on and not preserved else "",
        )


def main() -> None:
    configure_logging()
    client = openai_compatible_client(GATEWAY)
    logger.info("Probing %s:%s", GATEWAY, MODEL)
    probe_temperature(client)
    probe_tools(client)
    probe_replay(client)
    sweep_efforts(client)


if __name__ == "__main__":
    main()
