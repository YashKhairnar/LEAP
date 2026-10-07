"""Lazy context/future prefix pairs for learner-state JEPA training."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import Dataset

from leap.code_embeddings.store import EmbeddingLookup, code_sha256
from .splitting import load_student_split


class JEPAPrefixDataset(Dataset[dict[str, Any]]):
    """Create one example for each observed transition between consecutive attempts."""

    def __init__(
        self,
        trajectory_path: str | Path,
        embedding_path: str | Path,
        *,
        max_attempts: int = 20,
        split_path: str | Path | None = None,
        split: str | None = None,
        embedding_lookup: EmbeddingLookup | None = None,
    ) -> None:
        if max_attempts < 2:
            raise ValueError("max_attempts must be at least 2 for context/future pairs")
        if (split_path is None) != (split is None):
            raise ValueError("split_path and split must be provided together")

        self.trajectory_path = Path(trajectory_path)
        self.max_attempts = max_attempts
        allowed_students = load_student_split(split_path, split) if split_path else None
        self.examples = self._index_examples(self.trajectory_path, allowed_students)

        self.embedding_lookup = embedding_lookup or EmbeddingLookup(embedding_path)
        self.embedding_dim = self.embedding_lookup.embedding_dim

    @staticmethod
    def _index_examples(path: Path, allowed_students: set[str] | None) -> list[tuple[int, int]]:
        examples: list[tuple[int, int]] = []
        with path.open("rb") as file:
            while True:
                offset = file.tell()
                line = file.readline()
                if not line:
                    break
                if not line.strip():
                    continue
                trajectory = json.loads(line)
                if allowed_students is not None and str(trajectory["student_id"]) not in allowed_students:
                    continue
                # target_index is the future attempt; context ends one attempt earlier.
                examples.extend((offset, target_index) for target_index in range(1, len(trajectory["attempts"])))
        return examples

    def __len__(self) -> int:
        return len(self.examples)

    def _read_trajectory(self, offset: int) -> dict[str, Any]:
        with self.trajectory_path.open("rb") as file:
            file.seek(offset)
            return json.loads(file.readline())

    def _tensorize_window(
        self,
        all_attempts: list[dict[str, Any]],
        start: int,
        end: int,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        embeddings = torch.zeros(self.max_attempts, self.embedding_dim, dtype=torch.float32)
        metadata = torch.zeros(self.max_attempts, 3, dtype=torch.float32)
        padding_mask = torch.ones(self.max_attempts, dtype=torch.bool)

        for position, absolute_index in enumerate(range(start, end)):
            attempt = all_attempts[absolute_index]
            identifier = code_sha256(str(attempt["code"]))
            try:
                embedding = self.embedding_lookup.get(identifier)
            except KeyError as error:
                raise KeyError(
                    f"No embedding for attempt {attempt.get('attempt_number', absolute_index + 1)}"
                ) from error

            attempt_number = int(attempt.get("attempt_number", absolute_index + 1))
            previous_correct = bool(all_attempts[absolute_index - 1]["correct"]) if absolute_index else False
            embeddings[position] = embedding
            metadata[position] = torch.tensor(
                [
                    min(attempt_number / self.max_attempts, 1.0),
                    float(previous_correct),
                    float(absolute_index == 0),
                ],
                dtype=torch.float32,
            )
            padding_mask[position] = False
        return embeddings, metadata, padding_mask

    def __getitem__(self, index: int) -> dict[str, Any]:
        offset, target_index = self.examples[index]
        trajectory = self._read_trajectory(offset)
        attempts = trajectory["attempts"]

        # Rolling history retains later transitions instead of discarding attempts
        # beyond max_attempts. Target has at most max_attempts entries; context has one less.
        start = max(0, target_index - self.max_attempts + 1)
        context = self._tensorize_window(attempts, start, target_index)
        target = self._tensorize_window(attempts, start, target_index + 1)

        return {
            "trajectory_id": trajectory["trajectory_id"],
            "student_id": str(trajectory["student_id"]),
            "target_attempt_number": int(
                attempts[target_index].get("attempt_number", target_index + 1)
            ),
            "target_correct": bool(attempts[target_index]["correct"]),
            "context_embeddings": context[0],
            "context_metadata": context[1],
            "context_padding_mask": context[2],
            "target_embeddings": target[0],
            "target_metadata": target[1],
            "target_padding_mask": target[2],
        }
