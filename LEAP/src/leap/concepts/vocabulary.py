"""Load and encode the versioned LEAP concept ontology."""

from __future__ import annotations

import json
from pathlib import Path

import torch


class ConceptVocabulary:
    def __init__(self, path: str | Path) -> None:
        with Path(path).open(encoding="utf-8") as file:
            data = json.load(file)
        self.schema_version = str(data["schema_version"])
        self.name = str(data["name"])
        self.capacity = int(data["capacity"])
        self.concepts = list(data["concepts"])
        self.stage_mappings = data["stage_mappings"]
        self.objective_mappings = data["objective_mappings"]
        self.indices = {str(item["id"]): int(item["index"]) for item in self.concepts}
        self._validate()

    def _validate(self) -> None:
        if len(self.indices) != len(self.concepts):
            raise ValueError("Concept IDs must be unique")
        indices = list(self.indices.values())
        if len(set(indices)) != len(indices):
            raise ValueError("Concept indices must be unique")
        if any(index < 0 or index >= self.capacity for index in indices):
            raise ValueError("Concept index is outside vocabulary capacity")
        known = set(self.indices)
        for mapping_group in (self.stage_mappings, self.objective_mappings):
            for task_mappings in mapping_group.values():
                for mapped_concepts in task_mappings.values():
                    unknown = set(mapped_concepts) - known
                    if unknown:
                        raise ValueError(f"Mappings reference unknown concepts: {unknown}")

    def concepts_for_stage(self, task: str, stage: str) -> list[str]:
        return list(self.stage_mappings.get(task, {}).get(stage, []))

    def concepts_for_objective(self, task: str, objective: str) -> list[str]:
        return list(self.objective_mappings.get(task, {}).get(objective, []))

    def encode(self, concept_ids: list[str]) -> torch.Tensor:
        """Return a capacity-sized multi-hot concept vector."""
        vector = torch.zeros(self.capacity)
        for concept_id in concept_ids:
            if concept_id not in self.indices:
                raise KeyError(f"Unknown concept: {concept_id}")
            vector[self.indices[concept_id]] = 1.0
        return vector
