"""Validation and test evaluation for learner-state JEPA."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

import torch
import torch.nn.functional as F

from leap.learner_state.models import LearnerJEPA

from .losses import jepa_loss
from .step import move_jepa_batch


@torch.inference_mode()
def evaluate_jepa(
    model: LearnerJEPA,
    loader: Iterable[dict[str, Any]],
    device: str | torch.device,
    *,
    variance_weight: float = 0.1,
    minimum_std: float = 1.0,
    max_batches: int | None = None,
) -> dict[str, float]:
    """Evaluate without optimizer or EMA updates."""
    model.eval()
    totals: defaultdict[str, float] = defaultdict(float)
    examples = 0
    batches = 0

    for batch_index, raw_batch in enumerate(loader):
        if max_batches is not None and batch_index >= max_batches:
            break
        batch = move_jepa_batch(raw_batch, device)
        predicted, target, context = model(
            batch["context_embeddings"],
            batch["context_metadata"],
            batch["context_padding_mask"],
            batch["target_embeddings"],
            batch["target_metadata"],
            batch["target_padding_mask"],
        )
        _, metrics = jepa_loss(
            predicted,
            target,
            context,
            variance_weight=variance_weight,
            minimum_std=minimum_std,
        )
        batch_size = predicted.shape[0]
        for name, value in metrics.items():
            totals[name] += float(value.cpu()) * batch_size
        examples += batch_size
        batches += 1

    if not examples:
        raise ValueError("Evaluation loader produced no examples")
    result = {name: value / examples for name, value in totals.items()}
    result["cosine_similarity"] = 1.0 - result["prediction_loss"]
    result["examples"] = float(examples)
    result["batches"] = float(batches)
    return result


@torch.inference_mode()
def evaluate_identity_baseline(
    model: LearnerJEPA,
    loader: Iterable[dict[str, Any]],
    device: str | torch.device,
    *,
    max_batches: int | None = None,
) -> dict[str, float]:
    """Compare the predictor against using the unchanged current state."""
    model.eval()
    predicted_values: list[torch.Tensor] = []
    identity_values: list[torch.Tensor] = []

    for batch_index, raw_batch in enumerate(loader):
        if max_batches is not None and batch_index >= max_batches:
            break
        batch = move_jepa_batch(raw_batch, device)
        predicted, target, current = model(
            batch["context_embeddings"],
            batch["context_metadata"],
            batch["context_padding_mask"],
            batch["target_embeddings"],
            batch["target_metadata"],
            batch["target_padding_mask"],
        )
        predicted_values.append(F.cosine_similarity(predicted, target, dim=-1).cpu())
        identity_values.append(F.cosine_similarity(current, target, dim=-1).cpu())

    if not predicted_values:
        raise ValueError("Evaluation loader produced no examples")
    predicted_cosine = torch.cat(predicted_values)
    identity_cosine = torch.cat(identity_values)
    improvement = predicted_cosine - identity_cosine
    standard_error = improvement.std(unbiased=True) / improvement.numel() ** 0.5
    return {
        "examples": float(improvement.numel()),
        "predicted_target_cosine": float(predicted_cosine.mean()),
        "identity_target_cosine": float(identity_cosine.mean()),
        "mean_improvement": float(improvement.mean()),
        "median_improvement": float(improvement.median()),
        "improvement_standard_error": float(standard_error),
        "improvement_ci95_lower": float(improvement.mean() - 1.96 * standard_error),
        "improvement_ci95_upper": float(improvement.mean() + 1.96 * standard_error),
        "predictor_win_rate": float((improvement > 0).float().mean()),
        "tie_rate": float((improvement == 0).float().mean()),
    }
