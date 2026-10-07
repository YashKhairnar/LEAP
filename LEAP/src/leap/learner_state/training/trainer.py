"""Epoch-level JEPA training orchestration."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import torch

from leap.learner_state.models import LearnerJEPA

from .checkpointing import save_checkpoint
from .evaluation import evaluate_jepa
from .step import move_jepa_batch, train_jepa_step


def train_jepa_epoch(
    model: LearnerJEPA,
    loader,
    optimizer: torch.optim.Optimizer,
    device: str | torch.device,
    config: dict[str, Any],
    *,
    max_batches: int | None = None,
) -> dict[str, float]:
    """Train for one epoch and return mean step metrics."""
    totals: defaultdict[str, float] = defaultdict(float)
    batches = 0
    log_every = int(config.get("log_every_batches", 100))

    for batch_index, raw_batch in enumerate(loader):
        if max_batches is not None and batch_index >= max_batches:
            break
        batch = move_jepa_batch(raw_batch, device)
        metrics = train_jepa_step(
            model,
            batch,
            optimizer,
            target_momentum=float(config["target_momentum"]),
            variance_weight=float(config["variance_weight"]),
            minimum_std=float(config["minimum_state_std"]),
            max_gradient_norm=float(config["max_gradient_norm"]),
        )
        for name, value in metrics.items():
            totals[name] += value
        batches += 1
        if log_every > 0 and batches % log_every == 0:
            print(
                f"  batch {batches:,}: loss={totals['loss']/batches:.4f}, "
                f"cos={1.0-totals['prediction_loss']/batches:.4f}, "
                f"state_std={totals['context_state_std']/batches:.4f}"
            )

    if not batches:
        raise ValueError("Training loader produced no batches")
    result = {name: value / batches for name, value in totals.items()}
    result["cosine_similarity"] = 1.0 - result["prediction_loss"]
    result["batches"] = float(batches)
    return result


def fit_jepa(
    model: LearnerJEPA,
    loaders: dict[str, Any],
    optimizer: torch.optim.Optimizer,
    device: str | torch.device,
    config: dict[str, Any],
    *,
    start_epoch: int = 0,
    best_validation_loss: float = float("inf"),
    max_train_batches: int | None = None,
    max_validation_batches: int | None = None,
    append_history: bool = False,
) -> dict[str, Any]:
    """Train, validate, write history, and maintain latest/best checkpoints."""
    checkpoint_directory = Path(config["checkpoint_directory"])
    metrics_path = Path(config["metrics_path"])
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    history_mode = "a" if append_history else "w"
    history: list[dict[str, Any]] = []

    with metrics_path.open(history_mode, encoding="utf-8") as metrics_file:
        for epoch in range(start_epoch + 1, int(config["epochs"]) + 1):
            print(f"Epoch {epoch}/{config['epochs']}")
            train_metrics = train_jepa_epoch(
                model,
                loaders["train"],
                optimizer,
                device,
                config,
                max_batches=max_train_batches,
            )
            validation_metrics = evaluate_jepa(
                model,
                loaders["validation"],
                device,
                variance_weight=float(config["variance_weight"]),
                minimum_std=float(config["minimum_state_std"]),
                max_batches=max_validation_batches,
            )
            record = {"epoch": epoch, "train": train_metrics, "validation": validation_metrics}
            history.append(record)
            metrics_file.write(json.dumps(record) + "\n")
            metrics_file.flush()

            validation_loss = validation_metrics["loss"]
            if validation_loss < best_validation_loss:
                best_validation_loss = validation_loss
                save_checkpoint(
                    checkpoint_directory / "best_validation.pt",
                    model,
                    optimizer,
                    epoch=epoch,
                    best_validation_loss=best_validation_loss,
                    config=config,
                )
            save_checkpoint(
                checkpoint_directory / "latest.pt",
                model,
                optimizer,
                epoch=epoch,
                best_validation_loss=best_validation_loss,
                config=config,
            )
            print(
                f"  train loss={train_metrics['loss']:.4f}, "
                f"validation loss={validation_loss:.4f}, "
                f"validation cosine={validation_metrics['cosine_similarity']:.4f}"
            )

    return {"history": history, "best_validation_loss": best_validation_loss}

