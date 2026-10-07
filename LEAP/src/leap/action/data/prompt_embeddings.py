"""Creation and lookup of frozen instructional-prompt embeddings."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import torch

from leap.action.models.prompt_encoder import PromptEncoder


def prompt_sha256(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


class PromptEmbeddingLookup:
    def __init__(self, path: str | Path) -> None:
        store = load_prompt_embedding_store(path)
        self.checkpoint = str(store["checkpoint"])
        self.embedding_dim = int(store["embedding_dim"])
        self.embeddings: torch.Tensor = store["embeddings"]
        self.index = {value: row for row, value in enumerate(store["prompt_hashes"])}

    def get_prompt(self, prompt: str) -> torch.Tensor:
        return self.embeddings[self.index[prompt_sha256(prompt)]]


def generate_prompt_embedding_store(
    action_data_path: str | Path,
    output_path: str | Path,
    encoder: PromptEncoder,
    *,
    checkpoint: str,
    batch_size: int = 32,
) -> dict[str, Any]:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    unique: dict[str, str] = {}
    with Path(action_data_path).open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                prompt = str(json.loads(line)["prompt"])
                unique.setdefault(prompt_sha256(prompt), prompt)
    hashes = list(unique)
    prompts = [unique[value] for value in hashes]
    batches = [
        encoder.encode(prompts[start:start + batch_size])
        for start in range(0, len(prompts), batch_size)
    ]
    embeddings = torch.cat(batches) if batches else torch.empty((0, encoder.embedding_dim))
    store = {
        "format_version": 1,
        "checkpoint": checkpoint,
        "embedding_dim": encoder.embedding_dim,
        "prompt_hashes": hashes,
        "embeddings": embeddings,
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(store, output_path)
    return {
        "output_path": str(output_path), "unique_prompts": len(hashes),
        "embedding_dim": encoder.embedding_dim, "checkpoint": checkpoint,
    }


def load_prompt_embedding_store(path: str | Path) -> dict[str, Any]:
    try:
        store = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    except TypeError:
        store = torch.load(path, map_location="cpu")
    required = {"format_version", "checkpoint", "embedding_dim", "prompt_hashes", "embeddings"}
    missing = required.difference(store)
    if missing:
        raise ValueError(f"Prompt embedding store is missing: {', '.join(sorted(missing))}")
    if store["format_version"] != 1:
        raise ValueError(f"Unsupported prompt embedding format: {store['format_version']}")
    if len(store["prompt_hashes"]) != len(store["embeddings"]):
        raise ValueError("Prompt hashes and embedding rows have different lengths")
    return store
