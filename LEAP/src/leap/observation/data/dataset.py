"""Dataset of learner observations and cached response embeddings."""

import json
import math
from pathlib import Path

import torch
from torch.utils.data import Dataset

from .response_embeddings import ResponseEmbeddingLookup


def observation_numeric_features(record: dict) -> torch.Tensor:
    """Convert one observation's scalar outcomes into four bounded features."""
    response_time = min(max(float(record["response_time_ms"]), 0.0), 300_000.0)
    return torch.tensor([
        float(record["correct"]),
        float(record["score"]),
        min(max(float(record["attempt"]), 0.0), 10.0) / 10.0,
        math.log1p(response_time) / math.log1p(300_000.0),
    ], dtype=torch.float32)


class ObservationDataset(Dataset):
    def __init__(self, data_path, response_embedding_path) -> None:
        with Path(data_path).open(encoding="utf-8") as file:
            self.data = [json.loads(line) for line in file if line.strip()]
        self.response_embeddings = ResponseEmbeddingLookup(response_embedding_path)

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        record = self.data[index]
        return {
            "response_embedding": self.response_embeddings.get_response(record["response"]),
            "numeric_features": observation_numeric_features(record),
        }
