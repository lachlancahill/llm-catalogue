"""
Refresh the catalogue's published facts from the providers' live listings.

    uv run main.py

Needs TOGETHER_API_KEY, ANTHROPIC_API_KEY and OPENAI_API_KEY in the environment
(DeepInfra's listing is public). Exits 1 on a model a gateway no longer lists or
marks deprecated. The probes are separate, because they cost money and are run
only when a model is added: `uv run -m scripts.probe_model` and friends.
"""

import sys

from scripts.common import configure_logging
from scripts.refresh import refresh


def main() -> None:
    configure_logging()
    if not refresh():
        sys.exit(1)


if __name__ == "__main__":
    main()
