"""One-step model-predictive planner for tutoring actions."""

from __future__ import annotations

from typing import Any, Literal

import torch
import torch.nn.functional as F
from torch import nn

from leap.action.models import ActionConditionedJEPA

ACTION_KEYS = (
    "task_id",
    "stage_id",
    "step_id",
    "action_type_id",
    "content_id",
    "prompt_embedding",
)


class OneStepPlanner(nn.Module):
    """Choose the action whose predicted state is closest to a goal state."""

    def __init__(
        self,
        model: ActionConditionedJEPA,
        distance: Literal["cosine", "euclidean"] = "cosine",
        concept_probe: nn.Module | None = None,
    ) -> None:
        super().__init__()
        if distance not in {"cosine", "euclidean"}:
            raise ValueError("distance must be 'cosine' or 'euclidean'")
        self.model = model
        self.distance = distance
        self.concept_probe = concept_probe

    @torch.no_grad()
    def encode_current_state(self, history_batch: dict[str, torch.Tensor]) -> torch.Tensor:
        """Encode the observations available before the next tutor action."""
        self.model.eval()
        observations = self.model.context_observation_encoder(
            {
                "response_embedding": history_batch["context_response_embeddings"],
                "numeric_features": history_batch["context_numeric_features"],
            }
        )
        return self.model.context_temporal_encoder(
            observations,
            history_batch["context_metadata"],
            history_batch["context_padding_mask"],
        )

    def _distances(
        self, predicted_states: torch.Tensor, goal_state: torch.Tensor
    ) -> torch.Tensor:
        expanded_goal = goal_state.unsqueeze(1).expand_as(predicted_states)
        if self.distance == "cosine":
            return 1.0 - F.cosine_similarity(predicted_states, expanded_goal, dim=-1)
        return torch.linalg.vector_norm(predicted_states - expanded_goal, dim=-1)

    @torch.no_grad()
    def forward(
        self,
        current_state: torch.Tensor,
        candidate_actions: dict[str, torch.Tensor],
        goal_state: torch.Tensor,
        valid_action_mask: torch.Tensor | None = None,
    ) -> dict[str, Any]:
        """Evaluate candidates and return the best action for each learner.

        Candidate categorical tensors have shape ``[B, A]`` and prompt embeddings have
        shape ``[B, A, prompt_dim]``, where ``A`` is normally three.
        """
        self.model.eval()
        if current_state.ndim != 2:
            raise ValueError("current_state must have shape [batch, state_dim]")
        if goal_state.ndim == 1:
            goal_state = goal_state.unsqueeze(0).expand(current_state.shape[0], -1)
        if goal_state.shape != current_state.shape:
            raise ValueError("goal_state must have shape [state_dim] or [batch, state_dim]")
        missing = set(ACTION_KEYS) - candidate_actions.keys()
        if missing:
            raise KeyError(f"Missing candidate action fields: {sorted(missing)}")

        batch_size = current_state.shape[0]
        categorical_shape = candidate_actions["task_id"].shape
        if len(categorical_shape) != 2 or categorical_shape[0] != batch_size:
            raise ValueError("candidate action IDs must have shape [batch, actions]")
        action_count = categorical_shape[1]
        if action_count < 1:
            raise ValueError("At least one candidate action is required")
        for key in ACTION_KEYS[:-1]:
            if candidate_actions[key].shape != categorical_shape:
                raise ValueError(f"{key} must have shape [batch, actions]")
        prompt_embeddings = candidate_actions["prompt_embedding"]
        if prompt_embeddings.shape[:2] != categorical_shape:
            raise ValueError("prompt_embedding must have shape [batch, actions, prompt_dim]")

        flat_actions = {
            key: candidate_actions[key].reshape(batch_size * action_count, *candidate_actions[key].shape[2:])
            for key in ACTION_KEYS
        }
        action_vectors = self.model.action_encoder(flat_actions).reshape(
            batch_size, action_count, -1
        )
        repeated_states = current_state.unsqueeze(1).expand(-1, action_count, -1)
        predicted_states = self.model.predictor(
            repeated_states.reshape(batch_size * action_count, -1),
            action_vectors.reshape(batch_size * action_count, -1),
        ).reshape(batch_size, action_count, -1)

        distances = self._distances(predicted_states, goal_state)
        if valid_action_mask is not None:
            if valid_action_mask.shape != categorical_shape:
                raise ValueError("valid_action_mask must have shape [batch, actions]")
            valid_action_mask = valid_action_mask.bool()
            if not valid_action_mask.any(dim=1).all():
                raise ValueError("Each learner must have at least one valid action")
            distances = distances.masked_fill(~valid_action_mask, float("inf"))

        selected_indices = distances.argmin(dim=1)
        row_indices = torch.arange(batch_size, device=current_state.device)
        selected_actions = {
            key: value[row_indices, selected_indices]
            for key, value in candidate_actions.items()
        }
        result = {
            "selected_indices": selected_indices,
            "selected_actions": selected_actions,
            "selected_predicted_states": predicted_states[row_indices, selected_indices],
            "selected_distances": distances[row_indices, selected_indices],
            "candidate_predicted_states": predicted_states,
            "candidate_action_vectors": action_vectors,
            "candidate_distances": distances,
        }
        if self.concept_probe is not None:
            self.concept_probe.eval()
            concept_mastery = torch.sigmoid(
                self.concept_probe(predicted_states.reshape(batch_size * action_count, -1))
            ).reshape(batch_size, action_count, -1)
            result["candidate_concept_mastery"] = concept_mastery
            result["selected_concept_mastery"] = concept_mastery[
                row_indices, selected_indices
            ]
        return result

    @torch.no_grad()
    def plan_from_history(
        self,
        history_batch: dict[str, torch.Tensor],
        candidate_actions: dict[str, torch.Tensor],
        goal_state: torch.Tensor,
        valid_action_mask: torch.Tensor | None = None,
    ) -> dict[str, Any]:
        """Encode the current history and perform one-step planning."""
        current_state = self.encode_current_state(history_batch)
        result = self(current_state, candidate_actions, goal_state, valid_action_mask)
        result["current_state"] = current_state
        return result
