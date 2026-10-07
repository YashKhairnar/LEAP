"""Tutoring-domain JEPA baseline that receives no instructional action."""

from pathlib import Path
from typing import Any

import torch
from torch import nn

from .action_conditioned_jepa import MomentumTargetEncoder


class NoActionPredictor(nn.Module):
    """Predict a residual learner-state update without action information."""

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
        )
        self.output_norm = nn.LayerNorm(state_dim)

    def forward(self, learner_state: torch.Tensor) -> torch.Tensor:
        return self.output_norm(learner_state + self.network(learner_state))


class NoActionJEPA(nn.Module):
    """Use identical tutoring histories and targets while omitting the action."""

    def __init__(
        self,
        observation_encoder: nn.Module,
        temporal_encoder: nn.Module,
        predictor: nn.Module,
        *,
        train_temporal_encoder: bool = False,
    ) -> None:
        super().__init__()
        self.context_observation_encoder = observation_encoder
        self.target_observation_encoder = MomentumTargetEncoder(observation_encoder)
        self.context_temporal_encoder = temporal_encoder
        self.target_temporal_encoder = MomentumTargetEncoder(temporal_encoder)
        self.predictor = predictor
        self._temporal_trainable = False
        self.set_temporal_trainable(train_temporal_encoder)

    def set_temporal_trainable(self, trainable: bool) -> None:
        self._temporal_trainable = trainable
        self.context_temporal_encoder.requires_grad_(trainable)
        self.context_temporal_encoder.train(self.training and trainable)

    def train(self, mode: bool = True) -> "NoActionJEPA":
        super().train(mode)
        self.target_observation_encoder.eval()
        self.target_temporal_encoder.eval()
        if not self._temporal_trainable:
            self.context_temporal_encoder.eval()
        return self

    def trainable_parameters(self):
        return (parameter for parameter in self.parameters() if parameter.requires_grad)

    @torch.no_grad()
    def update_target_encoders(self, momentum: float = 0.996) -> None:
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
        checkpoint = torch.load(checkpoint_path, map_location=map_location, weights_only=False)
        state_dict = checkpoint.get("model_state_dict", checkpoint)
        context_state = {
            key.removeprefix("context_encoder."): value
            for key, value in state_dict.items()
            if key.startswith("context_encoder.")
        }
        target_state = {
            key.removeprefix("target_encoder.encoder."): value
            for key, value in state_dict.items()
            if key.startswith("target_encoder.encoder.")
        }
        if not context_state:
            raise ValueError("Checkpoint has no context temporal encoder weights")
        self.context_temporal_encoder.load_state_dict(context_state)
        self.target_temporal_encoder.encoder.load_state_dict(target_state or context_state)
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
        predicted_state = self.predictor(current_state)
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
        no_action = current_state.new_empty((current_state.shape[0], 0))
        return predicted_state, target_state, current_state, no_action
