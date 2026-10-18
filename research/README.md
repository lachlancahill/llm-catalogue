# Research index

Design decisions and findings for llm-catalogue. Read this first in a new session.

## Decisions

- [0001 — Why this repo exists](0001-why-this-repo-exists.md): the plan, copied from chat 0048. The three kinds of fact, why the repo is public, git-dependency pinning, the rollout order across the five apps.
- [0002 — The catalogue as built](0002-the-catalogue-as-built.md): name, layout, one writer per fact, `None` for unmeasured, `none` on the ladder, the extra fields, how refresh fails.
- [0003 — What the first refresh and probes found](0003-first-refresh-and-probes.md): DeepInfra discounts, OpenAI price cuts and long-context tier, Sonnet 5.5 cache at 0.05x, Claude 5.5 and MiMo probe results. Read before piloting an app.
- [0004 — Adding DeepSeek-V4.1-Flash-1017](0004-deepseek-v4.1-flash-1017.md): the first model added after the build. Probed fresh on DeepInfra, ladder `none/low/high/max`, 0.51 promo discount, not on Together yet.
- [0005 — V4.1-Flash-1017 replaces the September checkpoint and becomes the default](0005-v4.1-flash-1017-replaces-september-and-becomes-default.md): the September entry is removed; assistant defaults and every use of the old Flash move to 1017; wandly and legal switch only after their quality harnesses pass.

## Debug notes

None yet. Issue-specific investigations go in `debug/YYYY-MM-DD-slug.md`.
