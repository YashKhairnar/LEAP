"""Momentum-updated target encoder for JEPA training."""

from __future__ import annotations

from copy import deepcopy

import torch
from torch import nn


class TargetEncoder(nn.Module):
    """Frozen copy of a context encoder, updated only by exponential moving average."""

    def __init__(self, context_encoder: nn.Module) -> None:
        super().__init__()
        self.encoder = deepcopy(context_encoder)
        self.encoder.requires_grad_(False)
        self.train(False)

    def train(self, mode: bool = True) -> "TargetEncoder":
        """Keep the target in evaluation mode even when its parent model trains."""
        super().train(False)
        self.encoder.eval()
        return self

    @torch.no_grad()
    def update_from_context(self, context_encoder: nn.Module, momentum: float = 0.996) -> None:
        """Move target parameters toward context parameters using EMA."""
        if not 0.0 <= momentum <= 1.0:
            raise ValueError("momentum must be between 0 and 1")

        context_parameters = dict(context_encoder.named_parameters())
        target_parameters = dict(self.encoder.named_parameters())
        if context_parameters.keys() != target_parameters.keys():
            raise ValueError("Context and target encoders do not have matching parameters")

        for name, target_parameter in target_parameters.items():
            target_parameter.mul_(momentum).add_(
                context_parameters[name].detach(), alpha=1.0 - momentum
            )

        # LayerNorm currently has no running buffers, but copying buffers makes this
        # wrapper safe if the encoder later gains BatchNorm or other stateful layers.
        context_buffers = dict(context_encoder.named_buffers())
        target_buffers = dict(self.encoder.named_buffers())
        if context_buffers.keys() != target_buffers.keys():
            raise ValueError("Context and target encoders do not have matching buffers")
        for name, target_buffer in target_buffers.items():
            target_buffer.copy_(context_buffers[name])

    @torch.no_grad()
    def forward(
        self,
        code_embeddings: torch.Tensor,
        metadata: torch.Tensor,
        padding_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Encode a future trajectory prefix without building a gradient graph."""
        return self.encoder(code_embeddings, metadata, padding_mask)
