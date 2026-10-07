import torch
from torch import nn

from leap.action.models import (
    ActionConditionedJEPA,
    ActionConditionedPredictor,
    ActionEncoder,
)
from leap.learner_state.models import TemporalLearnerEncoder
from leap.observation.models import ObservationEncoder


def _make_model() -> ActionConditionedJEPA:
    observation_encoder = ObservationEncoder(
        response_dim=12,
        numeric_dim=4,
        hidden_dim=16,
        output_dim=16,
        dropout=0.0,
    )
    temporal_encoder = TemporalLearnerEncoder(
        code_dim=16,
        d_model=16,
        state_dim=8,
        num_layers=1,
        num_heads=2,
        feedforward_dim=24,
        max_attempts=3,
        dropout=0.0,
    )
    action_encoder = ActionEncoder(
        task_count=2,
        stage_count=3,
        step_count=4,
        action_type_count=5,
        content_count=6,
        categorical_dim=4,
        prompt_dim=12,
        action_dim=6,
    )
    predictor = ActionConditionedPredictor(
        state_dim=8, action_dim=6, hidden_dim=16, dropout=0.0
    )
    return ActionConditionedJEPA(
        observation_encoder, temporal_encoder, action_encoder, predictor
    )


def _make_batch() -> dict[str, torch.Tensor]:
    batch_size, attempts = 2, 3
    return {
        "context_response_embeddings": torch.randn(batch_size, attempts, 12),
        "context_numeric_features": torch.randn(batch_size, attempts, 4),
        "context_metadata": torch.randn(batch_size, attempts, 3),
        "context_padding_mask": torch.zeros(batch_size, attempts, dtype=torch.bool),
        "target_response_embeddings": torch.randn(batch_size, attempts, 12),
        "target_numeric_features": torch.randn(batch_size, attempts, 4),
        "target_metadata": torch.randn(batch_size, attempts, 3),
        "target_padding_mask": torch.zeros(batch_size, attempts, dtype=torch.bool),
        "task_id": torch.tensor([0, 1]),
        "stage_id": torch.tensor([1, 2]),
        "step_id": torch.tensor([2, 3]),
        "action_type_id": torch.tensor([3, 4]),
        "content_id": torch.tensor([4, 5]),
        "prompt_embedding": torch.randn(batch_size, 12),
    }


def test_forward_shapes_and_gradient_boundaries():
    model = _make_model()
    model.train()

    predicted, target, current, action = model(_make_batch())
    nn.functional.mse_loss(predicted, target).backward()

    assert predicted.shape == target.shape == current.shape == (2, 8)
    assert action.shape == (2, 6)
    assert any(
        parameter.grad is not None
        for parameter in model.context_observation_encoder.parameters()
    )
    assert any(parameter.grad is not None for parameter in model.action_encoder.parameters())
    assert all(
        parameter.grad is None
        for parameter in model.context_temporal_encoder.parameters()
    )
    assert all(
        parameter.grad is None
        for parameter in model.target_observation_encoder.parameters()
    )


def test_target_encoder_uses_ema_update():
    model = _make_model()
    context_parameter = next(model.context_observation_encoder.parameters())
    target_parameter = next(model.target_observation_encoder.parameters())
    original_target = target_parameter.detach().clone()

    with torch.no_grad():
        context_parameter.add_(2.0)
    model.update_target_encoders(momentum=0.5)

    assert torch.allclose(target_parameter, original_target + 1.0)
