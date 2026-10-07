"""Preprocess learner observations from tutoring transitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def extract_observation_data(raw_record: dict[str, Any]) -> dict[str, Any]:
    learning_record = raw_record["learning_record"]
    if isinstance(learning_record, str):
        learning_record = json.loads(learning_record)
    transition = learning_record["transition"]["payload"]
    observation = transition["observation"]
    return {
        "transition_id": transition["transition_id"],
        "learner_id": transition["learner_id"],
        "session_id": transition["session_id"],
        "sequence_index": transition["sequence_index"],
        "response": str(transition["learner_action"]["response"]),
        "correct": bool(observation["correct"]),
        "score": float(observation["score"]),
        "attempt": int(observation["attempt"]),
        "response_time_ms": int(observation["response_time_ms"]),
    }


def prepare_observation_dataset(
    input_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    with Path(input_path).open(encoding="utf-8") as file:
        raw_records = json.load(file)
    if not isinstance(raw_records, list):
        raise TypeError("Transition export must contain a JSON list")
    records = [extract_observation_data(record) for record in raw_records]
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record) + "\n")
    return {
        "records": len(records),
        "output_path": str(output_path),
    }
