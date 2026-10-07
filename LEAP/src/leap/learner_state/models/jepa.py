"""Student-state JEPA model composed from context, target, and predictor networks."""

from __future__ import annotations

import torch
from torch import nn
from .predictor import FutureStatePredictor
from .target_encoder import TargetEncoder


class LearnerJEPA(nn.Module):
    """Predict the target encoder's future state from a context trajectory prefix."""

    def __init__(
        self,
        context_encoder: nn.Module,
        predictor: FutureStatePredictor,
    ) -> None:
        super().__init__()
        self.context_encoder = context_encoder
        self.target_encoder = TargetEncoder(context_encoder)
        self.predictor = predictor

    def train(self, mode: bool = True) -> "LearnerJEPA":
        super().train(mode)
        self.target_encoder.train(False)
        return self

    def forward(
        self,
        context_embeddings: torch.Tensor,
        context_metadata: torch.Tensor,
        context_padding_mask: torch.Tensor,
        target_embeddings: torch.Tensor,
        target_metadata: torch.Tensor,
        target_padding_mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Return predicted future state, target future state, and current state."""
        current_state = self.context_encoder(
            context_embeddings,
            context_metadata,
            context_padding_mask,
        )
        predicted_future_state = self.predictor(current_state)
        target_future_state = self.target_encoder(
            target_embeddings,
            target_metadata,
            target_padding_mask,
        )
        return predicted_future_state, target_future_state, current_state

    @torch.no_grad()
    def update_target_encoder(self, momentum: float = 0.996) -> None:
        self.target_encoder.update_from_context(self.context_encoder, momentum)

    def trainable_parameters(self):
        """Yield only parameters that should be passed to the optimizer."""
        yield from self.context_encoder.parameters()
        yield from self.predictor.parameters()

