"""
A shared catalogue of facts about the LLMs Lachlan's apps call.

    import llm_catalogue
    glm = llm_catalogue.get("deepinfra:zai-org/GLM-5.3")
    glm.prompt_price_per_mtok, glm.effort_ladder, glm.supports_tools

`get(key)` and `ALL` are the whole public surface. Apps pin this package by git
commit (research/0001, decision 3), so what an app sees changes only when it
bumps its lock and runs its tests, never at runtime.

The entries are joined at import from three files, one writer each:
`published.json` (written by `scripts/refresh.py`), `manual.py` (typed prices
for providers that publish none) and `measured.py` (typed measurements). A key
that is missing from one of them, or a fact written by two of them, fails the
import rather than producing an entry with a hole in it.
"""

import json
from importlib.resources import files

from llm_catalogue.manual import MANUAL
from llm_catalogue.measured import MEASURED
from llm_catalogue.model import CatalogModel

__all__ = ["ALL", "CatalogModel", "get"]


def _load() -> dict[str, CatalogModel]:
    """Join the three sources into one CatalogModel per key, in `measured.py`'s order."""
    published = json.loads(files("llm_catalogue").joinpath("published.json").read_text())

    if set(published) != set(MEASURED):
        raise ValueError(
            "published.json and measured.py disagree on keys. Only in published.json: "
            f"{sorted(set(published) - set(MEASURED))}; only in measured.py: "
            f"{sorted(set(MEASURED) - set(published))}. Run scripts/refresh.py after "
            "adding or removing a model."
        )
    stray = set(MANUAL) - set(MEASURED)
    if stray:
        raise ValueError(f"manual.py has keys measured.py does not: {sorted(stray)}.")

    models = {}
    for key, measured in MEASURED.items():
        manual = MANUAL.get(key, {})
        overlap = (set(published[key]) & set(manual)) | (
            (set(published[key]) | set(manual)) & set(measured)
        )
        if overlap:
            raise ValueError(f"{key}: {sorted(overlap)} set by more than one source.")
        models[key] = CatalogModel(key=key, **published[key], **manual, **measured)
    return models


_MODELS = _load()

ALL: tuple[CatalogModel, ...] = tuple(_MODELS.values())


def get(key: str) -> CatalogModel:
    """
    The entry for `gateway:api_model_name`, e.g. `deepinfra:zai-org/GLM-5.3`.

    Raises KeyError for an unknown key. There is no fallback: which model to use
    instead is an app's decision, and guessing it here would hide the mistake.
    """
    if key not in _MODELS:
        raise KeyError(f"{key!r} is not in llm_catalogue. Known keys: {sorted(_MODELS)}")
    return _MODELS[key]
