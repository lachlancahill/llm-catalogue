"""
Measured behaviour of each (gateway, model) pair. Typed in by hand, with provenance.

These are the expensive facts: each cost real requests and wall clock to find,
and none depends on which app is asking. Each was measured once, in one repo, and
is recorded here so the other apps stop re-deriving or contradicting it.

Provenance cites notes by repo and number ("wandly 0178", "chat 0031") and copies
only the measurement. Never paste the surrounding context from those notes: some
of them name real people and their accounts (research/0001, decision 7).

The keys here are the catalogue's keys. Each must also be in `published.json`,
which `scripts/refresh.py` writes from the live listings.

Field meanings, and why an unmeasured fact is None, are on `CatalogModel`.
"""

MEASURED: dict[str, dict] = {
    # --- DeepInfra ----------------------------------------------------------------
    # Every DeepInfra response carries `usage.estimated_cost`, the figure it bills,
    # and every model here streams reasoning as `reasoning_content`.
    #
    # Probed 2026-10-15 (wandly 0178, probe_chat_models.py and
    # probe_preserved_thinking.py, nothing inherited). A real `tool_calls` finish.
    # Reasoning streams with nothing sent, so unset is on.
    #
    # Hard question, 3 samples a level, reasoning characters:
    #   unset 43,071  none 0  minimal 48,907  low 25,108
    #   medium 36,600  high 26,481  xhigh 30,975  max 18,552
    # `max` thought least and `minimal` most: the named levels sort as noise. The
    # only real step is `none`, which turns reasoning off (and got the question
    # wrong 3 of 3). So the ladder is `none` alone.
    #
    # The template keeps a replayed reasoning block unasked: 62 prompt tokens
    # without it, 1,863 with it.
    #
    # Temperature 0.5 accepted, and the test image described in full ("green, a
    # red circle ... the number 47"), both 2026-10-15 in this repo.
    "deepinfra:XiaomiMiMo/MiMo-V2.6-Pro": dict(
        supports_tools=True,
        supports_temperature=True,
        supports_images=True,
        effort_ladder=("none",),
        unset_effort="on",
        reasoning_field="reasoning_content",
        reports_cost=True,
        preserves_replayed_reasoning=True,
        measured=(
            "2026-10-15, wandly 0178: tools, ladder (3 samples x 8 levels), replay. "
            "Temperature and images 2026-10-15, this repo's probes."
        ),
    ),
    # Probed 2026-08-29 (chat 0034): accepts a temperature, calls tools, accepts
    # a 64,000 output ceiling. Unset is on and heavy (47,008 and 71,239 reasoning
    # chars on two samples); `none` measured 0.
    #
    # `low`/`high`/`max` are GLM-5.3-Flash's ladder, carried over by decision
    # (chat 0034), not separated by samples on this checkpoint. A single-sample
    # screen corroborates the direction (`low` ~35 reasoning chars, `high`
    # ~12,000). Chat, wandly and legal all offer these three, so the inheritance is
    # recorded here once rather than three times.
    #
    # Images: `405 Model ... does not accept image input` (chat probe_images.py,
    # 2026-09-13). Replayed reasoning preserved unasked, 53 -> 1,854 prompt
    # tokens (wandly 0141).
    "deepinfra:zai-org/GLM-5.3": dict(
        supports_tools=True,
        supports_temperature=True,
        supports_images=False,
        effort_ladder=("none", "low", "high", "max"),
        unset_effort="on",
        reasoning_field="reasoning_content",
        reports_cost=True,
        preserves_replayed_reasoning=True,
        measured=(
            "2026-08-29, chat 0034: tools, temperature, unset/none. low/high/max inherited "
            "from GLM-5.3-Flash. Images 2026-09-13 (chat 0038). Replay: wandly 0141."
        ),
    ),
    # Probed 2026-08-28 (chat 0034, 2 samples a level, streaming): calls tools,
    # accepts a temperature, reports cost. Reasoning characters:
    #   none 0-1,588  low 1,461-2,119  high 3,418-8,060  max 35,551-42,049
    #   unset 13,126-24,356 (on, between high and max, so below_max)
    # Images described (chat 0038). Replay preserved unasked (wandly 0141).
    "deepinfra:zai-org/GLM-5.3-Flash": dict(
        supports_tools=True,
        supports_temperature=True,
        supports_images=True,
        effort_ladder=("none", "low", "high", "max"),
        unset_effort="below_max",
        reasoning_field="reasoning_content",
        reports_cost=True,
        preserves_replayed_reasoning=True,
        measured=(
            "2026-08-28, chat 0034: tools, temperature, ladder (2 samples a level). "
            "Images chat 0038. Replay wandly 0141."
        ),
    ),
    # Tools and temperature verified 2026-07-18 (chat 0018). `none` is genuinely
    # off: 0 reasoning chars in 6 of 6 against unset's ~36,000 (wandly 0108). No
    # ladder among the thinking levels has been measured.
    #
    # The one Z.ai template that drops a replayed reasoning block: 53 prompt
    # tokens with or without it. `chat_template_kwargs={"clear_thinking": False}`
    # turns preservation on, to 1,854 (wandly 0141).
    "deepinfra:zai-org/GLM-5.2": dict(
        supports_tools=True,
        supports_temperature=True,
        supports_images=False,
        effort_ladder=("none",),
        unset_effort="on",
        reasoning_field="reasoning_content",
        reports_cost=True,
        preserves_replayed_reasoning=False,
        measured=(
            "2026-07-18, chat 0018: tools, temperature. Effort wandly 0108. Images chat "
            "0038. Replay wandly 0141."
        ),
    ),
    # Probed 2026-08-22 (chat 0030, 0031): calls tools, accepts a temperature,
    # reports cost. Sending no effort turns reasoning off entirely (0 chars), so
    # an app must send a level to get any thinking.
    #
    # 5 samples each, alternating (chat 0031):
    #   high  median 29,239  range 19,924-37,857
    #   max   median 38,229  range 37,241-43,250
    # `low` and `medium` measured inside `high`'s spread, so they are not on it.
    "deepinfra:deepseek-ai/DeepSeek-V4-Pro-0813": dict(
        supports_tools=True,
        supports_temperature=True,
        supports_images=False,
        effort_ladder=("none", "high", "max"),
        unset_effort="off",
        reasoning_field="reasoning_content",
        reports_cost=True,
        measured=(
            "2026-08-22, chat 0030/0031: tools, temperature, ladder (5 samples, "
            "alternating). Images chat 0038."
        ),
    ),
    # Probed 2026-09-11 (wandly 0169, used by chat 0037): a real `tool_calls`
    # finish, reports cost. Sending no effort turns reasoning off (0 chars).
    #
    # Hard question, 3 samples a level, reasoning characters:
    #   unset 0  none 0  minimal 10,165  medium 9,979  high 19,055  max 12,344
    #   low refused (429 engine_overloaded, 3 of 3)
    # Off against on is unambiguous. Among the thinking levels nothing separates
    # at n=3, `max` sat below `high`, so the ladder is `none`/`high`, which is
    # what 0007's bar supports. Wandly offers `xhigh`/`max` too, on DeepSeek's
    # documentation rather than a measurement. Its 0102-style campaign (six
    # samples a cell, four questions) is what would put them here.
    #
    # Drops a replayed reasoning block whatever it is told (wandly 0169).
    # Images described (chat 0038). Temperature 0.5 accepted 2026-10-15 in this
    # repo; the chat app had inherited it from V4-Flash-0731 unmeasured.
    "deepinfra:deepseek-ai/DeepSeek-V4.1-Flash": dict(
        supports_tools=True,
        supports_temperature=True,
        supports_images=True,
        effort_ladder=("none", "high"),
        unset_effort="off",
        reasoning_field="reasoning_content",
        reports_cost=True,
        preserves_replayed_reasoning=False,
        measured=(
            "2026-09-11, wandly 0169: tools, ladder (3 samples a level), replay. Images "
            "chat 0038. Temperature 2026-10-15, this repo."
        ),
    ),
    # Verified 2026-08-22 (chat 0030): accepts a temperature, a real tool call.
    # Thinks with nothing sent (18,355 reasoning chars). No ladder measured.
    # Images described (chat 0038).
    "deepinfra:moonshotai/Kimi-K3": dict(
        supports_tools=True,
        supports_temperature=True,
        supports_images=True,
        unset_effort="on",
        reasoning_field="reasoning_content",
        reports_cost=True,
        measured="2026-08-22, chat 0030: tools, temperature, unset. Images chat 0038.",
    ),
    # Verified 2026-08-22 (chat 0030): accepts a temperature, a real tool call.
    # Thinks with nothing sent (46,329 reasoning chars). Accepts `xhigh`,
    # `medium` and `low` and rejects `high` with a 400, but no ladder was
    # measured, so none is recorded. Images described (chat 0038). Replay
    # preserved unasked, 108 -> 1,909 (wandly 0141).
    "deepinfra:Qwen/Qwen3.8-27B": dict(
        supports_tools=True,
        supports_temperature=True,
        supports_images=True,
        unset_effort="on",
        reasoning_field="reasoning_content",
        reports_cost=True,
        preserves_replayed_reasoning=True,
        measured=(
            "2026-08-22, chat 0030: tools, temperature, unset. Images chat 0038. Replay "
            "wandly 0141."
        ),
    ),
    # For local_reverse_proxy, if it ever adopts the catalogue. Nothing about its
    # behaviour has been measured; its published facts are refreshed like the rest.
    "deepinfra:openai/gpt-oss-120b": dict(
        reports_cost=True,
        measured="Nothing measured. Run scripts/probe_model.py before relying on any flag.",
    ),
    # --- Together -----------------------------------------------------------------
    # Its own entry, never inherited from the DeepInfra twin (wandly 0156).
    #
    # Probed 2026-09-02 (wandly 0156): a real `tool_calls` finish, reasoning as
    # `reasoning_content`, honours `stream_options.include_usage`. Reports tokens
    # and no cost. All eight effort values return 200, and none separate on the
    # screen, `none` included (110 reasoning tokens against unset's 257), so
    # there is no ladder. Sending nothing leaves reasoning on. Temperature 0.5
    # accepted 2026-10-15 in this repo.
    "together:zai-org/GLM-5.3": dict(
        supports_tools=True,
        supports_temperature=True,
        unset_effort="on",
        reasoning_field="reasoning_content",
        reports_cost=False,
        measured=(
            "2026-09-02, wandly 0156: tools, effort screen (1 sample a cell). "
            "Temperature 2026-10-15, this repo."
        ),
    ),
    # --- Anthropic ----------------------------------------------------------------
    # The effort ladder, thinking and image support are read off the Models API
    # capability tree (`models.retrieve(id).capabilities`) on 2026-10-15: all
    # five effort levels, thinking `adaptive` only (`enabled` and `disabled` both
    # unsupported), `image_input` supported.
    #
    # Opus 5.5 with no effort runs at `medium`, not `high` as Opus 5 did. Sonnet
    # 5.5's unset is `high`, with its levels recalibrated (chat 0048).
    #
    # Probed 2026-10-15 in this repo (probe_anthropic.py, probe_images.py), both
    # models alike:
    #   temperature 0.5        400 "`temperature` is deprecated for this model"
    #   tools + adaptive       stop_reason tool_use, a real tool_use block
    #   forced tool_choice     400 'type "tool" and "any" are not supported for
    #                          this model'. No app sends it; recorded so none starts.
    #   image                  "Green background, red circle, number 47."
    "anthropic:claude-opus-5-5": dict(
        supports_tools=True,
        supports_temperature=False,
        supports_thinking=True,
        supports_images=True,
        supports_forced_tool_choice=False,
        effort_ladder=("low", "medium", "high", "xhigh", "max"),
        unset_effort="medium",
        reasoning_field="thinking",
        reports_cost=False,
        measured=(
            "2026-10-15: Models API capability tree; this repo's probes for temperature, "
            "tools, forced tool_choice and images; unset level from chat 0048."
        ),
    ),
    "anthropic:claude-sonnet-5-5": dict(
        supports_tools=True,
        supports_temperature=False,
        supports_thinking=True,
        supports_images=True,
        supports_forced_tool_choice=False,
        effort_ladder=("low", "medium", "high", "xhigh", "max"),
        unset_effort="high",
        reasoning_field="thinking",
        reports_cost=False,
        measured=(
            "2026-10-15: Models API capability tree; this repo's probes for temperature, "
            "tools, forced tool_choice and images; unset level from chat 0048."
        ),
    ),
    # --- OpenAI -------------------------------------------------------------------
    # The whole GPT-5 line rejects a non-default temperature, and on
    # /v1/chat/completions function tools are a 400 with any effort but `none`:
    # "Function tools with reasoning_effort are not supported ... use
    # /v1/responses" (chat 0018, legal 0022). Chat Completions streams no
    # reasoning text. OpenAI reports tokens and no cost.
    #
    # Effort values were probed by request (chat 0018): `minimal` and `max` are
    # rejected, `none` accepted, and Luna has no `xhigh`. Images: all four
    # described the test image (chat 0038). Tools on /v1/responses have not been
    # measured on the 5.6 line, so `supports_tools` stays unmeasured.
    "openai:gpt-5.6-sol": dict(
        supports_temperature=False,
        supports_images=True,
        tools_need_responses_api=True,
        effort_ladder=("none", "low", "medium", "high", "xhigh"),
        reports_cost=False,
        measured="2026-07-19, chat 0018: temperature, efforts, tools. Images chat 0038.",
    ),
    "openai:gpt-5.6-terra": dict(
        supports_temperature=False,
        supports_images=True,
        tools_need_responses_api=True,
        effort_ladder=("none", "low", "medium", "high", "xhigh"),
        reports_cost=False,
        measured="2026-07-19, chat 0018: temperature, efforts, tools. Images chat 0038.",
    ),
    "openai:gpt-5.6-luna": dict(
        supports_temperature=False,
        supports_images=True,
        tools_need_responses_api=True,
        effort_ladder=("none", "low", "medium", "high"),
        reports_cost=False,
        measured="2026-07-19, chat 0018: temperature, efforts, tools. Images chat 0038.",
    ),
    "openai:gpt-5.5": dict(
        supports_temperature=False,
        supports_images=True,
        tools_need_responses_api=True,
        effort_ladder=("none", "low", "medium", "high", "xhigh"),
        reports_cost=False,
        measured="2026-07-19, chat 0018: temperature, efforts, tools. Images chat 0038.",
    ),
    # Legal 0022, 2026-10-01: tools work through /v1/responses with reasoning on,
    # and are a 400 on Chat Completions. Its model page documents efforts `low`
    # to `max`, `medium` by default; the Chat Completions error offers `none`.
    "openai:gpt-6.1-sol": dict(
        supports_tools=True,
        tools_need_responses_api=True,
        effort_ladder=("low", "medium", "high", "xhigh", "max"),
        unset_effort="medium",
        reports_cost=False,
        measured="2026-10-01, legal 0022: tools via /v1/responses; efforts from the model page.",
    ),
}
