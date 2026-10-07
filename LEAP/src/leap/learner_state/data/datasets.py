"""PyTorch datasets for padded learner trajectories."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import torch
from torch.utils.data import Dataset

from leap.code_embeddings.store import code_sha256, load_embedding_store


class TrajectoryDataset(Dataset[dict[str, Any]]):
    """Join trajectory JSONL records to precomputed code embeddings."""

    def __init__(
        self,
        trajectory_path: str | Path,
        embedding_path: str | Path,
        *,
        max_attempts: int = 20,
        truncation: Literal["earliest", "latest"] = "latest",
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if truncation not in {"earliest", "latest"}:
            raise ValueError("truncation must be 'earliest' or 'latest'")

        self.trajectory_path = Path(trajectory_path)
        self.max_attempts = max_attempts
        self.truncation = truncation
        self.offsets = self._index_lines(self.trajectory_path)

        store = load_embedding_store(embedding_path)
        self.embedding_dim = int(store["embedding_dim"])
        self.embeddings: torch.Tensor = store["embeddings"]
        self.embedding_index = {identifier: i for i, identifier in enumerate(store["code_hashes"])}

    @staticmethod
    def _index_lines(path: Path) -> list[int]:
        offsets: list[int] = []
        with path.open("rb") as file:
            while True:
                offset = file.tell()
                line = file.readline()
                if not line:
                    break
                if line.strip():
                    offsets.append(offset)
        return offsets

    def __len__(self) -> int:
        return len(self.offsets)

    def _read_trajectory(self, index: int) -> dict[str, Any]:
        with self.trajectory_path.open("rb") as file:
            file.seek(self.offsets[index])
            return json.loads(file.readline())

    def __getitem__(self, index: int) -> dict[str, Any]:
        trajectory = self._read_trajectory(index)
        all_attempts = trajectory["attempts"]
        if self.truncation == "latest":
            attempts = all_attempts[-self.max_attempts :]
        else:
            attempts = all_attempts[: self.max_attempts]

        count = len(attempts)
        code_embeddings = torch.zeros(self.max_attempts, self.embedding_dim, dtype=torch.float32)
        metadata = torch.zeros(self.max_attempts, 3, dtype=torch.float32)
        correctness = torch.zeros(self.max_attempts, dtype=torch.bool)
        padding_mask = torch.ones(self.max_attempts, dtype=torch.bool)

        for position, attempt in enumerate(attempts):
            identifier = code_sha256(str(attempt["code"]))
            try:
                embedding_row = self.embedding_index[identifier]
            except KeyError as error:
                raise KeyError(
                    f"No embedding for trajectory {trajectory['trajectory_id']} attempt "
                    f"{attempt.get('attempt_number', position + 1)}"
                ) from error

            original_number = int(attempt.get("attempt_number", position + 1))
            previous_correct = (
                bool(all_attempts[original_number - 2]["correct"]) if original_number > 1 else False
            )
            code_embeddings[position] = self.embeddings[embedding_row]
            metadata[position] = torch.tensor(
                [
                    min(original_number / self.max_attempts, 1.0),
                    float(previous_correct),
                    float(original_number == 1),
                ]
            )
            correctness[position] = bool(attempt["correct"])
            padding_mask[position] = False

        return {
            "trajectory_id": trajectory["trajectory_id"],
            "code_embeddings": code_embeddings,
            "metadata": metadata,
            "padding_mask": padding_mask,
            "correctness": correctness,
            "attempt_count": count,
        }

