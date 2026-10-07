"""Versioned question-generation specifications for tutor actions."""

import json
from pathlib import Path
from typing import Any


class ActionSpecificationCatalog:
    def __init__(self, path: str | Path) -> None:
        with Path(path).open(encoding="utf-8") as file:
            data = json.load(file)
        self.schema_version = str(data["schema_version"])
        self.name = str(data["name"])
        self.curriculum_boundary = str(data.get("curriculum_boundary", ""))
        self.actions: dict[str, dict[str, Any]] = data["actions"]

    def get(self, action_type: str) -> dict[str, Any]:
        if action_type not in self.actions:
            raise KeyError(f"No question specification for action type: {action_type}")
        return dict(self.actions[action_type])
