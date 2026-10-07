"""Training and evaluation utilities for the concept probe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from .probe import ConceptProbe, masked_probe_loss


@torch.no_grad()
def fit_mean_baseline(loader: DataLoader, concept_count: int = 64) -> torch.Tensor:
    """Estimate a Laplace-smoothed training-set mean per concept."""
    sums = torch.zeros(concept_count)
    counts = torch.zeros(concept_count)
    for _, targets, mask in loader:
        sums += (targets * mask).sum(dim=0)
        counts += mask.sum(dim=0)
    return (sums + 1.0) / (counts + 2.0)


@torch.no_grad()
def evaluate_mean_baseline(
    concept_means: torch.Tensor,
    loader: DataLoader,
) -> dict[str, float | int]:
    """Evaluate constant per-concept predictions on a split."""
    loss_sum = 0.0
    absolute_error_sum = 0.0
    supervised_values = 0
    for _, targets, mask in loader:
        predictions = concept_means.unsqueeze(0).expand_as(targets)
        count = int(mask.sum())
        loss_sum += float(F.binary_cross_entropy(predictions[mask], targets[mask])) * count
        absolute_error_sum += float((predictions[mask] - targets[mask]).abs().sum())
        supervised_values += count
    return {
        "loss": loss_sum / supervised_values,
        "mae": absolute_error_sum / supervised_values,
        "supervised_values": supervised_values,
    }


@torch.no_grad()
def evaluate_probe(
    model: ConceptProbe,
    loader: DataLoader,
    device: torch.device,
) -> dict[str, Any]:
    model.eval()
    loss_sum = 0.0
    absolute_error_sum = 0.0
    supervised_values = 0
    concept_error_sum = torch.zeros(model.linear.out_features)
    concept_support = torch.zeros(model.linear.out_features, dtype=torch.long)
    for states, targets, mask in loader:
        states, targets, mask = states.to(device), targets.to(device), mask.to(device)
        logits = model(states)
        count = int(mask.sum())
        loss_sum += float(masked_probe_loss(logits, targets, mask)) * count
        absolute_errors = (torch.sigmoid(logits) - targets).abs()
        absolute_error_sum += float(absolute_errors[mask].sum())
        supervised_values += count
        concept_error_sum += (absolute_errors * mask).sum(dim=0).cpu()
        concept_support += mask.sum(dim=0).cpu()
    if supervised_values == 0:
        raise ValueError("Probe evaluation has no supervised concept values")
    per_concept_mae = [
        float(concept_error_sum[index] / support) if support else None
        for index, support in enumerate(concept_support)
    ]
    return {
        "loss": loss_sum / supervised_values,
        "mae": absolute_error_sum / supervised_values,
        "supervised_values": supervised_values,
        "concept_support": concept_support.tolist(),
        "per_concept_mae": per_concept_mae,
    }


def fit_probe(
    model: ConceptProbe,
    loaders: dict[str, DataLoader],
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    config: dict[str, Any],
) -> dict[str, Any]:
    checkpoint_path = Path(config["checkpoint_path"])
    metrics_path = Path(config["metrics_path"])
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text("", encoding="utf-8")
    best_validation_loss = float("inf")
    best_epoch = 0

    for epoch in range(1, int(config["epochs"]) + 1):
        model.train()
        train_loss_sum = 0.0
        train_values = 0
        for states, targets, mask in loaders["train"]:
            states, targets, mask = states.to(device), targets.to(device), mask.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = masked_probe_loss(model(states), targets, mask)
            loss.backward()
            optimizer.step()
            count = int(mask.sum())
            train_loss_sum += float(loss.detach()) * count
            train_values += count

        validation = evaluate_probe(model, loaders["validation"], device)
        train_loss = train_loss_sum / train_values
        improved = validation["loss"] < best_validation_loss
        if improved:
            best_validation_loss = float(validation["loss"])
            best_epoch = epoch
            torch.save(
                {
                    "format_version": 1,
                    "experiment": config.get("experiment_name", "concept_probe_v1"),
                    "epoch": epoch,
                    "best_validation_loss": best_validation_loss,
                    "model_state_dict": model.state_dict(),
                    "config": config,
                },
                checkpoint_path,
            )
        with metrics_path.open("a", encoding="utf-8") as file:
            file.write(
                json.dumps(
                    {
                        "epoch": epoch,
                        "train_loss": train_loss,
                        "validation_loss": validation["loss"],
                        "validation_mae": validation["mae"],
                        "best_validation_loss": best_validation_loss,
                    }
                )
                + "\n"
            )
    return {
        "best_epoch": best_epoch,
        "best_validation_loss": best_validation_loss,
        "checkpoint_path": str(checkpoint_path),
    }


def load_probe_checkpoint(
    path: str | Path,
    model: ConceptProbe,
    map_location: str | torch.device = "cpu",
    expected_experiment: str = "concept_probe_v1",
) -> dict[str, Any]:
    checkpoint = torch.load(path, map_location=map_location, weights_only=False)
    if checkpoint.get("experiment") != expected_experiment:
        raise ValueError("Not a concept-probe checkpoint")
    model.load_state_dict(checkpoint["model_state_dict"])
    return checkpoint
