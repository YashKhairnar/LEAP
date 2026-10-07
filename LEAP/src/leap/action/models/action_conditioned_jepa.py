"""Integrated action-conditioned JEPA model."""

from copy import deepcopy
from pathlib import Path
from typing import Any

import torch
from torch import nn


class MomentumTargetEncoder(nn.Module):
    """Frozen exponential-moving-average copy of an encoder."""

    def __init__(self, context_encoder: nn.Module) -> None:
        super().__init__()
        self.encoder = deepcopy(context_encoder)
        self.encoder.requires_grad_(False)
        self.encoder.eval()

    def train(self, mode: bool = True) -> "MomentumTargetEncoder":
        super().train(False)
        self.encoder.eval()
        return self

    @torch.no_grad()
    def update_from_context(
        self, context_encoder: nn.Module, momentum: float = 0.996
    ) -> None:
        if not 0.0 <= momentum <= 1.0:
            raise ValueError("momentum must be between 0 and 1")

        target_parameters = dict(self.encoder.named_parameters())
        for name, context_parameter in context_encoder.named_parameters():
            target_parameters[name].mul_(momentum).add_(
                context_parameter.detach(), alpha=1.0 - momentum
            )

        target_buffers = dict(self.encoder.named_buffers())
        for name, context_buffer in context_encoder.named_buffers():
            target_buffers[name].copy_(context_buffer)

    @torch.no_grad()
    def forward(self, *args: Any, **kwargs: Any) -> Any:
        return self.encoder(*args, **kwargs)


class ActionConditionedJEPA(nn.Module):
    """Predict the next learner state from current history and an action."""

    def __init__(
        self,
        observation_encoder: nn.Module,
        temporal_encoder: nn.Module,
        action_encoder: nn.Module,
        predictor: nn.Module,
        *,
        train_temporal_encoder: bool = False,
    ) -> None:
        super().__init__()
        self.context_observation_encoder = observation_encoder
        self.target_observation_encoder = MomentumTargetEncoder(observation_encoder)
        self.context_temporal_encoder = temporal_encoder
        self.target_temporal_encoder = MomentumTargetEncoder(temporal_encoder)
        self.action_encoder = action_encoder
        self.predictor = predictor
        self._temporal_trainable = False
        self.set_temporal_trainable(train_temporal_encoder)

    def set_temporal_trainable(self, trainable: bool) -> None:
        """Freeze the pretrained temporal encoder or enable fine-tuning."""
        self._temporal_trainable = trainable
        self.context_temporal_encoder.requires_grad_(trainable)
        self.context_temporal_encoder.train(self.training and trainable)

    def train(self, mode: bool = True) -> "ActionConditionedJEPA":
        super().train(mode)
        self.target_observation_encoder.eval()
        self.target_temporal_encoder.eval()
        if not self._temporal_trainable:
            self.context_temporal_encoder.eval()
        return self

    def trainable_parameters(self):
        """Yield optimizer parameters while excluding both target encoders."""
        return (parameter for parameter in self.parameters() if parameter.requires_grad)

    @torch.no_grad()
    def update_target_encoders(self, momentum: float = 0.996) -> None:
        """Update both target branches after an optimizer step."""
        self.target_observation_encoder.update_from_context(
            self.context_observation_encoder, momentum
        )
        self.target_temporal_encoder.update_from_context(
            self.context_temporal_encoder, momentum
        )

    def load_pretrained_temporal_checkpoint(
        self,
        checkpoint_path: str | Path,
        map_location: str | torch.device = "cpu",
    ) -> dict[str, Any]:
        """Load context and target temporal encoders from a learner-JEPA checkpoint."""
        checkpoint = torch.load(
            checkpoint_path, map_location=map_location, weights_only=False
        )
        state_dict = checkpoint.get("model_state_dict", checkpoint)

        context_prefix = "context_encoder."
        target_prefix = "target_encoder.encoder."
        context_state = {
            key.removeprefix(context_prefix): value
            for key, value in state_dict.items()
            if key.startswith(context_prefix)
        }
        target_state = {
            key.removeprefix(target_prefix): value
            for key, value in state_dict.items()
            if key.startswith(target_prefix)
        }
        if not context_state:
            raise ValueError("Checkpoint has no context temporal encoder weights")

        self.context_temporal_encoder.load_state_dict(context_state)
        if target_state:
            self.target_temporal_encoder.encoder.load_state_dict(target_state)
        else:
            self.target_temporal_encoder.encoder.load_state_dict(context_state)
        return checkpoint

    def forward(
        self, batch: dict[str, torch.Tensor]
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        context_observations = self.context_observation_encoder(
            {
                "response_embedding": batch["context_response_embeddings"],
                "numeric_features": batch["context_numeric_features"],
            }
        )
        current_state = self.context_temporal_encoder(
            context_observations,
            batch["context_metadata"],
            batch["context_padding_mask"],
        )
        action_vector = self.action_encoder(batch)
        predicted_state = self.predictor(current_state, action_vector)

        with torch.no_grad():
            target_observations = self.target_observation_encoder(
                {
                    "response_embedding": batch["target_response_embeddings"],
                    "numeric_features": batch["target_numeric_features"],
                }
            )
            target_state = self.target_temporal_encoder(
                target_observations,
                batch["target_metadata"],
                batch["target_padding_mask"],
            )

        return predicted_state, target_state, current_state, action_vector
