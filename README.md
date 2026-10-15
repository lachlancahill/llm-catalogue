# llm-catalogue

One place for the facts about the LLMs Lachlan's apps call: what each model costs,
how much it can take, and how it actually behaves on the gateway that serves it.
Each app pins it by git commit and keeps its own decisions (menus, defaults,
display names, output ceilings) locally.

```python
import llm_catalogue

glm = llm_catalogue.get("deepinfra:zai-org/GLM-5.3")
glm.prompt_price_per_mtok  # 0.5625 — billed, DeepInfra's discount applied
glm.effort_ladder  # ('none', 'low', 'high', 'max')
glm.supports_images  # False — a 405 on DeepInfra
```

`get(key)` and `ALL` are the whole API. A key is `gateway:model_id`, because a
model's behaviour belongs to the gateway serving it, not to the model alone.

## Using it from an app

```bash
uv add "git+https://github.com/lachlancahill/llm-catalogue" --branch main
```

`uv.lock` pins the exact commit, so builds stay reproducible while `main` moves. To
take a newer catalogue: `uv lock --upgrade-package llm-catalogue`, run the app's
tests, and deploy. The Dockerfile stage that runs `uv sync` needs `git`:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
```

## Where each fact comes from

| File | Holds | Written by |
|---|---|---|
| `src/llm_catalogue/published.json` | Prices, context, deprecation from live listings | `uv run main.py` |
| `src/llm_catalogue/manual.py` | Anthropic and OpenAI prices, OpenAI limits (no machine-readable source) | A person, with page and date |
| `src/llm_catalogue/measured.py` | Tools, temperature, images, effort ladder, reasoning replay | A person, from the probes, with provenance |

## Working on it

```bash
uv sync
uv run pre-commit install         # secret scanning; this repo is public
uv run pytest
uv run ruff check . && uv run ruff format --check .

# Refresh published facts (needs TOGETHER_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY):
uv run main.py

# Measure a model before adding it (costs real money; edit the constants at the top first):
uv run -m scripts.probe_model
uv run -m scripts.probe_anthropic
uv run -m scripts.probe_images
```

When probing OpenAI, unset `OPENAI_BASE_URL` and use OpenAI's own key. A shell that
points the OpenAI SDK at another gateway makes it measure that gateway instead,
and `scripts/common.py` refuses to run in that state.

Adding a model: probe it, add its entry to `measured.py` (and `manual.py` for
Anthropic or OpenAI), run `uv run main.py`, then `uv run pytest`.

## Public-repo rules

- No key, secret name or GCP project id ever enters the repo. Scripts read keys
  from the environment.
- Provenance cites notes by number ("wandly 0178") and copies only measurements,
  never the surrounding context.
- Assume anything pushed is permanent.

Design decisions are in `research/`, starting with `research/README.md`.
