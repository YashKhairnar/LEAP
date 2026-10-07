"""Trainable adapter from tutoring observations to attempt representations."""

import torch
from torch import nn


class ObservationEncoder(nn.Module):
    def __init__(
        self,
        response_dim: int = 384,
        numeric_dim: int = 4,
        hidden_dim: int = 384,
        output_dim: int = 256,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(response_dim + numeric_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, output_dim),
            nn.LayerNorm(output_dim),
        )

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        features = torch.cat([
            batch["response_embedding"],
            batch["numeric_features"],
        ], dim=-1)
        return self.network(features)
