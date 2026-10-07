"""Predict a future learner state from the current learner state."""

import torch
from torch import nn


class FutureStatePredictor(nn.Module):
    """MLP mapping ``[batch, state_dim]`` to a future state of the same size."""

    def __init__(
        self,
        state_dim: int = 128,
        hidden_dim: int = 256,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, state_dim),
            nn.LayerNorm(state_dim),
        )

    def forward(self, current_state: torch.Tensor) -> torch.Tensor:
        if current_state.ndim != 2:
            raise ValueError("current_state must have shape [batch, state_dim]")
        return self.network(current_state)

