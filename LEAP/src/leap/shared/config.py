"""Small configuration helpers shared by experiment entry points."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_config(path: str | Path) -> dict[str, Any]:
    """Load a JSON experiment configuration."""
    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)

