"""Chronological training pairs for action-conditioned learner dynamics."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import Dataset

from leap.observation.data import ResponseEmbeddingLookup, observation_numeric_features

from .prompt_embeddings import PromptEmbeddingLookup
from .splitting import load_tutoring_split

ACTION_FIELDS = ("task", "stage", "step", "action_type", "content_id")
ACTION_OUTPUT_NAMES = {
    "task": "task_id",
    "stage": "stage_id",
    "step": "step_id",
    "action_type": "action_type_id",
    "content_id": "content_id",
}


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


class ActionConditionedDataset(Dataset):
    """Return history before an action, that action, and history after its response."""

    def __init__(
        self,
        action_data_path: str | Path,
        observation_data_path: str | Path,
        action_vocabulary_path: str | Path,
        prompt_embedding_path: str | Path,
        response_embedding_path: str | Path,
        *,
        max_history: int = 20,
        allowed_learners: set[str] | None = None,
        split_path: str | Path | None = None,
        split: str | None = None,
    ) -> None:
        if max_history < 1:
            raise ValueError("max_history must be at least 1")
        if (split_path is None) != (split is None):
            raise ValueError("split_path and split must be provided together")
        if allowed_learners is not None and split_path is not None:
            raise ValueError("Use allowed_learners or split_path, not both")
        if split_path is not None and split is not None:
            allowed_learners = load_tutoring_split(split_path, split)
        self.max_history = max_history
        with Path(action_vocabulary_path).open(encoding="utf-8") as file:
            self.action_vocabularies = json.load(file)
        self.prompt_embeddings = PromptEmbeddingLookup(prompt_embedding_path)
        self.response_embeddings = ResponseEmbeddingLookup(response_embedding_path)

        actions = {record["transition_id"]: record for record in _read_jsonl(action_data_path)}
        observations = {
            record["transition_id"]: record for record in _read_jsonl(observation_data_path)
        }
        if actions.keys() != observations.keys():
            missing_actions = observations.keys() - actions.keys()
            missing_observations = actions.keys() - observations.keys()
            raise ValueError(
                "Action/observation transition IDs differ: "
                f"missing_actions={len(missing_actions)}, "
                f"missing_observations={len(missing_observations)}"
            )

        sessions: defaultdict[tuple[str, str], list[tuple[dict, dict]]] = defaultdict(list)
        for transition_id, observation in observations.items():
            learner_id = str(observation["learner_id"])
            if allowed_learners is not None and learner_id not in allowed_learners:
                continue
            action = actions[transition_id]
            if (
                str(action["learner_id"]) != learner_id
                or str(action["session_id"]) != str(observation["session_id"])
                or int(action["sequence_index"]) != int(observation["sequence_index"])
            ):
                raise ValueError(f"Joined transition metadata differs for {transition_id}")
            sessions[(learner_id, str(observation["session_id"]))].append((action, observation))

        self.examples: list[tuple[list[dict], dict, dict]] = []
        for transitions in sessions.values():
            transitions.sort(key=lambda pair: int(pair[1]["sequence_index"]))
            observations_so_far: list[dict] = []
            for action, observation in transitions:
                self.examples.append((list(observations_so_far), action, observation))
                observations_so_far.append(observation)

    def __len__(self) -> int:
        return len(self.examples)

    def _history_tensors(self, history: list[dict]) -> dict[str, torch.Tensor]:
        selected = history[-self.max_history :]
        response_dim = self.response_embeddings.embedding_dim
        response_embeddings = torch.zeros(self.max_history, response_dim)
        numeric_features = torch.zeros(self.max_history, 4)
        metadata = torch.zeros(self.max_history, 3)
        padding_mask = torch.ones(self.max_history, dtype=torch.bool)
        history_offset = len(history) - len(selected)

        for position, observation in enumerate(selected):
            absolute_index = history_offset + position
            response_embeddings[position] = self.response_embeddings.get_response(
                observation["response"]
            )
            numeric_features[position] = observation_numeric_features(observation)
            previous_correct = bool(history[absolute_index - 1]["correct"]) if absolute_index else False
            metadata[position] = torch.tensor([
                min((absolute_index + 1) / self.max_history, 1.0),
                float(previous_correct),
                float(absolute_index == 0),
            ])
            padding_mask[position] = False
        return {
            "response_embeddings": response_embeddings,
            "numeric_features": numeric_features,
            "metadata": metadata,
            "padding_mask": padding_mask,
        }

    def __getitem__(self, index: int) -> dict[str, Any]:
        history, action, current_observation = self.examples[index]
        context = self._history_tensors(history)
        target = self._history_tensors([*history, current_observation])
        item: dict[str, Any] = {
            "transition_id": action["transition_id"],
            "learner_id": str(action["learner_id"]),
            "session_id": str(action["session_id"]),
            "sequence_index": int(action["sequence_index"]),
            "context_response_embeddings": context["response_embeddings"],
            "context_numeric_features": context["numeric_features"],
            "context_metadata": context["metadata"],
            "context_padding_mask": context["padding_mask"],
            "target_response_embeddings": target["response_embeddings"],
            "target_numeric_features": target["numeric_features"],
            "target_metadata": target["metadata"],
            "target_padding_mask": target["padding_mask"],
        }
        for field in ACTION_FIELDS:
            item[ACTION_OUTPUT_NAMES[field]] = torch.tensor(
                self.action_vocabularies[field].get(
                    action[field], self.action_vocabularies[field]["<UNK>"]
                ),
                dtype=torch.long,
            )
        item["prompt_embedding"] = self.prompt_embeddings.get_prompt(action["prompt"])
        return item
