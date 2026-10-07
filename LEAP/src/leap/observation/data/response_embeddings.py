"""Generate and load cached learner-response embeddings."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import torch

from leap.observation.models.response_text_encoder import ResponseTextEncoder


def response_sha256(response: str) -> str:
    return hashlib.sha256(response.encode("utf-8")).hexdigest()


class ResponseEmbeddingLookup:
    def __init__(self, path: str | Path) -> None:
        store = load_response_embedding_store(path)
        self.embedding_dim = int(store["embedding_dim"])
        self.embeddings = store["embeddings"]
        self.index = {value: row for row, value in enumerate(store["response_hashes"])}

    def get_response(self, response: str) -> torch.Tensor:
        return self.embeddings[self.index[response_sha256(response)]]


def generate_response_embedding_store(
    observation_data_path: str | Path,
    output_path: str | Path,
    encoder: ResponseTextEncoder,
    *,
    checkpoint: str,
    batch_size: int = 32,
) -> dict[str, Any]:
    unique: dict[str, str] = {}
    with Path(observation_data_path).open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                response = str(json.loads(line)["response"])
                unique.setdefault(response_sha256(response), response)
    hashes = list(unique)
    responses = [unique[value] for value in hashes]
    batches = [encoder.encode(responses[i:i + batch_size]) for i in range(0, len(responses), batch_size)]
    embeddings = torch.cat(batches) if batches else torch.empty((0, encoder.embedding_dim))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "format_version": 1, "checkpoint": checkpoint,
        "embedding_dim": encoder.embedding_dim,
        "response_hashes": hashes, "embeddings": embeddings,
    }, output_path)
    return {
        "output_path": str(output_path), "unique_responses": len(hashes),
        "embedding_dim": encoder.embedding_dim, "checkpoint": checkpoint,
    }


def load_response_embedding_store(path: str | Path) -> dict[str, Any]:
    try:
        store = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    except TypeError:
        store = torch.load(path, map_location="cpu")
    required = {"format_version", "checkpoint", "embedding_dim", "response_hashes", "embeddings"}
    missing = required.difference(store)
    if missing:
        raise ValueError(f"Response embedding store is missing: {', '.join(sorted(missing))}")
    if store["format_version"] != 1:
        raise ValueError(f"Unsupported response embedding format: {store['format_version']}")
    return store
