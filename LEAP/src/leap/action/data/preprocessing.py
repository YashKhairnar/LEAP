"""Preprocessing utilities for action-conditioned tutoring records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def extract_action_data(raw_record: dict[str, Any]) -> dict[str, Any]:
    """Extract action-encoder inputs from one exported learning record."""
    learning_record = raw_record["learning_record"]
    if isinstance(learning_record, str):
        learning_record = json.loads(learning_record)

    transition = learning_record["transition"]["payload"]
    content = learning_record["content_item"]["payload"]

    return {
        "transition_id": transition["transition_id"],
        "learner_id": transition["learner_id"],
        "session_id": transition["session_id"],
        "sequence_index": transition["sequence_index"],
        "task": transition["location_before"]["task"],
        "stage": transition["location_before"]["stage"],
        "step": transition["location_before"]["step"],
        "action_type": transition["instructional_action"]["action_type"],
        "content_id": transition["instructional_action"]["content_id"],
        "prompt": content["prompt"],
        "learning_objectives": content.get("learning_objectives", []),
    }


def build_vocabulary(records: list[dict[str, Any]], field: str) -> dict[str, int]:
    """Create a deterministic vocabulary with index zero reserved for unknown values."""
    values = sorted({str(record[field]) for record in records})
    return {"<UNK>": 0, **{value: index + 1 for index, value in enumerate(values)}}


def build_action_vocabularies(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Build vocabularies for every categorical action field."""
    fields = ("task", "stage", "step", "action_type", "content_id")
    return {field: build_vocabulary(records, field) for field in fields}


def prepare_action_dataset(
    input_path: str | Path,
    output_path: str | Path,
    vocabulary_path: str | Path,
) -> dict[str, Any]:
    """Write extracted action records and their categorical vocabularies."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    vocabulary_path = Path(vocabulary_path)

    with input_path.open(encoding="utf-8") as file:
        raw_records = json.load(file)
    if not isinstance(raw_records, list):
        raise TypeError("Transition export must contain a JSON list")

    action_records = [extract_action_data(record) for record in raw_records]
    vocabularies = build_action_vocabularies(action_records)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for record in action_records:
            file.write(json.dumps(record) + "\n")

    vocabulary_path.parent.mkdir(parents=True, exist_ok=True)
    vocabulary_path.write_text(
        json.dumps(vocabularies, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "records": len(action_records),
        "output_path": str(output_path),
        "vocabulary_path": str(vocabulary_path),
        "vocabulary_sizes": {name: len(values) for name, values in vocabularies.items()},
    }
