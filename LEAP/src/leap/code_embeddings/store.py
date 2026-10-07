"""Creation and storage of code-embedding lookup tables."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import torch

from leap.code_embeddings.encoder import CodeEncoder


class EmbeddingLookup:
    """Memory-mapped embeddings plus one shared hash-to-row index."""

    def __init__(self, path: str | Path) -> None:
        store = load_embedding_store(path)
        self.checkpoint = str(store["checkpoint"])
        self.embedding_dim = int(store["embedding_dim"])
        self.embeddings: torch.Tensor = store["embeddings"]
        self.index = {identifier: row for row, identifier in enumerate(store["code_hashes"])}

    def __len__(self) -> int:
        return len(self.embeddings)

    def get(self, identifier: str) -> torch.Tensor:
        return self.embeddings[self.index[identifier]]


def code_sha256(code: str) -> str:
    """Return a stable content identifier for a normalized code submission."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def iter_unique_code(trajectory_path: str | Path) -> Iterable[tuple[str, str]]:
    """Yield ``(hash, code)`` once for every unique submission in a JSONL file."""
    seen: set[str] = set()
    with Path(trajectory_path).open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                trajectory = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on trajectory line {line_number}") from error
            for attempt in trajectory.get("attempts", []):
                code = str(attempt["code"])
                identifier = code_sha256(code)
                if identifier not in seen:
                    seen.add(identifier)
                    yield identifier, code


def generate_embedding_store(
    trajectory_path: str | Path,
    output_path: str | Path,
    encoder: CodeEncoder,
    *,
    checkpoint: str,
    batch_size: int = 32,
) -> dict[str, Any]:
    """Encode unique submissions and save a versioned PyTorch lookup table."""
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    hashes: list[str] = []
    embedding_batches: list[torch.Tensor] = []
    pending_hashes: list[str] = []
    pending_code: list[str] = []

    def flush() -> None:
        if not pending_code:
            return
        batch = encoder.encode(pending_code)
        if batch.shape != (len(pending_code), encoder.embedding_dim):
            raise ValueError("Code encoder returned an unexpected embedding shape")
        hashes.extend(pending_hashes)
        embedding_batches.append(batch)
        pending_hashes.clear()
        pending_code.clear()

    for identifier, code in iter_unique_code(trajectory_path):
        pending_hashes.append(identifier)
        pending_code.append(code)
        if len(pending_code) == batch_size:
            flush()
    flush()

    embeddings = (
        torch.cat(embedding_batches, dim=0)
        if embedding_batches
        else torch.empty((0, encoder.embedding_dim), dtype=torch.float32)
    )
    store = {
        "format_version": 1,
        "checkpoint": checkpoint,
        "embedding_dim": encoder.embedding_dim,
        "code_hashes": hashes,
        "embeddings": embeddings,
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(store, output_path)
    return {
        "output_path": str(output_path),
        "unique_submissions": len(hashes),
        "embedding_dim": encoder.embedding_dim,
        "checkpoint": checkpoint,
    }


def load_embedding_store(path: str | Path) -> dict[str, Any]:
    """Load and validate a code-embedding lookup table."""
    try:
        store = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    except TypeError:  # Compatibility with older PyTorch versions.
        store = torch.load(path, map_location="cpu")

    required = {"format_version", "checkpoint", "embedding_dim", "code_hashes", "embeddings"}
    missing = required.difference(store)
    if missing:
        raise ValueError(f"Embedding store is missing: {', '.join(sorted(missing))}")
    if store["format_version"] != 1:
        raise ValueError(f"Unsupported embedding format version: {store['format_version']}")
    if len(store["code_hashes"]) != len(store["embeddings"]):
        raise ValueError("Embedding hashes and tensor rows have different lengths")
    if store["embeddings"].ndim != 2 or store["embeddings"].shape[1] != store["embedding_dim"]:
        raise ValueError("Embedding tensor shape does not match embedding_dim")
    return store
