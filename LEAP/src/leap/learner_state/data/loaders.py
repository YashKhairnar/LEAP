"""DataLoader construction for JEPA experiments."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader

from leap.code_embeddings.store import EmbeddingLookup
from .jepa_dataset import JEPAPrefixDataset


def build_jepa_dataloaders(config: dict[str, Any]) -> dict[str, DataLoader]:
    """Build leakage-free loaders that share one memory-mapped embedding lookup."""
    trajectory_path = Path(config["trajectory_path"])
    embedding_path = Path(config["embedding_path"])
    split_path = Path(config["split_path"])
    max_attempts = int(config["max_attempts"])
    batch_size = int(config["batch_size"])
    num_workers = int(config.get("num_workers", 0))
    if batch_size < 1 or num_workers < 0:
        raise ValueError("batch_size must be positive and num_workers cannot be negative")

    lookup = EmbeddingLookup(embedding_path)
    datasets = {
        split: JEPAPrefixDataset(
            trajectory_path,
            embedding_path,
            max_attempts=max_attempts,
            split_path=split_path,
            split=split,
            embedding_lookup=lookup,
        )
        for split in ("train", "validation", "test")
    }

    generator = torch.Generator().manual_seed(int(config["seed"]))
    return {
        split: DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=split == "train",
            num_workers=num_workers,
            persistent_workers=num_workers > 0,
            generator=generator if split == "train" else None,
        )
        for split, dataset in datasets.items()
    }
