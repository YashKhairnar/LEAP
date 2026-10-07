"""Losses and anti-collapse diagnostics for learner-state JEPA training."""

from __future__ import annotations

import torch
import torch.nn.functional as F


def cosine_prediction_loss(
    predicted_state: torch.Tensor,
    target_state: torch.Tensor,
) -> torch.Tensor:
    """Minimize cosine distance between predicted and stop-gradient target states."""
    if predicted_state.shape != target_state.shape:
        raise ValueError("predicted_state and target_state must have the same shape")
    return 1.0 - F.cosine_similarity(
        predicted_state,
        target_state.detach(),
        dim=-1,
    ).mean()


def variance_regularization(states: torch.Tensor, minimum_std: float = 1.0) -> torch.Tensor:
    """Penalize state dimensions whose batch standard deviation collapses."""
    if states.ndim != 2:
        raise ValueError("states must have shape [batch, state_dim]")
    standard_deviation = torch.sqrt(states.var(dim=0, unbiased=False) + 1e-4)
    return F.relu(minimum_std - standard_deviation).mean()


def jepa_loss(
    predicted_state: torch.Tensor,
    target_state: torch.Tensor,
    context_state: torch.Tensor,
    *,
    variance_weight: float = 0.1,
    minimum_std: float = 1.0,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Combine future-state prediction with context-state variance regularization."""
    prediction = cosine_prediction_loss(predicted_state, target_state)
    variance = variance_regularization(context_state, minimum_std)
    total = prediction + variance_weight * variance
    metrics = {
        "loss": total.detach(),
        "prediction_loss": prediction.detach(),
        "variance_loss": variance.detach(),
        "context_state_std": context_state.detach().std(dim=0, unbiased=False).mean(),
    }
    return total, metrics

