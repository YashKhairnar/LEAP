"""Predict a future learner state conditioned on an instructional action."""

from __future__ import annotations

import torch
from torch import nn


class ActionConditionedPredictor(nn.Module):
    """Predict a residual update from learner-state and action vectors."""

    def __init__(
        self,
        state_dim: int = 128,
        action_dim: int = 32,
        hidden_dim: int = 256,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.network = nn.Sequential(
            nn.Linear(state_dim + action_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, state_dim),
        )
        self.output_norm = nn.LayerNorm(state_dim)

    def forward(
        self,
        learner_state: torch.Tensor,
        action_vector: torch.Tensor,
    ) -> torch.Tensor:
        if learner_state.ndim != 2 or learner_state.shape[-1] != self.state_dim:
            raise ValueError(
                f"learner_state must have shape [batch, {self.state_dim}]"
            )
        if action_vector.ndim != 2 or action_vector.shape[-1] != self.action_dim:
            raise ValueError(
                f"action_vector must have shape [batch, {self.action_dim}]"
            )
        if learner_state.shape[0] != action_vector.shape[0]:
            raise ValueError("learner_state and action_vector must share the batch dimension")

        combined = torch.cat([learner_state, action_vector], dim=-1)
        state_delta = self.network(combined)
        return self.output_norm(learner_state + state_delta)
