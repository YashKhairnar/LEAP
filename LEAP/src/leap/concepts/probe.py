"""Linear probe for decoding concept mastery from learner states."""

from __future__ import annotations

import torch
from torch import nn


class ConceptProbe(nn.Module):
    """Map a frozen learner state to generic ML concept mastery logits."""

    def __init__(self, state_dim: int = 128, concept_count: int = 64) -> None:
        super().__init__()
        self.linear = nn.Linear(state_dim, concept_count)

    def forward(self, learner_state: torch.Tensor) -> torch.Tensor:
        if learner_state.ndim != 2:
            raise ValueError("learner_state must have shape [batch, state_dim]")
        return self.linear(learner_state)

    @torch.no_grad()
    def mastery(self, learner_state: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(self(learner_state))


def masked_probe_loss(
    logits: torch.Tensor,
    targets: torch.Tensor,
    mask: torch.Tensor,
) -> torch.Tensor:
    """Binary cross-entropy over concepts with prior learner evidence."""
    if logits.shape != targets.shape or logits.shape != mask.shape:
        raise ValueError("logits, targets, and mask must have the same shape")
    if not mask.any():
        raise ValueError("mask contains no supervised concepts")
    return nn.functional.binary_cross_entropy_with_logits(logits[mask], targets[mask])
