"""Save and restore complete JEPA training state."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import torch

from leap.learner_state.models import LearnerJEPA


def save_checkpoint(
    path: str | Path,
    model: LearnerJEPA,
    optimizer: torch.optim.Optimizer,
    *,
    epoch: int,
    best_validation_loss: float,
    config: dict[str, Any],
) -> None:
    """Write a checkpoint atomically so interruption cannot leave a partial file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    torch.save(
        {
            "format_version": 1,
            "epoch": epoch,
            "best_validation_loss": best_validation_loss,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "config": config,
        },
        temporary_path,
    )
    temporary_path.replace(path)


def load_checkpoint(
    path: str | Path,
    model: LearnerJEPA,
    optimizer: torch.optim.Optimizer | None = None,
    *,
    map_location: str | torch.device = "cpu",
) -> dict[str, Any]:
    """Restore model and optional optimizer state, returning checkpoint metadata."""
    checkpoint = torch.load(path, map_location=map_location, weights_only=False)
    if checkpoint.get("format_version") != 1:
        raise ValueError(f"Unsupported checkpoint version: {checkpoint.get('format_version')}")
    model.load_state_dict(checkpoint["model_state_dict"])
    if optimizer is not None:
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    return checkpoint

