"""One optimizer step for learner-state JEPA training."""

from __future__ import annotations

from typing import Any

import torch

from leap.learner_state.models.jepa import LearnerJEPA

from .losses import jepa_loss


JEPA_BATCH_KEYS = {
    "context_embeddings",
    "context_metadata",
    "context_padding_mask",
    "target_embeddings",
    "target_metadata",
    "target_padding_mask",
}


def move_jepa_batch(
    batch: dict[str, Any],
    device: str | torch.device,
) -> dict[str, Any]:
    """Move tensor values to the training device while preserving metadata fields."""
    return {
        key: value.to(device) if isinstance(value, torch.Tensor) else value
        for key, value in batch.items()
    }


def train_jepa_step(
    model: LearnerJEPA,
    batch: dict[str, Any],
    optimizer: torch.optim.Optimizer,
    *,
    target_momentum: float = 0.996,
    variance_weight: float = 0.1,
    minimum_std: float = 1.0,
    max_gradient_norm: float | None = 1.0,
) -> dict[str, float]:
    """Backpropagate through context/predictor, then update the target by EMA."""
    missing = JEPA_BATCH_KEYS.difference(batch)
    if missing:
        raise KeyError(f"JEPA batch is missing: {', '.join(sorted(missing))}")

    model.train()
    optimizer.zero_grad(set_to_none=True)

    predicted_state, target_state, context_state = model(
        batch["context_embeddings"],
        batch["context_metadata"],
        batch["context_padding_mask"],
        batch["target_embeddings"],
        batch["target_metadata"],
        batch["target_padding_mask"],
    )
    loss, metric_tensors = jepa_loss(
        predicted_state,
        target_state,
        context_state,
        variance_weight=variance_weight,
        minimum_std=minimum_std,
    )
    loss.backward()

    if max_gradient_norm is not None:
        gradient_norm = torch.nn.utils.clip_grad_norm_(
            list(model.trainable_parameters()),
            max_norm=max_gradient_norm,
        )
    else:
        gradient_norm = torch.tensor(float("nan"), device=loss.device)

    optimizer.step()
    model.update_target_encoder(momentum=target_momentum)

    metrics = {name: float(value.cpu()) for name, value in metric_tensors.items()}
    metrics["gradient_norm"] = float(gradient_norm.detach().cpu())
    return metrics

